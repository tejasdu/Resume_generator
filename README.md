<img width="796" height="564" alt="Screenshot 2026-11-05 at 6 16 48 PM" src="https://github.com/user-attachments/assets/a788796e-52e6-449d-92b2-b56bdf941459" />

# Resume Tailor

A local automation tool that tailors a master resume for specific job descriptions and exports an ATS-optimized, single-page PDF in seconds.

## Overview

Applying to roles in volume requires tailoring skills, summary, and bullet points to match target job descriptions without losing document formatting. Resume Tailor eliminates manual editing by connecting Google Gemini to a headless Chromium rendering pipeline, guaranteeing exact typography, verified hyperlinks, and a strict single-page constraint.

## Architecture

1. **Intelligent Tailoring**: Uses Google Gemini with structured JSON output and a resilient fallback cascade (`gemini-3.5-flash`, `gemini-3-flash-preview`, `gemini-3.6-flash`, `gemini-3.5-flash-lite`) to prevent timeout and 503 errors.
2. **Boilerplate Stripping**: Automatically cleans HR disclaimer copy, benefits, and legal statements from pasted job descriptions before prompt evaluation.
3. **Deterministic PDF Export**: Renders the tailored JSON into semantic HTML/CSS and compiles a Letter-sized PDF using Playwright Chromium.
4. **Auto-Save**: Every run generates a timestamped PDF in `tailored_resumes/` and updates `tailored_resumes/latest.pdf` while simultaneously triggering a browser download.

## Requirements

- Python 3.10+
- Google Gemini API key (Google AI Studio)

## Setup

1. Clone the repository and navigate into the folder:
   ```bash
   git clone https://github.com/tejasdu/resume-generator.git
   cd resume-generator
   ```

2. Create and activate a virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   playwright install chromium
   ```

4. Create a `.env` file in the root directory:
   ```bash
   GOOGLE_API_KEY=your_gemini_api_key_here
   ```

## Usage

Start the local server:
```bash
./start.sh
```

The web interface will open automatically at `http://localhost:8000`. Paste any job description and click **Generate & Save Resume**. The tailored PDF will be generated and saved to `tailored_resumes/` within 20 seconds.
