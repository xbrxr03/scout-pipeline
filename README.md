# SCOUT Pipeline

AI-powered SWE internship auto-apply pipeline using browser-use + kimi-k2.6.

## How It Works

1. **Search** — Navigates Indeed live for SWE/internship jobs in Toronto/GTA
2. **Filter** — Smart filtering: only "Apply with Indeed" jobs, correct location, correct role
3. **Apply** — Clicks Apply, fills forms with real experience, uploads resume, solves reCAPTCHA
4. **Stop** — Hard stop after ONE application. No runaway applying.

## Proven Results

- ✅ Applied to Human Computer Lab — Intern, Software/ML Engineer, Toronto ON (Hybrid)
- ✅ Smart filtering: skipped Amazon (no Indeed Apply), Oncoustics (company site only)
- ✅ Tailored "Why join us" answer referencing HCL's mission
- ✅ reCAPTCHA solving (crosswalks, traffic lights, cars)
- ✅ Hard stop safeguard — no rogue applying

## Setup

```bash
# Prerequisites
pip install browser-use langchain-ollama

# Set Ollama API key
export OLLAMA_API_KEY="your-key"

# Run
python3 scout_apply.py --category internship    # Search + apply to ONE job
python3 scout_apply.py --category swe            # SWE roles
python3 scout_apply.py --discover               # Just find jobs, don't apply
python3 scout_apply.py --dry-run                # Show what would happen
```

## Config

- Resume: `Abrar-Habib-Resume-SWE.pdf` (upload to Indeed profile)
- Chrome profile: `~/.browser-use-profiles/job-hunter/` (log into Indeed once)
- Smart answers: Edit `SMART_ANSWERS` dict in `scout_apply.py`

## Architecture

- **browser-use v0.13.7** — Browser automation with vision support
- **kimi-k2.6:cloud via Ollama** — LLM with vision for CAPTCHA solving
- **Persistent Chrome profile** — Reuses Indeed login session
- **SCOUT DB** — SQLite tracking at `~/.applypilot/scout_jobs.db`
