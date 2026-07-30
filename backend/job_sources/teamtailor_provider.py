import httpx
import asyncio
from typing import List, Dict, Any
from job_sources.base_provider import BaseJobProvider
from job_sources.ats_directory_manager import TEAMTAILOR_COMPANIES

class TeamtailorJobProvider(BaseJobProvider):
    async def fetch_jobs(self, keywords: str, location: str, limit: int = 15) -> List[Dict[str, Any]]:
        jobs_out = []
        kw_lower = keywords.lower().strip()
        loc_lower = location.lower().strip()

        sem = asyncio.Semaphore(10)

        async def fetch_company(client: httpx.AsyncClient, company: str):
            async with sem:
                url = f"https://career.{company}.com/jobs.json"
                try:
                    resp = await client.get(url, timeout=6.0)
                    if resp.status_code == 200:
                        data = resp.json()
                        jobs = data.get("jobs", []) if isinstance(data, dict) else data
                        results = []
                        for j in jobs:
                            title = j.get("title", "")
                            job_loc = j.get("location", "Remote")
                            apply_url = j.get("url") or f"https://career.{company}.com/jobs/{j.get('id', '')}"

                            if kw_lower in title.lower() or kw_lower in str(job_loc).lower() or not kw_lower:
                                if "remote" in loc_lower or loc_lower in str(job_loc).lower() or not loc_lower:
                                    results.append({
                                        "title": title,
                                        "company": company.title(),
                                        "location": str(job_loc),
                                        "salary": "Not Specified",
                                        "description": f"Explore and apply for the {title} opportunity at {company.title()}.",
                                        "skills_required": [keywords.title()] if keywords else ["Development"],
                                        "url": apply_url
                                    })
                        return results
                except Exception:
                    return []
                return []

        try:
            async with httpx.AsyncClient() as client:
                tasks = [fetch_company(client, c) for c in TEAMTAILOR_COMPANIES]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                for res in results:
                    if isinstance(res, list):
                        jobs_out.extend(res)
        except Exception as e:
            print(f"Teamtailor fetch error: {e}")

        return jobs_out[:limit]
