import asyncio
import os
import json
import uuid
import re
from typing import List, Dict, Any
from models import Job, UserProfile

from job_sources.adzuna_provider import AdzunaJobProvider
from job_sources.jooble_provider import JoobleJobProvider
from job_sources.manual_import_provider import ManualImportJobProvider
from job_sources.company_careers_provider import CompanyCareersJobProvider
from ai.job_discovery_agent import evaluate_job_listing
from ai.ai_preference_parser import parse_user_instructions
from ai.resume_version_manager import ResumeVersionManager
from ai.provider_manager import ProviderManager
from ai.strict_job_validator import StrictJobValidationEngine, deduplicate_jobs, update_validation_stats
from constants import TECH_MATCH_WEIGHT, PREFERENCE_MATCH_WEIGHT, TRUST_SCORE_WEIGHT, OPPORTUNITY_SCORE_WEIGHT
import shutil
from utils import load_json_file, save_json_file


SETTINGS_FILE = "settings.json"

def get_active_providers() -> List[str]:
    # Default active sources
    active = ["company_careers", "adzuna", "jooble"]
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r") as f:
                data = json.load(f)
                # Check for toggles
                active = [p for p in active if data.get(f"source_{p}", True)]
                if data.get("source_manual_import", False):
                    active.append("manual_import")
        except Exception:
            pass
    return active

def check_salary_filter(salary_str: str, min_salary: float, currency: str, policy: str) -> tuple[bool, str]:
    sal_lower = salary_str.lower()
    
    # 1. Handle missing/undisclosed salary
    if "not specified" in sal_lower or not salary_str.strip():
        if policy == "Hide":
            return False, ""
        elif policy == "Warn":
            return True, "Salary undisclosed"
        return True, ""
        
    # 2. Parse numerical value
    sal_clean = re.sub(r'[$,₹,]', '', sal_lower).strip()
    numbers = re.findall(r'\d+(?:\.\d+)?', sal_clean)
    if not numbers:
        if policy == "Hide":
            return False, ""
        elif policy == "Warn":
            return True, "Salary undisclosed"
        return True, ""
        
    num = float(numbers[0])
    is_lpa = "lpa" in sal_lower or "lakh" in sal_lower or "l" in sal_lower or "₹" in salary_str
    is_monthly = "month" in sal_lower or "/mo" in sal_lower or "pm" in sal_lower
    
    job_lpa = 0.0
    job_usd = 0.0
    
    if is_lpa:
        job_lpa = num
        job_usd = (num * 100000.0) / 83.0
    elif is_monthly:
        if num < 100000:
            job_lpa = (num * 12) / 100000.0
            job_usd = (num * 12) / 83.0
        else:
            job_usd = num * 12
            job_lpa = (job_usd * 83.0) / 100000.0
    else:
        if num < 100.0:
            job_lpa = num
            job_usd = (num * 100000.0) / 83.0
        else:
            job_usd = num
            job_lpa = (num * 83.0) / 100000.0
            
    if currency == "INR_LPA":
        if job_lpa < min_salary:
            return False, ""
    else:
        if job_usd < min_salary:
            return False, ""
            
    return True, ""

def _load_pairwise_stats() -> dict:
    pairwise_stats = {
        "resume_company_type": {},  # (resume, company_type) -> {"applied": X, "success": Y}
        "resume_source": {},        # (resume, source) -> {"applied": X, "success": Y}
        "resume_location": {},      # (resume, location) -> {"applied": X, "success": Y}
    }
    default_queue = {
        "applications": {},
        "audit_logs": []
    }
    queue = load_json_file("application_queue.json", default_queue)

    applications = queue.get("applications", {})
    for app in applications.values():
        res_ver = app.get("resume_version", "react").lower()
        
        # Clean source
        src = app.get("source", "Search").lower()
        if "adzuna" in src:
            src = "adzuna"
        elif "jooble" in src:
            src = "jooble"
        elif "careers" in src or "local" in src or "radar" in src:
            src = "company_careers"
        elif "manual" in src:
            src = "manual_import"
        else:
            src = "generic"
            
        comp_name = app.get("company", "").lower()
        
        # Determine company_type
        is_startup = "startup" in comp_name or any(s in comp_name for s in ["riafy", "sayone", "keyval", "accubits", "entri", "carestack"])
        comp_type = "startup" if is_startup else "corporate"
        
        # Determine location
        loc = app.get("location", "remote").lower()
        is_remote = "remote" in loc or "work from home" in loc
        location_type = "remote" if is_remote else "onsite"
        
        # Success status check
        status = app.get("status", "Applied")
        success = 1 if status in ["Interviewing", "Offered"] else 0
        
        # Helper to increment stats
        def add_stat(stat_dict, key):
            if key not in stat_dict:
                stat_dict[key] = {"applied": 0, "success": 0}
            stat_dict[key]["applied"] += 1
            stat_dict[key]["success"] += success
            
        add_stat(pairwise_stats["resume_company_type"], (res_ver, comp_type))
        add_stat(pairwise_stats["resume_source"], (res_ver, src))
        add_stat(pairwise_stats["resume_location"], (res_ver, location_type))
        
    return pairwise_stats

async def generate_jobs_list(profile: UserProfile, pipeline_nodes: List[dict] = None) -> List[Job]:
    # Load pipeline nodes from file if not supplied (for background/direct callers)
    if pipeline_nodes is None:
        pipeline_data = load_json_file("pipeline.json", {"nodes": [], "edges": []})
        pipeline_nodes = pipeline_data.get("nodes", [])

    # 0. Extract Canvas configurations from nodes
    min_match_percent = 0.0
    
    # Salary Filter settings
    min_salary = 0.0
    salary_currency = "USD"
    salary_unknown_policy = "Allow"  # Allow, Warn, Hide
    
    # Scam Filter settings
    scam_mode = "balanced"  # Strict, Balanced, Off
    
    # Opportunity Ranker settings
    startup_w = "Medium"
    remote_w = "Medium"
    salary_w = "Medium"
    trust_w = "Medium"
    
    # Enabled sources toggles (from jobSources node)
    enabled_sources = None  
    
    # AI preference text override
    canvas_instructions = ""

    for node in pipeline_nodes:
        ntype = node.get("type")
        ndata = node.get("data", {})
        
        if ntype == "skillMatch":
            min_match_percent = float(ndata.get("minMatchPercent", 0.0))
            
        elif ntype == "salaryFilter":
            min_salary = float(ndata.get("minSalary", 0.0))
            salary_currency = ndata.get("currency", "USD")
            salary_unknown_policy = ndata.get("salaryUnknownPolicy", "Allow")
            
        elif ntype == "scamFilter":
            scam_mode = ndata.get("scamMode", "balanced").lower()
            
        elif ntype == "opportunityRanker":
            startup_w = ndata.get("startupWeight", "Medium")
            remote_w = ndata.get("remoteWeight", "Medium")
            salary_w = ndata.get("salaryWeight", "Medium")
            trust_w = ndata.get("trustWeight", "Medium")
            
        elif ntype == "jobSources":
            enabled_sources = []
            if ndata.get("sourceAdzuna", True):
                enabled_sources.append("adzuna")
            if ndata.get("sourceJooble", True):
                enabled_sources.append("jooble")
            if ndata.get("sourceManualImport", False):
                enabled_sources.append("manual_import")
            if ndata.get("sourceCompanyCareers", True):
                enabled_sources.append("company_careers")
                
        elif ntype == "preferenceFilter":
            canvas_instructions = ndata.get("aiInstructions", "")

    # 1. Parse user natural language instructions (canvas override has precedence)
    user_instructions = getattr(profile, "ai_instructions", "")
    if canvas_instructions.strip():
        user_instructions = canvas_instructions
        
    parsed_preferences = await parse_user_instructions(user_instructions)
    
    # Extract search criteria
    keywords = "Software Engineer"
    location_pref = "Remote"
    
    # Prefer values from pipeline trigger node if available
    for node in pipeline_nodes:
        if node.get("type") == "jobSearchTrigger":
            node_data = node.get("data", {})
            keywords = node_data.get("keywords", keywords)
            location_pref = node_data.get("location", location_pref)
            break
                
    # Otherwise, check parsed preferences roles
    if parsed_preferences.get("preferred_roles") and keywords == "Software Engineer":
        keywords = parsed_preferences["preferred_roles"][0]
        
    if profile.location and location_pref == "Remote":
        location_pref = profile.location

    # 2. Query enabled job sources in parallel
    if enabled_sources is not None:
        active_sources = enabled_sources
    else:
        active_sources = get_active_providers()
        
    providers = []
    
    if "adzuna" in active_sources:
        providers.append(AdzunaJobProvider())
    if "jooble" in active_sources:
        providers.append(JoobleJobProvider())
    if "manual_import" in active_sources:
        providers.append(ManualImportJobProvider())
    if "company_careers" in active_sources:
        providers.append(CompanyCareersJobProvider())
        
    tasks = [p.fetch_jobs(keywords, location_pref) for p in providers]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    merged_raw_jobs = []
    for res in results:
        if isinstance(res, list):
            merged_raw_jobs.extend(res)
            
    # Remove duplicates based on company & title
    unique_jobs = []
    seen = set()
    for job in merged_raw_jobs:
        key = f"{job['title'].lower()}|{job['company'].lower()}"
        if key not in seen:
            seen.add(key)
            unique_jobs.append(job)
            
    # 3. Load Career Memory queue to analyze historical outcomes
    pairwise_stats = _load_pairwise_stats()

    # 4. Analyze and score each job using AI / Local Fallback discovery agent
    scored_jobs = []
    
    for item in unique_jobs:
        # A. Apply Salary filter node configuration
        keep_salary, sal_warn = check_salary_filter(item["salary"], min_salary, salary_currency, salary_unknown_policy)
        if not keep_salary:
            continue
            
        job_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, item["title"] + item["company"]))
        
        # Instantiate base job structure
        job_obj = Job(
            id=job_id,
            title=item["title"],
            company=item["company"],
            location=item["location"],
            salary=item["salary"],
            description=item["description"],
            skills_required=item["skills_required"],
            url=item["url"],
            status="Matched"
        )
        
        # Run job discovery agent analysis (matching, scam checks, trust score, explanations, opportunity ranker weights)
        analysis = await evaluate_job_listing(job_obj, profile, parsed_preferences, startup_w, remote_w, salary_w, trust_w)
        
        # Merge analysis data
        job_obj.is_scam = analysis.get("is_scam", False)
        job_obj.scam_risk_score = analysis.get("scam_risk_score", 0)
        job_obj.scam_reason = analysis.get("scam_reason", "")
        
        # B. Apply Scam Filter mode node configuration
        if scam_mode == "off":
            job_obj.is_scam = False
            job_obj.scam_risk_score = 0
            job_obj.scam_reason = ""
        elif scam_mode == "strict" and job_obj.is_scam:
            continue  # discard suspicious job
            
        job_obj.tech_match_score = analysis.get("tech_match_score", 0.0)
        
        # C. Apply Skill matcher node threshold configuration
        if job_obj.tech_match_score < min_match_percent:
            continue  # discard low skill match job
            
        job_obj.pref_match_score = analysis.get("pref_match_score", 0.0)
        job_obj.trust_score = analysis.get("trust_score", 0.0)
        job_obj.opportunity_score = analysis.get("opportunity_score", 0.0)
        job_obj.recommendation_pros = analysis.get("recommendation_pros", [])
        job_obj.recommendation_cons = analysis.get("recommendation_cons", [])
        job_obj.ai_recommendation = analysis.get("ai_recommendation", "")
        job_obj.evaluation_mode = analysis.get("evaluation_mode", "Local Heuristics")
        
        # Append undisclosed salary warning if policy is Warn
        if sal_warn:
            job_obj.recommendation_cons.append(sal_warn)
            job_obj.trust_score = max(0, job_obj.trust_score - 10)
            
        # D. Career Memory Calculations
        # 1. Best resume version for this job
        rvm = ResumeVersionManager()
        best_res_version, _ = rvm.select_best_resume(job_obj.title, job_obj.description, job_obj.skills_required)
        best_res_version = best_res_version.lower()
        
        # 2. Source mapping
        job_src = "generic"
        url_lower = job_obj.url.lower()
        if "adzuna" in url_lower:
            job_src = "adzuna"
        elif "jooble" in url_lower:
            job_src = "jooble"
        elif "careers" in url_lower or any(s in job_obj.company.lower() for s in ["riafy", "sayone", "keyval", "accubits", "entri", "carestack"]):
            job_src = "company_careers"
            
        # 3. Company Type mapping
        job_comp_name = job_obj.company.lower()
        is_job_startup = "startup" in job_comp_name or "startup" in job_obj.description.lower() or any(s in job_comp_name for s in ["riafy", "sayone", "keyval", "accubits", "entri", "carestack"])
        job_comp_type = "startup" if is_job_startup else "corporate"
        
        # 4. Location Type mapping
        job_loc = job_obj.location.lower()
        is_job_remote = "remote" in job_loc or "remote" in job_obj.description.lower()
        job_loc_type = "remote" if is_job_remote else "onsite"
        
        total_career_adjustment = 0.0
        
        # Helper to compute adjustment for a specific dimension key & stat dictionary
        def compute_dimension_adjustment(stat_dict, pair_key, label_desc):
            if pair_key in stat_dict:
                stats = stat_dict[pair_key]
                applied = stats["applied"]
                success = stats["success"]
                if applied > 0:
                    success_rate = success / applied
                    # Confidence weighting: sample size validation
                    confidence = min(applied / 20.0, 1.0)
                    
                    if success_rate >= 0.15:
                        # High response boost (max +12)
                        raw_boost = 12.0
                        actual_boost = raw_boost * confidence
                        if actual_boost >= 0.5:
                            return actual_boost, f"Career Memory: High success with {label_desc} (+{actual_boost:.1f})"
                    elif success_rate < 0.05 and applied >= 5:
                        # Low response penalty (max -8)
                        raw_penalty = -8.0
                        actual_penalty = raw_penalty * confidence
                        if actual_penalty <= -0.5:
                            return actual_penalty, f"Career Memory: Low response for {label_desc} ({actual_penalty:.1f})"
            return 0.0, ""

        # Evaluate combinations
        adj_c, text_c = compute_dimension_adjustment(
            pairwise_stats["resume_company_type"], 
            (best_res_version, job_comp_type), 
            f"{best_res_version.capitalize()} + {job_comp_type.capitalize()}"
        )
        total_career_adjustment += adj_c
        if text_c:
            if adj_c > 0:
                job_obj.recommendation_pros.append(text_c)
            else:
                job_obj.recommendation_cons.append(text_c)
                
        adj_s, text_s = compute_dimension_adjustment(
            pairwise_stats["resume_source"], 
            (best_res_version, job_src), 
            f"{best_res_version.capitalize()} + {job_src.capitalize()}"
        )
        total_career_adjustment += adj_s
        if text_s:
            if adj_s > 0:
                job_obj.recommendation_pros.append(text_s)
            else:
                job_obj.recommendation_cons.append(text_s)
                
        adj_l, text_l = compute_dimension_adjustment(
            pairwise_stats["resume_location"], 
            (best_res_version, job_loc_type), 
            f"{best_res_version.capitalize()} + {job_loc_type.capitalize()}"
        )
        total_career_adjustment += adj_l
        if text_l:
            if adj_l > 0:
                job_obj.recommendation_pros.append(text_l)
            else:
                job_obj.recommendation_cons.append(text_l)
                
        # Cap Career Memory adjustments between -10 and +15
        total_career_adjustment = max(-10.0, min(15.0, total_career_adjustment))
        
        # Compute final composite Airohunt Score using constants.py weights
        composite_score = (
            (job_obj.tech_match_score * TECH_MATCH_WEIGHT) + 
            (job_obj.pref_match_score * PREFERENCE_MATCH_WEIGHT) + 
            (job_obj.trust_score * TRUST_SCORE_WEIGHT) + 
            (job_obj.opportunity_score * OPPORTUNITY_SCORE_WEIGHT)
        )
        # Add Career Memory dynamic boost
        composite_score += total_career_adjustment
        job_obj.match_score = round(max(0.0, min(100.0, composite_score)), 1)
        
        # Apply startup priority filter on final ranking
        is_startup_pref = "startup" in user_instructions.lower()
        is_job_startup = "startup" in item["company"].lower() or "startup" in item["description"].lower()
        if is_startup_pref and is_job_startup:
            job_obj.match_score = min(100.0, job_obj.match_score + 5)
            job_obj.recommendation_pros.append("Startup Priority Boost")
            
        scored_jobs.append(job_obj)
        
    # Deduplicate
    deduplicated_jobs, dup_removed = deduplicate_jobs(scored_jobs)
    
    # Validate
    validator = StrictJobValidationEngine(profile)
    validated_jobs = []
    for job in deduplicated_jobs:
        validated_job = validator.validate_job(job)
        validated_jobs.append(validated_job)
        
    # Update Stats
    update_validation_stats(validated_jobs, [j for j in validated_jobs if j.validation_tier != "D"], dup_removed)
    
    # Filter only displayed jobs (Tiers A, B, C)
    displayed_jobs = [j for j in validated_jobs if j.validation_tier != "D"]
    
    # Sort by overall match_score descending
    displayed_jobs.sort(key=lambda x: x.match_score, reverse=True)
    return displayed_jobs

async def scrape_more_jobs(profile: UserProfile, existing_jobs: List[dict], pipeline_nodes: List[dict] = None, override_keywords: str = None, override_location: str = None) -> List[Job]:
    if pipeline_nodes is None:
        pipeline_data = load_json_file("pipeline.json", {"nodes": [], "edges": []})
        pipeline_nodes = pipeline_data.get("nodes", [])

    # 0. Extract Canvas configurations from nodes
    min_match_percent = 0.0
    
    # Salary Filter settings
    min_salary = 0.0
    salary_currency = "USD"
    salary_unknown_policy = "Allow"  # Allow, Warn, Hide
    
    # Scam Filter settings
    scam_mode = "balanced"  # Strict, Balanced, Off
    
    # Opportunity Ranker settings
    startup_w = "Medium"
    remote_w = "Medium"
    salary_w = "Medium"
    trust_w = "Medium"
    
    # AI preference text override
    canvas_instructions = ""

    for node in pipeline_nodes:
        ntype = node.get("type")
        ndata = node.get("data", {})
        
        if ntype == "skillMatch":
            min_match_percent = float(ndata.get("minMatchPercent", 0.0))
            
        elif ntype == "salaryFilter":
            min_salary = float(ndata.get("minSalary", 0.0))
            salary_currency = ndata.get("currency", "USD")
            salary_unknown_policy = ndata.get("salaryUnknownPolicy", "Allow")
            
        elif ntype == "scamFilter":
            scam_mode = ndata.get("scamMode", "balanced").lower()
            
        elif ntype == "opportunityRanker":
            startup_w = ndata.get("startupWeight", "Medium")
            remote_w = ndata.get("remoteWeight", "Medium")
            salary_w = ndata.get("salaryWeight", "Medium")
            trust_w = ndata.get("trustWeight", "Medium")
            
        elif ntype == "preferenceFilter":
            canvas_instructions = ndata.get("aiInstructions", "")

    # 1. Parse user natural language instructions (canvas override has precedence)
    user_instructions = getattr(profile, "ai_instructions", "")
    if canvas_instructions.strip():
        user_instructions = canvas_instructions
        
    parsed_preferences = await parse_user_instructions(user_instructions)
    
    # Extract search criteria
    keywords = "Software Engineer"
    location_pref = "Remote"
    
    # Prefer values from pipeline trigger node if available
    for node in pipeline_nodes:
        if node.get("type") == "jobSearchTrigger":
            node_data = node.get("data", {})
            keywords = node_data.get("keywords", keywords)
            location_pref = node_data.get("location", location_pref)
            break
                
    # Otherwise, check parsed preferences roles
    if parsed_preferences.get("preferred_roles") and keywords == "Software Engineer":
        keywords = parsed_preferences["preferred_roles"][0]
        
    if profile.location and location_pref == "Remote":
        location_pref = profile.location

    # Apply overrides if provided
    if override_keywords and override_keywords.strip():
        keywords = override_keywords.strip()
    if override_location and override_location.strip():
        location_pref = override_location.strip()

    # 2. Build existing jobs list to exclude them
    existing_jobs_str = "\n".join([f"- {j.get('title')} at {j.get('company')}" for j in existing_jobs])

    # 3. Query LLM provider to fetch additional unique jobs
    pm = ProviderManager()
    active_provider = pm.settings.get("active_provider", "local")
    
    profile_skills = profile.skills
    profile_roles = profile.target_roles
    experience_level = profile.experience_level
    preferred_region = profile.region or profile.location or "Kerala, India"
    
    raw_jobs_list = []
    
    if active_provider and active_provider.lower() != "local":
        try:
            system_prompt = "You are a professional Job Discovery Scraper Agent."
            user_prompt = f"""
Search your database and knowledge base to fetch a list of 5-8 real-world, highly relevant active job roles for a candidate with the following details. The candidate may have an IT/tech or non-tech background, depending on their target roles and skills:
- Search Keywords: {keywords}
- Preferred Location: {location_pref} (Focus heavily on the {preferred_region} region if default or remote)
- Candidate Skills: {", ".join(profile_skills)}
- Target Roles: {", ".join(profile_roles)}
- Experience Level: {experience_level}

CRITICAL: Do NOT return any of the following jobs, as the candidate has already seen or applied to them:
{existing_jobs_str}

You MUST return a JSON list of job objects. Each object MUST have this schema:
[
  {{
    "title": "Job Title (matching candidate's target roles and field)",
    "company": "Company Name (use real active companies active in the targeted region matching the candidate's sector, different from existing ones)",
    "location": "Location (matching {preferred_region} or Remote)",
    "salary": "Salary (transparency is key, e.g. appropriate regional local currency salary standard or USD)",
    "description": "A detailed job description specifying responsibilities, skills, and evaluation style. Make it realistic and detailed (at least 3-4 sentences).",
    "skills_required": ["Skill1", "Skill2", "Skill3"],
    "url": "The direct official careers website URL of the company. It MUST be a real, working website URL of the company."
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
                
            jobs_list = json.loads(res_clean.strip())
            if isinstance(jobs_list, list):
                for job in jobs_list:
                    raw_jobs_list.append({
                        "title": job.get("title", "Software Developer"),
                        "company": job.get("company", "Tech Startup"),
                        "location": job.get("location", location_pref),
                        "salary": job.get("salary", "Not Specified"),
                        "description": job.get("description", "Software developer role."),
                        "skills_required": job.get("skills_required", [keywords]),
                        "url": job.get("url", "https://boards.greenhouse.io/careers")
                    })
        except Exception as e:
            print(f"LLM Job Discovery Scraper failed in scrape_more_jobs: {str(e)}")

    if not raw_jobs_list:
        # Local fallback generation based on candidate's skills and preferences
        fallback_roles = profile_roles if profile_roles else ["Full Stack Developer", "Software Engineer"]
        fallback_pool = []
        real_companies = [
            {"name": "SayOne Technologies", "url": "https://sayonetech.com/careers"},
            {"name": "KeyValue Systems", "url": "https://keyvalue.systems/careers"},
            {"name": "Accubits Technologies", "url": "https://accubits.com/careers"},
            {"name": "Riafy Technologies", "url": "https://riafy.me"},
            {"name": "Entri.app", "url": "https://entri.app"},
            {"name": "CareStack Systems", "url": "https://carestack.com/careers"},
            {"name": "UST Global", "url": "https://ust.com/careers"},
            {"name": "IBS Software", "url": "https://www.ibssoftware.com/careers"}
        ]
        for idx, role in enumerate(fallback_roles):
            comp_info = real_companies[idx % len(real_companies)]
            
            # Detect if tech or non-tech role
            is_tech = any(w in role.lower() for w in ["developer", "engineer", "programmer", "architect", "tech", "qa", "devops", "software", "sysadmin", "data scientist", "coder"])
            
            if is_tech:
                title = f"Associate {role}" if "associate" not in role.lower() else role
                desc = f"{comp_info['name']} is seeking an {title} to join our growing engineering department. This is a project-focused role where candidates will build and scale web services. Evaluation is strictly portfolio and task-oriented, no whiteboard DSA."
                skills = profile_skills[:3] if profile_skills else ["Python", "React", "JavaScript"]
            else:
                title = role
                desc = f"{comp_info['name']} is looking for a qualified {title} to support our business operations and growth. We are looking for candidates with strong communication, teamwork, and domain expertise. Evaluation is based on past experience, interview, and situational task."
                skills = profile_skills[:3] if profile_skills else ["Excel", "Communication", "Management"]
                
            fallback_pool.append({
                "title": title,
                "company": comp_info["name"],
                "location": f"{location_pref} (Hybrid)",
                "salary": "₹3.8 LPA - ₹5.5 LPA",
                "description": desc,
                "skills_required": skills,
                "url": comp_info["url"]
            })
        
        # Filter out existing ones
        for item in fallback_pool:
            if not any(j.get('title', '').lower() == item['title'].lower() and j.get('company', '').lower() == item['company'].lower() for j in existing_jobs):
                raw_jobs_list.append(item)

    # 4. Load Career Memory pairwise stats
    pairwise_stats = _load_pairwise_stats()

    # 5. Evaluate and score discovered jobs in parallel
    scored_jobs = []
    eval_tasks = []
    jobs_to_eval = []
    
    for item in raw_jobs_list:
        # Apply Salary filter node configuration
        keep_salary, sal_warn = check_salary_filter(item["salary"], min_salary, salary_currency, salary_unknown_policy)
        if not keep_salary:
            continue
            
        job_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, item["title"] + item["company"]))
        
        job_obj = Job(
            id=job_id,
            title=item["title"],
            company=item["company"],
            location=item["location"],
            salary=item["salary"],
            description=item["description"],
            skills_required=item["skills_required"],
            url=item["url"],
            status="Matched"
        )
        
        jobs_to_eval.append((job_obj, sal_warn, item))
        eval_tasks.append(evaluate_job_listing(job_obj, profile, parsed_preferences, startup_w, remote_w, salary_w, trust_w))
        
    eval_results = await asyncio.gather(*eval_tasks, return_exceptions=True)
    
    for (job_obj, sal_warn, raw_item), analysis in zip(jobs_to_eval, eval_results):
        if isinstance(analysis, Exception):
            print(f"Error evaluating job {job_obj.title}: {analysis}")
            continue
            
        job_obj.is_scam = analysis.get("is_scam", False)
        job_obj.scam_risk_score = analysis.get("scam_risk_score", 0)
        job_obj.scam_reason = analysis.get("scam_reason", "")
        
        # Apply Scam Filter mode node configuration
        if scam_mode == "off":
            job_obj.is_scam = False
            job_obj.scam_risk_score = 0
            job_obj.scam_reason = ""
        elif scam_mode == "strict" and job_obj.is_scam:
            continue  # discard suspicious job
            
        job_obj.tech_match_score = analysis.get("tech_match_score", 0.0)
        
        # Apply Skill matcher node threshold configuration
        if job_obj.tech_match_score < min_match_percent:
            continue  # discard low skill match job
            
        job_obj.pref_match_score = analysis.get("pref_match_score", 0.0)
        job_obj.trust_score = analysis.get("trust_score", 0.0)
        job_obj.opportunity_score = analysis.get("opportunity_score", 0.0)
        job_obj.recommendation_pros = analysis.get("recommendation_pros", [])
        job_obj.recommendation_cons = analysis.get("recommendation_cons", [])
        job_obj.ai_recommendation = analysis.get("ai_recommendation", "")
        job_obj.evaluation_mode = analysis.get("evaluation_mode", "Local Heuristics")
        
        job_obj.company_summary = analysis.get("company_summary", f"{job_obj.company} is hiring in the tech industry.")
        job_obj.tech_stack = analysis.get("tech_stack", job_obj.skills_required)
        job_obj.hiring_signals = analysis.get("hiring_signals", ["Standard Technical Review"])
        job_obj.trust_rating = analysis.get("trust_rating", "B")

        # Append undisclosed salary warning if policy is Warn
        if sal_warn:
            job_obj.recommendation_cons.append(sal_warn)
            job_obj.trust_score = max(0, job_obj.trust_score - 10)
            
        # Career Memory Calculations
        # 1. Best resume version for this job
        rvm = ResumeVersionManager()
        best_res_version, _ = rvm.select_best_resume(job_obj.title, job_obj.description, job_obj.skills_required)
        best_res_version = best_res_version.lower()
        
        # 2. Source mapping
        job_src = "generic"
        url_lower = job_obj.url.lower()
        if "adzuna" in url_lower:
            job_src = "adzuna"
        elif "jooble" in url_lower:
            job_src = "jooble"
        elif "careers" in url_lower or any(s in job_obj.company.lower() for s in ["riafy", "sayone", "keyval", "accubits", "entri", "carestack"]):
            job_src = "company_careers"
            
        # 3. Company Type mapping
        job_comp_name = job_obj.company.lower()
        is_job_startup = "startup" in job_comp_name or "startup" in job_obj.description.lower() or any(s in job_comp_name for s in ["riafy", "sayone", "keyval", "accubits", "entri", "carestack"])
        job_comp_type = "startup" if is_job_startup else "corporate"
        
        # 4. Location Type mapping
        job_loc = job_obj.location.lower()
        is_job_remote = "remote" in job_loc or "remote" in job_obj.description.lower()
        job_loc_type = "remote" if is_job_remote else "onsite"
        
        total_career_adjustment = 0.0
        
        def compute_dimension_adjustment(stat_dict, pair_key, label_desc):
            if pair_key in stat_dict:
                stats = stat_dict[pair_key]
                applied = stats["applied"]
                success = stats["success"]
                if applied > 0:
                    success_rate = success / applied
                    confidence = min(applied / 20.0, 1.0)
                    if success_rate >= 0.15:
                        raw_boost = 12.0
                        actual_boost = raw_boost * confidence
                        if actual_boost >= 0.5:
                            return actual_boost, f"Career Memory: High success with {label_desc} (+{actual_boost:.1f})"
                    elif success_rate < 0.05 and applied >= 5:
                        raw_penalty = -8.0
                        actual_penalty = raw_penalty * confidence
                        if actual_penalty <= -0.5:
                            return actual_penalty, f"Career Memory: Low response for {label_desc} ({actual_penalty:.1f})"
            return 0.0, ""

        # Evaluate combinations
        adj_c, text_c = compute_dimension_adjustment(pairwise_stats["resume_company_type"], (best_res_version, job_comp_type), f"{best_res_version.capitalize()} + {job_comp_type.capitalize()}")
        total_career_adjustment += adj_c
        if text_c:
            if adj_c > 0:
                job_obj.recommendation_pros.append(text_c)
            else:
                job_obj.recommendation_cons.append(text_c)
                
        adj_s, text_s = compute_dimension_adjustment(pairwise_stats["resume_source"], (best_res_version, job_src), f"{best_res_version.capitalize()} + {job_src.capitalize()}")
        total_career_adjustment += adj_s
        if text_s:
            if adj_s > 0:
                job_obj.recommendation_pros.append(text_s)
            else:
                job_obj.recommendation_cons.append(text_s)
                
        adj_l, text_l = compute_dimension_adjustment(pairwise_stats["resume_location"], (best_res_version, job_loc_type), f"{best_res_version.capitalize()} + {job_loc_type.capitalize()}")
        total_career_adjustment += adj_l
        if text_l:
            if adj_l > 0:
                job_obj.recommendation_pros.append(text_l)
            else:
                job_obj.recommendation_cons.append(text_l)
                
        total_career_adjustment = max(-10.0, min(15.0, total_career_adjustment))
        
        composite_score = (
            (job_obj.tech_match_score * TECH_MATCH_WEIGHT) + 
            (job_obj.pref_match_score * PREFERENCE_MATCH_WEIGHT) + 
            (job_obj.trust_score * TRUST_SCORE_WEIGHT) + 
            (job_obj.opportunity_score * OPPORTUNITY_SCORE_WEIGHT)
        )
        composite_score += total_career_adjustment
        job_obj.match_score = round(max(0.0, min(100.0, composite_score)), 1)
        
        is_startup_pref = "startup" in user_instructions.lower()
        is_job_startup = "startup" in raw_item["company"].lower() or "startup" in raw_item["description"].lower()
        if is_startup_pref and is_job_startup:
            job_obj.match_score = min(100.0, job_obj.match_score + 5)
            job_obj.recommendation_pros.append("Startup Priority Boost")
            
        scored_jobs.append(job_obj)
        
    # Deduplicate
    deduplicated_jobs, dup_removed = deduplicate_jobs(scored_jobs)
    
    # Validate
    validator = StrictJobValidationEngine(profile)
    validated_jobs = []
    for job in deduplicated_jobs:
        validated_job = validator.validate_job(job)
        validated_jobs.append(validated_job)
        
    # Update Stats
    update_validation_stats(validated_jobs, [j for j in validated_jobs if j.validation_tier != "D"], dup_removed)
    
    # Filter only displayed jobs (Tiers A, B, C)
    displayed_jobs = [j for j in validated_jobs if j.validation_tier != "D"]
    
    # Sort by overall match_score descending
    displayed_jobs.sort(key=lambda x: x.match_score, reverse=True)
    return displayed_jobs
