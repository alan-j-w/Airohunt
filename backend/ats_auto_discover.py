import re
from typing import Dict, Any

ATS_SIGNATURES = {
    "greenhouse": [r'boards\.greenhouse\.io', r'greenhouse-api', r'gh_jid'],
    "lever": [r'jobs\.lever\.co', r'lever-api'],
    "ashby": [r'jobs\.ashbyhq\.com', r'ashbyhq'],
    "workable": [r'apply\.workable\.com', r'workable'],
    "workday": [r'myworkdayjobs\.com', r'/wday/cxs/'],
    "smartrecruiters": [r'jobs\.smartrecruiters\.com', r'smartrecruiters'],
    "breezy": [r'breezy\.hr', r'breezy-content'],
    "teamtailor": [r'teamtailor\.com', r'career\..*\.com/jobs']
}

class ATSAutoDiscoveryCrawler:
    """Auto-detects underlying ATS platform from company career URL or HTML signatures."""
    def detect_ats_from_url(self, url: str) -> str:
        if not url:
            return "UNKNOWN"
        url_lower = url.lower()
        for ats_name, patterns in ATS_SIGNATURES.items():
            for pat in patterns:
                if re.search(pat, url_lower):
                    return ats_name
        return "UNKNOWN"

    def detect_ats_from_html(self, html: str) -> str:
        if not html:
            return "UNKNOWN"
        html_lower = html.lower()
        for ats_name, patterns in ATS_SIGNATURES.items():
            for pat in patterns:
                if re.search(pat, html_lower):
                    return ats_name
        return "UNKNOWN"

global_ats_discoverer = ATSAutoDiscoveryCrawler()
