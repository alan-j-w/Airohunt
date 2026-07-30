import httpx
import asyncio
from typing import Dict, Any, List
from database import AirohuntDatabase
from models import Job

class JobExpiryChecker:
    """Background engine checking URL health and flagging expired job listings."""
    def __init__(self, db: AirohuntDatabase = None):
        self.db = db or AirohuntDatabase()

    async def verify_job_url(self, url: str) -> Dict[str, Any]:
        if not url:
            return {"is_live": False, "status_code": 0, "reason": "Empty URL"}
        try:
            async with httpx.AsyncClient(follow_redirects=True, verify=False, timeout=5.0) as client:
                resp = await client.head(url, headers={"User-Agent": "Mozilla/5.0"})
                if resp.status_code in (404, 410):
                    return {"is_live": False, "status_code": resp.status_code, "reason": "Posting Removed"}
                elif resp.status_code == 200:
                    return {"is_live": True, "status_code": 200, "reason": "Active"}
                
                # Fallback to GET if HEAD failed
                resp_get = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
                if resp_get.status_code in (404, 410):
                    return {"is_live": False, "status_code": resp_get.status_code, "reason": "Posting Removed"}
                return {"is_live": resp_get.status_code < 400, "status_code": resp_get.status_code, "reason": "HTTP Response"}
        except Exception as e:
            return {"is_live": True, "status_code": 0, "reason": f"Network Check Exception: {str(e)}"}

    async def batch_check_jobs(self, jobs: List[Job]) -> List[Dict[str, Any]]:
        results = []
        for job in jobs:
            res = await self.verify_job_url(job.url)
            res["job_id"] = job.id
            res["title"] = job.title
            res["company"] = job.company
            results.append(res)
        return results

global_job_expiry_checker = JobExpiryChecker()
