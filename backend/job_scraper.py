import asyncio
import os
import json
import uuid
import re
import httpx
from html.parser import HTMLParser
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

QUERY_EXPANSION_MAP = {
    "react": ["React Developer", "Frontend Engineer", "React JS Developer", "MERN Stack Developer"],
    "frontend": ["Frontend Engineer", "Frontend Developer", "UI Developer", "React Developer", "Javascript Developer"],
    "backend": ["Backend Engineer", "Backend Developer", "Software Engineer (Backend)", "Python Developer", "Node.js Developer"],
    "python": ["Python Developer", "Backend Developer", "Python Engineer", "Software Engineer (Python)"],
    "full stack": ["Full Stack Developer", "Full Stack Engineer", "MERN Developer", "Software Engineer (Full Stack)"],
    "software engineer": ["Software Engineer", "Software Developer", "Associate Software Engineer", "Junior Developer"],
    "developer": ["Software Developer", "Software Engineer", "Developer"],
    "ui": ["UI/UX Designer", "Product Designer", "UI Developer", "Figma Designer"],
    "ux": ["UI/UX Designer", "Product Designer", "User Experience Researcher"],
    "design": ["Graphic Designer", "UI/UX Designer", "Creative Designer"],
    "marketing": ["Marketing Specialist", "Social Media Manager", "Digital Marketing Executive", "SEO Specialist"],
    "hr": ["HR Associate", "Recruiter", "Human Resources Manager", "Talent Acquisition Specialist"],
    "finance": ["Finance Executive", "Accountant", "Financial Analyst"]
}

def expand_search_query(query: str) -> List[str]:
    q_clean = query.strip().lower()
    expanded = []
    
    for key, values in QUERY_EXPANSION_MAP.items():
        if key in q_clean:
            for val in values:
                if val not in expanded:
                    expanded.append(val)
                    
    if not expanded:
        expanded = [query.strip()]
    return expanded

class HTMLTextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.reset()
        self.convert_charrefs = True
        self.text_parts = []
        self.ignore_tags = {"script", "style", "head", "nav", "footer", "noscript", "iframe", "header"}
        self.current_stack = []

    def handle_starttag(self, tag, attrs):
        self.current_stack.append(tag.lower())

    def handle_endtag(self, tag):
        if self.current_stack:
            self.current_stack.pop()

    def handle_data(self, data):
        if any(tag in self.ignore_tags for tag in self.current_stack):
            return
        cleaned = data.strip()
        if cleaned:
            self.text_parts.append(cleaned)

    def get_text(self):
        return "\n".join(self.text_parts)

def extract_clean_text_from_html(html: str) -> str:
    parser = HTMLTextExtractor()
    try:
        parser.feed(html)
        text = parser.get_text()
        text = re.sub(r'\n+', '\n', text)
        text = re.sub(r' +', ' ', text)
        return text.strip()
    except Exception:
        clean = re.sub(r'<script.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
        clean = re.sub(r'<style.*?</style>', '', clean, flags=re.DOTALL | re.IGNORECASE)
        clean = re.sub(r'<.*?>', ' ', clean, flags=re.DOTALL)
        return "\n".join([line.strip() for line in clean.split("\n") if line.strip()])

async def hydrate_job_description(url: str, current_snippet: str) -> str:
    if not url or "adzuna.com" in url or "jooble.org" in url or "google.com" in url:
        return current_snippet
        
    if len(current_snippet) > 600:
        return current_snippet
        
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5"
    }
    
    try:
        async with httpx.AsyncClient(follow_redirects=True, verify=False) as client:
            response = await client.get(url, headers=headers, timeout=4.0)
            if response.status_code == 200:
                html_text = response.text
                clean_text = extract_clean_text_from_html(html_text)
                if len(clean_text) > len(current_snippet) + 100:
                    return clean_text[:12000]
    except Exception as e:
        print(f"Failed to hydrate job description from {url}: {e}")
        
    return current_snippet

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
        
    # Expand keywords using synonym mapping
    expanded_keywords = expand_search_query(keywords)
    
    tasks = []
    for kw in expanded_keywords:
        for p in providers:
            tasks.append(p.fetch_jobs(kw, location_pref))
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    merged_raw_jobs = []
    for res in results:
        if isinstance(res, list):
            merged_raw_jobs.extend(res)
            
    def get_raw_source_rank(url: str) -> int:
        url_lower = url.lower()
        if any(k in url_lower for k in ["greenhouse.io", "lever.co", "ashbyhq.com", "workable.com"]):
            return 4
        if "careers" in url_lower:
            return 3
        if "jooble" in url_lower or "adzuna" in url_lower:
            return 1
        return 2

    # Sort raw jobs so direct careers URLs are prioritized during deduplication
    merged_raw_jobs.sort(key=lambda x: get_raw_source_rank(x.get("url", "")), reverse=True)
            
    # Remove duplicates based on company & title
    unique_jobs = []
    seen = set()
    for job in merged_raw_jobs:
        key = (job.get("title", "").strip().lower(), job.get("company", "").strip().lower())
        if key not in seen:
            seen.add(key)
            unique_jobs.append(job)
            
    # Asynchronously hydrate job description snippets concurrently (max 5 parallel requests)
    sem = asyncio.Semaphore(5)
    async def hydrate_task(job_dict):
        async with sem:
            hydrated_desc = await hydrate_job_description(job_dict.get("url", ""), job_dict.get("description", ""))
            job_dict["description"] = hydrated_desc
            
    hydration_tasks = [hydrate_task(job) for job in unique_jobs]
    await asyncio.gather(*hydration_tasks, return_exceptions=True)
            
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
    # Create a copy of the profile to modify for target roles/skills validation if we have search overrides
    eval_profile = UserProfile(**profile.dict())
    if override_keywords and override_keywords.strip():
        eval_profile.target_roles = [override_keywords.strip()]
        eval_profile.skills = [override_keywords.strip()]

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
        
    if eval_profile.location and location_pref == "Remote":
        location_pref = eval_profile.location

    # Apply overrides if provided
    if override_keywords and override_keywords.strip():
        keywords = override_keywords.strip()
    if override_location and override_location.strip():
        location_pref = override_location.strip()

    # 2. Build existing jobs list to exclude them
    existing_jobs_str = "\n".join([f"- {j.get('title')} at {j.get('company')}" for j in existing_jobs])    # 3. Query LLM provider to fetch additional unique jobs
    pm = ProviderManager()
    active_provider = pm.settings.get("active_provider", "local")
    
    profile_skills = eval_profile.skills
    profile_roles = eval_profile.target_roles
    experience_level = eval_profile.experience_level
    preferred_region = eval_profile.region or eval_profile.location or "Kerala, India"
    
    raw_jobs_list = []
    
    # Expand keywords using synonym mapping
    expanded_keywords = expand_search_query(keywords)
    
    if active_provider and active_provider.lower() != "local":
        async def fetch_llm_jobs_for_keyword(kw):
            llm_raw_list = []
            try:
                system_prompt = "You are a professional Job Discovery Scraper Agent."
                user_prompt = f"""
Search your database and knowledge base to fetch a list of 5-8 real-world, highly relevant active job roles for a candidate with the following details. The candidate may have an IT/tech or non-tech background, depending on their target roles and skills:
- Search Keywords: {kw}
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
                        llm_raw_list.append({
                            "title": job.get("title", "Software Developer"),
                            "company": job.get("company", "Tech Startup"),
                            "location": job.get("location", location_pref),
                            "salary": job.get("salary", "Not Specified"),
                            "description": job.get("description", "Software developer role."),
                            "skills_required": job.get("skills_required", [kw]),
                            "url": job.get("url", "https://boards.greenhouse.io/careers")
                        })
            except Exception as e:
                print(f"LLM Job Discovery Scraper failed in scrape_more_jobs for keyword {kw}: {str(e)}")
            return llm_raw_list

        llm_tasks = [fetch_llm_jobs_for_keyword(kw) for kw in expanded_keywords]
        llm_results = await asyncio.gather(*llm_tasks, return_exceptions=True)
        for r in llm_results:
            if isinstance(r, list):
                raw_jobs_list.extend(r)

    if not raw_jobs_list:
        return []

    # Raw Deduplication prioritizing direct sources
    def get_raw_source_rank(url: str) -> int:
        url_lower = url.lower()
        if any(k in url_lower for k in ["greenhouse.io", "lever.co", "ashbyhq.com", "workable.com"]):
            return 4
        if "careers" in url_lower:
            return 3
        return 2

    raw_jobs_list.sort(key=lambda x: get_raw_source_rank(x.get("url", "")), reverse=True)
    
    unique_raw_jobs = []
    seen = set()
    for job in raw_jobs_list:
        key = (job.get("title", "").strip().lower(), job.get("company", "").strip().lower())
        if key not in seen:
            seen.add(key)
            unique_raw_jobs.append(job)

    # Hydrate snippets concurrently with Semaphore control (max 5 parallel requests)
    sem = asyncio.Semaphore(5)
    async def hydrate_task(job_dict):
        async with sem:
            hydrated_desc = await hydrate_job_description(job_dict.get("url", ""), job_dict.get("description", ""))
            job_dict["description"] = hydrated_desc
            
    hydration_tasks = [hydrate_task(job) for job in unique_raw_jobs]
    await asyncio.gather(*hydration_tasks, return_exceptions=True)

    # 4. Load Career Memory pairwise stats
    pairwise_stats = _load_pairwise_stats()

    # 5. Evaluate and score discovered jobs in parallel
    scored_jobs = []
    eval_tasks = []
    jobs_to_eval = []
    
    for item in unique_raw_jobs:
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
        eval_tasks.append(evaluate_job_listing(job_obj, eval_profile, parsed_preferences, startup_w, remote_w, salary_w, trust_w))
        
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
    validator = StrictJobValidationEngine(eval_profile)
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
