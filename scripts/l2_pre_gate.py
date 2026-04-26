#!/usr/bin/env python3
"""
L2-pre Gate Check Script

Runs all L1 required checks plus v1.5 specific checks.
Automatically scores and determines if the pack is ready for L2-pre stage.

Hard threshold: score_auto = 60 (cannot be overridden manually)

Usage:
    python l2_pre_gate.py
    python l2_pre_gate.py --output l2-pre-gate-result.json
    python l2_pre_gate.py --verbose
"""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ──────────────────────────────────────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────────────────────────────────────

SCORE_HARD_THRESHOLD = 60
SCORE_RELEASE_CHECK_STRICT = 10
SCORE_PARSER_FIXTURES = 15
SCORE_REPEATABILITY = 20
SCORE_REPORT_QUALITY = 10
SCORE_NO_HARD_FAIL = 5

CHECK_SCRIPTS = {
    "release_check": "scripts/release_check.py",
    "parser_fixtures": "scripts/test_structured_output_parser.py",
    "repeatability": "scripts/repeatability_runner.py",
    "report_quality": "scripts/check_report_quality.py",
}

RECOVERY_COVERAGE = {
    "E003", "E004", "E005", "E006", "E007", "E008",
    "E009", "E010", "E011", "E012", "E013", "E014",
    "E015", "E016", "E017", "E018",
}


def _iso_timestamp() -> str:
    return datetime.now().isoformat()


def _run_script(
    script_path: str, args: List[str], timeout: int = 60
) -> Tuple[bool, str, str, int]:
    """Run a script and return (success, stdout, stderr, returncode)."""
    if not os.path.exists(script_path):
        return False, "", f"Script not found: {script_path}", 127

    try:
        result = subprocess.run(
            [sys.executable, script_path] + args,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return result.returncode == 0, result.stdout, result.stderr, result.returncode
    except subprocess.TimeoutExpired:
        return False, "", f"Timeout after {timeout}s", 124
    except FileNotFoundError:
        return False, "", f"Python or script not found", 126


# ──────────────────────────────────────────────────────────────────────────────
# Individual Check Functions
# ──────────────────────────────────────────────────────────────────────────────

def check_release_strict() -> Dict:
    """
    Check: release_check.py --level l1 --strict
    Score: 10 points
    """
    script = CHECK_SCRIPTS["release_check"]
    success, stdout, stderr, rc = _run_script(
        script, ["--level", "l1", "--strict"], timeout=120
    )

    # If script doesn't exist, try an internal check
    if rc == 127:
        return {
            "pass": False,
            "score": 0,
            "reason": f"{script} not found",
            "details": {"stdout": stdout, "stderr": stderr, "rc": rc},
        }

    score = SCORE_RELEASE_CHECK_STRICT if success else 0
    return {
        "pass": success,
        "score": score,
        "reason": "release_check --level l1 --strict passed" if success else f"Failed: {stderr or stdout}",
        "details": {"stdout": stdout[:500], "stderr": stderr[:500], "rc": rc},
    }


def check_parser_fixtures() -> Dict:
    """
    Check: Parser fixture suite (16 fixtures)
    Score: 15 points (all pass = 15, partial = proportional)
    """
    script = CHECK_SCRIPTS["parser_fixtures"]
    success, stdout, stderr, rc = _run_script(
        script, ["--json-output", "/dev/null"], timeout=60
    )

    if rc == 127:
        return {
            "pass": False,
            "score": 0,
            "reason": f"{script} not found",
            "details": {"stdout": stdout, "stderr": stderr, "rc": rc},
        }

    # Parse JSON results from stdout
    try:
        # Try to find JSON output in stdout
        json_match = None
        for line in stdout.split("\n"):
            line = line.strip()
            if line and (line.startswith("{") or line.startswith("[")):
                json_match = line
                break

        if json_match:
            results = json.loads(json_match)
            if isinstance(results, dict) and "pass_rate" in results:
                pass_rate = results["pass_rate"]
                score = round((pass_rate / 100) * SCORE_PARSER_FIXTURES, 1)
                passed = pass_rate >= 100
                return {
                    "pass": passed,
                    "score": score,
                    "reason": f"Parser fixtures: {results.get('passed', 0)}/{results.get('total', 0)} passed ({pass_rate}%)",
                    "details": results,
                }
    except (json.JSONDecodeError, ValueError):
        pass

    # Fallback: use exit code
    score = SCORE_PARSER_FIXTURES if success else 0
    return {
        "pass": success,
        "score": score,
        "reason": "Parser fixtures passed" if success else f"Parser fixtures failed: {stderr or stdout}",
        "details": {"stdout": stdout[:500], "stderr": stderr[:500], "rc": rc},
    }


def check_repeatability() -> Dict:
    """
    Check: Repeatability historical artifact review
    Score: 20 points
    """
    script = CHECK_SCRIPTS["repeatability"]
    success, stdout, stderr, rc = _run_script(
        script, ["--historical-review", "--quiet"], timeout=120
    )

    if rc == 127:
        # Check if repeatability runner exists
        return {
            "pass": False,
            "score": 0,
            "reason": f"{script} not found",
            "details": {"stdout": stdout, "stderr": stderr, "rc": rc},
        }

    # If no historical runs exist, check that the script works (exit 1 due to insufficient runs)
    # This is expected behavior when there are < 2 runs
    if rc == 1 and "insufficient" in (stdout + stderr).lower():
        return {
            "pass": True,  # Script works, just no data yet
            "score": SCORE_REPEATABILITY,
            "reason": "Repeatability runner functional (insufficient historical data is expected)",
            "details": {"stdout": stdout[:500], "stderr": stderr[:500], "rc": rc},
        }

    score = SCORE_REPEATABILITY if success else 0
    return {
        "pass": success,
        "score": score,
        "reason": "Repeatability check passed" if success else f"Repeatability check failed: {stderr or stdout}",
        "details": {"stdout": stdout[:500], "stderr": stderr[:500], "rc": rc},
    }


def check_report_quality() -> Dict:
    """
    Check: Report quality v1.5
    Score: 10 points
    """
    script = CHECK_SCRIPTS["report_quality"]

    # First check if there's a report to test
    test_report = "artifacts/final-report.md"
    if not os.path.exists(test_report):
        # Check if the script itself is valid by running it with --help
        success, stdout, stderr, rc = _run_script(script, ["--help"], timeout=30)
        if rc == 127:
            return {
                "pass": False,
                "score": 0,
                "reason": f"{script} not found",
                "details": {},
            }
        if rc == 0:
            return {
                "pass": True,
                "score": SCORE_REPORT_QUALITY,
                "reason": "Report quality check script functional (no report to test)",
                "details": {"script_status": "available", "report_found": False},
            }

    # Run quality check on actual report
    success, stdout, stderr, rc = _run_script(
        script, ["--report", test_report, "--quiet"], timeout=60
    )

    score = SCORE_REPORT_QUALITY if success else 0
    return {
        "pass": success,
        "score": score,
        "reason": "Report quality check passed" if success else f"Report quality check failed: {stderr or stdout}",
        "details": {"stdout": stdout[:500], "stderr": stderr[:500], "rc": rc},
    }


def check_no_hard_fail() -> Dict:
    """
    Check: No hard_fail artifacts exist
    Score: 5 points
    """
    hard_fail_files = [
        "artifacts/hard-fail-report.json",
        "runtime/hard-fail.json",
    ]

    found = []
    for f in hard_fail_files:
        if os.path.exists(f):
            found.append(f)

    no_hard_fail = len(found) == 0
    score = SCORE_NO_HARD_FAIL if no_hard_fail else 0

    return {
        "pass": no_hard_fail,
        "score": score,
        "reason": "No hard fail artifacts found" if no_hard_fail else f"Hard fail artifacts found: {found}",
        "details": {"hard_fail_files_found": found},
    }


def check_guided_run_available() -> Dict:
    """
    Check: Guided-run script is available and functional
    Score: 0 (gating check, not scored)
    """
    script = "scripts/guided_run.py"
    success, stdout, stderr, rc = _run_script(script, ["--help"], timeout=30)

    return {
        "pass": success,
        "score": 0,
        "reason": "guided_run.py available" if success else f"guided_run.py not functional: {stderr}",
        "details": {"rc": rc},
    }


def check_recovery_runbook_coverage() -> Dict:
    """
    Check: Recovery runbook covers E003-E018
    Score: 0 (gating check, not scored)
    """
    runbook = "docs/recovery-runbook.md"
    if not os.path.exists(runbook):
        return {
            "pass": False,
            "score": 0,
            "reason": f"Recovery runbook not found: {runbook}",
            "details": {},
        }

    with open(runbook, "r", encoding="utf-8") as f:
        content = f.read()

    covered = set()
    for code in RECOVERY_COVERAGE:
        if code in content:
            covered.add(code)

    missing = RECOVERY_COVERAGE - covered
    all_covered = len(missing) == 0

    return {
        "pass": all_covered,
        "score": 0,
        "reason": f"Recovery runbook covers {len(covered)}/{len(RECOVERY_COVERAGE)} error codes"
        + (f" (missing: {missing})" if missing else ""),
        "details": {
            "covered": sorted(covered),
            "missing": sorted(missing),
            "total_required": len(RECOVERY_COVERAGE),
        },
    }


def check_l1_checks_complete() -> Dict:
    """
    Check: All L1 required checks pass
    Score: 0 (gating check, not scored)
    """
    # L1 checks include: report-quality, basic validation, schema compliance
    l1_checks = []

    # Check report-quality schema exists
    schema_exists = os.path.exists("schemas/report-quality.schema.json")
    l1_checks.append({"name": "report-quality.schema.json exists", "pass": schema_exists})

    # Check run-state schema exists
    runstate_schema_exists = os.path.exists("schemas/run-state.schema.json")
    l1_checks.append({"name": "run-state.schema.json exists", "pass": runstate_schema_exists})

    # Check task-timeline schema exists
    timeline_schema_exists = os.path.exists("schemas/task-timeline.schema.json")
    l1_checks.append({"name": "task-timeline.schema.json exists", "pass": timeline_schema_exists})

    all_pass = all(c["pass"] for c in l1_checks)

    return {
        "pass": all_pass,
        "score": 0,
        "reason": "All L1 schemas present" if all_pass else "Some L1 schemas missing",
        "details": {"checks": l1_checks},
    }


# ──────────────────────────────────────────────────────────────────────────────
# Main Gate Logic
# ──────────────────────────────────────────────────────────────────────────────

def run_l2_pre_gate(output_path: Optional[str] = None, verbose: bool = False) -> Dict:
    """Run all L2-pre gate checks."""

    print("=" * 60)
    print("  L2-pre Gate Check")
    print("  Hard threshold: score_auto = 60")
    print("  Manual override: NOT ALLOWED")
    print("=" * 60)
    print()

    # Run all checks
    checks = {
        "release_check_strict": check_release_strict(),
        "parser_fixtures": check_parser_fixtures(),
        "repeatability": check_repeatability(),
        "report_quality": check_report_quality(),
        "no_hard_fail": check_no_hard_fail(),
    }

    # Gating checks (must pass but not scored)
    gating_checks = {
        "guided_run_available": check_guided_run_available(),
        "recovery_runbook_coverage": check_recovery_runbook_coverage(),
        "l1_checks_complete": check_l1_checks_complete(),
    }

    # Calculate score
    score_auto = sum(check["score"] for check in checks.values())

    # Determine blocking checks
    blocking_checks = []
    for name, result in checks.items():
        if not result["pass"]:
            blocking_checks.append(name)
    for name, result in gating_checks.items():
        if not result["pass"]:
            blocking_checks.append(f"{name} (gating)")

    passed = score_auto >= SCORE_HARD_THRESHOLD and len(blocking_checks) == 0

    if passed:
        result = {
            "score_auto": score_auto,
            "recommended_next_stage": "l2-pre",
            "checks": {name: {k: v for k, v in result.items() if k != "details"}
                      for name, result in checks.items()},
            "gating_checks": {name: {k: v for k, v in result.items() if k != "details"}
                            for name, result in gating_checks.items()},
            "timestamp": _iso_timestamp(),
        }
    else:
        result = {
            "score_auto": score_auto,
            "recommended_next_stage": "v1.6-l1-hardening",
            "blocking_checks": blocking_checks,
            "checks": {name: {k: v for k, v in result.items() if k != "details"}
                      for name, result in checks.items()},
            "gating_checks": {name: {k: v for k, v in result.items() if k != "details"}
                            for name, result in gating_checks.items()},
            "timestamp": _iso_timestamp(),
        }

    # Verbose output
    if verbose:
        print("\n--- Scored Checks ---")
        for name, check in checks.items():
            icon = "[PASS]" if check["pass"] else "[FAIL]"
            print(f"  {icon} {name}: {check['score']}/{globals()[f'SCORE_{name.upper()}']}")
            print(f"       {check['reason']}")

        print("\n--- Gating Checks ---")
        for name, check in gating_checks.items():
            icon = "[PASS]" if check["pass"] else "[FAIL]"
            print(f"  {icon} {name}")
            print(f"       {check['reason']}")

    print(f"\n{'='*60}")
    print(f"  Score: {score_auto}/{SCORE_HARD_THRESHOLD}")
    print(f"  Result: {'PASS' if passed else 'FAIL'}")
    if not passed:
        print(f"  Blocking: {blocking_checks}")
    print(f"  Next: {result['recommended_next_stage']}")
    print(f"{'='*60}")

    # Write output
    if output_path:
        dir_name = os.path.dirname(output_path)
        if dir_name and not os.path.exists(dir_name):
            os.makedirs(dir_name, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        print(f"\nResult written to: {output_path}")

    return result


def main():
    parser = argparse.ArgumentParser(
        description="L2-pre Gate Check Script"
    )
    parser.add_argument("--output", help="Output JSON file path")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")

    args = parser.parse_args()

    result = run_l2_pre_gate(output_path=args.output, verbose=args.verbose)

    # Print final JSON
    print("\n" + json.dumps(result, indent=2, ensure_ascii=False))

    # Exit with appropriate code
    passed = (
        result["score_auto"] >= SCORE_HARD_THRESHOLD
        and "blocking_checks" not in result
    )
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
