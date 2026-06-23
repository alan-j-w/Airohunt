import os
import httpx
from typing import List, Dict, Any
from job_sources.base_provider import BaseJobProvider

class JoobleJobProvider(BaseJobProvider):
    async def fetch_jobs(self, keywords: str, location: str, limit: int = 15) -> List[Dict[str, Any]]:
        jooble_api_key = os.getenv("JOOBLE_API_KEY", "")
        
        if not jooble_api_key:
            return []
            
        jobs_out = []
        try:
            url = f"https://jooble.org/api/{jooble_api_key}"
            payload = {
                "keywords": keywords,
                "location": location
            }
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=payload, timeout=10.0)
                if response.status_code == 200:
                    data = response.json()
                    jobs = data.get("jobs", [])
                    for item in jobs[:limit]:
                        jobs_out.append({
                            "title": item.get("title", ""),
                            "company": item.get("company", "Unknown Company"),
                            "location": item.get("location", "Remote"),
                            "salary": item.get("salary", "Not Specified"),
                            "description": item.get("snippet", ""),
                            "skills_required": [keywords],
                            "url": item.get("link", "https://jooble.org")
                        })
        except Exception as e:
            print(f"Jooble provider error: {str(e)}")
            
        return jobs_out
