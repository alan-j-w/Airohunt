import asyncio
import os
import sys
import unittest

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from models import Job, UserProfile
from database import AirohuntDatabase
from ai.deduplication_engine import (
    MultiStageDeduplicator,
    clean_canonical_url,
    compute_url_hash,
    compute_minhash_signature,
    calculate_minhash_jaccard,
    deduplicate_jobs_multi_stage
)
from async_queue import AsyncJobTaskQueue, global_job_task_queue

class TestPhase1Pipeline(unittest.TestCase):
    def setUp(self):
        self.db = AirohuntDatabase()
        self.dedup_engine = MultiStageDeduplicator()

    def test_canonical_url_cleaning(self):
        url1 = "https://boards.greenhouse.io/stripe/jobs/12345?utm_source=linkedin&ref=referrer&gh_jid=12345"
        url2 = "https://boards.greenhouse.io/stripe/jobs/12345"
        clean1 = clean_canonical_url(url1)
        clean2 = clean_canonical_url(url2)
        self.assertEqual(clean1, clean2)
        self.assertEqual(compute_url_hash(url1), compute_url_hash(url2))
        print("✓ Canonical URL cleaning & hashing test passed")

    def test_minhash_jaccard_similarity(self):
        desc1 = "We are hiring a Senior React Developer to join our frontend team in San Francisco. Requirements: 5+ years React, Redux, TypeScript."
        desc2 = "We are hiring a Senior React Developer to join our frontend team in San Francisco. Requirements: 5+ years React, Redux, TypeScript! Apply now."
        desc_different = "Looking for a Data Scientist with Python, PyTorch, SQL, and machine learning experience."

        sig1 = compute_minhash_signature(desc1)
        sig2 = compute_minhash_signature(desc2)
        sig_diff = compute_minhash_signature(desc_different)

        sim_similar = calculate_minhash_jaccard(sig1, sig2)
        sim_diff = calculate_minhash_jaccard(sig1, sig_diff)

        self.assertGreaterEqual(sim_similar, 0.75)
        self.assertLess(sim_diff, 0.30)
        print(f"✓ MinHash Jaccard similarity test passed (Similar: {sim_similar:.2f}, Different: {sim_diff:.2f})")

    def test_multi_stage_deduplication(self):
        job1 = Job(
            id="j1", title="React Developer", company="Stripe", location="Remote",
            salary="$120k", description="Senior React Engineer position at Stripe. Requirements: React, Node.",
            url="https://boards.greenhouse.io/stripe/jobs/1?utm_source=adzuna"
        )
        job2 = Job(
            id="j2", title="React Developer (Remote)", company="Stripe", location="Remote",
            salary="$120k", description="Senior React Engineer position at Stripe. Requirements: React, Node.",
            url="https://adzuna.com/redirect/999?utm_source=adzuna"
        )
        job3 = Job(
            id="j3", title="Python Backend Engineer", company="Vercel", location="Remote",
            salary="$140k", description="Building next gen serverless infrastructure with Python and FastAPI.",
            url="https://jobs.lever.co/vercel/2"
        )

        raw_jobs = [job1, job2, job3]
        deduped, removed = deduplicate_jobs_multi_stage(raw_jobs)
        self.assertEqual(len(deduped), 2)
        self.assertEqual(removed, 1)
        self.assertEqual(deduped[0].id, "j1")  # Higher rank source (Greenhouse > Adzuna)
        print("✓ Multi-stage deduplication test passed")

    def test_database_fingerprint_and_batch_upsert(self):
        job = Job(
            id="test_db_j1", title="Full Stack Developer", company="Figma", location="Remote",
            salary="$150k", description="Figma is hiring a Full Stack Developer.",
            url="https://boards.greenhouse.io/figma/jobs/99"
        )
        
        # Test bulk upsert
        self.db.bulk_upsert_jobs([job])
        
        # Test save fingerprint
        url_h = compute_url_hash(job.url)
        minhash_sig = compute_minhash_signature(job.description)
        self.db.save_job_fingerprint(job.id, url_h, "figma:fullstackdeveloper", minhash_sig)
        
        fingerprints = self.db.get_job_fingerprints()
        self.assertTrue(any(f["job_id"] == "test_db_j1" for f in fingerprints))
        print("✓ Database indexing & fingerprint persistence test passed")

    def test_async_job_task_queue(self):
        queue = AsyncJobTaskQueue()

        async def sample_scraping_worker(task_id: str, count: int):
            for i in range(1, count + 1):
                await asyncio.sleep(0.01)
                queue.update_progress(task_id, (i / count) * 100, f"Processed {i}/{count}")
            return {"scraped_count": count}

        async def run_async_test():
            task = queue.dispatch_background_task("Test Scrape", sample_scraping_worker, 5)
            self.assertEqual(task.status, "RUNNING")
            
            # Wait for completion
            await task._asyncio_task
            
            self.assertEqual(task.status, "COMPLETED")
            self.assertEqual(task.progress, 100.0)
            self.assertEqual(task.result, {"scraped_count": 5})

        asyncio.run(run_async_test())
        print("✓ Async job task queue test passed")

if __name__ == "__main__":
    unittest.main()
