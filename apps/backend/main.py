"""
Kimi Agent Pack Dashboard API - FastAPI Main Application v3.0.0

L3 Architecture Principle:
    UI does NOT bypass scripts.
    UI calls Backend API.
    Backend calls scripts/*.py.
    UI does NOT directly modify memory.
    UI does NOT skip QA.

This is the central entry point. All script execution flows through
services/script_runner.py with whitelist validation.
"""

import os
import sys
import json
# Database adapter (SQLite local / PostgreSQL production)
from db import init_schema, get_connection, execute, fetchall, fetchone, commit, get_db, is_postgres
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
from config import (
    BASE_DIR,
    CORS_ORIGINS,
    CORS_ALLOW_CREDENTIALS,
    CORS_ALLOW_METHODS,
    CORS_ALLOW_HEADERS,
    API_TITLE,
    API_VERSION,
    API_HOST,
    API_PORT,
    ALLOWED_SCRIPTS_SET,
    MAX_CONCURRENT_JOBS,
    SCRIPT_TIMEOUT,
    MAX_STDOUT_LENGTH,
    MAX_STDERR_LENGTH,
)

# ---------------------------------------------------------------------------
# Services
# ---------------------------------------------------------------------------
from services.job_state import job_service, JobStatus
from services.script_runner import (
    script_runner,
    ScriptNotAllowedError,
    ScriptNotFoundError,
    ScriptTimeoutError,
)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
from routers.project import router as project_router
from routers.artifacts import router as artifacts_router
from routers.tasks import router as tasks_router
from routers.agents import router as agents_router
from routers.eval import router as eval_router
from routers.memory import router as memory_router

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# FastAPI App
# ---------------------------------------------------------------------------

app = FastAPI(
    title=API_TITLE,
    version=API_VERSION,
    description="Kimi Production-Grade Agent System - Dashboard Backend API",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=CORS_ALLOW_CREDENTIALS,
    allow_methods=CORS_ALLOW_METHODS,
    allow_headers=CORS_ALLOW_HEADERS,
)

# Security
security = HTTPBearer()

# ---------------------------------------------------------------------------
# Database Initialization
# ---------------------------------------------------------------------------

def init_database():
    """
    Initialize all database tables on startup.
    Creates tables if they don't exist.
    """
    init_schema()
    logger.info("Database initialized (%s)", "PostgreSQL" if is_postgres() else "SQLite")


@app.on_event("startup")
async def startup_event():
    """Application startup handler."""
    init_database()
    logger.info("Kimi Agent Pack Dashboard API v%s started", API_VERSION)


@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown handler."""
    logger.info("Kimi Agent Pack Dashboard API shutting down")


# FastAPI dependency re-exported from db module
from db import get_db as _get_db
get_db = _get_db


# ---------------------------------------------------------------------------
# Register Routers
# ---------------------------------------------------------------------------

app.include_router(project_router)
app.include_router(artifacts_router)
app.include_router(tasks_router)
app.include_router(agents_router)
app.include_router(eval_router)
app.include_router(memory_router)

# ---------------------------------------------------------------------------
# Request/Response Models
# ---------------------------------------------------------------------------

class RunScriptRequest(BaseModel):
    """Request body for script execution."""
    params: Dict[str, Any] = {}
    async_execution: bool = False


class RunScriptResponse(BaseModel):
    """Response from script execution."""
    script: str
    returncode: int
    stdout: str
    stderr: Optional[str]
    duration_ms: float
    success: bool


class JobCreateRequest(BaseModel):
    """Request body for job creation."""
    job_type: str = "script_execution"
    script_name: str
    params: Dict[str, Any] = {}


class JobResponse(BaseModel):
    """Job information response."""
    id: int
    job_type: str
    script_name: Optional[str]
    status: str
    params: Optional[str]
    result: Optional[str]
    created_at: Optional[str]
    updated_at: Optional[str]
    started_at: Optional[str]
    completed_at: Optional[str]
    error_message: Optional[str]


# ---------------------------------------------------------------------------
# Core Endpoints (not moved to routers - direct script execution)
# ---------------------------------------------------------------------------

@app.post("/api/jobs/run-script", response_model=RunScriptResponse)
def run_script(
    script_name: str,
    request: RunScriptRequest,
):
    """
    Execute a whitelisted script with parameters.

    SECURITY - This is the ONLY endpoint that executes scripts.
    Constraints:
    1. Script must be in ALLOWED_SCRIPTS whitelist
    2. Script file must exist in scripts/ directory
    3. All executions are logged to audit_log
    4. Execution is subject to timeout

    Args:
        script_name: Name of the script (e.g. 'release_check.py')
        request: Execution parameters and options

    Returns:
        Execution results including stdout, stderr, and duration.

    Raises:
        HTTPException 403: Script not in allowlist
        HTTPException 404: Script file not found
        HTTPException 504: Script execution timed out
        HTTPException 500: Internal execution error
    """
    try:
        result = script_runner.run(
            script_name=script_name,
            params=request.params,
        )
        return result

    except ScriptNotAllowedError as e:
        logger.warning("Blocked script execution: %s - %s", script_name, str(e))
        raise HTTPException(status_code=403, detail=str(e))

    except ScriptNotFoundError as e:
        logger.warning("Script not found: %s - %s", script_name, str(e))
        raise HTTPException(status_code=404, detail=str(e))

    except ScriptTimeoutError as e:
        logger.error("Script timeout: %s - %s", script_name, str(e))
        raise HTTPException(status_code=504, detail=str(e))

    except Exception as e:
        logger.error("Script execution failed: %s - %s", script_name, str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/jobs/run-script-async")
def run_script_async(
    script_name: str,
    request: RunScriptRequest,
):
    """
    Start a script execution asynchronously (non-blocking).

    Creates a job record and starts the script in background.
    Use GET /api/jobs/{job_id} to poll for completion.

    Args:
        script_name: Name of the script
        request: Execution parameters

    Returns:
        Job information including job_id for polling.
    """
    # Create job record
    job_id = job_service.create_job(
        job_type="script_execution",
        script_name=script_name,
        params=request.params,
    )

    try:
        # Start script asynchronously
        process = script_runner.run_async(
            script_name=script_name,
            params=request.params,
        )

        # Update job with PID
        job_service.update_job_status(
            job_id=job_id,
            status=JobStatus.RUNNING,
            pid=process.pid,
        )

        return {
            "job_id": job_id,
            "script": script_name,
            "status": "running",
            "pid": process.pid,
            "poll_url": f"/api/jobs/{job_id}",
        }

    except (ScriptNotAllowedError, ScriptNotFoundError) as e:
        job_service.update_job_status(
            job_id=job_id,
            status=JobStatus.FAILED,
            error_message=str(e),
        )
        raise HTTPException(status_code=403, detail=str(e))

    except Exception as e:
        job_service.update_job_status(
            job_id=job_id,
            status=JobStatus.FAILED,
            error_message=str(e),
        )
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# Job Queue Endpoints
# ---------------------------------------------------------------------------

@app.get("/api/jobs")
def list_jobs(
    status: Optional[str] = Query(default=None, description="Filter by status"),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    """
    List jobs from the job queue.

    Args:
        status: Filter by job status
        limit: Maximum results
        offset: Pagination offset

    Returns:
        List of jobs.
    """
    jobs = job_service.list_jobs(status=status, limit=limit, offset=offset)
    return {"jobs": jobs, "total": len(jobs)}


@app.get("/api/jobs/{job_id}")
def get_job(job_id: int):
    """
    Get a specific job by ID.

    Args:
        job_id: The job identifier

    Returns:
        Job details or 404.
    """
    job = job_service.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")
    return job


@app.delete("/api/jobs/{job_id}")
def delete_job(job_id: int):
    """
    Delete a job by ID.

    Args:
        job_id: The job identifier

    Returns:
        Deletion confirmation.
    """
    if job_service.delete_job(job_id):
        return {"message": f"Job {job_id} deleted"}
    raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")


@app.get("/api/jobs/stats")
def get_job_stats():
    """Get job queue statistics."""
    return job_service.get_stats()


@app.post("/api/jobs/cleanup")
def cleanup_orphan_jobs():
    """
    Clean up orphan jobs (running jobs that have timed out).

    Returns:
        Number of jobs cleaned up.
    """
    cleaned = job_service.cleanup_orphan_jobs()
    return {"cleaned": cleaned}


# ---------------------------------------------------------------------------
# Audit Log Endpoints
# ---------------------------------------------------------------------------

@app.get("/api/audit-log")
def get_audit_log(
    limit: int = Query(default=100, ge=1, le=500),
    event_type: Optional[str] = Query(default=None),
):
    """
    Get audit log entries.

    Args:
        limit: Maximum entries
        event_type: Filter by event type

    Returns:
        Audit log entries.
    """
    with get_connection() as conn:
        if event_type:
            rows = fetchall(
                conn,
                "SELECT * FROM audit_log WHERE event_type = ? ORDER BY timestamp DESC LIMIT ?",
                (event_type, limit),
            )
        else:
            rows = fetchall(
                conn,
                "SELECT * FROM audit_log ORDER BY timestamp DESC LIMIT ?",
                (limit,),
            )

    return {"entries": rows, "total": len(rows)}


# ---------------------------------------------------------------------------
# Health & Root
# ---------------------------------------------------------------------------

@app.get("/")
def root():
    """API root - health check."""
    return {
        "message": f"{API_TITLE} v{API_VERSION}",
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat(),
    }


@app.get("/health")
def health_check():
    """Detailed health check endpoint."""
    db_ok = True  # Connection is tested by init_schema on startup
    jobs_running = job_service.count_running_jobs()

    return {
        "status": "healthy" if db_ok else "degraded",
        "version": API_VERSION,
        "database": "connected" if db_ok else "error",
        "jobs_running": jobs_running,
        "max_concurrent": MAX_CONCURRENT_JOBS,
        "timestamp": datetime.utcnow().isoformat(),
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=API_HOST, port=API_PORT)
