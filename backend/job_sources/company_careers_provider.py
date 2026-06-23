import re
import os
import json
from typing import List, Dict, Any
from job_sources.base_provider import BaseJobProvider
from ai.provider_manager import ProviderManager

KERALA_STARTUPS_POOL = []

class CompanyCareersJobProvider(BaseJobProvider):
    async def fetch_jobs(self, keywords: str, location: str, limit: int = 15) -> List[Dict[str, Any]]:
        # 1. Try to fetch dynamic active job postings using LLM if provider is active
        pm = ProviderManager()
        active_provider = pm.settings.get("active_provider", "local")
        
        if active_provider and active_provider.lower() != "local":
            try:
                # Load profile details for better contextual generation
                profile_skills = []
                profile_roles = []
                experience_level = "Fresher"
                preferred_region = "Kerala, India"
                if os.path.exists("profile.json"):
                    with open("profile.json", "r", encoding="utf-8") as f:
                        prof = json.load(f)
                        profile_skills = prof.get("skills", [])
                        profile_roles = prof.get("target_roles", [])
                        experience_level = prof.get("experience_level", "Fresher")
                        preferred_region = prof.get("region") or prof.get("location") or "Kerala, India"
                        
                system_prompt = "You are a professional Job Discovery Scraper Agent."
                user_prompt = f"""
Search your database and knowledge base to fetch a list of 5-8 real-world, highly relevant active job roles for a candidate with the following details. The candidate may have an IT/tech or non-tech background, depending on their target roles and skills:
- Search Keywords: {keywords}
- Preferred Location: {location} (Focus heavily on the {preferred_region} region if default or remote)
- Candidate Skills: {", ".join(profile_skills)}
- Target Roles: {", ".join(profile_roles)}
- Experience Level: {experience_level}

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
                if isinstance(jobs_list, list) and len(jobs_list) > 0:
                    cleaned_jobs = []
                    for job in jobs_list:
                        cleaned_jobs.append({
                            "title": job.get("title", "Software Developer"),
                            "company": job.get("company", "Tech Startup"),
                            "location": job.get("location", location),
                            "salary": job.get("salary", "Not Specified"),
                            "description": job.get("description", "Software developer role."),
                            "skills_required": job.get("skills_required", [keywords]),
                            "url": job.get("url", "https://boards.greenhouse.io/careers")
                        })
                    return cleaned_jobs[:limit]
            except Exception as e:
                print(f"LLM Job Discovery Scraper failed, falling back to local pool: {str(e)}")

        return []
