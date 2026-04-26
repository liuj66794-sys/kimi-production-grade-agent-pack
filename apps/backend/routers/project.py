"""
Project Router - Project state, run state, and release status endpoints.

Provides read-only access to project configuration and execution state.
All endpoints are GET-only; mutations go through /api/jobs/run-script.
"""

import os
import json
from typing import Dict, Any, Optional

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db import get_connection, execute, fetchone, commit
from config import BASE_DIR, RUNTIME_DIR

router = APIRouter(prefix="/api", tags=["project"])


# ---------------------------------------------------------------------------
# Response Models
# ---------------------------------------------------------------------------

class ProjectStateResponse(BaseModel):
    """Current project configuration and stage."""
    id: int
    name: str
    current_stage: str
    status: str
    config: str
    last_updated: str


class RunStateResponse(BaseModel):
    """Current pipeline execution state."""
    status: str  # idle / running / blocked / completed / failed
    current_step: Optional[str]
    progress: float
    started_at: Optional[str]
    completed_at: Optional[str]


class ReleaseStatusResponse(BaseModel):
    """Release check result from release_check.py."""
    status: str
    level: str
    checks: Optional[list] = None
    passed: Optional[bool] = None
    error: Optional[str] = None


# ---------------------------------------------------------------------------
# Database helper
# ---------------------------------------------------------------------------




# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/project-state", response_model=Dict[str, Any])
def get_project_state() -> Dict[str, Any]:
    """
    Get current project state from project_state table.

    Returns the singleton project configuration record (id=1).
    Creates default record if none exists.
    """
    with get_connection() as conn:
        row = fetchone(conn, "SELECT * FROM project_state WHERE id = 1")

        if not row:
            execute(
                conn,
                """
                    INSERT INTO project_state (id, name, current_stage, status, config)
                    VALUES (1, 'default', 'l1', 'active', '{}')
                """,
            )
            commit(conn)
            row = fetchone(conn, "SELECT * FROM project_state WHERE id = 1")

    return row if row else {}


@router.get("/run-state", response_model=RunStateResponse)
def get_run_state() -> Dict[str, Any]:
    """
    Get current pipeline execution state.

    Reads from runtime/run-state.json if it exists.
    Returns idle state if no run is active.
    """
    run_state_path = os.path.join(RUNTIME_DIR, "run-state.json")

    if os.path.exists(run_state_path):
        try:
            with open(run_state_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to read run-state.json: {str(e)}"
            )

    # Default idle state
    return {
        "status": "idle",
        "current_step": None,
        "progress": 0.0,
        "started_at": None,
        "completed_at": None,
    }


@router.get("/release-status", response_model=ReleaseStatusResponse)
def get_release_status(level: str = "l1") -> Dict[str, Any]:
    """
    Get release status by calling release_check.py.

    Args:
        level: Release level to check (l1, l2, l3)

    Returns:
        Parsed JSON output from release_check.py
    """
    # Import here to avoid circular dependencies
    import sys
    sys.path.insert(0, os.path.join(BASE_DIR, "apps", "backend"))
    from services.script_runner import script_runner, ScriptNotAllowedError, ScriptNotFoundError

    try:
        result = script_runner.run(
            script_name="release_check.py",
            params={"level": level, "json": True},
        )

        if result["success"]:
            try:
                return json.loads(result["stdout"])
            except json.JSONDecodeError:
                return {
                    "status": "unknown",
                    "level": level,
                    "stdout": result["stdout"],
                    "error": "Failed to parse JSON output",
                }
        else:
            return {
                "status": "error",
                "level": level,
                "error": result.get("stderr") or result.get("stdout", "Unknown error"),
            }

    except (ScriptNotAllowedError, ScriptNotFoundError) as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        return {
            "status": "unknown",
            "level": level,
            "error": str(e),
        }
