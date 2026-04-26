#!/usr/bin/env python3
"""
Task Events Replay & Summary — v1.2
Kimi Production-Grade Agent Pack

Reads task-events JSONL files, replays events chronologically,
generates timeline summaries, identifies failures and blockers.

Usage:
    python replay_task_events.py --task-id root.integration_smoke_001
    python replay_task_events.py --format summary
    python replay_task_events.py --format full
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

EVENT_TYPES_FOR_DISPLAY: dict[str, str] = {
    "task_created": "TASK CREATED",
    "subtask_created": "SUBTASK CREATED",
    "subtask_assigned": "SUBTASK ASSIGNED",
    "subtask_started": "SUBTASK STARTED",
    "subtask_done": "SUBTASK DONE",
    "artifact_created": "ARTIFACT CREATED",
    "blocker_found": "BLOCKER FOUND",
    "quality_review_started": "QA REVIEW STARTED",
    "quality_review_done": "QA REVIEW DONE",
    "task_completed": "TASK COMPLETED",
    "task_failed": "TASK FAILED",
}

RUNTIME_DIR = Path("runtime")

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

    @property
    def display_type(self) -> str:
        return EVENT_TYPES_FOR_DISPLAY.get(self.event_type, self.event_type.upper())

    @property
    def is_failure(self) -> bool:
        return self.event_type in ("task_failed", "blocker_found") or self.error is not None

    @property
    def is_blocker(self) -> bool:
        return self.event_type == "blocker_found"

    @property
    def timestamp_pretty(self) -> str:
        try:
            dt = datetime.fromisoformat(self.timestamp)
            return dt.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3] + " UTC"
        except (ValueError, TypeError):
            return str(self.timestamp)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TaskEvent:
        return cls(
            event_id=data.get("event_id", "unknown"),
            task_id=data.get("task_id", "unknown"),
            event_type=data.get("event_type", "unknown"),
            timestamp=data.get("timestamp", ""),
            agent=data.get("agent", "unknown"),
            status=data.get("status", "unknown"),
            payload=data.get("payload", {}),
            error=data.get("error"),
        )


@dataclass
class StepSummary:
    step_name: str
    agent: str = ""
    started_at: str = ""
    completed_at: str = ""
    status: str = "pending"  # pending | running | success | failed | blocked
    artifacts: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)

    @property
    def duration_seconds(self) -> float | None:
        if not self.started_at or not self.completed_at:
            return None
        try:
            start = datetime.fromisoformat(self.started_at)
            end = datetime.fromisoformat(self.completed_at)
            return (end - start).total_seconds()
        except (ValueError, TypeError):
            return None


@dataclass
class ReplayReport:
    task_id: str
    total_events: int = 0
    event_breakdown: dict[str, int] = field(default_factory=dict)
    step_summaries: dict[str, StepSummary] = field(default_factory=dict)
    failures: list[dict[str, Any]] = field(default_factory=list)
    blockers: list[dict[str, Any]] = field(default_factory=list)
    artifacts_created: list[str] = field(default_factory=list)
    qa_result: dict[str, Any] | None = None
    task_status: str = "unknown"
    started_at: str = ""
    completed_at: str = ""
    duration_seconds: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "total_events": self.total_events,
            "event_breakdown": self.event_breakdown,
            "step_summaries": {
                name: {
                    "agent": s.agent,
                    "status": s.status,
                    "started_at": s.started_at,
                    "completed_at": s.completed_at,
                    "duration_seconds": s.duration_seconds,
                    "artifacts": s.artifacts,
                    "errors": s.errors,
                    "blockers": s.blockers,
                }
                for name, s in self.step_summaries.items()
            },
            "failures": self.failures,
            "blockers": self.blockers,
            "artifacts_created": self.artifacts_created,
            "qa_result": self.qa_result,
            "task_status": self.task_status,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "duration_seconds": self.duration_seconds,
        }


# ---------------------------------------------------------------------------
# Task events reader
# ---------------------------------------------------------------------------

class TaskEventReader:
    def __init__(self, task_id: str, runtime_dir: Path = RUNTIME_DIR) -> None:
        self.task_id = task_id
        self.runtime_dir = runtime_dir
        self.file_path = runtime_dir / f"task-events-{task_id}.jsonl"
        self.logger = logging.getLogger(self.__class__.__name__)

    def read_all(self) -> list[TaskEvent]:
        events: list[TaskEvent] = []
        if not self.file_path.exists():
            self.logger.warning("Task events file not found: %s", self.file_path)
            return events

        with open(self.file_path, "r", encoding="utf-8") as f:
            for line_no, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    events.append(TaskEvent.from_dict(data))
                except (json.JSONDecodeError, KeyError, TypeError) as exc:
                    self.logger.warning("Skipping invalid event at line %d: %s", line_no, exc)

        # Sort by timestamp
        events.sort(key=lambda e: e.timestamp)
        return events


# ---------------------------------------------------------------------------
# Replay engine
# ---------------------------------------------------------------------------

class TaskReplayEngine:
    def __init__(self, events: list[TaskEvent], task_id: str) -> None:
        self.events = events
        self.task_id = task_id
        self.logger = logging.getLogger(self.__class__.__name__)

    def build_report(self) -> ReplayReport:
        report = ReplayReport(task_id=self.task_id)
        report.total_events = len(self.events)

        for event in self.events:
            # Event breakdown
            report.event_breakdown[event.event_type] = report.event_breakdown.get(event.event_type, 0) + 1

            # Timeline
            if event.event_type == "task_created":
                report.started_at = event.timestamp
            if event.event_type in ("task_completed", "task_failed"):
                report.completed_at = event.timestamp
                report.task_status = event.status

            # Step tracking
            step = event.payload.get("step", "")
            if step and step not in report.step_summaries:
                report.step_summaries[step] = StepSummary(step_name=step, agent=event.agent)

            if step:
                summary = report.step_summaries[step]
                summary.agent = event.agent

                if event.event_type == "subtask_started":
                    summary.status = "running"
                    summary.started_at = event.timestamp
                elif event.event_type == "subtask_done":
                    summary.completed_at = event.timestamp
                    summary.status = event.status
                elif event.event_type == "artifact_created":
                    artifact = event.payload.get("artifact", "")
                    if artifact and artifact not in summary.artifacts:
                        summary.artifacts.append(artifact)
                    if artifact and artifact not in report.artifacts_created:
                        report.artifacts_created.append(artifact)
                elif event.event_type == "blocker_found":
                    summary.status = "blocked"
                    blocker = event.payload.get("reason", "unknown")
                    summary.blockers.append(blocker)
                    report.blockers.append({
                        "step": step,
                        "reason": blocker,
                        "timestamp": event.timestamp,
                    })
                elif event.event_type == "quality_review_done":
                    report.qa_result = {
                        "result": event.payload.get("result"),
                        "findings": event.payload.get("findings", []),
                        "scored_categories": event.payload.get("scored_categories", {}),
                    }

            # Failures
            if event.is_failure:
                report.failures.append({
                    "event_type": event.event_type,
                    "agent": event.agent,
                    "status": event.status,
                    "timestamp": event.timestamp,
                    "error": event.error,
                    "payload": event.payload,
                })

        # Calculate total duration
        if report.started_at and report.completed_at:
            try:
                start = datetime.fromisoformat(report.started_at)
                end = datetime.fromisoformat(report.completed_at)
                report.duration_seconds = (end - start).total_seconds()
            except (ValueError, TypeError):
                pass

        return report


# ---------------------------------------------------------------------------
# Formatters
# ---------------------------------------------------------------------------

def format_summary(report: ReplayReport) -> str:
    """Generate a concise summary."""
    lines: list[str] = []
    lines.append("\n" + "=" * 70)
    lines.append("  TASK EVENTS REPLAY — SUMMARY")
    lines.append("=" * 70)
    lines.append(f"  Task ID         : {report.task_id}")
    lines.append(f"  Total Events    : {report.total_events}")
    lines.append(f"  Task Status     : {report.task_status.upper()}")
    lines.append(f"  Duration        : {report.duration_seconds:.3f}s")
    lines.append("")

    # Event breakdown
    lines.append("  Event Breakdown:")
    for event_type, count in sorted(report.event_breakdown.items(), key=lambda x: -x[1]):
        display = EVENT_TYPES_FOR_DISPLAY.get(event_type, event_type)
        lines.append(f"    {display:<35} {count:>3}")

    # Step summary
    lines.append("")
    lines.append("  Step Summary:")
    for step_name, summary in report.step_summaries.items():
        icon = "✓" if summary.status == "success" else "✗" if summary.status in ("failed", "blocked") else "○"
        lines.append(f"    {icon} {step_name:<30} [{summary.status.upper():<10}]  agent={summary.agent}")
        if summary.artifacts:
            lines.append(f"      Artifacts: {', '.join(summary.artifacts)}")
        if summary.errors:
            for err in summary.errors:
                lines.append(f"      ERROR: {err}")
        if summary.blockers:
            for b in summary.blockers:
                lines.append(f"      BLOCKER: {b}")

    # QA Result
    if report.qa_result:
        lines.append("")
        lines.append("  QA Review Result:")
        lines.append(f"    Status: {report.qa_result.get('result', 'N/A')}")
        for finding in report.qa_result.get("findings", []):
            lines.append(f"    - {finding}")

    # Failures
    if report.failures:
        lines.append("")
        lines.append(f"  ⚠ FAILURES ({len(report.failures)}):")
        for fail in report.failures:
            lines.append(f"    [{fail['event_type']}] agent={fail['agent']} status={fail['status']}")
            if fail['error']:
                lines.append(f"      Error: {fail['error']}")

    # Blockers
    if report.blockers:
        lines.append("")
        lines.append(f"  ⛔ BLOCKERS ({len(report.blockers)}):")
        for blocker in report.blockers:
            lines.append(f"    Step '{blocker['step']}': {blocker['reason']}")

    lines.append("")
    lines.append(f"  Artifacts Created ({len(report.artifacts_created)}):")
    for art in report.artifacts_created:
        lines.append(f"    ✓ {art}")

    lines.append("")
    lines.append("=" * 70)
    return "\n".join(lines)


def format_full(events: list[TaskEvent]) -> str:
    """Generate a full chronological replay."""
    lines: list[str] = []
    lines.append("\n" + "=" * 70)
    lines.append("  TASK EVENTS REPLAY — FULL CHRONOLOGY")
    lines.append("=" * 70)
    lines.append(f"  Total Events: {len(events)}")
    lines.append("")

    for idx, event in enumerate(events, 1):
        icon = "⚠" if event.is_failure else "●"
        lines.append(f"  [{idx:>3}] {icon} {event.display_type:<30}  {event.timestamp_pretty}")
        lines.append(f"        Agent : {event.agent}")
        lines.append(f"        Status: {event.status}")
        if event.payload:
            payload_str = json.dumps(event.payload, ensure_ascii=False, indent=12)
            lines.append(f"        Payload:\n{payload_str}")
        if event.error:
            lines.append(f"        ERROR : {event.error}")
        lines.append("")

    lines.append("=" * 70)
    return "\n".join(lines)


def generate_markdown_report(report: ReplayReport, events: list[TaskEvent]) -> str:
    """Generate a markdown replay report."""
    lines: list[str] = []
    lines.append("# Task Events Replay Report\n")
    lines.append(f"- **Task ID**: `{report.task_id}`")
    lines.append(f"- **Total Events**: {report.total_events}")
    lines.append(f"- **Task Status**: `{report.task_status}`")
    lines.append(f"- **Duration**: {report.duration_seconds:.3f}s")
    lines.append(f"- **Generated At**: {datetime.now(timezone.utc).isoformat()}")
    lines.append("")

    # Event breakdown
    lines.append("## Event Breakdown\n")
    lines.append("| Event Type | Count |")
    lines.append("|------------|-------|")
    for event_type, count in sorted(report.event_breakdown.items(), key=lambda x: -x[1]):
        display = EVENT_TYPES_FOR_DISPLAY.get(event_type, event_type)
        lines.append(f"| {display} | {count} |")
    lines.append("")

    # Step summary
    lines.append("## Step Summary\n")
    lines.append("| Step | Agent | Status | Artifacts | Duration |")
    lines.append("|------|-------|--------|-----------|----------|")
    for step_name, summary in report.step_summaries.items():
        artifacts = ", ".join(summary.artifacts) if summary.artifacts else "—"
        duration = f"{summary.duration_seconds:.1f}s" if summary.duration_seconds else "—"
        lines.append(f"| {step_name} | {summary.agent} | {summary.status} | {artifacts} | {duration} |")
    lines.append("")

    # QA Result
    if report.qa_result:
        lines.append("## QA Review Result\n")
        lines.append(f"- **Result**: `{report.qa_result.get('result', 'N/A')}`")
        lines.append("- **Findings**:")
        for finding in report.qa_result.get("findings", []):
            lines.append(f"  - {finding}")
        if report.qa_result.get("scored_categories"):
            lines.append("- **Scores**:")
            for cat, score in report.qa_result["scored_categories"].items():
                lines.append(f"  - {cat}: {score}")
        lines.append("")

    # Failures
    if report.failures:
        lines.append("## Failures\n")
        for fail in report.failures:
            lines.append(f"- **[{fail['event_type']}]** agent={fail['agent']} status={fail['status']}")
            if fail['error']:
                lines.append(f"  - Error: `{fail['error']}`")
        lines.append("")

    # Blockers
    if report.blockers:
        lines.append("## Blockers\n")
        for blocker in report.blockers:
            lines.append(f"- Step `{blocker['step']}`: {blocker['reason']}")
        lines.append("")

    # Full event log
    lines.append("## Full Event Log\n")
    lines.append("| # | Time | Type | Agent | Status | Error |")
    lines.append("|---|------|------|-------|--------|-------|")
    for idx, event in enumerate(events, 1):
        error_str = f"`{event.error}`" if event.error else "—"
        lines.append(
            f"| {idx} | {event.timestamp_pretty} | {event.display_type} | "
            f"{event.agent} | {event.status} | {error_str} |"
        )
    lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Task Events Replay & Summary — v1.2",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --task-id root.integration_smoke_001
  %(prog)s --task-id root.integration_smoke_001 --format summary
  %(prog)s --task-id root.integration_smoke_001 --format full
  %(prog)s --events-file runtime/task-events-custom.jsonl --format full
        """,
    )
    parser.add_argument(
        "--task-id",
        default="root.integration_smoke_001",
        help="Task identifier (default: root.integration_smoke_001)",
    )
    parser.add_argument(
        "--events-file",
        type=Path,
        help="Path to task events JSONL file (overrides --task-id)",
    )
    parser.add_argument(
        "--format",
        choices=["summary", "full"],
        default="summary",
        help="Output format (default: summary)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Output markdown file path (default: auto-generated)",
    )
    parser.add_argument(
        "--runtime-dir",
        type=Path,
        default=RUNTIME_DIR,
        help=f"Runtime directory (default: {RUNTIME_DIR})",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output JSON report to stdout instead of text",
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
        level=logging.DEBUG if args.verbose else logging.WARNING,
        format=LOG_FORMAT,
    )
    logger = logging.getLogger("main")

    # Determine events file
    if args.events_file:
        events_file = args.events_file
        task_id = args.task_id  # still use provided task_id for report
    else:
        task_id = args.task_id
        events_file = args.runtime_dir / f"task-events-{task_id}.jsonl"

    if not events_file.exists():
        print(f"ERROR: Task events file not found: {events_file}", file=sys.stderr)
        return 1

    # Read events
    reader = TaskEventReader(task_id, args.runtime_dir)
    events = reader.read_all()
    if not events:
        print("WARNING: No events found in file.", file=sys.stderr)
        return 0

    logger.info("Read %d events for task %s", len(events), task_id)

    # Build report
    engine = TaskReplayEngine(events, task_id)
    report = engine.build_report()

    # Determine output
    if args.json:
        output = json.dumps(report.to_dict(), indent=2, ensure_ascii=False)
    elif args.format == "full":
        output = format_full(events)
    else:
        output = format_summary(report)

    print(output)

    # Write markdown report
    output_path = args.output
    if output_path is None:
        output_path = args.runtime_dir / f"task-replay-{task_id}.md"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    md_content = generate_markdown_report(report, events)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(md_content)

    print(f"\nMarkdown report written to: {output_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
