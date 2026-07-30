import httpx
import asyncio
import random
import time
from typing import Dict, Any, Optional
from urllib.parse import urlparse
from stealth_headers import get_random_stealth_headers
from proxy_manager import global_proxy_manager, ProxyManager

class StealthHTTPClient:
    """
    High-resilience HTTP client wrapper with stealth header rotation,
    proxy rotation, exponential backoff retries, and domain rate-limiting.
    """
    def __init__(
        self,
        proxy_manager: Optional[ProxyManager] = None,
        max_retries: int = 3,
        timeout: float = 8.0,
        domain_min_interval: float = 0.2
    ):
        self.proxy_manager = proxy_manager or global_proxy_manager
        self.max_retries = max_retries
        self.timeout = timeout
        self.domain_min_interval = domain_min_interval
        self._domain_last_request: Dict[str, float] = {}
        self._lock = asyncio.Lock()

    async def _enforce_domain_rate_limit(self, url: str):
        try:
            domain = urlparse(url).netloc.lower()
        except Exception:
            return
        async with self._lock:
            now = time.time()
            last = self._domain_last_request.get(domain, 0.0)
            elapsed = now - last
            if elapsed < self.domain_min_interval:
                await asyncio.sleep(self.domain_min_interval - elapsed)
            self._domain_last_request[domain] = time.time()

    async def get(self, url: str, params: Dict[str, Any] = None, headers: Dict[str, str] = None, timeout: float = None) -> httpx.Response:
        return await self._request("GET", url, params=params, headers=headers, timeout=timeout)

    async def post(self, url: str, json: Any = None, data: Any = None, headers: Dict[str, str] = None, timeout: float = None) -> httpx.Response:
        return await self._request("POST", url, json=json, data=data, headers=headers, timeout=timeout)

    async def _request(self, method: str, url: str, params: Dict[str, Any] = None, json: Any = None, data: Any = None, headers: Dict[str, str] = None, timeout: float = None) -> httpx.Response:
        req_timeout = timeout or self.timeout
        last_exception = None

        for attempt in range(1, self.max_retries + 1):
            await self._enforce_domain_rate_limit(url)
            
            # Prepare stealth headers
            request_headers = get_random_stealth_headers()
            if headers:
                request_headers.update(headers)

            # Select proxy if available
            proxy_url = self.proxy_manager.get_next_proxy()
            client_kwargs = {
                "follow_redirects": True,
                "timeout": req_timeout,
                "verify": False
            }
            if proxy_url:
                client_kwargs["proxies"] = proxy_url

            try:
                async with httpx.AsyncClient(**client_kwargs) as client:
                    if method.upper() == "GET":
                        resp = await client.get(url, params=params, headers=request_headers)
                    else:
                        resp = await client.post(url, json=json, data=data, headers=request_headers)

                    # Report status to ProxyManager
                    if proxy_url:
                        self.proxy_manager.report_status(proxy_url, resp.status_code, resp.text)

                    # Retry on rate-limiting or server errors
                    if resp.status_code in (429, 502, 503, 504) and attempt < self.max_retries:
                        backoff = (2 ** attempt) + random.uniform(0.1, 0.5)
                        await asyncio.sleep(backoff)
                        continue

                    return resp

            except (httpx.TimeoutException, httpx.NetworkError, httpx.HTTPError) as e:
                last_exception = e
                if proxy_url:
                    self.proxy_manager.report_status(proxy_url, 599, str(e))
                if attempt < self.max_retries:
                    backoff = (2 ** attempt) + random.uniform(0.1, 0.5)
                    await asyncio.sleep(backoff)
                else:
                    raise last_exception

        raise last_exception or httpx.HTTPError(f"Failed request after {self.max_retries} attempts")

global_stealth_client = StealthHTTPClient()
