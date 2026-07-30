import os
import json
from typing import Dict, Any, List
from datetime import datetime
from utils import load_json_file, save_json_file

STATS_FILE = "filter_usage_stats.json"

class SearchAnalyticsTracker:
    """Tracks search query volume, location trends, and role demand."""
    def __init__(self, stats_file: str = STATS_FILE):
        self.stats_file = stats_file

    def record_search(self, keyword: str, location: str, result_count: int):
        data = load_json_file(self.stats_file, {
            "total_searches": 0,
            "keywords": {},
            "locations": {},
            "last_searched": None
        })

        kw_clean = keyword.lower().strip() if keyword else "all"
        loc_clean = location.lower().strip() if location else "all"

        data["total_searches"] = data.get("total_searches", 0) + 1
        data["keywords"][kw_clean] = data.get("keywords", {}).get(kw_clean, 0) + 1
        data["locations"][loc_clean] = data.get("locations", {}).get(loc_clean, 0) + 1
        data["last_searched"] = datetime.utcnow().isoformat()

        save_json_file(self.stats_file, data)

    def get_top_searches(self, top_n: int = 5) -> Dict[str, Any]:
        data = load_json_file(self.stats_file, {
            "total_searches": 0,
            "keywords": {},
            "locations": {}
        })

        top_kw = sorted(data.get("keywords", {}).items(), key=lambda x: x[1], reverse=True)[:top_n]
        top_loc = sorted(data.get("locations", {}).items(), key=lambda x: x[1], reverse=True)[:top_n]

        return {
            "total_searches": data.get("total_searches", 0),
            "top_keywords": dict(top_kw),
            "top_locations": dict(top_loc)
        }

global_search_analytics = SearchAnalyticsTracker()
