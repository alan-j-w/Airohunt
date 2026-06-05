import sys
import os
import json
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

from models import Job, UserProfile
from ai.strict_job_validator import StrictJobValidationEngine, deduplicate_jobs

def test_experience_penalties():
    profile = UserProfile(
        name="Test User",
        target_roles=["React Developer"],
        skills=["React", "Node.js"],
        experience_level="Fresher",  # Candidate max target: 0 years
        salary_expectation=0
    )
    validator = StrictJobValidationEngine(profile)

    # 1. 0 years exp (Fresher) -> no experience penalty (expect 15/15)
    fresher_job = Job(
        id="j1", title="React Developer", company="Startup Corp", location="Remote",
        salary="10 LPA", description="Looking for a fresher React Developer.", url="https://greenhouse.io/startup/jobs/1",
        skills_required=["React"]
    )
    validated_fresher = validator.validate_job(fresher_job)
    print(f"Fresher Job Validation Score: {validated_fresher.validation_score}, Tier: {validated_fresher.validation_tier}, Warnings: {validated_fresher.validation_warnings}")
    assert validated_fresher.validation_tier in ["A", "B"]

    # 2. 1 year experience (+1 above target) -> -15 points penalty
    one_yr_job = Job(
        id="j2", title="React Developer", company="Startup Corp", location="Remote",
        salary="10 LPA", description="Looking for a React Developer with 1 year experience.", url="https://greenhouse.io/startup/jobs/2",
        skills_required=["React"]
    )
    validated_one = validator.validate_job(one_yr_job)
    print(f"1 Year Exp Job Validation Score: {validated_one.validation_score}, Tier: {validated_one.validation_tier}, Warnings: {validated_one.validation_warnings}")
    assert any("experience slightly above preference" in w.lower() for w in validated_one.validation_warnings)

    # 3. 3 years experience (+3 above target) -> -30 points penalty
    three_yr_job = Job(
        id="j3", title="React Developer", company="Startup Corp", location="Remote",
        salary="10 LPA", description="Looking for a React Developer with 3 years of experience.", url="https://greenhouse.io/startup/jobs/3",
        skills_required=["React"]
    )
    validated_three = validator.validate_job(three_yr_job)
    print(f"3 Year Exp Job Validation Score: {validated_three.validation_score}, Tier: {validated_three.validation_tier}, Warnings: {validated_three.validation_warnings}")
    assert any("experience requirements exceed preference" in w.lower() for w in validated_three.validation_warnings)

    # 4. 5+ years experience (+5 above target) -> Hard reject Tier D
    five_yr_job = Job(
        id="j4", title="Senior React Developer", company="Startup Corp", location="Remote",
        salary="10 LPA", description="Looking for a Senior React Developer with 5+ years of experience.", url="https://greenhouse.io/startup/jobs/4",
        skills_required=["React"]
    )
    validated_five = validator.validate_job(five_yr_job)
    print(f"5 Year Exp Job Validation Score: {validated_five.validation_score}, Tier: {validated_five.validation_tier}, Rejections: {validated_five.rejection_reasons}")
    assert validated_five.validation_tier == "D"
    assert "Experience Too High" in validated_five.rejection_reasons


def test_hard_reject_gates():
    profile = UserProfile(
        name="Test User",
        target_roles=["React Developer"],
        skills=["React"],
        experience_level="Fresher"
    )
    validator = StrictJobValidationEngine(profile)

    # Scam
    scam_job = Job(
        id="s1", title="React Developer", company="Startup Corp", location="Remote",
        salary="10 LPA", description="React Developer", url="https://greenhouse.io/startup/jobs/scam",
        is_scam=True
    )
    v_scam = validator.validate_job(scam_job)
    assert v_scam.validation_tier == "D"
    assert "Potential Scam Indicators" in v_scam.rejection_reasons

    # Training institute keywords
    training_job = Job(
        id="t1", title="React Developer Trainee", company="Brototype", location="Remote",
        salary="10 LPA", description="Pay to join our course and get placement", url="https://greenhouse.io/startup/jobs/training"
    )
    v_training = validator.validate_job(training_job)
    assert v_training.validation_tier == "D"
    assert "Company Blacklist" in v_training.rejection_reasons or "Training Institute" in v_training.rejection_reasons


def test_deduplication():
    # Duplicate jobs
    jobs = [
        Job(id="d1", title="React Developer", company="Google", location="Remote", salary="Not Specified", description="Nice job", url="https://jooble.org/google-job"),
        Job(id="d2", title="React Developer", company="Google", location="Remote", salary="Not Specified", description="Nice job", url="https://greenhouse.io/google/jobs/1"),
        Job(id="d3", title="React Developer", company="Google", location="Remote", salary="Not Specified", description="Nice job", url="https://adzuna.com/google-job")
    ]
    
    deduped, removed_count = deduplicate_jobs(jobs)
    print(f"Deduplicated count: {len(deduped)}, removed: {removed_count}")
    assert len(deduped) == 1
    assert removed_count == 2
    # The greenhouse URL is rank 4, while jooble/adzuna are rank 1. It should keep greenhouse version
    assert "greenhouse.io" in deduped[0].url

if __name__ == "__main__":
    print("Running Airohunt strict validator tests...")
    test_experience_penalties()
    test_hard_reject_gates()
    test_deduplication()
    print("All tests passed successfully!")
