import os
import re
import json
import shutil
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
from datetime import datetime

from models import UserProfile, Job, Pipeline, AISettings
from job_scraper import generate_jobs_list
from resume_tailor import process_resume_tailoring
from ai.provider_manager import ProviderManager
from job_sources.company_careers_provider import KERALA_STARTUPS_POOL
from ai.resume_version_manager import ResumeVersionManager
from automation.application_engine import ApplicationEngine

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
    location="Remote",
    target_roles=[],
    skills=[],
    salary_expectation=0,
    base_resume="",
    experience_level="Fresher",
    preferred_work_mode="Remote",
    region="Kerala",
    ai_instructions=""
)

# Initialize storage files if they don't exist
def load_json_file(filename, default):
    if os.path.exists(filename):
        try:
            with open(filename, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"JSON Corruption detected in {filename}: {str(e)}")
            try:
                backup_name = f"{filename}.corrupted"
                shutil.copy(filename, backup_name)
                print(f"Backed up corrupted file to {backup_name}")
                os.remove(filename)
            except Exception as copy_err:
                print(f"Failed to backup corrupted file {filename}: {str(copy_err)}")
    return default

def save_json_file(filename, data):
    with open(filename, "w") as f:
        json.dump(data, f, indent=4)

# Load profile on startup
profile_data = load_json_file(PROFILE_FILE, current_profile.dict())
current_profile = UserProfile(**profile_data)

# Load settings on startup
current_settings = AISettings()
settings_data = load_json_file(SETTINGS_FILE, current_settings.dict())
current_settings = AISettings(**settings_data)

# Sync loaded settings to process environment variables immediately on startup
os.environ["AI_PROVIDER"] = current_settings.active_provider
os.environ["OPENAI_API_KEY"] = current_settings.openai_api_key
os.environ["GROQ_API_KEY"] = current_settings.groq_api_key
os.environ["GEMINI_API_KEY"] = current_settings.gemini_api_key
os.environ["OLLAMA_URL"] = current_settings.ollama_url

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
                extracted_text = f"[Resume File Name: {file.filename}]\n\nWarning: Please install 'pypdf' library in python environment to enable automatic PDF parsing. Running in fallback mode."
        except Exception as e:
            extracted_text = f"Error reading PDF: {str(e)}"
    else:
        try:
            with open(temp_path, "r", encoding="utf-8") as f:
                extracted_text = f.read()
        except Exception as e:
            extracted_text = f"Error reading text file: {str(e)}"
            
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


@app.get("/api/jobs")
async def get_jobs():
    pipeline = load_json_file(PIPELINE_FILE, {"nodes": [], "edges": []})
    jobs_list = await generate_jobs_list(current_profile, pipeline.get("nodes", []))
    
    global jobs_db
    jobs_db = load_json_file(JOBS_STORE_FILE, [])
    
    jobs_list_dict = {j.id: j for j in jobs_list}
    
    for db_job_dict in jobs_db:
        jid = db_job_dict.get("id")
        if not jid:
            continue
        if jid in jobs_list_dict:
            jobs_list_dict[jid].status = db_job_dict.get("status", "Matched")
            jobs_list_dict[jid].tailored_resume = db_job_dict.get("tailored_resume", "")
        else:
            try:
                extra_job = Job(**db_job_dict)
                jobs_list_dict[jid] = extra_job
            except Exception as e:
                print(f"Error parsing job from db: {e}")
                
    final_list = list(jobs_list_dict.values())
    final_list.sort(key=lambda x: x.match_score, reverse=True)
    return final_list

@app.post("/api/jobs/scrape-more")
async def scrape_more_jobs_endpoint():
    pipeline = load_json_file(PIPELINE_FILE, {"nodes": [], "edges": []})
    
    global jobs_db
    jobs_db = load_json_file(JOBS_STORE_FILE, [])
    
    existing_jobs = [{"title": j.get("title", ""), "company": j.get("company", "")} for j in jobs_db]
    
    from job_scraper import scrape_more_jobs
    
    new_jobs = await scrape_more_jobs(current_profile, existing_jobs, pipeline.get("nodes", []))
    
    for job in new_jobs:
        if not any(j["id"] == job.id for j in jobs_db):
            jobs_db.append(job.dict())
            
    save_json_file(JOBS_STORE_FILE, jobs_db)
    
    return await get_jobs()

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
    
    # Refresh settings in environment or in active clients
    os.environ["AI_PROVIDER"] = settings.active_provider
    os.environ["OPENAI_API_KEY"] = settings.openai_api_key
    os.environ["GROQ_API_KEY"] = settings.groq_api_key
    os.environ["GEMINI_API_KEY"] = settings.gemini_api_key
    os.environ["OLLAMA_URL"] = settings.ollama_url
    
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
    # Return hiring startups list matching target roles
    user_roles_lower = [r.lower() for r in current_profile.target_roles]
    user_skills_lower = [s.lower() for s in current_profile.skills]
    
    radar_list = []
    
    for s in KERALA_STARTUPS_POOL:
        # Check relevance
        role_rel = any(role in s["title"].lower() for role in user_roles_lower)
        skill_rel = any(skill.lower() in " ".join(s["skills_required"]).lower() for skill in user_skills_lower)
        
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
            "skills": s["skills_required"],
            "url": s["url"]
        })
        
    # Sort by relevance
    radar_list.sort(key=lambda x: x["relevance"], reverse=True)
    return radar_list


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
        "validation_stats.json",
        "validation_history.json"
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
        location="Remote",
        target_roles=[],
        skills=[],
        salary_expectation=0,
        base_resume="",
        experience_level="Fresher",
        preferred_work_mode="Remote",
        region="Kerala",
        ai_instructions=""
    )
    current_settings = AISettings()
    jobs_db = []
    
    # Reset env keys
    for key in ["AI_PROVIDER", "OPENAI_API_KEY", "GROQ_API_KEY", "GEMINI_API_KEY", "OLLAMA_URL"]:
        if key in os.environ:
            del os.environ[key]
            
    return {"status": "success", "message": "All local data reset successfully."}