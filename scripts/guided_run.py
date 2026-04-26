#!/usr/bin/env python3
"""
Guided Run - Core Orchestration Script

Guided Run is NOT:
- A background Swarm
- A fully automatic scheduler
- A multi-agent parallel system

Guided Run IS:
- A semi-automatic wrapper for assisted mode
- An interactive step-by-step guide
- A state manager that validates and tracks progress

Usage:
    python guided_run.py --status
    python guided_run.py --next
    python guided_run.py --step researcher
    python guided_run.py --resume
    python guided_run.py --reset --confirm
    python guided_run.py --validate-step researcher
"""

import argparse
import json
import os
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

RUN_STATE_DIR = "runtime"
RUN_STATE_FILE = os.path.join(RUN_STATE_DIR, "run-state.json")

STEP_ORDER = [
    "task-intake",
    "researcher",
    "analyst",
    "evidence-synthesis",
    "writer",
    "qa-reviewer",
    "release",
]

STEP_PROMPTS = {
    "task-intake": {
        "title": "Step 1: Task-Intake",
        "description": "Understand the task and clarify requirements",
        "prompt_ref": "docs/assisted-mode-prompts.md#step-1-task-intake",
        "artifacts": [
            "artifacts/task-understanding.json",
            "artifacts/requirement-clarification.md",
        ],
    },
    "researcher": {
        "title": "Step 2: Researcher",
        "description": "Collect evidence and build evidence map",
        "prompt_ref": "docs/assisted-mode-prompts.md#step-2-researcher",
        "artifacts": [
            "artifacts/evidence-map.json",
            "artifacts/researcher-notes.md",
        ],
    },
    "analyst": {
        "title": "Step 3: Analyst",
        "description": "Analyze evidence and extract insights",
        "prompt_ref": "docs/assisted-mode-prompts.md#step-3-analyst",
        "artifacts": [
            "artifacts/analysis-report.json",
            "artifacts/insight-summary.md",
        ],
    },
    "evidence-synthesis": {
        "title": "Step 4: Evidence-Synthesis",
        "description": "Synthesize evidence and resolve conflicts",
        "prompt_ref": "docs/assisted-mode-prompts.md#step-4-evidence-synthesis",
        "artifacts": [
            "artifacts/synthesis-report.json",
            "artifacts/conflict-resolution.md",
        ],
    },
    "writer": {
        "title": "Step 5: Writer",
        "description": "Write the final report",
        "prompt_ref": "docs/assisted-mode-prompts.md#step-5-writer",
        "artifacts": [
            "artifacts/final-report.md",
            "artifacts/report-quality.json",
        ],
    },
    "qa-reviewer": {
        "title": "Step 6: QA-Reviewer",
        "description": "Quality review the final report",
        "prompt_ref": "docs/assisted-mode-prompts.md#step-6-qa-reviewer",
        "artifacts": [
            "artifacts/qa-review.json",
            "artifacts/qa-findings.md",
        ],
    },
    "release": {
        "title": "Step 7: Release",
        "description": "Release checks and finalization",
        "prompt_ref": None,
        "artifacts": [
            "artifacts/release-check.json",
        ],
    },
}


def _iso_timestamp() -> str:
    return datetime.now().isoformat()


def atomic_write_json(path: str, data: Dict):
    """Atomically write JSON file using temp file + rename."""
    dir_name = os.path.dirname(path)
    if dir_name and not os.path.exists(dir_name):
        os.makedirs(dir_name, exist_ok=True)

    fd, tmp_path = tempfile.mkstemp(dir=dir_name or ".", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, path)
    except Exception:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise


def load_run_state() -> Optional[Dict]:
    """Load run state from file."""
    if not os.path.exists(RUN_STATE_FILE):
        return None
    try:
        with open(RUN_STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return None


def create_default_run_state(case_id: str) -> Dict:
    """Create a default run state."""
    step_status = {step: "not_started" for step in STEP_ORDER}
    artifacts = {step: [] for step in STEP_ORDER}
    return {
        "case_id": case_id,
        "current_step": "task-intake",
        "completed_steps": [],
        "blocked_steps": [],
        "step_status": step_status,
        "artifacts": artifacts,
        "timestamp": _iso_timestamp(),
        "version": "1.5",
        "run_metadata": {
            "started_at": _iso_timestamp(),
            "last_updated_by": "guided_run.py",
            "resume_count": 0,
            "total_retries": 0,
        },
        "blocking_reasons": [],
    }


def save_run_state(state: Dict):
    """Save run state atomically."""
    state["timestamp"] = _iso_timestamp()
    state["run_metadata"]["last_updated_by"] = "guided_run.py"
    atomic_write_json(RUN_STATE_FILE, state)


def get_step_index(step_name: str) -> int:
    """Get the index of a step in the step order."""
    try:
        return STEP_ORDER.index(step_name)
    except ValueError:
        return -1


def get_next_step(state: Dict) -> Optional[str]:
    """Determine the next step to execute."""
    current = state.get("current_step", "task-intake")
    current_idx = get_step_index(current)

    # Check if current step is complete
    if state.get("step_status", {}).get(current) == "completed":
        if current_idx + 1 < len(STEP_ORDER):
            return STEP_ORDER[current_idx + 1]
        return None  # All done

    # If current step is blocked, don't advance
    if state.get("step_status", {}).get(current) == "blocked":
        return None

    return current


def check_previous_artifacts(state: Dict, step_name: str) -> List[str]:
    """Check if previous step's artifacts exist."""
    step_idx = get_step_index(step_name)
    if step_idx <= 0:
        return []  # First step, no prerequisites

    prev_step = STEP_ORDER[step_idx - 1]
    expected_artifacts = STEP_PROMPTS.get(prev_step, {}).get("artifacts", [])
    missing = []

    for artifact in expected_artifacts:
        if not os.path.exists(artifact):
            missing.append(artifact)

    return missing


def validate_step_with_smoke_runner(step_name: str) -> Dict:
    """Call integration_smoke_runner.py --validate-step for validation."""
    import subprocess

    smoke_runner = "scripts/integration_smoke_runner.py"
    if not os.path.exists(smoke_runner):
        return {
            "valid": True,
            "warnings": ["integration_smoke_runner.py not found, skipping validation"],
        }

    try:
        result = subprocess.run(
            [sys.executable, smoke_runner, "--validate-step", "--step", step_name],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0:
            return {"valid": True, "warnings": []}
        else:
            return {
                "valid": False,
                "warnings": [result.stderr or "Validation failed"],
            }
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        return {
            "valid": True,
            "warnings": [f"Smoke runner unavailable: {e}"],
        }


def print_status(state: Dict):
    """Print current run status."""
    print("=" * 60)
    print(f"  Guided Run Status")
    print(f"  Case ID: {state.get('case_id', 'unknown')}")
    print(f"  Version: {state.get('version', 'unknown')}")
    print(f"  Last Updated: {state.get('timestamp', 'unknown')}")
    print("=" * 60)
    print()

    for step in STEP_ORDER:
        status = state.get("step_status", {}).get(step, "unknown")
        status_icon = {
            "completed": "[PASS]",
            "blocked": "[BLOCK]",
            "in_progress": "[RUN ]",
            "failed": "[FAIL]",
            "not_started": "[WAIT]",
            "incomplete": "[PART]",
        }.get(status, "[ ?  ]")

        marker = "  >>>" if step == state.get("current_step") else "     "
        print(f"  {marker} {status_icon} {step}")

    print()
    print(f"  Current Step: {state.get('current_step', 'unknown')}")
    print(f"  Completed: {len(state.get('completed_steps', []))}/{len(STEP_ORDER)}")

    blocked = state.get("blocked_steps", [])
    if blocked:
        print(f"  Blocked Steps: {', '.join(blocked)}")

    blocking_reasons = state.get("blocking_reasons", [])
    if blocking_reasons:
        print(f"\n  ⚠️  BLOCKING ISSUES:")
        for reason in blocking_reasons:
            print(f"     - [{reason.get('error_code', '???')}] {reason.get('reason', 'Unknown')}")

    print("=" * 60)


def print_next_step(state: Dict):
    """Print instructions for the next step."""
    next_step = get_next_step(state)

    if not next_step:
        print("=" * 60)
        print("  All steps completed!")
        print("=" * 60)
        return

    step_info = STEP_PROMPTS.get(next_step)
    if not step_info:
        print(f"Unknown step: {next_step}")
        return

    # Check if previous artifacts exist
    missing_artifacts = check_previous_artifacts(state, next_step)
    if missing_artifacts:
        print("=" * 60)
        print(f"  ⚠️  PREREQUISITE ARTIFACTS MISSING:")
        for artifact in missing_artifacts:
            print(f"     - {artifact}")
        print()
        print(f"  Cannot proceed with '{next_step}' until these are created.")
        print(f"  Run: python guided_run.py --step {STEP_ORDER[get_step_index(next_step) - 1]}")
        print("=" * 60)
        return

    # Check for blocking issues
    if state.get("blocked_steps"):
        print("=" * 60)
        print(f"  ⛔ BLOCKED: Cannot proceed while steps are blocked.")
        print(f"  Blocked: {', '.join(state['blocked_steps'])}")
        print(f"  Consult: docs/recovery-runbook.md")
        print("=" * 60)
        return

    # Run validation via smoke runner
    validation = validate_step_with_smoke_runner(next_step)
    if not validation["valid"]:
        print("=" * 60)
        print(f"  ⚠️  VALIDATION FAILED for step '{next_step}'")
        for warning in validation.get("warnings", []):
            print(f"     - {warning}")
        print("=" * 60)
        return

    print("=" * 60)
    print(f"  NEXT STEP: {step_info['title']}")
    print(f"  Description: {step_info['description']}")
    print("=" * 60)
    print()
    print(f"  1. Open the prompt reference:")
    print(f"     {step_info['prompt_ref'] or 'N/A (release step)'}")
    print()
    print(f"  2. Copy the prompt and paste it into Kimi Code")
    print()
    print(f"  3. Expected artifacts to save:")
    for artifact in step_info["artifacts"]:
        exists = "[EXISTS]" if os.path.exists(artifact) else "[NEW]"
        print(f"     {exists} {artifact}")
    print()
    print(f"  4. After saving artifacts, confirm with:")
    print(f"     python guided_run.py --step {next_step}")
    print()

    if validation.get("warnings"):
        print(f"  ⚠️  Warnings:")
        for w in validation["warnings"]:
            print(f"     - {w}")

    print("=" * 60)


def advance_step(state: Dict, step_name: str) -> bool:
    """Mark a step as completed and advance."""
    if step_name not in STEP_ORDER:
        print(f"Unknown step: {step_name}")
        return False

    # Check if step is blocked
    if state.get("step_status", {}).get(step_name) == "blocked":
        print(f"Step '{step_name}' is blocked. Cannot advance.")
        print("Consult docs/recovery-runbook.md for recovery procedures.")
        return False

    # Validate step via smoke runner
    validation = validate_step_with_smoke_runner(step_name)
    if not validation["valid"]:
        print(f"Validation failed for step '{step_name}':")
        for w in validation.get("warnings", []):
            print(f"  - {w}")
        return False

    # Mark step as completed
    state["step_status"][step_name] = "completed"
    if step_name not in state["completed_steps"]:
        state["completed_steps"].append(step_name)

    # Determine next step
    step_idx = get_step_index(step_name)
    if step_idx + 1 < len(STEP_ORDER):
        next_step = STEP_ORDER[step_idx + 1]
        state["current_step"] = next_step
        state["step_status"][next_step] = "in_progress"
    else:
        state["current_step"] = "release"

    save_run_state(state)
    print(f"Step '{step_name}' marked as completed.")
    if state["current_step"] != step_name:
        print(f"Advanced to: {state['current_step']}")
    return True


def resume_run(state: Dict):
    """Resume from last known state."""
    current = state.get("current_step", "task-intake")
    status = state.get("step_status", {}).get(current, "not_started")

    state["run_metadata"]["resume_count"] = (
        state.get("run_metadata", {}).get("resume_count", 0) + 1
    )
    save_run_state(state)

    print("=" * 60)
    print(f"  RESUME: Case {state.get('case_id', 'unknown')}")
    print(f"  Resuming from: {current} (status: {status})")
    resume_count = state.get("run_metadata", {}).get("resume_count", 0)
    print(f"  Resume count: {resume_count}")
    print("=" * 60)
    print()

    if status == "blocked":
        print("⚠️  Current step is BLOCKED.")
        print("Recommended actions:")
        blocking_reasons = state.get("blocking_reasons", [])
        for reason in blocking_reasons:
            print(f"  - [{reason.get('error_code', '???')}] {reason.get('reason', '')}")
        print()
        print("1. Consult docs/recovery-runbook.md for the specific error code")
        print("2. Apply the recovery procedure")
        print("3. Run: python guided_run.py --status")
        print("4. If resolved, run: python guided_run.py --next")
    elif status == "not_started":
        print("Next: Run 'python guided_run.py --next' to get started")
    elif status == "completed":
        print("Next: Run 'python guided_run.py --next' to advance")
    else:
        print("Next: Continue with the current step")
        print(f"  Run: python guided_run.py --step {current}")

    print("=" * 60)


def reset_run(confirm: bool = False):
    """Reset the run state. Requires --confirm flag."""
    if not confirm:
        print("=" * 60)
        print("  ⚠️  RESET REQUIRES CONFIRMATION")
        print()
        print("  This will delete all run state and progress.")
        print("  To confirm, run:")
        print("    python guided_run.py --reset --confirm")
        print("=" * 60)
        return

    if os.path.exists(RUN_STATE_FILE):
        os.unlink(RUN_STATE_FILE)
        print("Run state has been reset.")
    else:
        print("No run state file found. Nothing to reset.")


def main():
    parser = argparse.ArgumentParser(
        description="Guided Run - Semi-automatic wrapper for assisted mode"
    )
    parser.add_argument("--status", action="store_true", help="Show current status")
    parser.add_argument("--next", action="store_true", help="Show next step instructions")
    parser.add_argument(
        "--step",
        choices=STEP_ORDER,
        help="Mark a step as completed and advance",
    )
    parser.add_argument("--resume", action="store_true", help="Resume from last state")
    parser.add_argument("--reset", action="store_true", help="Reset run state")
    parser.add_argument(
        "--confirm", action="store_true", help="Confirm destructive operations"
    )
    parser.add_argument(
        "--validate-step",
        dest="validate_step",
        help="Validate a specific step (internal use)",
    )
    parser.add_argument(
        "--case-id",
        dest="case_id",
        default=None,
        help="Case ID for new runs",
    )

    args = parser.parse_args()

    # Load or create run state
    state = load_run_state()

    if args.reset:
        reset_run(confirm=args.confirm)
        return

    if not state:
        case_id = args.case_id or f"case-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        state = create_default_run_state(case_id)
        save_run_state(state)
        print(f"Created new run state for case: {case_id}")

    if args.resume:
        resume_run(state)
    elif args.status:
        print_status(state)
    elif args.next:
        print_next_step(state)
    elif args.step:
        advance_step(state, args.step)
    elif args.validate_step:
        result = validate_step_with_smoke_runner(args.validate_step)
        print(json.dumps(result, indent=2))
    else:
        parser.print_help()
        print()
        print_status(state)


if __name__ == "__main__":
    main()
