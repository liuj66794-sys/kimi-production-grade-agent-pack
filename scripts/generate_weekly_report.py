#!/usr/bin/env python3
"""
Weekly Report Generator

Generates a weekly summary report including:
- Task completion statistics
- Artifact generation summary
- Anomalies and blockers
- Pending approvals
- Context budget usage
- Recommended next steps
"""

import json
import os
import glob
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE_PATH = os.path.join(PROJECT_ROOT, "runtime", "project-state.json")
ROADMAP_PATH = os.path.join(PROJECT_ROOT, "runtime", "roadmap.json")
REPORT_OUTPUT = os.path.join(PROJECT_ROOT, "docs", "weekly-report.md")
TASK_EVENTS_DIR = os.path.join(PROJECT_ROOT, "logs", "task-events")

TOKEN_PER_CHAR = 0.25


# ---------------------------------------------------------------------------
# Data Collection
# ---------------------------------------------------------------------------

def read_json_safe(path: str, default: Optional[dict] = None) -> Optional[dict]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, IOError):
        return default


def get_past_7_days_events() -> List[dict]:
    """Read task events from the past 7 days."""
    events = []
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=7)

    # Try to read from task-events directory
    if os.path.isdir(TASK_EVENTS_DIR):
        for filepath in sorted(glob.glob(os.path.join(TASK_EVENTS_DIR, "*.json"))):
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        for ev in data:
                            ev_time = parse_event_time(ev)
                            if ev_time and ev_time >= cutoff:
                                events.append(ev)
                    elif isinstance(data, dict):
                        ev_time = parse_event_time(data)
                        if ev_time and ev_time >= cutoff:
                            events.append(data)
            except (json.JSONDecodeError, IOError):
                continue

    return events


def parse_event_time(event: dict) -> Optional[datetime]:
    """Parse timestamp from an event dict."""
    ts = event.get("timestamp") or event.get("created_at") or event.get("time")
    if ts:
        try:
            return datetime.fromisoformat(ts.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            pass
    return None


def count_task_stats(events: List[dict]) -> dict:
    """Count task completion statistics from events."""
    completed = 0
    failed = 0
    blocked = 0
    in_progress = 0

    for ev in events:
        status = ev.get("status", "")
        if status == "completed":
            completed += 1
        elif status in ("failed", "error"):
            failed += 1
        elif status == "blocked":
            blocked += 1
        elif status in ("in_progress", "started"):
            in_progress += 1

    return {
        "completed": completed,
        "failed": failed,
        "blocked": blocked,
        "in_progress": in_progress,
        "total": len(events),
    }


def count_artifacts(events: List[dict]) -> List[dict]:
    """Extract generated artifacts from events."""
    artifacts = []
    for ev in events:
        if "artifact" in ev:
            artifacts.append(ev["artifact"])
        elif ev.get("type") == "artifact_created":
            artifacts.append({
                "name": ev.get("artifact_name", "unknown"),
                "type": ev.get("artifact_type", "unknown"),
                "path": ev.get("path", ""),
            })
    return artifacts


def detect_anomalies(events: List[dict], state: dict) -> List[dict]:
    """Detect anomaly patterns in events."""
    anomalies = []

    counter = state.get("anomaly_counter", {})
    if counter.get("degrade_count_24h", 0) > 0:
        anomalies.append({
            "type": "degrade",
            "description": f"{counter['degrade_count_24h']} degrade events in 24h",
            "severity": "high" if counter["degrade_count_24h"] >= 3 else "medium",
        })

    if counter.get("pause_count_24h", 0) > 0:
        anomalies.append({
            "type": "pause",
            "description": f"{counter['pause_count_24h']} pause events in 24h",
            "severity": "critical" if counter["pause_count_24h"] >= 5 else "high",
        })

    # Detect repeated failures
    failed_events = [e for e in events if e.get("status") in ("failed", "error")]
    if len(failed_events) >= 3:
        anomalies.append({
            "type": "repeated_failures",
            "description": f"{len(failed_events)} failures in the past 7 days",
            "severity": "medium",
        })

    return anomalies


def get_context_budget_usage(state: dict) -> dict:
    """Calculate context budget usage."""
    budget = state.get("context_budget", {})
    max_tokens = budget.get("max_tokens", 128000)
    hot_limit = budget.get("hot_context_limit", 16000)
    warm_limit = budget.get("warm_context_limit", 32000)

    # Estimate current usage (simplified)
    hot_usage = int(hot_limit * 0.75)  # placeholder
    warm_usage = int(warm_limit * 0.60)  # placeholder

    return {
        "hot": {"used": hot_usage, "limit": hot_limit, "pct": round(hot_usage / hot_limit * 100, 1)},
        "warm": {"used": warm_usage, "limit": warm_limit, "pct": round(warm_usage / warm_limit * 100, 1)},
        "total": {"used": hot_usage + warm_usage, "limit": max_tokens, "pct": round((hot_usage + warm_usage) / max_tokens * 100, 1)},
    }


# ---------------------------------------------------------------------------
# Report Generation
# ---------------------------------------------------------------------------

def generate_report() -> dict:
    """Generate the full weekly report data."""
    state = read_json_safe(STATE_PATH, {})
    roadmap = read_json_safe(ROADMAP_PATH, {})
    events = get_past_7_days_events()

    now = datetime.now(timezone.utc)
    week_ago = now - timedelta(days=7)

    task_stats = count_task_stats(events)
    artifacts = count_artifacts(events)
    anomalies = detect_anomalies(events, state)
    pending = state.get("pending_approvals", [])
    budget_usage = get_context_budget_usage(state)

    report = {
        "version": 1,
        "report_period_start": week_ago.isoformat(),
        "report_period_end": now.isoformat(),
        "generated_at": now.isoformat(),
        "project": {
            "name": state.get("name", "unknown"),
            "version": state.get("current_version", "unknown"),
            "status": state.get("status", "unknown"),
            "autonomy_level": state.get("autonomy_level", "unknown"),
        },
        "sprint": roadmap.get("current_sprint", {}),
        "task_stats": task_stats,
        "artifacts": artifacts,
        "anomalies": anomalies,
        "pending_approvals": pending,
        "context_budget": budget_usage,
        "recommendations": generate_recommendations(state, task_stats, anomalies, pending),
    }

    return report


def generate_recommendations(state: dict, stats: dict, anomalies: list, pending: list) -> List[str]:
    """Generate recommended next steps based on current state."""
    recs = []

    if stats["failed"] > 0:
        recs.append(f"Review {stats['failed']} failed tasks from the past week")

    if stats["blocked"] > 0:
        recs.append(f"Unblock {stats['blocked']} blocked tasks")

    if len(pending) > 0:
        recs.append(f"Process {len(pending)} pending approval(s)")

    counter = state.get("anomaly_counter", {})
    if counter.get("degrade_count_24h", 0) >= 3:
        recs.append("URGENT: Anomaly degrade threshold reached. Review system behavior.")
    if counter.get("pause_count_24h", 0) >= 5:
        recs.append("CRITICAL: L4 is paused. Immediate human intervention required.")

    if not recs:
        recs.append("No immediate action required. Continue current sprint.")

    return recs


def render_markdown(report: dict) -> str:
    """Render the report as Markdown."""
    lines = []
    lines.append("# Weekly Report")
    lines.append(f"**Period:** {report['report_period_start'][:10]} ~ {report['report_period_end'][:10]}")
    lines.append(f"**Generated:** {report['generated_at']}")
    lines.append("")

    # Overview
    lines.append("## Overview")
    proj = report["project"]
    lines.append(f"- **Project:** {proj['name']}")
    lines.append(f"- **Version:** {proj['version']}")
    lines.append(f"- **Status:** {proj['status']}")
    lines.append(f"- **Autonomy Level:** {proj['autonomy_level']}")
    sprint = report.get("sprint", {})
    lines.append(f"- **Sprint:** {sprint.get('name', 'N/A')} ({sprint.get('id', 'N/A')}) - {sprint.get('status', 'N/A')}")
    lines.append("")

    # Task Stats
    lines.append("## Task Statistics")
    stats = report["task_stats"]
    lines.append(f"- Total: {stats['total']}")
    lines.append(f"- Completed: {stats['completed']}")
    lines.append(f"- Failed: {stats['failed']}")
    lines.append(f"- Blocked: {stats['blocked']}")
    lines.append(f"- In Progress: {stats['in_progress']}")
    lines.append("")

    # Artifacts
    lines.append("## Generated Artifacts")
    if report["artifacts"]:
        for a in report["artifacts"]:
            lines.append(f"- {a.get('name', 'unknown')} ({a.get('type', 'unknown')})")
    else:
        lines.append("_No artifacts generated this week._")
    lines.append("")

    # Anomalies
    lines.append("## Anomalies & Blockers")
    if report["anomalies"]:
        for anom in report["anomalies"]:
            lines.append(f"- **[{anom['severity'].upper()}]** {anom['type']}: {anom['description']}")
    else:
        lines.append("_No anomalies detected._")
    lines.append("")

    # Pending Approvals
    lines.append("## Pending Approvals")
    if report["pending_approvals"]:
        for a in report["pending_approvals"]:
            lines.append(f"- `{a['approval_id']}`: {a['action_name']} [{a['action_level']}] - {a['status']}")
    else:
        lines.append("_No pending approvals._")
    lines.append("")

    # Context Budget
    lines.append("## Context Budget Usage")
    budget = report["context_budget"]
    h = budget["hot"]
    w = budget["warm"]
    t = budget["total"]
    lines.append(f"| Layer | Used | Limit | % |")
    lines.append(f"|-------|------|-------|---|")
    lines.append(f"| Hot   | {h['used']:,} | {h['limit']:,} | {h['pct']}% |")
    lines.append(f"| Warm  | {w['used']:,} | {w['limit']:,} | {w['pct']}% |")
    lines.append(f"| Total | {t['used']:,} | {t['limit']:,} | {t['pct']}% |")
    lines.append("")

    # Recommendations
    lines.append("## Recommended Next Steps")
    for i, rec in enumerate(report["recommendations"], 1):
        lines.append(f"{i}. {rec}")
    lines.append("")

    return "\n".join(lines)


def write_report(report: dict, md_path: str) -> str:
    """Write both JSON and Markdown reports."""
    md = render_markdown(report)

    tmp_path = md_path + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        f.write(md)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp_path, md_path)

    return md


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Weekly Report Generator CLI")
    parser.add_argument("--output", default=REPORT_OUTPUT, help="Output markdown path")
    parser.add_argument("--json-output", help="Output JSON path")
    args = parser.parse_args()

    report = generate_report()
    md = write_report(report, args.output)

    if args.json_output:
        tmp = args.json_output + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, args.json_output)

    print(md)
    print(f"\nReport written to: {args.output}")


if __name__ == "__main__":
    main()
