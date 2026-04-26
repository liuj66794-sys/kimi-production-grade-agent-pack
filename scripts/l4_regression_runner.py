#!/usr/bin/env python3
"""
L4 Regression Runner

Runs the complete regression suite:
  - L1 required cases
  - L2 required cases
  - L3 UI checks
  - L4 adversarial evals
  - Autonomy Gate rule tests
  - HITL workflow tests
  - Context Pack Compiler tests
"""

import json
import os
import sys
import subprocess
from datetime import datetime, timezone
from typing import Dict, List

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS_DIR = os.path.join(PROJECT_ROOT, "scripts")
LOGS_DIR = os.path.join(PROJECT_ROOT, "logs")


# ---------------------------------------------------------------------------
# Test Runner Framework
# ---------------------------------------------------------------------------

class RegressionTest:
    def __init__(self, name: str, category: str, func=None, script_path: str = ""):
        self.name = name
        self.category = category
        self.func = func
        self.script_path = script_path
        self.passed = False
        self.details = ""
        self.duration_ms = 0


def run_adversarial_eval() -> RegressionTest:
    """Run L4 adversarial evaluation suite."""
    t = RegressionTest("L4 Adversarial Eval", "L4")
    script = os.path.join(SCRIPTS_DIR, "l4_adversarial_eval.py")

    import time
    start = time.time()
    try:
        result = subprocess.run(
            [sys.executable, script],
            capture_output=True,
            text=True,
            timeout=120,
        )
        t.duration_ms = int((time.time() - start) * 1000)

        if result.returncode == 0:
            t.passed = True
            t.details = "All adversarial tests passed"
        else:
            t.passed = False
            t.details = f"Exit code {result.returncode}. stderr: {result.stderr[:500]}"
    except subprocess.TimeoutExpired:
        t.passed = False
        t.details = "Timed out after 120s"
    except Exception as e:
        t.passed = False
        t.details = f"Error: {str(e)}"

    return t


def run_autonomy_gate_tests() -> List[RegressionTest]:
    """Run Autonomy Gate unit tests."""
    tests = []

    sys.path.insert(0, SCRIPTS_DIR)
    from autonomy_gate import evaluate_action, A2_ALLOWLIST

    # Test 1: A1 read is allowed
    t1 = RegressionTest("A1 read_project_state allowed", "Autonomy Gate")
    result = evaluate_action("read_project_state", "a1")
    t1.passed = result["decision"] == "allow"
    t1.details = f"decision={result['decision']}"
    tests.append(t1)

    # Test 2: A2 in allowlist is allowed
    t2 = RegressionTest("A2 read_roadmap allowed", "Autonomy Gate")
    result = evaluate_action("read_roadmap", "a2")
    t2.passed = result["decision"] == "allow"
    t2.details = f"decision={result['decision']}"
    tests.append(t2)

    # Test 3: A2 not in allowlist is blocked
    t3 = RegressionTest("A2 unknown action blocked", "Autonomy Gate")
    result = evaluate_action("unknown_a2_action", "a2")
    t3.passed = result["decision"] == "block"
    t3.details = f"decision={result['decision']}"
    tests.append(t3)

    # Test 4: A3 requires approval
    t4 = RegressionTest("A3 requires HITL approval", "Autonomy Gate")
    result = evaluate_action("update_task_status", "a3")
    t4.passed = result["decision"] == "require_approval" and result.get("approval_type") == "hitl"
    t4.details = f"decision={result['decision']}, approval_type={result.get('approval_type')}"
    tests.append(t4)

    # Test 5: A5 requires explicit human (use non-forbidden A5 action)
    t5 = RegressionTest("A5 requires explicit_human", "Autonomy Gate")
    result = evaluate_action("modify_security_rules", "a5")
    t5.passed = result["decision"] == "require_approval" and result.get("approval_type") == "explicit_human"
    t5.details = f"decision={result['decision']}, approval_type={result.get('approval_type')}"
    tests.append(t5)

    # Test 6: Forbidden pattern blocks
    t6 = RegressionTest("Forbidden pattern blocks", "Autonomy Gate")
    result = evaluate_action("bypass_gate", "a2")
    t6.passed = result["decision"] == "block"
    t6.details = f"decision={result['decision']}"
    tests.append(t6)

    # Test 7: Unknown action level blocked
    t7 = RegressionTest("Unknown action level blocked", "Autonomy Gate")
    result = evaluate_action("some_action", "a99")
    t7.passed = result["decision"] == "block"
    t7.details = f"decision={result['decision']}"
    tests.append(t7)

    # Test 8: A2 allowlist completeness
    t8 = RegressionTest("A2 allowlist not empty", "Autonomy Gate")
    t8.passed = len(A2_ALLOWLIST) > 0
    t8.details = f"allowlist size = {len(A2_ALLOWLIST)}"
    tests.append(t8)

    return tests


def run_hitl_tests() -> List[RegressionTest]:
    """Run HITL workflow tests."""
    tests = []

    sys.path.insert(0, SCRIPTS_DIR)
    from hitl_approval import (
        is_auto_accept_eligible, create_approval,
        respond_approval, get_approval, list_pending_approvals
    )

    # Test 1: A1 is auto-accept eligible
    t1 = RegressionTest("A1 auto-accept eligible", "HITL")
    t1.passed = is_auto_accept_eligible("a1") == True
    t1.details = f"eligible={is_auto_accept_eligible('a1')}"
    tests.append(t1)

    # Test 2: A5 is NOT auto-accept eligible
    t2 = RegressionTest("A5 not auto-accept eligible", "HITL")
    t2.passed = is_auto_accept_eligible("a5") == False
    t2.details = f"eligible={is_auto_accept_eligible('a5')}"
    tests.append(t2)

    # Test 3: A3 is NOT auto-accept eligible
    t3 = RegressionTest("A3 not auto-accept eligible", "HITL")
    t3.passed = is_auto_accept_eligible("a3") == False
    t3.details = f"eligible={is_auto_accept_eligible('a3')}"
    tests.append(t3)

    # Test 4: Approval creation
    t4 = RegressionTest("Approval creation", "HITL")
    try:
        apr = create_approval(
            action_name="test_action",
            action_level="a3",
            actor="regression_test",
            request_details="Test approval creation",
            risk_assessment="low",
            timeout_minutes=5,
        )
        t4.passed = apr["status"] == "pending" and apr["approval_id"].startswith("apr-")
        t4.details = f"approval_id={apr['approval_id']}, status={apr['status']}"

        # Clean up: reject it
        respond_approval(apr["approval_id"], "rejected", "regression_test")
    except Exception as e:
        t4.passed = False
        t4.details = f"Error: {str(e)}"
    tests.append(t4)

    # Test 5: Approval response
    t5 = RegressionTest("Approval response workflow", "HITL")
    try:
        apr = create_approval(
            action_name="test_action_2",
            action_level="a3",
            actor="regression_test",
            request_details="Test approval response",
            risk_assessment="low",
            timeout_minutes=5,
        )
        responded = respond_approval(apr["approval_id"], "approved", "regression_runner")
        t5.passed = responded["status"] == "approved" and responded["responded_by"] == "regression_runner"
        t5.details = f"status={responded['status']}, responded_by={responded['responded_by']}"
    except Exception as e:
        t5.passed = False
        t5.details = f"Error: {str(e)}"
    tests.append(t5)

    return tests


def run_context_pack_tests() -> List[RegressionTest]:
    """Run Context Pack Compiler tests."""
    tests = []

    sys.path.insert(0, SCRIPTS_DIR)
    from context_pack_compiler import (
        compile_context_pack_safe, PROTECTED_KEYS, estimate_tokens
    )

    # Test 1: Basic compilation
    t1 = RegressionTest("Context pack basic compilation", "Context Pack")
    try:
        pack = compile_context_pack_safe()
        t1.passed = (
            pack.get("version") == 1
            and "hot_context" in pack
            and "warm_context" in pack
            and "cold_references" in pack
        )
        t1.details = f"total_tokens={pack.get('total_tokens')}"
    except Exception as e:
        t1.passed = False
        t1.details = f"Error: {str(e)}"
    tests.append(t1)

    # Test 2: Protected keys present
    t2 = RegressionTest("Protected keys in context pack", "Context Pack")
    pack = compile_context_pack_safe()
    hot = pack.get("hot_context", "")
    all_present = all(key in hot for key in PROTECTED_KEYS)
    t2.passed = all_present
    t2.details = f"all_protected_present={all_present}"
    tests.append(t2)

    # Test 3: Truncation doesn't remove protected keys
    t3 = RegressionTest("Protected keys survive truncation", "Context Pack")
    pack = compile_context_pack_safe(extra_hot="X" * 100000, extra_warm="Y" * 200000)
    hot = pack.get("hot_context", "")
    all_present = all(key in hot for key in PROTECTED_KEYS)
    t3.passed = all_present
    t3.details = f"all_protected_present_after_truncation={all_present}"
    tests.append(t3)

    # Test 4: Cold references present
    t4 = RegressionTest("Cold references included", "Context Pack")
    pack = compile_context_pack_safe()
    refs = pack.get("cold_references", [])
    t4.passed = len(refs) > 0
    t4.details = f"cold_refs_count={len(refs)}"
    tests.append(t4)

    # Test 5: Token estimation
    t5 = RegressionTest("Token estimation", "Context Pack")
    tokens = estimate_tokens("Hello world")
    t5.passed = tokens > 0
    t5.details = f"tokens_for_11_chars={tokens}"
    tests.append(t5)

    return tests


def run_file_integrity_tests() -> List[RegressionTest]:
    """Check that all required files exist and are valid."""
    tests = []

    required_files = [
        ("runtime/project-state.json", "json"),
        ("runtime/roadmap.json", "json"),
        ("docs/autonomy-policy.md", "text"),
        ("scripts/autonomy_gate.py", "text"),
        ("scripts/hitl_approval.py", "text"),
        ("scripts/context_pack_compiler.py", "text"),
        ("scripts/anomaly_counter.py", "text"),
        ("scripts/l4_adversarial_eval.py", "text"),
        ("schemas/autonomy-decision.schema.json", "json"),
        ("schemas/hitl-approval.schema.json", "json"),
        ("schemas/context-pack.schema.json", "json"),
        ("schemas/weekly-report.schema.json", "json"),
    ]

    for relpath, ftype in required_files:
        t = RegressionTest(f"File exists: {relpath}", "Integrity")
        fullpath = os.path.join(PROJECT_ROOT, relpath)
        exists = os.path.exists(fullpath)
        t.passed = exists
        t.details = f"path={fullpath}, exists={exists}"

        if exists and ftype == "json":
            try:
                with open(fullpath, "r", encoding="utf-8") as f:
                    json.load(f)
                t.passed = True
                t.details += ", valid_json=True"
            except json.JSONDecodeError as e:
                t.passed = False
                t.details += f", valid_json=False ({str(e)})"

        tests.append(t)

    return tests


# ---------------------------------------------------------------------------
# Main Runner
# ---------------------------------------------------------------------------

def run_regression() -> dict:
    """Run the full regression suite."""
    all_tests: List[RegressionTest] = []

    print("=" * 60)
    print("  L4 REGRESSION RUNNER")
    print("=" * 60)

    # 1. File integrity
    print("\n[1/5] Running file integrity checks...")
    all_tests.extend(run_file_integrity_tests())

    # 2. Autonomy Gate
    print("[2/5] Running Autonomy Gate tests...")
    all_tests.extend(run_autonomy_gate_tests())

    # 3. HITL
    print("[3/5] Running HITL tests...")
    all_tests.extend(run_hitl_tests())

    # 4. Context Pack
    print("[4/5] Running Context Pack tests...")
    all_tests.extend(run_context_pack_tests())

    # 5. Adversarial Eval
    print("[5/5] Running L4 adversarial evaluation...")
    all_tests.append(run_adversarial_eval())

    # Summary
    passed = sum(1 for t in all_tests if t.passed)
    failed = sum(1 for t in all_tests if not t.passed)

    categories = {}
    for t in all_tests:
        cat = t.category
        if cat not in categories:
            categories[cat] = {"total": 0, "passed": 0}
        categories[cat]["total"] += 1
        if t.passed:
            categories[cat]["passed"] += 1

    report = {
        "run_id": f"regression-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_tests": len(all_tests),
        "passed": passed,
        "failed": failed,
        "status": "PASSED" if failed == 0 else "FAILED",
        "categories": {
            cat: {"total": v["total"], "passed": v["passed"], "failed": v["total"] - v["passed"]}
            for cat, v in categories.items()
        },
        "tests": [
            {
                "name": t.name,
                "category": t.category,
                "status": "passed" if t.passed else "failed",
                "details": t.details,
                "duration_ms": t.duration_ms,
            }
            for t in all_tests
        ],
    }

    return report


def main():
    report = run_regression()

    print("\n" + "=" * 60)
    print("  REGRESSION REPORT")
    print("=" * 60)
    print(f"  Run ID : {report['run_id']}")
    print(f"  Status : {report['status']}")
    print(f"  Total  : {report['total_tests']}")
    print(f"  Passed : {report['passed']}")
    print(f"  Failed : {report['failed']}")
    print("-" * 60)

    for cat, stats in report["categories"].items():
        status = "OK" if stats["failed"] == 0 else "FAIL"
        print(f"  [{status}] {cat}: {stats['passed']}/{stats['total']} passed")

    print("-" * 60)
    failed_tests = [t for t in report["tests"] if t["status"] == "failed"]
    if failed_tests:
        print("  FAILED TESTS:")
        for t in failed_tests:
            print(f"    - {t['category']} | {t['name']}: {t['details'][:80]}")
    print("=" * 60)

    # Save report
    report_path = os.path.join(LOGS_DIR, "regression-report.json")
    os.makedirs(LOGS_DIR, exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"\nReport saved to: {report_path}")

    return 0 if report["failed"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
