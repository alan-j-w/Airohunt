from pydantic import BaseModel, Field
from typing import List, Optional

class UserProfile(BaseModel):
    name: str = ""
    email: str = ""
    phone: str = ""
    location: str = ""
    target_roles: List[str] = Field(default_factory=list)
    skills: List[str] = Field(default_factory=list)
    salary_expectation: Optional[int] = 0
    base_resume: str = ""
    
    # New Onboarding preferences
    experience_level: str = "Fresher" # Fresher, Experienced
    preferred_work_mode: str = "Remote" # Remote, Onsite, Hybrid, Any
    region: str = "Kerala"
    ai_instructions: str = ""
    
    # Validation engine fields
    preferred_company_types: List[str] = Field(default_factory=list)
    excluded_company_types: List[str] = Field(default_factory=list)
    global_rules: str = ""
    temporary_search_rules: str = ""

class Job(BaseModel):
    id: str
    title: str
    company: str
    location: str
    salary: str
    description: str
    skills_required: List[str] = Field(default_factory=list)
    url: str
    is_scam: bool = False
    scam_reason: Optional[str] = ""
    match_score: float = 0.0
    status: str = "Matched" # Matched, Applied, Interviewing, Offered, Rejected
    tailored_resume: Optional[str] = ""
    
    # New AI Scoring Breakdown
    scam_risk_score: int = 0
    tech_match_score: float = 0.0
    pref_match_score: float = 0.0
    trust_score: float = 0.0
    opportunity_score: float = 0.0
    recommendation_pros: List[str] = Field(default_factory=list)
    recommendation_cons: List[str] = Field(default_factory=list)
    ai_recommendation: str = ""
    evaluation_mode: str = "Local Heuristics"
    
    # New Company Research Assistant Fields
    company_summary: str = ""
    tech_stack: List[str] = Field(default_factory=list)
    hiring_signals: List[str] = Field(default_factory=list)
    trust_rating: str = "B"
    
    # Strict validation engine fields
    validation_tier: str = "B" # A, B, C, D
    validation_score: float = 0.0
    validation_confidence: float = 0.0
    validation_reasons: List[str] = Field(default_factory=list)
    validation_warnings: List[str] = Field(default_factory=list)
    rejection_reasons: List[str] = Field(default_factory=list)


class Pipeline(BaseModel):
    nodes: List[dict] = Field(default_factory=list)
    edges: List[dict] = Field(default_factory=list)

class AISettings(BaseModel):
    active_provider: str = "openai"
    openai_api_key: str = ""
    groq_api_key: str = ""
    gemini_api_key: str = ""
    ollama_url: str = "http://localhost:11434"
    
    # Provider sources toggles
    source_adzuna: bool = True
    source_jooble: bool = True
    source_manual_import: bool = False
    source_company_careers: bool = True
