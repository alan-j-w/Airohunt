import os
import re
import uuid
from datetime import datetime
from typing import List, Tuple, Dict, Any
from models import Job, UserProfile
from utils import load_json_file, save_json_file
from geo_utils import get_state_from_city

# Filenames for local persistence
BLACKLIST_FILE = "company_blacklist.json"
STATS_FILE = "validation_stats.json"
HISTORY_FILE = "validation_history.json"

class StrictJobValidationEngine:
    def __init__(self, profile: UserProfile):
        self.profile = profile
        self.blacklist = self._load_blacklist()

    def _load_blacklist(self) -> List[str]:
        defaults = [
            "luminar", "brototype", "novotech", "suntech", 
            "placement india", "placement agency", "placement consultancy", 
            "recruitment agency", "job consulting", "career institute", 
            "training academy", "training institute", "course sellers", 
            "pay-to-join", "novosoft"
        ]
        data = load_json_file(BLACKLIST_FILE, defaults)
        if isinstance(data, list):
            return [item.lower().strip() for item in data]
        return [item.lower().strip() for item in defaults]

    def _parse_experience(self, job: Job) -> int:
        """Parses minimum years of experience required from title and description."""
        text = f"{job.title} {job.description}".lower()
        
        # Helper to check if a match is likely a false positive company age/history statement
        def is_false_positive(match_start: int, match_end: int) -> bool:
            start_window = max(0, match_start - 50)
            end_window = min(len(text), match_end + 50)
            window_text = text[start_window:end_window]
            history_indicators = [
                "years of history", "years in business", "years old", 
                "established", "founded", "company has", "track record of",
                "presence", "history in", "operating for"
            ]
            return any(ind in window_text for ind in history_indicators)
            
        # 1. Look for range e.g. "2-3 years" -> min is 2
        for match in re.finditer(r'\b(\d+)\s*(?:to|-)\s*(\d+)\s*years?\s*(?:of\s*)?experience\b|\b(\d+)\s*(?:to|-)\s*(\d+)\s*years?\b', text):
            if not is_false_positive(match.start(), match.end()):
                val = match.group(1) or match.group(3)
                return int(val)
                
        # 2. Look for "year(s) of experience" e.g. "1 year of experience"
        for match in re.finditer(r'\b(\d+)\s*years?\s*of\s*experience\b|\bexperience\s*:\s*(\d+)\s*years?\b|\brequired\s*experience\s*:\s*(\d+)\b', text):
            if not is_false_positive(match.start(), match.end()):
                val = match.group(1) or match.group(2) or match.group(3)
                return int(val)

        # 3. Look for "+ years" e.g. "5+ years"
        for match in re.finditer(r'\b(\d+)\s*\+?\s*years?\b', text):
            if not is_false_positive(match.start(), match.end()):
                start_w = max(0, match.start() - 30)
                end_w = min(len(text), match.end() + 30)
                sub_context = text[start_w:end_w]
                requirement_words = ["require", "need", "minimum", "at least", "experience", "work", "seeking", "looking for"]
                if any(w in sub_context for w in requirement_words):
                    return int(match.group(1))

        # 4. Check keywords indicating entry-level
        if any(kw in text for kw in ["fresher", "entry-level", "intern", "junior developer", "junior engineer"]):
            return 0

        # Default fallback
        return 0

    def _check_hard_rejects(self, job: Job) -> Tuple[bool, str]:
        """
        Runs the Universal Hard Reject checks.
        Returns (is_rejected, reason).
        """
        # 1. Known Scam Listings
        if job.is_scam:
            return True, "Potential Scam Indicators"

        # 2. Company Name Missing
        if not job.company or not job.company.strip() or job.company.lower() in ["unknown", "unknown company"]:
            return True, "Missing Company Name"

        # 3. Application URL Missing
        if not job.url or not job.url.strip() or job.url.lower() in ["", "https://", "http://"]:
            return True, "Missing Apply URL"

        # 4. Known Blacklisted Companies
        comp_lower = job.company.lower().strip()
        for black_item in self.blacklist:
            if black_item in comp_lower:
                return True, "Company Blacklist"

        # 5. Training/Pay-to-Join/Course keywords in company/description
        text_check = f"{job.company} {job.title} {job.description}".lower()
        pay_to_join_keywords = [
            "training fee", "course fee", "pay to join", "enrollment fee", 
            "certification fee", "purchase course", "security deposit",
            "bond company", "placement fee", "agency fee"
        ]
        for kw in pay_to_join_keywords:
            if kw in text_check:
                return True, "Training Institute"

        # 6. Experience hard reject for Freshers
        cand_level = self.profile.experience_level.lower().strip()
        if cand_level == "fresher":
            req_exp = self._parse_experience(job)
            if req_exp >= 2:
                return True, f"Experience Too High ({req_exp} yrs required)"
            
            title_lower = job.title.lower()
            senior_keywords = ["senior", "sr.", "sr ", "lead", "manager", "architect", "principal", "director", "head", "vp", "staff", "chief"]
            for kw in senior_keywords:
                pattern = r'\b' + re.escape(kw) + r'\b'
                if re.search(pattern, title_lower):
                    return True, f"Senior Level Role ({kw.title()})"

        return False, ""

    def validate_job(self, job: Job) -> Job:
        """
        Validates a single job. Calculates score, confidence, and assigns the validation tier.
        """
        rejection_reasons = []
        validation_reasons = []
        validation_warnings = []
        
        # 1. Run Hard Reject Check
        is_rejected, reject_reason = self._check_hard_rejects(job)
        if is_rejected:
            job.validation_score = 0.0
            job.validation_tier = "D"
            job.rejection_reasons = [reject_reason]
            job.validation_confidence = self._calculate_confidence(job)
            return job

        # 2. Score Calculation Components
        role_score, role_reasons = self._score_role_match(job)
        skill_score, skill_reasons = self._score_skill_match(job)
        loc_score, loc_reasons = self._score_location_match(job)
        exp_score, exp_reasons, exp_warns, exp_rejected = self._score_experience_match(job)
        sal_score, sal_reasons, sal_warns = self._score_salary_match(job)
        comp_score, comp_reasons, comp_warns = self._score_company_match(job)

        # Handle experience hard limit (5+ years above target)
        if exp_rejected:
            job.validation_score = 0.0
            job.validation_tier = "D"
            job.rejection_reasons = ["Experience Too High"]
            job.validation_confidence = self._calculate_confidence(job)
            return job

        # Accumulate scores
        base_score = role_score + skill_score + loc_score + exp_score + sal_score + comp_score
        
        # Add Source Quality Match boost (+5 pts max)
        source_quality_boost = self._get_source_quality_boost(job)
        final_score = min(100.0, base_score + source_quality_boost)

        # Apply Global Rules and Temporary Search Rules (Heuristic local keyword match)
        rule_passed, rule_warns, rule_rejects = self._apply_custom_rules(job)
        if not rule_passed:
            job.validation_score = 0.0
            job.validation_tier = "D"
            job.rejection_reasons = rule_rejects
            job.validation_confidence = self._calculate_confidence(job)
            return job

        # Compile reasons and warnings
        validation_reasons.extend(role_reasons + skill_reasons + loc_reasons + exp_reasons + sal_reasons + comp_reasons)
        if source_quality_boost > 0:
            validation_reasons.append("✓ Direct Application Source")
            
        validation_warnings.extend(exp_warns + sal_warns + comp_warns + rule_warns)

        # Update Job model
        job.validation_score = round(final_score, 1)
        job.validation_confidence = self._calculate_confidence(job)
        job.validation_reasons = validation_reasons
        job.validation_warnings = validation_warnings
        job.rejection_reasons = []

        # Classify into Tiers
        if final_score >= 90.0:
            job.validation_tier = "A"
        elif final_score >= 75.0:
            job.validation_tier = "B"
        elif final_score >= 60.0:
            job.validation_tier = "C"
        else:
            job.validation_tier = "D"
            job.rejection_reasons = ["Low Validation Score"]

        return job

    # Scoring helper functions

    def _score_role_match(self, job: Job) -> Tuple[float, List[str]]:
        score = 0.0
        reasons = []
        title_lower = job.title.lower()
        
        if not self.profile.target_roles:
            return 25.0, ["✓ Default Role Match"]
            
        matched_roles = []
        for role in self.profile.target_roles:
            if role.lower().strip() in title_lower:
                matched_roles.append(role)
                
        if matched_roles:
            score = 25.0
            reasons.append(f"✓ Target Role Match ({matched_roles[0]})")
        else:
            # Partial match
            score = 10.0
            reasons.append("⚠ Secondary Role Match")
            
        return score, reasons

    def _score_skill_match(self, job: Job) -> Tuple[float, List[str]]:
        score = 0.0
        reasons = []
        
        if not self.profile.skills:
            return 20.0, ["✓ Default Skill Match"]
            
        desc_lower = job.description.lower()
        matched_skills = []
        
        for skill in self.profile.skills:
            # Word boundary check for skills
            pattern = r'\b' + re.escape(skill.lower()) + r'\b'
            if re.search(pattern, desc_lower) or any(s.lower() == skill.lower() for s in job.skills_required):
                matched_skills.append(skill)
                
        total_skills = len(self.profile.skills)
        match_ratio = len(matched_skills) / max(total_skills, 1)
        
        if len(matched_skills) >= 3 or match_ratio >= 0.5:
            score = 20.0
            reasons.append(f"✓ Strong Skill Alignment ({len(matched_skills)} matched)")
        elif len(matched_skills) >= 1:
            score = 12.0
            reasons.append(f"✓ Partial Skill Alignment ({len(matched_skills)} matched)")
        else:
            score = 5.0
            reasons.append("⚠ Low Skill Match")
            
        return score, reasons

    def _score_location_match(self, job: Job) -> Tuple[float, List[str]]:
        score = 0.0
        reasons = []
        
        job_loc = job.location.lower()
        pref_work = self.profile.preferred_work_mode.lower()
        pref_region = self.profile.region.lower() if self.profile.region else ""
        
        is_job_remote = "remote" in job_loc or "work from home" in job_loc
        
        # Work mode checks
        work_mode_match = False
        if pref_work == "any" or pref_work == "":
            work_mode_match = True
        elif pref_work == "remote" and is_job_remote:
            work_mode_match = True
        elif pref_work in ["onsite", "hybrid"] and not is_job_remote:
            work_mode_match = True
            
        # Region checks
        region_match = False
        if not pref_region:
            region_match = True
        elif pref_region in job_loc:
            region_match = True
        else:
            resolved_state = get_state_from_city(job.location)
            if resolved_state and resolved_state.lower() in pref_region:
                region_match = True
            
        if work_mode_match and region_match:
            score = 15.0
            reasons.append("✓ Location & Work Mode Match")
        elif work_mode_match or is_job_remote:
            score = 10.0
            reasons.append("✓ Partial Work Mode Match")
        else:
            score = 5.0
            
        return score, reasons


    def _score_experience_match(self, job: Job) -> Tuple[float, List[str], List[str], bool]:
        """
        Returns (score, reasons, warnings, is_hard_rejected)
        """
        score = 15.0
        reasons = []
        warnings = []
        
        req_exp = self._parse_experience(job)
        cand_level = self.profile.experience_level.lower()
        
        # User max target experience based on profile experience_level
        target_exp = 0 if cand_level == "fresher" else 3
        
        if req_exp <= target_exp:
            reasons.append("✓ Experience Match")
            return 15.0, reasons, warnings, False
            
        diff = req_exp - target_exp
        
        # 1. 5+ years above target -> Hard Reject (Tier D)
        if diff >= 5:
            return 0.0, [], [], True
            
        # 2. 2-3 years above target -> Heavy Penalty -30 pts
        if diff >= 2:
            score = max(0.0, score - 30.0)
            warnings.append("⚠ Experience requirements exceed preference (-30 pts)")
            reasons.append("⚠ Experience Above Target")
            
        # 3. 0-1 years above target -> Penalty -15 pts
        else:
            score = max(0.0, score - 15.0)
            warnings.append("⚠ Experience slightly above preference (-15 pts)")
            reasons.append("⚠ Experience Slightly Above Target")
            
        return score, reasons, warnings, False

    def _score_salary_match(self, job: Job) -> Tuple[float, List[str], List[str]]:
        score = 10.0
        reasons = []
        warnings = []
        
        expectation = self.profile.salary_expectation or 0
        if expectation <= 0:
            return 10.0, ["✓ Salary Match (No Expectation)"], []
            
        sal_str = job.salary.lower()
        if "not specified" in sal_str or not sal_str.strip():
            # Undisclosed salary gets 5 points and a warning
            warnings.append("⚠ Salary Undisclosed")
            return 5.0, [], warnings
            
        # Extract numbers from salary
        numbers = [float(n) for n in re.findall(r'\d+(?:\.\d+)?', sal_str.replace(',', ''))]
        if not numbers:
            warnings.append("⚠ Salary Format Unrecognized")
            return 5.0, [], warnings
            
        val = numbers[0]
        # Check if LPA (multiply by 100k) or USD
        is_lpa = "lpa" in sal_str or "lakh" in sal_str or "l" in sal_str or "₹" in job.salary
        is_monthly = "month" in sal_str or "/mo" in sal_str or "pm" in sal_str
        
        annual_val = val
        if is_lpa:
            # Convert LPA to USD (approx divide by 83, multiply by 100k)
            annual_val = (val * 100000.0) / 83.0
        elif is_monthly:
            annual_val = val * 12
            
        if annual_val >= expectation:
            reasons.append("✓ Meets Salary Expectation")
            score = 10.0
        else:
            warnings.append("⚠ Salary below expectation")
            score = 2.0
            
        return score, reasons, warnings

    def _score_company_match(self, job: Job) -> Tuple[float, List[str], List[str]]:
        score = 10.0 # base
        reasons = []
        warnings = []
        
        comp_lower = job.company.lower()
        desc_lower = job.description.lower()
        
        # Preferred Check
        matched_pref = []
        for pref in self.profile.preferred_company_types:
            if pref.lower().strip() in comp_lower or pref.lower().strip() in desc_lower:
                matched_pref.append(pref)
                
        # Excluded Check
        matched_ex = []
        for ex in self.profile.excluded_company_types:
            if ex.lower().strip() in comp_lower or ex.lower().strip() in desc_lower:
                matched_ex.append(ex)
                
        if matched_ex:
            score = 0.0
            warnings.append(f"⚠ Matches Excluded Company Type: {matched_ex[0]}")
        elif matched_pref:
            score = 15.0
            reasons.append(f"✓ Preferred Company Type: {matched_pref[0]}")
        else:
            score = 10.0
            
        return score, reasons, warnings

    def _get_source_quality_boost(self, job: Job) -> float:
        """Calculates a quality score based on source type (+5 boost max)."""
        url = job.url.lower()
        
        # Direct Greenhouse, Lever, Ashby, Workable, direct careers urls
        if any(keyword in url for keyword in ["greenhouse.io", "lever.co", "ashbyhq.com", "workable.com", "careers", "hiring"]):
            return 5.0
        elif "jooble" in url:
            return 2.0
        elif "adzuna" in url:
            return 1.0
        return 0.0

    def _calculate_confidence(self, job: Job) -> float:
        """
        Confidence formula:
        Salary listed: +30
        Detailed description length: +40
        Company name/summary available: +30
        """
        confidence = 0.0
        
        # 1. Salary listed
        sal_str = job.salary.lower()
        if "not specified" not in sal_str and sal_str.strip():
            confidence += 30.0
            
        # 2. Description length
        desc_len = len(job.description)
        if desc_len > 300:
            confidence += 40.0
        elif desc_len > 150:
            confidence += 20.0
            
        # 3. Company name/info
        if job.company and job.company.lower() not in ["unknown", "unknown company"]:
            confidence += 30.0
            
        return confidence

    def _apply_custom_rules(self, job: Job) -> Tuple[bool, List[str], List[str]]:
        """
        Applies Global Rules and Temporary Search Rules locally.
        Returns (passed, warnings, rejection_reasons)
        """
        passed = True
        warnings = []
        rejections = []
        
        rules_text = f"{self.profile.global_rules} {self.profile.temporary_search_rules}".lower()
        text_check = f"{job.title} {job.company} {job.description}".lower()
        
        # Local keyword extraction checks from user instructions
        # If rules contain "no X" or "avoid X" or "exclude X"
        negative_patterns = [
            r'no\s+([\w\s\-\.\#]+)',
            r'avoid\s+([\w\s\-\.\#]+)',
            r'exclude\s+([\w\s\-\.\#]+)',
            r'dont\s+want\s+([\w\s\-\.\#]+)',
            r'don\'t\s+want\s+([\w\s\-\.\#]+)'
        ]
        
        for pattern in negative_patterns:
            matches = re.findall(pattern, rules_text)
            for match in matches:
                keyword = match.split('\n')[0].split(',')[0].strip()
                if len(keyword) > 2 and keyword in text_check:
                    passed = False
                    rejections.append(f"Violates Rule: Avoid '{keyword}'")
                    
        return passed, warnings, rejections


def rank_duplicate_sources(job: Job) -> int:
    """Assigns a quality rank to duplicate postings. Direct urls > aggregators."""
    url = job.url.lower()
    if any(k in url for k in ["greenhouse.io", "lever.co", "ashbyhq.com", "workable.com"]):
        return 4
    if "careers" in url:
        return 3
    if "jooble" in url or "adzuna" in url:
        return 1
    return 2

def deduplicate_jobs(jobs: List[Job]) -> Tuple[List[Job], int]:
    """
    Groups jobs by (title, company) and retains the one with the highest quality source.
    Returns (deduplicated_jobs, duplicates_removed_count).
    """
    grouped: Dict[Tuple[str, str], List[Job]] = {}
    for job in jobs:
        key = (job.title.lower().strip(), job.company.lower().strip())
        if key not in grouped:
            grouped[key] = []
        grouped[key].append(job)
        
    deduplicated = []
    removed_count = 0
    
    for key, job_list in grouped.items():
        if len(job_list) == 1:
            deduplicated.append(job_list[0])
        else:
            # Sort by rank descending, then match score descending
            job_list.sort(key=lambda x: (rank_duplicate_sources(x), x.match_score), reverse=True)
            deduplicated.append(job_list[0])
            removed_count += len(job_list) - 1
            
    return deduplicated, removed_count


def update_validation_stats(all_collected: List[Job], active_jobs: List[Job], duplicates_removed: int):
    """
    Compiles batch stats, updates validation_stats.json, and appends to validation_history.json.
    """
    # Categorize raw data
    tier_a = sum(1 for j in all_collected if j.validation_tier == "A")
    tier_b = sum(1 for j in all_collected if j.validation_tier == "B")
    tier_c = sum(1 for j in all_collected if j.validation_tier == "C")
    tier_d = sum(1 for j in all_collected if j.validation_tier == "D")
    
    scams = sum(1 for j in all_collected if j.is_scam)
    
    # Analyze failure reasons
    rejections_count = {
        "Scam Detected": scams,
        "Company Blacklist": 0,
        "Training Institute": 0,
        "Experience Too High": 0,
        "Missing Company Name": 0,
        "Missing Apply URL": 0,
        "Low Skill Match": 0,
        "Low Validation Score": 0
    }
    
    for job in all_collected:
        if job.validation_tier == "D":
            for reason in job.rejection_reasons:
                if reason in rejections_count:
                    rejections_count[reason] += 1
                else:
                    rejections_count[reason] = rejections_count.get(reason, 0) + 1
                    
    # Read/Initialize stats
    default_stats = {
        "jobs_collected": 0,
        "jobs_rejected": 0,
        "jobs_displayed": 0,
        "duplicates_removed": 0,
        "scams_blocked": 0,
        "training_institutes_blocked": 0,
        "experience_rejected": 0,
        "rejection_categories": {}
    }
    
    current_stats = load_json_file(STATS_FILE, default_stats)
            
    # Add new counts
    current_stats["jobs_collected"] += len(all_collected) + duplicates_removed
    current_stats["jobs_rejected"] += tier_d
    current_stats["jobs_displayed"] += (tier_a + tier_b + tier_c)
    current_stats["duplicates_removed"] += duplicates_removed
    current_stats["scams_blocked"] += scams
    current_stats["training_institutes_blocked"] += rejections_count.get("Training Institute", 0)
    current_stats["experience_rejected"] += rejections_count.get("Experience Too High", 0)
    
    # Merge rejection reason counts
    rej_cats = current_stats.get("rejection_categories", {})
    for key, val in rejections_count.items():
        rej_cats[key] = rej_cats.get(key, 0) + val
    current_stats["rejection_categories"] = rej_cats
    
    # Sort and pick top failure reasons
    sorted_rejections = sorted(rej_cats.items(), key=lambda x: x[1], reverse=True)
    current_stats["top_failure_reasons"] = [{"reason": r, "count": c} for r, c in sorted_rejections[:5]]
    
    save_json_file(STATS_FILE, current_stats)
        
    # Append to History
    history_entry = {
        "timestamp": datetime.now().isoformat(),
        "collected": len(all_collected) + duplicates_removed,
        "displayed": tier_a + tier_b + tier_c,
        "tier_a": tier_a,
        "tier_b": tier_b,
        "tier_c": tier_c,
        "tier_d": tier_d,
        "duplicates_removed": duplicates_removed,
        "scams_blocked": scams,
        "training_institutes_blocked": rejections_count.get("Training Institute", 0),
        "experience_rejected": rejections_count.get("Experience Too High", 0)
    }
    
    history_list = load_json_file(HISTORY_FILE, [])
    if not isinstance(history_list, list):
        history_list = []
            
    history_list.append(history_entry)
    save_json_file(HISTORY_FILE, history_list)
