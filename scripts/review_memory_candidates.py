#!/usr/bin/env python3
"""
review_memory_candidates.py

批量审查memory candidates的脚本。
读取候选文件，按照review skill的5个维度进行评分，输出审查结果。

用法:
    python review_memory_candidates.py --candidates-dir memory/candidates [--entries-dir memory/entries] [--output-dir memory/reviews]
"""

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ── Paths ───────────────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).resolve().parent
CANDIDATE_SCHEMA_PATH = SCRIPT_DIR.parent / "schemas" / "memory-candidate.schema.json"
REVIEW_SCHEMA_PATH = SCRIPT_DIR.parent / "schemas" / "memory-review.schema.json"
ENTRY_SCHEMA_PATH = SCRIPT_DIR.parent / "schemas" / "memory-entry.schema.json"

# ── Dimension weights ───────────────────────────────────────────────
DIMENSION_WEIGHTS = {
    "source_reliability": 0.25,
    "confidence_reasonableness": 0.20,
    "risk_completeness": 0.20,
    "generalization_potential": 0.20,
    "conflict_with_existing": 0.15,
}


def load_entries(entries_dir: Path) -> list[dict[str, Any]]:
    """Load all approved memory entries for conflict detection."""
    entries = []
    if not entries_dir.exists():
        return entries
    for f in entries_dir.glob("*.json"):
        try:
            entry = json.loads(f.read_text(encoding="utf-8"))
            if entry.get("status") == "active":
                entries.append(entry)
        except (json.JSONDecodeError, OSError):
            continue
    return entries


def check_source_reliability(candidate: dict[str, Any]) -> tuple[int, str]:
    """
    Score source reliability (1-5).
    5: specific file path + verifiable
    4: file path mentioned
    3: task reference but no file
    2: vague reference
    1: no source or unverifiable
    """
    source = candidate.get("source", "")
    source_task = candidate.get("source_task", "")

    if not source:
        return 1, "Source is empty"

    # Check if source looks like a file path
    is_file_path = "/" in source or source.endswith((".md", ".txt", ".py", ".json", ".yaml"))
    is_specific = len(source) > 10

    if is_file_path and is_specific and Path(source).exists():
        return 5, f"Source is verifiable file path: {source}"
    elif is_file_path and is_specific:
        return 4, f"Source is specific file path (not verified): {source}"
    elif source_task and is_specific:
        return 3, f"Source references task but no specific file: {source}"
    elif len(source) > 0:
        return 2, f"Source is vague: {source}"
    return 1, "Source is missing"


def check_confidence_reasonableness(candidate: dict[str, Any]) -> tuple[int, str]:
    """
    Score confidence reasonableness (1-5).
    Check if confidence level matches content signals.
    """
    confidence = candidate.get("confidence", "medium")
    content = candidate.get("content", "")
    content_lower = content.lower()

    # Signals for different confidence levels
    high_signals = ["verified", "tested", "confirmed", "多次验证", "已确认", "proven"]
    low_signals = ["maybe", "possibly", "猜测", "可能", "未验证", "unclear", "待定"]

    has_high = any(s in content_lower for s in high_signals)
    has_low = any(s in content_lower for s in low_signals)

    if confidence == "high":
        if has_high and not has_low:
            return 5, "High confidence supported by strong evidence signals"
        elif has_high:
            return 4, "High confidence but some mixed signals"
        else:
            return 2, "High confidence without supporting evidence signals"
    elif confidence == "medium":
        if not has_high and not has_low:
            return 4, "Medium confidence with neutral signals"
        elif has_high:
            return 3, "Medium confidence but has high-confidence signals; consider upgrade"
        else:
            return 3, "Medium confidence with low-confidence signals"
    else:  # low
        if has_low and not has_high:
            return 5, "Low confidence appropriately reflects uncertainty"
        elif has_low:
            return 4, "Low confidence with some mixed signals"
        else:
            return 2, "Low confidence without clear uncertainty signals"


def check_risk_completeness(candidate: dict[str, Any]) -> tuple[int, str]:
    """
    Score risk assessment completeness (1-5).
    5: risk level appropriate + misuse scenario described for high/critical
    3: risk level appropriate but no misuse scenario
    1: risk level inappropriate
    """
    risk = candidate.get("risk", "medium")
    content = candidate.get("content", "")
    content_lower = content.lower()

    # Check if high/critical risk has misuse scenario
    if risk in ("high", "critical"):
        has_scenario = any(kw in content_lower for kw in [
            "if misused", "misuse", "误用", "如果", "可能导致", "注意",
            "caution", "warning", "可能导致",
        ])
        if has_scenario:
            return 5, f"{risk} risk with misuse scenario described"
        else:
            return 2, f"{risk} risk but no misuse scenario provided"

    # For low/medium, check appropriateness
    critical_keywords = ["安全漏洞", "数据丢失", "权限", "加密", "delete", "drop"]
    has_critical = any(kw in content_lower for kw in critical_keywords)

    if has_critical and risk in ("low", "medium"):
        return 1, f"Content implies critical risk but rated as {risk}"

    return 4, f"Risk level {risk} appears appropriate"


def check_generalization_potential(candidate: dict[str, Any]) -> tuple[int, str]:
    """
    Score generalization potential (1-5).
    5: highly reusable across tasks/domains
    3: reusable within domain
    1: overly specific to single scenario
    """
    content = candidate.get("content", "")
    content_lower = content.lower()
    content_type = candidate.get("content_type", "")

    # Templates and patterns are generally more reusable
    if content_type in ("template", "pattern"):
        base_score = 4
    elif content_type == "rule":
        base_score = 3
    elif content_type == "lesson":
        base_score = 3
    else:
        base_score = 3

    # Check for overly specific references
    overly_specific = [
        r"project-[a-z0-9]+",
        r"v\d+\.\d+\.\d+",
        r"202[0-9]-[0-9]{2}-[0-9]{2}",
    ]
    specificity_hits = sum(1 for pat in overly_specific if re.search(pat, content_lower))

    if specificity_hits >= 2:
        return max(1, base_score - 2), f"Content contains {specificity_hits} overly specific references"
    elif specificity_hits == 1:
        return max(2, base_score - 1), "Content has one overly specific reference"

    # Check abstraction level
    abstract_terms = ["general", "typically", "usually", "generally", "通常", "一般", "通常情况"]
    has_abstract = any(t in content_lower for t in abstract_terms)

    if has_abstract:
        return min(5, base_score + 1), "Content uses generalizable language"

    return base_score, "Content has moderate generalization potential"


def check_conflict_with_existing(
    candidate: dict[str, Any],
    entries: list[dict[str, Any]],
) -> tuple[int, str]:
    """
    Score conflict with existing entries (1-5).
    5: no conflict
    3: partial overlap but no contradiction
    1: direct contradiction
    """
    if not entries:
        return 5, "No existing entries to conflict with"

    cand_content = candidate.get("content", "").lower()
    cand_type = candidate.get("content_type", "")
    conflicts = []

    for entry in entries:
        entry_content = entry.get("content", {}).get("content", "").lower()
        entry_type = entry.get("content", {}).get("content_type", "")

        # Skip if different types (less likely to conflict)
        if entry_type and cand_type and entry_type != cand_type:
            continue

        # Check for similarity
        if not entry_content:
            continue

        # Simple keyword overlap check
        cand_words = set(cand_content.split())
        entry_words = set(entry_content.split())
        if len(cand_words) < 3 or len(entry_words) < 3:
            continue

        overlap = len(cand_words & entry_words) / max(len(cand_words), 1)

        if overlap > 0.7:
            conflicts.append((entry.get("entry_id", "?"), "high_similarity", overlap))
        elif overlap > 0.4:
            # Check for contradiction signals
            contradiction_signals = ["but", "however", "not", "instead", "错误", "但是", "不应"]
            has_contra = any(s in cand_content for s in contradiction_signals)
            if has_contra:
                conflicts.append((entry.get("entry_id", "?"), "possible_contradiction", overlap))

    if not conflicts:
        return 5, "No conflicts detected with existing entries"

    high_similarity = [c for c in conflicts if c[1] == "high_similarity"]
    contradictions = [c for c in conflicts if c[1] == "possible_contradiction"]

    if contradictions:
        return 1, f"Possible contradiction with {len(contradictions)} existing entry(s)"
    elif high_similarity:
        return 3, f"High similarity with {len(high_similarity)} existing entry(s); may be redundant"

    return 4, f"Minor overlap with {len(conflicts)} existing entry(s)"


def determine_status(scores: dict[str, int], weighted_score: float) -> str:
    """Determine review status based on scores."""
    # Auto-reject conditions
    if scores.get("source_reliability", 5) <= 1:
        return "reject"
    if scores.get("risk_completeness", 5) <= 1:
        return "reject"

    # Auto-request_changes
    if any(v <= 2 for v in scores.values()):
        return "request_changes"

    # Score-based
    if weighted_score >= 4.0:
        return "approve"
    elif weighted_score >= 3.0:
        return "approve"
    elif weighted_score >= 2.0:
        return "request_changes"
    return "reject"


def review_candidate(
    candidate: dict[str, Any],
    entries: list[dict[str, Any]],
) -> dict[str, Any]:
    """Review a single candidate and return review result."""
    scores = {
        "source_reliability": check_source_reliability(candidate),
        "confidence_reasonableness": check_confidence_reasonableness(candidate),
        "risk_completeness": check_risk_completeness(candidate),
        "generalization_potential": check_generalization_potential(candidate),
        "conflict_with_existing": check_conflict_with_existing(candidate, entries),
    }

    # Build dimensions array
    dimensions = []
    for name, (score, notes) in scores.items():
        dimensions.append({
            "name": name,
            "score": score,
            "notes": notes,
        })

    # Calculate weighted score
    weighted_score = sum(
        scores[name][0] * weight
        for name, weight in DIMENSION_WEIGHTS.items()
    )

    # Determine status
    score_values = {name: s[0] for name, s in scores.items()}
    status = determine_status(score_values, weighted_score)

    # Build conflicts_detected
    conflicts_detected = []
    conflict_notes = scores["conflict_with_existing"][1]
    if "contradiction" in conflict_notes.lower() or "similarity" in conflict_notes.lower():
        # Extract entry IDs from notes if possible
        pass  # simplified

    # Build change_requests for request_changes
    change_requests = []
    if status == "request_changes":
        for dim in dimensions:
            if dim["score"] <= 2:
                change_requests.append({
                    "field": dim["name"],
                    "issue": dim["notes"],
                    "suggestion": f"Improve {dim['name']} to meet minimum standards",
                })

    review_id = f"review-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{hashlib.sha256(json.dumps(candidate, sort_keys=True).encode()).hexdigest()[:6]}"

    return {
        "review_id": review_id,
        "candidate_id": candidate.get("candidate_id", "unknown"),
        "reviewer": "memory-reviewer",
        "status": status,
        "dimensions": dimensions,
        "weighted_score": round(weighted_score, 2),
        "conflicts_detected": conflicts_detected,
        "reviewed_at": datetime.now(timezone.utc).isoformat(),
        "change_requests": change_requests if change_requests else None,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Batch review memory candidates")
    parser.add_argument("--candidates-dir", required=True, help="Directory containing candidate JSON files")
    parser.add_argument("--entries-dir", default="memory/entries", help="Directory containing approved entries")
    parser.add_argument("--output-dir", default="memory/reviews", help="Directory to write review results")
    parser.add_argument("--dry-run", action="store_true", help="Print without writing files")
    args = parser.parse_args()

    candidates_dir = Path(args.candidates_dir)
    entries_dir = Path(args.entries_dir)
    output_dir = Path(args.output_dir)

    if not candidates_dir.exists():
        print(f"[ERROR] Candidates directory not found: {candidates_dir}", file=sys.stderr)
        return 1

    if not args.dry_run:
        output_dir.mkdir(parents=True, exist_ok=True)

    # Load existing entries for conflict detection
    entries = load_entries(entries_dir)
    print(f"[INFO] Loaded {len(entries)} existing active entries for conflict detection.")

    # Process all candidates
    candidate_files = sorted(candidates_dir.glob("memory-candidate-*.json"))
    if not candidate_files:
        print("[INFO] No candidate files found.")
        return 0

    stats = {"approve": 0, "reject": 0, "request_changes": 0}

    for cand_file in candidate_files:
        try:
            candidate = json.loads(cand_file.read_text(encoding="utf-8"))
            review = review_candidate(candidate, entries)

            status = review["status"]
            stats[status] = stats.get(status, 0) + 1

            if args.dry_run:
                print(f"[DRY-RUN] {candidate.get('candidate_id', '?')} -> {status} (score={review['weighted_score']})")
            else:
                out_path = output_dir / f"memory-review-{review['review_id']}.json"
                # Remove None values for cleaner JSON
                review_clean = {k: v for k, v in review.items() if v is not None}
                out_path.write_text(json.dumps(review_clean, ensure_ascii=False, indent=2), encoding="utf-8")
                print(f"[OK] Reviewed {candidate.get('candidate_id', '?')} -> {status} (score={review['weighted_score']})")

        except (json.JSONDecodeError, OSError) as e:
            print(f"[ERROR] Failed to process {cand_file}: {e}", file=sys.stderr)
            continue

    print(f"\n[INFO] Review complete: {stats}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
