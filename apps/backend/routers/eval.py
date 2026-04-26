"""
Eval Router - Evaluation results, test execution, and regression status.

Provides read-only access to evaluation results and regression test status.
Test execution is triggered via /api/jobs/run-script endpoint.
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
from config import EVALS_DIR, BASE_DIR, ALLOWED_SCRIPTS_SET

router = APIRouter(prefix="/api", tags=["eval"])


# ---------------------------------------------------------------------------
# Response Models
# ---------------------------------------------------------------------------

class EvalResult(BaseModel):
    """Single evaluation result."""
    eval_id: Optional[str] = None
    timestamp: Optional[str] = None
    level: Optional[str] = None
    passed: Optional[bool] = None
    score: Optional[float] = None
    metrics: Optional[Dict[str, Any]] = None
    details: Optional[Dict[str, Any]] = None


class EvalResultsResponse(BaseModel):
    """List of evaluation results."""
    results: List[Dict[str, Any]]
    total: int


class RegressionStatusResponse(BaseModel):
    """Regression test suite status."""
    status: str
    last_run: Optional[str]
    total_tests: int
    passed: int
    failed: int
    skipped: int
    details: Optional[List[Dict[str, Any]]]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _find_eval_result_dirs() -> List[str]:
    """Find all evaluation result directories."""
    if not os.path.exists(EVALS_DIR):
        return []
    dirs = glob.glob(os.path.join(EVALS_DIR, "*", "*"))
    return sorted(dirs, reverse=True)


def _load_eval_result(result_dir: str) -> Optional[Dict[str, Any]]:
    """Load eval-result.json from a result directory."""
    eval_file = os.path.join(result_dir, "eval-result.json")
    if not os.path.exists(eval_file):
        return None
    try:
        with open(eval_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/eval-results", response_model=EvalResultsResponse)
def get_eval_results(
    limit: int = Query(default=10, ge=1, le=50),
    level: Optional[str] = Query(default=None, description="Filter by level (l1/l2/l3)"),
) -> Dict[str, Any]:
    """
    Get evaluation results from evals/results/ directory.

    Scans for eval-result.json files in subdirectories and returns
    the most recent results.

    Args:
        limit: Maximum number of results to return
        level: Filter by evaluation level

    Returns:
        List of evaluation results sorted by recency.
    """
    result_dirs = _find_eval_result_dirs()
    results = []

    for d in result_dirs:
        # Filter by level if specified
        if level and level not in os.path.basename(d):
            continue

        result = _load_eval_result(d)
        if result:
            # Add directory path as metadata
            result["_source_dir"] = d
            result["_dir_name"] = os.path.basename(d)
            results.append(result)

        if len(results) >= limit:
            break

    return {
        "results": results,
        "total": len(results),
    }


@router.get("/eval-results/{eval_id}")
def get_eval_detail(eval_id: str) -> Dict[str, Any]:
    """
    Get detailed information about a specific evaluation.

    Args:
        eval_id: The evaluation identifier (directory name)

    Returns:
        Detailed evaluation result with all metrics.
    """
    # Search for eval_id in result directories
    result_dirs = _find_eval_result_dirs()

    for d in result_dirs:
        if eval_id in os.path.basename(d):
            result = _load_eval_result(d)
            if result:
                # Look for additional files
                detail_files = glob.glob(os.path.join(d, "*.json"))
                detail_files.extend(glob.glob(os.path.join(d, "*.md")))
                detail_files.extend(glob.glob(os.path.join(d, "*.txt")))

                extras = []
                for f in sorted(detail_files):
                    fname = os.path.basename(f)
                    if fname == "eval-result.json":
                        continue
                    try:
                        if f.endswith(".json"):
                            with open(f, "r", encoding="utf-8") as fh:
                                extras.append({
                                    "filename": fname,
                                    "type": "json",
                                    "data": json.load(fh),
                                })
                        else:
                            with open(f, "r", encoding="utf-8") as fh:
                                extras.append({
                                    "filename": fname,
                                    "type": "text",
                                    "content": fh.read(5000),
                                })
                    except (IOError, UnicodeDecodeError, json.JSONDecodeError):
                        extras.append({
                            "filename": fname,
                            "type": "unknown",
                            "error": "Failed to read",
                        })

                return {
                    **result,
                    "_source_dir": d,
                    "extra_files": extras,
                }

    raise HTTPException(status_code=404, detail=f"Evaluation not found: {eval_id}")


@router.get("/regression-status", response_model=RegressionStatusResponse)
def get_regression_status() -> Dict[str, Any]:
    """
    Get regression test suite status.

    Attempts to read regression results from runtime/regression-status.json
    or falls back to running regression_runner.py --status.

    Returns:
        Regression test summary with pass/fail counts.
    """
    # Try to read cached status
    status_path = os.path.join(BASE_DIR, "runtime", "regression-status.json")
    if os.path.exists(status_path):
        try:
            with open(status_path, "r", encoding="utf-8") as f:
                cached = json.load(f)
                return {
                    "status": cached.get("status", "unknown"),
                    "last_run": cached.get("last_run"),
                    "total_tests": cached.get("total_tests", 0),
                    "passed": cached.get("passed", 0),
                    "failed": cached.get("failed", 0),
                    "skipped": cached.get("skipped", 0),
                    "details": cached.get("details", []),
                }
        except (json.JSONDecodeError, IOError):
            pass

    # Fallback: return unknown status
    return {
        "status": "unknown",
        "last_run": None,
        "total_tests": 0,
        "passed": 0,
        "failed": 0,
        "skipped": 0,
        "details": [],
    }


@router.get("/eval-metrics/summary")
def get_eval_metrics_summary() -> Dict[str, Any]:
    """
    Get aggregated evaluation metrics across all runs.

    Computes average scores, pass rates, and trends from
    all available evaluation results.

    Returns:
        Aggregated metrics and trend data.
    """
    result_dirs = _find_eval_result_dirs()
    all_results = []

    for d in result_dirs[:50]:  # Last 50 runs
        result = _load_eval_result(d)
        if result:
            all_results.append(result)

    if not all_results:
        return {
            "total_runs": 0,
            "average_score": 0,
            "pass_rate": 0,
            "trend": [],
        }

    # Calculate metrics
    scores = []
    pass_count = 0
    trend = []

    for r in all_results:
        score = r.get("score") or r.get("overall_score") or r.get("pass_rate")
        if score is not None:
            scores.append(float(score))
        if r.get("passed") == True:
            pass_count += 1

        trend.append({
            "timestamp": r.get("timestamp") or r.get("run_at"),
            "score": score,
            "passed": r.get("passed"),
            "level": r.get("level"),
        })

    avg_score = sum(scores) / len(scores) if scores else 0
    pass_rate = (pass_count / len(all_results) * 100) if all_results else 0

    return {
        "total_runs": len(all_results),
        "average_score": round(avg_score, 2),
        "pass_rate": round(pass_rate, 2),
        "trend": trend[:20],  # Last 20 data points
    }
