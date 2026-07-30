import httpx
import asyncio
from typing import List, Dict, Any
from job_sources.base_provider import BaseJobProvider
from job_sources.ats_directory_manager import WORKDAY_TENANTS

class WorkdayJobProvider(BaseJobProvider):
    async def fetch_jobs(self, keywords: str, location: str, limit: int = 15) -> List[Dict[str, Any]]:
        jobs_out = []
        kw_lower = keywords.lower().strip()
        loc_lower = location.lower().strip()

        sem = asyncio.Semaphore(10)

        async def fetch_tenant(client: httpx.AsyncClient, tenant_info: Dict[str, str]):
            async with sem:
                company = tenant_info["company"]
                tenant = tenant_info["tenant"]
                site = tenant_info["site"]
                url = f"https://{tenant}.wd1.myworkdayjobs.com/wday/cxs/{tenant}/{site}/jobs"

                payload = {
                    "appliedFacets": {},
                    "limit": 20,
                    "offset": 0,
                    "searchText": keywords
                }

                try:
                    resp = await client.post(url, json=payload, headers={
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                        "Accept": "application/json"
                    }, timeout=6.0)

                    if resp.status_code == 200:
                        data = resp.json()
                        postings = data.get("jobPostings", [])
                        results = []
                        for j in postings:
                            title = j.get("title", "")
                            job_loc = j.get("location", "Remote")
                            external_path = j.get("externalPath", "")
                            full_url = f"https://{tenant}.wd1.myworkdayjobs.com/en-US/{site}{external_path}"

                            if kw_lower in title.lower() or kw_lower in job_loc.lower() or not kw_lower:
                                if "remote" in loc_lower or loc_lower in job_loc.lower() or not loc_lower:
                                    results.append({
                                        "title": title,
                                        "company": company,
                                        "location": job_loc,
                                        "salary": "Not Specified",
                                        "description": f"Apply for the {title} opportunity at {company} via Workday portal.",
                                        "skills_required": [keywords.title()] if keywords else ["Enterprise Software"],
                                        "url": full_url
                                    })
                        return results
                except Exception:
                    return []
                return []

        try:
            async with httpx.AsyncClient(follow_redirects=True) as client:
                tasks = [fetch_tenant(client, t) for t in WORKDAY_TENANTS]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                for res in results:
                    if isinstance(res, list):
                        jobs_out.extend(res)
        except Exception as e:
            print(f"Workday fetch error: {e}")

        return jobs_out[:limit]
