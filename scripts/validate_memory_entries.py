#!/usr/bin/env python3
"""
validate_memory_entries.py

验证memory entries的格式和约束的脚本。
检查schema合规性、字段约束、状态一致性等。

用法:
    python validate_memory_entries.py --entries-dir memory/entries [--schema schemas/memory-entry.schema.json] [--index memory/index.json]
"""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

# ── Paths ───────────────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_SCHEMA_PATH = SCRIPT_DIR.parent / "schemas" / "memory-entry.schema.json"

# ── Valid enums ─────────────────────────────────────────────────────
VALID_CONTENT_TYPES = {"pattern", "template", "rule", "reference", "lesson"}
VALID_CONFIDENCE = {"high", "medium", "low"}
VALID_RISK = {"low", "medium", "high", "critical"}
VALID_STATUS = {"active", "deprecated", "retracted"}
VALID_RETRACTION_REASONS = {"factual_error", "security_risk", "outdated", "conflicting", "superseded"}

# ── ID patterns ─────────────────────────────────────────────────────
ENTRY_ID_PATTERN = re.compile(r"^entry-[0-9]{8}-[a-f0-9]{4,}$")
CANDIDATE_ID_PATTERN = re.compile(r"^cand-[0-9]{8}-[a-f0-9]{6,}$")
DATETIME_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$")


class ValidationError:
    """Represents a single validation error."""

    def __init__(self, entry_id: str, field: str, message: str, severity: str = "error"):
        self.entry_id = entry_id
        self.field = field
        self.message = message
        self.severity = severity

    def __str__(self) -> str:
        return f"[{self.severity.upper()}] {self.entry_id} | {self.field}: {self.message}"


def validate_datetime(value: Any, field_name: str, entry_id: str) -> list[ValidationError]:
    """Validate ISO 8601 datetime string."""
    errors = []
    if not isinstance(value, str):
        errors.append(ValidationError(entry_id, field_name, "Must be a string"))
    elif not DATETIME_PATTERN.match(value):
        errors.append(ValidationError(entry_id, field_name, f"Invalid datetime format: {value}"))
    return errors


def validate_entry_id(value: Any, entry_id: str) -> list[ValidationError]:
    """Validate entry_id format."""
    errors = []
    if not isinstance(value, str):
        errors.append(ValidationError(entry_id, "entry_id", "Must be a string"))
    elif not ENTRY_ID_PATTERN.match(value):
        errors.append(ValidationError(entry_id, "entry_id", f"Invalid format: {value}"))
    return errors


def validate_schema_compliance(entry: dict[str, Any]) -> list[ValidationError]:
    """Validate basic schema compliance."""
    errors = []
    entry_id = entry.get("entry_id", "unknown")

    # Required fields
    required = ["entry_id", "candidate_ref", "approved_by", "approved_at", "status"]
    for field in required:
        if field not in entry:
            errors.append(ValidationError(entry_id, field, "Missing required field"))

    # approved_by
    if entry.get("approved_by") not in (None, "memory-reviewer"):
        errors.append(ValidationError(entry_id, "approved_by", "Must be 'memory-reviewer'"))

    # status
    status = entry.get("status")
    if status and status not in VALID_STATUS:
        errors.append(ValidationError(entry_id, "status", f"Invalid status: {status}"))

    # Datetime fields
    for field in ["approved_at", "last_accessed_at"]:
        value = entry.get(field)
        if value is not None:
            errors.extend(validate_datetime(value, field, entry_id))

    # entry_id format
    if "entry_id" in entry:
        errors.extend(validate_entry_id(entry["entry_id"], entry_id))

    # candidate_ref format
    cand_ref = entry.get("candidate_ref")
    if cand_ref and not CANDIDATE_ID_PATTERN.match(cand_ref):
        errors.append(ValidationError(entry_id, "candidate_ref", f"Invalid format: {cand_ref}"))

    return errors


def validate_status_consistency(entry: dict[str, Any]) -> list[ValidationError]:
    """Validate status-specific field consistency."""
    errors = []
    entry_id = entry.get("entry_id", "unknown")
    status = entry.get("status")

    # active: should not have deprecated_info or retraction_info
    if status == "active":
        if entry.get("deprecated_info"):
            errors.append(ValidationError(
                entry_id, "deprecated_info",
                "Active entry should not have deprecated_info",
                "warning"
            ))
        if entry.get("retraction_info"):
            errors.append(ValidationError(
                entry_id, "retraction_info",
                "Active entry should not have retraction_info",
                "warning"
            ))

    # deprecated: must have deprecated_info
    if status == "deprecated":
        if not entry.get("deprecated_info"):
            errors.append(ValidationError(
                entry_id, "deprecated_info",
                "Deprecated entry must have deprecated_info"
            ))
        else:
            dep = entry["deprecated_info"]
            if "reason" not in dep or not dep["reason"]:
                errors.append(ValidationError(entry_id, "deprecated_info.reason", "Required"))
            if "deprecated_at" in dep:
                errors.extend(validate_datetime(dep["deprecated_at"], "deprecated_info.deprecated_at", entry_id))

    # retracted: must have retraction_info
    if status == "retracted":
        if not entry.get("retraction_info"):
            errors.append(ValidationError(
                entry_id, "retraction_info",
                "Retracted entry must have retraction_info"
            ))
        else:
            ret = entry["retraction_info"]
            if "reason" not in ret or not ret["reason"]:
                errors.append(ValidationError(entry_id, "retraction_info.reason", "Required"))
            elif ret["reason"] not in VALID_RETRACTION_REASONS:
                errors.append(ValidationError(
                    entry_id, "retraction_info.reason",
                    f"Invalid reason: {ret['reason']}"
                ))
            for field in ["retracted_at"]:
                if field in ret:
                    errors.extend(validate_datetime(ret[field], f"retraction_info.{field}", entry_id))

    return errors


def validate_content(entry: dict[str, Any]) -> list[ValidationError]:
    """Validate embedded content structure."""
    errors = []
    entry_id = entry.get("entry_id", "unknown")
    content = entry.get("content")

    if not content:
        # Content is optional at top level but recommended
        return [ValidationError(entry_id, "content", "Missing content block", "warning")]

    if not isinstance(content, dict):
        errors.append(ValidationError(entry_id, "content", "Must be an object"))
        return errors

    # Required content fields
    content_required = ["source_task", "source_agent", "content_type", "content", "source", "confidence", "risk", "created_at"]
    for field in content_required:
        if field not in content:
            errors.append(ValidationError(entry_id, f"content.{field}", "Missing required field"))

    # Validate enums
    ct = content.get("content_type")
    if ct and ct not in VALID_CONTENT_TYPES:
        errors.append(ValidationError(entry_id, "content.content_type", f"Invalid: {ct}"))

    conf = content.get("confidence")
    if conf and conf not in VALID_CONFIDENCE:
        errors.append(ValidationError(entry_id, "content.confidence", f"Invalid: {conf}"))

    risk = content.get("risk")
    if risk and risk not in VALID_RISK:
        errors.append(ValidationError(entry_id, "content.risk", f"Invalid: {risk}"))

    # Validate content.content is non-empty
    if content.get("content") and len(str(content["content"])) < 10:
        errors.append(ValidationError(entry_id, "content.content", "Too short (min 10 chars)"))

    # Validate datetime
    if "created_at" in content:
        errors.extend(validate_datetime(content["created_at"], "content.created_at", entry_id))

    # Tags
    tags = content.get("tags")
    if tags is not None:
        if not isinstance(tags, list):
            errors.append(ValidationError(entry_id, "content.tags", "Must be an array"))
        else:
            for i, tag in enumerate(tags):
                if not isinstance(tag, str) or not tag.strip():
                    errors.append(ValidationError(entry_id, f"content.tags[{i}]", "Invalid tag"))

    return errors


def validate_access_count(entry: dict[str, Any]) -> list[ValidationError]:
    """Validate access_count consistency."""
    errors = []
    entry_id = entry.get("entry_id", "unknown")
    count = entry.get("access_count")

    if count is not None:
        if not isinstance(count, int) or count < 0:
            errors.append(ValidationError(entry_id, "access_count", "Must be a non-negative integer"))

        # If access_count > 0, last_accessed_at should exist
        if isinstance(count, int) and count > 0 and not entry.get("last_accessed_at"):
            errors.append(ValidationError(
                entry_id, "last_accessed_at",
                "Should exist when access_count > 0",
                "warning"
            ))

    return errors


def validate_against_index(entry: dict[str, Any], index_entries: list[dict[str, Any]]) -> list[ValidationError]:
    """Cross-validate against index.json if provided."""
    errors = []
    entry_id = entry.get("entry_id", "unknown")

    if not index_entries:
        return errors

    index_ids = {e.get("entry_id") for e in index_entries}
    if entry_id not in index_ids:
        errors.append(ValidationError(
            entry_id, "entry_id",
            "Entry not found in index.json",
            "warning"
        ))

    return errors


def validate_file(file_path: Path, index_entries: list[dict[str, Any]]) -> list[ValidationError]:
    """Validate a single entry file."""
    errors = []
    entry_id = file_path.stem

    try:
        entry = json.loads(file_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        return [ValidationError(entry_id, "_file", f"Invalid JSON: {e}")]
    except OSError as e:
        return [ValidationError(entry_id, "_file", f"Read error: {e}")]

    if not isinstance(entry, dict):
        return [ValidationError(entry_id, "_root", "Root must be an object")]

    errors.extend(validate_schema_compliance(entry))
    errors.extend(validate_status_consistency(entry))
    errors.extend(validate_content(entry))
    errors.extend(validate_access_count(entry))
    errors.extend(validate_against_index(entry, index_entries))

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate memory entries")
    parser.add_argument("--entries-dir", required=True, help="Directory containing entry JSON files")
    parser.add_argument("--schema", default=str(DEFAULT_SCHEMA_PATH), help="Path to JSON schema")
    parser.add_argument("--index", default=None, help="Path to index.json for cross-validation")
    parser.add_argument("--strict", action="store_true", help="Treat warnings as errors")
    args = parser.parse_args()

    entries_dir = Path(args.entries_dir)
    if not entries_dir.exists():
        print(f"[ERROR] Entries directory not found: {entries_dir}", file=sys.stderr)
        return 1

    # Load index if provided
    index_entries: list[dict[str, Any]] = []
    if args.index:
        index_path = Path(args.index)
        if index_path.exists():
            try:
                index_data = json.loads(index_path.read_text(encoding="utf-8"))
                index_entries = index_data.get("entries", [])
            except (json.JSONDecodeError, OSError) as e:
                print(f"[WARN] Failed to load index: {e}", file=sys.stderr)

    # Validate all entry files
    entry_files = sorted(entries_dir.glob("*.json"))
    if not entry_files:
        print("[INFO] No entry files found.")
        return 0

    all_errors: list[ValidationError] = []
    stats = {"ok": 0, "warning": 0, "error": 0}

    for entry_file in entry_files:
        errors = validate_file(entry_file, index_entries)
        if not errors:
            stats["ok"] += 1
            print(f"[OK] {entry_file.name}")
        else:
            for err in errors:
                all_errors.append(err)
                stats[err.severity] += 1
                print(str(err))

    # Summary
    print(f"\n{'='*50}")
    print(f"Validation Summary: {len(entry_files)} file(s)")
    print(f"  OK:       {stats['ok']}")
    print(f"  Warnings: {stats['warning']}")
    print(f"  Errors:   {stats['error']}")

    if args.strict and stats["warning"] > 0:
        print("\n[FAIL] Strict mode: warnings treated as errors")
        return 1

    if stats["error"] > 0:
        print("\n[FAIL] Validation errors found")
        return 1

    print("\n[PASS] All entries valid")
    return 0


if __name__ == "__main__":
    sys.exit(main())
