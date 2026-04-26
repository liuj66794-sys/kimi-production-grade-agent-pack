#!/usr/bin/env python3
"""
check_hard_fail.py — Kimi Production-Grade Agent Pack v1.1
=========================================================
Run pre-defined Hard Fail rules against evaluation outputs.

Hard Fail Rules (triggering ANY caps the max score at 60):
  1. 关键事实无来源且写成确定事实 — Key facts stated as certain without sources
  2. 核心交付物缺失 — Core deliverable missing
  3. 代码声称测试通过但未运行测试 — Code claims tests passed but no test run
  4. 表格计算不可追溯 — Table calculations not traceable
  5. PPT只是报告切片，无页级观点 — PPT is just report slices, no page-level insight
  6. 明显忽略用户约束 — User constraints clearly ignored
  7. 工具失败后假装成功 — Tool failure masked as success
  8. 子Agent缺失context_snapshot连续3次 — Sub-agent missing context_snapshot 3x

Usage:
    python scripts/check_hard_fail.py --input evals/results/unit-smoke/2026-04-25 --threshold 0.8
    python scripts/check_hard_fail.py --input evals/results/unit-smoke/2026-04-25T000000 --threshold 0.5
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# ─── Hard Fail Rule Definitions ───────────────────────────────────────────────

HARD_FAIL_RULES = {
    "HF001": {
        "name": "关键事实无来源且写成确定事实",
        "en_name": "key_facts_without_sources",
        "description": "Key facts are stated as certain without any source citation",
        "check": "evidence_missing_for_claims",
    },
    "HF002": {
        "name": "核心交付物缺失",
        "en_name": "core_deliverable_missing",
        "description": "The core deliverable artifact is completely missing",
        "check": "missing_deliverables_or_artifacts",
    },
    "HF003": {
        "name": "代码声称测试通过但未运行测试",
        "en_name": "code_claims_tests_passed_not_run",
        "description": "Code claims all tests pass but no test execution record exists",
        "check": "test_claim_without_execution",
    },
    "HF004": {
        "name": "表格计算不可追溯",
        "en_name": "table_calculations_untraceable",
        "description": "Table/calculation values cannot be traced back to source data",
        "check": "untraceable_calculations",
    },
    "HF005": {
        "name": "PPT只是报告切片，无页级观点",
        "en_name": "ppt_report_slices_no_insight",
        "description": "PPT output is mere report slicing without page-level insight",
        "check": "ppt_lacks_page_insights",
    },
    "HF006": {
        "name": "明显忽略用户约束",
        "en_name": "user_constraints_ignored",
        "description": "User-specified constraints are clearly violated",
        "check": "constraints_violated",
    },
    "HF007": {
        "name": "工具失败后假装成功",
        "en_name": "tool_failure_masked_as_success",
        "description": "A tool/API call failed but output pretends it succeeded",
        "check": "masked_tool_failures",
    },
    "HF008": {
        "name": "子Agent缺失context_snapshot连续3次",
        "en_name": "subagent_missing_context_snapshot_3x",
        "description": "Sub-agent missing context_snapshot for 3 consecutive turns",
        "check": "missing_context_snapshot",
    },
}

# ─── Data Models ──────────────────────────────────────────────────────────────


@dataclass
class HardFailEntry:
    """A single hard-fail detection entry."""

    rule_id: str
    rule_name: str
    eval_id: str
    triggered: bool
    details: str = ""
    severity: str = "critical"  # critical, high, medium

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class HardFailReport:
    """Aggregated hard-fail report."""

    report_timestamp: str = ""
    pack_version: str = "v1.1.0"
    input_path: str = ""
    threshold: float = 0.8
    total_tests: int = 0
    hard_fail_count: int = 0
    hard_fail_rate: float = 0.0
    threshold_exceeded: bool = False
    entries: List[HardFailEntry] = field(default_factory=list)
    summary: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        d = asdict(self)
        return d


# ─── Detection Functions ──────────────────────────────────────────────────────


def check_evidence_missing_for_claims(eval_result: dict, raw_output: str = "") -> bool:
    """HF001: Key facts stated as certain without sources."""
    structured = eval_result.get("structured_output", {})
    if isinstance(structured, str):
        try:
            structured = json.loads(structured)
        except json.JSONDecodeError:
            return False

    evidence = structured.get("evidence", []) if isinstance(structured, dict) else []
    conclusion = structured.get("conclusion", []) if isinstance(structured, dict) else []

    # If there are conclusions but no evidence, trigger hard-fail
    if conclusion and not evidence:
        return True

    # Check if any claim has confidence=1.0 without source
    if isinstance(evidence, list):
        for ev in evidence:
            if isinstance(ev, dict):
                confidence = ev.get("confidence", 0)
                source = ev.get("source", "")
                if confidence == 1.0 and not source:
                    return True

    return False


def check_missing_deliverables(eval_result: dict, raw_output: str = "") -> bool:
    """HF002: Core deliverable missing."""
    structured = eval_result.get("structured_output", {})
    if isinstance(structured, str):
        try:
            structured = json.loads(structured)
        except json.JSONDecodeError:
            return False

    if not isinstance(structured, dict):
        return True

    deliverables = structured.get("deliverables", [])
    artifacts = structured.get("artifacts", [])

    # No deliverables AND no artifacts = hard fail
    if not deliverables and not artifacts:
        return True

    # Check if artifacts list is empty or has empty entries
    if isinstance(artifacts, list) and len(artifacts) == 0:
        if not deliverables:
            return True

    return False


def check_test_claim_without_execution(eval_result: dict, raw_output: str = "") -> bool:
    """HF003: Code claims tests passed but no test run."""
    structured = eval_result.get("structured_output", {})
    if isinstance(structured, str):
        try:
            structured = json.loads(structured)
        except json.JSONDecodeError:
            return False

    if not isinstance(structured, dict):
        return False

    test_results = structured.get("test_results", {})
    if isinstance(test_results, dict):
        passed = test_results.get("passed", False)
        ran = test_results.get("ran", False)
        test_count = test_results.get("count", 0)

        # Claims tests passed but no tests actually ran
        if passed and not ran:
            return True
        if passed and test_count == 0:
            return True

    # Check raw output for suspicious claims
    if raw_output:
        claim_patterns = [
            r"测试通过",
            r"tests?\s+pass(ed)?",
            r"all\s+tests?\s+ok",
        ]
        has_claim = any(re.search(p, raw_output, re.IGNORECASE) for p in claim_patterns)

        run_patterns = [
            r"运行.*测试",
            r"ran\s+test",
            r"executed\s+test",
            r"pytest",
            r"unittest",
        ]
        has_run_record = any(re.search(p, raw_output, re.IGNORECASE) for p in run_patterns)

        if has_claim and not has_run_record:
            return True

    return False


def check_untraceable_calculations(eval_result: dict, raw_output: str = "") -> bool:
    """HF004: Table calculations not traceable."""
    structured = eval_result.get("structured_output", {})
    if isinstance(structured, str):
        try:
            structured = json.loads(structured)
        except json.JSONDecodeError:
            return False

    if not isinstance(structured, dict):
        return False

    # Check for table data without formula/source trace
    artifacts = structured.get("artifacts", [])
    if isinstance(artifacts, list):
        for artifact in artifacts:
            if isinstance(artifact, dict):
                artifact_type = artifact.get("type", "")
                description = artifact.get("description", "")
                if artifact_type == "table" or "表格" in description:
                    # Tables should have traceable calculations
                    if "formula" not in description.lower() and "来源" not in description:
                        return True

    return False


def check_ppt_lacks_insights(eval_result: dict, raw_output: str = "") -> bool:
    """HF005: PPT is just report slices, no page-level insight."""
    structured = eval_result.get("structured_output", {})
    if isinstance(structured, str):
        try:
            structured = json.loads(structured)
        except json.JSONDecodeError:
            return False

    if not isinstance(structured, dict):
        return False

    artifacts = structured.get("artifacts", [])
    if isinstance(artifacts, list):
        for artifact in artifacts:
            if isinstance(artifact, dict):
                artifact_type = artifact.get("type", "")
                if artifact_type in ("ppt", "presentation", "slide"):
                    description = artifact.get("description", "")
                    # PPT should have page-level insights, not just slicing
                    if "slice" in description.lower() or "切片" in description:
                        return True
                    # Should describe insights per page
                    if "page" not in description.lower() and "页" not in description:
                        return True

    return False


def check_constraints_violated(eval_result: dict, raw_output: str = "") -> bool:
    """HF006: User constraints clearly ignored."""
    structured = eval_result.get("structured_output", {})
    if isinstance(structured, str):
        try:
            structured = json.loads(structured)
        except json.JSONDecodeError:
            return False

    if not isinstance(structured, dict):
        return False

    constraints = structured.get("constraints", [])
    if isinstance(constraints, list) and len(constraints) == 0:
        # Check if raw output mentions constraints that were then ignored
        if raw_output and "约束" in raw_output:
            # If constraints section exists in input but output doesn't address them
            pass

    # Check for explicit constraint violation markers in the output
    violation_markers = [
        "忽略约束",
        "constraint violated",
        "requirements not met",
    ]
    if raw_output:
        for marker in violation_markers:
            if marker in raw_output.lower():
                return True

    return False


def check_masked_tool_failures(eval_result: dict, raw_output: str = "") -> bool:
    """HF007: Tool failure masked as success."""
    if not raw_output:
        return False

    # Patterns indicating a tool failed but was reported as success
    failure_then_success = [
        r"(error|failed|timeout|异常|失败).{0,50}(success|成功|通过)",
        r"工具.*失败.{0,30}(假装|伪装|mask)",
        r"API.*error.{0,50}(success|成功)",
        r"(404|500|503|timeout).{0,30}(success|通过)",
    ]

    for pattern in failure_then_success:
        if re.search(pattern, raw_output, re.IGNORECASE | re.DOTALL):
            return True

    return False


def check_missing_context_snapshot(eval_result: dict, raw_output: str = "") -> bool:
    """HF008: Sub-agent missing context_snapshot 3 times in a row."""
    structured = eval_result.get("structured_output", {})
    if isinstance(structured, str):
        try:
            structured = json.loads(structured)
        except json.JSONDecodeError:
            return False

    if not isinstance(structured, dict):
        return False

    context_snapshot = structured.get("context_snapshot", {})
    if not context_snapshot:
        # Check if this is a sub-agent task by looking for subagent indicators
        status = structured.get("status", "")
        if status in ("delegated", "subagent"):
            return True

    return False


# ─── Rule Dispatch ────────────────────────────────────────────────────────────

RULE_CHECKS = {
    "HF001": check_evidence_missing_for_claims,
    "HF002": check_missing_deliverables,
    "HF003": check_test_claim_without_execution,
    "HF004": check_untraceable_calculations,
    "HF005": check_ppt_lacks_insights,
    "HF006": check_constraints_violated,
    "HF007": check_masked_tool_failures,
    "HF008": check_missing_context_snapshot,
}


# ─── Report Generation ────────────────────────────────────────────────────────


def load_eval_results(input_path: Path) -> list:
    """Load evaluation results from the input directory."""
    results = []

    # If input is a directory, look for eval-result.json
    if input_path.is_dir():
        eval_file = input_path / "eval-result.json"
        if eval_file.is_file():
            with open(eval_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    results = data
                elif isinstance(data, dict):
                    results = [data]
        else:
            # Try to find raw-output.md files and parse them
            for raw_file in sorted(input_path.rglob("raw-output.md")):
                # Parent directory name might be the eval_id
                eval_id = raw_file.parent.name
                results.append({"eval_id": eval_id, "raw_path": str(raw_file)})
    elif input_path.is_file():
        with open(input_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                results = data
            elif isinstance(data, dict):
                results = [data]

    return results


def run_hard_fail_checks(
    eval_results: list,
    raw_outputs_dir: Optional[Path] = None,
) -> HardFailReport:
    """Run all hard-fail checks against evaluation results."""
    report = HardFailReport(
        report_timestamp=datetime.now(timezone.utc).isoformat(),
        total_tests=len(eval_results),
        entries=[],
    )

    for eval_result in eval_results:
        eval_id = eval_result.get("eval_id", "unknown")

        # Load raw output if available
        raw_output = ""
        if raw_outputs_dir:
            raw_file = raw_outputs_dir / "raw-output.md"
            if raw_file.is_file():
                raw_output = raw_file.read_text(encoding="utf-8")
        elif "raw_path" in eval_result:
            raw_path = Path(eval_result["raw_path"])
            if raw_path.is_file():
                raw_output = raw_path.read_text(encoding="utf-8")

        # Run each hard-fail rule
        for rule_id, rule_info in HARD_FAIL_RULES.items():
            check_func = RULE_CHECKS.get(rule_id)
            if not check_func:
                continue

            try:
                triggered = check_func(eval_result, raw_output)
            except Exception as e:
                triggered = False
                print(f"Warning: Check {rule_id} failed for {eval_id}: {e}")

            entry = HardFailEntry(
                rule_id=rule_id,
                rule_name=rule_info["name"],
                eval_id=eval_id,
                triggered=triggered,
                details=f"Rule '{rule_info['en_name']}' check result" if triggered else "",
                severity="critical",
            )
            report.entries.append(entry)

            if triggered:
                report.hard_fail_count += 1

    # Calculate rate
    if report.total_tests > 0:
        report.hard_fail_rate = round(report.hard_fail_count / report.total_tests, 4)

    # Build summary
    rule_trigger_counts = {}
    for entry in report.entries:
        if entry.triggered:
            rule_trigger_counts[entry.rule_id] = rule_trigger_counts.get(entry.rule_id, 0) + 1

    report.summary = {
        "total_tests": report.total_tests,
        "total_hard_fails": report.hard_fail_count,
        "hard_fail_rate": f"{report.hard_fail_rate:.2%}",
        "rule_trigger_counts": rule_trigger_counts,
        "rules_checked": list(HARD_FAIL_RULES.keys()),
    }

    return report


def print_summary(report: HardFailReport, threshold: float) -> None:
    """Print a human-readable summary to console."""
    report.threshold = threshold
    report.threshold_exceeded = report.hard_fail_rate > threshold

    print("\n" + "=" * 60)
    print("  HARD FAIL CHECK REPORT")
    print("=" * 60)
    print(f"  Timestamp:      {report.report_timestamp}")
    print(f"  Input path:     {report.input_path}")
    print(f"  Threshold:      {threshold:.0%}")
    print(f"  Total tests:    {report.total_tests}")
    print(f"  Hard fails:     {report.hard_fail_count}")
    print(f"  Hard fail rate: {report.hard_fail_rate:.2%}")
    print(f"  Status:         {'EXCEEDED' if report.threshold_exceeded else 'WITHIN LIMIT'}")
    print("-" * 60)

    if report.hard_fail_count > 0:
        print("  Triggered hard fails:")
        for entry in report.entries:
            if entry.triggered:
                print(f"    [{entry.rule_id}] {entry.rule_name}")
                print(f"      Eval: {entry.eval_id}")
                if entry.details:
                    print(f"      Details: {entry.details}")

    print("-" * 60)
    print(f"  Rule trigger counts:")
    for rule_id, rule_info in HARD_FAIL_RULES.items():
        count = report.summary.get("rule_trigger_counts", {}).get(rule_id, 0)
        status = "TRIGGERED" if count > 0 else "clean"
        print(f"    {rule_id} ({rule_info['en_name']}): {count} {status}")

    print("=" * 60)

    if report.threshold_exceeded:
        print(f"\n  RESULT: FAIL — Hard-fail rate ({report.hard_fail_rate:.2%}) ")
        print(f"          exceeds threshold ({threshold:.0%})")
    else:
        print(f"\n  RESULT: PASS — Hard-fail rate ({report.hard_fail_rate:.2%}) ")
        print(f"          within threshold ({threshold:.0%})")
    print("=" * 60 + "\n")


def main(argv: list[str] | None = None) -> int:
    """Main entry point for the hard-fail checker."""
    parser = argparse.ArgumentParser(
        description="Kimi Production-Grade Agent Pack — Hard Fail Checker v1.1",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/check_hard_fail.py --input evals/results/unit-smoke/2026-04-25T000000
  python scripts/check_hard_fail.py --input evals/results/unit-smoke/ --threshold 0.5
        """,
    )

    parser.add_argument(
        "--input",
        type=str,
        default=None,
        help="Path to eval results directory or eval-result.json file",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.8,
        help="Hard-fail rate threshold (0.0-1.0, default: 0.8)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output path for hard-fail-report.json (default: auto)",
    )
    parser.add_argument(
        "--list-rules",
        action="store_true",
        help="List all hard-fail rules and exit",
    )

    args = parser.parse_args(argv)

    if args.list_rules:
        print("\nHard-Fail Rules:")
        print("-" * 50)
        for rule_id, info in HARD_FAIL_RULES.items():
            print(f"  {rule_id}: {info['name']}")
            print(f"         EN: {info['en_name']}")
            print(f"         {info['description']}")
            print()
        return 0

    if not args.input:
        print("Error: --input is required (unless using --list-rules)")
        return 2

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: Input path does not exist: {input_path}")
        return 2

    print(f"Loading eval results from: {input_path}")
    eval_results = load_eval_results(input_path)

    if not eval_results:
        print("Warning: No evaluation results found.")
        return 0

    print(f"Loaded {len(eval_results)} evaluation result(s)")

    # Run checks
    report = run_hard_fail_checks(eval_results, raw_outputs_dir=input_path if input_path.is_dir() else None)
    report.input_path = str(input_path)
    report.threshold = args.threshold
    report.threshold_exceeded = report.hard_fail_rate > args.threshold

    # Print summary
    print_summary(report, args.threshold)

    # Save report
    if args.output:
        report_path = Path(args.output)
    else:
        report_path = input_path / "hard-fail-report.json" if input_path.is_dir() else input_path.parent / "hard-fail-report.json"

    report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report.to_dict(), f, ensure_ascii=False, indent=2)
    print(f"Report saved to: {report_path}")

    # Return non-zero if threshold exceeded
    return 1 if report.threshold_exceeded else 0


if __name__ == "__main__":
    sys.exit(main())
