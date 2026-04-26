#!/usr/bin/env python3
"""
Integration Smoke Runner - v1.2
Kimi Production-Grade Agent Pack

Semi-automatic stage-progression runner for L1 main-link integration validation.
- Unified task-events JSONL writer
- Step-by-step execution with explicit confirmation
- Resume support, artifact validation, QA Gate integration

Usage:
    python integration_smoke_runner.py --task-id root.integration_smoke_001
    python integration_smoke_runner.py --step task-intake
    python integration_smoke_runner.py --resume-from-step analyst
    python integration_smoke_runner.py --dry-run
    python integration_smoke_runner.py --validate-step
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
L1_MAIN_LINK: list[str] = [
    "task-intake",
    "swarm-orchestrator",
    "researcher",
    "analyst",
    "evidence-synthesis",
    "writer",
    "qa-reviewer",
    "eval-runner",
]

# Minimal pipeline for deep-research smoke test (excludes orchestrator and eval-runner)
DEEP_RESEARCH_PIPELINE: list[str] = [
    "task-intake",
    "researcher",
    "analyst",
    "evidence-synthesis",
    "writer",
    "qa-reviewer",
]

EVENT_TYPES: list[str] = [
    "task_created",
    "subtask_created",
    "subtask_assigned",
    "subtask_started",
    "subtask_done",
    "artifact_created",
    "blocker_found",
    "quality_review_started",
    "quality_review_done",
    "task_completed",
    "task_failed",
]

STEP_AGENT_MAP: dict[str, str] = {
    "task-intake": "task-intake-agent",
    "swarm-orchestrator": "swarm-orchestrator",
    "researcher": "researcher-agent",
    "analyst": "analyst-agent",
    "evidence-synthesis": "evidence-synthesis-agent",
    "writer": "writer-agent",
    "qa-reviewer": "qa-reviewer-agent",
    "eval-runner": "eval-runner",
}

STEP_ARTIFACTS: dict[str, list[str]] = {
    "task-intake": ["task-brief.json"],
    "researcher": ["research-notes.md"],
    "analyst": ["analysis-report.md"],
    "evidence-synthesis": ["claim-evidence-map.json"],
    "writer": ["final-report.md"],
    "qa-reviewer": ["qa-review.json"],
    "swarm-orchestrator": ["orchestration-plan.json"],
    "eval-runner": ["eval-result.json"],
}

ARTIFACT_SCHEMAS: dict[str, dict[str, Any]] = {
    "task-brief.json": {
        "required_keys": ["task_id", "title", "description", "requirements", "created_at"],
        "value_types": {"task_id": str, "title": str, "description": str, "requirements": list},
    },
    "research-notes.md": {"min_lines": 5, "required_headers": ["## "]},
    "analysis-report.md": {"min_lines": 5, "required_headers": ["## "]},
    "claim-evidence-map.json": {
        "required_keys": ["claims", "evidence_map"],
        "value_types": {"claims": list, "evidence_map": dict},
    },
    "final-report.md": {"min_lines": 10, "required_headers": ["# ", "## "]},
    "qa-review.json": {
        "required_keys": ["review_status", "findings", "scored_categories"],
        "value_types": {"review_status": str, "findings": list, "scored_categories": dict},
    },
    "orchestration-plan.json": {
        "required_keys": ["plan_id", "steps"],
        "value_types": {"plan_id": str, "steps": list},
    },
    "eval-result.json": {
        "required_keys": ["eval_id", "passed", "metrics"],
        "value_types": {"eval_id": str, "passed": bool, "metrics": dict},
    },
}

RUNTIME_DIR = Path("runtime")
ARTIFACTS_DIR = Path("artifacts")
EVALS_DIR = Path("evals/results/integration-smoke")

LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"

# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass
class TaskEvent:
    event_id: str
    task_id: str
    event_type: str
    timestamp: str
    agent: str
    status: str
    payload: dict = field(default_factory=dict)
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def create(
        cls,
        task_id: str,
        event_type: str,
        agent: str,
        status: str,
        payload: dict | None = None,
        error: str | None = None,
    ) -> TaskEvent:
        return cls(
            event_id=str(uuid.uuid4()),
            task_id=task_id,
            event_type=event_type,
            timestamp=datetime.now(timezone.utc).isoformat(),
            agent=agent,
            status=status,
            payload=payload or {},
            error=error,
        )


@dataclass
class RunState:
    task_id: str
    current_step: str | None = None
    completed_steps: list[str] = field(default_factory=list)
    status: str = "initialized"  # initialized | running | paused | completed | failed
    started_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RunState:
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

    @classmethod
    def load(cls, path: Path) -> RunState | None:
        if not path.exists():
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                return cls.from_dict(json.load(f))
        except (json.JSONDecodeError, TypeError, KeyError):
            return None

    def save(self, path: Path) -> None:
        self.updated_at = datetime.now(timezone.utc).isoformat()
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)


# ---------------------------------------------------------------------------
# TaskEvents writer
# ---------------------------------------------------------------------------

class TaskEventWriter:
    def __init__(self, task_id: str, runtime_dir: Path = RUNTIME_DIR) -> None:
        self.task_id = task_id
        self.runtime_dir = runtime_dir
        self.file_path = runtime_dir / f"task-events-{task_id}.jsonl"
        self.file_path.parent.mkdir(parents=True, exist_ok=True)

    def write(self, event: TaskEvent) -> None:
        with open(self.file_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(event.to_dict(), ensure_ascii=False) + "\n")

    def read_all(self) -> list[TaskEvent]:
        events: list[TaskEvent] = []
        if not self.file_path.exists():
            return events
        with open(self.file_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    events.append(TaskEvent(**data))
                except (json.JSONDecodeError, TypeError):
                    continue
        return events

    def get_completed_steps(self) -> set[str]:
        """Infer completed steps from subtask_done events."""
        completed: set[str] = set()
        for event in self.read_all():
            if event.event_type == "subtask_done" and event.status == "success":
                step = event.payload.get("step")
                if step:
                    completed.add(step)
        return completed

    def get_latest_for_step(self, step: str) -> TaskEvent | None:
        """Get the latest event for a given step."""
        events = [e for e in self.read_all() if e.payload.get("step") == step]
        if not events:
            return None
        return events[-1]

    def has_hard_fail(self) -> bool:
        for event in self.read_all():
            if event.event_type == "task_failed":
                return True
            if event.event_type == "quality_review_done" and event.payload.get("result") == "hard_fail":
                return True
        return False

    def get_qa_result(self) -> dict[str, Any] | None:
        for event in reversed(self.read_all()):
            if event.event_type == "quality_review_done":
                return {
                    "result": event.payload.get("result"),
                    "findings": event.payload.get("findings", []),
                    "scored_categories": event.payload.get("scored_categories", {}),
                }
        return None


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------

def validate_artifact(artifact_path: Path, schema: dict[str, Any]) -> dict[str, Any]:
    """Validate a single artifact against its schema. Returns validation report."""
    report: dict[str, Any] = {
        "path": str(artifact_path),
        "exists": False,
        "readable": False,
        "non_empty": False,
        "schema_valid": False,
        "errors": [],
    }

    if not artifact_path.exists():
        report["errors"].append("File does not exist")
        return report

    report["exists"] = True

    try:
        stat = artifact_path.stat()
        if stat.st_size == 0:
            report["errors"].append("File is empty (0 bytes)")
            return report
        report["non_empty"] = True
    except OSError as exc:
        report["errors"].append(f"Cannot stat file: {exc}")
        return report

    try:
        content = artifact_path.read_text(encoding="utf-8")
        report["readable"] = True
    except OSError as exc:
        report["errors"].append(f"Cannot read file: {exc}")
        return report

    # Schema validation
    errors: list[str] = []
    is_valid = True

    if "min_lines" in schema:
        lines = content.strip().splitlines()
        if len(lines) < schema["min_lines"]:
            errors.append(f"Expected at least {schema['min_lines']} lines, got {len(lines)}")
            is_valid = False

    if "required_headers" in schema:
        for header_prefix in schema["required_headers"]:
            if not any(line.startswith(header_prefix) for line in content.splitlines()):
                errors.append(f"Missing required header starting with '{header_prefix}'")
                is_valid = False

    if "required_keys" in schema:
        try:
            data = json.loads(content)
            if not isinstance(data, dict):
                errors.append("JSON root must be an object")
                is_valid = False
            else:
                for key in schema["required_keys"]:
                    if key not in data:
                        errors.append(f"Missing required key: '{key}'")
                        is_valid = False
                if "value_types" in schema and isinstance(data, dict):
                    for key, expected_type in schema["value_types"].items():
                        if key in data and not isinstance(data[key], expected_type):
                            errors.append(
                                f"Key '{key}' expected type {expected_type.__name__}, "
                                f"got {type(data[key]).__name__}"
                            )
                            is_valid = False
        except json.JSONDecodeError as exc:
            errors.append(f"Invalid JSON: {exc}")
            is_valid = False

    report["schema_valid"] = is_valid
    report["errors"].extend(errors)
    return report


def validate_step_artifacts(step: str, artifacts_dir: Path) -> dict[str, Any]:
    """Validate all artifacts for a given step."""
    artifact_names = STEP_ARTIFACTS.get(step, [])
    results: dict[str, Any] = {
        "step": step,
        "artifacts_dir": str(artifacts_dir),
        "all_valid": True,
        "details": {},
    }

    for name in artifact_names:
        schema = ARTIFACT_SCHEMAS.get(name, {})
        report = validate_artifact(artifacts_dir / name, schema)
        results["details"][name] = report
        if not report["schema_valid"]:
            results["all_valid"] = False

    return results


# ---------------------------------------------------------------------------
# Runner core
# ---------------------------------------------------------------------------

class IntegrationSmokeRunner:
    def __init__(
        self,
        task_id: str,
        runtime_dir: Path = RUNTIME_DIR,
        artifacts_dir: Path = ARTIFACTS_DIR,
        evals_dir: Path = EVALS_DIR,
        dry_run: bool = False,
        pipeline: list[str] | None = None,
    ) -> None:
        self.task_id = task_id
        self.runtime_dir = runtime_dir
        self.artifacts_dir = artifacts_dir / task_id.replace("root.", "")
        self.evals_dir = evals_dir
        self.dry_run = dry_run
        self.pipeline = pipeline or L1_MAIN_LINK
        self.logger = logging.getLogger(self.__class__.__name__)

        self.event_writer = TaskEventWriter(task_id, runtime_dir)
        self.run_state_path = runtime_dir / "run-state.json"
        self.run_state = RunState.load(self.run_state_path) or RunState(task_id=task_id)

    def emit(
        self,
        event_type: str,
        agent: str,
        status: str,
        payload: dict | None = None,
        error: str | None = None,
    ) -> TaskEvent:
        event = TaskEvent.create(
            task_id=self.task_id,
            event_type=event_type,
            agent=agent,
            status=status,
            payload=payload,
            error=error,
        )
        self.event_writer.write(event)
        self.logger.info("Event: %s | agent=%s | status=%s", event_type, agent, status)
        return event

    def init_task(self) -> None:
        """Initialize the task if not already started."""
        if self.run_state.status == "initialized":
            self.emit(
                event_type="task_created",
                agent="integration-smoke-runner",
                status="success",
                payload={"task_id": self.task_id, "link": "L1-main", "version": "1.2"},
            )
            self.run_state.status = "running"
            self.run_state.save(self.run_state_path)
            self.logger.info("Task initialized: %s", self.task_id)

    def preview_step(self, step: str) -> None:
        """Preview what would happen for a step (dry-run mode)."""
        agent = STEP_AGENT_MAP.get(step, "unknown")
        artifacts = STEP_ARTIFACTS.get(step, [])
        idx = self.pipeline.index(step) if step in self.pipeline else -1

        print(f"\n{'='*60}")
        print(f"  [DRY-RUN PREVIEW] Step: {step}")
        print(f"  Agent: {agent}")
        print(f"  Position: {idx + 1}/{len(self.pipeline)}")
        print(f"  Pipeline: {' -> '.join(self.pipeline)}")
        print(f"  Expected artifacts: {artifacts}")
        print(f"{'='*60}\n")

        # Check previous step artifacts
        if idx > 0:
            prev_step = self.pipeline[idx - 1]
            prev_validation = validate_step_artifacts(prev_step, self.artifacts_dir)
            status_icon = "[PASS]" if prev_validation["all_valid"] else "[FAIL]"
            print(f"  Previous step '{prev_step}' artifacts: {status_icon}")
            for name, detail in prev_validation["details"].items():
                icon = "[PASS]" if detail["schema_valid"] else "[FAIL]"
                print(f"    {icon} {name}: exists={detail['exists']}, schema_valid={detail['schema_valid']}")
                if detail["errors"]:
                    for err in detail["errors"]:
                        print(f"       ERROR: {err}")

        # Show next step
        if idx < len(self.pipeline) - 1:
            print(f"\n  -> Next step after this: {self.pipeline[idx + 1]}")
        else:
            print(f"\n  -> This is the FINAL step")

    def execute_step(self, step: str) -> dict[str, Any]:
        """Execute a single step (mock execution for smoke test)."""
        agent = STEP_AGENT_MAP.get(step, "unknown")
        artifacts = STEP_ARTIFACTS.get(step, [])
        result: dict[str, Any] = {"step": step, "agent": agent, "artifacts": {}, "success": True}

        self.logger.info("Executing step: %s (agent=%s)", step, agent)

        # Emit subtask_created + subtask_started
        self.emit(
            event_type="subtask_created",
            agent=agent,
            status="pending",
            payload={"step": step, "task_id": self.task_id},
        )
        self.emit(
            event_type="subtask_started",
            agent=agent,
            status="running",
            payload={"step": step},
        )

        # --- Mock execution: generate placeholder artifacts ---
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)

        for artifact_name in artifacts:
            artifact_path = self.artifacts_dir / artifact_name
            try:
                if artifact_name.endswith(".json"):
                    self._write_mock_json(artifact_path, artifact_name)
                elif artifact_name.endswith(".md"):
                    self._write_mock_md(artifact_path, artifact_name, step)
                else:
                    artifact_path.write_text("# placeholder\n", encoding="utf-8")

                result["artifacts"][artifact_name] = "created"
                self.emit(
                    event_type="artifact_created",
                    agent=agent,
                    status="success",
                    payload={"step": step, "artifact": artifact_name, "path": str(artifact_path)},
                )
            except OSError as exc:
                result["artifacts"][artifact_name] = f"error: {exc}"
                result["success"] = False
                self.emit(
                    event_type="artifact_created",
                    agent=agent,
                    status="failed",
                    payload={"step": step, "artifact": artifact_name},
                    error=str(exc),
                )

        # Validate created artifacts
        validation = validate_step_artifacts(step, self.artifacts_dir)

        # Special handling: QA reviewer step
        if step == "qa-reviewer":
            result["qa_result"] = self._run_qa_review(agent, validation)
            if result["qa_result"].get("result") == "hard_fail":
                result["success"] = False
                self.emit(
                    event_type="task_failed",
                    agent=agent,
                    status="hard_fail",
                    payload={"step": step, "reason": "QA hard_fail"},
                )
                self.run_state.status = "failed"
                self.run_state.save(self.run_state_path)
                return result

        # Mark subtask done
        status = "success" if result["success"] else "failed"
        self.emit(
            event_type="subtask_done",
            agent=agent,
            status=status,
            payload={"step": step, "validation": validation},
            error=None if result["success"] else "Step execution failed",
        )

        # Update run state
        if step not in self.run_state.completed_steps:
            self.run_state.completed_steps.append(step)
        current_idx = self.pipeline.index(step) if step in self.pipeline else -1
        if current_idx >= 0 and current_idx < len(self.pipeline) - 1:
            self.run_state.current_step = self.pipeline[current_idx + 1]
        else:
            self.run_state.current_step = None
            self.run_state.status = "completed"
        self.run_state.save(self.run_state_path)

        return result

    def _write_mock_json(self, path: Path, artifact_name: str) -> None:
        templates: dict[str, Any] = {
            "task-brief.json": {
                "task_id": self.task_id,
                "title": "AI Programming Assistants 2025 Market Landscape",
                "description": "Research the 2025 market landscape for AI programming assistants.",
                "requirements": ["Identify key players", "Analyze market share", "Review capabilities"],
                "created_at": datetime.now(timezone.utc).isoformat(),
            },
            "claim-evidence-map.json": {
                "claims": [
                    {"id": "c1", "text": "GitHub Copilot leads in market share.", "confidence": "high"},
                    {"id": "c2", "text": "Cursor is growing rapidly among developers.", "confidence": "medium"},
                ],
                "evidence_map": {
                    "c1": ["e1", "e2"],
                    "c2": ["e3"],
                },
            },
            "qa-review.json": {
                "review_status": "pass",
                "findings": ["Well-structured report", "Sources cited adequately"],
                "scored_categories": {
                    "accuracy": 0.92,
                    "completeness": 0.88,
                    "clarity": 0.95,
                    "source_quality": 0.85,
                },
            },
            "orchestration-plan.json": {
                "plan_id": f"plan-{self.task_id}",
                "steps": [s for s in self.pipeline],
            },
            "eval-result.json": {
                "eval_id": f"eval-{self.task_id}",
                "passed": True,
                "metrics": {
                    "artifacts_count": 6,
                    "schema_compliance": 1.0,
                    "qa_pass": True,
                    "no_hard_fail": True,
                },
            },
        }
        data = templates.get(artifact_name, {"placeholder": True})
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    def _write_mock_md(self, path: Path, artifact_name: str, step: str) -> None:
        templates: dict[str, str] = {
            "research-notes.md": (
                "# Research Notes: AI Programming Assistants 2025\n\n"
                "## Key Players\n\n"
                "- GitHub Copilot (Microsoft)\n"
                "- Cursor (Anysphere)\n"
                "- Amazon CodeWhisperer\n"
                "- JetBrains AI Assistant\n"
                "- Continue.dev\n\n"
                "## Market Trends\n\n"
                "1. Increased adoption across enterprise teams\n"
                "2. Integration with IDEs becoming standard\n"
                "3. Open-source alternatives emerging\n\n"
                "## Sources\n\n"
                "- Gartner Hype Cycle 2024\n"
                "- Stack Overflow Developer Survey 2024\n"
            ),
            "analysis-report.md": (
                "# Analysis Report: AI Programming Assistants Market 2025\n\n"
                "## Executive Summary\n\n"
                "The AI programming assistant market in 2025 shows continued growth\n"
                "with GitHub Copilot maintaining leadership while new entrants\n"
                "like Cursor gain significant traction.\n\n"
                "## Market Share Analysis\n\n"
                "| Vendor | Share | Trend |\n"
                "|--------|-------|-------|\n"
                "| GitHub Copilot | 35% | stable |\n"
                "| Cursor | 18% | up |\n"
                "| CodeWhisperer | 12% | down |\n\n"
                "## Recommendations\n\n"
                "- Monitor Cursor growth closely\n"
                "- Evaluate enterprise security features\n"
            ),
            "final-report.md": (
                "# Final Report: AI Programming Assistants 2025 Market Landscape\n\n"
                "# Introduction\n\n"
                "This report examines the competitive landscape of AI programming\n"
                "assistants as of 2025, analyzing key players, market dynamics,\n"
                "and emerging trends.\n\n"
                "## Market Overview\n\n"
                "The market for AI-powered programming assistants has matured\n"
                "significantly since 2023, with enterprise adoption reaching\n"
                "critical mass in Q4 2024.\n\n"
                "## Key Findings\n\n"
                "1. **Market Leadership**: GitHub Copilot continues to lead with\n"
                "   approximately 35% market share among professional developers.\n\n"
                "2. **Rapid Growth**: Cursor has experienced the fastest growth,\n"
                "   increasing from 5% to 18% market share in 12 months.\n\n"
                "3. **Enterprise Focus**: Vendors are increasingly competing on\n"
                "   enterprise security, compliance, and team features.\n\n"
                "## Detailed Analysis\n\n"
                "### GitHub Copilot\n\n"
                "Microsoft's GitHub Copilot remains the market leader, benefiting\n"
                "from deep IDE integration and first-mover advantages.\n\n"
                "### Cursor\n\n"
                "Cursor's context-aware editing and composer features have\n"
                "resonated strongly with power users.\n\n"
                "## Conclusion\n\n"
                "The AI programming assistant market is consolidating around\n"
                "a few key players while remaining open to innovation.\n\n"
                "## References\n\n"
                "- Stack Overflow Developer Survey 2024\n"
                "- GitHub Universe 2024 Keynote\n"
                "- Gartner Market Analysis Q1 2025\n"
            ),
        }
        content = templates.get(artifact_name, f"# {artifact_name}\n\nPlaceholder content for {step}\n")
        path.write_text(content, encoding="utf-8")

    def _run_qa_review(self, agent: str, validation: dict[str, Any]) -> dict[str, Any]:
        """Run QA review and record result."""
        self.emit(
            event_type="quality_review_started",
            agent=agent,
            status="running",
            payload={"step": "qa-reviewer"},
        )

        # Mock QA review - check if all expected artifacts exist
        all_artifacts_valid = validation["all_valid"]
        qa_result = {
            "result": "pass" if all_artifacts_valid else "hard_fail",
            "findings": ["All artifacts present and valid"] if all_artifacts_valid else ["Missing or invalid artifacts"],
            "scored_categories": {
                "accuracy": 0.92,
                "completeness": 0.88,
                "clarity": 0.95,
                "source_quality": 0.85,
            },
        }

        self.emit(
            event_type="quality_review_done",
            agent=agent,
            status="success",
            payload={"step": "qa-reviewer", **qa_result},
        )
        return qa_result

    def run_step(self, step: str) -> dict[str, Any]:
        """Run (or preview) a single step."""
        if step not in self.pipeline:
            raise ValueError(f"Unknown step: {step}. Valid steps in pipeline: {self.pipeline}")

        self.init_task()

        if self.dry_run:
            self.preview_step(step)
            return {"mode": "dry-run", "step": step}

        # Check for hard_fail from previous QA
        if self.event_writer.has_hard_fail():
            self.logger.error("Cannot proceed: previous QA review resulted in hard_fail")
            return {"error": "Blocked by previous hard_fail", "step": step}

        # Check if step already completed
        if step in self.event_writer.get_completed_steps():
            self.logger.info("Step '%s' already completed. Skipping execution.", step)
            return {"step": step, "status": "skipped", "reason": "already_completed"}

        # Validate previous step artifacts (within the pipeline)
        idx = self.pipeline.index(step)
        if idx > 0:
            prev_step = self.pipeline[idx - 1]
            prev_validation = validate_step_artifacts(prev_step, self.artifacts_dir)
            if not prev_validation["all_valid"]:
                self.logger.error("Previous step '%s' has invalid artifacts. Blocking.", prev_step)
                self.emit(
                    event_type="blocker_found",
                    agent="integration-smoke-runner",
                    status="blocked",
                    payload={"step": step, "blocked_by": prev_step, "reason": "invalid_artifacts"},
                )
                return {"step": step, "status": "blocked", "blocked_by": prev_step}

        # Execute
        result = self.execute_step(step)

        # Print summary
        print(f"\n{'='*60}")
        print(f"  Step '{step}' Result: {'SUCCESS' if result['success'] else 'FAILED'}")
        print(f"{'='*60}")
        for art, status in result["artifacts"].items():
            icon = "[PASS]" if status == "created" else "[FAIL]"
            print(f"  {icon} {art}: {status}")
        if "qa_result" in result:
            print(f"\n  QA Result: {result['qa_result']['result']}")
        print()

        return result

    def resume_from(self, step: str) -> dict[str, Any]:
        """Resume execution from a given step."""
        if step not in self.pipeline:
            raise ValueError(f"Unknown step: {step} in pipeline {self.pipeline}")

        self.init_task()

        # Determine which steps are already completed
        completed = self.event_writer.get_completed_steps()
        start_idx = self.pipeline.index(step)

        results: list[dict[str, Any]] = []
        for s in self.pipeline[start_idx:]:
            if s in completed:
                self.logger.info("Step '%s' already completed - skipping", s)
                results.append({"step": s, "status": "skipped", "reason": "already_completed"})
                continue
            result = self.run_step(s)
            results.append(result)
            if not result.get("success", True):
                self.logger.error("Step '%s' failed. Stopping resume.", s)
                break

        return {"resume_from": step, "results": results}

    def run_full(self) -> dict[str, Any]:
        """Run the full pipeline (step by step with confirmation)."""
        self.init_task()
        results: list[dict[str, Any]] = []

        for step in self.pipeline:
            if self.dry_run:
                self.preview_step(step)
                results.append({"step": step, "mode": "dry-run"})
                continue

            # In semi-auto mode, require explicit --step
            # Here we just run if not already done
            if step in self.event_writer.get_completed_steps():
                results.append({"step": step, "status": "skipped"})
                continue

            result = self.run_step(step)
            results.append(result)
            if not result.get("success", True):
                break

        # Emit final event
        all_success = all(r.get("success", True) for r in results if "success" in r)
        if all_success and not self.dry_run:
            self.emit(
                event_type="task_completed",
                agent="integration-smoke-runner",
                status="success",
                payload={"task_id": self.task_id, "completed_steps": self.run_state.completed_steps},
            )

        return {"task_id": self.task_id, "dry_run": self.dry_run, "pipeline": self.pipeline, "results": results}

    def validate_current_step(self) -> dict[str, Any]:
        """Validate the current/next step's prerequisites."""
        completed = self.event_writer.get_completed_steps()

        # Find the next uncompleted step in the pipeline
        next_step = None
        for step in self.pipeline:
            if step not in completed:
                next_step = step
                break

        if next_step is None:
            return {"status": "all_completed", "message": "All steps are completed", "pipeline": self.pipeline}

        idx = self.pipeline.index(next_step)
        status = "ready"
        checks: dict[str, Any] = {
            "step": next_step,
            "previous_steps_completed": list(completed),
            "pipeline": self.pipeline,
        }

        # Validate previous step artifacts
        if idx > 0:
            prev_step = self.pipeline[idx - 1]
            validation = validate_step_artifacts(prev_step, self.artifacts_dir)
            checks["previous_artifact_validation"] = validation
            if not validation["all_valid"]:
                status = "blocked"

        # Check for hard_fail
        if self.event_writer.has_hard_fail():
            status = "blocked"
            checks["hard_fail"] = True

        return {
            "step_status": "completed" if next_step in completed else (status if status != "blocked" else "blocked"),
            "next_step": next_step,
            "checks": checks,
        }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Integration Smoke Runner - v1.2 (semi-automatic stage progression)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --task-id root.integration_smoke_001
  %(prog)s --step task-intake
  %(prog)s --resume-from-step analyst
  %(prog)s --dry-run
  %(prog)s --validate-step
        """,
    )
    parser.add_argument(
        "--task-id",
        default="root.integration_smoke_001",
        help="Task identifier (default: root.integration_smoke_001)",
    )
    parser.add_argument(
        "--step",
        help=f"Execute a single step explicitly. Valid steps: {', '.join(L1_MAIN_LINK)}",
    )
    parser.add_argument(
        "--resume-from-step",
        dest="resume_from",
        help=f"Resume execution from the given step. Valid steps: {', '.join(L1_MAIN_LINK)}",
    )
    parser.add_argument(
        "--pipeline",
        choices=["full", "deep-research"],
        default="deep-research",
        help="Pipeline to use: 'full' (L1 main link) or 'deep-research' (minimal, default)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview mode: show what would happen without executing",
    )
    parser.add_argument(
        "--validate-step",
        action="store_true",
        help="Validate the current/next step prerequisites",
    )
    parser.add_argument(
        "--runtime-dir",
        type=Path,
        default=RUNTIME_DIR,
        help=f"Runtime directory (default: {RUNTIME_DIR})",
    )
    parser.add_argument(
        "--artifacts-dir",
        type=Path,
        default=ARTIFACTS_DIR,
        help=f"Artifacts base directory (default: {ARTIFACTS_DIR})",
    )
    parser.add_argument(
        "--evals-dir",
        type=Path,
        default=EVALS_DIR,
        help=f"Evaluations directory (default: {EVALS_DIR})",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format=LOG_FORMAT,
    )
    logger = logging.getLogger("main")

    pipeline = DEEP_RESEARCH_PIPELINE if args.pipeline == "deep-research" else L1_MAIN_LINK

    runner = IntegrationSmokeRunner(
        task_id=args.task_id,
        runtime_dir=args.runtime_dir,
        artifacts_dir=args.artifacts_dir,
        evals_dir=args.evals_dir,
        dry_run=args.dry_run,
        pipeline=pipeline,
    )

    try:
        if args.validate_step:
            result = runner.validate_current_step()
            print(json.dumps(result, indent=2, ensure_ascii=False))
            return 0 if result.get("step_status") not in ("blocked",) else 1

        if args.step:
            result = runner.run_step(args.step)
            return 0 if result.get("success", True) else 1

        if args.resume_from:
            result = runner.resume_from(args.resume_from)
            all_ok = all(r.get("success", True) for r in result.get("results", []))
            return 0 if all_ok else 1

        # Default: full run (dry-run by default unless --step specified)
        result = runner.run_full()
        return 0

    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        runner.emit(
            event_type="task_failed",
            agent="integration-smoke-runner",
            status="interrupted",
            payload={"reason": "keyboard_interrupt"},
        )
        return 130
    except Exception as exc:
        logger.exception("Runner failed: %s", exc)
        runner.emit(
            event_type="task_failed",
            agent="integration-smoke-runner",
            status="error",
            payload={"reason": str(exc)},
            error=str(exc),
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
