from typing import Dict, Any, List
from database import AirohuntDatabase

class CareerMemoryOptimizer:
    """Analyzes historical application outcomes to compute dynamic score adjustments."""
    def __init__(self, db: AirohuntDatabase = None):
        self.db = db or AirohuntDatabase()

    def compute_source_conversion_rates(self) -> Dict[str, float]:
        app_data = self.db.get_application_queue_data()
        applications = app_data.get("applications", {})
        
        counts: Dict[str, Dict[str, int]] = {}
        for app in applications.values():
            src = app.get("source", "Search").lower()
            if src not in counts:
                counts[src] = {"applied": 0, "success": 0}
            counts[src]["applied"] += 1
            if app.get("status") in ("Interviewing", "Offered"):
                counts[src]["success"] += 1

        conversion_rates = {}
        for src, stat in counts.items():
            if stat["applied"] > 0:
                conversion_rates[src] = round(stat["success"] / stat["applied"], 2)
            else:
                conversion_rates[src] = 0.0

        return conversion_rates

    def get_dynamic_source_boost(self, source_name: str) -> float:
        rates = self.compute_source_conversion_rates()
        rate = rates.get(source_name.lower(), 0.0)
        # Boost jobs from sources with >20% interview conversion rate
        if rate >= 0.20:
            return 5.0
        elif rate > 0.0:
            return 2.0
        return 0.0

global_career_memory_optimizer = CareerMemoryOptimizer()
