#!/usr/bin/env python3
"""
Human-in-the-Loop (HITL) Approval System

Manages pending approvals for A3+ actions.
Principles:
- A3+ actions MUST go through HITL approval
- A5 actions are NEVER auto-accepted by timeout
- Default on timeout is REJECT (not accept)
- All responses are written to audit log
"""

import json
import os
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE_PATH = os.path.join(PROJECT_ROOT, "runtime", "project-state.json")
AUDIT_LOG_PATH = os.path.join(PROJECT_ROOT, "logs", "audit.log")

# A5 actions can NEVER be auto-accepted
A5_AUTO_ACCEPT_ELIGIBLE = False
# Default timeout in minutes
DEFAULT_TIMEOUT_MINUTES = 60


# ---------------------------------------------------------------------------
# State Access
# ---------------------------------------------------------------------------

def read_project_state() -> dict:
    """Read current project state."""
    with open(STATE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def atomic_write_state(new_state: dict, expected_version: int) -> bool:
    """
    Atomic write with version conflict check.
    
    1. Read current state, verify version == expected_version
    2. Write to temp file
    3. fsync
    4. rename (atomic)
    5. Increment version
    """
    with open(STATE_PATH, "r", encoding="utf-8") as f:
        current = json.load(f)

    if current.get("version", 0) != expected_version:
        raise VersionConflictError(
            f"Version conflict: expected {expected_version}, "
            f"found {current.get('version')}"
        )

    new_state["version"] = expected_version + 1
    new_state["last_updated"] = datetime.now(timezone.utc).isoformat()

    tmp_path = STATE_PATH + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(new_state, f, indent=2, ensure_ascii=False)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp_path, STATE_PATH)
    return True


class VersionConflictError(Exception):
    """Raised when state version does not match expected."""


# ---------------------------------------------------------------------------
# Audit Logging
# ---------------------------------------------------------------------------

def log_audit(entry: dict) -> None:
    """Append to audit log."""
    os.makedirs(os.path.dirname(AUDIT_LOG_PATH), exist_ok=True)
    line = json.dumps(entry, ensure_ascii=False)
    tmp_path = AUDIT_LOG_PATH + ".tmp"
    try:
        with open(tmp_path, "a", encoding="utf-8") as f:
            f.write(line + "\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, AUDIT_LOG_PATH)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Approval Core
# ---------------------------------------------------------------------------

def is_auto_accept_eligible(action_level: str) -> bool:
    """
    Determine if an action level is eligible for auto-accept on timeout.
    ONLY A1/A2 read-only actions are eligible.
    A3+ are NEVER eligible.
    A5 is explicitly blocked.
    """
    if action_level == "a5":
        return False
    if action_level in ("a1", "a2"):
        return True
    return False


def create_approval(
    action_name: str,
    action_level: str,
    actor: str,
    request_details: str,
    risk_assessment: str,
    timeout_minutes: int = DEFAULT_TIMEOUT_MINUTES,
) -> dict:
    """
    Create a new pending approval and persist it to project state.
    
    Returns the created approval object.
    """
    approval_id = f"apr-{uuid.uuid4().hex[:8]}"
    now = datetime.now(timezone.utc)
    timeout_at = now + timedelta(minutes=timeout_minutes)

    approval = {
        "approval_id": approval_id,
        "action_name": action_name,
        "action_level": action_level,
        "actor": actor,
        "request_details": request_details,
        "risk_assessment": risk_assessment,
        "status": "pending",
        "requested_at": now.isoformat(),
        "responded_at": None,
        "responded_by": None,
        "auto_accept_eligible": is_auto_accept_eligible(action_level),
        "timeout_at": timeout_at.isoformat(),
    }

    # Persist to project state
    state = read_project_state()
    pending = state.get("pending_approvals", [])
    pending.append(approval)
    state["pending_approvals"] = pending

    atomic_write_state(state, state["version"])

    # Log
    log_audit({
        "event": "approval_created",
        "approval_id": approval_id,
        "action_name": action_name,
        "action_level": action_level,
        "actor": actor,
        "auto_accept_eligible": approval["auto_accept_eligible"],
        "timestamp": now.isoformat(),
    })

    return approval


def respond_approval(
    approval_id: str,
    decision: str,  # "approved", "rejected", "deferred"
    responder: str,
) -> dict:
    """
    Respond to a pending approval.
    
    Args:
        approval_id: The approval to respond to
        decision: approved, rejected, or deferred
        responder: Human identifier
    
    Returns:
        Updated approval object
    """
    if decision not in ("approved", "rejected", "deferred"):
        raise ValueError(f"Invalid decision: {decision}")

    state = read_project_state()
    pending = state.get("pending_approvals", [])

    approval = None
    for a in pending:
        if a["approval_id"] == approval_id:
            approval = a
            break

    if approval is None:
        raise ValueError(f"Approval not found: {approval_id}")

    if approval["status"] != "pending":
        raise ValueError(f"Approval already {approval['status']}: {approval_id}")

    now = datetime.now(timezone.utc)
    approval["status"] = decision
    approval["responded_at"] = now.isoformat()
    approval["responded_by"] = responder

    # If deferred, reset status to pending but update timeout
    if decision == "deferred":
        approval["status"] = "pending"
        new_timeout = now + timedelta(minutes=DEFAULT_TIMEOUT_MINUTES)
        approval["timeout_at"] = new_timeout.isoformat()

    atomic_write_state(state, state["version"])

    log_audit({
        "event": "approval_responded",
        "approval_id": approval_id,
        "decision": decision,
        "responder": responder,
        "timestamp": now.isoformat(),
    })

    return approval


def check_expired_approvals() -> List[dict]:
    """
    Check for timed-out approvals and mark them.
    A3/A4 timeout -> status "timeout" (treated as rejected)
    A1/A2 timeout -> status "approved" (auto-accept eligible only)
    A5 NEVER auto-accepted.
    """
    state = read_project_state()
    pending = state.get("pending_approvals", [])
    now = datetime.now(timezone.utc)
    expired = []

    for approval in pending:
        if approval["status"] != "pending":
            continue

        timeout_at_str = approval.get("timeout_at")
        if not timeout_at_str:
            continue

        timeout_at = datetime.fromisoformat(timeout_at_str)
        if now >= timeout_at:
            if approval.get("auto_accept_eligible") and approval["action_level"] in ("a1", "a2"):
                approval["status"] = "approved"
                approval["responded_at"] = now.isoformat()
                approval["responded_by"] = "system_timeout_autoaccept"
            else:
                approval["status"] = "timeout"
                approval["responded_at"] = now.isoformat()
                approval["responded_by"] = "system_timeout_reject"

            expired.append(approval)

            log_audit({
                "event": "approval_timeout",
                "approval_id": approval["approval_id"],
                "action_level": approval["action_level"],
                "auto_accept_eligible": approval.get("auto_accept_eligible"),
                "final_status": approval["status"],
                "timestamp": now.isoformat(),
            })

    if expired:
        atomic_write_state(state, state["version"])

    return expired


def list_pending_approvals() -> List[dict]:
    """List all approvals with status 'pending'."""
    state = read_project_state()
    return [a for a in state.get("pending_approvals", []) if a["status"] == "pending"]


def get_approval(approval_id: str) -> Optional[dict]:
    """Get a specific approval by ID."""
    state = read_project_state()
    for a in state.get("pending_approvals", []):
        if a["approval_id"] == approval_id:
            return a
    return None


def display_approval_request(approval: dict) -> str:
    """Format an approval request for human display."""
    lines = [
        "=" * 60,
        "  HITL APPROVAL REQUEST",
        "=" * 60,
        f"  Approval ID : {approval['approval_id']}",
        f"  Action      : {approval['action_name']}",
        f"  Level       : {approval['action_level']}",
        f"  Actor       : {approval['actor']}",
        f"  Details     : {approval['request_details']}",
        f"  Risk        : {approval['risk_assessment']}",
        f"  Auto-Accept : {approval['auto_accept_eligible']}",
        f"  Timeout At  : {approval['timeout_at']}",
        "-" * 60,
        "  Respond with: approve(apr-id) / reject(apr-id) / defer(apr-id)",
        "=" * 60,
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Convenience API
# ---------------------------------------------------------------------------

def request_approval_for_action(
    action_name: str,
    action_level: str,
    actor: str = "agent",
    details: str = "",
    risk: str = "",
) -> dict:
    """
    Full workflow: create an approval request for an action that passed
    Autonomy Gate with 'require_approval' decision.
    """
    return create_approval(
        action_name=action_name,
        action_level=action_level,
        actor=actor,
        request_details=details or f"Execute action: {action_name}",
        risk_assessment=risk or f"Action level: {action_level}",
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    import argparse
    parser = argparse.ArgumentParser(description="HITL Approval System CLI")
    sub = parser.add_subparsers(dest="cmd")

    # create
    p_create = sub.add_parser("create", help="Create a pending approval")
    p_create.add_argument("action_name")
    p_create.add_argument("--level", required=True, choices=["a3", "a4", "a5"])
    p_create.add_argument("--actor", default="agent")
    p_create.add_argument("--details", default="")
    p_create.add_argument("--risk", default="")
    p_create.add_argument("--timeout", type=int, default=60)

    # respond
    p_resp = sub.add_parser("respond", help="Respond to a pending approval")
    p_resp.add_argument("approval_id")
    p_resp.add_argument("decision", choices=["approved", "rejected", "deferred"])
    p_resp.add_argument("--responder", required=True)

    # list
    sub.add_parser("list", help="List pending approvals")

    # check
    sub.add_parser("check", help="Check expired approvals")

    args = parser.parse_args()

    if args.cmd == "create":
        apr = create_approval(
            args.action_name, args.level, args.actor,
            args.details, args.risk, args.timeout
        )
        print(display_approval_request(apr))
    elif args.cmd == "respond":
        apr = respond_approval(args.approval_id, args.decision, args.responder)
        print(json.dumps(apr, indent=2, ensure_ascii=False))
    elif args.cmd == "list":
        for a in list_pending_approvals():
            print(f"{a['approval_id']}: {a['action_name']} [{a['action_level']}] - {a['status']}")
    elif args.cmd == "check":
        expired = check_expired_approvals()
        print(f"Expired approvals processed: {len(expired)}")
        for a in expired:
            print(f"  {a['approval_id']} -> {a['status']}")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
