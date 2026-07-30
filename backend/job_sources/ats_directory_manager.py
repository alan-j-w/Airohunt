from typing import Dict, List, Any

# Expanded global company career board directory categorized by ATS engine
GREENHOUSE_BOARDS = [
    "gitlab", "figma", "vercel", "hashicorp", "stripe", "reddit", "openai", "scaleai",
    "cloudera", "datadog", "doordash", "dropbox", "elastic", "github", "hubspot",
    "instacart", "launchdarkly", "lyft", "mongodb", "netflix", "okta",
    "pinterest", "plaid", "postman", "roblox", "segment", "slack", "snowflake",
    "squarespace", "twilio", "unity", "zoom", "airbnb", "canva", "coinbase",
    "coursera", "databrick", "discord", "duolingo", "grammarly", "notion", "patreon",
    "ramp", "robinhood", "roblox", "snap", "spotify", "uber", "webflow", "zapier"
]

LEVER_BOARDS = [
    "lever", "hotjar", "vercel", "buffer", "mural", "figma", "asana", "box",
    "deliveryhero", "docker", "framer", "medium", "miro", "palantir", "quizlet",
    "revolut", "shopify", "snyk", "stackoverflow", "udacity", "wealthfront", "yelp",
    "atlassian", "bitpanda", "klarna", "n26", "personio", "transferwise", "vimeo"
]

ASHBY_BOARDS = [
    "linear", "clerk", "replicate", "perplexity", "devcycle", "humeai", "sandbar",
    "retool", "calcom", "chronosphere", "dopt", "gatus", "langchain", "pinecone",
    "resend", "supabase", "sentry", "togetherai", "vapi"
]

WORKABLE_BOARDS = [
    "huggingface", "cypress", "taxfix", "toptal", "deliveroo", "skyscanner", "contentful", "moderne",
    "charliehr", "careem", "starlingbank", "invision", "typeform", "unbabel"
]

WORKDAY_TENANTS = [
    {"company": "Adobe", "tenant": "adobe", "site": "external_careers"},
    {"company": "Salesforce", "tenant": "salesforce", "site": "External_Careers"},
    {"company": "Nvidia", "tenant": "nvidia", "site": "NVIDIAExternalCareerSite"},
    {"company": "Workday", "tenant": "workday", "site": "Workday"},
    {"company": "Walmart", "tenant": "walmart", "site": "WalmartExternal"},
    {"company": "Target", "tenant": "target", "site": "TargetCareers"},
    {"company": "Siemens", "tenant": "siemens", "site": "SiemensCareers"},
    {"company": "Dell", "tenant": "dell", "site": "DellCareers"}
]

SMARTRECRUITERS_COMPANIES = [
    "Visa", "Ubisoft", "BoschGroup", "Square", "LinkedIn", "AveryDennison",
    "SGS", "PublicisGroupe", "Equinix", "Check24"
]

BREEZY_COMPANIES = [
    "carrd", "framer", "screenstudio", "raycast", "arcbrowser", "superhuman"
]

TEAMTAILOR_COMPANIES = [
    "epidemicsound", "krisiun", "mentimeter", "kry", "bonnier", "storytel"
]

class ATSDirectoryManager:
    """Manages multi-ATS company board registries and lookup indices."""
    def __init__(self):
        self.greenhouse = GREENHOUSE_BOARDS
        self.lever = LEVER_BOARDS
        self.ashby = ASHBY_BOARDS
        self.workable = WORKABLE_BOARDS
        self.workday = WORKDAY_TENANTS
        self.smartrecruiters = SMARTRECRUITERS_COMPANIES
        self.breezy = BREEZY_COMPANIES
        self.teamtailor = TEAMTAILOR_COMPANIES

    def get_all_counts(self) -> Dict[str, int]:
        return {
            "greenhouse": len(self.greenhouse),
            "lever": len(self.lever),
            "ashby": len(self.ashby),
            "workable": len(self.workable),
            "workday": len(self.workday),
            "smartrecruiters": len(self.smartrecruiters),
            "breezy": len(self.breezy),
            "teamtailor": len(self.teamtailor),
            "total_companies": (
                len(self.greenhouse) + len(self.lever) + len(self.ashby) +
                len(self.workable) + len(self.workday) + len(self.smartrecruiters) +
                len(self.breezy) + len(self.teamtailor)
            )
        }

global_ats_directory = ATSDirectoryManager()
