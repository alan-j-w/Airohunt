import re
import os
import json
from typing import List, Dict, Any
from job_sources.base_provider import BaseJobProvider
from ai.provider_manager import ProviderManager

# Highly targeted mock database representing real startup patterns in Kerala (Kochi/Trivandrum) and Remote
KERALA_STARTUPS_POOL = [
    {
        "title": "Junior React Developer",
        "company": "Riafy Technologies",
        "location": "Kochi, Kerala (Hybrid)",
        "salary": "₹3.6 LPA - ₹5.0 LPA",
        "description": "Riafy is a leading product startup building global AI apps. We are looking for a Junior React Developer. Hiring is project-based: we will review your Github repositories and ask you to build a small web widget instead of solving DSA whiteboard algorithms. Strong Javascript/CSS skills are required.",
        "skills_required": ["React", "JavaScript", "HTML", "CSS", "Git"],
        "url": "https://riafy.me"
    },
    {
        "title": "Django Backend Developer",
        "company": "SayOne Technologies",
        "location": "Kochi, Kerala (Onsite)",
        "salary": "₹4.0 LPA - ₹6.0 LPA",
        "description": "SayOne specializes in Django web architectures. We are hiring a Django developer. Our interview process is project-based: you will build a quick REST API. No DSA whiteboard tests. Freshers with good hobby projects are welcome to apply.",
        "skills_required": ["Python", "Django", "PostgreSQL", "REST APIs", "Git"],
        "url": "https://sayonetech.com/careers"
    },
    {
        "title": "Full Stack Developer (MERN)",
        "company": "KeyVal Software Systems",
        "location": "Trivandrum, Kerala (Hybrid)",
        "salary": "₹5.0 LPA - ₹7.2 LPA",
        "description": "KeyValue builds scalable product systems. Hiring MERN developers. We value clean code, git usage, and solid frontend state design. We test candidates via take-home coding challenges where you write clean, modular React and Node code.",
        "skills_required": ["MongoDB", "Express.js", "React", "Node.js", "TypeScript", "Git"],
        "url": "https://keyvalue.systems/careers"
    },
    {
        "title": "Software Engineer Intern (Python)",
        "company": "Accubits Technologies",
        "location": "Trivandrum, Kerala (Onsite)",
        "salary": "₹15,000 - ₹25,000 / month",
        "description": "Accubits is an AI and Web3 product company. We are hiring intern software engineers. Learn Python backend development, Docker deployments, and LLM integrations. Outstanding interns are offered full-time roles upon completion. Hiring evaluates your Github profile.",
        "skills_required": ["Python", "Git", "SQL"],
        "url": "https://accubits.com/careers"
    },
    {
        "title": "React Frontend Developer (Fresher)",
        "company": "Entri.app",
        "location": "Kochi, Kerala (Remote/Hybrid)",
        "salary": "₹3.0 LPA - ₹4.5 LPA",
        "description": "Entri is a high-growth local learning startup. We are seeking a Fresher React Developer to build responsive user portals. We do not do DSA-heavy interviews. We evaluate your web portfolio and take-home React widgets.",
        "skills_required": ["React", "JavaScript", "CSS"],
        "url": "https://entri.app"
    },
    {
        "title": "Junior Python Web Developer",
        "company": "CareStack Systems",
        "location": "Trivandrum, Kerala (Hybrid)",
        "salary": "₹4.5 LPA - ₹6.0 LPA",
        "description": "CareStack builds cloud-based dental practice systems. Seeking Junior Python developers. Work with Python backend services, SQL databases, and secure APIs. Interviews include practical coding assignments.",
        "skills_required": ["Python", "SQL", "Git"],
        "url": "https://carestack.com/careers"
    },
    {
        "title": "Frontend React Engineer",
        "company": "Huddle Remote Products",
        "location": "Remote (India)",
        "salary": "₹8.0 LPA - ₹12.0 LPA",
        "description": "Huddle is a remote-first startup. We hire MERN/React engineers. Hiring is 100% remote: we review your Github, look at your projects, and host a collaborative coding session where we add a feature together.",
        "skills_required": ["React", "JavaScript", "TypeScript", "Tailwind CSS"],
        "url": "https://wellfound.com"
    },
    {
        "title": "Graphic Designer & UI Creator",
        "company": "Riafy Technologies",
        "location": "Kochi, Kerala (Hybrid)",
        "salary": "₹3.5 LPA - ₹5.0 LPA",
        "description": "Seeking a creative Graphic Designer to join our product UI team. You will create assets, mockups, social graphics, and interface layouts for our global AI applications. Candidates are evaluated via a small creative portfolio review.",
        "skills_required": ["Figma", "UI/UX", "Adobe Photoshop", "Illustrator", "Creative Design"],
        "url": "https://riafy.me"
    },
    {
        "title": "Social Media & Marketing Specialist",
        "company": "Entri.app",
        "location": "Kochi, Kerala (Remote/Hybrid)",
        "salary": "₹3.0 LPA - ₹4.5 LPA",
        "description": "Entri is hiring a Social Media Specialist to coordinate digital marketing, manage content across platforms, run local ad campaigns, and engage our learning community. No IT background required; strong writing and marketing skills are essential.",
        "skills_required": ["Marketing", "Social Media", "Content Writing", "SEO", "Communication"],
        "url": "https://entri.app"
    },
    {
        "title": "Human Resources & Operations Associate",
        "company": "KeyValue Systems",
        "location": "Kochi, Kerala (Onsite)",
        "salary": "₹4.0 LPA - ₹5.5 LPA",
        "description": "KeyValue is looking for an HR & Operations Associate. Responsibilities include employee onboarding, operational support, workplace management, and coordinating recruiter pipelines. Strong interpersonal skills are highly valued.",
        "skills_required": ["HR", "Recruitment", "Operations", "Excel", "Communication"],
        "url": "https://keyvalue.systems/careers"
    },
    {
        "title": "Finance Executive & Accountant",
        "company": "SayOne Technologies",
        "location": "Kochi, Kerala (Onsite)",
        "salary": "₹4.2 LPA - ₹6.0 LPA",
        "description": "SayOne is seeking a Finance Executive. You will handle accounting, payroll, invoicing, vendor coordination, and tax compliance. Requires a degree in Finance/Commerce and knowledge of Tally/Excel.",
        "skills_required": ["Accounting", "Finance", "Excel", "Tally", "Invoicing"],
        "url": "https://sayonetech.com/careers"
    },
    {
        "title": "English Content & Technical Writer",
        "company": "Accubits Technologies",
        "location": "Trivandrum, Kerala (Hybrid)",
        "salary": "₹3.6 LPA - ₹5.2 LPA",
        "description": "We are seeking a Content Writer to construct high-quality articles, documentation, marketing blogs, and copy. Work closely with product teams to draft descriptions and reports. A strong command of written English is mandatory.",
        "skills_required": ["Content Writing", "Copywriting", "SEO", "English", "Communication"],
        "url": "https://accubits.com/careers"
    },
    {
        "title": "Sales & Business Development Representative",
        "company": "CareStack Systems",
        "location": "Trivandrum, Kerala (Hybrid)",
        "salary": "₹4.0 LPA - ₹6.5 LPA",
        "description": "CareStack is seeking a BDR to handle lead generation, client communication, sales demos, and partner pipeline development. Excellent communication and sales pitching are required. Training is provided.",
        "skills_required": ["Sales", "Business Development", "Communication", "CRM", "Excel"],
        "url": "https://carestack.com/careers"
    }
]

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
                if os.path.exists("profile.json"):
                    with open("profile.json", "r", encoding="utf-8") as f:
                        prof = json.load(f)
                        profile_skills = prof.get("skills", [])
                        profile_roles = prof.get("target_roles", [])
                        experience_level = prof.get("experience_level", "Fresher")
                        
                system_prompt = "You are a professional Job Discovery Scraper Agent."
                user_prompt = f"""
Search your database and knowledge base to fetch a list of 5-8 real-world, highly relevant active job roles for a candidate with the following details. The candidate may have an IT/tech or non-tech background, depending on their target roles and skills:
- Search Keywords: {keywords}
- Preferred Location: {location} (Focus heavily on Kerala, India region if default or remote)
- Candidate Skills: {", ".join(profile_skills)}
- Target Roles: {", ".join(profile_roles)}
- Experience Level: {experience_level}

You MUST return a JSON list of job objects. Each object MUST have this schema:
[
  {{
    "title": "Job Title (matching candidate's target roles and field)",
    "company": "Company Name (use real active companies active in India/Kochi/Trivandrum/Remote matching the candidate's sector, e.g., Riafy, SayOne, CareStack, Accubits, KeyValue, Entri, or others)",
    "location": "Location (e.g. Kochi, Kerala, India or Remote)",
    "salary": "Salary (transparency is key, e.g. ₹4.5 LPA - ₹6.0 LPA or $80,000 - $100,000)",
    "description": "A detailed job description specifying responsibilities, skills, and evaluation style. Make it realistic and detailed (at least 3-4 sentences).",
    "skills_required": ["Skill1", "Skill2", "Skill3"],
    "url": "The direct official careers website URL of the company (e.g., https://riafy.me, https://sayonetech.com/careers, or the specific job's application link on the official company website). It MUST be a real, working website URL of the company."
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

        # 2. Local Fallback: Filter mock startup pool based on keywords/locations in memory
        filtered = []
        kw = keywords.lower()
        loc = location.lower()
        
        for job in KERALA_STARTUPS_POOL:
            # Check if keywords match title/description/skills
            skills_text = " ".join(job["skills_required"]).lower()
            text_match = (
                kw in job["title"].lower() or 
                kw in job["description"].lower() or 
                kw in skills_text
            )
            
            # Check location match
            loc_match = True
            if loc and loc != "remote":
                loc_match = loc in job["location"].lower()
                
            if text_match and loc_match:
                filtered.append({
                    "title": job["title"],
                    "company": job["company"],
                    "location": job["location"],
                    "salary": job["salary"],
                    "description": job["description"],
                    "skills_required": job["skills_required"],
                    "url": job["url"]
                })
                
        # If no specific matches, return a couple of general listings to prevent empty feeds
        if not filtered:
            return KERALA_STARTUPS_POOL[:2]
            
        return filtered[:limit]
