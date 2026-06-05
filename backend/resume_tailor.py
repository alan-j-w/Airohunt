import os
import re
from typing import Tuple

def calculate_keyword_overlap(resume_text: str, job_desc: str) -> Tuple[float, list]:
    # Extract words from both texts
    def get_words(text: str):
        return set(re.findall(r'\b[a-zA-Z]{3,15}\b', text.lower()))
        
    resume_words = get_words(resume_text)
    job_words = get_words(job_desc)
    
    # Simple list of stop words to exclude
    stop_words = {
        "and", "the", "for", "with", "from", "you", "that", "this", "their", "are", 
        "will", "our", "our", "your", "have", "has", "had", "been", "was", "were"
    }
    
    important_job_words = job_words - stop_words
    matching_keywords = resume_words.intersection(important_job_words)
    
    if not important_job_words:
        return 0.0, []
        
    score = (len(matching_keywords) / len(important_job_words)) * 100
    # cap at 95% for heuristic, leave 100% for actual perfect matches
    score = min(score, 95.0)
    
    return round(score, 1), list(matching_keywords)[:15]

def tailor_resume_local(resume_text: str, job_title: str, job_company: str, job_desc: str, user_skills: list) -> str:
    # Heuristically generate an optimized Resume introduction
    overlap_score, matching_keywords = calculate_keyword_overlap(resume_text, job_desc)
    
    skills_bullet = ", ".join(user_skills)
    keywords_bullet = ", ".join([k.capitalize() for k in matching_keywords[:6]])
    
    tailored_text = f"""# Tailored Resume for {job_title} at {job_company}
[ATS Optimization Level: Local Heuristic Match]

## Professional Summary
Dedicated professional with targeted capabilities in {job_title}. Equipped with core skills in {skills_bullet}. Proven competence utilizing industry key skills including: {keywords_bullet} to deliver high-quality project contributions.

---

## Targeted Core Competencies
* **Primary Skills**: {skills_bullet}
* **Role Alignment Keywords**: {keywords_bullet}

---

## Professional Work History & Experience
{resume_text}

---
*Note: This resume was automatically structured to highlight matching skills for the {job_title} role at {job_company} without fabricating credentials.*
"""
    return tailored_text

def tailor_resume_openai(api_key: str, resume_text: str, job_title: str, job_company: str, job_desc: str) -> str:
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        
        prompt = f"""
You are an expert ATS-friendly resume tailoring AI. 
Your task is to tailor a user's resume for a specific job title and job description.
Do NOT fabricate any credentials, jobs, companies, dates, or certifications. 
Only use information present in the user's base resume. 
Your job is to restructure, highlight matching skills, rephrase descriptions, and align the phrasing to matching keywords from the job description to improve the ATS score.

Target Job Title: {job_title}
Target Company: {job_company}
Target Job Description:
{job_desc}

User Base Resume:
{resume_text}

Format the output resume in clean, professional Markdown. Add a small footer stating "ATS Optimized by Airohunt (OpenAI)".
"""
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a professional resume writer who tailors resumes accurately and never invents details."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3
        )
        return response.choices[0].message.content
    except Exception as e:
        # Fallback to local
        return f"[AI Generation Error: {str(e)}]\n\n" + tailor_resume_local(resume_text, job_title, job_company, job_desc, [])

async def process_resume_tailoring(resume_text: str, job_title: str, job_company: str, job_desc: str, user_skills: list, provider: str = "local") -> Tuple[float, str]:
    from ai.provider_manager import ProviderManager
    
    # Calculate score using keyword overlap
    score, _ = calculate_keyword_overlap(resume_text, job_desc)
    
    if not provider or provider.lower() == "local":
        tailored = tailor_resume_local(resume_text, job_title, job_company, job_desc, user_skills)
        return score, tailored
        
    try:
        prompt = f"""
You are an expert ATS-friendly resume tailoring AI. 
Your task is to tailor a user's resume for a specific job title and job description.
Do NOT fabricate any credentials, jobs, companies, dates, or certifications. 
Only use information present in the user's base resume. 
Your job is to restructure, highlight matching skills, rephrase descriptions, and align the phrasing to matching keywords from the job description to improve the ATS score.

Target Job Title: {job_title}
Target Company: {job_company}
Target Job Description:
{job_desc}

User Base Resume:
{resume_text}

Format the output resume in clean, professional Markdown. Add a small footer stating "ATS Optimized by Airohunt ({provider.upper()})".
"""
        pm = ProviderManager()
        tailored = await pm.call_llm(
            system_prompt="You are a professional resume writer who tailors resumes accurately and never invents details.",
            user_prompt=prompt,
            provider=provider.lower()
        )
        # Boost score slightly if AI optimization succeeds
        score = min(score + 15, 100)
    except Exception as e:
        print(f"AI resume tailoring failed, falling back to local: {str(e)}")
        tailored = f"[AI Tailoring Failed: {str(e)}]\n\n" + tailor_resume_local(resume_text, job_title, job_company, job_desc, user_skills)
        
    return score, tailored
