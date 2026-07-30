import os
import shutil
import sqlite3
from typing import Dict, Any
from database import DB_FILE
from proxy_manager import global_proxy_manager
from async_queue import global_job_task_queue

class HealthMonitor:
    """System health check and diagnostic provider for Airohunt backend."""
    def __init__(self, db_path: str = DB_FILE):
        self.db_path = db_path

    def check_database(self) -> Dict[str, Any]:
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT count(*) FROM jobs")
            job_count = cursor.fetchone()[0]
            cursor.execute("SELECT count(*) FROM job_fingerprints")
            fp_count = cursor.fetchone()[0]
            conn.close()
            return {"status": "UP", "job_records": job_count, "fingerprint_records": fp_count}
        except Exception as e:
            return {"status": "DOWN", "error": str(e)}

    def check_disk_space(self) -> Dict[str, Any]:
        try:
            total, used, free = shutil.disk_usage(os.path.dirname(self.db_path))
            free_gb = round(free / (1024 ** 3), 2)
            return {"status": "UP" if free_gb > 1.0 else "WARNING", "free_gb": free_gb}
        except Exception as e:
            return {"status": "UNKNOWN", "error": str(e)}

    def get_full_diagnostics(self) -> Dict[str, Any]:
        db_health = self.check_database()
        disk_health = self.check_disk_space()
        proxy_stats = global_proxy_manager.get_stats()
        active_tasks = global_job_task_queue.list_active_tasks()

        overall_status = "HEALTHY"
        if db_health.get("status") != "UP" or disk_health.get("status") == "DOWN":
            overall_status = "UNHEALTHY"
        elif disk_health.get("status") == "WARNING":
            overall_status = "DEGRADED"

        return {
            "status": overall_status,
            "database": db_health,
            "disk": disk_health,
            "proxies": proxy_stats,
            "background_tasks": {"active_count": len(active_tasks)}
        }

global_health_monitor = HealthMonitor()
