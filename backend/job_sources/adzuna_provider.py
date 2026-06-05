import os
import httpx
from typing import List, Dict, Any
from job_sources.base_provider import BaseJobProvider

class AdzunaJobProvider(BaseJobProvider):
    async def fetch_jobs(self, keywords: str, location: str, limit: int = 15) -> List[Dict[str, Any]]:
        adzuna_app_id = os.getenv("ADZUNA_APP_ID", "")
        adzuna_app_key = os.getenv("ADZUNA_APP_KEY", "")
        
        if not adzuna_app_id or not adzuna_app_key:
            return []
            
        jobs_out = []
        try:
            url = "https://api.adzuna.com/v1/api/jobs/us/search/1"
            params = {
                "app_id": adzuna_app_id,
                "app_key": adzuna_app_key,
                "results_per_page": limit,
                "what": keywords,
                "where": location,
                "content-type": "application/json"
            }
            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params, timeout=10.0)
                if response.status_code == 200:
                    data = response.json()
                    results = data.get("results", [])
                    for item in results:
                        sal_min = item.get("salary_min", "")
                        sal_max = item.get("salary_max", "")
                        salary_str = "Not Specified"
                        if sal_min and sal_max:
                            salary_str = f"${int(sal_min):,} - ${int(sal_max):,}"
                        elif sal_min:
                            salary_str = f"${int(sal_min):,}+"

                        jobs_out.append({
                            "title": item.get("title", ""),
                            "company": item.get("company", {}).get("display_name", "Unknown Company"),
                            "location": item.get("location", {}).get("display_name", "Remote"),
                            "salary": salary_str,
                            "description": item.get("description", ""),
                            "skills_required": [keywords] if keywords else ["Development"],
                            "url": item.get("redirect_url", "https://adzuna.com")
                        })
        except Exception as e:
            print(f"Adzuna provider error: {str(e)}")
            
        return jobs_out
