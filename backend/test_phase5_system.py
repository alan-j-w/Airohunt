import unittest
import os
import sys

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from health_monitor import global_health_monitor
from metrics_collector import global_metrics_collector
from rate_limiter import global_rate_limiter
from search_analytics import global_search_analytics
from db_maintenance import global_db_maintenance
from ai.career_memory_optimizer import global_career_memory_optimizer
from ats_auto_discover import global_ats_discoverer
from benchmark_scraper import global_benchmark_suite

class TestPhase5System(unittest.TestCase):
    def test_health_monitor(self):
        diag = global_health_monitor.get_full_diagnostics()
        self.assertIn("status", diag)
        self.assertIn("database", diag)
        print(f"✓ Health monitor diagnostics passed (System status: {diag['status']})")

    def test_metrics_collector(self):
        global_metrics_collector.record_provider_latency("workday", 150.0, True)
        global_metrics_collector.record_provider_latency("workday", 200.0, False)
        summary = global_metrics_collector.get_summary()
        self.assertGreater(len(summary), 0)
        print("✓ Provider metrics collector test passed")

    def test_ats_auto_discovery(self):
        ats1 = global_ats_discoverer.detect_ats_from_url("https://boards.greenhouse.io/stripe/jobs/1")
        ats2 = global_ats_discoverer.detect_ats_from_url("https://jobs.lever.co/vercel/2")
        ats3 = global_ats_discoverer.detect_ats_from_url("https://company.myworkdayjobs.com/wday/cxs/company/site/jobs")
        
        self.assertEqual(ats1, "greenhouse")
        self.assertEqual(ats2, "lever")
        self.assertEqual(ats3, "workday")
        print("✓ ATS auto-discovery crawler test passed")

    def test_search_analytics(self):
        global_search_analytics.record_search("React Developer", "Remote", 15)
        top = global_search_analytics.get_top_searches()
        self.assertGreater(top["total_searches"], 0)
        print("✓ Search analytics tracking test passed")

    def test_benchmark_suite(self):
        res = global_benchmark_suite.benchmark_deduplication(50)
        self.assertGreater(res["throughput_jobs_per_sec"], 0.0)
        print(f"✓ Scraper benchmark test passed ({res['throughput_jobs_per_sec']} jobs/sec)")

if __name__ == "__main__":
    unittest.main()
