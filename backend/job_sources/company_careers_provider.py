import re
import os
import json
import httpx
import asyncio
from typing import List, Dict, Any
from job_sources.base_provider import BaseJobProvider

GREENHOUSE_BOARDS = [
    "gitlab", "figma", "vercel", "hashicorp", "stripe", "reddit", "openai", "scaleai",
    "cloudera", "datadog", "doordash", "dropbox", "elastic", "github", "hubspot",
    "instacart", "launchdarkly", "lyft", "mongodb", "netflix", "okta",
    "pinterest", "plaid", "postman", "roblox", "segment", "slack", "snowflake",
    "squarespace", "twilio", "unity", "zoom"
]

LEVER_BOARDS = [
    "lever", "hotjar", "vercel", "buffer", "mural", "figma", "asana", "box",
    "deliveryhero", "docker", "framer", "medium", "miro", "palantir", "quizlet",
    "revolut", "shopify", "snyk", "stackoverflow", "udacity", "wealthfront", "yelp"
]

ASHBY_BOARDS = [
    "linear", "clerk", "replicate", "perplexity", "devcycle", "humeai", "sandbar",
    "retool", "calcom", "chronosphere", "dopt", "gatus"
]

WORKABLE_BOARDS = [
    "huggingface", "cypress", "taxfix", "toptal", "deliveroo", "skyscanner", "contentful", "moderne",
    "charliehr", "careem", "starlingbank"
]

KERALA_STARTUPS_POOL = []

class CompanyCareersJobProvider(BaseJobProvider):
    async def fetch_jobs(self, keywords: str, location: str, limit: int = 15) -> List[Dict[str, Any]]:
        jobs_out = []
        kw_lower = keywords.lower().strip()
        loc_lower = location.lower().strip()
        
        # Concurrency control: max 15 concurrent HTTP requests to prevent connection exhaustion
        sem = asyncio.Semaphore(15)
        
        async def sem_fetch(fetch_fn, *args):
            async with sem:
                return await fetch_fn(*args)
        
        async with httpx.AsyncClient(timeout=8.0, follow_redirects=True) as client:
            tasks = []
            
            # Greenhouse boards
            for board in GREENHOUSE_BOARDS:
                tasks.append(sem_fetch(self._fetch_greenhouse, client, board, kw_lower, loc_lower))
                
            # Lever boards
            for board in LEVER_BOARDS:
                tasks.append(sem_fetch(self._fetch_lever, client, board, kw_lower, loc_lower))
                
            # Ashby boards
            for board in ASHBY_BOARDS:
                tasks.append(sem_fetch(self._fetch_ashby, client, board, kw_lower, loc_lower))
                
            # Workable boards
            for board in WORKABLE_BOARDS:
                tasks.append(sem_fetch(self._fetch_workable, client, board, kw_lower, loc_lower))
                
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for res in results:
                if isinstance(res, list):
                    jobs_out.extend(res)
                    
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
                    
                    if kw in title.lower() or kw in job_loc.lower():
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

    async def _fetch_ashby(self, client: httpx.AsyncClient, board: str, kw: str, loc: str) -> List[Dict[str, Any]]:
        jobs = []
        try:
            url = f"https://api.ashbyhq.com/posting-api/job-board/{board}"
            resp = await client.get(url)
            if resp.status_code == 200:
                data = resp.json()
                for j in data.get("jobs", []):
                    title = j.get("title", "")
                    job_loc = j.get("location", "Remote")
                    desc = j.get("descriptionPlain", "")
                    
                    if kw in title.lower() or kw in job_loc.lower() or kw in desc.lower():
                        if "remote" in loc or loc in job_loc.lower() or not loc:
                            jobs.append({
                                "title": title,
                                "company": board.title(),
                                "location": job_loc,
                                "salary": "Not Specified",
                                "description": desc[:400] + "..." if desc else f"View and apply for the {title} role at {board.title()}.",
                                "skills_required": [kw.title()] if kw else ["Development"],
                                "url": j.get("applyUrl") or j.get("jobUrl") or f"https://jobs.ashbyhq.com/{board}/{j.get('id')}"
                            })
        except Exception as e:
            print(f"Ashby fetch error for {board}: {e}")
        return jobs

    async def _fetch_workable(self, client: httpx.AsyncClient, board: str, kw: str, loc: str) -> List[Dict[str, Any]]:
        jobs = []
        try:
            url = f"https://apply.workable.com/api/v1/widget/accounts/{board}?details=true"
            resp = await client.get(url)
            if resp.status_code == 200:
                data = resp.json()
                for j in data.get("jobs", []):
                    title = j.get("title", "")
                    country = j.get("country", "")
                    city = j.get("city", "")
                    state = j.get("state", "")
                    workplace = j.get("telecommuting", False)
                    
                    job_loc = ", ".join([p for p in [city, state, country] if p]) or "Remote"
                    if workplace:
                        job_loc = f"{job_loc} (Remote)"
                        
                    raw_desc = j.get("description", "")
                    clean_desc = re.sub(r'<[^>]*>', ' ', raw_desc)
                    clean_desc = " ".join(clean_desc.split())
                    
                    if kw in title.lower() or kw in job_loc.lower() or kw in clean_desc.lower():
                        if "remote" in loc or loc in job_loc.lower() or not loc:
                            jobs.append({
                                "title": title,
                                "company": board.title(),
                                "location": job_loc,
                                "salary": "Not Specified",
                                "description": clean_desc[:400] + "..." if clean_desc else f"View and apply for the {title} role at {board.title()}.",
                                "skills_required": [kw.title()] if kw else ["Development"],
                                "url": j.get("url") or j.get("shortlink") or f"https://apply.workable.com/{board}/j/{j.get('shortcode')}"
                            })
        except Exception as e:
            print(f"Workable fetch error for {board}: {e}")
        return jobs

