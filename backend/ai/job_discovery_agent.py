import json
import re
from typing import Dict, Any
from models import Job, UserProfile
from ai.provider_manager import ProviderManager
from ai.prompt_templates import SCAM_DETECTOR_SYSTEM, SCAM_DETECTOR_USER, JOB_MATCHER_SYSTEM, JOB_MATCHER_USER

provider_manager = ProviderManager()

LOCAL_SCAM_INDICATORS = [
    "training fee", "enrollment fee", "must pay", "purchase hardware", 
    "reimburse the kit", "pay for certificate", "exam voucher", 
    "fees apply", "internship training program"
]

def calculate_opportunity_score(job: Job, startup_w: str = "Medium", remote_w: str = "Medium", salary_w: str = "Medium", trust_w: str = "Medium") -> float:
    multipliers = {"low": 0.5, "medium": 1.0, "high": 2.0}
    s_mult = multipliers.get(startup_w.lower(), 1.0)
    r_mult = multipliers.get(remote_w.lower(), 1.0)
    sal_mult = multipliers.get(salary_w.lower(), 1.0)
    t_mult = multipliers.get(trust_w.lower(), 1.0)
    
    score = 50.0  # base
    
    desc_lower = job.description.lower()
    title_lower = job.title.lower()
    
    # 1. Salary Transparency
    if "not specified" not in job.salary.lower():
        score += 15.0 * sal_mult
        
    # 2. Remote Flexibility
    if "remote" in job.location.lower() or "remote" in desc_lower:
        score += 15.0 * r_mult
        
    # 3. Startup Potential
    if "startup" in job.company.lower() or "startup" in desc_lower:
        score += 15.0 * s_mult
        
    # 4. Trust and scam indicators
    is_scam_suspect = any(phrase in desc_lower for phrase in LOCAL_SCAM_INDICATORS)
    if len(desc_lower) >= 150 and not is_scam_suspect:
        score += 10.0 * t_mult
        
    return min(100.0, score)

def evaluate_job_locally(job: Job, profile: UserProfile, parsed_preferences: dict, startup_w: str = "Medium", remote_w: str = "Medium", salary_w: str = "Medium", trust_w: str = "Medium") -> dict:
    # 1. Scam Check
    is_scam = False
    scam_risk_score = 10
    scam_reason = ""
    
    text_check = f"{job.title} {job.company} {job.description}".lower()
    for phrase in LOCAL_SCAM_INDICATORS:
        if phrase in text_check:
            is_scam = True
            scam_risk_score = 90
            scam_reason = f"Suspected Training/Course Scam: Mentions '{phrase}' which is a red flag."
            break
            
    # 2. Technical Match Score
    matched_skills = []
    user_skills_lower = [s.lower() for s in profile.skills]
    for s in job.skills_required:
        if s.lower() in user_skills_lower:
            matched_skills.append(s)
            
    tech_score = 0.0
    if job.skills_required:
        tech_score = (len(matched_skills) / len(job.skills_required)) * 100
    else:
        tech_score = 50.0
        
    # 3. Preference Match Score
    pref_score = 70.0
    pros = []
    cons = []
    
    role_match = False
    for role in parsed_preferences.get("preferred_roles", []):
        if role.lower() in job.title.lower():
            role_match = True
            pros.append(role)
            break
    if role_match:
        pref_score += 20
    else:
        cons.append("Title mismatch")
        
    excluded_match = False
    for ex in parsed_preferences.get("excluded_company_types", []):
        if ex.lower() in job.company.lower() or ex.lower() in job.description.lower():
            excluded_match = True
            cons.append(f"Contains excluded type: {ex}")
            break
    if excluded_match:
        pref_score -= 40
        
    remote_pref = parsed_preferences.get("remote_preference", "Any")
    if remote_pref == "Remote" and "remote" in job.location.lower():
        pros.append("Remote")
        pref_score += 10
    elif remote_pref == "Onsite" and "remote" not in job.location.lower():
        pros.append("Onsite")
        pref_score += 10
        
    pref_score = max(0, min(100, pref_score))
    
    # 4. Trust Score
    trust_score = 90.0
    if "not specified" in job.salary.lower():
        trust_score -= 15
        cons.append("Salary hidden")
    else:
        pros.append("Salary disclosed")
        
    if is_scam:
        trust_score -= 60
        
    if len(job.description) < 150:
        trust_score -= 20
        cons.append("Vague description")
        
    trust_score = max(0, min(100, trust_score))
    
    # Calculate Opportunity Score
    opp_score = calculate_opportunity_score(job, startup_w, remote_w, salary_w, trust_w)
    if opp_score >= 80:
        pros.append("High Opportunity")
    
    # Calculate Trust Rating Grade
    trust_rating = "B"
    if trust_score >= 90:
        trust_rating = "A+"
    elif trust_score >= 80:
        trust_rating = "A"
    elif trust_score >= 70:
        trust_rating = "B"
    elif trust_score >= 50:
        trust_rating = "C"
    else:
        trust_rating = "D"
    if is_scam:
        trust_rating = "F"

    # Local Company Info Database for Research Sidebar
    KERALA_STARTUPS_INFO = {
        "riafy": "Riafy Technologies is a leading AI research and product design startup in Kochi, building global mobile apps.",
        "sayone": "SayOne Technologies is a premier Django web application and backend engineering firm based in Kochi.",
        "keyval": "KeyValue Software Systems is a product development and cloud engineering firm in Trivandrum specializing in high-scale React and Node systems.",
        "accubits": "Accubits Technologies is a global digital transformation and product development company specializing in AI, Web3, and enterprise solutions in Trivandrum.",
        "entri": "Entri.app is an educational technology and learning platform startup based in Kochi helping users prepare for exams in local languages.",
        "carestack": "CareStack Systems builds cloud-based dental practice management and healthtech solutions based in Trivandrum."
    }
    
    comp_lower = job.company.lower()
    summary = ""
    for name, info in KERALA_STARTUPS_INFO.items():
        if name in comp_lower:
            summary = info
            break
    if not summary:
        sentences = re.split(r'(?<=[.!?])\s+', job.description)
        summary = " ".join(sentences[:2]) if len(sentences) >= 2 else (sentences[0] if sentences else f"{job.company} is hiring in the tech industry.")

    # Tech Stack extraction
    TECH_TAGS = ["React", "JavaScript", "TypeScript", "Node.js", "Django", "Python", "MongoDB", "PostgreSQL", "SQL", "HTML", "CSS", "Tailwind CSS", "Git", "Docker", "AWS", "FastAPI", "Flask"]
    tech_stack = []
    desc_lower = job.description.lower()
    for tag in TECH_TAGS:
        if tag.lower() in desc_lower or any(s.lower() == tag.lower() for s in job.skills_required):
            tech_stack.append(tag)
    if not tech_stack:
        tech_stack = job.skills_required if job.skills_required else ["General Tech Stack"]

    # Hiring signals
    hiring_signals = []
    if any(phrase in desc_lower for phrase in ["no dsa", "project-based", "github", "practical challenge", "take-home"]):
        hiring_signals.append("Project-Based Evaluation (No Whiteboard)")
    else:
        hiring_signals.append("Standard Technical Review")
        
    if "remote" in job.location.lower() or "remote" in desc_lower:
        hiring_signals.append("Remote-First Setup")
    else:
        hiring_signals.append("Onsite Integration")
        
    if any(phrase in desc_lower for phrase in ["fresher", "junior", "intern", "entry"]):
        hiring_signals.append("Early Career Onboarding")

    # Create AI Recommendation
    rec_text = ""
    if is_scam:
        rec_text = "Highly advise avoiding. This listing exhibits indicators typical of predatory course placement or training fee scams."
    elif tech_score >= 70 and pref_score >= 70:
        rec_text = f"Strong recommendation to apply. You match {len(matched_skills)} core skills requested and the listing aligns with your target preferences."
    else:
        rec_text = "Moderate match. Consider reviewing if you possess matching projects, but verify details regarding salary and hiring style."
        
    if len(pros) == 0:
        pros = ["General Job Match"]
        
    return {
        "is_scam": is_scam,
        "scam_risk_score": scam_risk_score,
        "scam_reason": scam_reason,
        "tech_match_score": round(tech_score, 1),
        "pref_match_score": round(pref_score, 1),
        "trust_score": round(trust_score, 1),
        "opportunity_score": round(opp_score, 1),
        "recommendation_pros": pros[:5],
        "recommendation_cons": cons[:3],
        "ai_recommendation": rec_text,
        "evaluation_mode": "Local Heuristics",
        "company_summary": summary,
        "tech_stack": tech_stack,
        "hiring_signals": hiring_signals,
        "trust_rating": trust_rating
    }

async def evaluate_job_listing(job: Job, profile: UserProfile, parsed_preferences: dict, startup_w: str = "Medium", remote_w: str = "Medium", salary_w: str = "Medium", trust_w: str = "Medium") -> dict:
    try:
        # 1. Scam Check
        scam_sys = SCAM_DETECTOR_SYSTEM
        scam_user = SCAM_DETECTOR_USER.format(
            company_name=job.company,
            job_title=job.title,
            salary=job.salary,
            job_desc=job.description
        )
        
        scam_res = await provider_manager.call_llm(scam_sys, scam_user, response_format_json=True)
        
        scam_text = scam_res.strip()
        if scam_text.startswith("```json"):
            scam_text = scam_text[7:]
        if scam_text.endswith("```"):
            scam_text = scam_text[:-3]
        scam_data = json.loads(scam_text.strip())
        
        # 2. Match & Trust Scoring
        match_sys = JOB_MATCHER_SYSTEM
        match_user = JOB_MATCHER_USER.format(
            user_skills=", ".join(profile.skills),
            target_roles=", ".join(profile.target_roles),
            parsed_preferences=json.dumps(parsed_preferences),
            job_title=job.title,
            company_name=job.company,
            location=job.location,
            salary=job.salary,
            job_desc=job.description
        )
        
        match_res = await provider_manager.call_llm(match_sys, match_user, response_format_json=True)
        
        match_text = match_res.strip()
        if match_text.startswith("```json"):
            match_text = match_text[7:]
        if match_text.endswith("```"):
            match_text = match_text[:-3]
        match_data = json.loads(match_text.strip())
        
        opp_score = calculate_opportunity_score(job, startup_w, remote_w, salary_w, trust_w)
        
        # Determine the active provider label
        prov = provider_manager.settings.get("active_provider", "AI").capitalize()
        eval_mode = f"AI Analyzed ({prov})"
        
        # Calculate Trust Grade
        ts = float(match_data.get("trust_score", 0.0))
        t_grade = "B"
        if ts >= 90: t_grade = "A+"
        elif ts >= 80: t_grade = "A"
        elif ts >= 70: t_grade = "B"
        elif ts >= 50: t_grade = "C"
        else: t_grade = "D"
        if scam_data.get("is_scam", False): t_grade = "F"

        # Safe extractions
        summary = match_data.get("company_summary", "")
        if not summary:
            sentences = re.split(r'(?<=[.!?])\s+', job.description)
            summary = " ".join(sentences[:2]) if len(sentences) >= 2 else (sentences[0] if sentences else f"{job.company} is hiring in the tech industry.")

        tech_stack = match_data.get("tech_stack", [])
        if not tech_stack:
            TECH_TAGS = ["React", "JavaScript", "TypeScript", "Node.js", "Django", "Python", "MongoDB", "PostgreSQL", "SQL"]
            tech_stack = [tag for tag in TECH_TAGS if tag.lower() in job.description.lower()]
            if not tech_stack: tech_stack = job.skills_required

        hiring_signals = match_data.get("hiring_signals", [])
        if not hiring_signals:
            hiring_signals = ["Project-Based Evaluation" if "project" in job.description.lower() or "portfolio" in job.description.lower() else "Standard Technical Review"]

        return {
            "is_scam": scam_data.get("is_scam", False),
            "scam_risk_score": int(scam_data.get("scam_risk_score", 0)),
            "scam_reason": scam_data.get("scam_reason", ""),
            "tech_match_score": float(match_data.get("tech_match_score", 0.0)),
            "pref_match_score": float(match_data.get("pref_match_score", 0.0)),
            "trust_score": ts,
            "opportunity_score": float(opp_score),
            "recommendation_pros": match_data.get("recommendation_pros", []),
            "recommendation_cons": match_data.get("recommendation_cons", []),
            "ai_recommendation": match_data.get("ai_recommendation", ""),
            "evaluation_mode": eval_mode,
            "company_summary": summary,
            "tech_stack": tech_stack,
            "hiring_signals": hiring_signals,
            "trust_rating": t_grade
        }
        
    except Exception as e:
        print(f"AI job evaluation failed, falling back to local scorer: {str(e)}")
        fallback_res = evaluate_job_locally(job, profile, parsed_preferences, startup_w, remote_w, salary_w, trust_w)
        # Check if the failure is because key is missing/empty
        missing_key_reason = ""
        err_msg = str(e).lower()
        if "key not configured" in err_msg or "api key was empty" in err_msg or "failed to load provider" in err_msg or "unconfigured" in err_msg:
            missing_key_reason = "[Missing AI Credentials - Running in Free Local Mode]"
        else:
            missing_key_reason = f"[AI Connection Failed: {str(e)}]"
            
        fallback_res["ai_recommendation"] = f"{missing_key_reason} {fallback_res['ai_recommendation']}"
        return fallback_res
