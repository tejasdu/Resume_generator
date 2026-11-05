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
import re
import datetime
import threading
import webbrowser

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse
from google import genai
from google.genai import types
from dotenv import load_dotenv

# ─── Config ───────────────────────────────────────────────────────────────────

load_dotenv()
_client = genai.Client(api_key=os.environ.get("GOOGLE_API_KEY", ""))

# Resilient model fallback cascade (ordered by stability and speed)
FALLBACK_MODELS = [
    "gemini-3.5-flash",
    "gemini-3-flash-preview",
    "gemini-3.6-flash",
    "gemini-3.5-flash-lite",
]

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

# ─── Gemini System Prompt ─────────────────────────────────────────────────────

SYSTEM_PROMPT = f"""You are an elite resume writer and ATS optimization specialist. \
You write resumes that sound like a confident, articulate human wrote them — \
not AI-generated and not robotic.

TASK: Tailor the candidate's resume for the given job description.

RULES:
1. Weave specific keywords, language, and terminology from the JD naturally into the content — never keyword-stuffed.
2. Sound human and genuine — vary sentence structure, avoid stiff corporate buzzwords.
3. Keep ALL quantified achievements (numbers, percentages, counts) intact.
4. Lead each bullet with the most relevant impact for THIS role.
5. Keep the EXACT same number of bullet points per job as the master.
6. Summary: 2-3 sentences max, tailored to the role, human-sounding, no first-person pronouns. \
   Choose and adapt the best summary variant from the master.
7. Skills: Select the 4 most relevant skill categories for this role and reorder so the most \
   ATS-critical ones for this role come first. For hardware/embedded roles, include the hardware \
   category. Always output exactly 4 skill rows.
8. Experience: Select the 3-4 MOST RELEVANT jobs for this role. For each selected job, pick the \
   best-fitting bullet variants from the pool.
9. Projects: Select the 2-3 most relevant projects for this role and rewrite bullets to surface \
   the most relevant aspects.
10. NEVER fabricate experience, tools, or achievements that are not in the master knowledge base.
11. Output ONLY valid JSON — no markdown fences, no commentary, just the JSON object.

LOCKED — DO NOT CHANGE:
- Name / contact: Tejas Dumpeta | +1 (734)-489-4824 | tejasd2022@gmail.com | LinkedIn | GitHub | Portfolio
- Education: University of Michigan - Ann Arbor | B.S in Computer Science | Aug 2022 – May 2026
- Coursework: AI, UI/UX Design, Databases, Data Structures, Computer Networks, Computer Organization

MASTER KNOWLEDGE BASE:
{json.dumps(MASTER, indent=2)}"""

# ─── Helper: Clean Job Description ────────────────────────────────────────────

def clean_jd(jd: str) -> str:
    """Strip extraneous boilerplate (benefits, legal disclaimers, EEO) to keep prompt crisp and fast."""
    cleaned = jd.strip()
    boilerplate_patterns = [
        r"(?i)\b(equal opportunity employer|eeo statement|benefits and perks|what we offer|our benefits|compensation & benefits|salary range|affirmative action|accommodations)\b.*"
    ]
    for pat in boilerplate_patterns:
        cleaned = re.split(pat, cleaned, maxsplit=1)[0].strip()

    # Cap at 7,000 characters to prevent prompt bloat while preserving all requirements
    if len(cleaned) > 7000:
        cleaned = cleaned[:7000]
    return cleaned

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
  <h1>Resume Tailor <span class="badge">Fast Tier</span></h1>
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
  }catch(e){status('Error: '+e.message,'err')}
  finally{btn.disabled=false;btn.textContent='⚡\u00a0 Generate & Save Resume'}
}
function status(msg,cls=''){
  const el=document.getElementById('st');el.innerHTML=msg;el.className='st '+(cls||'');
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
        bullets = "".join(f"<li>{b}</li>" for b in job.get("bullets", []))
        exp_html += f"""
<div class="job">
  <div class="row">
    <div><span class="b">{job.get('company','')}</span> | <span class="i">{job.get('title','')}</span> | {job.get('location','')}</div>
    <div class="date">{job.get('dates','')}</div>
  </div>
  <ul>{bullets}</ul>
</div>"""

    # Projects
    proj_html = ""
    for proj in data.get("projects", []):
        bullets = "".join(f"<li>{b}</li>" for b in proj.get("bullets", []))
        link = f'&nbsp;&nbsp;<a href="#">{proj["link"]}</a>' if proj.get("link") else ""
        proj_html += f"""
<div class="project">
  <div class="ph"><span class="b">{proj.get('name','')}</span>: <span class="i">{proj.get('tech','')}</span>{link}</div>
  <ul>{bullets}</ul>
</div>"""

    # Skills rows — format keys nicely
    skill_rows = ""
    for label, value in data.get("skills", {}).items():
        display = label.replace("_", " ").title().replace("And", "&")
        skill_rows += f'<div class="sk"><span class="b">{display}:</span> {value}</div>\n'

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

<div class="summary">{data.get('summary','')}</div>

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

# ─── Core: Resilient Gemini Caller ───────────────────────────────────────────

async def call_gemini(job_description: str) -> dict:
    cleaned_jd = clean_jd(job_description)
    prompt = f"""Tailor my resume for the job description below. Follow all rules.

JOB DESCRIPTION:
{cleaned_jd}

Return ONLY a JSON object with this exact shape:
{{
  "summary": "...",
  "skills": {{
    "languages": "...",
    "frameworks_libraries": "...",
    "systems_platforms": "...",
    "client_product": "..."
  }},
  "experience": [
    {{"company":"...","title":"...","location":"...","dates":"...","bullets":["...","..."]}}
  ],
  "projects": [
    {{"name":"...","tech":"...","link":"...","bullets":["...","..."]}}
  ]
}}"""

    last_error = None
    for model_name in FALLBACK_MODELS:
        try:
            print(f"[Gemini] Requesting tailored resume via {model_name}...")
            response = await asyncio.wait_for(
                _client.aio.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=SYSTEM_PROMPT,
                        response_mime_type="application/json",
                        temperature=0.6,
                    ),
                ),
                timeout=45.0,
            )
            raw = response.text.strip()
            # Clean possible markdown wrapping if any
            if raw.startswith("```"):
                raw = re.sub(r"^```(?:json)?\n?", "", raw)
                raw = re.sub(r"\n?```$", "", raw)
            data = json.loads(raw)
            print(f"[Gemini] Successfully generated via {model_name}!")
            return data
        except Exception as e:
            print(f"[Gemini] {model_name} failed: {type(e).__name__} ({str(e)[:70]}). Trying fallback...")
            last_error = e

    raise RuntimeError(f"All available AI models encountered temporary spikes. Last error: {last_error}")


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
        data = await call_gemini(jd)

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
