#!/usr/bin/env python3
"""
Context Pack Compiler - Three-Tier Context Management

Manages Hot/Warm/Cold context layers with token budget enforcement.
Core principle: PROTECTED KEYS are NEVER truncated.

Layers:
  Hot  (~16K): current conversation, active task state
  Warm (~32K): recent task history, relevant memories
  Cold (refs): full project history, archived data (stored externally)
"""

import json
import os
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE_PATH = os.path.join(PROJECT_ROOT, "runtime", "project-state.json")
ROADMAP_PATH = os.path.join(PROJECT_ROOT, "runtime", "roadmap.json")

# Token limits (approximate characters / 4)
HOT_LIMIT_TOKENS = 16000
WARM_LIMIT_TOKENS = 32000
MAX_TOTAL_TOKENS = 128000
TOKEN_PER_CHAR = 0.25  # rough estimate

# Keys that MUST NOT be truncated
PROTECTED_KEYS = [
    "autonomy_policy",
    "hitl_config",
    "security_rules",
    "pending_approvals",
    "anomaly_counter",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def estimate_tokens(text: str) -> int:
    """Rough token estimation."""
    return int(len(text) / TOKEN_PER_CHAR)


def read_file_safe(path: str, default: str = "") -> str:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except (FileNotFoundError, IOError):
        return default


def read_json_safe(path: str, default: Optional[dict] = None) -> Optional[dict]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, IOError):
        return default


# ---------------------------------------------------------------------------
# Layer Builders
# ---------------------------------------------------------------------------

def build_hot_context(state: dict) -> str:
    """Build hot context from current state."""
    parts = []
    parts.append("=== PROJECT STATE ===")
    parts.append(f"Project: {state.get('name', 'unknown')}")
    parts.append(f"Stage: {state.get('current_stage', 'unknown')}")
    parts.append(f"Version: {state.get('current_version', 'unknown')}")
    parts.append(f"Status: {state.get('status', 'unknown')}")
    parts.append(f"Autonomy Level: {state.get('autonomy_level', 'unknown')}")

    # Anomaly counter (protected)
    anomaly = state.get("anomaly_counter", {})
    parts.append(f"Anomaly (24h): degrade={anomaly.get('degrade_count_24h', 0)}, "
                 f"pause={anomaly.get('pause_count_24h', 0)}")

    # Pending approvals (protected)
    pending = state.get("pending_approvals", [])
    parts.append(f"Pending Approvals: {len(pending)}")
    for a in pending:
        parts.append(f"  - {a['approval_id']}: {a['action_name']} [{a['action_level']}] {a['status']}")

    # Context budget summary
    budget = state.get("context_budget", {})
    parts.append(f"Context Budget: max={budget.get('max_tokens', 0)}")

    return "\n".join(parts)


def build_warm_context(state: dict, roadmap: dict) -> str:
    """Build warm context from recent history."""
    parts = []
    parts.append("=== ROADMAP ===")
    current_sprint = roadmap.get("current_sprint", {})
    parts.append(f"Sprint: {current_sprint.get('name', 'unknown')} "
                 f"({current_sprint.get('id', 'unknown')})")
    parts.append(f"Status: {current_sprint.get('status', 'unknown')}")

    milestones = roadmap.get("milestones", [])
    parts.append(f"\nMilestones ({len(milestones)} total):")
    for m in milestones:
        parts.append(f"  [{m['status']}] {m['name']} -> {m['target_version']}")

    return "\n".join(parts)


def build_cold_references() -> List[str]:
    """Build cold layer references."""
    return [
        "logs/audit.log",
        "logs/task-events/",
        "archive/",
    ]


def extract_protected_content(state: dict) -> str:
    """Extract protected keys content (NEVER truncated)."""
    parts = []
    parts.append("=== PROTECTED KEYS (NON-TRUNCABLE) ===")

    # Always use the full PROTECTED_KEYS constant, not just what's in context_budget
    protected = PROTECTED_KEYS
    parts.append(f"Protected keys list: {protected}")

    anomaly = state.get("anomaly_counter", {})
    parts.append(f"\nAnomaly Counter: {json.dumps(anomaly, ensure_ascii=False)}")

    pending = state.get("pending_approvals", [])
    parts.append(f"\nPending Approvals ({len(pending)}):")
    for a in pending:
        parts.append(f"  {json.dumps(a, ensure_ascii=False)}")

    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Truncation
# ---------------------------------------------------------------------------

def truncate_text(text: str, max_tokens: int, truncation_log: List[dict], layer: str) -> str:
    """Truncate text to fit within token limit."""
    current_tokens = estimate_tokens(text)
    if current_tokens <= max_tokens:
        return text

    # Truncate from the end
    max_chars = int(max_tokens * (1 / TOKEN_PER_CHAR))
    truncated = text[:max_chars]

    truncation_log.append({
        "layer": layer,
        "reason": "token_budget_exceeded",
        "original_tokens": current_tokens,
        "max_tokens": max_tokens,
        "final_tokens": estimate_tokens(truncated),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })

    return truncated + "\n...[truncated]"


# ---------------------------------------------------------------------------
# Compiler
# ---------------------------------------------------------------------------

def compile_context_pack(
    state: Optional[dict] = None,
    roadmap: Optional[dict] = None,
    extra_hot: str = "",
    extra_warm: str = "",
) -> dict:
    """
    Compile a context pack with hot/warm/cold layers.
    
    Protected keys are always preserved and never truncated.
    Truncation order: warm first, then hot (non-protected portions).
    """
    if state is None:
        state = read_json_safe(STATE_PATH, {})
    if roadmap is None:
        roadmap = read_json_safe(ROADMAP_PATH, {})

    truncation_log: List[dict] = []

    # 1. Extract protected content (highest priority, never truncated)
    protected_content = extract_protected_content(state)
    protected_tokens = estimate_tokens(protected_content)

    # 2. Build hot context
    hot_content = build_hot_context(state)
    if extra_hot:
        hot_content += "\n\n=== EXTRA HOT ===\n" + extra_hot

    # 3. Build warm context
    warm_content = build_warm_context(state, roadmap)
    if extra_warm:
        warm_content += "\n\n=== EXTRA WARM ===\n" + extra_warm

    # 4. Budget calculation
    # Protected keys always get their full space
    remaining_for_hot = HOT_LIMIT_TOKENS - protected_tokens
    remaining_for_warm = WARM_LIMIT_TOKENS

    # Truncate hot if needed (but preserve protected)
    if remaining_for_hot < 0:
        # Edge case: protected keys exceed hot limit
        truncation_log.append({
            "layer": "hot",
            "reason": "protected_keys_exceed_hot_limit",
            "protected_tokens": protected_tokens,
            "hot_limit": HOT_LIMIT_TOKENS,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        remaining_for_hot = 0

    hot_content = truncate_text(hot_content, remaining_for_hot, truncation_log, "hot")

    # Hot layer = protected + hot content
    full_hot = protected_content + "\n\n" + hot_content
    hot_tokens = estimate_tokens(full_hot)

    # 5. Truncate warm if needed
    warm_content = truncate_text(warm_content, remaining_for_warm, truncation_log, "warm")
    warm_tokens = estimate_tokens(warm_content)

    # 6. Cold references (never loaded directly)
    cold_refs = build_cold_references()

    # 7. Total
    total_tokens = hot_tokens + warm_tokens

    # 8. Hard fail check
    if total_tokens > MAX_TOTAL_TOKENS:
        truncation_log.append({
            "layer": "total",
            "reason": "max_tokens_exceeded_hard_fail",
            "total_tokens": total_tokens,
            "max_tokens": MAX_TOTAL_TOKENS,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        # In production, this would raise an exception
        # For compilation, we truncate warm further
        excess = total_tokens - MAX_TOTAL_TOKENS + 1000  # margin
        warm_allowed = max(0, remaining_for_warm - excess)
        warm_content = truncate_text(warm_content, warm_allowed, truncation_log, "warm_emergency")
        warm_tokens = estimate_tokens(warm_content)
        total_tokens = hot_tokens + warm_tokens

    context_pack = {
        "version": 1,
        "total_tokens": total_tokens,
        "hot_context": full_hot,
        "warm_context": warm_content,
        "cold_references": cold_refs,
        "protected_keys": PROTECTED_KEYS,
        "truncation_log": truncation_log,
    }

    return context_pack


def compile_context_pack_safe(
    state: Optional[dict] = None,
    roadmap: Optional[dict] = None,
    extra_hot: str = "",
    extra_warm: str = "",
) -> dict:
    """Safe wrapper: never fail, always return a valid context pack."""
    try:
        return compile_context_pack(state, roadmap, extra_hot, extra_warm)
    except Exception as e:
        # Emergency fallback: minimal context pack
        return {
            "version": 1,
            "total_tokens": 0,
            "hot_context": f"[Context pack compilation failed: {str(e)}]",
            "warm_context": "",
            "cold_references": [],
            "protected_keys": PROTECTED_KEYS,
            "truncation_log": [{
                "layer": "emergency",
                "reason": f"compilation_error: {str(e)}",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }],
        }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Context Pack Compiler CLI")
    parser.add_argument("--extra-hot", default="", help="Extra hot context")
    parser.add_argument("--extra-warm", default="", help="Extra warm context")
    parser.add_argument("--output", help="Output JSON file path")
    args = parser.parse_args()

    pack = compile_context_pack_safe(extra_hot=args.extra_hot, extra_warm=args.extra_warm)

    output = json.dumps(pack, indent=2, ensure_ascii=False)
    if args.output:
        tmp_path = args.output + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            f.write(output)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, args.output)
        print(f"Context pack written to {args.output} ({pack['total_tokens']} tokens)")
    else:
        print(output)


if __name__ == "__main__":
    main()
