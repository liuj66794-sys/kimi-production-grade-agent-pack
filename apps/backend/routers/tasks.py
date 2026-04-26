"""
Tasks Router - Task board, task details, and task events endpoints.

Provides read-only access to task event streams from runtime/task-events-*.jsonl.
UI must NEVER modify tasks directly - all mutations go through scripts/*.py.
"""

import os
import json
import glob
from typing import Dict, Any, List, Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import RUNTIME_DIR, BASE_DIR

router = APIRouter(prefix="/api", tags=["tasks"])


# ---------------------------------------------------------------------------
# Response Models
# ---------------------------------------------------------------------------

class TaskEvent(BaseModel):
    """Single task event from the event stream."""
    task_id: Optional[str] = None
    task_name: Optional[str] = None
    status: str  # todo / running / blocked / done
    agent: Optional[str] = None
    stage: Optional[str] = None
    timestamp: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


class TaskBoardResponse(BaseModel):
    """Task board with columns for each status."""
    todo: List[Dict[str, Any]]
    running: List[Dict[str, Any]]
    blocked: List[Dict[str, Any]]
    done: List[Dict[str, Any]]
    total: int


class TaskDetailResponse(BaseModel):
    """Detailed task information with event history."""
    task_id: str
    task_name: str
    current_status: str
    history: List[Dict[str, Any]]
    event_count: int


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _find_task_event_files() -> List[str]:
    """Find all task event files in runtime directory."""
    events_dir = RUNTIME_DIR
    if not os.path.exists(events_dir):
        return []
    return sorted(
        glob.glob(os.path.join(events_dir, "task-events-*.jsonl")),
        reverse=True,  # Newest first
    )


def _read_events_from_file(filepath: str) -> List[Dict[str, Any]]:
    """Read all JSON lines from a task events file."""
    events = []
    if not os.path.exists(filepath):
        return events
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        events.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
    except (IOError, OSError):
        pass
    return events


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/task-board", response_model=TaskBoardResponse)
def get_task_board() -> Dict[str, Any]:
    """
    Get the task board organized by status columns.

    Reads all task-events-*.jsonl files from runtime/ directory
    and groups events by their status field.

    Returns:
        Task board with todo, running, blocked, and done columns.
    """
    files = _find_task_event_files()

    board = {
        "todo": [],
        "running": [],
        "blocked": [],
        "done": [],
    }

    # Deduplicate by task_id + status, keeping newest
    seen = set()

    for filepath in files:
        events = _read_events_from_file(filepath)
        for event in events:
            task_id = event.get("task_id", "unknown")
            status = event.get("status", "unknown")
            key = f"{task_id}:{status}"

            if key in seen:
                continue
            seen.add(key)

            if status in board:
                board[status].append(event)
            else:
                # Unknown status goes to todo
                board["todo"].append(event)

    total = sum(len(v) for v in board.values())

    return {
        "todo": board["todo"],
        "running": board["running"],
        "blocked": board["blocked"],
        "done": board["done"],
        "total": total,
    }


@router.get("/task-board/{task_id}", response_model=TaskDetailResponse)
def get_task_detail(task_id: str) -> Dict[str, Any]:
    """
    Get detailed history for a specific task.

    Args:
        task_id: The unique task identifier

    Returns:
        Task details with full event history.
    """
    files = _find_task_event_files()
    history = []
    task_name = None
    current_status = "unknown"

    for filepath in files:
        events = _read_events_from_file(filepath)
        for event in events:
            if event.get("task_id") == task_id:
                history.append(event)
                if event.get("task_name") and not task_name:
                    task_name = event["task_name"]
                if event.get("status"):
                    current_status = event["status"]

    if not history:
        raise HTTPException(status_code=404, detail=f"Task not found: {task_id}")

    # Sort by timestamp if available
    history.sort(
        key=lambda e: e.get("timestamp", ""),
        reverse=True,
    )

    return {
        "task_id": task_id,
        "task_name": task_name or task_id,
        "current_status": current_status,
        "history": history,
        "event_count": len(history),
    }


@router.get("/task-events")
def get_task_events(
    limit: int = Query(default=100, ge=1, le=500),
    status: Optional[str] = Query(default=None, description="Filter by status"),
    agent: Optional[str] = Query(default=None, description="Filter by agent name"),
) -> Dict[str, Any]:
    """
    Get raw task events with optional filtering.

    Args:
        limit: Maximum number of events to return
        status: Filter by task status (todo/running/blocked/done)
        agent: Filter by agent name

    Returns:
        List of task events matching the filters.
    """
    files = _find_task_event_files()
    events = []

    for filepath in files:
        file_events = _read_events_from_file(filepath)
        for event in file_events:
            # Apply filters
            if status and event.get("status") != status:
                continue
            if agent and event.get("agent") != agent:
                continue
            events.append(event)

        if len(events) >= limit:
            break

    # Trim to limit and sort by timestamp
    events = events[:limit]
    events.sort(
        key=lambda e: e.get("timestamp", ""),
        reverse=True,
    )

    return {
        "events": events,
        "total": len(events),
        "filters": {
            "status": status,
            "agent": agent,
        },
    }
