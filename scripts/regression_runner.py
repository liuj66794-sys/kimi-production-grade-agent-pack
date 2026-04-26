#!/usr/bin/env python3
"""
regression_runner.py — Regression test runner for Kimi Agent Pack.

Usage:
    python scripts/regression_runner.py --suite l1-regression
    python scripts/regression_runner.py --suite l1-regression --output evals/results/l1-regression

Reads evals/task-suite.yaml for the test list, executes tests in priority order,
and generates a regression report with pass/fail/hard_fail statistics.

Exit codes:
    0 — All required tests passed
    1 — One or more required tests failed
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DEFAULT_TASK_SUITE = "evals/task-suite.yaml"
DEFAULT_OUTPUT_DIR = "evals/results"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_project_root() -> Path:
    """Return the project root directory."""
    return Path(__file__).resolve().parent.parent


def log(msg: str, level: str = "INFO") -> None:
    """Print a formatted log message."""
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%MZ")
    print(f"[{timestamp}] [{level}] {msg}")


def load_task_suite(suite_path: Path) -> list[dict[str, Any]]:
    """Load and parse the task suite YAML file."""
    if not suite_path.is_file():
        log(f"Task suite file not found: {suite_path}", level="ERROR")
        return []

    try:
        import yaml
    except ImportError:
        log("PyYAML not installed, trying built-in parser", level="WARN")
        return _parse_yaml_simple(suite_path.read_text(encoding="utf-8"))

    with open(suite_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if isinstance(data, dict):
        # Handle nested suite format (smoke_tests, unit_smoke_tests, integration_smoke_tests, etc.)
        all_tests: list[dict[str, Any]] = []
        for key, section in data.items():
            if isinstance(section, dict) and "tests" in section:
                all_tests.extend(section["tests"])
            elif isinstance(section, list):
                all_tests.extend(section)
        if all_tests:
            return all_tests
        # Fallback: try root-level tests
        if "tests" in data:
            return data["tests"]
        log("Unexpected task suite format: no tests found in any section", level="ERROR")
        return []
    elif isinstance(data, list):
        return data
    else:
        log("Unexpected task suite format", level="ERROR")
        return []


def _parse_yaml_simple(text: str) -> list[dict[str, Any]]:
    """Minimal YAML list-of-dicts parser as fallback."""
    tests: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("- "):
            if current:
                tests.append(current)
            current = {}
            # Handle inline key: value after '-'
            rest = stripped[2:]
            if ":" in rest:
                k, v = rest.split(":", 1)
                current[k.strip()] = v.strip()
        elif stripped.startswith("  ") and ":" in stripped and current is not None:
            k, v = stripped.split(":", 1)
            current[k.strip()] = v.strip()
    if current:
        tests.append(current)
    return tests


def run_test(test: dict[str, Any], output_dir: Path, verbose: bool) -> dict[str, Any]:
    """Execute a single regression test and return the result."""
    name = test.get("name", "unnamed-test")
    command = test.get("command", "")
    required = test.get("required", "false").lower() in ("true", "yes", "1")
    priority = int(test.get("priority", "99"))
    timeout = int(test.get("timeout", "300"))

    if not command:
        return {
            "name": name,
            "status": "FAIL",
            "required": required,
            "priority": priority,
            "duration_ms": 0,
            "stdout": "",
            "stderr": "No command specified",
        }

    log(f"Running: {name} (priority={priority}, required={required})")

    start = time.perf_counter()
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(get_project_root()),
        )
        duration_ms = int((time.perf_counter() - start) * 1000)

        if result.returncode == 0:
            status = "PASS"
        elif result.returncode == 2:  # Convention: 2 = hard_fail
            status = "HARD_FAIL"
        else:
            status = "FAIL"

        if verbose:
            if result.stdout:
                print(f"  [STDOUT] {result.stdout[:500]}")
            if result.stderr:
                print(f"  [STDERR] {result.stderr[:500]}")

        return {
            "name": name,
            "status": status,
            "required": required,
            "priority": priority,
            "duration_ms": duration_ms,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode,
        }

    except subprocess.TimeoutExpired:
        duration_ms = int((time.perf_counter() - start) * 1000)
        log(f"Test '{name}' timed out after {timeout}s", level="ERROR")
        return {
            "name": name,
            "status": "HARD_FAIL",
            "required": required,
            "priority": priority,
            "duration_ms": duration_ms,
            "stdout": "",
            "stderr": f"Timeout after {timeout} seconds",
        }
    except Exception as exc:
        duration_ms = int((time.perf_counter() - start) * 1000)
        log(f"Test '{name}' raised exception: {exc}", level="ERROR")
        return {
            "name": name,
            "status": "HARD_FAIL",
            "required": required,
            "priority": priority,
            "duration_ms": duration_ms,
            "stdout": "",
            "stderr": str(exc),
        }


def generate_report(
    suite_name: str,
    results: list[dict[str, Any]],
    output_dir: Path,
) -> dict[str, Any]:
    """Generate the regression report."""
    total = len(results)
    passed = sum(1 for r in results if r["status"] == "PASS")
    failed = sum(1 for r in results if r["status"] == "FAIL")
    hard_fail = sum(1 for r in results if r["status"] == "HARD_FAIL")

    required_failed = any(r["status"] != "PASS" and r["required"] for r in results)

    report = {
        "report_type": "regression",
        "suite": suite_name,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "total": total,
            "passed": passed,
            "failed": failed,
            "hard_fail": hard_fail,
            "result": "FAIL" if required_failed else "PASS",
        },
        "tests": results,
    }

    # Write report
    output_dir.mkdir(parents=True, exist_ok=True)
    report_path = output_dir / "regression-report.json"
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    return report, report_path


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Regression test runner for Kimi Agent Pack",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/regression_runner.py --suite l1-regression
  python scripts/regression_runner.py --suite l1-regression --output evals/results/l1-regression
        """,
    )
    parser.add_argument("--suite", required=True, help="Test suite name (e.g., l1-regression)")
    parser.add_argument("--output", default=DEFAULT_OUTPUT_DIR, help="Output directory for results")
    parser.add_argument("--verbose", action="store_true", help="Show test output")
    parser.add_argument("--task-suite", default=DEFAULT_TASK_SUITE, help="Path to task-suite.yaml")
    args = parser.parse_args()

    root = get_project_root()
    suite_path = root / args.task_suite
    output_dir = root / args.output

    print("=" * 50)
    print("  Kimi Agent Pack — Regression Runner")
    print(f"  Suite: {args.suite}")
    print(f"  Task Suite: {suite_path}")
    print(f"  Output: {output_dir}")
    print("=" * 50)
    print()

    # Load tests
    tests = load_task_suite(suite_path)
    if not tests:
        log("No tests found in task suite", level="ERROR")
        return 1

    log(f"Loaded {len(tests)} tests from {suite_path}")

    # Sort by priority (lower = higher priority)
    tests.sort(key=lambda t: int(t.get("priority", "99")))

    # Run tests
    results: list[dict[str, Any]] = []
    for test in tests:
        result = run_test(test, output_dir, args.verbose)
        results.append(result)
        status_icon = "PASS" if result["status"] == "PASS" else "FAIL"
        level = "INFO" if result["status"] == "PASS" else "ERROR"
        log(f"[{status_icon}] {result['name']} ({result['duration_ms']}ms)", level=level)

    # Generate report
    report, report_path = generate_report(args.suite, results, output_dir)
    summary = report["summary"]

    print()
    print("-" * 40)
    log(f"Total:   {summary['total']}")
    log(f"Passed:  {summary['passed']}")
    log(f"Failed:  {summary['failed']}")
    log(f"HardFail:{summary['hard_fail']}")
    log(f"Result:  {summary['result']}")
    log(f"Report:  {report_path}")

    return 0 if summary["result"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
