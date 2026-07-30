import sqlite3
from typing import Dict, Any
from database import DB_FILE

class DatabaseMaintenanceEngine:
    """Database maintenance engine for vacuuming, purging stale records, and optimizing indices."""
    def __init__(self, db_path: str = DB_FILE):
        self.db_path = db_path

    def vacuum_database(self) -> bool:
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute("VACUUM;")
            conn.close()
            return True
        except Exception:
            return False

    def purge_old_audit_logs(self, max_records: int = 1000) -> int:
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT count(*) FROM audit_logs")
            total = cursor.fetchone()[0]
            deleted = 0
            if total > max_records:
                to_delete = total - max_records
                cursor.execute("""
                    DELETE FROM audit_logs WHERE id IN (
                        SELECT id FROM audit_logs ORDER BY id ASC LIMIT ?
                    )
                """, (to_delete,))
                deleted = cursor.rowcount
                conn.commit()
            conn.close()
            return deleted
        except Exception:
            return 0

    def run_full_maintenance(self) -> Dict[str, Any]:
        purged_logs = self.purge_old_audit_logs(1000)
        vacuumed = self.vacuum_database()
        return {
            "vacuum_status": "SUCCESS" if vacuumed else "FAILED",
            "purged_audit_logs": purged_logs
        }

global_db_maintenance = DatabaseMaintenanceEngine()
