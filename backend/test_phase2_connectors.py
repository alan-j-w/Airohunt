import asyncio
import os
import sys
import unittest

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from job_sources.ats_directory_manager import ATSDirectoryManager, global_ats_directory
from job_sources.workday_provider import WorkdayJobProvider
from job_sources.smartrecruiters_provider import SmartRecruitersJobProvider
from job_sources.breezy_provider import BreezyJobProvider
from job_sources.teamtailor_provider import TeamtailorJobProvider
from job_sources.company_careers_provider import CompanyCareersJobProvider

class TestPhase2Connectors(unittest.TestCase):
    def setUp(self):
        self.directory = global_ats_directory
        self.workday = WorkdayJobProvider()
        self.smartrecruiters = SmartRecruitersJobProvider()
        self.breezy = BreezyJobProvider()
        self.teamtailor = TeamtailorJobProvider()
        self.company_careers = CompanyCareersJobProvider()

    def test_ats_directory_indexing(self):
        counts = self.directory.get_all_counts()
        self.assertGreater(counts["greenhouse"], 40)
        self.assertGreater(counts["lever"], 25)
        self.assertGreater(counts["ashby"], 15)
        self.assertGreater(counts["workable"], 10)
        self.assertGreater(counts["workday"], 5)
        self.assertGreater(counts["smartrecruiters"], 5)
        self.assertGreater(counts["total_companies"], 100)
        print(f"✓ ATS Directory indexing passed ({counts['total_companies']} global company boards registered)")

    def test_workday_provider_execution(self):
        async def run_test():
            jobs = await self.workday.fetch_jobs("Engineer", "Remote", limit=5)
            self.assertIsInstance(jobs, list)
            for j in jobs:
                self.assertIn("title", j)
                self.assertIn("company", j)
                self.assertIn("url", j)
                self.assertTrue(j["url"].startswith("http"))
            return len(jobs)

        count = asyncio.run(run_test())
        print(f"✓ Workday ATS connector execution passed ({count} jobs returned)")

    def test_smartrecruiters_provider_execution(self):
        async def run_test():
            jobs = await self.smartrecruiters.fetch_jobs("Developer", "Remote", limit=5)
            self.assertIsInstance(jobs, list)
            for j in jobs:
                self.assertIn("title", j)
                self.assertIn("company", j)
                self.assertIn("url", j)
            return len(jobs)

        count = asyncio.run(run_test())
        print(f"✓ SmartRecruiters connector execution passed ({count} jobs returned)")

    def test_breezy_provider_execution(self):
        async def run_test():
            jobs = await self.breezy.fetch_jobs("Developer", "Remote", limit=5)
            self.assertIsInstance(jobs, list)
            return len(jobs)

        count = asyncio.run(run_test())
        print(f"✓ Breezy HR connector execution passed ({count} jobs returned)")

    def test_teamtailor_provider_execution(self):
        async def run_test():
            jobs = await self.teamtailor.fetch_jobs("Engineer", "Remote", limit=5)
            self.assertIsInstance(jobs, list)
            return len(jobs)

        count = asyncio.run(run_test())
        print(f"✓ Teamtailor connector execution passed ({count} jobs returned)")

    def test_expanded_company_careers_provider(self):
        async def run_test():
            jobs = await self.company_careers.fetch_jobs("React", "Remote", limit=10)
            self.assertIsInstance(jobs, list)
            return len(jobs)

        count = asyncio.run(run_test())
        print(f"✓ Expanded Company Careers provider execution passed ({count} jobs fetched across Greenhouse/Lever/Ashby/Workable)")

if __name__ == "__main__":
    unittest.main()
