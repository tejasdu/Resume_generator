<img width="796" height="564" alt="Screenshot 2026-11-05 at 6 16 48 PM" src="https://github.com/user-attachments/assets/a788796e-52e6-449d-92b2-b56bdf941459" />

# Resume Tailor

A local app that tailors a master resume to a job description and exports a Letter-sized PDF.

## Setup

Use Python 3.10+ and a recent Codex CLI signed in to your ChatGPT account. On macOS the app uses the CLI bundled with ChatGPT when available. Otherwise it uses `codex` on PATH. Set `RESUME_CODEX_BIN` in `.env` to override the executable path.

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
playwright install chromium
codex login status
```

If the CLI is signed out, run `codex login` and choose ChatGPT sign-in. If you use the bundled CLI and `codex` is unavailable on PATH, use `/Applications/ChatGPT.app/Contents/Resources/codex-cli/bin/codex` for these commands.

## Usage

Run `./start.sh` or open `ResumeTailor.command`. Paste a job description and click **Generate & Save Resume**. The app downloads the PDF, saves a timestamped copy in `tailored_resumes/`, and updates `tailored_resumes/latest.pdf`.

The model defaults to GPT‑6.1 Sol through your signed-in Codex session. You can set `RESUME_MODEL` in `.env` to another model available to that session. Generation uses your ChatGPT plan's Codex allowance. The model receives the job description and the master resume data in `app.py`. Playwright renders the structured response locally.
