"""
Job Queue Service — Unified SQLite / PostgreSQL job management.

Provides CRUD operations for the jobs table, concurrency control,
and orphan job cleanup.
"""

import json
import os
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from enum import Enum

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db import get_connection, execute, fetchall, fetchone, commit, is_postgres
from config import MAX_CONCURRENT_JOBS, JOB_ORPHAN_THRESHOLD


class JobStatus(str, Enum):
    """Job lifecycle states."""
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


class JobStateService:
    """Service for managing job queue state."""

    def __init__(self) -> None:
        pass  # Schema is initialised by main.py init_schema()

    # ------------------------------------------------------------------
    # CRUD Operations
    # ------------------------------------------------------------------

    def create_job(
        self,
        job_type: str,
        script_name: str,
        params: Optional[Dict[str, Any]] = None,
        triggered_by: str = "dashboard_user"
    ) -> int:
        """
        Create a new job record.
        Returns the newly created job ID.
        """
        with get_connection() as conn:
            proxy = execute(
                conn,
                """
                    INSERT INTO jobs (job_type, script_name, params, status, triggered_by)
                    VALUES (?, ?, ?, 'pending', ?)
                    RETURNING id
                """,
                (
                    job_type,
                    script_name,
                    json.dumps(params) if params else "{}",
                    triggered_by,
                ),
            )
            row = proxy.fetchone()
            commit(conn)
            return row[0] if row else proxy.lastrowid

    def get_job(self, job_id: int) -> Optional[Dict[str, Any]]:
        """Get a single job by ID."""
        with get_connection() as conn:
            return fetchone(conn, "SELECT * FROM jobs WHERE id = ?", (job_id,))

    def list_jobs(
        self,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """List jobs with optional status filter."""
        with get_connection() as conn:
            if status:
                return fetchall(
                    conn,
                    """
                        SELECT * FROM jobs WHERE status = ?
                        ORDER BY created_at DESC LIMIT ? OFFSET ?
                    """,
                    (status, limit, offset),
                )
            else:
                return fetchall(
                    conn,
                    """
                        SELECT * FROM jobs
                        ORDER BY created_at DESC LIMIT ? OFFSET ?
                    """,
                    (limit, offset),
                )

    def update_job_status(
        self,
        job_id: int,
        status: JobStatus,
        result: Optional[str] = None,
        error_message: Optional[str] = None,
        pid: Optional[int] = None
    ) -> bool:
        """Update job status and optional fields."""
        now = datetime.utcnow().isoformat()
        with get_connection() as conn:
            fields = ["status = ?", "updated_at = ?"]
            params: List[Any] = [status.value, now]

            if result is not None:
                fields.append("result = ?")
                params.append(result)
            if error_message is not None:
                fields.append("error_message = ?")
                params.append(error_message)
            if pid is not None:
                fields.append("pid = ?")
                params.append(pid)
            if status == JobStatus.RUNNING:
                fields.append("started_at = ?")
                params.append(now)
            if status in (JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.TIMEOUT):
                fields.append("completed_at = ?")
                params.append(now)

            params.append(job_id)

            proxy = execute(
                conn,
                f"UPDATE jobs SET {', '.join(fields)} WHERE id = ?",
                tuple(params),
            )
            commit(conn)
            return proxy.rowcount > 0

    def delete_job(self, job_id: int) -> bool:
        """Delete a job by ID. Returns True if deleted."""
        with get_connection() as conn:
            proxy = execute(conn, "DELETE FROM jobs WHERE id = ?", (job_id,))
            commit(conn)
            return proxy.rowcount > 0

    # ------------------------------------------------------------------
    # Concurrency Control
    # ------------------------------------------------------------------

    def count_running_jobs(self) -> int:
        """Count currently running jobs."""
        with get_connection() as conn:
            proxy = execute(conn, "SELECT COUNT(*) FROM jobs WHERE status = 'running'")
            row = proxy.fetchone()
            return row[0] if row else 0

    def can_start_job(self) -> bool:
        """Check if a new job can be started (under concurrency limit)."""
        return self.count_running_jobs() < MAX_CONCURRENT_JOBS

    def get_next_pending_job(self) -> Optional[Dict[str, Any]]:
        """
        Atomically fetch the oldest pending job for processing.
        """
        with get_connection() as conn:
            now = datetime.utcnow().isoformat()
            proxy = execute(
                conn,
                """
                    UPDATE jobs
                    SET status = 'running', started_at = ?, updated_at = ?, pid = -1
                    WHERE id = (
                        SELECT id FROM jobs
                        WHERE status = 'pending'
                        ORDER BY created_at ASC
                        LIMIT 1
                    )
                    RETURNING *
                """,
                (now, now),
            )
            row = proxy.fetchone()
            commit(conn)
            return dict(row) if row else None

    # ------------------------------------------------------------------
    # Orphan Cleanup
    # ------------------------------------------------------------------

    def cleanup_orphan_jobs(self) -> int:
        """
        Mark jobs as TIMEOUT if they have been running too long.
        Returns number of jobs cleaned up.
        """
        threshold = (
            datetime.utcnow() - timedelta(seconds=JOB_ORPHAN_THRESHOLD)
        ).isoformat()

        with get_connection() as conn:
            proxy = execute(
                conn,
                """
                    UPDATE jobs
                    SET status = 'timeout',
                        error_message = 'Job timed out (orphan cleanup)',
                        completed_at = ?,
                        updated_at = ?
                    WHERE status = 'running'
                      AND started_at < ?
                """,
                (datetime.utcnow().isoformat(), datetime.utcnow().isoformat(), threshold),
            )
            commit(conn)
            return proxy.rowcount

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        """Get job queue statistics."""
        with get_connection() as conn:
            rows = fetchall(
                conn,
                "SELECT status, COUNT(*) as count FROM jobs GROUP BY status",
            )
            status_counts = {r["status"]: r["count"] for r in rows}

            proxy = execute(conn, "SELECT COUNT(*) FROM jobs")
            row = proxy.fetchone()
            total = row[0] if row else 0

            # Average duration: dialect-aware
            if is_postgres():
                avg_rows = fetchall(
                    conn,
                    """
                        SELECT EXTRACT(EPOCH FROM (completed_at - started_at)) as avg_duration
                        FROM jobs
                        WHERE status = 'completed' AND started_at IS NOT NULL
                    """,
                )
            else:
                avg_rows = fetchall(
                    conn,
                    """
                        SELECT (
                            julianday(completed_at) - julianday(started_at)
                        ) * 86400 as avg_duration
                        FROM jobs
                        WHERE status = 'completed' AND started_at IS NOT NULL
                    """,
                )

            durations = [r["avg_duration"] for r in avg_rows if r["avg_duration"] is not None]
            avg_duration = sum(durations) / len(durations) if durations else 0

            return {
                "total": total,
                "by_status": status_counts,
                "running": status_counts.get("running", 0),
                "pending": status_counts.get("pending", 0),
                "max_concurrent": MAX_CONCURRENT_JOBS,
                "avg_duration_seconds": round(avg_duration, 2),
            }


# Singleton instance
job_service = JobStateService()
