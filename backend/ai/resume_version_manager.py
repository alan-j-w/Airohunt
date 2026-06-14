import os
import re
from typing import Dict, Any, Tuple
from utils import load_json_file, save_json_file

RESUME_PROFILES_FILE = "resume_profiles.json"

DEFAULT_TEMPLATES = {
    "react": {
        "name": "React Developer Version",
        "skills": ["React", "JavaScript", "TypeScript", "HTML", "CSS", "Tailwind CSS", "Redux", "Next.js", "Vite", "Git"],
        "resume_text": "Alan Joy Wilson\nReact Frontend Developer\nKochi, Kerala | alanjoywilson@gmail.com\n\nProfessional Summary\nHighly motivated Frontend Developer specializing in React.js and modern frontend workflows. Proficient in building responsive user interfaces, handling state management, and integrating secure REST APIs.\n\nTechnical Skills\n- Frontend: React.js, Next.js, HTML5, CSS3, Tailwind CSS, JavaScript (ES6+), TypeScript\n- Tools & Platforms: Git, GitHub, VS Code, Vite, npm\n- Concepts: REST APIs, State Management, Responsive Web Design, Component-Driven Development"
    },
    "django": {
        "name": "Django Backend Version",
        "skills": ["Python", "Django", "SQL", "PostgreSQL", "REST APIs", "FastAPI", "Flask", "Docker", "Git"],
        "resume_text": "Alan Joy Wilson\nDjango Backend Developer\nKochi, Kerala | alanjoywilson@gmail.com\n\nProfessional Summary\nBackend Engineer with strong expertise in Python, Django, and SQL database design. Focused on building high-performance REST APIs, database query optimizations, and secure backend routing logic.\n\nTechnical Skills\n- Backend: Python, Django, Django REST Framework, FastAPI, Flask\n- Databases: PostgreSQL, MySQL, SQLite\n- Tools & Concepts: Git, Docker, REST APIs, JSON Web Tokens (JWT), Query Optimization"
    },
    "fullstack": {
        "name": "Full Stack MERN Version",
        "skills": ["React", "Node.js", "Express.js", "MongoDB", "JavaScript", "SQL", "Git", "REST APIs"],
        "resume_text": "Alan Joy Wilson\nFull Stack Web Developer\nKochi, Kerala | alanjoywilson@gmail.com\n\nProfessional Summary\nFull Stack Developer experienced in the MERN stack (MongoDB, Express, React, Node.js). Competent in architecting end-to-end web applications, integrating user authentication, and structuring responsive web apps.\n\nTechnical Skills\n- Frontend: React.js, Next.js, HTML, CSS, Tailwind CSS, JavaScript\n- Backend: Node.js, Express.js, Django\n- Databases: MongoDB, MySQL, SQLite\n- Core Competencies: REST APIs, JWT Authentication, OAuth, CRUD Operations, Version Control"
    },
    "cybersecurity": {
        "name": "Cybersecurity & Django Version",
        "skills": ["Python", "Django", "Security", "Penetration Testing", "Vulnerability", "JavaScript", "SQL", "Git"],
        "resume_text": "Alan Joy Wilson\nCybersecurity Specialist & Developer\nKochi, Kerala | alanjoywilson@gmail.com\n\nProfessional Summary\nDeveloper and security enthusiast with a strong focus on secure web application development. Experienced in building cybersecurity learning tools, lab setups, and implementing threat countermeasures against OWASP Top 10 vulnerabilities.\n\nTechnical Skills\n- Security Concepts: Penetration Testing, OWASP Top 10, SQL Injection, CSRF Mitigation, RBAC\n- Technologies: Python, Django, HTML, CSS, JavaScript, SQL\n- Tools & Environments: Git, Kali Linux, VS Code"
    }
}

class ResumeVersionManager:
    def __init__(self):
        self.profiles_path = RESUME_PROFILES_FILE
        self._initialize_profiles()

    def _initialize_profiles(self):
        if not os.path.exists(self.profiles_path):
            save_json_file(self.profiles_path, DEFAULT_TEMPLATES)

    def load_profiles(self) -> Dict[str, Any]:
        return load_json_file(self.profiles_path, DEFAULT_TEMPLATES)

    def save_profiles(self, data: Dict[str, Any]):
        save_json_file(self.profiles_path, data)

    def select_best_resume(self, job_title: str, job_description: str, job_skills: list) -> Tuple[str, str]:
        """
        Dynamically matches job details against available resume versions.
        Returns a tuple: (selected_version_key, selected_resume_text)
        """
        profiles = self.load_profiles()
        best_key = "react"  # Default fallback
        best_score = -1.0
        
        job_text_lower = f"{job_title} {job_description}".lower()
        job_skills_lower = [s.lower() for s in job_skills]
        
        for key, version in profiles.items():
            score = 0.0
            version_skills = version.get("skills", [])
            version_skills_lower = [vs.lower() for vs in version_skills]
            
            # 1. Direct Skill matches
            for js in job_skills_lower:
                if js in version_skills_lower:
                    score += 10.0
                    
            # 2. Text Keyword overlaps
            for vs in version_skills_lower:
                # Give points for occurrences in job title/description
                pattern = r'\b' + re.escape(vs) + r'\b'
                matches = len(re.findall(pattern, job_text_lower))
                score += matches * 2.0
                
            # 3. Title match boost
            if key == "react" and ("react" in job_title.lower() or "frontend" in job_title.lower()):
                score += 30.0
            elif key == "django" and ("django" in job_title.lower() or "backend" in job_title.lower() or "python" in job_title.lower()):
                score += 30.0
            elif key == "fullstack" and ("full stack" in job_title.lower() or "mern" in job_title.lower() or "node" in job_title.lower()):
                score += 30.0
            elif key == "cybersecurity" and ("security" in job_title.lower() or "pentest" in job_title.lower() or "cyber" in job_title.lower()):
                score += 30.0
                
            if score > best_score:
                best_score = score
                best_key = key
                
        # Return best match. If no profiles exist or key not found, fallback to React
        matched_profile = profiles.get(best_key, profiles.get("react"))
        return best_key, matched_profile.get("resume_text", "")
