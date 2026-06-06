import urllib.request
import json
import os

def run_tests():
    print("Starting integration tests for Smart Dynamic Job Filters...")
    
    base_url = "http://127.0.0.1:8000"
    
    # 1. Test GET /api/filter-options
    print("\n--- Testing GET /api/filter-options ---")
    try:
        req = urllib.request.Request(f"{base_url}/api/filter-options", method="GET")
        with urllib.request.urlopen(req) as response:
            status = response.status
            body = response.read().decode('utf-8')
            print(f"Status Code: {status}")
            data = json.loads(body)
            print(f"Locations discovered: {data.get('locations')}")
            print(f"Company Types discovered: {data.get('company_types')}")
            print(f"Experience Levels discovered: {data.get('experience_levels')}")
            print(f"Sources discovered: {data.get('sources')}")
            
            assert "locations" in data, "Missing locations in response"
            assert "company_types" in data, "Missing company_types in response"
            assert "experience_levels" in data, "Missing experience_levels in response"
            assert "sources" in data, "Missing sources in response"
            print("GET /api/filter-options passed!")
    except Exception as e:
        print(f"FAILED: GET /api/filter-options with error {e}")
        return False
        
    # 2. Test POST /api/jobs/filter with default tiers A and B
    print("\n--- Testing POST /api/jobs/filter ---")
    # Read usage stats before request
    stats_file = "filter_usage_stats.json"
    initial_stats = {}
    if os.path.exists(stats_file):
        try:
            with open(stats_file, "r") as f:
                initial_stats = json.load(f)
        except Exception:
            pass

    filter_payload = {
        "locations": ["Remote"],
        "work_modes": ["Remote"],
        "company_types": [],
        "experience_levels": [],
        "tiers": ["A", "B"],
        "sources": [],
        "min_salary": None,
        "posted_within_days": None,
        "fresher_compatibility": "90%+"
    }
    
    try:
        req_data = json.dumps(filter_payload).encode('utf-8')
        req = urllib.request.Request(
            f"{base_url}/api/jobs/filter",
            data=req_data,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req) as response:
            status = response.status
            body = response.read().decode('utf-8')
            print(f"Status Code: {status}")
            jobs_data = json.loads(body)
            print(f"Received {len(jobs_data)} filtered jobs.")
            
            # Basic validation of returned structure
            if len(jobs_data) > 0:
                sample_job = jobs_data[0]
                assert "id" in sample_job, "Job missing ID"
                assert "title" in sample_job, "Job missing title"
                assert "company" in sample_job, "Job missing company"
                assert "validation_tier" in sample_job, "Job missing validation_tier"
                
                # Check that tier filtering actually worked
                for job in jobs_data:
                    assert job["validation_tier"] in ["A", "B"], f"Job validation tier {job['validation_tier']} was returned but expected only A or B"
            
            print("POST /api/jobs/filter response structure validated!")
    except Exception as e:
        print(f"FAILED: POST /api/jobs/filter with error {e}")
        return False
        
    # 3. Verify that stats are updated in filter_usage_stats.json
    print("\n--- Testing Filter Usage Stats Verification ---")
    if os.path.exists(stats_file):
        try:
            with open(stats_file, "r") as f:
                updated_stats = json.load(f)
                
            # Verify work_modes count increased
            initial_remote_modes = initial_stats.get("work_modes", {}).get("Remote", 0)
            updated_remote_modes = updated_stats.get("work_modes", {}).get("Remote", 0)
            print(f"Remote Work Mode clicks: {initial_remote_modes} -> {updated_remote_modes}")
            assert updated_remote_modes == initial_remote_modes + 1, "Work Mode stats count did not increment"
            
            # Verify tiers count increased
            for tier in ["A", "B"]:
                initial_tier = initial_stats.get("tiers", {}).get(tier, 0)
                updated_tier = updated_stats.get("tiers", {}).get(tier, 0)
                print(f"Tier {tier} clicks: {initial_tier} -> {updated_tier}")
                assert updated_tier == initial_tier + 1, f"Tier {tier} stats count did not increment"
                
            # Verify fresher compatibility click count increased
            initial_fc = initial_stats.get("fresher_compatibility_clicks", 0)
            updated_fc = updated_stats.get("fresher_compatibility_clicks", 0)
            print(f"Fresher Compatibility clicks: {initial_fc} -> {updated_fc}")
            assert updated_fc == initial_fc + 1, "Fresher compatibility stats count did not increment"
            
            print("Filter Usage Stats increment verification passed!")
        except Exception as e:
            print(f"FAILED: Usage Stats verification with error {e}")
            return False
    else:
        print("FAILED: filter_usage_stats.json does not exist!")
        return False
        
    print("\nAll integration tests passed successfully!")
    return True

if __name__ == "__main__":
    import sys
    success = run_tests()
    sys.exit(0 if success else 1)
