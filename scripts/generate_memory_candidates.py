#!/usr/bin/env python3
"""
generate_memory_candidates.py

从任务产物生成memory candidates的脚本。
扫描指定任务目录，提取可复用经验并生成结构化的memory-candidate JSON文件。

用法:
    python generate_memory_candidates.py --task-dir /path/to/task-output --task-id task-name --agent-name agent-id
"""

import argparse
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ── Schema path resolution ──────────────────────────────────────────
SCRIPT_DIR = Path(__file__).resolve().parent
SCHEMA_PATH = SCRIPT_DIR.parent / "schemas" / "memory-candidate.schema.json"

# ── Content type detection rules ────────────────────────────────────
CONTENT_TYPE_PATTERNS = {
    "pattern": [
        r"pattern[：:]\s*(.+)",
        r"(?: reusable | best.+)pattern",
        r"模式[：:]\s*(.+)",
    ],
    "template": [
        r"template[：:]\s*(.+)",
        r"模板[：:]\s*(.+)",
        r"(?:code|config)\s+template",
    ],
    "rule": [
        r"rule[：:]\s*(.+)",
        r"规则[：:]\s*(.+)",
        r"(must|should|never|always|禁止|必须|应)",
    ],
    "lesson": [
        r"lesson\s*(learned|learnt)?[：:]\s*(.+)",
        r"教训[：:]\s*(.+)",
        r"踩坑",
        r"注意[：:]\s*(.+)",
    ],
    "reference": [
        r"reference[：:]\s*(.+)",
        r"参考[：:]\s*(.+)",
        r"see also",
    ],
}

RISK_KEYWORDS = {
    "critical": ["安全漏洞", "数据丢失", "权限", "加密", "delete", "drop", "remove all"],
    "high": ["错误输出", "系统故障", "性能", "timeout", "死锁"],
    "medium": ["低效", "返工", "兼容", "deprecated"],
    "low": ["风格", "命名", "格式", "排版"],
}


def load_schema() -> dict[str, Any]:
    """Load and return the memory-candidate schema."""
    if not SCHEMA_PATH.exists():
        print(f"[WARN] Schema not found at {SCHEMA_PATH}; skipping validation.", file=sys.stderr)
        return {}
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def detect_content_type(text: str) -> str:
    """Detect content type from text patterns."""
    text_lower = text.lower()
    scores = {ctype: 0 for ctype in CONTENT_TYPE_PATTERNS}
    for ctype, patterns in CONTENT_TYPE_PATTERNS.items():
        for pat in patterns:
            if re.search(pat, text_lower):
                scores[ctype] += 1
    if max(scores.values(), default=0) > 0:
        return max(scores, key=scores.get)  # type: ignore[return-value]
    return "lesson"  # default


def estimate_risk(text: str) -> str:
    """Estimate risk level from content keywords."""
    text_lower = text.lower()
    for level, keywords in RISK_KEYWORDS.items():
        for kw in keywords:
            if kw.lower() in text_lower:
                return level
    return "low"


def estimate_confidence(text: str) -> str:
    """Estimate confidence level from content signals."""
    text_lower = text.lower()
    # High confidence indicators
    if any(k in text_lower for k in ["verified", "tested", "confirmed", "多次验证", "已确认"]):
        return "high"
    # Low confidence indicators
    if any(k in text_lower for k in ["maybe", "possibly", "猜测", "可能", "未验证"]):
        return "low"
    return "medium"


def generate_candidate_id(content: str) -> str:
    """Generate a deterministic candidate ID."""
    ts = datetime.now(timezone.utc).strftime("%Y%m%d")
    h = hashlib.sha256(content.encode()).hexdigest()[:6]
    return f"cand-{ts}-{h}"


def extract_candidates_from_file(
    file_path: Path,
    task_id: str,
    agent_name: str,
) -> list[dict[str, Any]]:
    """Scan a single file and extract candidate-worthy content sections."""
    candidates: list[dict[str, Any]] = []
    content = file_path.read_text(encoding="utf-8")

    # Split by sections (markdown headers, code blocks, etc.)
    # Look for sections that seem like learnings/patterns/rules
    section_pattern = r"(?:^#{1,3}\s+.+$|^\s*[-*]{3,}\s*$|^```\w*\s*$)"
    sections = re.split(section_pattern, content, flags=re.MULTILINE)

    for section in sections:
        section = section.strip()
        if len(section) < 50:  # too short to be meaningful
            continue

        # Heuristic: look for keyword indicators of valuable content
        has_value_indicator = any(
            kw in section.lower()
            for kw in [
                "important", "note", "warning", "caution", "recommend",
                "best practice", "should", "must", "avoid", "注意",
                "重要", "建议", "推荐", "避免", "必须", "不要",
            ]
        )
        if not has_value_indicator:
            continue

        # Truncate overly long sections
        if len(section) > 2000:
            section = section[:2000] + "\n... (truncated)"

        content_type = detect_content_type(section)
        risk = estimate_risk(section)
        confidence = estimate_confidence(section)
        candidate_id = generate_candidate_id(section)

        candidate = {
            "candidate_id": candidate_id,
            "source_task": task_id,
            "source_agent": agent_name,
            "content_type": content_type,
            "content": section,
            "source": str(file_path),
            "confidence": confidence,
            "risk": risk,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        candidates.append(candidate)

    return candidates


def validate_candidate(candidate: dict[str, Any], schema: dict[str, Any]) -> bool:
    """Validate a candidate against the schema (basic check)."""
    if not schema:
        return True
    required = schema.get("required", [])
    for field in required:
        if field not in candidate or candidate[field] in (None, ""):
            print(f"[WARN] Missing required field: {field} in {candidate.get('candidate_id', '?')}", file=sys.stderr)
            return False
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate memory candidates from task output")
    parser.add_argument("--task-dir", required=True, help="Directory containing task output files")
    parser.add_argument("--task-id", required=True, help="Task identifier")
    parser.add_argument("--agent-name", required=True, help="Agent that executed the task")
    parser.add_argument("--output-dir", default=None, help="Output directory for candidates")
    parser.add_argument("--dry-run", action="store_true", help="Print without writing files")
    args = parser.parse_args()

    task_dir = Path(args.task_dir)
    if not task_dir.exists():
        print(f"[ERROR] Task directory not found: {task_dir}", file=sys.stderr)
        return 1

    output_dir = Path(args.output_dir) if args.output_dir else Path("memory/candidates")
    if not args.dry_run:
        output_dir.mkdir(parents=True, exist_ok=True)

    schema = load_schema()

    # Scan all relevant files
    candidates: list[dict[str, Any]] = []
    for ext in (".md", ".txt", ".json", ".yaml", ".yml", ".py", ".js", ".ts", ".sh"):
        for file_path in task_dir.rglob(f"*{ext}"):
            if file_path.is_file():
                try:
                    file_candidates = extract_candidates_from_file(
                        file_path, args.task_id, args.agent_name
                    )
                    candidates.extend(file_candidates)
                except Exception as e:
                    print(f"[WARN] Failed to process {file_path}: {e}", file=sys.stderr)

    if not candidates:
        print("[INFO] No memory candidates found in task output.")
        return 0

    # Validate and write
    written = 0
    for cand in candidates:
        if not validate_candidate(cand, schema):
            continue

        if args.dry_run:
            print(f"[DRY-RUN] Would write: {cand['candidate_id']} (type={cand['content_type']}, risk={cand['risk']})")
        else:
            out_path = output_dir / f"memory-candidate-{cand['candidate_id']}.json"
            out_path.write_text(json.dumps(cand, ensure_ascii=False, indent=2), encoding="utf-8")
            written += 1

    print(f"[INFO] Generated {written} memory candidate(s) from task '{args.task_id}'.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
