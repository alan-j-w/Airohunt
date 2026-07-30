import os
import json
import time
import random
from typing import List, Dict, Optional, Any

class ProxyHealth:
    def __init__(self, url: str):
        self.url = url
        self.success_count = 0
        self.fail_count = 0
        self.ban_count = 0
        self.last_used = 0.0
        self.cooldown_until = 0.0

    def mark_success(self):
        self.success_count += 1
        self.last_used = time.time()

    def mark_failure(self, is_ban: bool = False):
        self.fail_count += 1
        self.last_used = time.time()
        if is_ban:
            self.ban_count += 1
            # Cooldown proxy for 5 minutes if banned
            self.cooldown_until = time.time() + 300.0
        else:
            self.cooldown_until = time.time() + 30.0

    def is_available(self) -> bool:
        return time.time() >= self.cooldown_until

class ProxyManager:
    """Manages proxy rotation pool, health tracking, and ban detection."""
    def __init__(self):
        self._proxies: Dict[str, ProxyHealth] = {}
        self._load_proxies()
        self._rr_index = 0

    def _load_proxies(self):
        proxy_env = os.getenv("PROXY_LIST", "").strip()
        proxy_urls = []
        if proxy_env:
            if proxy_env.startswith("["):
                try:
                    proxy_urls = json.loads(proxy_env)
                except Exception:
                    proxy_urls = [p.strip() for p in proxy_env.split(",") if p.strip()]
            else:
                proxy_urls = [p.strip() for p in proxy_env.split(",") if p.strip()]

        for url in proxy_urls:
            self._proxies[url] = ProxyHealth(url)

    def add_proxy(self, url: str):
        if url and url not in self._proxies:
            self._proxies[url] = ProxyHealth(url)

    def get_next_proxy(self) -> Optional[str]:
        available = [ph for ph in self._proxies.values() if ph.is_available()]
        if not available:
            return None
        selected = available[self._rr_index % len(available)]
        self._rr_index = (self._rr_index + 1) % len(available)
        return selected.url

    def report_status(self, proxy_url: str, status_code: int, response_text: str = ""):
        if not proxy_url or proxy_url not in self._proxies:
            return
        ph = self._proxies[proxy_url]
        is_ban = status_code in (403, 429, 503) or "cloudflare" in response_text.lower() or "attention required" in response_text.lower()
        if 200 <= status_code < 400:
            ph.mark_success()
        else:
            ph.mark_failure(is_ban=is_ban)

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_proxies": len(self._proxies),
            "available_proxies": sum(1 for ph in self._proxies.values() if ph.is_available()),
            "banned_proxies": sum(1 for ph in self._proxies.values() if ph.ban_count > 0)
        }

global_proxy_manager = ProxyManager()
