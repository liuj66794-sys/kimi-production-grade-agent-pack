"""
Artifacts Router - Artifact listing, detail, and download endpoints.

Provides read-only access to the artifacts index and artifact files.
UI must NEVER write artifacts directly - all writes go through scripts/*.py.
"""

import os
import json
from typing import Dict, Any, List, Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse, PlainTextResponse
from pydantic import BaseModel

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db import get_connection, execute, fetchall, fetchone
from config import ARTIFACTS_DIR, BASE_DIR

router = APIRouter(prefix="/api", tags=["artifacts"])


# ---------------------------------------------------------------------------
# Response Models
# ---------------------------------------------------------------------------

class ArtifactItem(BaseModel):
    """Single artifact metadata."""
    id: str
    name: str
    type: str  # report / ppt / spreadsheet / code / image
    path: str
    size: int
    created_at: str
    task_id: str


class ArtifactsListResponse(BaseModel):
    """List of artifacts with total count."""
    artifacts: List[Dict[str, Any]]
    total: int


class ArtifactDetailResponse(BaseModel):
    """Detailed artifact information."""
    id: str
    name: str
    type: str
    path: str
    size: int
    created_at: str
    task_id: str
    checksum: Optional[str]
    exists: bool
    content_preview: Optional[str]


# ---------------------------------------------------------------------------
# Database helper
# ---------------------------------------------------------------------------




# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/recent-artifacts", response_model=ArtifactsListResponse)
def get_recent_artifacts(
    limit: int = Query(default=20, ge=1, le=100),
    artifact_type: Optional[str] = Query(default=None, description="Filter by artifact type"),
) -> Dict[str, Any]:
    """
    Get recently created artifacts from the artifacts index.

    Args:
        limit: Maximum number of artifacts to return (1-100)
        artifact_type: Optional filter by type (report/ppt/spreadsheet/code/image)

    Returns:
        List of artifacts sorted by creation time, newest first.
    """
    with get_connection() as conn:
        if artifact_type:
            rows = fetchall(
                conn,
                """
                    SELECT * FROM artifacts_index
                    WHERE type = ?
                    ORDER BY created_at DESC
                    LIMIT ?
                """,
                (artifact_type, limit),
            )
        else:
            rows = fetchall(
                conn,
                """
                    SELECT * FROM artifacts_index
                    ORDER BY created_at DESC
                    LIMIT ?
                """,
                (limit,),
            )

    # Check file existence
    for row in rows:
        full_path = os.path.join(BASE_DIR, row["path"])
        row["file_exists"] = os.path.exists(full_path)

    return {"artifacts": rows, "total": len(rows)}


@router.get("/artifacts/{artifact_id}", response_model=ArtifactDetailResponse)
def get_artifact_detail(artifact_id: str) -> Dict[str, Any]:
    """
    Get detailed information about a specific artifact.

    Args:
        artifact_id: Unique artifact identifier

    Returns:
        Artifact metadata with file existence check and content preview.
    """
    with get_connection() as conn:
        row = fetchone(conn, "SELECT * FROM artifacts_index WHERE id = ?", (artifact_id,))

    if not row:
        raise HTTPException(status_code=404, detail=f"Artifact not found: {artifact_id}")

    artifact = row
    full_path = os.path.join(BASE_DIR, artifact["path"])
    exists = os.path.exists(full_path)

    # Content preview for text-based artifacts
    content_preview = None
    if exists and artifact["type"] in ("report", "code"):
        try:
            with open(full_path, "r", encoding="utf-8") as f:
                content_preview = f.read(2000)  # First 2000 chars
        except (UnicodeDecodeError, IOError):
            content_preview = "[Binary file - preview not available]"

    return {
        **artifact,
        "exists": exists,
        "content_preview": content_preview,
    }


@router.get("/artifacts/{artifact_id}/download")
def download_artifact(artifact_id: str):
    """
    Download an artifact file.

    Args:
        artifact_id: Unique artifact identifier

    Returns:
        FileResponse for the artifact file.
    """
    with get_connection() as conn:
        row = fetchone(conn, "SELECT * FROM artifacts_index WHERE id = ?", (artifact_id,))

    if not row:
        raise HTTPException(status_code=404, detail=f"Artifact not found: {artifact_id}")

    artifact = row
    full_path = os.path.join(BASE_DIR, artifact["path"])

    if not os.path.exists(full_path):
        raise HTTPException(
            status_code=404,
            detail=f"Artifact file not found on disk: {artifact['path']}"
        )

    # Determine media type
    media_type = _get_media_type(artifact["type"], artifact["name"])

    return FileResponse(
        path=full_path,
        filename=artifact["name"],
        media_type=media_type,
    )


def _get_media_type(artifact_type: str, filename: str) -> str:
    """Determine MIME type from artifact type and filename extension."""
    ext = os.path.splitext(filename)[1].lower()
    mime_map = {
        ".md": "text/markdown",
        ".txt": "text/plain",
        ".json": "application/json",
        ".py": "text/x-python",
        ".html": "text/html",
        ".pdf": "application/pdf",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".gif": "image/gif",
        ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ".csv": "text/csv",
    }
    return mime_map.get(ext, "application/octet-stream")
