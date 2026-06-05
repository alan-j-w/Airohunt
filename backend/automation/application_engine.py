import re
from typing import Dict, Any, List
from models import UserProfile, Job

class ApplicationEngine:
    @staticmethod
    def classify_url(url: str) -> Dict[str, Any]:
        """
        Classifies application URLs and returns the platform name and automation support score.
        """
        url_lower = url.lower()
        if "greenhouse.io" in url_lower:
            return {"platform": "Greenhouse", "automation_support": "95%"}
        elif "lever.co" in url_lower:
            return {"platform": "Lever", "automation_support": "95%"}
        elif "workable.com" in url_lower:
            return {"platform": "Workable", "automation_support": "90%"}
        elif "ashbyhq.com" in url_lower:
            return {"platform": "Ashby", "automation_support": "85%"}
        elif "smartrecruiters.com" in url_lower:
            return {"platform": "SmartRecruiters", "automation_support": "85%"}
        elif "github.com" in url_lower or "google.com" in url_lower or "linkedin.com" in url_lower:
            return {"platform": "External Portal", "automation_support": "60%"}
        else:
            return {"platform": "Generic Careers Page", "automation_support": "40%"}

    @staticmethod
    def detect_custom_questions(description: str) -> List[Dict[str, str]]:
        """
        Scans job descriptions for indicators of common custom application questions.
        """
        questions = []
        desc_lower = description.lower()
        
        # 1. Notice Period
        if any(term in desc_lower for term in ["notice period", "how soon", "start date", "availability"]):
            questions.append({
                "id": "notice_period",
                "label": "Notice Period / Availability",
                "placeholder": "e.g., Immediate, 30 days, 2 months"
            })
            
        # 2. Visa sponsorship
        if any(term in desc_lower for term in ["visa", "sponsorship", "citizenship", "work authorization", "authorized to work"]):
            questions.append({
                "id": "visa_sponsorship",
                "label": "Visa Sponsorship Status",
                "placeholder": "e.g., No sponsorship required, Citizen, H-1B"
            })
            
        # 3. Salary Expectation
        if any(term in desc_lower for term in ["salary expectation", "desired salary", "expected salary", "ctc expectation"]):
            questions.append({
                "id": "salary_expectations",
                "label": "Salary Expectations",
                "placeholder": "e.g., ₹5.0 LPA, $80k/year"
            })
            
        # 4. Cover letter
        if any(term in desc_lower for term in ["cover letter", "statement of purpose", "why join", "why are you interested"]):
            questions.append({
                "id": "cover_letter_why",
                "label": "Cover Letter / Why do you want to join?",
                "placeholder": "Briefly state your motivation..."
            })
            
        # 5. Experience years
        if any(term in desc_lower for term in ["years of experience", "years experience", "how many years"]):
            questions.append({
                "id": "experience_years",
                "label": "Years of Relevant Experience",
                "placeholder": "e.g., 1.5 years, 2 years"
            })

        return questions

    @staticmethod
    def generate_autofill_script(platform: str, profile: UserProfile, job_company: str) -> str:
        """
        Generates platform-specific JavaScript code to paste into the browser's Developer Console.
        """
        # Parse name
        name_parts = profile.name.split()
        first_name = name_parts[0] if name_parts else ""
        last_name = " ".join(name_parts[1:]) if len(name_parts) > 1 else ""
        
        # Social Fallbacks
        linkedin = f"https://linkedin.com/in/{first_name.lower()}-{last_name.lower()}".replace(" ", "") if last_name else f"https://linkedin.com/in/{first_name.lower()}"
        github = f"https://github.com/{first_name.lower()}{last_name.lower()}".replace(" ", "") if last_name else f"https://github.com/{first_name.lower()}"
        portfolio = f"https://{first_name.lower()}{last_name.lower()}.vercel.app".replace(" ", "") if last_name else f"https://{first_name.lower()}.dev"

        # Escaping inputs
        name_esc = profile.name.replace("'", "\\'")
        fn_esc = first_name.replace("'", "\\'")
        ln_esc = last_name.replace("'", "\\'")
        email_esc = profile.email.replace("'", "\\'")
        phone_esc = profile.phone.replace("'", "\\'")
        comp_esc = job_company.replace("'", "\\'")

        if platform == "Greenhouse":
            return f"""
(() => {{
  console.log("%cAirohunt Autofill Executing...", "color: #06b6d4; font-weight: bold;");
  
  const setVal = (selector, val) => {{
    const el = document.querySelector(selector);
    if (el) {{
      el.value = val;
      el.dispatchEvent(new Event('input', {{ bubbles: true }}));
      el.dispatchEvent(new Event('change', {{ bubbles: true }}));
    }}
  }};
  
  setVal('#first_name', '{fn_esc}');
  setVal('#last_name', '{ln_esc}');
  setVal('#email', '{email_esc}');
  setVal('#phone', '{phone_esc}');
  setVal('#org', '{comp_esc}');
  
  // Greenhouse dynamic question mapping
  const li = document.querySelector('input[name*="linkedin"], input[name*="linkedin_profile"]');
  if (li) {{ li.value = '{linkedin}'; li.dispatchEvent(new Event('input')); }}
  
  const gh = document.querySelector('input[name*="github"]');
  if (gh) {{ gh.value = '{github}'; gh.dispatchEvent(new Event('input')); }}
  
  const port = document.querySelector('input[name*="portfolio"], input[name*="website"]');
  if (port) {{ port.value = '{portfolio}'; port.dispatchEvent(new Event('input')); }}
  
  console.log("%cAirohunt Autofill Complete!", "color: #10b981; font-weight: bold;");
}})();
""".strip()

        elif platform == "Lever":
            return f"""
(() => {{
  console.log("%cAirohunt Autofill Executing...", "color: #06b6d4; font-weight: bold;");
  
  const setValByName = (name, val) => {{
    const el = document.querySelector(`input[name="${{name}}"]`);
    if (el) {{
      el.value = val;
      el.dispatchEvent(new Event('input', {{ bubbles: true }}));
      el.dispatchEvent(new Event('change', {{ bubbles: true }}));
    }}
  }};
  
  setValByName('name', '{name_esc}');
  setValByName('email', '{email_esc}');
  setValByName('phone', '{phone_esc}');
  setValByName('org', '{comp_esc}');
  setValByName('urls[LinkedIn]', '{linkedin}');
  setValByName('urls[GitHub]', '{github}');
  setValByName('urls[Portfolio]', '{portfolio}');
  
  console.log("%cAirohunt Autofill Complete!", "color: #10b981; font-weight: bold;");
}})();
""".strip()

        elif platform == "Workable":
            return f"""
(() => {{
  console.log("%cAirohunt Autofill Executing...", "color: #06b6d4; font-weight: bold;");
  
  const setVal = (el, val) => {{
    if (el) {{
      el.value = val;
      el.dispatchEvent(new Event('input', {{ bubbles: true }}));
      el.dispatchEvent(new Event('change', {{ bubbles: true }}));
    }}
  }};
  
  setVal(document.querySelector('input[name="firstname"]'), '{fn_esc}');
  setVal(document.querySelector('input[name="lastname"]'), '{ln_esc}');
  setVal(document.querySelector('input[name="email"]'), '{email_esc}');
  setVal(document.querySelector('input[name="phone"]'), '{phone_esc}');
  setVal(document.querySelector('input[name="summary"]'), 'MERN Stack Web Developer');
  
  // Workable URLs
  setVal(document.querySelector('input[name="linkedin_url"]'), '{linkedin}');
  setVal(document.querySelector('input[name="github_url"]'), '{github}');
  
  console.log("%cAirohunt Autofill Complete!", "color: #10b981; font-weight: bold;");
}})();
""".strip()

        else:
            # Generic script looking for common input attributes
            return f"""
(() => {{
  console.log("%cAirohunt Autofill (Generic Platform)...", "color: #06b6d4; font-weight: bold;");
  
  const inputs = document.querySelectorAll('input, textarea');
  inputs.forEach(el => {{
    const id = (el.id || '').toLowerCase();
    const name = (el.name || '').toLowerCase();
    const label = (el.getAttribute('placeholder') || '').toLowerCase();
    
    const isField = (key) => id.includes(key) || name.includes(key) || label.includes(key);
    
    if (isField('first') && isField('name')) el.value = '{fn_esc}';
    else if (isField('last') && isField('name')) el.value = '{ln_esc}';
    else if (isField('email')) el.value = '{email_esc}';
    else if (isField('phone') || isField('mobile') || isField('contact')) el.value = '{phone_esc}';
    else if (isField('linkedin')) el.value = '{linkedin}';
    else if (isField('github')) el.value = '{github}';
    else if (isField('portfolio') || isField('website') || isField('homepage')) el.value = '{portfolio}';
    else if (isField('full') && isField('name')) el.value = '{name_esc}';
    
    el.dispatchEvent(new Event('input', {{ bubbles: true }}));
  }});
  console.log("%cAirohunt Autofill Complete!", "color: #10b981; font-weight: bold;");
}})();
""".strip()

    @staticmethod
    def prepare_application_payload(job: Job, profile: UserProfile) -> Dict[str, Any]:
        """
        Orchestrates classification, question detection, mapping, and script generation.
        """
        classification = ApplicationEngine.classify_url(job.url)
        platform = classification["platform"]
        support = classification["automation_support"]
        
        custom_questions = ApplicationEngine.detect_custom_questions(job.description)
        autofill_script = ApplicationEngine.generate_autofill_script(platform, profile, job.company)
        
        # Social links mapping
        name_parts = profile.name.split()
        first_name = name_parts[0] if name_parts else ""
        last_name = " ".join(name_parts[1:]) if len(name_parts) > 1 else ""
        
        linkedin = f"https://linkedin.com/in/{first_name.lower()}-{last_name.lower()}".replace(" ", "") if last_name else f"https://linkedin.com/in/{first_name.lower()}"
        github = f"https://github.com/{first_name.lower()}{last_name.lower()}".replace(" ", "") if last_name else f"https://github.com/{first_name.lower()}"
        portfolio = f"https://{first_name.lower()}{last_name.lower()}.vercel.app".replace(" ", "") if last_name else f"https://{first_name.lower()}.dev"

        return {
            "platform": platform,
            "automation_support": support,
            "mapped_fields": {
                "Full Name": profile.name,
                "Email": profile.email,
                "Phone": profile.phone,
                "LinkedIn": linkedin,
                "GitHub": github,
                "Portfolio": portfolio
            },
            "custom_questions": custom_questions,
            "autofill_script": autofill_script
        }
