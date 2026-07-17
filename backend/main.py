import os
import re
import json
import shutil
import tempfile
import threading
import asyncio
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
from datetime import datetime

from models import UserProfile, Job, AISettings, JobFilterState
from job_scraper import generate_jobs_list
from resume_tailor import process_resume_tailoring
from ai.provider_manager import ProviderManager
from job_sources.company_careers_provider import KERALA_STARTUPS_POOL
from ai.resume_version_manager import ResumeVersionManager
from automation.application_engine import ApplicationEngine
from ai.strict_job_validator import StrictJobValidationEngine
from geo_utils import get_standardized_city
from database import AirohuntDatabase

db = AirohuntDatabase()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Files for persistent local storage (Free local-first SaaS concept)
PROFILE_FILE = "profile.json"
JOBS_STORE_FILE = "jobs_store.json"
SETTINGS_FILE = "settings.json"
RESUME_PROFILES_FILE = "resume_profiles.json"
APPLICATION_QUEUE_FILE = "application_queue.json"
STARTUPS_STORE_FILE = "startups_store.json"

def load_application_queue() -> dict:
    default_queue = {
        "applications": {},
        "audit_logs": []
    }
    return load_json_file(APPLICATION_QUEUE_FILE, default_queue)

def save_application_queue(data: dict):
    save_json_file(APPLICATION_QUEUE_FILE, data)


# In-memory storage defaults
current_profile = UserProfile(
    name="",
    email="",
    phone="",
    location="Kerala, India",
    target_roles=[],
    skills=[],
    salary_expectation=0,
    base_resume="",
    experience_level="Fresher",
    preferred_work_mode="Any",
    region="Kerala, India",
    ai_instructions=""
)

from utils import load_json_file, save_json_file

# Load profile on startup
profile_data = load_json_file(PROFILE_FILE, current_profile.dict())
current_profile = UserProfile(**profile_data)

# Load settings on startup
current_settings = AISettings()
settings_data = load_json_file(SETTINGS_FILE, current_settings.dict())
current_settings = AISettings(**settings_data)

# Load jobs store
jobs_db = []

# Asynchronous background loop for scraping jobs
async def background_scrape_loop():
    while True:
        try:
            print("[Airohunt Background Crawler] Running periodic job crawl...")
            # Load fresh profile
            prof_data = load_json_file(PROFILE_FILE, current_profile.dict())
            prof = UserProfile(**prof_data)
            if prof.name and prof.target_roles:
                new_jobs = await generate_jobs_list(prof)
                for job in new_jobs:
                    db.save_job(job)
                print(f"[Airohunt Background Crawler] Successfully crawled and saved {len(new_jobs)} jobs.")
        except Exception as e:
            print(f"[Airohunt Background Crawler] Error during crawl: {e}")
        # Sleep for 1 hour
        await asyncio.sleep(3600)

@app.on_event("startup")
async def startup_event():
    global jobs_db
    # Migrate jobs from jobs_store.json to SQLite database if json exists
    if os.path.exists(JOBS_STORE_FILE):
        try:
            json_jobs = load_json_file(JOBS_STORE_FILE, [])
            if json_jobs:
                print(f"[Airohunt DB Migration] Migrating {len(json_jobs)} jobs to SQLite database...")
                for j_dict in json_jobs:
                    try:
                        job_obj = Job(**j_dict)
                        db.save_job(job_obj)
                    except Exception as e:
                        print(f"[Airohunt DB Migration] Failed to migrate job: {e}")
                # Rename the file to prevent re-migration
                os.rename(JOBS_STORE_FILE, f"{JOBS_STORE_FILE}.migrated")
        except Exception as e:
            print(f"[Airohunt DB Migration] Error migrating jobs_store.json: {e}")

    # Migrate application queue from application_queue.json to SQLite database if json exists
    if os.path.exists(APPLICATION_QUEUE_FILE):
        try:
            json_queue = load_json_file(APPLICATION_QUEUE_FILE, {})
            if json_queue:
                apps = json_queue.get("applications", {})
                print(f"[Airohunt DB Migration] Migrating {len(apps)} applications to SQLite database...")
                for job_id, app_data in apps.items():
                    try:
                        db.save_application(app_data)
                    except Exception as e:
                        print(f"[Airohunt DB Migration] Failed to migrate application {job_id}: {e}")
                
                logs = json_queue.get("audit_logs", [])
                print(f"[Airohunt DB Migration] Migrating {len(logs)} audit logs to SQLite database...")
                for log in logs:
                    try:
                        db.add_audit_log(log)
                    except Exception as e:
                        print(f"[Airohunt DB Migration] Failed to migrate audit log: {e}")
                # Rename the file
                os.rename(APPLICATION_QUEUE_FILE, f"{APPLICATION_QUEUE_FILE}.migrated")
        except Exception as e:
            print(f"[Airohunt DB Migration] Error migrating application_queue.json: {e}")

    # Start the background scrape worker task
    asyncio.create_task(background_scrape_loop())

# List of common keywords to check for skills auto-extraction
SKILLS_KEYWORDS = [
    "Python", "JavaScript", "TypeScript", "React", "Node.js", "Java", "C++", "C#", "Ruby",
    "SQL", "PostgreSQL", "MongoDB", "Figma", "UI/UX", "HTML", "CSS", "Tailwind CSS",
    "Git", "Docker", "AWS", "Kubernetes", "FastAPI", "Flask", "Django", "Excel",
    "Agile", "Scrum", "Machine Learning", "PyTorch", "TensorFlow", "Pandas", "ETL"
]

def extract_profile_from_text(text: str) -> dict:
    profile = {}
    
    # 1. Extract Email
    email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', text)
    if email_match:
        profile["email"] = email_match.group(0)
        
    # 2. Extract Phone Number
    phone_match = re.search(r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}', text)
    if phone_match:
        profile["phone"] = phone_match.group(0)
        
    # 3. Extract Name
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    if lines:
        first_line = lines[0]
        if "@" not in first_line and len(first_line) < 50:
            profile["name"] = first_line
            
    # 4. Extract Skills
    found_skills = []
    text_lower = text.lower()
    for skill in SKILLS_KEYWORDS:
        pattern = r'\b' + re.escape(skill.lower()) + r'\b'
        if re.search(pattern, text_lower):
            found_skills.append(skill)
            
    profile["skills"] = found_skills
    profile["base_resume"] = text
    return profile


@app.post("/api/profile/save")
async def save_profile(profile: UserProfile):
    global current_profile
    current_profile = profile
    save_json_file(PROFILE_FILE, current_profile.dict())
    return {"status": "success", "profile": current_profile}

@app.get("/api/profile")
async def get_profile():
    return current_profile

@app.post("/api/profile/upload-resume")
async def upload_resume(file: UploadFile = File(...)):
    os.makedirs("temp", exist_ok=True)
    temp_path = os.path.join("temp", file.filename)
    
    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    extracted_text = ""
    
    if file.filename.endswith(".pdf"):
        try:
            import pypdf
            reader = pypdf.PdfReader(temp_path)
            extracted_text = "\n".join([page.extract_text() for page in reader.pages])
        except ImportError:
            try:
                import PyPDF2
                reader = PyPDF2.PdfReader(temp_path)
                extracted_text = "\n".join([page.extract_text() for page in reader.pages])
            except Exception:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                raise HTTPException(status_code=400, detail="PDF parser dependencies ('pypdf' or 'PyPDF2') are missing in the Python environment. Please run 'pip install pypdf' or manually copy and paste your resume text in settings.")
        except Exception as e:
            if os.path.exists(temp_path):
                os.remove(temp_path)
            raise HTTPException(status_code=400, detail=f"Error reading PDF: {str(e)}")
    else:
        try:
            with open(temp_path, "r", encoding="utf-8") as f:
                extracted_text = f.read()
        except Exception as e:
            if os.path.exists(temp_path):
                os.remove(temp_path)
            raise HTTPException(status_code=400, detail=f"Error reading text file: {str(e)}")
            
    if os.path.exists(temp_path):
        os.remove(temp_path)
        
    if not extracted_text.strip():
        raise HTTPException(status_code=400, detail="Failed to extract text from the file.")
        
    extracted_data = extract_profile_from_text(extracted_text)
    
    global current_profile
    current_profile.name = extracted_data.get("name", current_profile.name)
    current_profile.email = extracted_data.get("email", current_profile.email)
    current_profile.phone = extracted_data.get("phone", current_profile.phone)
    current_profile.skills = list(set(current_profile.skills + extracted_data.get("skills", [])))
    current_profile.base_resume = extracted_data.get("base_resume", current_profile.base_resume)
    
    save_json_file(PROFILE_FILE, current_profile.dict())
    
    return {
        "status": "success", 
        "profile": current_profile,
        "message": "Resume uploaded successfully and skills extracted!"
    }


async def get_all_jobs() -> List[Job]:
    jobs = db.get_all_jobs()
    if not jobs:
        print("Database is empty. Scraping live jobs...")
        jobs_list = await generate_jobs_list(current_profile)
        for job in jobs_list:
            db.save_job(job)
        jobs = db.get_all_jobs()
    return jobs

@app.get("/api/jobs")
async def get_jobs():
    return await get_all_jobs()

@app.post("/api/jobs/scrape-more")
async def scrape_more_jobs_endpoint(payload: dict = None):
    payload = payload or {}
    keywords = payload.get("keywords")
    location = payload.get("location")

    existing_jobs = [{"title": j.title, "company": j.company} for j in db.get_all_jobs()]
    
    from job_scraper import scrape_more_jobs
    
    new_jobs = await scrape_more_jobs(
        current_profile, 
        existing_jobs, 
        override_keywords=keywords,
        override_location=location
    )
    
    for job in new_jobs:
        db.save_job(job)
        
    return await get_all_jobs()

@app.post("/api/jobs/update-status")
async def update_job_status(data: dict):
    job_id = data.get("job_id")
    status = data.get("status")
    
    if not job_id or not status:
        raise HTTPException(status_code=400, detail="Missing job_id or status")
        
    updated = db.update_job_status(job_id, status)
    
    if not updated:
        jobs_list = await generate_jobs_list(current_profile)
        for job in jobs_list:
            if job.id == job_id:
                job.status = status
                db.save_job(job)
                updated = True
                break
                
    if not updated:
        raise HTTPException(status_code=404, detail="Job not found")
        
    return {"status": "success", "job_id": job_id, "new_status": status}

@app.post("/api/jobs/apply")
async def apply_job(data: dict):
    job_id = data.get("job_id")
    
    if not job_id:
        raise HTTPException(status_code=400, detail="Missing job_id")
        
    target_job = db.get_job(job_id)
    if not target_job:
        jobs_list = await generate_jobs_list(current_profile)
        for j in jobs_list:
            if j.id == job_id:
                target_job = j
                break
                
    if not target_job:
        raise HTTPException(status_code=404, detail="Job not found")
        
    # 1. Select the best resume version dynamically using ResumeVersionManager
    rvm = ResumeVersionManager()
    selected_version_key, base_resume_text = rvm.select_best_resume(
        target_job.title, 
        target_job.description, 
        target_job.skills_required
    )
    
    # If no resume versions are configured or matching fails, fallback to profile base resume
    if not base_resume_text.strip():
        base_resume_text = current_profile.base_resume
        selected_version_key = "profile base"
    
    # 2. Retrieve dynamic model provider and automation mode from settings.json
    global current_settings
    settings_data = load_json_file(SETTINGS_FILE, current_settings.dict())
    current_settings = AISettings(**settings_data)
    model_provider = current_settings.active_provider or "local"
    automation_mode = current_settings.automation_mode or "Assisted Apply"
 
    # 3. Tailor the selected resume version
    score, tailored_resume = await process_resume_tailoring(
        base_resume_text,
        target_job.title,
        target_job.company,
        target_job.description,
        current_profile.skills,
        provider=model_provider
    )
    
    # 4. Prepare application payload, classifier, and script using ApplicationEngine
    payload = ApplicationEngine.prepare_application_payload(target_job, current_profile)
    
    # Determine the status to save (Assisted/Quick prepare maps to "Prepared")
    new_status = "Prepared" if automation_mode != "Disabled" else "Applied"
    
    # 5. Log and save to SQLite applications and audit_logs tables
    app_record = {
        "job_id": job_id,
        "company": target_job.company,
        "title": target_job.title,
        "status": new_status,
        "source": target_job.evaluation_mode or "Search",
        "resume_version": selected_version_key,
        "last_updated": datetime.now().isoformat(),
        "platform": payload["platform"],
        "support": payload["automation_support"]
    }
    db.save_application(app_record)
    
    log_event = {
        "timestamp": datetime.now().isoformat(),
        "job_id": job_id,
        "company": target_job.company,
        "title": target_job.title,
        "action": f"Application prepared via {automation_mode} using {selected_version_key} resume version",
        "mode": automation_mode
    }
    db.add_audit_log(log_event)
    
    # Update status and tailored resume in jobs store
    db.update_tailored_resume(job_id, new_status, tailored_resume)
    
    return {
        "status": "success",
        "job_id": job_id,
        "tailored_resume": tailored_resume,
        "match_score": score,
        "autofill_data": payload
    }

# Pipeline endpoints removed as part of canvas cleanup


@app.get("/api/validation/report")
async def get_validation_report():
    default_stats = {
        "jobs_collected": 0,
        "jobs_rejected": 0,
        "jobs_displayed": 0,
        "duplicates_removed": 0,
        "scams_blocked": 0,
        "training_institutes_blocked": 0,
        "experience_rejected": 0,
        "rejection_categories": {},
        "top_failure_reasons": []
    }
    return load_json_file("validation_stats.json", default_stats)

# ─────────────── NEW AI & SETTINGS ENDPOINTS ───────────────

@app.get("/api/settings")
async def get_settings():
    global current_settings
    settings_data = load_json_file(SETTINGS_FILE, current_settings.dict())
    current_settings = AISettings(**settings_data)
    return current_settings

@app.post("/api/settings/save")
async def save_settings(settings: AISettings):
    global current_settings
    current_settings = settings
    save_json_file(SETTINGS_FILE, current_settings.dict())
    
    return {"status": "success", "settings": current_settings}

@app.post("/api/settings/test")
async def test_settings_connection(data: dict):
    provider = data.get("provider")
    key = data.get("key", "")
    url = data.get("url", "")
    
    if not provider:
        raise HTTPException(status_code=400, detail="Missing provider")
        
    if provider != "ollama" and (not key or not key.strip()):
        return {
            "status": "failed", 
            "connected": False, 
            "reason": f"API key for {provider.upper()} is empty. Please enter an API key to test."
        }
        
    pm = ProviderManager()
    success, reason = await pm.test_connection(provider, key, url)
    return {
        "status": "success" if success else "failed", 
        "connected": success,
        "reason": reason
    }

@app.get("/api/startups/radar")
async def get_startups_radar():
    global STARTUPS_STORE_FILE
    # Load from file. If it doesn't exist, initialize with KERALA_STARTUPS_POOL and save to file.
    startups_data = load_json_file(STARTUPS_STORE_FILE, [])
    if not startups_data:
        startups_data = KERALA_STARTUPS_POOL.copy()
        save_json_file(STARTUPS_STORE_FILE, startups_data)

    # Return hiring startups list matching target roles
    user_roles_lower = [r.lower() for r in current_profile.target_roles]
    user_skills_lower = [s.lower() for s in current_profile.skills]
    
    radar_list = []
    
    for s in startups_data:
        # Check relevance
        role_rel = any(role in s["title"].lower() for role in user_roles_lower)
        skills_list = s.get("skills_required") or s.get("skills") or []
        skill_rel = any(skill.lower() in " ".join(skills_list).lower() for skill in user_skills_lower)
        
        relevance_score = 50.0
        if role_rel:
            relevance_score += 30.0
        if skill_rel:
            relevance_score += 20.0
            
        radar_list.append({
            "company": s["company"],
            "title": s["title"],
            "location": s["location"],
            "salary": s["salary"],
            "relevance": relevance_score,
            "skills": skills_list,
            "url": s["url"],
            "description": s.get("description", "")
        })
        
    # Sort by relevance
    radar_list.sort(key=lambda x: x["relevance"], reverse=True)
    return radar_list


# ─────────────── SMART DYNAMIC JOB FILTERS UTILS & ENDPOINTS ───────────────

def classify_work_mode(job: Job) -> str:
    loc_lower = job.location.lower()
    desc_lower = job.description.lower()
    if "remote" in loc_lower or "work from home" in loc_lower or "wfh" in loc_lower or "remote" in desc_lower or "work from home" in desc_lower:
        return "Remote"
    elif "hybrid" in loc_lower or "hybrid" in desc_lower:
        return "Hybrid"
    return "Onsite"

def get_experience_category(job: Job) -> str:
    validator = StrictJobValidationEngine(current_profile)
    years = validator._parse_experience(job)
    if years == 0:
        return "Fresher"
    elif years == 1:
        return "0-1 Years"
    elif years == 2:
        return "1-2 Years"
    elif years <= 5:
        return "2-5 Years"
    return "5+ Years"

def classify_company_type(job: Job) -> str:
    comp_lower = job.company.lower()
    desc_lower = job.description.lower()
    summary_lower = job.company_summary.lower() if hasattr(job, 'company_summary') else ""
    
    # Startup check
    is_startup = ("startup" in comp_lower or 
                  "startup" in desc_lower or 
                  "startup" in summary_lower or
                  any(s in comp_lower for s in ["riafy", "sayone", "keyval", "accubits", "entri", "carestack", "focaloid"]))
    if is_startup:
        return "Startup"
        
    # MNC Check
    is_mnc = ("mnc" in comp_lower or 
              "mnc" in desc_lower or 
              "multinational" in desc_lower or 
              "global" in comp_lower or
              any(s in comp_lower for s in ["google", "infosys", "tech mahindra", "nagarro", "tata", "tcs", "wipro", "cognizant", "toptal", "ust global", "ibs software", "ibs"]))
    if is_mnc:
        return "MNC"
        
    # Consultancy / Service Agency
    is_consultancy = ("consultancy" in comp_lower or "consulting" in comp_lower or "services" in comp_lower or "agency" in comp_lower or "agency" in desc_lower)
    if is_consultancy:
        return "Consultancy"
        
    # Mid-size Product
    is_product = ("product" in desc_lower or "product" in comp_lower or "product" in summary_lower)
    if is_product:
        return "Mid-size Product"
        
    return "Enterprise"

def get_job_source(job: Job) -> str:
    url = job.url.lower()
    if "greenhouse.io" in url:
        return "Greenhouse"
    elif "lever.co" in url:
        return "Lever"
    elif "ashbyhq.com" in url:
        return "Ashby"
    elif "workable.com" in url:
        return "Workable"
    elif "smartrecruiters.com" in url:
        return "SmartRecruiters"
    elif "jooble" in url:
        return "Jooble"
    elif "adzuna" in url:
        return "Adzuna"
    elif "careers" in url or any(s in job.company.lower() for s in ["riafy", "sayone", "keyval", "accubits", "entri", "carestack"]):
        return "Company Careers"
    return "Other"

def get_fresher_compatibility_score(job: Job) -> float:
    score = 0.0
    validator = StrictJobValidationEngine(current_profile)
    
    # 1. Experience Match (max 40 pts)
    years = validator._parse_experience(job)
    if years == 0:
        score += 40.0
    elif years == 1:
        score += 20.0
        
    # 2. Role Match (max 20 pts)
    title_lower = job.title.lower()
    if any(kw in title_lower for kw in ["fresher", "intern", "trainee", "junior", "associate", "entry-level"]):
        score += 20.0
    elif any(role.lower() in title_lower for role in current_profile.target_roles):
        score += 10.0
        
    # 3. Skill Match (max 20 pts)
    desc_lower = job.description.lower()
    matched_skills = []
    for skill in current_profile.skills:
        pattern = r'\b' + re.escape(skill.lower()) + r'\b'
        if re.search(pattern, desc_lower) or any(s.lower() == skill.lower() for s in job.skills_required):
            matched_skills.append(skill)
    ratio = len(matched_skills) / max(len(current_profile.skills), 1)
    if ratio >= 0.5 or len(matched_skills) >= 3:
        score += 20.0
    elif len(matched_skills) >= 1:
        score += 10.0
        
    # 4. Company Type (max 10 pts)
    comp_type = classify_company_type(job)
    if comp_type in ["Startup", "Mid-size Product"]:
        score += 10.0
        
    # 5. Hiring Style (max 10 pts)
    if any(kw in desc_lower for kw in ["project-based", "portfolio", "take-home", "coding task", "no whiteboard", "no dsa"]):
        score += 10.0
        
    return score

@app.get("/api/filter-options")
async def get_filter_options():
    jobs = await get_all_jobs()
    
    locations = set()
    for j in jobs:
        loc = j.location.lower()
        if "remote" in loc or "wfh" in loc or "work from home" in loc:
            locations.add("Remote")
            continue
            
        std_city = get_standardized_city(j.location)
        if std_city:
            locations.add(std_city)
        else:
            parts = [p.strip() for p in j.location.split(',')]
            if parts and parts[0]:
                locations.add(parts[0].title())
                
    locations = sorted(list(locations))
        
    company_types = ["Startup", "Mid-size Product", "Enterprise", "MNC", "Agency", "Consultancy"]
    experience_levels = ["Fresher", "0-1 Years", "1-2 Years", "2-5 Years", "5+ Years"]
    sources = ["Company Careers", "Greenhouse", "Lever", "Ashby", "Workable", "SmartRecruiters", "Jooble", "Adzuna", "Other"]
    
    return {
        "locations": locations,
        "company_types": company_types,
        "experience_levels": experience_levels,
        "sources": sources
    }

@app.post("/api/jobs/filter")
async def filter_jobs(filter_state: JobFilterState):
    jobs = await get_all_jobs()
    filtered = []
    
    stats_file = "filter_usage_stats.json"
    stats = load_json_file(stats_file, {
        "locations": {},
        "work_modes": {},
        "company_types": {},
        "experience_levels": {},
        "tiers": {},
        "sources": {},
        "min_salary_clicks": 0,
        "posted_within_days_clicks": 0,
        "fresher_compatibility_clicks": 0
    })
    
    def inc_stat(category, values):
        if not values:
            return
        if category not in stats:
            stats[category] = {}
        for val in values:
            stats[category][val] = stats[category].get(val, 0) + 1
            
    inc_stat("locations", filter_state.locations)
    inc_stat("work_modes", filter_state.work_modes)
    inc_stat("company_types", filter_state.company_types)
    inc_stat("experience_levels", filter_state.experience_levels)
    inc_stat("tiers", filter_state.tiers)
    inc_stat("sources", filter_state.sources)
    if filter_state.min_salary is not None:
        stats["min_salary_clicks"] = stats.get("min_salary_clicks", 0) + 1
    if filter_state.posted_within_days is not None:
        stats["posted_within_days_clicks"] = stats.get("posted_within_days_clicks", 0) + 1
    if filter_state.fresher_compatibility:
        stats["fresher_compatibility_clicks"] = stats.get("fresher_compatibility_clicks", 0) + 1
        
    save_json_file(stats_file, stats)
    
    for j in jobs:
        if filter_state.locations:
            loc_match = False
            for target_loc in filter_state.locations:
                if target_loc.lower() == "remote" and ("remote" in j.location.lower() or "wfh" in j.location.lower() or "work from home" in j.location.lower()):
                    loc_match = True
                    break
                elif target_loc.lower() in j.location.lower():
                    loc_match = True
                    break
            if not loc_match:
                continue
                
        if filter_state.work_modes:
            mode = classify_work_mode(j)
            if mode not in filter_state.work_modes:
                continue
                
        if filter_state.experience_levels:
            exp_cat = get_experience_category(j)
            if exp_cat not in filter_state.experience_levels:
                continue
                
        if filter_state.company_types:
            comp_type = classify_company_type(j)
            if comp_type not in filter_state.company_types:
                continue
                
        if filter_state.tiers:
            if j.validation_tier not in filter_state.tiers:
                continue
                
        if filter_state.sources:
            src = get_job_source(j)
            if src not in filter_state.sources:
                continue
                
        if filter_state.min_salary is not None:
            sal_str = j.salary.lower()
            sal_val = 0.0
            if "not specified" not in sal_str and sal_str.strip():
                numbers = [float(n) for n in re.findall(r'\d+(?:\.\d+)?', sal_str.replace(',', ''))]
                if numbers:
                    val = numbers[0]
                    is_lpa = "lpa" in sal_str or "lakh" in sal_str or "l" in sal_str or "₹" in j.salary
                    is_monthly = "month" in sal_str or "/mo" in sal_str or "pm" in sal_str
                    if is_lpa:
                        sal_val = val
                    elif is_monthly:
                        sal_val = (val * 12) / 100000.0
                    else:
                        if val > 1000:
                            sal_val = (val * 83.0) / 100000.0
                        else:
                            sal_val = val
            if sal_val < filter_state.min_salary:
                continue
                
        if filter_state.posted_within_days is not None:
            posted_date_str = j.posted_at or datetime.now().isoformat()
            try:
                posted_date = datetime.fromisoformat(posted_date_str)
                delta = datetime.now() - posted_date
                if delta.days > filter_state.posted_within_days:
                    continue
            except Exception:
                pass
                
        if filter_state.fresher_compatibility and filter_state.fresher_compatibility != "All":
            comp_score = get_fresher_compatibility_score(j)
            threshold = 0.0
            if filter_state.fresher_compatibility == "90%+":
                threshold = 90.0
            elif filter_state.fresher_compatibility == "75%+":
                threshold = 75.0
            elif filter_state.fresher_compatibility == "50%+":
                threshold = 50.0
            if comp_score < threshold:
                continue
                
        filtered.append(j)
        
    return filtered


@app.post("/api/startups/radar/scrape-more")
async def scrape_more_startups_endpoint():
    global STARTUPS_STORE_FILE
    # Load existing startups
    startups_data = load_json_file(STARTUPS_STORE_FILE, [])
    if not startups_data:
        startups_data = KERALA_STARTUPS_POOL.copy()

    # Query LLM (or fallback) to fetch additional unique startups
    pm = ProviderManager()
    active_provider = pm.settings.get("active_provider", "local")
    
    profile_skills = current_profile.skills
    profile_roles = current_profile.target_roles
    experience_level = current_profile.experience_level
    location_pref = current_profile.location or "Remote"
    preferred_region = current_profile.region or current_profile.location or "Kerala, India"
    
    existing_companies_str = "\n".join([f"- {s.get('company')} ({s.get('title')})" for s in startups_data])
    
    new_startups = []
    
    if active_provider and active_provider.lower() != "local":
        try:
            system_prompt = "You are a professional Job Discovery Scraper Agent specializing in Startups."
            user_prompt = f"""
Search your database and knowledge base to fetch a list of 4-6 real-world, active companies/startups hiring in the targeted region or globally matching the candidate's profile and industry sector:
- Candidate Skills: {", ".join(profile_skills)}
- Target Roles: {", ".join(profile_roles)}
- Experience Level: {experience_level}
- Location Preference: {location_pref} (Focus heavily on the {preferred_region} region if default or remote)

CRITICAL: Do NOT return any of the following startups/roles that the candidate already has in their list:
{existing_companies_str}

You MUST return a JSON list of startup hiring objects. Each object MUST have this schema:
[
  {{
    "title": "Hiring Job Title (matching candidate's target roles and field)",
    "company": "Company Name (use real active companies/startups hiring in this region or remote matching candidate's sector, different from existing ones)",
    "location": "Location (matching {preferred_region} or Remote)",
    "salary": "Salary (e.g. appropriate local currency standard or USD)",
    "description": "A brief description of what the startup does and the hiring role details.",
    "skills_required": ["Skill1", "Skill2", "Skill3"],
    "url": "The direct official careers website URL of the company. It MUST be a real, working website URL."
  }}
]

Return ONLY the raw JSON list. Do not write any explanation, introduction, markdown blocks, or code fences.
"""
            res = await pm.call_llm(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                response_format_json=True
            )
            
            res_clean = res.strip()
            if res_clean.startswith("```json"):
                res_clean = res_clean[7:]
            if res_clean.endswith("```"):
                res_clean = res_clean[:-3]
                
            startups_list = json.loads(res_clean.strip())
            if isinstance(startups_list, list):
                for s in startups_list:
                    new_startups.append({
                        "title": s.get("title", "Software Engineer"),
                        "company": s.get("company", "Tech Startup"),
                        "location": s.get("location", location_pref),
                        "salary": s.get("salary", "Not Specified"),
                        "description": s.get("description", "Hiring role."),
                        "skills_required": s.get("skills_required") or s.get("skills") or ["Software"],
                        "url": s.get("url", "https://wellfound.com")
                    })
        except Exception as e:
            print(f"LLM Startup Scraper failed, falling back: {str(e)}")

    if not new_startups:
        # Fallback local pool generation of new startups based on user's target roles
        fallback_roles = profile_roles if profile_roles else ["Associate Project Lead", "Representative", "Consultant"]
        fallback_startups_pool = [
            {
                "company": "UST Global",
                "url": "https://ust.com/careers"
            },
            {
                "company": "IBS Software",
                "url": "https://www.ibssoftware.com/careers"
            },
            {
                "company": "Focaloid Technologies",
                "url": "https://focaloid.com/careers"
            }
        ]
        
        for idx, role in enumerate(fallback_roles[:3]):
            comp_info = fallback_startups_pool[idx % len(fallback_startups_pool)]
            
            # Detect if tech or non-tech role
            is_tech = any(w in role.lower() for w in ["developer", "engineer", "programmer", "architect", "tech", "qa", "devops", "software", "sysadmin", "data scientist", "coder"])
            
            if is_tech:
                title = f"Junior {role}" if "junior" not in role.lower() else role
                desc = f"{comp_info['company']} is seeking a {title}. Evaluated via a practical coding task."
                skills = profile_skills[:3] if profile_skills else ["Selenium", "JavaScript", "Python"]
            else:
                title = role
                desc = f"{comp_info['company']} is hiring a {title} to lead client relations and operational campaigns."
                skills = profile_skills[:3] if profile_skills else ["Excel", "Communication", "Management"]
                
            new_startups.append({
                "title": title,
                "company": comp_info["company"],
                "location": f"{location_pref} (Hybrid)",
                "salary": "₹4.0 LPA - ₹6.0 LPA",
                "description": desc,
                "skills_required": skills,
                "url": comp_info["url"]
            })

    # Append to existing
    for item in new_startups:
        if not any(s.get('company', '').lower() == item['company'].lower() and s.get('title', '').lower() == item['title'].lower() for s in startups_data):
            startups_data.append(item)
            
    save_json_file(STARTUPS_STORE_FILE, startups_data)
    
    # Return updated sorted list
    return await get_startups_radar()


# Backwards compatibility endpoint removed

# ─────────────── RESUME VERSION ENDPOINTS ───────────────
@app.get("/api/profile/resumes")
async def get_resume_profiles():
    rvm = ResumeVersionManager()
    return rvm.load_profiles()

@app.post("/api/profile/resumes")
async def save_resume_profiles(data: dict):
    rvm = ResumeVersionManager()
    rvm.save_profiles(data)
    return {"status": "success", "message": "Resume versions saved successfully."}

# ─────────────── AUTOMATION QUEUE & METRICS ENDPOINTS ───────────────
@app.get("/api/automation/queue")
async def get_queue():
    return load_application_queue()

@app.post("/api/automation/queue")
async def update_queue(data: dict):
    queue = load_application_queue()
    app_id = data.get("job_id")
    status = data.get("status")
    
    if not app_id or not status:
        raise HTTPException(status_code=400, detail="Missing job_id or status")
        
    global jobs_db
    jobs_db = load_json_file(JOBS_STORE_FILE, [])
    found_job = None
    for j in jobs_db:
        if j["id"] == app_id:
            j["status"] = status
            found_job = j
            break
            
    if found_job:
        save_json_file(JOBS_STORE_FILE, jobs_db)

    app_entry = queue["applications"].get(app_id, {})
    old_status = app_entry.get("status", "Unknown")
    
    # Update properties in application entry
    app_entry["status"] = status
    app_entry["last_updated"] = datetime.now().isoformat()
    if found_job:
        app_entry["company"] = found_job.get("company", app_entry.get("company", "Unknown"))
        app_entry["title"] = found_job.get("title", app_entry.get("title", "Unknown"))
        
    log_event = {
        "timestamp": datetime.now().isoformat(),
        "job_id": app_id,
        "company": app_entry.get("company", "Unknown"),
        "title": app_entry.get("title", "Unknown"),
        "action": f"Status updated from {old_status} to {status}",
        "mode": app_entry.get("mode", "Manual")
    }
    queue["applications"][app_id] = app_entry
    queue["audit_logs"].append(log_event)
    save_application_queue(queue)
    
    return {"status": "success", "queue": queue}

@app.get("/api/automation/metrics")
async def get_metrics():
    app_data = db.get_applications()
    apps = app_data.get("applications", {})
    
    total_submitted = sum(1 for app in apps.values() if app.get("status") in ["Applied", "Interviewing", "Offered", "Rejected"])
    total_interviews = sum(1 for app in apps.values() if app.get("status") in ["Interviewing", "Offered"])
    total_offers = sum(1 for app in apps.values() if app.get("status") == "Offered")
    
    interview_rate = 0.0
    if total_submitted > 0:
        interview_rate = round((total_interviews / total_submitted) * 100, 1)
        
    offer_rate = 0.0
    if total_submitted > 0:
        offer_rate = round((total_offers / total_submitted) * 100, 1)

    sources_count = {}
    sources_hires = {}
    resumes_count = {}
    resumes_hires = {}
    
    for app in apps.values():
        src = app.get("source", "Search")
        ver = app.get("resume_version", "react")
        stat = app.get("status")
        
        sources_count[src] = sources_count.get(src, 0) + 1
        resumes_count[ver] = resumes_count.get(ver, 0) + 1
        
        if stat in ["Interviewing", "Offered"]:
            sources_hires[src] = sources_hires.get(src, 0) + 1
            resumes_hires[ver] = resumes_hires.get(ver, 0) + 1
            
    best_source = "N/A"
    best_src_rate = -1.0
    for src, count in sources_count.items():
        hires = sources_hires.get(src, 0)
        rate = (hires / count) * 100
        if rate > best_src_rate:
            best_src_rate = rate
            best_source = f"{src} ({rate:.0f}% Resp)"
            
    best_resume = "N/A"
    best_res_rate = -1.0
    for ver, count in resumes_count.items():
        hires = resumes_hires.get(ver, 0)
        rate = (hires / count) * 100
        if rate > best_res_rate:
            best_res_rate = rate
            best_resume = f"{ver.capitalize()} Resume ({rate:.0f}% Resp)"
            
    return {
        "total_submitted": total_submitted,
        "interview_rate": interview_rate,
        "offer_rate": offer_rate,
        "best_source": best_source,
        "best_resume": best_resume,
        "audit_logs": app_data.get("audit_logs", [])[-20:] # Last 20 logs
    }

@app.get("/api/validation/report")
async def get_validation_report():
    default_stats = {
        "jobs_collected": 0,
        "jobs_rejected": 0,
        "jobs_displayed": 0,
        "duplicates_removed": 0,
        "scams_blocked": 0,
        "training_institutes_blocked": 0,
        "experience_rejected": 0,
        "rejection_categories": {},
        "top_failure_reasons": []
    }
    stats = default_stats
    stats_file = "validation_stats.json"
    if os.path.exists(stats_file):
        try:
            with open(stats_file, "r", encoding="utf-8") as f:
                stats = json.load(f)
        except Exception:
            pass
            
    history = []
    history_file = "validation_history.json"
    if os.path.exists(history_file):
        try:
            with open(history_file, "r", encoding="utf-8") as f:
                history = json.load(f)
        except Exception:
            pass
            
    return {
        "stats": stats,
        "history": history
    }

@app.post("/api/data/reset")
async def reset_all_data():
    files_to_delete = [
        PROFILE_FILE, 
        JOBS_STORE_FILE, 
        SETTINGS_FILE, 
        RESUME_PROFILES_FILE, 
        APPLICATION_QUEUE_FILE,
        STARTUPS_STORE_FILE,
        "filter_usage_stats.json",
        "validation_stats.json",
        "validation_history.json",
        "cache_metadata.json",
        os.path.join(os.path.dirname(__file__), "airohunt.db")
    ]
    for filename in files_to_delete:
        if os.path.exists(filename):
            try:
                os.remove(filename)
            except Exception as e:
                print(f"Error deleting file {filename}: {str(e)}")
                
    # Re-initialize in-memory states to defaults
    global current_profile, current_settings, jobs_db
    current_profile = UserProfile(
        name="",
        email="",
        phone="",
        location="Kerala, India",
        target_roles=[],
        skills=[],
        salary_expectation=0,
        base_resume="",
        experience_level="Fresher",
        preferred_work_mode="Any",
        region="Kerala, India",
        ai_instructions=""
    )
    current_settings = AISettings()
    jobs_db = []
    return {"status": "success", "message": "All local data reset successfully."}