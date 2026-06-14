import os
import re
import json
import shutil
import tempfile
import threading
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
from datetime import datetime

from models import UserProfile, Job, Pipeline, AISettings, JobFilterState
from job_scraper import generate_jobs_list
from resume_tailor import process_resume_tailoring
from ai.provider_manager import ProviderManager
from job_sources.company_careers_provider import KERALA_STARTUPS_POOL
from ai.resume_version_manager import ResumeVersionManager
from automation.application_engine import ApplicationEngine
from ai.strict_job_validator import StrictJobValidationEngine

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
PIPELINE_FILE = "pipeline.json"
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
jobs_db = load_json_file(JOBS_STORE_FILE, [])

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
    global jobs_db
    jobs_db = load_json_file(JOBS_STORE_FILE, [])
    
    cache_meta = load_json_file("cache_metadata.json", {})
    last_scraped_str = cache_meta.get("last_scraped", "")
    
    needs_scrape = False
    if not jobs_db:
        needs_scrape = True
    elif last_scraped_str:
        try:
            last_scraped = datetime.fromisoformat(last_scraped_str)
            if (datetime.now() - last_scraped).total_seconds() > 3600:
                needs_scrape = True
        except Exception:
            needs_scrape = True
    else:
        needs_scrape = True
        
    if needs_scrape:
        print("Cache expired or empty. Scraping live jobs...")
        pipeline = load_json_file(PIPELINE_FILE, {"nodes": [], "edges": []})
        jobs_list = await generate_jobs_list(current_profile, pipeline.get("nodes", []))
        
        jobs_list_dict = {j.id: j for j in jobs_list}
        for db_job_dict in jobs_db:
            jid = db_job_dict.get("id")
            if not jid:
                continue
            if jid in jobs_list_dict:
                jobs_list_dict[jid].status = db_job_dict.get("status", "Matched")
                jobs_list_dict[jid].tailored_resume = db_job_dict.get("tailored_resume", "")
                if "posted_at" in db_job_dict:
                    jobs_list_dict[jid].posted_at = db_job_dict["posted_at"]
            else:
                try:
                    extra_job = Job(**db_job_dict)
                    jobs_list_dict[jid] = extra_job
                except Exception as e:
                    print(f"Error parsing job from db: {e}")
                    
        final_list = list(jobs_list_dict.values())
        final_list.sort(key=lambda x: x.match_score, reverse=True)
        
        # Save cache
        jobs_db = [j.dict() for j in final_list]
        save_json_file(JOBS_STORE_FILE, jobs_db)
        save_json_file("cache_metadata.json", {"last_scraped": datetime.now().isoformat()})
        return final_list
    else:
        parsed_list = []
        for db_job_dict in jobs_db:
            try:
                parsed_list.append(Job(**db_job_dict))
            except Exception as e:
                print(f"Error parsing job from db: {e}")
        parsed_list.sort(key=lambda x: x.match_score, reverse=True)
        return parsed_list

@app.get("/api/jobs")
async def get_jobs():
    return await get_all_jobs()

@app.post("/api/jobs/scrape-more")
async def scrape_more_jobs_endpoint(payload: dict = None):
    payload = payload or {}
    keywords = payload.get("keywords")
    location = payload.get("location")

    pipeline = load_json_file(PIPELINE_FILE, {"nodes": [], "edges": []})
    
    global jobs_db
    jobs_db = load_json_file(JOBS_STORE_FILE, [])
    
    existing_jobs = [{"title": j.get("title", ""), "company": j.get("company", "")} for j in jobs_db]
    
    from job_scraper import scrape_more_jobs
    
    new_jobs = await scrape_more_jobs(
        current_profile, 
        existing_jobs, 
        pipeline.get("nodes", []),
        override_keywords=keywords,
        override_location=location
    )
    
    for job in new_jobs:
        if not any(j["id"] == job.id for j in jobs_db):
            jobs_db.append(job.dict())
            
    save_json_file(JOBS_STORE_FILE, jobs_db)
    save_json_file("cache_metadata.json", {"last_scraped": datetime.now().isoformat()})
    
    return await get_all_jobs()

@app.post("/api/jobs/update-status")
async def update_job_status(data: dict):
    job_id = data.get("job_id")
    status = data.get("status")
    
    if not job_id or not status:
        raise HTTPException(status_code=400, detail="Missing job_id or status")
        
    global jobs_db
    jobs_db = load_json_file(JOBS_STORE_FILE, [])
    
    found = False
    for job in jobs_db:
        if job["id"] == job_id:
            job["status"] = status
            found = True
            break
            
    if not found:
        jobs_list = await generate_jobs_list(current_profile)
        for job in jobs_list:
            if job.id == job_id:
                job.status = status
                jobs_db.append(job.dict())
                found = True
                break
                
    if not found:
        raise HTTPException(status_code=404, detail="Job not found")
        
    save_json_file(JOBS_STORE_FILE, jobs_db)
    return {"status": "success", "job_id": job_id, "new_status": status}

@app.post("/api/jobs/apply")
async def apply_job(data: dict):
    job_id = data.get("job_id")
    
    if not job_id:
        raise HTTPException(status_code=400, detail="Missing job_id")
        
    jobs_list = await generate_jobs_list(current_profile)
    target_job = None
    for j in jobs_list:
        if j.id == job_id:
            target_job = j
            break
            
    if not target_job:
        local_db = load_json_file(JOBS_STORE_FILE, [])
        for j_dict in local_db:
            if j_dict["id"] == job_id:
                target_job = Job(**j_dict)
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
    
    # 2. Retrieve dynamic model provider and automation mode from pipeline.json
    model_provider = "local"
    pipeline = load_json_file(PIPELINE_FILE, {"nodes": [], "edges": []})
    automation_mode = "Assisted Apply" # Default
    for node in pipeline.get("nodes", []):
        if node.get("type") == "resumeTailor":
            model_provider = node.get("data", {}).get("modelType", "local")
        elif node.get("type") == "appSubmit":
            automation_mode = node.get("data", {}).get("automationMode", "Assisted Apply")

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
    
    # 5. Log and save to Application Queue json database
    queue = load_application_queue()
    queue["applications"][job_id] = {
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
    
    log_event = {
        "timestamp": datetime.now().isoformat(),
        "job_id": job_id,
        "company": target_job.company,
        "title": target_job.title,
        "action": f"Application prepared via {automation_mode} using {selected_version_key} resume version",
        "mode": automation_mode
    }
    queue["audit_logs"].append(log_event)
    save_application_queue(queue)
    
    # Update in jobs store
    global jobs_db
    jobs_db = load_json_file(JOBS_STORE_FILE, [])
    found = False
    for j in jobs_db:
        if j["id"] == job_id:
            j["status"] = new_status
            j["tailored_resume"] = tailored_resume
            found = True
            break
    if not found:
        target_job.status = new_status
        target_job.tailored_resume = tailored_resume
        jobs_db.append(target_job.dict())
    save_json_file(JOBS_STORE_FILE, jobs_db)
    
    return {
        "status": "success",
        "job_id": job_id,
        "tailored_resume": tailored_resume,
        "match_score": score,
        "autofill_data": payload
    }

@app.post("/api/pipeline/save")
async def save_pipeline(pipeline: Pipeline):
    save_json_file(PIPELINE_FILE, pipeline.dict())
    return {"status": "success", "pipeline": pipeline}

@app.get("/api/pipeline/load")
async def load_pipeline():
    pipeline = load_json_file(PIPELINE_FILE, {"nodes": [], "edges": []})
    return pipeline


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
        if "remote" in loc:
            locations.add("Remote")
        if "kochi" in loc or "cochin" in loc:
            locations.add("Kochi")
        if "trivandrum" in loc or "thiruvananthapuram" in loc:
            locations.add("Trivandrum")
        if "kozhikode" in loc or "calicut" in loc:
            locations.add("Kozhikode")
        if "bangalore" in loc or "bengaluru" in loc:
            locations.add("Bangalore")
        if "hyderabad" in loc:
            locations.add("Hyderabad")
        if "chennai" in loc:
            locations.add("Chennai")
        if "pune" in loc:
            locations.add("Pune")
        if "mumbai" in loc:
            locations.add("Mumbai")
        if "delhi" in loc or "ncr" in loc:
            locations.add("Delhi")
            
    if not locations:
        locations = list(set(j.location for j in jobs if j.location))
    else:
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
    
    existing_companies_str = "\n".join([f"- {s.get('company')} ({s.get('title')})" for s in startups_data])
    
    new_startups = []
    
    if active_provider and active_provider.lower() != "local":
        try:
            system_prompt = "You are a professional Job Discovery Scraper Agent specializing in Startups."
            user_prompt = f"""
Search your database and knowledge base to fetch a list of 4-6 real-world, active companies/startups hiring in India (especially Kochi/Trivandrum/Bangalore/Remote) matching the candidate's profile and industry sector:
- Candidate Skills: {", ".join(profile_skills)}
- Target Roles: {", ".join(profile_roles)}
- Experience Level: {experience_level}
- Location Preference: {location_pref} (Focus heavily on Kerala, India region if default or remote)

CRITICAL: Do NOT return any of the following startups/roles that the candidate already has in their list:
{existing_companies_str}

You MUST return a JSON list of startup hiring objects. Each object MUST have this schema:
[
  {{
    "title": "Hiring Job Title (matching candidate's target roles and field)",
    "company": "Company Name (use real companies/startups active in India/Remote matching the candidate's sector, e.g. UST Global, CareStack, Accubits, Riafy, SayOne, Entri, KeyValue, or others)",
    "location": "Location (e.g. Kochi, Kerala, India or Remote)",
    "salary": "Salary (e.g. ₹4.0 LPA - ₹6.0 LPA or $50,000 - $70,000)",
    "description": "A brief description of what the startup does and the hiring role details.",
    "skills_required": ["Skill1", "Skill2", "Skill3"],
    "url": "The direct official careers website URL of the company (e.g., https://companyname.com/careers or similar official company website). It MUST be a real, working website URL."
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


# Backwards compatibility endpoint
@app.post("/pipelines/parse")
async def parse_pipeline(data: dict):
    nodes = data.get("nodes", [])
    edges = data.get("edges", [])
    return {
        "num_nodes": len(nodes),
        "num_edges": len(edges),
        "is_dag": True
    }

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
    queue = load_application_queue()
    apps = queue.get("applications", {})
    
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
        "audit_logs": queue.get("audit_logs", [])[-20:] # Last 20 logs
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
        PIPELINE_FILE, 
        JOBS_STORE_FILE, 
        SETTINGS_FILE, 
        RESUME_PROFILES_FILE, 
        APPLICATION_QUEUE_FILE,
        STARTUPS_STORE_FILE,
        "filter_usage_stats.json",
        "validation_stats.json",
        "validation_history.json",
        "cache_metadata.json"
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