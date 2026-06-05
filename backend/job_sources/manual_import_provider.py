import os
import json
from typing import List, Dict, Any
from job_sources.base_provider import BaseJobProvider

IMPORTED_JOBS_FILE = "imported_jobs.json"

class ManualImportJobProvider(BaseJobProvider):
    async def fetch_jobs(self, keywords: str, location: str, limit: int = 15) -> List[Dict[str, Any]]:
        if not os.path.exists(IMPORTED_JOBS_FILE):
            return []
            
        try:
            with open(IMPORTED_JOBS_FILE, "r") as f:
                jobs = json.load(f)
                
            # Filter based on keywords in memory
            kw = keywords.lower()
            filtered = []
            for j in jobs:
                if kw in j.get("title", "").lower() or kw in j.get("description", "").lower():
                    filtered.append({
                        "title": j.get("title", ""),
                        "company": j.get("company", "Imported Company"),
                        "location": j.get("location", "Remote"),
                        "salary": j.get("salary", "Not Specified"),
                        "description": j.get("description", ""),
                        "skills_required": j.get("skills_required", []),
                        "url": j.get("url", "http://localhost")
                    })
            return filtered[:limit]
        except Exception as e:
            print(f"Manual import provider error: {str(e)}")
            return []
