#!/usr/bin/env python3
"""
Autonomy Gate - L4 Semi-Autonomous System Rule Engine

Core security gate that evaluates every agent action request.
Principle: DEFAULT DENY - any action not explicitly allowed is blocked.

Security constraints:
- A2 actions must be in explicit allowlist
- A5 actions cannot be auto-approved by timeout
- Anomaly counter can degrade or pause L4
- State modifications must use atomic write + version conflict check
"""

import json
import os
import re
import fnmatch
from datetime import datetime, timezone
from typing import Dict, List, Optional, Set

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE_PATH = os.path.join(PROJECT_ROOT, "runtime", "project-state.json")
AUDIT_LOG_PATH = os.path.join(PROJECT_ROOT, "logs", "audit.log")

A2_ALLOWLIST: Set[str] = {
    "read_project_state",
    "read_roadmap",
    "read_task_events",
    "read_artifact_index",
    "read_skill_definitions",
    "generate_summary",
    "generate_weekly_report_draft",
    "run_eval_dry_run",
    "check_artifact_quality",
}

A2_FORBIDDEN_PATTERNS: List[str] = [
    "write_*_without_approval",
    "modify_autonomy_*",
    "delete_audit_*",
    "bypass_gate",
    "approve_memory",
    "execute_shell",
    "publish_release",
]

LEVEL_HIERARCHY = {
    "a0": 0,
    "a1": 1,
    "a2": 2,
    "a3": 3,
    "a4": 4,
    "a5": 5,
}

# Degrade threshold: 3 anomalies in 24h blocks A3+
DEGRADE_THRESHOLD = 3
# Pause threshold: 5 anomalies in 24h pauses L4 entirely
PAUSE_THRESHOLD = 5


# ---------------------------------------------------------------------------
# State Access
# ---------------------------------------------------------------------------

def read_project_state() -> dict:
    """Read current project state (A1 action)."""
    if not os.path.exists(STATE_PATH):
        raise FileNotFoundError(f"Project state not found: {STATE_PATH}")
    with open(STATE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def get_autonomy_level() -> str:
    """Get current autonomy level from project state."""
    state = read_project_state()
    return state.get("autonomy_level", "a1")


def get_anomaly_counter() -> dict:
    """Get current anomaly counter from project state."""
    state = read_project_state()
    return state.get("anomaly_counter", {
        "degrade_count_24h": 0,
        "pause_count_24h": 0,
        "last_reset": datetime.now(timezone.utc).isoformat()
    })


def get_pending_approvals() -> list:
    """Get list of pending approvals."""
    state = read_project_state()
    return state.get("pending_approvals", [])


# ---------------------------------------------------------------------------
# Audit Logging
# ---------------------------------------------------------------------------

def log_audit(decision: dict) -> None:
    """Append a decision record to the audit log (atomic)."""
    os.makedirs(os.path.dirname(AUDIT_LOG_PATH), exist_ok=True)
    entry = {
        **decision,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    line = json.dumps(entry, ensure_ascii=False)
    tmp_path = AUDIT_LOG_PATH + ".tmp"
    try:
        with open(tmp_path, "a", encoding="utf-8") as f:
            f.write(line + "\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, AUDIT_LOG_PATH)
    except Exception:
        # Best-effort audit logging; don't let audit failures block actions
        pass


# ---------------------------------------------------------------------------
# Evaluation Core
# ---------------------------------------------------------------------------

def matches_forbidden_pattern(action_name: str) -> bool:
    """Check if action name matches any forbidden pattern."""
    for pattern in A2_FORBIDDEN_PATTERNS:
        if fnmatch.fnmatch(action_name, pattern):
            return True
    return False


def level_allows_action(current_level: str, action_level: str) -> bool:
    """Check if current autonomy level permits the requested action level."""
    cur = LEVEL_HIERARCHY.get(current_level, 0)
    req = LEVEL_HIERARCHY.get(action_level, -1)
    return cur >= req


def check_anomaly_limits(anomaly: dict, action_level: str) -> Optional[str]:
    """
    Check anomaly counter thresholds.
    Returns reason string if blocked, None if allowed.
    """
    if anomaly.get("pause_count_24h", 0) >= PAUSE_THRESHOLD:
        return (
            f"Anomaly counter exceeded pause threshold "
            f"({anomaly['pause_count_24h']} >= {PAUSE_THRESHOLD})"
        )
    if (
        anomaly.get("degrade_count_24h", 0) >= DEGRADE_THRESHOLD
        and action_level in ("a3", "a4", "a5")
    ):
        return (
            f"Anomaly counter exceeded degrade threshold "
            f"({anomaly['degrade_count_24h']} >= {DEGRADE_THRESHOLD}), "
            f"A3+ actions blocked"
        )
    return None


def evaluate_action(
    action_name: str,
    action_level: str,
    actor: str = "agent"
) -> dict:
    """
    Evaluate an action request against all security policies.

    Returns a decision dict with keys:
        decision: "allow" | "block" | "require_approval"
        action_name, action_level, actor, reason, approval_type, timestamp
    """
    result = {
        "action_name": action_name,
        "action_level": action_level,
        "actor": actor,
        "reason": "",
        "approval_type": None,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    # 1. Validate action_level
    if action_level not in LEVEL_HIERARCHY:
        result["decision"] = "block"
        result["reason"] = f"Unknown action level: {action_level}"
        log_audit(result)
        return result

    # 2. Check forbidden patterns (HIGHEST PRIORITY)
    if matches_forbidden_pattern(action_name):
        result["decision"] = "block"
        result["reason"] = f"Action '{action_name}' matches forbidden pattern"
        log_audit(result)
        return result

    # 3. Check A2 allowlist for A2 actions
    if action_level == "a2" and action_name not in A2_ALLOWLIST:
        result["decision"] = "block"
        result["reason"] = (
            f"A2 action '{action_name}' not in allowlist; "
            f"allowed actions: {sorted(A2_ALLOWLIST)}"
        )
        log_audit(result)
        return result

    # 4. Check autonomy level permission
    current_level = get_autonomy_level()
    if not level_allows_action(current_level, action_level):
        result["decision"] = "block"
        result["reason"] = (
            f"Autonomy level '{current_level}' does not allow '{action_level}'"
        )
        log_audit(result)
        return result

    # 5. Check anomaly counter
    anomaly = get_anomaly_counter()
    anomaly_reason = check_anomaly_limits(anomaly, action_level)
    if anomaly_reason:
        result["decision"] = "block"
        result["reason"] = anomaly_reason
        log_audit(result)
        return result

    # 6. Route decision based on level
    if action_level in ("a0", "a1"):
        result["decision"] = "allow"
        result["reason"] = "Read-only action permitted"
    elif action_level == "a2":
        result["decision"] = "allow"
        result["reason"] = "A2 action in allowlist"
    elif action_level in ("a3", "a4"):
        result["decision"] = "require_approval"
        result["approval_type"] = "hitl"
        result["reason"] = f"{action_level.upper()} action requires HITL approval"
    elif action_level == "a5":
        result["decision"] = "require_approval"
        result["approval_type"] = "explicit_human"
        result["reason"] = "A5 action requires explicit human approval"
    else:
        # Should never reach here due to level validation above
        result["decision"] = "block"
        result["reason"] = f"Unhandled action level: {action_level}"

    log_audit(result)
    return result


def evaluate_action_strict(
    action_name: str,
    action_level: str,
    actor: str = "agent"
) -> dict:
    """
    Strict evaluation variant that treats any system error as block.
    Use this for safety-critical paths.
    """
    try:
        return evaluate_action(action_name, action_level, actor)
    except Exception as e:
        return {
            "decision": "block",
            "action_name": action_name,
            "action_level": action_level,
            "actor": actor,
            "reason": f"Evaluation error (safe default): {str(e)}",
            "approval_type": None,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def is_action_allowed(action_name: str, action_level: str, actor: str = "agent") -> bool:
    """Convenience: return True only if decision is 'allow'."""
    result = evaluate_action(action_name, action_level, actor)
    return result["decision"] == "allow"


def require_approval(action_name: str, action_level: str, actor: str = "agent") -> bool:
    """Convenience: return True if decision requires approval."""
    result = evaluate_action(action_name, action_level, actor)
    return result["decision"] == "require_approval"


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Autonomy Gate CLI")
    parser.add_argument("action_name", help="Name of the action to evaluate")
    parser.add_argument("--level", default="a2", choices=list(LEVEL_HIERARCHY.keys()))
    parser.add_argument("--actor", default="agent")
    args = parser.parse_args()

    decision = evaluate_action(args.action_name, args.level, args.actor)
    print(json.dumps(decision, indent=2, ensure_ascii=False))
    return 0 if decision["decision"] == "allow" else 1


if __name__ == "__main__":
    sys.exit(main())
