import sqlite3
import json
import os
from typing import List, Dict, Any, Optional
from models import Job
from datetime import datetime

DB_FILE = os.path.join(os.path.dirname(__file__), "airohunt.db")

class AirohuntDatabase:
    def __init__(self, db_path: str = DB_FILE):
        self.db_path = db_path
        self._init_db()

    def _get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # 1. Jobs Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY,
                    title TEXT,
                    company TEXT,
                    location TEXT,
                    salary TEXT,
                    description TEXT,
                    skills_required TEXT, -- JSON string
                    url TEXT,
                    is_scam INTEGER, -- Boolean 0 or 1
                    scam_reason TEXT,
                    match_score REAL,
                    status TEXT,
                    tailored_resume TEXT,
                    posted_at TEXT,
                    scam_risk_score INTEGER,
                    tech_match_score REAL,
                    pref_match_score REAL,
                    trust_score REAL,
                    opportunity_score REAL,
                    recommendation_pros TEXT, -- JSON string
                    recommendation_cons TEXT, -- JSON string
                    ai_recommendation TEXT,
                    evaluation_mode TEXT,
                    company_summary TEXT,
                    tech_stack TEXT, -- JSON string
                    hiring_signals TEXT, -- JSON string
                    trust_rating TEXT,
                    validation_tier TEXT,
                    validation_score REAL,
                    validation_confidence REAL,
                    validation_reasons TEXT, -- JSON string
                    validation_warnings TEXT, -- JSON string
                    rejection_reasons TEXT -- JSON string
                )
            """)

            # 2. RDAP Cache Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS rdap_cache (
                    domain TEXT PRIMARY KEY,
                    resolves INTEGER, -- Boolean 0 or 1
                    age_days INTEGER,
                    info TEXT,
                    cached_at TEXT
                )
            """)

            # 3. Applications Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS applications (
                    job_id TEXT PRIMARY KEY,
                    company TEXT,
                    title TEXT,
                    status TEXT,
                    source TEXT,
                    resume_version TEXT,
                    last_updated TEXT,
                    platform TEXT,
                    support TEXT
                )
            """)

            # 4. Audit Logs Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS audit_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT,
                    job_id TEXT,
                    company TEXT,
                    title TEXT,
                    action TEXT,
                    mode TEXT
                )
            """)
            
            conn.commit()

    # --- JOB OPERATIONS ---
    
    def save_job(self, job: Job):
        job_dict = job.dict()
        self.save_job_dict(job_dict)

    def save_job_dict(self, job_dict: Dict[str, Any]):
        # Helper to serialize fields
        def serialize(val):
            if isinstance(val, (list, dict)):
                return json.dumps(val)
            return val

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO jobs (
                    id, title, company, location, salary, description, skills_required, url, 
                    is_scam, scam_reason, match_score, status, tailored_resume, posted_at, 
                    scam_risk_score, tech_match_score, pref_match_score, trust_score, opportunity_score, 
                    recommendation_pros, recommendation_cons, ai_recommendation, evaluation_mode, 
                    company_summary, tech_stack, hiring_signals, trust_rating, validation_tier, 
                    validation_score, validation_confidence, validation_reasons, validation_warnings, 
                    rejection_reasons
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    title=excluded.title,
                    company=excluded.company,
                    location=excluded.location,
                    salary=excluded.salary,
                    description=excluded.description,
                    skills_required=excluded.skills_required,
                    url=excluded.url,
                    is_scam=excluded.is_scam,
                    scam_reason=excluded.scam_reason,
                    match_score=excluded.match_score,
                    status=excluded.status,
                    tailored_resume=excluded.tailored_resume,
                    posted_at=excluded.posted_at,
                    scam_risk_score=excluded.scam_risk_score,
                    tech_match_score=excluded.tech_match_score,
                    pref_match_score=excluded.pref_match_score,
                    trust_score=excluded.trust_score,
                    opportunity_score=excluded.opportunity_score,
                    recommendation_pros=excluded.recommendation_pros,
                    recommendation_cons=excluded.recommendation_cons,
                    ai_recommendation=excluded.ai_recommendation,
                    evaluation_mode=excluded.evaluation_mode,
                    company_summary=excluded.company_summary,
                    tech_stack=excluded.tech_stack,
                    hiring_signals=excluded.hiring_signals,
                    trust_rating=excluded.trust_rating,
                    validation_tier=excluded.validation_tier,
                    validation_score=excluded.validation_score,
                    validation_confidence=excluded.validation_confidence,
                    validation_reasons=excluded.validation_reasons,
                    validation_warnings=excluded.validation_warnings,
                    rejection_reasons=excluded.rejection_reasons
            """, (
                job_dict.get("id"),
                job_dict.get("title"),
                job_dict.get("company"),
                job_dict.get("location"),
                job_dict.get("salary"),
                job_dict.get("description"),
                serialize(job_dict.get("skills_required", [])),
                job_dict.get("url"),
                1 if job_dict.get("is_scam", False) else 0,
                job_dict.get("scam_reason", ""),
                job_dict.get("match_score", 0.0),
                job_dict.get("status", "Matched"),
                job_dict.get("tailored_resume", ""),
                job_dict.get("posted_at", datetime.now().isoformat()),
                job_dict.get("scam_risk_score", 0),
                job_dict.get("tech_match_score", 0.0),
                job_dict.get("pref_match_score", 0.0),
                job_dict.get("trust_score", 0.0),
                job_dict.get("opportunity_score", 0.0),
                serialize(job_dict.get("recommendation_pros", [])),
                serialize(job_dict.get("recommendation_cons", [])),
                job_dict.get("ai_recommendation", ""),
                job_dict.get("evaluation_mode", "Local Heuristics"),
                job_dict.get("company_summary", ""),
                serialize(job_dict.get("tech_stack", [])),
                serialize(job_dict.get("hiring_signals", [])),
                job_dict.get("trust_rating", "B"),
                job_dict.get("validation_tier", "B"),
                job_dict.get("validation_score", 0.0),
                job_dict.get("validation_confidence", 0.0),
                serialize(job_dict.get("validation_reasons", [])),
                serialize(job_dict.get("validation_warnings", [])),
                serialize(job_dict.get("rejection_reasons", []))
            ))
            conn.commit()

    def get_job(self, job_id: str) -> Optional[Job]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM jobs WHERE id = ?", (job_id,))
            row = cursor.fetchone()
            if row:
                return self._row_to_job(row)
        return None

    def get_all_jobs(self) -> List[Job]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM jobs ORDER BY match_score DESC")
            rows = cursor.fetchall()
            return [self._row_to_job(row) for row in rows]

    def update_job_status(self, job_id: str, status: str) -> bool:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE jobs SET status = ? WHERE id = ?", (status, job_id))
            conn.commit()
            return cursor.rowcount > 0

    def update_tailored_resume(self, job_id: str, status: str, resume_text: str) -> bool:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE jobs SET status = ?, tailored_resume = ? WHERE id = ?", (status, resume_text, job_id))
            conn.commit()
            return cursor.rowcount > 0

    def delete_job(self, job_id: str) -> bool:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM jobs WHERE id = ?", (job_id,))
            conn.commit()
            return cursor.rowcount > 0

    def _row_to_job(self, row: sqlite3.Row) -> Job:
        # Deserialize JSON columns
        def safe_json_load(val):
            if not val:
                return []
            try:
                return json.loads(val)
            except Exception:
                return []

        return Job(
            id=row["id"],
            title=row["title"],
            company=row["company"],
            location=row["location"],
            salary=row["salary"],
            description=row["description"],
            skills_required=safe_json_load(row["skills_required"]),
            url=row["url"],
            is_scam=bool(row["is_scam"]),
            scam_reason=row["scam_reason"],
            match_score=row["match_score"],
            status=row["status"],
            tailored_resume=row["tailored_resume"],
            posted_at=row["posted_at"],
            scam_risk_score=row["scam_risk_score"],
            tech_match_score=row["tech_match_score"],
            pref_match_score=row["pref_match_score"],
            trust_score=row["trust_score"],
            opportunity_score=row["opportunity_score"],
            recommendation_pros=safe_json_load(row["recommendation_pros"]),
            recommendation_cons=safe_json_load(row["recommendation_cons"]),
            ai_recommendation=row["ai_recommendation"],
            evaluation_mode=row["evaluation_mode"],
            company_summary=row["company_summary"],
            tech_stack=safe_json_load(row["tech_stack"]),
            hiring_signals=safe_json_load(row["hiring_signals"]),
            trust_rating=row["trust_rating"],
            validation_tier=row["validation_tier"],
            validation_score=row["validation_score"],
            validation_confidence=row["validation_confidence"],
            validation_reasons=safe_json_load(row["validation_reasons"]),
            validation_warnings=safe_json_load(row["validation_warnings"]),
            rejection_reasons=safe_json_load(row["rejection_reasons"])
        )

    # --- RDAP DOMAIN CACHE OPERATIONS ---

    def get_rdap_cache(self, domain: str) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM rdap_cache WHERE domain = ?", (domain,))
            row = cursor.fetchone()
            if row:
                return {
                    "domain": row["domain"],
                    "resolves": bool(row["resolves"]),
                    "age_days": row["age_days"],
                    "info": row["info"],
                    "cached_at": row["cached_at"]
                }
        return None

    def save_rdap_cache(self, domain: str, resolves: bool, age_days: int, info: str):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO rdap_cache (domain, resolves, age_days, info, cached_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(domain) DO UPDATE SET
                    resolves=excluded.resolves,
                    age_days=excluded.age_days,
                    info=excluded.info,
                    cached_at=excluded.cached_at
            """, (domain, 1 if resolves else 0, age_days, info, datetime.now().isoformat()))
            conn.commit()

    # --- APPLICATIONS QUEUE OPERATIONS ---

    def get_applications(self) -> Dict[str, Any]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM applications")
            apps = {}
            for row in cursor.fetchall():
                apps[row["job_id"]] = {
                    "job_id": row["job_id"],
                    "company": row["company"],
                    "title": row["title"],
                    "status": row["status"],
                    "source": row["source"],
                    "resume_version": row["resume_version"],
                    "last_updated": row["last_updated"],
                    "platform": row["platform"],
                    "support": row["support"]
                }
            
            cursor.execute("SELECT * FROM audit_logs ORDER BY id DESC")
            logs = []
            for row in cursor.fetchall():
                logs.append({
                    "timestamp": row["timestamp"],
                    "job_id": row["job_id"],
                    "company": row["company"],
                    "title": row["title"],
                    "action": row["action"],
                    "mode": row["mode"]
                })
            
            return {
                "applications": apps,
                "audit_logs": logs
            }

    def save_application(self, app_data: Dict[str, Any]):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO applications (job_id, company, title, status, source, resume_version, last_updated, platform, support)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(job_id) DO UPDATE SET
                    company=excluded.company,
                    title=excluded.title,
                    status=excluded.status,
                    source=excluded.source,
                    resume_version=excluded.resume_version,
                    last_updated=excluded.last_updated,
                    platform=excluded.platform,
                    support=excluded.support
            """, (
                app_data["job_id"],
                app_data["company"],
                app_data["title"],
                app_data["status"],
                app_data["source"],
                app_data["resume_version"],
                app_data["last_updated"],
                app_data["platform"],
                app_data["support"]
            ))
            conn.commit()

    def add_audit_log(self, log_entry: Dict[str, Any]):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO audit_logs (timestamp, job_id, company, title, action, mode)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                log_entry["timestamp"],
                log_entry["job_id"],
                log_entry["company"],
                log_entry["title"],
                log_entry["action"],
                log_entry["mode"]
            ))
            conn.commit()
