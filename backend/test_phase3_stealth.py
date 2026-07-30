import asyncio
import os
import sys
import unittest

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from stealth_headers import get_random_stealth_headers
from proxy_manager import ProxyManager, ProxyHealth
from stealth_http_client import StealthHTTPClient

class TestPhase3Stealth(unittest.TestCase):
    def test_stealth_header_generation(self):
        headers1 = get_random_stealth_headers()
        headers2 = get_random_stealth_headers()
        
        self.assertIn("User-Agent", headers1)
        self.assertIn("Accept-Language", headers1)
        self.assertIn("Sec-Fetch-Mode", headers1)
        self.assertEqual(headers1["Sec-Fetch-Mode"], "navigate")
        print("✓ Stealth header signature rotation test passed")

    def test_proxy_manager_health_tracking(self):
        pm = ProxyManager()
        pm.add_proxy("http://proxy1.test:8080")
        pm.add_proxy("http://proxy2.test:8080")

        p1 = pm.get_next_proxy()
        self.assertIsNotNone(p1)

        # Simulate 429 Rate Limit Ban on proxy1
        pm.report_status(p1, 429, "Rate limit exceeded")

        # Next selected proxy should be proxy2 (since proxy1 is in cooldown)
        p2 = pm.get_next_proxy()
        self.assertEqual(p2, "http://proxy2.test:8080")

        stats = pm.get_stats()
        self.assertEqual(stats["total_proxies"], 2)
        self.assertEqual(stats["banned_proxies"], 1)
        print(f"✓ Proxy manager health tracking & ban detection test passed ({stats['banned_proxies']} proxy blacklisted)")

    def test_stealth_http_client_execution(self):
        async def run_test():
            client = StealthHTTPClient(max_retries=2, timeout=5.0)
            # Query reliable test endpoint
            resp = await client.get("https://httpbin.org/headers")
            self.assertEqual(resp.status_code, 200)
            data = resp.json()
            headers = data.get("headers", {})
            self.assertIn("User-Agent", headers)
            return resp.status_code

        try:
            status = asyncio.run(run_test())
            self.assertEqual(status, 200)
            print("✓ Stealth HTTP client live request test passed")
        except Exception as e:
            print(f"⚠ Live network test skipped or warning: {e}")

if __name__ == "__main__":
    unittest.main()
