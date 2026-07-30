import re
from typing import Dict, Any, List

VISA_SPONSORSHIP_POSITIVE = [
    r'visa sponsorship (?:offered|available|provided|supported)',
    r'h-?1b (?:sponsorship|transfer|eligible)',
    r'eu blue card',
    r'uk skilled worker visa',
    r'stem opt (?:eligible|accepted)',
    r'sponsorship (?:is|available)'
]

VISA_SPONSORSHIP_NEGATIVE = [
    r'no visa sponsorship',
    r'cannot sponsor visas',
    r'must be legally authorized to work',
    r'us citizen or permanent resident only',
    r'no h-?1b'
]

TIMEZONE_PATTERNS = [
    (r'(?:est|edt|cst|cdt|mst|mdt|pst|pdt)\s*\+?-\s*\d+\s*hrs?', "US_TIMEZONE_RANGE"),
    (r'emea\s*(?:timezone|hours|region)', "EMEA"),
    (r'apac\s*(?:timezone|hours|region)', "APAC"),
    (r'latam\s*(?:timezone|hours|region)', "LATAM"),
    (r'work from anywhere|global remote|anywhere in the world', "GLOBAL_REMOTE"),
    (r'us remote only|must reside in the us', "US_ONLY")
]

class GlobalMetadataEngine:
    """
    Extracts global visa sponsorship, work authorization, and timezone constraints from job descriptions.
    """
    def extract_visa_sponsorship(self, text: str) -> Dict[str, Any]:
        t_lower = text.lower()
        offered = False
        prohibited = False

        for pat in VISA_SPONSORSHIP_POSITIVE:
            if re.search(pat, t_lower):
                offered = True
                break

        for pat in VISA_SPONSORSHIP_NEGATIVE:
            if re.search(pat, t_lower):
                prohibited = True
                break

        sponsorship_status = "UNKNOWN"
        if offered and not prohibited:
            sponsorship_status = "OFFERED"
        elif prohibited:
            sponsorship_status = "NOT_OFFERED"

        return {
            "sponsorship_offered": offered and not prohibited,
            "sponsorship_status": sponsorship_status,
            "requires_work_auth": prohibited
        }

    def extract_timezone_constraints(self, text: str) -> List[str]:
        t_lower = text.lower()
        constraints = []
        for pat, tag in TIMEZONE_PATTERNS:
            if re.search(pat, t_lower):
                constraints.append(tag)
        return constraints

    def extract_all_metadata(self, text: str) -> Dict[str, Any]:
        visa_info = self.extract_visa_sponsorship(text)
        tz_info = self.extract_timezone_constraints(text)
        return {
            **visa_info,
            "timezone_constraints": tz_info
        }

global_metadata_engine = GlobalMetadataEngine()
