#!/usr/bin/env python3
"""
Artifact Validation Script — v1.2
Kimi Production-Grade Agent Pack

Validates integration smoke test artifacts:
- Checks required artifacts exist
- Validates format against expected schemas
- Verifies file integrity (non-zero size, readable)
- Generates artifact-manifest.json

Usage:
    python validate_artifacts.py --artifacts-dir artifacts/integration-smoke-001/
    python validate_artifacts.py --manifest artifact-manifest.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"

# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

ARTIFACT_SCHEMAS: dict[str, dict[str, Any]] = {
    "task-brief.json": {
        "type": "json",
        "required_keys": ["task_id", "title", "description", "requirements", "created_at"],
        "value_types": {
            "task_id": str,
            "title": str,
            "description": str,
            "requirements": list,
        },
    },
    "research-notes.md": {
        "type": "markdown",
        "min_lines": 5,
        "required_headers": ["## "],
    },
    "analysis-report.md": {
        "type": "markdown",
        "min_lines": 5,
        "required_headers": ["## "],
    },
    "claim-evidence-map.json": {
        "type": "json",
        "required_keys": ["claims", "evidence_map"],
        "value_types": {
            "claims": list,
            "evidence_map": dict,
        },
    },
    "final-report.md": {
        "type": "markdown",
        "min_lines": 10,
        "required_headers": ["# ", "## "],
    },
    "qa-review.json": {
        "type": "json",
        "required_keys": ["review_status", "findings", "scored_categories"],
        "value_types": {
            "review_status": str,
            "findings": list,
            "scored_categories": dict,
        },
    },
    "orchestration-plan.json": {
        "type": "json",
        "required_keys": ["plan_id", "steps"],
        "value_types": {
            "plan_id": str,
            "steps": list,
        },
    },
    "eval-result.json": {
        "type": "json",
        "required_keys": ["eval_id", "passed", "metrics"],
        "value_types": {
            "eval_id": str,
            "passed": bool,
            "metrics": dict,
        },
    },
}

# Required artifacts for the deep-research-minimal smoke test
REQUIRED_ARTIFACTS: list[str] = [
    "task-brief.json",
    "research-notes.md",
    "analysis-report.md",
    "claim-evidence-map.json",
    "final-report.md",
    "qa-review.json",
]

# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass
class ArtifactEntry:
    name: str
    path: str
    type: str
    size_bytes: int
    sha256: str
    exists: bool
    readable: bool
    non_empty: bool
    schema_valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @property
    def valid(self) -> bool:
        return self.exists and self.readable and self.non_empty and self.schema_valid


@dataclass
class ArtifactManifest:
    manifest_version: str = "1.2"
    generated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    artifacts_dir: str = ""
    total_artifacts: int = 0
    valid_count: int = 0
    invalid_count: int = 0
    missing_count: int = 0
    entries: list[ArtifactEntry] = field(default_factory=list)
    summary: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        return data

    def compute_summary(self) -> None:
        self.total_artifacts = len(self.entries)
        self.valid_count = sum(1 for e in self.entries if e.valid)
        self.invalid_count = sum(1 for e in self.entries if e.exists and not e.valid)
        self.missing_count = sum(1 for e in self.entries if not e.exists)
        self.summary = {
            "total": self.total_artifacts,
            "valid": self.valid_count,
            "invalid": self.invalid_count,
            "missing": self.missing_count,
            "pass_rate": round(self.valid_count / self.total_artifacts, 4) if self.total_artifacts else 0.0,
            "all_pass": self.valid_count == self.total_artifacts and self.total_artifacts > 0,
        }


# ---------------------------------------------------------------------------
# Validation engine
# ---------------------------------------------------------------------------

class ArtifactValidator:
    def __init__(self, artifacts_dir: Path) -> None:
        self.artifacts_dir = artifacts_dir.resolve()
        self.logger = logging.getLogger(self.__class__.__name__)

    @staticmethod
    def sha256_file(path: Path) -> str:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        return h.hexdigest()

    def validate_file(self, name: str) -> ArtifactEntry:
        """Validate a single artifact file."""
        path = self.artifacts_dir / name
        schema = ARTIFACT_SCHEMAS.get(name, {})
        entry = ArtifactEntry(
            name=name,
            path=str(path),
            type=schema.get("type", "unknown"),
            size_bytes=0,
            sha256="",
            exists=False,
            readable=False,
            non_empty=False,
            schema_valid=False,
        )

        # 1. Existence
        if not path.exists():
            entry.errors.append("File does not exist")
            return entry
        entry.exists = True

        # 2. Readability & size
        try:
            stat = path.stat()
            entry.size_bytes = stat.st_size
            if stat.st_size == 0:
                entry.errors.append("File is empty (0 bytes)")
                return entry
            entry.non_empty = True
        except OSError as exc:
            entry.errors.append(f"Cannot stat file: {exc}")
            return entry

        # 3. Compute hash
        try:
            entry.sha256 = self.sha256_file(path)
        except OSError as exc:
            entry.errors.append(f"Cannot compute hash: {exc}")
            return entry

        # 4. Read content
        try:
            content = path.read_text(encoding="utf-8")
            entry.readable = True
        except (OSError, UnicodeDecodeError) as exc:
            entry.errors.append(f"Cannot read file as UTF-8 text: {exc}")
            return entry

        # 5. Schema validation
        entry.schema_valid = True
        self._validate_schema(content, schema, entry)

        return entry

    def _validate_schema(self, content: str, schema: dict[str, Any], entry: ArtifactEntry) -> None:
        """Validate file content against schema definition."""
        if not schema:
            entry.warnings.append("No schema defined for this artifact type")
            return

        artifact_type = schema.get("type", "")

        if artifact_type == "json":
            self._validate_json(content, schema, entry)
        elif artifact_type == "markdown":
            self._validate_markdown(content, schema, entry)
        else:
            entry.warnings.append(f"Unknown schema type: {artifact_type}")

    def _validate_json(self, content: str, schema: dict[str, Any], entry: ArtifactEntry) -> None:
        try:
            data = json.loads(content)
        except json.JSONDecodeError as exc:
            entry.schema_valid = False
            entry.errors.append(f"Invalid JSON: {exc}")
            return

        if not isinstance(data, dict):
            entry.schema_valid = False
            entry.errors.append("JSON root must be an object")
            return

        # Check required keys
        for key in schema.get("required_keys", []):
            if key not in data:
                entry.schema_valid = False
                entry.errors.append(f"Missing required key: '{key}'")

        # Check value types
        for key, expected_type in schema.get("value_types", {}).items():
            if key in data and not isinstance(data[key], expected_type):
                entry.schema_valid = False
                entry.errors.append(
                    f"Key '{key}' expected type {expected_type.__name__}, "
                    f"got {type(data[key]).__name__}"
                )

        # Check enum values for known fields
        if "review_status" in data and data.get("review_status") not in ("pass", "pass_with_notes", "fail", "hard_fail"):
            entry.warnings.append(
                f"review_status has unexpected value: {data['review_status']}"
            )

    def _validate_markdown(self, content: str, schema: dict[str, Any], entry: ArtifactEntry) -> None:
        lines = content.strip().splitlines()

        # Check minimum lines
        min_lines = schema.get("min_lines", 0)
        if min_lines > 0 and len(lines) < min_lines:
            entry.schema_valid = False
            entry.errors.append(f"Expected at least {min_lines} lines, got {len(lines)}")

        # Check required headers
        for header_prefix in schema.get("required_headers", []):
            if not any(line.startswith(header_prefix) for line in lines):
                entry.schema_valid = False
                entry.errors.append(f"Missing required header starting with '{header_prefix}'")

    def validate_all(self, required: list[str] | None = None) -> ArtifactManifest:
        """Validate all required artifacts and generate manifest."""
        artifact_names = required or REQUIRED_ARTIFACTS
        manifest = ArtifactManifest(artifacts_dir=str(self.artifacts_dir))

        self.logger.info("Validating artifacts in: %s", self.artifacts_dir)

        for name in artifact_names:
            entry = self.validate_file(name)
            manifest.entries.append(entry)
            status = "VALID" if entry.valid else "INVALID"
            self.logger.info("  %s: %s (size=%d bytes)", name, status, entry.size_bytes)
            for err in entry.errors:
                self.logger.warning("    ERROR: %s", err)

        manifest.compute_summary()
        return manifest

    def validate_from_manifest(self, manifest_path: Path) -> ArtifactManifest:
        """Re-validate artifacts using an existing manifest as reference."""
        with open(manifest_path, "r", encoding="utf-8") as f:
            old_manifest = json.load(f)

        artifact_names = [e["name"] for e in old_manifest.get("entries", [])]
        if not artifact_names:
            artifact_names = REQUIRED_ARTIFACTS

        # Use the artifacts_dir from manifest if available
        artifacts_dir = old_manifest.get("artifacts_dir", str(self.artifacts_dir))
        self.artifacts_dir = Path(artifacts_dir)

        new_manifest = self.validate_all(artifact_names)
        return new_manifest


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

def print_summary(manifest: ArtifactManifest) -> None:
    """Print validation summary to console."""
    print("\n" + "=" * 70)
    print("  ARTIFACT VALIDATION SUMMARY")
    print("=" * 70)
    print(f"  Artifacts directory : {manifest.artifacts_dir}")
    print(f"  Generated at       : {manifest.generated_at}")
    print(f"  Manifest version   : {manifest.manifest_version}")
    print("-" * 70)

    for entry in manifest.entries:
        status_icon = "✓" if entry.valid else "✗"
        status_text = "PASS" if entry.valid else "FAIL"
        print(f"\n  {status_icon} {entry.name:<30} [{status_text}]")
        print(f"    Path    : {entry.path}")
        print(f"    Type    : {entry.type}")
        print(f"    Size    : {entry.size_bytes:,} bytes")
        print(f"    SHA256  : {entry.sha256[:16]}...")
        print(f"    Exists  : {entry.exists}")
        print(f"    Readable: {entry.readable}")
        print(f"    Non-empty: {entry.non_empty}")
        print(f"    Schema  : {entry.schema_valid}")
        if entry.errors:
            print(f"    Errors  :")
            for err in entry.errors:
                print(f"      - {err}")
        if entry.warnings:
            print(f"    Warnings:")
            for warn in entry.warnings:
                print(f"      - {warn}")

    print("\n" + "=" * 70)
    print("  SUMMARY")
    print("=" * 70)
    s = manifest.summary
    print(f"  Total    : {s['total']}")
    print(f"  Valid    : {s['valid']}")
    print(f"  Invalid  : {s['invalid']}")
    print(f"  Missing  : {s['missing']}")
    print(f"  Pass rate: {s['pass_rate']:.1%}")
    print(f"  All pass : {s['all_pass']}")
    print("=" * 70 + "\n")


def write_manifest(manifest: ArtifactManifest, output_path: Path) -> None:
    """Write manifest to JSON file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(manifest.to_dict(), f, indent=2, ensure_ascii=False)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Artifact Validation Script — v1.2",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --artifacts-dir artifacts/integration-smoke-001/
  %(prog)s --manifest artifact-manifest.json
  %(prog)s --artifacts-dir ./artifacts --output-manifest manifest.json
  %(prog)s --artifacts-dir ./artifacts --json-only
        """,
    )
    parser.add_argument(
        "--artifacts-dir",
        type=Path,
        help="Directory containing artifacts to validate",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        help="Path to existing manifest for re-validation",
    )
    parser.add_argument(
        "--output-manifest",
        type=Path,
        default=Path("artifact-manifest.json"),
        help="Output path for generated manifest (default: artifact-manifest.json)",
    )
    parser.add_argument(
        "--required",
        nargs="+",
        help="List of required artifact names (overrides default set)",
    )
    parser.add_argument(
        "--json-only",
        action="store_true",
        help="Output only JSON result to stdout (no human-readable summary)",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format=LOG_FORMAT,
    )

    # Determine mode
    if args.manifest:
        # Re-validation mode
        if not args.manifest.exists():
            print(f"ERROR: Manifest file not found: {args.manifest}", file=sys.stderr)
            return 1
        # Read manifest to get artifacts_dir
        with open(args.manifest, "r", encoding="utf-8") as f:
            manifest_data = json.load(f)
        artifacts_dir = Path(manifest_data.get("artifacts_dir", "."))
        validator = ArtifactValidator(artifacts_dir)
        manifest = validator.validate_from_manifest(args.manifest)
    elif args.artifacts_dir:
        validator = ArtifactValidator(args.artifacts_dir)
        manifest = validator.validate_all(args.required)
    else:
        parser.error("Must specify either --artifacts-dir or --manifest")
        return 1  # unreachable

    # Write manifest
    write_manifest(manifest, args.output_manifest)

    if not args.json_only:
        print_summary(manifest)
        print(f"Manifest written to: {args.output_manifest}")
    else:
        print(json.dumps(manifest.to_dict(), indent=2, ensure_ascii=False))

    # Exit code: 0 if all pass, 1 otherwise
    return 0 if manifest.summary.get("all_pass", False) else 1


if __name__ == "__main__":
    sys.exit(main())
