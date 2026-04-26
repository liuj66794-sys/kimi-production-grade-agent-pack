#!/usr/bin/env python3
"""
clean_runtime_artifacts.py — Safe cleanup script for runtime temp files and artifacts.

Usage:
    python scripts/clean_runtime_artifacts.py --dry-run    # Preview what would be deleted (default)
    python scripts/clean_runtime_artifacts.py --confirm    # Actually delete files

Cleans:
    - runtime/ directory (temp files, logs, task events)
    - artifacts/ directory (generated outputs)

Safety:
    - Default is dry-run; must pass --confirm to actually delete
    - Preserves .gitkeep files
    - Generates cleanup report
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

CLEAN_TARGETS: list[str] = [
    "runtime",
    "artifacts",
]

PRESERVE_FILES: set[str] = {
    ".gitkeep",
    ".gitignore",
    ".keep",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_project_root() -> Path:
    """Return the project root directory."""
    return Path(__file__).resolve().parent.parent


def log(msg: str, level: str = "INFO") -> None:
    """Print a formatted log message."""
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%MZ")
    print(f"[{timestamp}] [{level}] {msg}")


def format_size(size_bytes: int) -> str:
    """Format byte size to human-readable string."""
    for unit in ["B", "KB", "MB", "GB"]:
        if abs(size_bytes) < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} TB"


def scan_directory(dpath: Path) -> dict[str, Any]:
    """Scan a directory and return statistics about its contents."""
    stats = {
        "path": str(dpath),
        "exists": dpath.exists(),
        "total_files": 0,
        "total_dirs": 0,
        "total_size": 0,
        "files": [],
    }

    if not dpath.is_dir():
        return stats

    for item in sorted(dpath.rglob("*")):
        if item.is_file():
            if item.name in PRESERVE_FILES:
                continue
            size = item.stat().st_size
            stats["total_files"] += 1
            stats["total_size"] += size
            stats["files"].append({
                "path": str(item.relative_to(dpath)),
                "size": size,
            })
        elif item.is_dir():
            stats["total_dirs"] += 1

    return stats


def clean_directory(dpath: Path, dry_run: bool = True) -> dict[str, Any]:
    """Clean a single directory. Returns stats about what was done."""
    stats = scan_directory(dpath)
    stats["dry_run"] = dry_run
    stats["cleaned"] = False

    if not stats["exists"]:
        log(f"Directory does not exist: {dpath}")
        return stats

    if stats["total_files"] == 0:
        log(f"Directory is empty: {dpath}/")
        return stats

    action = "Would delete" if dry_run else "Deleting"
    log(f"{action} {stats['total_files']} files ({format_size(stats['total_size'])}) from {dpath}/")

    if not dry_run:
        # Delete files but preserve directory structure and .gitkeep
        for item in sorted(dpath.rglob("*"), reverse=True):
            if item.is_file() and item.name not in PRESERVE_FILES:
                item.unlink()
            elif item.is_dir():
                # Remove empty directories
                try:
                    item.rmdir()
                except OSError:
                    pass  # Directory not empty (may have .gitkeep)
        stats["cleaned"] = True

    return stats


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Clean runtime temp files and artifacts",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/clean_runtime_artifacts.py --dry-run    # Preview (default)
  python scripts/clean_runtime_artifacts.py --confirm    # Actually delete
        """,
    )
    parser.add_argument("--dry-run", action="store_true", default=True, help="Preview mode (default)")
    parser.add_argument("--confirm", action="store_true", help="Actually delete files")
    parser.add_argument("--targets", nargs="*", default=None, help="Specific directories to clean")
    args = parser.parse_args()

    dry_run = not args.confirm
    root = get_project_root()
    targets = args.targets if args.targets else CLEAN_TARGETS

    print("=" * 50)
    print("  Kimi Agent Pack — Cleanup Tool")
    print(f"  Mode: {'DRY-RUN (preview only)' if dry_run else 'CONFIRM (will delete)'}")
    print("=" * 50)
    print()

    if not dry_run:
        log("WARNING: This will permanently delete files!", level="WARN")
        # Double-check in non-dry-run mode
        print()

    all_stats: list[dict[str, Any]] = []
    total_files = 0
    total_size = 0

    for target in targets:
        dpath = root / target
        stats = clean_directory(dpath, dry_run=dry_run)
        all_stats.append(stats)
        total_files += stats["total_files"]
        total_size += stats["total_size"]
        print()

    # Generate report
    report = {
        "report_type": "cleanup",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "dry_run": dry_run,
        "summary": {
            "targets_cleaned": len(targets),
            "total_files": total_files,
            "total_size_bytes": total_size,
            "total_size_human": format_size(total_size),
        },
        "details": all_stats,
    }

    report_path = root / "runtime" / "cleanup-report.json"
    if not dry_run and report_path.parent.is_dir():
        report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        log(f"Cleanup report written to: {report_path}")
    else:
        # Write to current directory in dry-run mode
        dry_run_report = root / "cleanup-report.json"
        dry_run_report.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        log(f"Cleanup report written to: {dry_run_report}")

    # Summary
    print("-" * 40)
    log(f"Targets: {len(targets)}")
    log(f"Files: {total_files}")
    log(f"Size: {format_size(total_size)}")
    log(f"Mode: {'preview' if dry_run else 'deleted'}")

    if dry_run and total_files > 0:
        print()
        log("Run with --confirm to actually delete these files", level="WARN")

    return 0


if __name__ == "__main__":
    sys.exit(main())
