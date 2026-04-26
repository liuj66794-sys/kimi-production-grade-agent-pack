#!/usr/bin/env python3
"""
check_memory_conflicts.py

检查记忆条目之间冲突的脚本。
检测contradiction（矛盾）、redundancy（冗余）、complementary（互补）三类冲突。

用法:
    python check_memory_conflicts.py --entries-dir memory/entries [--output-dir memory/conflicts] [--threshold 0.6]
"""

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ── Paths ───────────────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).resolve().parent
CONFLICT_SCHEMA_PATH = SCRIPT_DIR.parent / "schemas" / "memory-conflict.schema.json"

# ── Conflict detection thresholds ───────────────────────────────────
DEFAULT_SIMILARITY_THRESHOLD = 0.60  # for redundancy detection
CONTRADICTION_SIGNALS = [
    "but", "however", "instead", "not", "never", "should not", "must not",
    "错误", "但是", "不应", "不要", "禁止", "相反", "而非",
]
SIMILARITY_BOOST_TERMS = [
    "same", "similar", "also", "additionally", "furthermore",
    "同样", "也", "另外", "此外",
]


def load_entries(entries_dir: Path) -> list[dict[str, Any]]:
    """Load all active memory entries."""
    entries = []
    if not entries_dir.exists():
        return entries

    for f in sorted(entries_dir.glob("*.json")):
        try:
            entry = json.loads(f.read_text(encoding="utf-8"))
            # Only check active entries
            if entry.get("status") == "active":
                # Normalize content
                content_block = entry.get("content", {})
                if isinstance(content_block, dict):
                    entry["_content_text"] = content_block.get("content", "")
                    entry["_content_type"] = content_block.get("content_type", "")
                    entry["_risk"] = content_block.get("risk", "")
                    entry["_confidence"] = content_block.get("confidence", "")
                else:
                    entry["_content_text"] = str(content_block)
                    entry["_content_type"] = ""
                    entry["_risk"] = ""
                    entry["_confidence"] = ""
                entries.append(entry)
        except (json.JSONDecodeError, OSError):
            continue
    return entries


def tokenize(text: str) -> set[str]:
    """Simple tokenization for similarity comparison."""
    # Lowercase, remove punctuation, split
    text = text.lower()
    text = re.sub(r"[^\w\s]", " ", text)
    # Filter out common stop words (English + Chinese)
    stop_words = {
        "the", "a", "an", "is", "are", "was", "were", "be", "been",
        "being", "have", "has", "had", "do", "does", "did", "will",
        "would", "could", "should", "may", "might", "must", "shall",
        "can", "need", "dare", "ought", "used", "to", "of", "in",
        "for", "on", "with", "at", "by", "from", "as", "into",
        "through", "during", "before", "after", "above", "below",
        "between", "out", "off", "over", "under", "again", "further",
        "then", "once", "的", "了", "在", "是", "我", "有", "和",
        "就", "不", "人", "都", "一", "一个", "上", "也", "很",
        "到", "说", "要", "去", "你", "会", "着", "没有", "看",
        "好", "自己", "这", "那", "这些", "那些", "这个", "那个",
    }
    tokens = {w for w in text.split() if w and w not in stop_words and len(w) > 1}
    return tokens


def jaccard_similarity(set_a: set[str], set_b: set[str]) -> float:
    """Calculate Jaccard similarity between two sets."""
    if not set_a and not set_b:
        return 1.0
    if not set_a or not set_b:
        return 0.0
    intersection = len(set_a & set_b)
    union = len(set_a | set_b)
    return intersection / union if union > 0 else 0.0


def check_contradiction(entry_a: dict[str, Any], entry_b: dict[str, Any]) -> dict[str, Any] | None:
    """
    Check if two entries contradict each other.
    Contradiction signals: both discuss same topic but give opposite advice.
    """
    text_a = entry_a.get("_content_text", "").lower()
    text_b = entry_b.get("_content_text", "").lower()

    if not text_a or not text_b:
        return None

    # Must have significant overlap first
    tokens_a = tokenize(text_a)
    tokens_b = tokenize(text_b)
    sim = jaccard_similarity(tokens_a, tokens_b)

    # Need at least moderate overlap to be about same topic
    if sim < 0.2:
        return None

    # Check if one has contradiction signals while the other doesn't
    a_has_contra = any(sig in text_a for sig in CONTRADICTION_SIGNALS)
    b_has_contra = any(sig in text_b for sig in CONTRADICTION_SIGNALS)

    # Check for opposing advice patterns
    opposite_patterns = [
        (r"should\s+use", r"should\s+not\s+use"),
        (r"must\s+use", r"must\s+not\s+use"),
        (r"recommend", r"not\s+recommend"),
        (r"启用", r"禁用"),
        (r"使用", r"不使用"),
        (r"应该", r"不应"),
        (r"必须", r"禁止"),
    ]

    has_opposite = False
    for pat_a, pat_b in opposite_patterns:
        a_match_a = bool(re.search(pat_a, text_a))
        a_match_b = bool(re.search(pat_b, text_a))
        b_match_a = bool(re.search(pat_a, text_b))
        b_match_b = bool(re.search(pat_b, text_b))
        if (a_match_a and b_match_b) or (a_match_b and b_match_a):
            has_opposite = True
            break

    if has_opposite or (a_has_contra and b_has_contra and sim > 0.3):
        return {
            "type": "contradiction",
            "confidence": "high" if has_opposite else "medium",
            "similarity": round(sim, 3),
            "description": (
                f"Entries appear to give conflicting advice on the same topic "
                f"(similarity={sim:.2f})"
            ),
        }

    return None


def check_redundancy(
    entry_a: dict[str, Any],
    entry_b: dict[str, Any],
    threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
) -> dict[str, Any] | None:
    """
    Check if two entries are redundant (high similarity, same type).
    """
    text_a = entry_a.get("_content_text", "")
    text_b = entry_b.get("_content_text", "")

    if not text_a or not text_b:
        return None

    # Same content type required for redundancy
    type_a = entry_a.get("_content_type", "")
    type_b = entry_b.get("_content_type", "")
    if type_a and type_b and type_a != type_b:
        return None

    tokens_a = tokenize(text_a)
    tokens_b = tokenize(text_b)
    sim = jaccard_similarity(tokens_a, tokens_b)

    if sim >= threshold:
        return {
            "type": "redundancy",
            "confidence": "high" if sim > 0.8 else "medium",
            "similarity": round(sim, 3),
            "description": f"Entries have high content similarity (Jaccard={sim:.2f}), may be redundant",
        }

    return None


def check_complementary(
    entry_a: dict[str, Any],
    entry_b: dict[str, Any],
) -> dict[str, Any] | None:
    """
    Check if two entries are complementary (moderate overlap, different aspects).
    """
    text_a = entry_a.get("_content_text", "")
    text_b = entry_b.get("_content_text", "")

    if not text_a or not text_b:
        return None

    # Must be same content type to be complementary
    type_a = entry_a.get("_content_type", "")
    type_b = entry_b.get("_content_type", "")
    if type_a and type_b and type_a != type_b:
        return None

    tokens_a = tokenize(text_a)
    tokens_b = tokenize(text_b)
    sim = jaccard_similarity(tokens_a, tokens_b)

    # Complementary: moderate overlap but not too high
    if 0.15 <= sim < 0.5:
        # Check if they cover different sub-topics
        unique_a = tokens_a - tokens_b
        unique_b = tokens_b - tokens_a

        if len(unique_a) > 5 and len(unique_b) > 5:
            return {
                "type": "complementary",
                "confidence": "medium",
                "similarity": round(sim, 3),
                "description": (
                    f"Entries cover related but distinct aspects "
                    f"(similarity={sim:.2f}, unique tokens: A={len(unique_a)}, B={len(unique_b)})"
                ),
            }

    return None


def detect_conflicts(
    entries: list[dict[str, Any]],
    threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
) -> list[dict[str, Any]]:
    """Detect all conflicts between entry pairs."""
    conflicts = []
    seen_pairs: set[tuple[str, str]] = set()

    for i, entry_a in enumerate(entries):
        for entry_b in entries[i + 1:]:
            id_a = entry_a.get("entry_id", "")
            id_b = entry_b.get("entry_id", "")

            if not id_a or not id_b:
                continue

            # Skip already checked pairs
            pair = tuple(sorted([id_a, id_b]))
            if pair in seen_pairs:
                continue
            seen_pairs.add(pair)

            # Check all conflict types
            checks = [
                check_contradiction(entry_a, entry_b),
                check_redundancy(entry_a, entry_b, threshold),
                check_complementary(entry_a, entry_b),
            ]

            for result in checks:
                if result is None:
                    continue

                conflict_id = (
                    f"conflict-{datetime.now(timezone.utc).strftime('%Y%m%d')}-"
                    f"{hashlib.sha256(f'{id_a}-{id_b}'.encode()).hexdigest()[:6]}"
                )

                conflict = {
                    "conflict_id": conflict_id,
                    "entry_a": id_a,
                    "entry_b": id_b,
                    "conflict_type": result["type"],
                    "description": result["description"],
                    "status": "open",
                    "detected_at": datetime.now(timezone.utc).isoformat(),
                    "detected_by": "check_memory_conflicts.py",
                    "_meta": {
                        "similarity": result["similarity"],
                        "confidence": result["confidence"],
                    },
                }
                conflicts.append(conflict)

    return conflicts


def main() -> int:
    parser = argparse.ArgumentParser(description="Check memory entries for conflicts")
    parser.add_argument("--entries-dir", required=True, help="Directory containing entry JSON files")
    parser.add_argument("--output-dir", default="memory/conflicts", help="Directory to write conflict reports")
    parser.add_argument("--threshold", type=float, default=DEFAULT_SIMILARITY_THRESHOLD,
                        help=f"Similarity threshold for redundancy detection (default: {DEFAULT_SIMILARITY_THRESHOLD})")
    parser.add_argument("--dry-run", action="store_true", help="Print without writing files")
    parser.add_argument("--min-similarity", type=float, default=0.0,
                        help="Minimum similarity to report (filters low-relevance results)")
    args = parser.parse_args()

    entries_dir = Path(args.entries_dir)
    output_dir = Path(args.output_dir)

    if not entries_dir.exists():
        print(f"[ERROR] Entries directory not found: {entries_dir}", file=sys.stderr)
        return 1

    # Load entries
    entries = load_entries(entries_dir)
    print(f"[INFO] Loaded {len(entries)} active entries.")

    if len(entries) < 2:
        print("[INFO] Need at least 2 entries to detect conflicts.")
        return 0

    # Detect conflicts
    conflicts = detect_conflicts(entries, threshold=args.threshold)

    # Filter by minimum similarity
    if args.min_similarity > 0:
        conflicts = [c for c in conflicts if c.get("_meta", {}).get("similarity", 0) >= args.min_similarity]

    # Summary by type
    by_type: dict[str, int] = {}
    for c in conflicts:
        ctype = c["conflict_type"]
        by_type[ctype] = by_type.get(ctype, 0) + 1

    print(f"[INFO] Detected {len(conflicts)} conflict(s):")
    for ctype, count in sorted(by_type.items()):
        print(f"       {ctype}: {count}")

    if not conflicts:
        print("[INFO] No conflicts detected.")
        return 0

    # Write output
    if not args.dry_run:
        output_dir.mkdir(parents=True, exist_ok=True)

    for conflict in conflicts:
        # Remove internal meta before writing
        conflict_clean = {k: v for k, v in conflict.items() if not k.startswith("_")}

        if args.dry_run:
            print(f"[DRY-RUN] {conflict['conflict_id']}: {conflict['conflict_type']} "
                  f"between {conflict['entry_a']} and {conflict['entry_b']} "
                  f"(sim={conflict.get('_meta', {}).get('similarity', 'N/A')})")
        else:
            out_path = output_dir / f"{conflict['conflict_id']}.json"
            out_path.write_text(json.dumps(conflict_clean, ensure_ascii=False, indent=2), encoding="utf-8")

    # Write summary report
    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_entries": len(entries),
        "total_conflicts": len(conflicts),
        "by_type": by_type,
        "conflict_ids": [c["conflict_id"] for c in conflicts],
    }

    if args.dry_run:
        print(f"\n[DRY-RUN] Summary: {json.dumps(summary, indent=2, ensure_ascii=False)}")
    else:
        summary_path = output_dir / "conflict-summary.json"
        summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[OK] Summary written to {summary_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
