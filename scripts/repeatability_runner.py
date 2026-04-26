#!/usr/bin/env python3
"""
Repeatability Historical Artifact Review

Reads historical integration-smoke run artifacts and compares
results across multiple runs to check consistency.

Usage:
    python repeatability_runner.py --historical-review
    python repeatability_runner.py --historical-review --runs-dir runs/
    python repeatability_runner.py --historical-review --output repeatability-report.json
"""

import argparse
import json
import os
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

DEFAULT_RUNS_DIR = "runs"
DEFAULT_REPORT_NAME = "repeatability-report.json"


def _iso_timestamp() -> str:
    return datetime.now().isoformat()


def discover_runs(runs_dir: str) -> List[str]:
    """Discover historical run directories."""
    if not os.path.exists(runs_dir):
        return []

    runs = []
    for entry in sorted(os.listdir(runs_dir)):
        run_path = os.path.join(runs_dir, entry)
        if os.path.isdir(run_path):
            # Check for expected artifacts
            artifacts_dir = os.path.join(run_path, "artifacts")
            if os.path.exists(artifacts_dir):
                runs.append(run_path)
    return runs


def load_artifact(run_path: str, artifact_name: str) -> Optional[Any]:
    """Load a specific artifact from a run directory."""
    artifact_path = os.path.join(run_path, "artifacts", artifact_name)
    if not os.path.exists(artifact_path):
        return None
    try:
        with open(artifact_path, "r", encoding="utf-8") as f:
            content = f.read()
            # Try JSON first
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                # Return as string for non-JSON
                return content
    except (IOError, OSError):
        return None


def get_artifact_list(run_path: str) -> List[str]:
    """Get list of artifact files in a run."""
    artifacts_dir = os.path.join(run_path, "artifacts")
    if not os.path.exists(artifacts_dir):
        return []
    try:
        return sorted(os.listdir(artifacts_dir))
    except OSError:
        return []


def compare_values(
    val1: Any, val2: Any, path: str = ""
) -> List[Dict]:
    """Compare two values recursively and return differences."""
    diffs = []

    if type(val1) != type(val2):
        diffs.append({
            "path": path,
            "type": "type_mismatch",
            "run_a_type": type(val1).__name__,
            "run_b_type": type(val2).__name__,
        })
        return diffs

    if isinstance(val1, dict):
        all_keys = set(val1.keys()) | set(val2.keys())
        for key in all_keys:
            subpath = f"{path}.{key}" if path else key
            if key not in val1:
                diffs.append({
                    "path": subpath,
                    "type": "missing_in_run_a",
                    "value_in_run_b": val2[key],
                })
            elif key not in val2:
                diffs.append({
                    "path": subpath,
                    "type": "missing_in_run_b",
                    "value_in_run_a": val1[key],
                })
            else:
                diffs.extend(compare_values(val1[key], val2[key], subpath))
    elif isinstance(val1, list):
        if len(val1) != len(val2):
            diffs.append({
                "path": path,
                "type": "list_length_mismatch",
                "run_a_length": len(val1),
                "run_b_length": len(val2),
            })
        else:
            for i, (a, b) in enumerate(zip(val1, val2)):
                subpath = f"{path}[{i}]"
                diffs.extend(compare_values(a, b, subpath))
    else:
        if val1 != val2:
            diffs.append({
                "path": path,
                "type": "value_mismatch",
                "run_a_value": str(val1)[:100],
                "run_b_value": str(val2)[:100],
            })

    return diffs


def check_artifact_existence(runs: List[str]) -> Dict:
    """Check which artifacts exist across all runs."""
    artifact_presence = defaultdict(list)

    for run in runs:
        artifacts = get_artifact_list(run)
        for artifact in artifacts:
            artifact_presence[artifact].append(run)

    # Check which are present in all runs
    total_runs = len(runs)
    result = {
        "total_runs": total_runs,
        "artifacts_in_all_runs": [],
        "artifacts_in_some_runs": [],
        "artifacts_details": {},
    }

    for artifact, present_in in artifact_presence.items():
        count = len(present_in)
        detail = {
            "artifact": artifact,
            "present_count": count,
            "absent_count": total_runs - count,
            "presence_rate": round(count / total_runs * 100, 1) if total_runs > 0 else 0,
        }
        result["artifacts_details"][artifact] = detail

        if count == total_runs:
            result["artifacts_in_all_runs"].append(artifact)
        else:
            result["artifacts_in_some_runs"].append(artifact)

    return result


def check_field_consistency(
    runs: List[str], artifact_name: str, key_fields: List[str]
) -> Dict:
    """Check if key fields are consistent across runs for a given artifact."""
    field_values = defaultdict(list)

    for run in runs:
        data = load_artifact(run, artifact_name)
        if data is None:
            continue
        if isinstance(data, dict):
            for field in key_fields:
                value = _deep_get(data, field)
                field_values[field].append({"run": run, "value": value})

    consistency = {}
    for field, values in field_values.items():
        if not values:
            consistency[field] = {"status": "no_data", "unique_values": 0}
            continue

        non_none_values = [v["value"] for v in values if v["value"] is not None]
        unique_values = set(json.dumps(v, sort_keys=True) if isinstance(v, (dict, list)) else str(v) for v in non_none_values)

        if len(unique_values) <= 1:
            consistency[field] = {
                "status": "consistent",
                "unique_values": len(unique_values),
                "sample": non_none_values[0] if non_none_values else None,
            }
        else:
            consistency[field] = {
                "status": "inconsistent",
                "unique_values": len(unique_values),
                "values": list(unique_values)[:5],
            }

    return consistency


def check_contradictory_conclusions(runs: List[str]) -> List[Dict]:
    """Check if conclusions contradict across runs."""
    contradictions = []

    # Check report-quality.json
    quality_scores = []
    for run in runs:
        data = load_artifact(run, "report-quality.json")
        if isinstance(data, dict) and "total_score" in data:
            quality_scores.append({
                "run": run,
                "score": data["total_score"],
                "passed": data.get("passed_threshold", False),
            })

    if quality_scores:
        passed_values = [q["passed"] for q in quality_scores]
        if len(set(passed_values)) > 1:
            contradictions.append({
                "type": "quality_gate_flip",
                "description": "Some runs pass quality gate while others fail",
                "details": quality_scores,
            })

        scores = [q["score"] for q in quality_scores]
        if scores:
            score_range = max(scores) - min(scores)
            if score_range > 15:
                contradictions.append({
                    "type": "large_score_variance",
                    "description": f"Score varies by {score_range:.1f} points across runs",
                    "score_range": score_range,
                    "min_score": min(scores),
                    "max_score": max(scores),
                    "details": quality_scores,
                })

    # Check qa-review.json
    qa_results = []
    for run in runs:
        data = load_artifact(run, "qa-review.json")
        if isinstance(data, dict) and "overall_result" in data:
            qa_results.append({
                "run": run,
                "result": data["overall_result"],
            })

    if qa_results:
        unique_results = set(q["result"] for q in qa_results)
        if len(unique_results) > 1:
            contradictions.append({
                "type": "qa_result_flip",
                "description": f"QA results differ: {unique_results}",
                "details": qa_results,
            })

    return contradictions


def _deep_get(data: Dict, path: str, default: Any = None) -> Any:
    """Get a nested dict value by dot-path."""
    keys = path.split(".")
    current = data
    for key in keys:
        if isinstance(current, dict) and key in current:
            current = current[key]
        else:
            return default
    return current


def perform_historical_review(
    runs_dir: str = DEFAULT_RUNS_DIR,
    output_path: Optional[str] = None,
) -> Dict:
    """Perform a full historical review."""
    runs = discover_runs(runs_dir)

    report = {
        "review_id": f"repeatability-review-{_iso_timestamp()}",
        "timestamp": _iso_timestamp(),
        "runs_directory": runs_dir,
        "total_runs_discovered": len(runs),
        "run_paths": runs,
        "checks": {},
        "summary": {
            "all_checks_pass": False,
            "blocking_issues": [],
        },
    }

    if len(runs) < 2:
        report["summary"]["blocking_issues"].append(
            "Insufficient runs for repeatability check (need >= 2)"
        )
        report["summary"]["all_checks_pass"] = False
        _write_report(report, output_path)
        return report

    # Check 1: Artifact existence
    existence = check_artifact_existence(runs)
    report["checks"]["artifact_existence"] = {
        "pass": len(existence["artifacts_in_some_runs"]) == 0,
        "details": existence,
    }
    if not report["checks"]["artifact_existence"]["pass"]:
        report["summary"]["blocking_issues"].append(
            f"Some artifacts missing in some runs: {existence['artifacts_in_some_runs']}"
        )

    # Check 2: Key field consistency
    key_artifacts = {
        "report-quality.json": ["total_score", "passed_threshold", "word_count"],
        "qa-review.json": ["overall_result", "total_score", "gate_result"],
        "task-understanding.json": ["estimated_complexity", "estimated_steps"],
    }

    field_consistency_results = {}
    for artifact, fields in key_artifacts.items():
        consistency = check_field_consistency(runs, artifact, fields)
        field_consistency_results[artifact] = consistency

    all_consistent = all(
        all(c.get("status") == "consistent" for c in artifact_check.values())
        for artifact_check in field_consistency_results.values()
        if artifact_check
    )

    report["checks"]["field_consistency"] = {
        "pass": all_consistent,
        "details": field_consistency_results,
    }
    if not all_consistent:
        report["summary"]["blocking_issues"].append("Key fields inconsistent across runs")

    # Check 3: Contradictory conclusions
    contradictions = check_contradictory_conclusions(runs)
    report["checks"]["contradiction_check"] = {
        "pass": len(contradictions) == 0,
        "contradictions_found": contradictions,
    }
    if contradictions:
        report["summary"]["blocking_issues"].append(
            f"Found {len(contradictions)} contradictions across runs"
        )

    # Check 4: Score fluctuation
    scores = []
    for run in runs:
        data = load_artifact(run, "report-quality.json")
        if isinstance(data, dict) and "total_score" in data:
            scores.append(data["total_score"])

    if scores:
        score_range = max(scores) - min(scores)
        report["checks"]["score_fluctuation"] = {
            "pass": score_range <= 10,
            "score_range": score_range,
            "min_score": min(scores),
            "max_score": max(scores),
            "mean_score": round(sum(scores) / len(scores), 1),
            "scores": scores,
        }
        if score_range > 10:
            report["summary"]["blocking_issues"].append(
                f"Score fluctuation too high: {score_range:.1f} points"
            )
    else:
        report["checks"]["score_fluctuation"] = {
            "pass": False,
            "reason": "No quality scores found",
        }

    # Final summary
    report["summary"]["all_checks_pass"] = (
        len(report["summary"]["blocking_issues"]) == 0
    )

    _write_report(report, output_path)
    return report


def _write_report(report: Dict, output_path: Optional[str]):
    """Write report to file if path is provided."""
    if output_path:
        dir_name = os.path.dirname(output_path)
        if dir_name and not os.path.exists(dir_name):
            os.makedirs(dir_name, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        print(f"Repeatability report written to: {output_path}")


def print_report(report: Dict):
    """Print report in human-readable format."""
    print("=" * 60)
    print("  Repeatability Historical Artifact Review")
    print("=" * 60)
    print(f"\n  Review ID: {report['review_id']}")
    print(f"  Runs Directory: {report['runs_directory']}")
    print(f"  Total Runs: {report['total_runs_discovered']}")
    print(f"  Timestamp: {report['timestamp']}")
    print()

    for check_name, check_data in report["checks"].items():
        status = "[PASS]" if check_data.get("pass") else "[FAIL]"
        print(f"  {status} {check_name}")
        if not check_data.get("pass") and "details" in check_data:
            if isinstance(check_data["details"], dict):
                for k, v in check_data["details"].items():
                    if isinstance(v, str):
                        print(f"       {k}: {v}")

    print()
    print(f"  Overall: {'ALL CHECKS PASSED' if report['summary']['all_checks_pass'] else 'ISSUES FOUND'}")

    if report["summary"]["blocking_issues"]:
        print(f"\n  Blocking Issues:")
        for issue in report["summary"]["blocking_issues"]:
            print(f"    - {issue}")

    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description="Repeatability Historical Artifact Review"
    )
    parser.add_argument(
        "--historical-review",
        action="store_true",
        required=True,
        help="Perform historical review (required flag)",
    )
    parser.add_argument(
        "--runs-dir",
        default=DEFAULT_RUNS_DIR,
        help=f"Directory containing historical runs (default: {DEFAULT_RUNS_DIR})",
    )
    parser.add_argument(
        "--output",
        default=DEFAULT_REPORT_NAME,
        help=f"Output path for report (default: {DEFAULT_REPORT_NAME})",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Only output JSON",
    )

    args = parser.parse_args()

    report = perform_historical_review(
        runs_dir=args.runs_dir,
        output_path=args.output,
    )

    if not args.quiet:
        print_report(report)
    else:
        print(json.dumps(report, indent=2, ensure_ascii=False))

    # Exit code based on results
    sys.exit(0 if report["summary"]["all_checks_pass"] else 1)


if __name__ == "__main__":
    main()
