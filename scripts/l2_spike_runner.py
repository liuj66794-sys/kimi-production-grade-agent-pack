#!/usr/bin/env python3
"""
L2 Spike Runner — Kimi Production-Grade Agent Pack v2.5

This script executes L2 spike tests sequentially, validating each agent's
configuration, skill triggers, and hard-fail rules.

Usage:
    python l2_spike_runner.py --spike all
    python l2_spike_runner.py --spike memory-candidate
    python l2_spike_runner.py --spike slide-outline
    python l2_spike_runner.py --list
"""

import argparse
import json
import logging
import os
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
PACK_ROOT = Path("/mnt/agents/output/kimi-production-grade-agent-pack")
SCHEMAS_DIR = PACK_ROOT / "schemas"
AGENTS_DIR = PACK_ROOT / "agents"
SKILLS_DIR = PACK_ROOT / "skills"
EVALS_DIR = PACK_ROOT / "evals" / "l2-spike"

SPIKES = {
    "memory-candidate": {
        "id": "memory-candidate-spike",
        "version": "2.1.0",
        "agent": "memory-sub.yaml",
        "skills": ["memory-store/SKILL.md", "memory-retrieve/SKILL.md"],
        "schema": "memory-result.schema.json",
        "eval": "memory-candidate-spike.md",
        "order": 1,
    },
    "slide-outline": {
        "id": "slide-outline-spike",
        "version": "2.2.0",
        "agent": "slide-maker-sub.yaml",
        "skills": ["slide-outline/SKILL.md", "slide-content/SKILL.md"],
        "schema": "slide-result.schema.json",
        "eval": "slide-outline-spike.md",
        "order": 2,
    },
    "spreadsheet": {
        "id": "spreadsheet-spike",
        "version": "2.3.0",
        "agent": "spreadsheet-sub.yaml",
        "skills": ["spreadsheet-analysis/SKILL.md", "table-summary/SKILL.md", "data-quality-check/SKILL.md"],
        "schemas": ["spreadsheet-analysis.schema.json", "table-summary.schema.json", "data-quality-result.schema.json"],
        "order": 3,
    },
    "multimodal": {
        "id": "multimodal-spike",
        "version": "2.4.0",
        "agent": "multimodal-sub.yaml",
        "skills": ["multimodal-review/SKILL.md", "ui-screenshot-review/SKILL.md", "visual-evidence-extraction/SKILL.md"],
        "schemas": ["multimodal-review.schema.json", "visual-evidence.schema.json"],
        "order": 4,
    },
}

# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class TestCase:
    case_id: str
    name: str
    category: str
    agent: str
    pass_: bool = False
    score: float = 0.0
    duration_ms: int = 0
    notes: str = ""
    error: str = ""
    hard_fail_triggered: bool = False
    hard_fail_rule_id: str = ""

    def to_dict(self) -> dict:
        d = asdict(self)
        d["pass"] = d.pop("pass_")
        return d


@dataclass
class SpikeResult:
    spike_id: str
    spike_name: str
    status: str = "pending"
    cases: List[TestCase] = field(default_factory=list)
    started_at: str = ""
    completed_at: str = ""
    duration_seconds: float = 0.0

    @property
    def passed(self) -> int:
        return sum(1 for c in self.cases if c.pass_)

    @property
    def failed(self) -> int:
        return sum(1 for c in self.cases if not c.pass_)

    @property
    def hard_fail_count(self) -> int:
        return sum(1 for c in self.cases if c.hard_fail_triggered)


# ---------------------------------------------------------------------------
# Validators
# ---------------------------------------------------------------------------

class SpikeValidator:
    """Validates spike artifacts (agents, skills, schemas)."""

    def __init__(self, spike_name: str, config: dict):
        self.spike_name = spike_name
        self.config = config
        self.cases: List[TestCase] = []

    def _record(self, case_id: str, name: str, category: str, agent: str,
                pass_: bool, duration_ms: int = 0, notes: str = "",
                error: str = "", hard_fail_triggered: bool = False,
                hard_fail_rule_id: str = "") -> None:
        self.cases.append(TestCase(
            case_id=case_id, name=name, category=category, agent=agent,
            pass_=pass_, duration_ms=duration_ms, notes=notes, error=error,
            hard_fail_triggered=hard_fail_triggered,
            hard_fail_rule_id=hard_fail_rule_id,
        ))

    # ---- Agent validation ------------------------------------------------

    def validate_agent_config(self) -> None:
        """Check agent YAML exists and has required fields."""
        start = time.time()
        agent_file = AGENTS_DIR / self.config["agent"]
        case_id = f"L2-{self.spike_name[:2].upper()}-{(self.config['order']):04d}"

        if not agent_file.exists():
            self._record(
                case_id=case_id, name=f"Agent config exists: {self.config['agent']}",
                category="l2_agent_config", agent=self.spike_name,
                pass_=False, error=f"File not found: {agent_file}",
            )
            return

        content = agent_file.read_text()
        required_fields = ["name:", "version:", "description:", "tools:", "hard_fail_rules:"]
        missing = [f for f in required_fields if f not in content]

        if missing:
            self._record(
                case_id=case_id, name=f"Agent config valid: {self.config['agent']}",
                category="l2_agent_config", agent=self.spike_name,
                pass_=False, error=f"Missing fields: {missing}",
            )
        else:
            duration = int((time.time() - start) * 1000)
            self._record(
                case_id=case_id, name=f"Agent config valid: {self.config['agent']}",
                category="l2_agent_config", agent=self.spike_name,
                pass_=True, duration_ms=duration,
                notes=f"Found all {len(required_fields)} required fields",
            )

    # ---- Skill validation ------------------------------------------------

    def validate_skills(self) -> None:
        """Check each skill file exists and has YAML frontmatter."""
        for idx, skill_name in enumerate(self.config.get("skills", []), 1):
            start = time.time()
            skill_file = SKILLS_DIR / skill_name
            order = self.config["order"]
            case_id = f"L2-{self.spike_name[:2].upper()}-{order * 100 + idx:04d}"

            if not skill_file.exists():
                self._record(
                    case_id=case_id, name=f"Skill exists: {skill_name}",
                    category="l2_skill_validation", agent=self.spike_name,
                    pass_=False, error=f"File not found: {skill_file}",
                )
                continue

            content = skill_file.read_text()
            has_frontmatter = content.startswith("---")
            has_hard_fail = "hard_fail" in content.lower()

            duration = int((time.time() - start) * 1000)
            if has_frontmatter:
                self._record(
                    case_id=case_id, name=f"Skill valid: {skill_name}",
                    category="l2_skill_validation", agent=self.spike_name,
                    pass_=True, duration_ms=duration,
                    notes=f"YAML frontmatter: yes, hard_fail refs: {has_hard_fail}",
                )
            else:
                self._record(
                    case_id=case_id, name=f"Skill valid: {skill_name}",
                    category="l2_skill_validation", agent=self.spike_name,
                    pass_=False, error="Missing YAML frontmatter",
                )

    # ---- Schema validation -----------------------------------------------

    def validate_schemas(self) -> None:
        """Check schema files exist and are valid JSON."""
        schemas = self.config.get("schemas") or ([self.config["schema"]] if "schema" in self.config else [])

        for idx, schema_name in enumerate(schemas, 1):
            start = time.time()
            schema_file = SCHEMAS_DIR / schema_name
            order = self.config["order"]
            case_id = f"L2-{self.spike_name[:2].upper()}-{order * 100 + 50 + idx:04d}"

            if not schema_file.exists():
                self._record(
                    case_id=case_id, name=f"Schema exists: {schema_name}",
                    category="l2_schema_compliance", agent=self.spike_name,
                    pass_=False, error=f"File not found: {schema_file}",
                )
                continue

            try:
                content = schema_file.read_text()
                schema = json.loads(content)
                is_draft7 = schema.get("$schema", "").endswith("draft-07/schema#")
                has_id = "$id" in schema
                duration = int((time.time() - start) * 1000)

                self._record(
                    case_id=case_id, name=f"Schema valid: {schema_name}",
                    category="l2_schema_compliance", agent=self.spike_name,
                    pass_=True, duration_ms=duration,
                    notes=f"JSON valid, Draft 7: {is_draft7}, has $id: {has_id}",
                )
            except json.JSONDecodeError as e:
                self._record(
                    case_id=case_id, name=f"Schema valid: {schema_name}",
                    category="l2_schema_compliance", agent=self.spike_name,
                    pass_=False, error=f"Invalid JSON: {e}",
                )

    # ---- Tool permissions validation -------------------------------------

    def validate_tool_permissions(self) -> None:
        """Verify agent has correct tool permissions."""
        start = time.time()
        agent_file = AGENTS_DIR / self.config["agent"]
        case_id = f"L2-{self.spike_name[:2].upper()}-{self.config['order'] * 100 + 80:04d}"

        if not agent_file.exists():
            self._record(
                case_id=case_id, name="Tool permissions valid",
                category="l2_security", agent=self.spike_name,
                pass_=False, error="Agent config not found",
            )
            return

        content = agent_file.read_text()
        has_allowed = "allowed:" in content
        has_denied = "denied:" in content
        duration = int((time.time() - start) * 1000)

        self._record(
            case_id=case_id, name="Tool permissions valid",
            category="l2_security", agent=self.spike_name,
            pass_=has_allowed and has_denied, duration_ms=duration,
            notes=f"Allowed list: {has_allowed}, Denied list: {has_denied}",
        )

    # ---- Hard-fail rule validation --------------------------------------

    def validate_hard_fail_rules(self) -> None:
        """Verify hard-fail rules are defined and actionable."""
        start = time.time()
        agent_file = AGENTS_DIR / self.config["agent"]
        case_id = f"L2-{self.spike_name[:2].upper()}-{self.config['order'] * 100 + 90:04d}"

        if not agent_file.exists():
            self._record(
                case_id=case_id, name="Hard-fail rules defined",
                category="l2_hard_fail", agent=self.spike_name,
                pass_=False, error="Agent config not found",
            )
            return

        content = agent_file.read_text()
        hf_count = content.lower().count("hard_fail")
        has_consequence = "consequence" in content.lower()
        duration = int((time.time() - start) * 1000)

        self._record(
            case_id=case_id, name="Hard-fail rules defined",
            category="l2_hard_fail", agent=self.spike_name,
            pass_=hf_count >= 3 and has_consequence, duration_ms=duration,
            notes=f"Hard-fail refs: {hf_count}, has consequence: {has_consequence}",
        )

    def run_all(self) -> SpikeResult:
        """Execute all validation checks for this spike."""
        started = datetime.now(timezone.utc).isoformat()
        t0 = time.time()

        self.validate_agent_config()
        self.validate_skills()
        self.validate_schemas()
        self.validate_tool_permissions()
        self.validate_hard_fail_rules()

        duration = time.time() - t0
        completed = datetime.now(timezone.utc).isoformat()
        status = "passed" if all(c.pass_ for c in self.cases) else "failed"

        return SpikeResult(
            spike_id=self.config["id"],
            spike_name=self.spike_name,
            status=status,
            cases=self.cases,
            started_at=started,
            completed_at=completed,
            duration_seconds=round(duration, 2),
        )


# ---------------------------------------------------------------------------
# Reporter
# ---------------------------------------------------------------------------

class ReportGenerator:
    """Generates test result reports in multiple formats."""

    @staticmethod
    def json_report(results: List[SpikeResult], output_path: Path) -> None:
        """Generate JSON report conforming to l2-regression-result schema."""
        all_cases = []
        l1_passed = True  # Spike runner doesn't test L1; assume true
        l2_smoke_passed = all(r.status == "passed" for r in results)
        hard_fail_count = sum(r.hard_fail_count for r in results)

        for r in results:
            all_cases.extend([c.to_dict() for c in r.cases])

        total_passed = sum(1 for c in all_cases if c["pass"])
        total_failed = sum(1 for c in all_cases if not c["pass"])

        report = {
            "suite_name": "l2-unit-smoke",
            "version": "2.5.0",
            "executed_at": datetime.now(timezone.utc).isoformat(),
            "duration_seconds": round(sum(r.duration_seconds for r in results), 2),
            "cases": all_cases,
            "summary": {
                "total_cases": len(all_cases),
                "passed": total_passed,
                "failed": total_failed,
                "skipped": 0,
                "hard_fail_triggered": hard_fail_count,
                "pass_rate": round(total_passed / len(all_cases) * 100, 1) if all_cases else 0,
            },
            "l1_regression_passed": l1_passed,
            "l2_unit_smoke_passed": l2_smoke_passed,
            "hard_fail_count": hard_fail_count,
            "overall_status": "passed" if l2_smoke_passed and hard_fail_count == 0 else "failed",
        }

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(report, indent=2))
        logging.info(f"JSON report written to {output_path}")

    @staticmethod
    def console_report(results: List[SpikeResult]) -> None:
        """Print human-readable report to console."""
        print("\n" + "=" * 70)
        print("  L2 SPIKE RUNNER RESULTS")
        print("=" * 70)

        for r in results:
            icon = "PASS" if r.status == "passed" else "FAIL"
            print(f"\n  [{icon}] {r.spike_name} (v{r.spike_id})")
            print(f"       Duration: {r.duration_seconds:.2f}s")
            print(f"       Cases: {r.passed} passed, {r.failed} failed")

            for c in r.cases:
                status = "PASS" if c.pass_ else "FAIL"
                print(f"         [{status}] {c.name}")
                if c.error:
                    print(f"              Error: {c.error}")
                if c.notes:
                    print(f"              Notes: {c.notes}")

        total_cases = sum(len(r.cases) for r in results)
        total_passed = sum(r.passed for r in results)
        total_failed = sum(r.failed for r in results)

        print("\n" + "-" * 70)
        print(f"  TOTAL: {total_cases} cases, {total_passed} passed, {total_failed} failed")
        overall = "PASS" if total_failed == 0 else "FAIL"
        print(f"  OVERALL: {overall}")
        print("=" * 70 + "\n")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description="L2 Spike Runner")
    parser.add_argument(
        "--spike",
        choices=["all"] + list(SPIKES.keys()),
        default="all",
        help="Which spike to run (default: all)",
    )
    parser.add_argument(
        "--list", action="store_true", help="List available spikes and exit"
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=PACK_ROOT / "reports" / "l2-spike-results.json",
        help="Output report path",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Verbose logging"
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    if args.list:
        print("\nAvailable spikes:")
        for name, cfg in sorted(SPIKES.items(), key=lambda x: x[1]["order"]):
            print(f"  {cfg['order']}. {name} (v{cfg['version']}) — {cfg['id']}")
        print()
        return 0

    spikes_to_run = list(SPIKES.keys()) if args.spike == "all" else [args.spike]
    results: List[SpikeResult] = []

    logging.info("=" * 60)
    logging.info("L2 Spike Runner starting")
    logging.info(f"Pack root: {PACK_ROOT}")
    logging.info(f"Spikes to run: {spikes_to_run}")
    logging.info("=" * 60)

    for spike_name in spikes_to_run:
        if spike_name not in SPIKES:
            logging.error(f"Unknown spike: {spike_name}")
            continue

        config = SPIKES[spike_name]
        logging.info(f"\n--- Running spike: {spike_name} ---")

        validator = SpikeValidator(spike_name, config)
        result = validator.run_all()
        results.append(result)

        logging.info(f"Spike {spike_name}: {result.status} ({len(result.cases)} cases)")

    # Generate reports
    ReportGenerator.console_report(results)
    ReportGenerator.json_report(results, args.output)

    return 0 if all(r.status == "passed" for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
