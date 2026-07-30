import time
from typing import Dict, Any, List
from models import Job
from ai.deduplication_engine import deduplicate_jobs_multi_stage

class ScraperBenchmarkSuite:
    """Benchmarking suite to measure deduplication throughput and processing latency."""
    def benchmark_deduplication(self, sample_size: int = 200) -> Dict[str, Any]:
        sample_jobs = []
        for i in range(sample_size):
            comp = f"Company_{i % 20}"
            title = f"Software Engineer {i % 5}"
            url = f"https://boards.greenhouse.io/{comp.lower()}/jobs/{i}?utm_source=test"
            desc = f"Looking for a Software Engineer at {comp}. Skills required: Python, React, AWS."
            sample_jobs.append(Job(
                id=f"bm_j_{i}", title=title, company=comp, location="Remote",
                salary="$120k", description=desc, url=url
            ))

        start_time = time.time()
        deduped, removed = deduplicate_jobs_multi_stage(sample_jobs)
        duration = time.time() - start_time
        throughput = round(sample_size / duration, 2) if duration > 0 else 0.0

        return {
            "sample_size": sample_size,
            "duration_seconds": round(duration, 4),
            "throughput_jobs_per_sec": throughput,
            "deduplicated_count": len(deduped),
            "duplicates_removed": removed
        }

global_benchmark_suite = ScraperBenchmarkSuite()
