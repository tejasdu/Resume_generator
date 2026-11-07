#!/usr/bin/env python3
"""
Resume Tailor
─────────────
Paste a job description → get a tailored, ATS-optimized one-page PDF resume.
Run with:  python app.py
"""

import os
import json
import asyncio
import io
import datetime
import tempfile
import threading
import webbrowser
from html import escape
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse
from pydantic import BaseModel, ConfigDict, ValidationError
from dotenv import load_dotenv

# ─── Config ───────────────────────────────────────────────────────────────────

load_dotenv()
CODEX_MODEL = os.getenv("RESUME_MODEL", "gpt-6.1-sol")
BUNDLED_CODEX = Path("/Applications/ChatGPT.app/Contents/Resources/codex-cli/bin/codex")
CODEX_BIN = os.getenv("RESUME_CODEX_BIN") or (
    str(BUNDLED_CODEX) if BUNDLED_CODEX.is_file() else "codex"
)

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tailored_resumes")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ─── Contact Links ────────────────────────────────────────────────────────────

LINKS = {
    "linkedin": "https://www.linkedin.com/in/tejas-dumpeta/",
    "github":   "https://github.com/tejasdu",
    "portfolio":"https://tejasdu.github.io/",
}

# ─── Master Knowledge Base ────────────────────────────────────────────────────

MASTER = {
    "summary_variants": {
        "general": (
            "Product and Solutions-oriented Engineer skilled at translating ambiguous stakeholder "
            "problems into clear requirements, actionable execution plans, and deployed systems. "
            "Work best in fast-paced, collaborative environments requiring communication across "
            "cross-functional teams and clients to own and build solutions that drive operational efficiency."
        ),
        "swe": (
            "Full-stack software engineer with a track record of shipping production systems — "
            "from real-time streaming backends to data pipelines and interactive web apps. "
            "Thrive in fast-moving environments where owning the problem end-to-end matters."
        ),
        "hardware": (
            "Pragmatic Software Engineer specializing in hardware-software integration, real-time "
            "telemetry, and C/C++ development. Proven track record of building embedded sensor systems, "
            "engineering Bluetooth/Arduino prototypes, and processing high-fidelity 3D environments "
            "for autonomous vehicle validation. Eager to design and troubleshoot end-to-end "
            "full-system integrations to make products work and create change."
        ),
    },
    "skills": {
        "languages": "Python, C++, C, JavaScript, TypeScript, SQL, Go, R",
        "frameworks_libraries": "FastAPI, React.js, Next.js, Node/Express.js, Redis Streams, Pandas, Tailwind CSS, NumPy, PyTorch, Socket.io",
        "systems_platforms": "Azure, Docker, Kubernetes, OpenShift, PostgreSQL, Redis 7, Supabase, Figma, Vercel, Railway, CI/CD",
        "hardware_integration": "Arduino processors, gyroscopic sensors, Bluetooth Low Energy (BLE), real-time motor telemetry, embedded system circuit-boarding",
        "client_product": (
            "Requirement Scoping, Stakeholder Discovery, Technical Documentation, "
            "Workflow Automation, Cross-Functional Triage & Escalation, "
            "Security & Compliance Auditing, SDLC/practices"
        ),
    },
    "experience": [
        {
            "company": "University of Michigan - IT Services",
            "title": "Technical Solutions Consultant",
            "location": "Ann Arbor, MI",
            "dates": "July 2024 - May 2026",
            "bullets": [
                "Served as a technical consultant for university faculty, staff & students across 19+ departments to translate complex technical diagnostics of university-managed applications into actionable resolutions for various stakeholders",
                "Resolved incident management debugging for campus computing equipment and macOs, Windows & Linux systems",
            ],
        },
        {
            "company": "University of Michigan - IT Services",
            "title": "Software Developer Intern",
            "location": "Ann Arbor, MI",
            "dates": "May 2025 - May 2026",
            "bullets": [
                "Architected custom Python ETL pipelines to integrate third-party APIs (Sunbird DCTrack, NetBox), successfully unifying cross-platform data silos for 23,000+ network devices to drive operational visibility.",
                "Modernized legacy workflows by designing a real-time NDJSON streaming architecture with FastAPI, delivering instant data visibility and continuous uptime for end-user applications.",
                "Maintained AWS & OpenShift deployment environments to reproduce production issues & troubleshoot cross-system integration failures across development and production environments",
                "Architected ETL pipelines to automate real-time synchronization of rack and server inventory for 23,000+ network devices by integrating Sunbird DC Track & Netbox APIs to ensure continuous data integrity & lifecycle tracking",
                "Redesigned backend architecture of a Wi-Fi analytics application by replacing a legacy Splunk job-polling workflow with NDJSON streaming via FastAPI, achieving ASGI-compliant real-time delivery of RADIUS log queries",
            ],
        },
        {
            "company": "Capoom",
            "title": "Software Developer Intern",
            "location": "Ann Arbor, MI",
            "dates": "August 2025 - December 2025",
            "bullets": [
                "Delivered an end-to-end 3D reconstruction pipeline using Gaussian Splatting & semantic segmentation, processing 18,000+ real-world images of the Mcity test track into a high-fidelity digital twin for autonomous vehicle (AV) testing.",
                "Benchmarked our modeling pipelines against ground truth via PSNR and NMI metrics to provide data-backed quality assurance for simulation workflows to our stakeholders.",
                "Engineered an end-to-end 3D reconstruction data pipeline leveraging Gaussian Splatting to process 18,000+ RGB real-world images for synthetic scene generation, creating a high-fidelity digital twin of the UofM City AV testing track to aid in Capoom's AV edge-case training models",
                "Evaluated the RealityCapture & Postshot image-to-model pipeline against ground truth using PSNR & NMI",
            ],
        },
        {
            "company": "Spire Investment Partners",
            "title": "Technology and Cybersecurity Intern",
            "location": "McLean, VA",
            "dates": "June 2024 - August 2024",
            "bullets": [
                "Scoped stakeholder requirements to redesign onboarding workflows for 300+ employees and built a centralized staff directory that streamlined identity & contract verifications via Azure & SQL Rest APIs to cut approval time by 60%.",
                "Managed concurrent IT & security projects across the full SDLC, authoring Business Requirements Documents (BRDs), system architecture documentation, & rollout plans to align executive stakeholders & internal teams.",
                "Architected a centralized staff directory schema and custom REST endpoints for 300+ records, engineering automated sync triggers to propagate profile updates across dependent systems and ensure single-source data consistency",
                "Automated employee onboarding workflows across Microsoft cloud services, writing custom SQL queries and REST-triggered automations to streamline identity & contract verifications and reduce approval turnaround by 60%",
            ],
        },
        {
            "company": "Skylark Drones",
            "title": "Research Intern",
            "location": "Bengaluru, India",
            "dates": "June 2023 - August 2023",
            "bullets": [
                "Accelerated post-mission image processing by 20% for Skylark's enterprise drone analytics platform by building a photo deduplication tool to optimize large-scale aerial datasets for 3D geospatial scene reconstruction of sites.",
                "Accelerated post-mission image processing by 20% for Skylark's drone analytics platform by building a GUI photo deduplication tool (C++) to optimize large-scale aerial datasets for 3D geospatial scene reconstruction of sites.",
            ],
        },
    ],
    "projects": [
        {
            "name": "F1 Pitwall Telemetry Engine",
            "tech": "Python, FastAPI, WebSockets, Docker, Nginx, OpenF1 API",
            "link": "Link",
            "bullets": [
                "Architected an end-to-end real-time telemetry streaming engine using FastAPI and WebSockets to deliver 60 FPS spatial tracking & engine metrics to replay F1 Grand Prix sessions",
                "Engineered an automated cache manager to sync & upload 87 historical races alongside real-time telemetry to the cloud, bypassing strict third-party API rate limits to guarantee zero-buffer session switching & high availability for live users.",
                "Engineered a high-frequency telemetry streaming backend using FastAPI & WebSockets to stream historic F1 races",
                "Created an automated cache manager to continuously sync & upload 87+ historical races alongside real-time telemetry to the cloud, bypassing strict third-party API rate limits to guarantee zero-buffer sessions & high availability.",
            ],
        },
        {
            "name": "Selectaurant",
            "tech": "Next.js, Node.js, TypeScript, Tailwind CSS, Supabase, Socket.io, Leaflet, Google Places API",
            "link": "Link",
            "bullets": [
                "Built a real-time multiplayer web application that allows users to create private lobbies, fetch & filter restaurants via Google Places API, and vote on filtered restaurants to select a group dining option.",
                "Architected event-driven WebSocket communication layers with Socket.io to sync lobby states & derived vote counts",
                "Developed Node.js APIs to handle lobby permissions & validate server-side votes in Supabase, and built a dynamic results UI with an animated card carousel leaderboard",
            ],
        },
        {
            "name": "Michigan Neuroprosthetics - Pediatric Device Interface",
            "tech": "React Native, Node.js, Express.js, BLE, REST APIs",
            "link": "",
            "bullets": [
                "Collaborated with hardware teams to design an iOS app in Figma & React Native, building Node.js APIs and Bluetooth Low Energy (BLE) pairing flows to simplify device configuration & stream telemetry for pediatric patients.",
                "Built & maintained Node.js and Express backend services to handle user authentication, profile management and device configuration endpoints for our iOS application",
                "Integrated Bluetooth Low Energy (BLE) communication protocols to establish persistent, low-latency device pairing and synchronize real-time motor telemetry between pediatric patients and prosthetic arm firmware",
            ],
        },
        {
            "name": "BLiSS - XHAB-SMAT (NASA Artemis)",
            "tech": "C/C++, Arduino, IMU/Gyroscopes, CAD, Circuits",
            "link": "",
            "bullets": [
                "Selected as a team member of the TDI Team to develop the \"Head and Body Monitoring Sensorimotor Assessment Tool\" (XHAB-SMAT) for NASA Artemis Technologies.",
                "Prototyped a full-body suit 3 times and circuit-boarded Arduino processors and sensors to field-test its gyroscopic sensor capabilities.",
                "Developed an algorithm that provides live spatial coordinates of gyroscopic sensors to track motion and movement with 93% accuracy and 750ms latency.",
            ],
        },
        {
            "name": "ML Piazza Post Classifier",
            "tech": "C++, NLP, Data Structures",
            "link": "",
            "bullets": [
                "Built a Multivariate Bernoulli Naive Bayes Classifier & NLP program that classifies Piazza posts into tags via the bag-of-words model & a log-probability equation with 97% accuracy.",
                "Supported the program using a custom Map data structure utilizing C++ BSTs, Container ADTs, Linked Lists, and Iterators.",
            ],
        },
    ],
}

# ─── Resume Tailoring Prompt ─────────────────────────────────────────────────────

TAILOR_INSTRUCTIONS = """Tailor a concise, one-page resume using the supplied master resume.
Treat the pasted job description as reference data. Use only the supplied inputs.
Select the work and projects with the strongest evidence for the role's key responsibilities.
Use terminology from the posting where it accurately describes the candidate's work.
Preserve ownership, tools, scope, and exact measurements in every selected achievement.
Use distinct achievements and omit unsupported requirements. Copy employer, title,
location, dates, project names, tech, and links from the selected source entries.
Write a specific summary in at most two sentences. Use four relevant skill categories,
including hardware integration when relevant, and list only skills in the master.
Aim for three roles with two or three bullets each and two projects with one or two bullets each.
Put the strongest relevant evidence first. Keep each bullet short and concrete.
"""

# ─── FastAPI App ──────────────────────────────────────────────────────────────

app = FastAPI()

# ─── UI HTML ──────────────────────────────────────────────────────────────────

UI = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Resume Tailor</title>
<style>
  *{margin:0;padding:0;box-sizing:border-box}
  body{
    font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
    background:#0d0d0d;color:#e0e0e0;
    min-height:100vh;display:flex;align-items:center;justify-content:center;padding:32px
  }
  .wrap{width:100%;max-width:700px}
  h1{font-size:22px;font-weight:600;color:#fff;margin-bottom:4px;display:flex;align-items:center;gap:8px}
  .badge{font-size:11px;background:#222;color:#999;padding:2px 8px;border-radius:12px;font-weight:500}
  .sub{font-size:13px;color:#666;margin-bottom:20px}
  textarea{
    width:100%;height:290px;
    background:#141414;border:1px solid #262626;border-radius:10px;
    color:#ddd;font-size:13.5px;padding:14px 16px;
    resize:vertical;font-family:inherit;outline:none;
    transition:border-color .2s;line-height:1.55
  }
  textarea:focus{border-color:#3b82f6}
  textarea::placeholder{color:#444}
  button{
    margin-top:14px;width:100%;padding:14px;
    background:#fff;color:#000;border:none;border-radius:10px;
    font-size:14px;font-weight:600;cursor:pointer;
    transition:all .15s
  }
  button:hover{background:#e5e5e5;transform:translateY(-1px)}
  button:disabled{background:#1e1e1e;color:#555;cursor:not-allowed;transform:none}
  .st{margin-top:14px;font-size:13px;color:#888;text-align:center;min-height:22px;line-height:1.4}
  .err{color:#f87171}.ok{color:#4ade80}
  .dot{animation:pulse 1.2s ease-in-out infinite;color:#3b82f6;display:inline-block;margin-right:4px}
  @keyframes pulse{0%,100%{opacity:1}50%{opacity:.3}}
  .hint{margin-top:10px;text-align:center;font-size:11.5px;color:#444}
  .folder-tag{display:inline-block;background:#181818;border:1px solid #2e2e2e;color:#aaa;padding:2px 7px;border-radius:4px;font-family:monospace;font-size:11.5px}
</style>
</head>
<body>
<div class="wrap">
  <h1>Resume Tailor <span class="badge">ChatGPT</span></h1>
  <p class="sub">Paste any job description → generates and saves directly to <span class="folder-tag">tailored_resumes/</span> in seconds.</p>
  <textarea id="jd" placeholder="Paste the job description here... (supports any length)"></textarea>
  <button id="btn" onclick="go()">⚡&nbsp; Generate &amp; Save Resume</button>
  <div class="st" id="st"></div>
  <div class="hint">Tip: press ⌘ + Enter to generate</div>
</div>
<script>
async function go(){
  const jd=document.getElementById('jd').value.trim();
  if(!jd){status('Paste a job description first.','err');return}
  const btn=document.getElementById('btn');
  btn.disabled=true; btn.textContent='Tailoring Resume…';
  status('<span class="dot">●</span> Analyzing job description and optimizing keywords…');
  try{
    const r=await fetch('/generate',{
      method:'POST',headers:{"Content-Type":"application/json"},
      body:JSON.stringify({job_description:jd})
    });
    if(!r.ok){
      const e=await r.json().catch(()=>({}));
      throw new Error(e.detail||'Generation failed. Please try again.');
    }
    const filename = r.headers.get('X-Filename') || 'tailored_resume.pdf';
    const blob=await r.blob();
    const url=URL.createObjectURL(blob);
    const a=document.createElement('a');
    a.href=url;
    a.download=filename;
    a.click();
    URL.revokeObjectURL(url);
    status(`✓ Saved to <span class="folder-tag">tailored_resumes/${filename}</span> and downloaded!`,'ok');
  }catch(e){status('Error: '+e.message,'err',true)}
  finally{btn.disabled=false;btn.textContent='⚡\u00a0 Generate & Save Resume'}
}
function status(msg,cls='',plainText=false){
  const el=document.getElementById('st');if(plainText){el.textContent=msg}else{el.innerHTML=msg};el.className='st '+(cls||'');
}
document.getElementById('jd').addEventListener('keydown',e=>{
  if((e.ctrlKey||e.metaKey)&&e.key==='Enter')go();
});
</script>
</body>
</html>"""

# ─── Resume HTML Template ─────────────────────────────────────────────────────

def build_resume_html(data: dict) -> str:
    """Render tailored resume data into a print-ready, one-page HTML document."""

    # Work experience
    exp_html = ""
    for job in data.get("experience", []):
        bullets = "".join(f"<li>{escape(b)}</li>" for b in job.get("bullets", []))
        exp_html += f"""
<div class="job">
  <div class="row">
    <div><span class="b">{escape(job.get('company',''))}</span> | <span class="i">{escape(job.get('title',''))}</span> | {escape(job.get('location',''))}</div>
    <div class="date">{escape(job.get('dates',''))}</div>
  </div>
  <ul>{bullets}</ul>
</div>"""

    # Projects
    proj_html = ""
    for proj in data.get("projects", []):
        bullets = "".join(f"<li>{escape(b)}</li>" for b in proj.get("bullets", []))
        link = f'&nbsp;&nbsp;<a href="#">{escape(proj["link"])}</a>' if proj.get("link") else ""
        proj_html += f"""
<div class="project">
  <div class="ph"><span class="b">{escape(proj.get('name',''))}</span>: <span class="i">{escape(proj.get('tech',''))}</span>{link}</div>
  <ul>{bullets}</ul>
</div>"""

    # Skills rows — format keys nicely
    skill_rows = ""
    for label, value in data.get("skills", {}).items():
        display = label.replace("_", " ").title().replace("And", "&")
        skill_rows += f'<div class="sk"><span class="b">{escape(display)}:</span> {escape(value)}</div>\n'

    linkedin = LINKS["linkedin"]
    github   = LINKS["github"]
    portfolio= LINKS["portfolio"]

    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
  *{{margin:0;padding:0;box-sizing:border-box}}
  @page{{size:letter;margin:.40in .5in .40in .5in}}
  body{{font-family:Arial,Helvetica,sans-serif;font-size:9.5pt;color:#000;line-height:1.26;background:#fff}}

  /* Header */
  .name{{text-align:center;font-size:17pt;font-weight:700;letter-spacing:.3px;margin-bottom:2px}}
  .contact{{text-align:center;font-size:9pt;margin-bottom:5px}}
  .contact a{{color:#000;text-decoration:none}}
  .contact a:hover{{text-decoration:underline}}

  /* Summary — centered */
  .summary{{font-size:9.2pt;line-height:1.32;margin-bottom:5px;text-align:center}}

  /* Sections */
  .sec{{margin-bottom:4px}}
  .sh{{
    font-size:9.8pt;font-weight:700;text-transform:uppercase;
    letter-spacing:.5px;border-bottom:1.2px solid #000;
    padding-bottom:1px;margin-bottom:3px
  }}

  /* Education */
  .erow{{display:flex;justify-content:space-between;align-items:baseline}}
  .deg{{font-style:italic;font-size:9.5pt}}
  .cw{{font-size:9pt}}

  /* Skills */
  .sk{{font-size:9.2pt;margin-bottom:1.2px}}

  /* Experience */
  .job{{margin-bottom:3.5px}}
  .row{{display:flex;justify-content:space-between;align-items:baseline;margin-bottom:1px;font-size:9.5pt}}
  .date{{white-space:nowrap;margin-left:8px;font-size:9pt}}

  /* Lists */
  ul{{padding-left:13px;margin-top:1px}}
  li{{font-size:9.2pt;margin-bottom:1px;line-height:1.26}}

  /* Projects */
  .project{{margin-bottom:3.5px}}
  .ph{{font-size:9.5pt;margin-bottom:1px}}
  .ph a{{color:#000;text-decoration:underline}}

  /* Helpers */
  .b{{font-weight:700}}
  .i{{font-style:italic}}
</style>
</head>
<body>

<div class="name">Tejas Dumpeta</div>
<div class="contact">
  +1 (734)-489-4824 &nbsp;|&nbsp;
  <a href="mailto:tejasd2022@gmail.com">tejasd2022@gmail.com</a> &nbsp;|&nbsp;
  <a href="{linkedin}">LinkedIn</a> &nbsp;|&nbsp;
  <a href="{github}">GitHub</a> &nbsp;|&nbsp;
  <a href="{portfolio}">Portfolio</a>
</div>

<div class="summary">{escape(data.get('summary',''))}</div>

<div class="sec">
  <div class="sh">Education</div>
  <div class="erow">
    <span class="b">University of Michigan - Ann Arbor</span>
    <span style="font-size:9pt">August 2022 - May 2026</span>
  </div>
  <div class="deg">B.S in Computer Science</div>
  <div class="cw"><span class="b">Relevant Coursework:</span> AI, UI/UX Design, Databases, Data Structures, Computer Networks, Computer Organization</div>
</div>

<div class="sec">
  <div class="sh">Skills</div>
  {skill_rows}
</div>

<div class="sec">
  <div class="sh">Work Experience</div>
  {exp_html}
</div>

<div class="sec">
  <div class="sh">Projects</div>
  {proj_html}
</div>

</body>
</html>"""

# ─── Core: ChatGPT-backed Codex CLI ────────────────────────────────────────────

class ResumeFields(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SkillRow(ResumeFields):
    category: str
    skills: str


class Experience(ResumeFields):
    company: str
    title: str
    location: str
    dates: str
    bullets: list[str]


class Project(ResumeFields):
    name: str
    tech: str
    link: str
    bullets: list[str]


class TailoredResume(ResumeFields):
    summary: str
    skills: list[SkillRow]
    experience: list[Experience]
    projects: list[Project]


async def tailor_resume(job_description: str) -> dict:
    prompt = TAILOR_INSTRUCTIONS + json.dumps({
        "master_resume": MASTER,
        "job_description": job_description,
    }, ensure_ascii=False)
    cli_env = os.environ.copy()
    for key in ("OPENAI_API_KEY", "CODEX_API_KEY", "GOOGLE_API_KEY"):
        cli_env.pop(key, None)

    with tempfile.TemporaryDirectory(prefix="resume-tailor-") as workdir:
        schema_path = Path(workdir) / "schema.json"
        schema_path.write_text(json.dumps(TailoredResume.model_json_schema()), encoding="utf-8")
        try:
            process = await asyncio.create_subprocess_exec(
                CODEX_BIN, "--ask-for-approval", "never", "exec", "--model", CODEX_MODEL,
                "--sandbox", "read-only", "--ignore-user-config", "--ephemeral",
                "-c", 'model_reasoning_effort="medium"', "-c", 'web_search="disabled"',
                "--skip-git-repo-check", "--output-schema", str(schema_path), "-",
                stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE, cwd=workdir, env=cli_env,
            )
        except FileNotFoundError as exc:
            raise RuntimeError(
                "Codex CLI was not found. Start the app from a terminal with Codex on PATH "
                "or set RESUME_CODEX_BIN to its full path."
            ) from exc

        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(prompt.encode("utf-8")), timeout=120,
            )
        except (asyncio.TimeoutError, asyncio.CancelledError) as exc:
            if process.returncode is None:
                process.kill()
            await process.wait()
            if isinstance(exc, asyncio.CancelledError):
                raise
            raise RuntimeError(f"{CODEX_MODEL} timed out after 120 seconds.") from exc

    if process.returncode:
        diagnostic = stderr.decode("utf-8", errors="replace")
        error = next(
            (line for line in reversed(diagnostic.splitlines()) if line.lower().startswith("error:")),
            "",
        )
        raise RuntimeError(
            f"Codex could not generate a resume with {CODEX_MODEL}. "
            f"Check your ChatGPT sign-in with `codex login status`. {error[:300]}"
        )
    try:
        resume = TailoredResume.model_validate_json(stdout)
    except ValidationError as exc:
        raise RuntimeError("Codex returned an invalid resume. Please try again.") from exc
    data = resume.model_dump()
    data["skills"] = {row.category: row.skills for row in resume.skills}
    return data


async def html_to_pdf(html: str) -> bytes:
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.set_content(html, wait_until="networkidle")
        pdf = await page.pdf(format="Letter", print_background=True)
        await browser.close()
        return pdf

# ─── Routes ───────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def index():
    return UI


@app.post("/generate")
async def generate(request: Request):
    try:
        body = await request.json()
        jd = body.get("job_description", "").strip()
        if not jd:
            return JSONResponse({"detail": "Job description is required."}, status_code=400)

        # 1. Generate tailored data
        data = await tailor_resume(jd)

        # 2. Render to HTML
        html = build_resume_html(data)

        # 3. Convert to PDF
        pdf_bytes = await html_to_pdf(html)

        # 4. Save directly to tailored_resumes/ folder
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"tailored_resume_{timestamp}.pdf"
        target_path = os.path.join(OUTPUT_DIR, filename)

        with open(target_path, "wb") as f:
            f.write(pdf_bytes)

        # Also maintain a latest pointer
        latest_path = os.path.join(OUTPUT_DIR, "latest.pdf")
        with open(latest_path, "wb") as f:
            f.write(pdf_bytes)

        print(f"[Save] Saved resume to: {target_path}")

        return StreamingResponse(
            io.BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "X-Filename": filename,
                "Access-Control-Expose-Headers": "X-Filename",
            },
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse({"detail": str(e)}, status_code=500)

# ─── Entry Point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn

    def _open_browser():
        import time
        time.sleep(1.2)
        webbrowser.open("http://localhost:8000")

    threading.Thread(target=_open_browser, daemon=True).start()
    print("\n  Resume Tailor running → http://localhost:8000\n")
    print(f"  Target save directory → {OUTPUT_DIR}\n")
    uvicorn.run(app, host="localhost", port=8000, log_level="warning")
