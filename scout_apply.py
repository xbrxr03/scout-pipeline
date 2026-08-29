"""
SCOUT Auto-Apply Pipeline v3 — SWE & Internships
==================================================
browser-use + kimi-k2.6 cloud for SWE/internship job applications.

WORKFLOW:
1. SEARCH: browser-use navigates Indeed, searches for SWE internships
2. FILTER: Checks location (Toronto/GTA/Remote) and role (SWE/intern)
3. CLICK: Opens the first active job listing
4. APPLY: Clicks "Apply with Indeed", uploads resume, fills forms, solves CAPTCHA
5. STOP: Hard stop after ONE application. No runaway applying.

SAFEGUARDS:
- STOPS after ONE application
- LOCATION FILTER: Toronto/GTA/Remote/Canada ONLY
- ROLE FILTER: SWE, internship, new grad, junior dev ONLY
- UPLOADS resume (never "apply without resume")
- SMART ANSWERS for SWE/internship forms
- LOGS everything to SCOUT DB
- SKIPS expired/inactive job listings

Usage:
    python3 scout_apply.py                           # Search + apply to ONE SWE internship
    python3 scout_apply.py --category swe             # Search + apply to ONE SWE job
    python3 scout_apply.py --category internship      # Search + apply to ONE internship
    python3 scout_apply.py --discover                 # Just find jobs, don't apply
    python3 scout_apply.py --dry-run                  # Show what would happen, don't apply
"""

import asyncio
import os
import sys
import sqlite3
from datetime import datetime
from pathlib import Path

# ── Config ──────────────────────────────────────────────────────────────────

OLLAMA_API_KEY = os.environ.get("OLLAMA_API_KEY", "")
OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434/v1")
PROFILE_DIR = str(Path.home() / ".browser-use-profiles" / "job-hunter")
SCOUT_DB = str(Path.home() / ".applypilot" / "scout_jobs.db")
RESUMES_DIR = str(Path.home() / "Projects" / "auto-apply" / "resumes")

# Acceptable locations
ACCEPTABLE_LOCATIONS = [
    "toronto", "scarborough", "north york", "etobicoke", "mississauga",
    "brampton", "markham", "vaughan", "richmond hill", "concord",
    "pickering", "ajax", "whitby", "gta", "ontario", "on", "canada",
    "remote", "hybrid",
]

# Reject these locations
REJECT_LOCATIONS = [
    "montreal", "vancouver", "calgary", "surrey", "edmonton", "ottawa",
    "winnipeg", "halifax", "london", "kitchener", "waterloo",
    "amsterdam", "usa", "united states", "new york", "san francisco",
    "seattle", "austin", "boston", "chicago", "london, uk",
]

# SWE/internship keywords (for role validation in the task prompt)
SWE_KEYWORDS = [
    "software engineer", "software developer", "full stack", "fullstack",
    "frontend", "frontend developer", "backend", "backend developer",
    "web developer", "python developer", "javascript developer",
    "react developer", "node developer", "devops", "sre",
    "platform engineer", "application developer", "data engineer",
    "technology analyst", "ml engineer", "ai engineer",
]

INTERNSHIP_KEYWORDS = [
    "intern", "internship", "co-op", "co-op", "new grad", "junior developer",
    "entry level", "associate developer", "software intern",
    "engineering intern", "developer intern", "summer 2026",
    "fall 2026", "winter 2026", "spring 2026", "student",
]

# ── Smart Answers ───────────────────────────────────────────────────────────

SMART_ANSWERS = {
    "swe": {
        "years_experience": "2",
        "experience_context": "Software Developer at VertexGrid Technologies — built and maintained REST APIs in Python/Django handling 10K+ requests/day, designed PostgreSQL schemas, set up CI/CD with GitHub Actions to AWS EC2, Docker packaging. Data Operations Specialist at LionSton Group — automated data validation with Python cutting manual entry by 60%, maintained SQL pipelines. IT Support Technician at Go-Co — set up and maintained network infrastructure for 50+ users, managed Linux servers, wrote Bash automation scripts.",
        "tech_stack": "Python, TypeScript, JavaScript, React, Next.js, Node.js, Express, FastAPI, Django, PostgreSQL, SQLite, MongoDB, ChromaDB, Docker, Nginx, AWS (EC2, S3), Git, Linux",
        "education": "Software Engineering Technology — AI, Centennial College (in progress). DeepLearning.AI Prompt Engineering for Developers. AWS Generative AI Essentials (in progress).",
        "availability": "Available immediately for full-time roles. Open to remote, hybrid, or onsite in Toronto/GTA.",
        "work_authorization": "Canadian citizen, authorized to work in Canada",
        "salary_expectation": "Open to competitive market rate for the role",
        "resume_file": "Abrar-Habib-Resume-SWE.pdf",
    },
    "internship": {
        "years_experience": "2 (including professional SWE experience)",
        "experience_context": "Software Developer at VertexGrid Technologies — built and maintained REST APIs in Python/Django handling 10K+ requests/day, designed PostgreSQL schemas, set up CI/CD with GitHub Actions to AWS EC2, Docker packaging. Data Operations Specialist at LionSton Group — automated data validation with Python cutting manual entry by 60%, maintained SQL pipelines. IT Support Technician at Go-Co — set up and maintained network infrastructure for 50+ users. Built ClawOS — AI agent system with 53 GitHub stars, runs entirely locally with no cloud APIs.",
        "tech_stack": "Python, TypeScript, JavaScript, React, Next.js, Node.js, Express, FastAPI, Django, PostgreSQL, SQLite, MongoDB, ChromaDB, Docker, Nginx, AWS (EC2, S3), Git, Linux",
        "education": "Software Engineering Technology — AI, Centennial College (in progress). DeepLearning.AI Prompt Engineering for Developers. AWS Generative AI Essentials (in progress).",
        "availability": "Summer 2026 (May–August) or Fall 2026 (September–December) for full-time internship/co-op. Available immediately for part-time.",
        "work_authorization": "Canadian citizen, authorized to work in Canada",
        "internship_term": "Summer 2026 (May–August) or Fall 2026 (September–December)",
        "gpa": "Available upon request",
        "salary_expectation": "Open to competitive intern compensation",
        "resume_file": "Abrar-Habib-Resume-SWE.pdf",
    },
}

# ── Search URLs ─────────────────────────────────────────────────────────────

INDEED_SEARCH_URLS = {
    "internship": [
        "https://ca.indeed.com/jobs?q=software+engineering+internship&l=Scarborough%2C+ON&radius=50&sort=date",
        "https://ca.indeed.com/jobs?q=software+developer+intern+summer+2026&l=Toronto%2C+ON&radius=50&sort=date",
        "https://ca.indeed.com/jobs?q=developer+co-op+2026&l=Toronto%2C+ON&radius=50&sort=date",
    ],
    "swe": [
        "https://ca.indeed.com/jobs?q=software+engineer&l=Scarborough%2C+ON&radius=50&sort=date",
        "https://ca.indeed.com/jobs?q=python+developer&l=Toronto%2C+ON&radius=50&sort=date",
        "https://ca.indeed.com/jobs?q=full+stack+developer+junior&l=Toronto%2C+ON&radius=50&sort=date",
    ],
}


# ── Live Search + Apply ─────────────────────────────────────────────────────

async def search_and_apply(category: str = "internship", dry_run: bool = False):
    """
    Search Indeed LIVE, find an active SWE/internship job, apply to ONE.
    
    This replaces the stale-URL approach. The agent:
    1. Navigates to Indeed search results
    2. Finds active job listings (not expired)
    3. Clicks into a job that matches location + role
    4. Applies using "Apply with Indeed"
    5. STOPS after one submission
    """
    from browser_use.agent.service import Agent
    from browser_use.browser.profile import BrowserProfile
    from browser_use.llm.openai.chat import ChatOpenAI
    
    answers = SMART_ANSWERS.get(category, SMART_ANSWERS["internship"])
    resume_path = os.path.join(RESUMES_DIR, answers["resume_file"])
    
    if not os.path.exists(resume_path):
        print(f"❌ Resume not found: {resume_path}")
        return False
    
    search_urls = INDEED_SEARCH_URLS.get(category, INDEED_SEARCH_URLS["internship"])
    first_url = search_urls[0]
    
    # Build role keywords string for the prompt
    if category == "internship":
        role_desc = "software engineering internship, software developer intern, co-op, summer 2026, fall 2026, junior developer, entry-level developer"
    else:
        role_desc = "software engineer, software developer, full-stack developer, python developer, react developer, backend developer"
    
    task = f"""You are helping Abrar Habib apply for ONE SWE/internship job on Indeed.

CRITICAL RULES — VIOLATION OF ANY RULE MEANS FAILURE:
1. You will apply to ONLY ONE job and then STOP completely.
2. NEVER navigate to other job listings after submitting an application.
3. NEVER apply to more than one job, even if you see other listings.
4. When you see "Your application was submitted" or "Application submitted" or similar confirmation, IMMEDIATELY report "APPLICATION_SUBMITTED" and STOP all actions.
5. If a job is EXPIRED or has no "Apply" button, go BACK to search results and try the NEXT listing. Do NOT give up after one expired job.
6. If the job is NOT in Toronto, GTA, Ontario, or Remote — go BACK and try the next listing.
7. If the job is NOT a {role_desc} role — go BACK and try the next listing.

STEP 1: SEARCH
Navigate to this Indeed search URL: {first_url}
Look at the job search results on the page.

STEP 2: FIND A VALID JOB
Look through the job listings on the search results page. Find one that:
- Is in Toronto, Scarborough, GTA, Ontario, or Remote/Canada
- Is a {role_desc} role
- Is NOT expired (no "expired" label)
- Has an "Apply" or "Apply now" button visible

STEP 3: CLICK INTO THE JOB
Click on a valid job listing to open its details page.

STEP 4: VERIFY THE JOB
On the job detail page, verify:
- Location is in Toronto/GTA/Ontario/Canada or Remote
- Role matches {role_desc}
- The job is NOT expired
- There is an "Apply with Indeed" or "Apply now" button

If any check fails, go BACK to search results and try the next listing.

STEP 5: APPLY
Click "Apply with Indeed" or "Apply now".
When given the option to upload a resume or "Apply without a resume", ALWAYS choose to UPLOAD the resume. The resume file is at: {resume_path}
Do NOT select "Apply without a resume" or "I don't have a resume".

FILL FORM FIELDS using these answers:
- First Name: Abrar
- Last Name: Habib
- Email: abrar04h@gmail.com
- Phone: 647-522-9553
- Location: Scarborough, ON, Canada
- Years of experience: {answers["years_experience"]}
- Experience details: {answers["experience_context"]}
- Tech stack / Skills: {answers["tech_stack"]}
- Education: {answers["education"]}
- Availability: {answers["availability"]}
- Work authorization: {answers["work_authorization"]}
- Salary expectation: {answers["salary_expectation"]}"""

    if category == "internship":
        task += f"""
- Internship term: {answers["internship_term"]}
- GPA: {answers["gpa"]}"""

    task += """
- GitHub: github.com/xbrxr03
- LinkedIn: linkedin.com/in/xbrxr03

If you encounter a reCAPTCHA or image challenge, try to solve it.

STOP CONDITION: After submitting ONE application, report "APPLICATION_SUBMITTED" and STOP.
Do NOT apply to any other jobs. Do NOT browse other listings. Do NOT click on "Similar jobs" or "Recommended jobs".
STOP after ONE application."""

    llm = ChatOpenAI(
        model="kimi-k2.6:cloud",
        base_url=OLLAMA_BASE_URL,
        api_key=OLLAMA_API_KEY,
    )
    
    agent = Agent(
        task=task,
        llm=llm,
        browser_profile=BrowserProfile(headless=False, user_data_dir=PROFILE_DIR),
        max_actions_per_step=5,
        use_vision=True,
        max_failures=15,
    )
    
    print(f"🚀 Starting live search + apply for category: {category}")
    print(f"📄 Resume: {answers['resume_file']}")
    print(f"🔍 Search URL: {first_url}")
    if dry_run:
        print("🏃 DRY RUN — would apply but not executing")
        return True
    
    try:
        result = await agent.run()
        result_text = str(result)
        
        submitted = "APPLICATION_SUBMITTED" in result_text or "application was submitted" in result_text.lower()
        location_rejected = "LOCATION_REJECTED" in result_text
        role_rejected = "ROLE_REJECTED" in result_text
        
        status = "location_rejected" if location_rejected else "role_rejected" if role_rejected else "applied" if submitted else "attempted"
        
        log_application(url=first_url, category=category, status=status, result=result_text[:2000], source="indeed_live_search")
        
        if submitted:
            print("✅ APPLICATION SUBMITTED SUCCESSFULLY")
            print("🛑 STOPPING — will NOT apply to more jobs")
        elif location_rejected:
            print("🚫 LOCATION REJECTED — no suitable jobs found in Toronto/GTA")
        elif role_rejected:
            print("🚫 ROLE REJECTED — no SWE/internship jobs found")
        else:
            print("⚠️  Application status unclear")
            print(f"Result snippet: {result_text[:500]}")
        
        return submitted
        
    except Exception as e:
        print(f"❌ Error: {e}")
        log_application(url=first_url, category=category, status="error", result=str(e)[:1000], source="indeed_live_search")
        return False


# ── Discovery Only ────────────────────────────────────────────────────────────

async def discover_jobs(category: str = "internship", max_jobs: int = 20):
    """Just find jobs, don't apply. Uses browser-use to search Indeed live."""
    from browser_use.agent.service import Agent
    from browser_use.browser.profile import BrowserProfile
    from browser_use.llm.openai.chat import ChatOpenAI
    
    search_urls = INDEED_SEARCH_URLS.get(category, INDEED_SEARCH_URLS["internship"])
    first_url = search_urls[0]
    
    if category == "internship":
        role_desc = "software engineering internship, software developer intern, co-op, summer 2026, fall 2026"
    else:
        role_desc = "software engineer, software developer, full-stack developer, python developer"
    
    task = f"""You are searching Indeed for job listings. DO NOT apply to any job.

Navigate to: {first_url}

Look at the job search results. For each listing, extract:
- Job title
- Company name
- Location
- Whether it looks like an active listing (not expired)
- Whether it matches: {role_desc}
- Whether the location is in Toronto, GTA, Ontario, or Remote

List all matching jobs with their details. Do NOT click on any job. Do NOT apply to anything.
Just read the search results page and report what you find."""

    llm = ChatOpenAI(
        model="kimi-k2.6:cloud",
        base_url=OLLAMA_BASE_URL,
        api_key=OLLAMA_API_KEY,
    )
    
    agent = Agent(
        task=task,
        llm=llm,
        browser_profile=BrowserProfile(headless=False, user_data_dir=PROFILE_DIR),
        max_actions_per_step=5,
        use_vision=True,
        max_failures=10,
    )
    
    print(f"🔍 Discovering {category} jobs on Indeed...")
    result = await agent.run()
    print(f"\n📋 Results:\n{result}")
    return result


# ── SCOUT DB ─────────────────────────────────────────────────────────────────

def log_application(url: str, category: str, status: str, result: str, source: str = "indeed"):
    """Log application to SCOUT database"""
    os.makedirs(os.path.dirname(SCOUT_DB), exist_ok=True)
    conn = sqlite3.connect(SCOUT_DB)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS swe_applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            url TEXT,
            category TEXT,
            status TEXT,
            source TEXT,
            result TEXT
        )
    """)
    conn.execute(
        "INSERT INTO swe_applications (date, url, category, status, source, result) VALUES (?, ?, ?, ?, ?, ?)",
        (datetime.now().isoformat(), url, category, status, source, result)
    )
    conn.commit()
    conn.close()
    print(f"📝 Logged: {status} | {category} | {source} | {url[:60]}")


# ── Main ─────────────────────────────────────────────────────────────────────

async def main():
    import argparse
    parser = argparse.ArgumentParser(description="SCOUT SWE/Internship Auto-Apply Pipeline")
    parser.add_argument("--category", choices=["swe", "internship"], default="internship")
    parser.add_argument("--discover", action="store_true", help="Just find jobs, don't apply")
    parser.add_argument("--dry-run", action="store_true", help="Show what would happen without applying")
    args = parser.parse_args()
    
    # Load API key from .env if not set
    global OLLAMA_API_KEY
    if not OLLAMA_API_KEY:
        env_path = os.path.expanduser("~/.hermes/.env")
        if os.path.exists(env_path):
            with open(env_path) as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("OLLAMA_API_KEY="):
                        OLLAMA_API_KEY = line.split("=", 1)[1].strip()
                        os.environ["OLLAMA_API_KEY"] = OLLAMA_API_KEY
    
    if args.discover:
        await discover_jobs(category=args.category)
    else:
        await search_and_apply(category=args.category, dry_run=args.dry_run)

if __name__ == "__main__":
    asyncio.run(main())