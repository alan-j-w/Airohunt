import httpx
import asyncio
from typing import List, Dict, Any
from job_sources.base_provider import BaseJobProvider
from job_sources.ats_directory_manager import SMARTRECRUITERS_COMPANIES

class SmartRecruitersJobProvider(BaseJobProvider):
    async def fetch_jobs(self, keywords: str, location: str, limit: int = 15) -> List[Dict[str, Any]]:
        jobs_out = []
        kw_lower = keywords.lower().strip()
        loc_lower = location.lower().strip()

        sem = asyncio.Semaphore(10)

        async def fetch_company(client: httpx.AsyncClient, company: str):
            async with sem:
                url = f"https://api.smartrecruiters.com/v1/companies/{company}/postings"
                params = {"q": keywords, "limit": 20}
                try:
                    resp = await client.get(url, params=params, timeout=6.0)
                    if resp.status_code == 200:
                        data = resp.json()
                        postings = data.get("content", [])
                        results = []
                        for j in postings:
                            title = j.get("name", "")
                            location_obj = j.get("location", {})
                            city = location_obj.get("city", "")
                            country = location_obj.get("country", "")
                            job_loc = f"{city}, {country}".strip(", ") if city else country or "Remote"
                            job_id = j.get("id", "")
                            apply_url = f"https://jobs.smartrecruiters.com/{company}/{job_id}"

                            if kw_lower in title.lower() or kw_lower in job_loc.lower() or not kw_lower:
                                if "remote" in loc_lower or loc_lower in job_loc.lower() or not loc_lower:
                                    results.append({
                                        "title": title,
                                        "company": company.title(),
                                        "location": job_loc,
                                        "salary": "Not Specified",
                                        "description": f"Apply for the {title} position at {company.title()} on SmartRecruiters.",
                                        "skills_required": [keywords.title()] if keywords else ["Development"],
                                        "url": apply_url
                                    })
                        return results
                except Exception:
                    return []
                return []

        try:
            async with httpx.AsyncClient() as client:
                tasks = [fetch_company(client, c) for c in SMARTRECRUITERS_COMPANIES]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                for res in results:
                    if isinstance(res, list):
                        jobs_out.extend(res)
        except Exception as e:
            print(f"SmartRecruiters fetch error: {e}")

        return jobs_out[:limit]
