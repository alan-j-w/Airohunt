import re
import os
import json
import httpx
import asyncio
from typing import List, Dict, Any
from job_sources.base_provider import BaseJobProvider

GREENHOUSE_BOARDS = ["gitlab", "figma", "vercel", "hashicorp", "stripe", "reddit", "openai", "scaleai"]
LEVER_BOARDS = ["lever", "hotjar", "vercel", "buffer", "mural"]
KERALA_STARTUPS_POOL = []

class CompanyCareersJobProvider(BaseJobProvider):
    async def fetch_jobs(self, keywords: str, location: str, limit: int = 15) -> List[Dict[str, Any]]:
        jobs_out = []
        kw_lower = keywords.lower().strip()
        loc_lower = location.lower().strip()
        
        async with httpx.AsyncClient(timeout=8.0, follow_redirects=True) as client:
            tasks = []
            
            # Greenhouse boards
            for board in GREENHOUSE_BOARDS:
                tasks.append(self._fetch_greenhouse(client, board, kw_lower, loc_lower))
                
            # Lever boards
            for board in LEVER_BOARDS:
                tasks.append(self._fetch_lever(client, board, kw_lower, loc_lower))
                
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for res in results:
                if isinstance(res, list):
                    jobs_out.extend(res)
                    
        # Sort and return up to limit
        return jobs_out[:limit]

    async def _fetch_greenhouse(self, client: httpx.AsyncClient, board: str, kw: str, loc: str) -> List[Dict[str, Any]]:
        jobs = []
        try:
            url = f"https://boards-api.greenhouse.io/v1/boards/{board}/jobs"
            resp = await client.get(url)
            if resp.status_code == 200:
                data = resp.json()
                for j in data.get("jobs", []):
                    title = j.get("title", "")
                    job_loc = j.get("location", {}).get("name", "Remote")
                    
                    # Match query
                    if kw in title.lower() or kw in job_loc.lower():
                        # Location check
                        if "remote" in loc or loc in job_loc.lower() or not loc:
                            jobs.append({
                                "title": title,
                                "company": board.title(),
                                "location": job_loc,
                                "salary": "Not Specified",
                                "description": f"View and apply for the {title} role at {board.title()}.",
                                "skills_required": [kw.title()] if kw else ["Development"],
                                "url": j.get("absolute_url", "")
                            })
        except Exception as e:
            print(f"Greenhouse fetch error for {board}: {e}")
        return jobs

    async def _fetch_lever(self, client: httpx.AsyncClient, board: str, kw: str, loc: str) -> List[Dict[str, Any]]:
        jobs = []
        try:
            url = f"https://api.lever.co/v0/postings/{board}"
            resp = await client.get(url)
            if resp.status_code == 200:
                data = resp.json()
                for j in data:
                    title = j.get("title", "")
                    job_loc = j.get("categories", {}).get("location", "Remote")
                    desc = j.get("descriptionPlain", "")
                    
                    if kw in title.lower() or kw in job_loc.lower():
                        if "remote" in loc or loc in job_loc.lower() or not loc:
                            jobs.append({
                                "title": title,
                                "company": board.title(),
                                "location": job_loc,
                                "salary": "Not Specified",
                                "description": desc[:400] + "...",
                                "skills_required": [kw.title()] if kw else ["Development"],
                                "url": j.get("hostedUrl", "")
                            })
        except Exception as e:
            print(f"Lever fetch error for {board}: {e}")
        return jobs
