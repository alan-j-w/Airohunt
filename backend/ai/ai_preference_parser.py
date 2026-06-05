import re
import json
from ai.provider_manager import ProviderManager
from ai.prompt_templates import PREFERENCE_PARSER_SYSTEM, PREFERENCE_PARSER_USER

provider_manager = ProviderManager()

def parse_user_instructions_local(instructions: str) -> dict:
    # Heuristic regex backup parser
    inst_lower = instructions.lower()
    
    preferred_roles = []
    if "react" in inst_lower:
        preferred_roles.append("React Developer")
    if "django" in inst_lower:
        preferred_roles.append("Django Developer")
    if "mern" in inst_lower:
        preferred_roles.append("MERN Stack Developer")
    if "full stack" in inst_lower:
        preferred_roles.append("Full Stack Developer")
    if "python" in inst_lower and "django" not in inst_lower:
        preferred_roles.append("Python Developer")
        
    excluded = []
    if "training" in inst_lower or "course" in inst_lower:
        excluded.append("training institute")
    if "bond" in inst_lower:
        excluded.append("bond company")
    if "placement" in inst_lower:
        excluded.append("placement consultant")
        
    hiring_style = []
    if "project" in inst_lower or "assignment" in inst_lower:
        hiring_style.append("project review")
    if "no dsa" in inst_lower or "avoid dsa" in inst_lower:
        hiring_style.append("no-dsa")
        
    remote_pref = "Any"
    if "remote" in inst_lower:
        remote_pref = "Remote"
    elif "hybrid" in inst_lower:
        remote_pref = "Hybrid"
    elif "onsite" in inst_lower or "office" in inst_lower:
        remote_pref = "Onsite"
        
    # Guess min salary in LPA
    min_sal = 0
    salary_match = re.search(r'(\d+(\.\d+)?)\s*(lpa|lakh|l)', inst_lower)
    if salary_match:
        try:
            min_sal = float(salary_match.group(1))
        except ValueError:
            pass
            
    return {
        "preferred_roles": preferred_roles if preferred_roles else ["Software Engineer"],
        "excluded_company_types": excluded,
        "preferred_hiring_style": hiring_style,
        "min_salary_lpa": min_sal,
        "max_age_days": 14,
        "remote_preference": remote_pref
    }

async def parse_user_instructions(instructions: str) -> dict:
    if not instructions or not instructions.strip():
        return parse_user_instructions_local("")
        
    try:
        sys_prompt = PREFERENCE_PARSER_SYSTEM
        user_prompt = PREFERENCE_PARSER_USER.format(user_instructions=instructions)
        
        response_text = await provider_manager.call_llm(sys_prompt, user_prompt, response_format_json=True)
        
        # Clean potential markdown wrappers
        clean_text = response_text.strip()
        if clean_text.startswith("```json"):
            clean_text = clean_text[7:]
        if clean_text.endswith("```"):
            clean_text = clean_text[:-3]
            
        data = json.loads(clean_text.strip())
        return data
    except Exception as e:
        print(f"AI preference parsing failed, calling local parser fallback: {str(e)}")
        return parse_user_instructions_local(instructions)
