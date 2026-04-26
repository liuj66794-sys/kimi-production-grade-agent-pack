"""
Memory Router - Read-only access to memory candidates and approved memories.

CRITICAL SECURITY: This router provides ONLY read-only endpoints.
UI is NOT allowed to auto-approve memory items.
All memory write operations MUST go through scripts/*.py.

Principle: UI reads memory via API; memory curation is done by
memory-curator agent through the approved script pipeline.
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
from config import MEMORY_DIR, BASE_DIR

router = APIRouter(prefix="/api", tags=["memory"])


# ---------------------------------------------------------------------------
# Response Models
# ---------------------------------------------------------------------------

class MemoryCandidate(BaseModel):
    """A memory item candidate awaiting approval."""
    id: Optional[str] = None
    content: Optional[str] = None
    source: Optional[str] = None
    agent: Optional[str] = None
    task_id: Optional[str] = None
    created_at: Optional[str] = None
    confidence: Optional[float] = None
    status: str = "pending"  # pending | approved | rejected


class MemoryApproved(BaseModel):
    """An approved and committed memory item."""
    id: Optional[str] = None
    content: Optional[str] = None
    source: Optional[str] = None
    approved_by: Optional[str] = None
    approved_at: Optional[str] = None
    version: int = 1
    tags: List[str] = []


class MemoryCandidatesResponse(BaseModel):
    """List of memory candidates."""
    candidates: List[Dict[str, Any]]
    total: int
    pending: int
    approved: int
    rejected: int


class MemoryApprovedResponse(BaseModel):
    """List of approved memories."""
    memories: List[Dict[str, Any]]
    total: int


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_memory_candidates_dir() -> str:
    """Get the memory candidates directory path."""
    return os.path.join(MEMORY_DIR, "candidates") if MEMORY_DIR else ""


def _get_memory_approved_dir() -> str:
    """Get the memory approved directory path."""
    return os.path.join(MEMORY_DIR, "approved") if MEMORY_DIR else ""


def _load_json_files(directory: str, limit: int = 50) -> List[Dict[str, Any]]:
    """
    Load JSON files from a directory, sorted by modification time (newest first).

    Args:
        directory: Path to directory containing JSON files
        limit: Maximum number of files to load

    Returns:
        List of parsed JSON objects.
    """
    if not directory or not os.path.exists(directory):
        return []

    files = glob.glob(os.path.join(directory, "*.json"))
    files.sort(key=os.path.getmtime, reverse=True)

    items = []
    for f in files[:limit]:
        try:
            with open(f, "r", encoding="utf-8") as fh:
                data = json.load(fh)
                if isinstance(data, dict):
                    data["_file"] = os.path.basename(f)
                    data["_modified"] = datetime.fromtimestamp(
                        os.path.getmtime(f)
                    ).isoformat()
                items.append(data)
        except (json.JSONDecodeError, IOError, UnicodeDecodeError):
            continue

    return items


# ---------------------------------------------------------------------------
# Endpoints - READ ONLY
# ---------------------------------------------------------------------------
# SECURITY: All endpoints below are GET only.
# NO POST/PUT/DELETE endpoints for memory mutation.
# UI must use /api/jobs/run-script to trigger memory operations.

@router.get("/memory-candidates", response_model=MemoryCandidatesResponse)
def get_memory_candidates(
    limit: int = Query(default=50, ge=1, le=200),
    status: Optional[str] = Query(default=None, description="Filter by status (pending/approved/rejected)"),
) -> Dict[str, Any]:
    """
    Get memory candidates (read-only).

    Returns memory items that are candidates for approval.
    UI must NOT auto-approve these items.
    Use /api/jobs/run-script with approved scripts for curation.

    Args:
        limit: Maximum number of candidates to return
        status: Optional status filter

    Returns:
        List of memory candidates with status breakdown.
    """
    candidates_dir = _get_memory_candidates_dir()
    candidates = _load_json_files(candidates_dir, limit=limit)

    # Apply status filter
    if status:
        candidates = [c for c in candidates if c.get("status") == status]

    # Count by status
    pending = sum(1 for c in candidates if c.get("status") == "pending")
    approved = sum(1 for c in candidates if c.get("status") == "approved")
    rejected = sum(1 for c in candidates if c.get("status") == "rejected")

    return {
        "candidates": candidates,
        "total": len(candidates),
        "pending": pending,
        "approved": approved,
        "rejected": rejected,
    }


@router.get("/memory-candidates/{candidate_id}")
def get_memory_candidate_detail(candidate_id: str) -> Dict[str, Any]:
    """
    Get detailed information about a specific memory candidate.

    Args:
        candidate_id: The candidate identifier (filename without .json)

    Returns:
        Memory candidate details.
    """
    candidates_dir = _get_memory_candidates_dir()
    if not candidates_dir or not os.path.exists(candidates_dir):
        raise HTTPException(status_code=404, detail="Memory candidates directory not found")

    candidate_file = os.path.join(candidates_dir, f"{candidate_id}.json")
    if not os.path.exists(candidate_file):
        raise HTTPException(status_code=404, detail=f"Candidate not found: {candidate_id}")

    try:
        with open(candidate_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict):
                data["_file"] = os.path.basename(candidate_file)
                data["_modified"] = datetime.fromtimestamp(
                    os.path.getmtime(candidate_file)
                ).isoformat()
            return data
    except (json.JSONDecodeError, IOError) as e:
        raise HTTPException(status_code=500, detail=f"Failed to read candidate: {str(e)}")


@router.get("/memory-approved", response_model=MemoryApprovedResponse)
def get_memory_approved(
    limit: int = Query(default=50, ge=1, le=200),
    tag: Optional[str] = Query(default=None, description="Filter by tag"),
) -> Dict[str, Any]:
    """
    Get approved memories (read-only).

    Returns memory items that have been approved and committed.
    This endpoint is strictly read-only.

    Args:
        limit: Maximum number of memories to return
        tag: Optional tag filter

    Returns:
        List of approved memories.
    """
    approved_dir = _get_memory_approved_dir()
    memories = _load_json_files(approved_dir, limit=limit)

    # Apply tag filter
    if tag:
        memories = [
            m for m in memories
            if tag in (m.get("tags", []) or [])
        ]

    return {
        "memories": memories,
        "total": len(memories),
    }


@router.get("/memory-approved/{memory_id}")
def get_memory_approved_detail(memory_id: str) -> Dict[str, Any]:
    """
    Get detailed information about a specific approved memory.

    Args:
        memory_id: The memory identifier (filename without .json)

    Returns:
        Approved memory details with version history if available.
    """
    approved_dir = _get_memory_approved_dir()
    if not approved_dir or not os.path.exists(approved_dir):
        raise HTTPException(status_code=404, detail="Memory approved directory not found")

    memory_file = os.path.join(approved_dir, f"{memory_id}.json")
    if not os.path.exists(memory_file):
        raise HTTPException(status_code=404, detail=f"Memory not found: {memory_id}")

    try:
        with open(memory_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict):
                data["_file"] = os.path.basename(memory_file)
                data["_modified"] = datetime.fromtimestamp(
                    os.path.getmtime(memory_file)
                ).isoformat()

                # Check for version history
                versions_dir = os.path.join(approved_dir, "versions", memory_id)
                if os.path.exists(versions_dir):
                    versions = glob.glob(os.path.join(versions_dir, "*.json"))
                    versions.sort()
                    data["_version_count"] = len(versions)
                    data["_versions"] = [os.path.basename(v) for v in versions[-5:]]

            return data
    except (json.JSONDecodeError, IOError) as e:
        raise HTTPException(status_code=500, detail=f"Failed to read memory: {str(e)}")


@router.get("/memory/stats")
def get_memory_stats() -> Dict[str, Any]:
    """
    Get memory system statistics.

    Returns counts and storage information for the memory system.

    Returns:
        Memory statistics including candidate counts and disk usage.
    """
    stats = {
        "candidates": {"total": 0, "pending": 0, "approved": 0, "rejected": 0},
        "approved": {"total": 0},
        "disk_usage": {"candidates": 0, "approved": 0, "total": 0},
    }

    # Count candidates
    candidates_dir = _get_memory_candidates_dir()
    if candidates_dir and os.path.exists(candidates_dir):
        candidate_files = glob.glob(os.path.join(candidates_dir, "*.json"))
        stats["candidates"]["total"] = len(candidate_files)
        stats["disk_usage"]["candidates"] = sum(
            os.path.getsize(f) for f in candidate_files
        )

        for f in candidate_files:
            try:
                with open(f, "r", encoding="utf-8") as fh:
                    data = json.load(fh)
                    status = data.get("status", "pending")
                    if status in stats["candidates"]:
                        stats["candidates"][status] += 1
            except (json.JSONDecodeError, IOError):
                continue

    # Count approved
    approved_dir = _get_memory_approved_dir()
    if approved_dir and os.path.exists(approved_dir):
        approved_files = glob.glob(os.path.join(approved_dir, "*.json"))
        stats["approved"]["total"] = len(approved_files)
        stats["disk_usage"]["approved"] = sum(
            os.path.getsize(f) for f in approved_files
        )

    stats["disk_usage"]["total"] = (
        stats["disk_usage"]["candidates"] + stats["disk_usage"]["approved"]
    )

    # Convert to human-readable
    for key in ["candidates", "approved", "total"]:
        bytes_val = stats["disk_usage"][key]
        stats["disk_usage"][f"{key}_human"] = _format_bytes(bytes_val)

    return stats


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _format_bytes(size: int) -> str:
    """Format byte size to human-readable string."""
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"
