#!/usr/bin/env python3
"""
Task Timeline Generator - Summary/Full dual modes

Generates a task execution timeline from run-state.json and step definitions.

Usage:
    python generate_task_timeline.py --run-state runtime/run-state.json --mode summary
    python generate_task_timeline.py --run-state runtime/run-state.json --mode full --output timeline.json
    python generate_task_timeline.py --case-id CASE-001 --mode full
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

DEFAULT_STEP_DEFINITIONS = [
    {
        "step_id": "step-1",
        "step_name": "task-intake",
        "display_order": 1,
        "estimated_duration_minutes": 15,
        "depends_on": [],
        "artifacts": ["artifacts/task-understanding.json", "artifacts/requirement-clarification.md"],
        "prompt_template": "docs/assisted-mode-prompts.md#step-1-task-intake",
    },
    {
        "step_id": "step-2",
        "step_name": "researcher",
        "display_order": 2,
        "estimated_duration_minutes": 30,
        "depends_on": ["step-1"],
        "artifacts": ["artifacts/evidence-map.json", "artifacts/researcher-notes.md"],
        "prompt_template": "docs/assisted-mode-prompts.md#step-2-researcher",
    },
    {
        "step_id": "step-3",
        "step_name": "analyst",
        "display_order": 3,
        "estimated_duration_minutes": 25,
        "depends_on": ["step-2"],
        "artifacts": ["artifacts/analysis-report.json", "artifacts/insight-summary.md"],
        "prompt_template": "docs/assisted-mode-prompts.md#step-3-analyst",
    },
    {
        "step_id": "step-4",
        "step_name": "evidence-synthesis",
        "display_order": 4,
        "estimated_duration_minutes": 20,
        "depends_on": ["step-3"],
        "artifacts": ["artifacts/synthesis-report.json", "artifacts/conflict-resolution.md"],
        "prompt_template": "docs/assisted-mode-prompts.md#step-4-evidence-synthesis",
    },
    {
        "step_id": "step-5",
        "step_name": "writer",
        "display_order": 5,
        "estimated_duration_minutes": 35,
        "depends_on": ["step-4"],
        "artifacts": ["artifacts/final-report.md", "artifacts/report-quality.json"],
        "prompt_template": "docs/assisted-mode-prompts.md#step-5-writer",
    },
    {
        "step_id": "step-6",
        "step_name": "qa-reviewer",
        "display_order": 6,
        "estimated_duration_minutes": 20,
        "depends_on": ["step-5"],
        "artifacts": ["artifacts/qa-review.json", "artifacts/qa-findings.md"],
        "prompt_template": "docs/assisted-mode-prompts.md#step-6-qa-reviewer",
    },
    {
        "step_id": "step-7",
        "step_name": "release",
        "display_order": 7,
        "estimated_duration_minutes": 10,
        "depends_on": ["step-6"],
        "artifacts": ["artifacts/release-check.json"],
        "prompt_template": None,
    },
]


def _iso_timestamp() -> str:
    return datetime.now().isoformat()


def load_run_state(run_state_path: str) -> Optional[Dict]:
    """Load run-state.json file."""
    if not os.path.exists(run_state_path):
        return None
    try:
        with open(run_state_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return None


def generate_timeline(
    case_id: str,
    run_state: Optional[Dict],
    mode: str,
    step_definitions: Optional[List[Dict]] = None,
) -> Dict:
    """Generate task timeline."""
    steps_def = step_definitions or DEFAULT_STEP_DEFINITIONS
    timeline = {
        "case_id": case_id,
        "version": "1.5",
        "generated_at": _iso_timestamp(),
        "timeline_mode": mode,
        "total_steps": len(steps_def),
        "completed_steps": 0,
        "pending_steps": 0,
        "blocked_steps": 0,
        "total_estimated_duration_minutes": 0,
        "steps": [],
    }

    # Map run state step status
    step_status_map = {}
    step_artifacts = {}
    if run_state:
        step_status_map = run_state.get("step_status", {})
        step_artifacts = run_state.get("artifacts", {})

    for step_def in steps_def:
        step_name = step_def["step_name"]
        status = step_status_map.get(step_name, "not_started")
        artifacts = step_artifacts.get(step_name, step_def.get("artifacts", []))

        timeline["total_estimated_duration_minutes"] += step_def.get(
            "estimated_duration_minutes", 0
        )

        if status == "completed":
            timeline["completed_steps"] += 1
        elif status == "blocked":
            timeline["blocked_steps"] += 1
        elif status in ("not_started", "incomplete"):
            timeline["pending_steps"] += 1

        step_entry = {
            "step_id": step_def["step_id"],
            "step_name": step_name,
            "display_order": step_def["display_order"],
            "status": status,
            "estimated_duration_minutes": step_def.get("estimated_duration_minutes"),
            "depends_on": step_def.get("depends_on", []),
            "artifacts": artifacts,
        }

        if mode == "full":
            step_entry["prompt_template"] = step_def.get("prompt_template")
            step_entry["actual_duration_minutes"] = None  # Not tracked in basic mode
            step_entry["notes"] = _get_step_note(status, step_name)

            if run_state:
                started = run_state.get("run_metadata", {}).get("started_at")
                if started and status == "completed":
                    # Estimate actual duration (simplified)
                    step_entry["started_at"] = started

        timeline["steps"].append(step_entry)

    return timeline


def _get_step_note(status: str, step_name: str) -> str:
    """Get a human-readable note for a step status."""
    notes = {
        "not_started": f"Step '{step_name}' has not been started yet. Copy the prompt from docs/assisted-mode-prompts.md and paste into Kimi Code.",
        "in_progress": f"Step '{step_name}' is currently in progress. Wait for completion and validate the output artifacts.",
        "completed": f"Step '{step_name}' is complete. Validate artifacts and proceed to next step.",
        "blocked": f"Step '{step_name}' is BLOCKED. Check blocking_reasons and consult recovery-runbook.md before proceeding.",
        "incomplete": f"Step '{step_name}' is incomplete. Review outputs and determine if retry or fallback is needed.",
        "failed": f"Step '{step_name}' failed. Consult recovery-runbook.md for error-specific recovery procedures.",
        "skipped": f"Step '{step_name}' was skipped. Ensure this is intentional and documented.",
    }
    return notes.get(status, f"Unknown status for step '{step_name}'")


def format_timeline_text(timeline: Dict) -> str:
    """Format timeline as human-readable text."""
    lines = []
    lines.append("=" * 60)
    lines.append(f"  Task Timeline: {timeline['case_id']}")
    lines.append(f"  Mode: {timeline['timeline_mode'].upper()}")
    lines.append(f"  Generated: {timeline['generated_at']}")
    lines.append("=" * 60)
    lines.append("")
    lines.append(f"  Progress: {timeline['completed_steps']}/{timeline['total_steps']} steps completed")
    lines.append(f"  Blocked:  {timeline['blocked_steps']}")
    lines.append(f"  Pending:  {timeline['pending_steps']}")
    lines.append(f"  Estimated Total Duration: {timeline['total_estimated_duration_minutes']} minutes")
    lines.append("")

    for step in timeline["steps"]:
        status_icon = {
            "completed": "[PASS]",
            "blocked": "[BLOCK]",
            "in_progress": "[RUN ]",
            "failed": "[FAIL]",
            "not_started": "[WAIT]",
            "incomplete": "[PART]",
            "skipped": "[SKIP]",
        }.get(step["status"], "[ ?  ]")

        lines.append(f"  {status_icon} {step['display_order']}. {step['step_name']}")
        if timeline["timeline_mode"] == "full":
            lines.append(f"       Status: {step['status']}")
            if step.get("estimated_duration_minutes"):
                lines.append(f"       Est. Duration: {step['estimated_duration_minutes']} min")
            if step.get("artifacts"):
                lines.append(f"       Artifacts: {', '.join(step['artifacts'])}")
            if step.get("notes"):
                lines.append(f"       Note: {step['notes']}")
            lines.append("")

    lines.append("=" * 60)
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Task Timeline Generator")
    parser.add_argument(
        "--run-state",
        dest="run_state",
        default="runtime/run-state.json",
        help="Path to run-state.json (default: runtime/run-state.json)",
    )
    parser.add_argument(
        "--case-id",
        dest="case_id",
        default=None,
        help="Case ID (auto-detected from run-state if not provided)",
    )
    parser.add_argument(
        "--mode",
        choices=["summary", "full"],
        default="summary",
        help="Timeline detail level (default: summary)",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output JSON file path (default: print to stdout)",
    )
    parser.add_argument(
        "--text-output",
        dest="text_output",
        default=None,
        help="Output human-readable text file path",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Only output JSON",
    )

    args = parser.parse_args()

    # Load run state
    run_state = load_run_state(args.run_state)

    # Determine case_id
    case_id = args.case_id
    if not case_id and run_state:
        case_id = run_state.get("case_id", "unknown")
    if not case_id:
        case_id = "unknown-case"

    # Generate timeline
    timeline = generate_timeline(
        case_id=case_id,
        run_state=run_state,
        mode=args.mode,
    )

    # Write outputs
    if args.output:
        out_dir = os.path.dirname(args.output)
        if out_dir and not os.path.exists(out_dir):
            os.makedirs(out_dir, exist_ok=True)
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(timeline, f, indent=2, ensure_ascii=False)
        if not args.quiet:
            print(f"Timeline written to: {args.output}")

    if args.text_output:
        text = format_timeline_text(timeline)
        out_dir = os.path.dirname(args.text_output)
        if out_dir and not os.path.exists(out_dir):
            os.makedirs(out_dir, exist_ok=True)
        with open(args.text_output, "w", encoding="utf-8") as f:
            f.write(text)
        if not args.quiet:
            print(f"Text timeline written to: {args.text_output}")

    # Always print timeline to stdout (unless quiet)
    if not args.quiet:
        print(format_timeline_text(timeline))
    else:
        print(json.dumps(timeline, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
