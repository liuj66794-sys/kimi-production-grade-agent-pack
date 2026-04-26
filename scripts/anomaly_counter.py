#!/usr/bin/env python3
"""
Anomaly Counter - 24h Sliding Window Anomaly Tracking

Tracks degrade/pause events in a 24-hour sliding window.
- degrade_count_24h >= 3: Blocks A3+ actions
- pause_count_24h >= 5: Fully pauses L4

All events are persisted to project-state.json with atomic writes.
"""

import json
import os
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE_PATH = os.path.join(PROJECT_ROOT, "runtime", "project-state.json")
AUDIT_LOG_PATH = os.path.join(PROJECT_ROOT, "logs", "audit.log")

DEGRADE_THRESHOLD = 3
PAUSE_THRESHOLD = 5
WINDOW_HOURS = 24


# ---------------------------------------------------------------------------
# State Access
# ---------------------------------------------------------------------------

def read_project_state() -> dict:
    with open(STATE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def atomic_write_state(new_state: dict, expected_version: int) -> bool:
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
    pass


# ---------------------------------------------------------------------------
# Audit
# ---------------------------------------------------------------------------

def log_audit(entry: dict) -> None:
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
# Anomaly Counter Core
# ---------------------------------------------------------------------------

def reset_window(state: Optional[dict] = None) -> dict:
    """
    Reset the 24h anomaly counter window.
    Returns the updated anomaly counter.
    """
    if state is None:
        state = read_project_state()

    counter = state.get("anomaly_counter", {})
    counter["degrade_count_24h"] = 0
    counter["pause_count_24h"] = 0
    counter["last_reset"] = datetime.now(timezone.utc).isoformat()
    state["anomaly_counter"] = counter

    atomic_write_state(state, state["version"])

    log_audit({
        "event": "anomaly_window_reset",
        "timestamp": counter["last_reset"],
    })

    return counter


def check_reset_needed(state: Optional[dict] = None) -> bool:
    """Check if the 24h window has expired and needs reset."""
    if state is None:
        state = read_project_state()

    counter = state.get("anomaly_counter", {})
    last_reset_str = counter.get("last_reset")
    if not last_reset_str:
        return True

    last_reset = datetime.fromisoformat(last_reset_str)
    now = datetime.now(timezone.utc)
    return (now - last_reset) >= timedelta(hours=WINDOW_HOURS)


def auto_reset_if_needed() -> Optional[dict]:
    """Automatically reset the window if 24h has passed."""
    if check_reset_needed():
        return reset_window()
    return None


def record_degrade(reason: str = "", actor: str = "system") -> dict:
    """
    Record a degrade event.
    Returns the current anomaly counter after recording.
    """
    auto_reset_if_needed()

    state = read_project_state()
    counter = state.get("anomaly_counter", {})
    counter["degrade_count_24h"] = counter.get("degrade_count_24h", 0) + 1
    state["anomaly_counter"] = counter

    atomic_write_state(state, state["version"])

    log_audit({
        "event": "degrade_recorded",
        "reason": reason,
        "actor": actor,
        "degrade_count_24h": counter["degrade_count_24h"],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })

    return counter


def record_pause(reason: str = "", actor: str = "system") -> dict:
    """
    Record a pause event.
    Returns the current anomaly counter after recording.
    """
    auto_reset_if_needed()

    state = read_project_state()
    counter = state.get("anomaly_counter", {})
    counter["pause_count_24h"] = counter.get("pause_count_24h", 0) + 1
    state["anomaly_counter"] = counter

    atomic_write_state(state, state["version"])

    log_audit({
        "event": "pause_recorded",
        "reason": reason,
        "actor": actor,
        "pause_count_24h": counter["pause_count_24h"],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })

    return counter


def record_anomaly(event_type: str, reason: str = "", actor: str = "system") -> dict:
    """
    Record an anomaly event of the given type.
    event_type: "degrade" or "pause"
    """
    if event_type == "degrade":
        return record_degrade(reason, actor)
    elif event_type == "pause":
        return record_pause(reason, actor)
    else:
        raise ValueError(f"Unknown event_type: {event_type}")


# ---------------------------------------------------------------------------
# Status Queries
# ---------------------------------------------------------------------------

def get_counter() -> dict:
    """Get current anomaly counter values."""
    state = read_project_state()
    return state.get("anomaly_counter", {
        "degrade_count_24h": 0,
        "pause_count_24h": 0,
        "last_reset": datetime.now(timezone.utc).isoformat(),
    })


def is_l4_paused() -> bool:
    """Check if L4 is fully paused."""
    counter = get_counter()
    return counter.get("pause_count_24h", 0) >= PAUSE_THRESHOLD


def is_a3_blocked() -> bool:
    """Check if A3+ actions are blocked due to degrade threshold."""
    counter = get_counter()
    return counter.get("degrade_count_24h", 0) >= DEGRADE_THRESHOLD


def get_status() -> dict:
    """Get full anomaly counter status with derived flags."""
    counter = get_counter()
    paused = counter.get("pause_count_24h", 0) >= PAUSE_THRESHOLD
    degraded = counter.get("degrade_count_24h", 0) >= DEGRADE_THRESHOLD

    return {
        "counter": counter,
        "l4_paused": paused,
        "a3_blocked": degraded,
        "effective_level": "a0" if paused else ("a2" if degraded else None),
        "thresholds": {
            "degrade": DEGRADE_THRESHOLD,
            "pause": PAUSE_THRESHOLD,
        },
        "window_hours": WINDOW_HOURS,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Anomaly Counter CLI")
    sub = parser.add_subparsers(dest="cmd")

    p_degrade = sub.add_parser("degrade", help="Record a degrade event")
    p_degrade.add_argument("--reason", default="")
    p_degrade.add_argument("--actor", default="system")

    p_pause = sub.add_parser("pause", help="Record a pause event")
    p_pause.add_argument("--reason", default="")
    p_pause.add_argument("--actor", default="system")

    sub.add_parser("status", help="Show current status")
    sub.add_parser("reset", help="Reset the 24h window")

    args = parser.parse_args()

    if args.cmd == "degrade":
        counter = record_degrade(args.reason, args.actor)
        print(f"Degrade recorded. Count: {counter['degrade_count_24h']}")
    elif args.cmd == "pause":
        counter = record_pause(args.reason, args.actor)
        print(f"Pause recorded. Count: {counter['pause_count_24h']}")
    elif args.cmd == "status":
        status = get_status()
        print(json.dumps(status, indent=2, ensure_ascii=False))
    elif args.cmd == "reset":
        counter = reset_window()
        print(f"Window reset. {json.dumps(counter, indent=2)}")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
