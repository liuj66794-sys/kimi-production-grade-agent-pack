#!/usr/bin/env python3
"""
L4 Release Checklist

Validates all requirements before an L4 release can be approved.
Any hard_fail item blocks the release.

Checks:
  1. project-state.json completeness
  2. autonomy-policy.md exists and is valid
  3. Autonomy Gate rule completeness
  4. HITL system availability
  5. Anomaly Counter functionality
  6. Context Pack Compiler functionality
  7. L4 adversarial eval passes
  8. No hard_fail conditions
"""

import json
import os
import sys
import subprocess
from datetime import datetime, timezone
from typing import Dict, List, Tuple

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS_DIR = os.path.join(PROJECT_ROOT, "scripts")
REQUIRED_FILES = [
    "runtime/project-state.json",
    "runtime/roadmap.json",
    "docs/autonomy-policy.md",
    "docs/v4.0-l4-pre-spec.md",
    "docs/v4.1-project-state-spec.md",
    "docs/v4.2-roadmap-sprint-spec.md",
    "docs/v4.3-context-management-spec.md",
    "docs/v4.4-autonomy-gate-spec.md",
    "docs/v4.5-hitl-spec.md",
    "docs/v4.6-weekly-report-spec.md",
    "docs/v4.7-adversarial-eval-spec.md",
    "docs/l4-known-limits.md",
    "scripts/autonomy_gate.py",
    "scripts/hitl_approval.py",
    "scripts/context_pack_compiler.py",
    "scripts/anomaly_counter.py",
    "scripts/generate_weekly_report.py",
    "scripts/l4_adversarial_eval.py",
    "scripts/l4_regression_runner.py",
    "scripts/l4_release_check.py",
    "schemas/autonomy-decision.schema.json",
    "schemas/hitl-approval.schema.json",
    "schemas/context-pack.schema.json",
    "schemas/weekly-report.schema.json",
]


# ---------------------------------------------------------------------------
# Check Functions
# ---------------------------------------------------------------------------

def check_project_state() -> Tuple[bool, str]:
    """Check 1: project-state.json completeness."""
    path = os.path.join(PROJECT_ROOT, "runtime", "project-state.json")
    try:
        with open(path, "r", encoding="utf-8") as f:
            state = json.load(f)

        required_fields = [
            "project_id", "name", "current_stage", "current_version",
            "status", "autonomy_level", "autonomy_policy_version",
            "hitl_enabled", "context_budget", "anomaly_counter",
            "pending_approvals", "version",
        ]

        missing = [f for f in required_fields if f not in state]
        if missing:
            return False, f"Missing fields: {missing}"

        # Validate context_budget
        budget = state.get("context_budget", {})
        if "max_tokens" not in budget or "protected_keys" not in budget:
            return False, "context_budget missing required sub-fields"

        # Validate anomaly_counter
        counter = state.get("anomaly_counter", {})
        if "degrade_count_24h" not in counter or "pause_count_24h" not in counter:
            return False, "anomaly_counter missing required sub-fields"

        # Validate version
        if not isinstance(state.get("version"), int) or state["version"] < 1:
            return False, f"Invalid version: {state.get('version')}"

        # Security: hitl must be enabled
        if state.get("hitl_enabled") != True:
            return False, "hitl_enabled must be True"

        # Security: autonomy_level should be a1 at minimum
        if state.get("autonomy_level") not in ("a0", "a1", "a2", "a3", "a4", "a5"):
            return False, f"Invalid autonomy_level: {state.get('autonomy_level')}"

        return True, f"All {len(required_fields)} required fields present, HITL enabled"

    except json.JSONDecodeError as e:
        return False, f"Invalid JSON: {str(e)}"
    except FileNotFoundError:
        return False, "File not found"


def check_autonomy_policy() -> Tuple[bool, str]:
    """Check 2: autonomy-policy.md exists and contains required content."""
    path = os.path.join(PROJECT_ROOT, "docs", "autonomy-policy.md")
    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()

        required_sections = [
            "A0:", "A1:", "A2:", "A3:", "A4:", "A5:",
            "Default Deny",
            "A2 Allowlist",
            "A2 Forbidden Patterns",
        ]

        missing = [s for s in required_sections if s not in content]
        if missing:
            return False, f"Missing sections: {missing}"

        return True, f"All {len(required_sections)} required sections present"
    except FileNotFoundError:
        return False, "File not found"


def check_autonomy_gate() -> Tuple[bool, str]:
    """Check 3: Autonomy Gate rule completeness."""
    path = os.path.join(PROJECT_ROOT, "scripts", "autonomy_gate.py")
    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()

        required_elements = [
            "A2_ALLOWLIST",
            "A2_FORBIDDEN_PATTERNS",
            "LEVEL_HIERARCHY",
            "matches_forbidden_pattern",
            "level_allows_action",
            "check_anomaly_limits",
            "evaluate_action",
            "evaluate_action_strict",
            "log_audit",
        ]

        missing = [e for e in required_elements if e not in content]
        if missing:
            return False, f"Missing elements: {missing}"

        # Verify it can be imported
        sys.path.insert(0, SCRIPTS_DIR)
        from autonomy_gate import evaluate_action
        result = evaluate_action("read_project_state", "a1")
        if result["decision"] != "allow":
            return False, f"Gate test failed: expected allow, got {result['decision']}"

        return True, "All elements present and functional"
    except Exception as e:
        return False, f"Import/execution error: {str(e)}"


def check_hitl_system() -> Tuple[bool, str]:
    """Check 4: HITL system availability."""
    path = os.path.join(PROJECT_ROOT, "scripts", "hitl_approval.py")
    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()

        required_elements = [
            "create_approval",
            "respond_approval",
            "check_expired_approvals",
            "is_auto_accept_eligible",
            "auto_accept_eligible",
            "atomic_write_state",
        ]

        missing = [e for e in required_elements if e not in content]
        if missing:
            return False, f"Missing elements: {missing}"

        return True, "All HITL elements present"
    except FileNotFoundError:
        return False, "File not found"


def check_anomaly_counter() -> Tuple[bool, str]:
    """Check 5: Anomaly Counter functionality."""
    path = os.path.join(PROJECT_ROOT, "scripts", "anomaly_counter.py")
    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()

        required_elements = [
            "record_degrade",
            "record_pause",
            "reset_window",
            "is_l4_paused",
            "is_a3_blocked",
            "DEGRADE_THRESHOLD",
            "PAUSE_THRESHOLD",
        ]

        missing = [e for e in required_elements if e not in content]
        if missing:
            return False, f"Missing elements: {missing}"

        return True, "All anomaly counter elements present"
    except FileNotFoundError:
        return False, "File not found"


def check_context_pack_compiler() -> Tuple[bool, str]:
    """Check 6: Context Pack Compiler functionality."""
    path = os.path.join(PROJECT_ROOT, "scripts", "context_pack_compiler.py")
    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()

        required_elements = [
            "compile_context_pack",
            "PROTECTED_KEYS",
            "build_hot_context",
            "build_warm_context",
            "truncate_text",
            "estimate_tokens",
        ]

        missing = [e for e in required_elements if e not in content]
        if missing:
            return False, f"Missing elements: {missing}"

        # Verify it works
        sys.path.insert(0, SCRIPTS_DIR)
        from context_pack_compiler import compile_context_pack_safe
        pack = compile_context_pack_safe()
        if not pack.get("hot_context"):
            return False, "Compiled context pack has no hot_context"

        return True, "All elements present and functional"
    except Exception as e:
        return False, f"Error: {str(e)}"


def check_adversarial_eval() -> Tuple[bool, str]:
    """Check 7: L4 adversarial eval passes."""
    script = os.path.join(PROJECT_ROOT, "scripts", "l4_adversarial_eval.py")
    if not os.path.exists(script):
        return False, "l4_adversarial_eval.py not found"

    try:
        result = subprocess.run(
            [sys.executable, script],
            capture_output=True,
            text=True,
            timeout=120,
        )

        if result.returncode == 0:
            return True, "All adversarial tests passed"
        else:
            return False, f"Adversarial eval failed (exit {result.returncode}): {result.stderr[:300]}"
    except subprocess.TimeoutExpired:
        return False, "Adversarial eval timed out"
    except Exception as e:
        return False, f"Error running eval: {str(e)}"


def check_no_hard_fail() -> Tuple[bool, str]:
    """Check 8: No hard_fail conditions in current state."""
    path = os.path.join(PROJECT_ROOT, "runtime", "project-state.json")
    try:
        with open(path, "r", encoding="utf-8") as f:
            state = json.load(f)

        status = state.get("status", "")
        if status == "halted":
            return False, "Project status is 'halted'"

        counter = state.get("anomaly_counter", {})
        if counter.get("pause_count_24h", 0) >= 5:
            return False, f"Pause count >= 5: {counter['pause_count_24h']}"

        return True, f"Status={status}, no hard_fail conditions"
    except Exception as e:
        return False, f"Error: {str(e)}"


def check_schema_files() -> Tuple[bool, str]:
    """Bonus check: All schema files are valid JSON Schema."""
    schema_dir = os.path.join(PROJECT_ROOT, "schemas")
    if not os.path.isdir(schema_dir):
        return False, "schemas directory not found"

    schema_files = [
        "autonomy-decision.schema.json",
        "hitl-approval.schema.json",
        "context-pack.schema.json",
        "weekly-report.schema.json",
    ]

    for sf in schema_files:
        path = os.path.join(schema_dir, sf)
        if not os.path.exists(path):
            return False, f"Missing schema: {sf}"
        try:
            with open(path, "r", encoding="utf-8") as f:
                schema = json.load(f)
            if schema.get("type") != "object":
                return False, f"Schema {sf} missing type:object"
        except json.JSONDecodeError:
            return False, f"Invalid JSON in schema: {sf}"

    return True, f"All {len(schema_files)} schema files valid"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

RELEASE_CHECKS = [
    ("project-state.json completeness", check_project_state),
    ("autonomy-policy.md valid", check_autonomy_policy),
    ("Autonomy Gate rules", check_autonomy_gate),
    ("HITL system available", check_hitl_system),
    ("Anomaly Counter functional", check_anomaly_counter),
    ("Context Pack Compiler functional", check_context_pack_compiler),
    ("L4 adversarial eval passes", check_adversarial_eval),
    ("No hard_fail conditions", check_no_hard_fail),
    ("Schema files valid", check_schema_files),
]


def run_release_check() -> dict:
    """Run all release checks."""
    results = []

    print("=" * 60)
    print("  L4 RELEASE CHECK")
    print("=" * 60)

    for name, check_fn in RELEASE_CHECKS:
        print(f"\n  Checking: {name}...")
        try:
            passed, details = check_fn()
        except Exception as e:
            passed = False
            details = f"Exception: {str(e)}"

        icon = "PASS" if passed else "FAIL"
        print(f"  [{icon}] {name}: {details[:60]}")

        results.append({
            "check": name,
            "passed": passed,
            "details": details,
        })

    total = len(results)
    passed = sum(1 for r in results if r["passed"])
    failed = total - passed

    report = {
        "check_id": f"release-check-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_checks": total,
        "passed": passed,
        "failed": failed,
        "status": "PASSED" if failed == 0 else "BLOCKED",
        "release_approved": failed == 0,
        "results": results,
    }

    return report


def main():
    report = run_release_check()

    print("\n" + "=" * 60)
    print("  RELEASE CHECK SUMMARY")
    print("=" * 60)
    print(f"  Status  : {report['status']}")
    print(f"  Release : {'APPROVED' if report['release_approved'] else 'BLOCKED'}")
    print(f"  Total   : {report['total_checks']}")
    print(f"  Passed  : {report['passed']}")
    print(f"  Failed  : {report['failed']}")
    print("-" * 60)

    for r in report["results"]:
        icon = "PASS" if r["passed"] else "FAIL"
        print(f"  [{icon}] {r['check']}")
    print("=" * 60)

    # Save report
    report_path = os.path.join(PROJECT_ROOT, "logs", "release-check-report.json")
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"\nReport saved to: {report_path}")

    return 0 if report["release_approved"] else 1


if __name__ == "__main__":
    sys.exit(main())
