import time
import asyncio
from typing import Dict

class TokenBucket:
    def __init__(self, capacity: int = 5, fill_rate: float = 2.0):
        self.capacity = capacity
        self.fill_rate = fill_rate  # Tokens added per second
        self.tokens = float(capacity)
        self.last_update = time.time()

    def acquire(self) -> bool:
        now = time.time()
        elapsed = now - self.last_update
        self.last_update = now
        self.tokens = min(self.capacity, self.tokens + elapsed * self.fill_rate)

        if self.tokens >= 1.0:
            self.tokens -= 1.0
            return True
        return False

class DomainRateLimiter:
    """Token Bucket rate limiter for managing domain-level request budgets."""
    def __init__(self, default_capacity: int = 5, fill_rate: float = 2.0):
        self.default_capacity = default_capacity
        self.fill_rate = fill_rate
        self.buckets: Dict[str, TokenBucket] = {}
        self._lock = asyncio.Lock()

    async def acquire_slot(self, domain: str, max_wait_seconds: float = 3.0) -> bool:
        domain_clean = domain.lower().strip()
        async with self._lock:
            if domain_clean not in self.buckets:
                self.buckets[domain_clean] = TokenBucket(self.default_capacity, self.fill_rate)

        bucket = self.buckets[domain_clean]
        start_time = time.time()

        while time.time() - start_time < max_wait_seconds:
            if bucket.acquire():
                return True
            await asyncio.sleep(0.1)

        return False

global_rate_limiter = DomainRateLimiter()
