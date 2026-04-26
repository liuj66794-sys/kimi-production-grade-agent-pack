#!/usr/bin/env python3
"""
package_l1_release.py — Release packaging script for Kimi Agent Pack.

Usage:
    python scripts/package_l1_release.py --version v1.3.0-rc1
    python scripts/package_l1_release.py --version v1.3.0 --skip-check

Steps:
    1. Run release_check.py
    2. Clean runtime/ and artifacts/ (dry-run by default)
    3. Exclude evals/results/ and other large files
    4. Copy required files to dist/
    5. Generate release-manifest.json
    6. Package as zip
    7. Generate release-report.json

Exclusions:
    runtime/*, artifacts/*, evals/results/*, .github/*, __pycache__/
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DEFAULT_EXCLUDES = [
    "runtime/*",
    "artifacts/*",
    "evals/results/*",
    ".github/*",
    "__pycache__/*",
    "*.pyc",
    "*.pyo",
    ".git/*",
    ".gitignore",
    ".venv/*",
    "venv/*",
    "*.egg-info/*",
    "dist/*",
    "*.zip",
    ".pytest_cache/*",
    "*.bak",
    "*.swp",
    ".DS_Store",
    "Thumbs.db",
]

REQUIRED_FOR_DIST: list[str] = [
    "README.md",
    "QUICKSTART.md",
    "CHANGELOG.md",
    "RELEASE_NOTES.md",
    "TROUBLESHOOTING.md",
    "DESIGN.md",
    "AGENTS.md",
    "SKILL.md",
    "VERSION",
    "requirements.txt",
    "LICENSE",
]

REQUIRED_DIRS_FOR_DIST: list[str] = [
    "agents",
    "skills",
    "schemas",
    "scripts",
    "evals",
    "examples",
    "docs",
]


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


def compute_sha256(filepath: Path) -> str:
    """Compute SHA256 hash of a file."""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def should_exclude(rel_path: str, excludes: list[str]) -> bool:
    """Check if a relative path matches any exclude pattern."""
    for pattern in excludes:
        # Handle wildcard patterns
        if pattern.endswith("/*"):
            prefix = pattern[:-2]
            if rel_path == prefix or rel_path.startswith(prefix + "/"):
                return True
        elif pattern.startswith("*"):
            if rel_path.endswith(pattern[1:]):
                return True
        elif rel_path == pattern:
            return True
    return False


# ---------------------------------------------------------------------------
# Steps
# ---------------------------------------------------------------------------

def run_release_check(root: Path) -> bool:
    """Step 1: Run release_check.py and return True if passed."""
    check_script = root / "scripts" / "release_check.py"
    if not check_script.is_file():
        log("release_check.py not found, skipping", level="WARN")
        return True

    log("Running release check...")
    try:
        result = subprocess.run(
            [sys.executable, str(check_script), "--level", "l1"],
            capture_output=True,
            text=True,
            timeout=60,
        )
        passed = result.returncode == 0
        if passed:
            log("Release check: PASS")
        else:
            log("Release check: FAIL", level="ERROR")
            if result.stdout:
                print(result.stdout[-1000:])
        return passed
    except Exception as exc:
        log(f"Release check failed with exception: {exc}", level="ERROR")
        return False


def clean_temp_files(root: Path, dry_run: bool = True) -> dict[str, Any]:
    """Step 2: Clean runtime/ and artifacts/ directories."""
    cleaned: dict[str, Any] = {"dry_run": dry_run, "cleaned_dirs": [], "deleted_files": 0}

    for dirname in ["runtime", "artifacts"]:
        dpath = root / dirname
        if not dpath.is_dir():
            continue
        files = list(dpath.rglob("*"))
        file_count = sum(1 for f in files if f.is_file())
        log(f"{'Would clean' if dry_run else 'Cleaning'} {file_count} files from {dirname}/")

        if not dry_run:
            shutil.rmtree(dpath, ignore_errors=True)
            dpath.mkdir(exist_ok=True)

        cleaned["cleaned_dirs"].append(dirname)
        cleaned["deleted_files"] += file_count

    return cleaned


def collect_files(root: Path, excludes: list[str]) -> list[dict[str, Any]]:
    """Step 3+4: Collect all files to include in the release."""
    files: list[dict[str, Any]] = []

    for item in sorted(root.rglob("*")):
        if not item.is_file():
            continue

        try:
            rel_path = item.relative_to(root).as_posix()
        except ValueError:
            continue

        if should_exclude(rel_path, excludes):
            continue

        stat = item.stat()
        files.append({
            "path": rel_path,
            "size": stat.st_size,
            "sha256": compute_sha256(item),
            "mtime": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
        })

    return files


def generate_manifest(version: str, files: list[dict[str, Any]]) -> dict[str, Any]:
    """Generate release-manifest.json content."""
    total_size = sum(f["size"] for f in files)
    return {
        "manifest_version": "1.0",
        "release_version": version,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "file_count": len(files),
        "total_size_bytes": total_size,
        "files": files,
    }


def create_zip(dist_dir: Path, version: str, files: list[dict[str, Any]], root: Path) -> Path:
    """Step 6: Create the release zip archive."""
    zip_name = f"kimi-agent-pack-{version}.zip"
    zip_path = dist_dir / zip_name

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for file_info in files:
            src = root / file_info["path"]
            if src.is_file():
                zf.write(src, file_info["path"])

    log(f"Created zip: {zip_path} ({zip_path.stat().st_size:,} bytes)")
    return zip_path


def generate_release_report(
    version: str,
    check_passed: bool,
    clean_info: dict[str, Any],
    manifest: dict[str, Any],
    zip_path: Path,
) -> dict[str, Any]:
    """Step 7: Generate release-report.json."""
    return {
        "report_type": "release",
        "version": version,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "release_check": {"passed": check_passed},
        "cleanup": clean_info,
        "manifest": {
            "file_count": manifest["file_count"],
            "total_size_bytes": manifest["total_size_bytes"],
        },
        "package": {
            "zip_file": str(zip_path.name),
            "zip_size_bytes": zip_path.stat().st_size if zip_path.exists() else 0,
            "zip_path": str(zip_path),
        },
        "result": "PASS" if check_passed else "FAIL",
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Package L1 release for Kimi Agent Pack",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/package_l1_release.py --version v1.3.0-rc1
  python scripts/package_l1_release.py --version v1.3.0 --skip-check
        """,
    )
    parser.add_argument("--version", required=True, help="Release version (e.g., v1.3.0-rc1)")
    parser.add_argument("--skip-check", action="store_true", help="Skip release check step")
    parser.add_argument("--dry-run", action="store_true", default=True, help="Dry run (do not clean or copy)")
    parser.add_argument("--confirm", action="store_true", help="Actually perform cleaning and packaging")
    parser.add_argument("--excludes", nargs="*", default=None, help="Additional exclude patterns")
    args = parser.parse_args()

    dry_run = not args.confirm
    root = get_project_root()
    dist_dir = root / "dist"
    dist_dir.mkdir(exist_ok=True)

    print("=" * 50)
    print("  Kimi Agent Pack — Release Packager")
    print(f"  Version: {args.version}")
    print(f"  Dry Run: {dry_run}")
    print("=" * 50)
    print()

    # Step 1: Release Check
    check_passed = True
    if not args.skip_check:
        check_passed = run_release_check(root)
        if not check_passed and not args.confirm:
            log("Release check failed. Use --skip-check to bypass or fix issues.", level="ERROR")
            return 1
    else:
        log("Skipping release check (--skip-check)")

    # Step 2: Clean temp files
    clean_info = clean_temp_files(root, dry_run=dry_run)
    print()

    # Step 3+4: Collect files
    excludes = list(DEFAULT_EXCLUDES)
    if args.excludes:
        excludes.extend(args.excludes)

    log("Collecting files...")
    files = collect_files(root, excludes)
    log(f"Found {len(files)} files to include")

    # Step 5: Generate manifest
    manifest = generate_manifest(args.version, files)
    manifest_path = dist_dir / "release-manifest.json"
    if not dry_run:
        manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    log(f"{'Would write' if dry_run else 'Wrote'} manifest: {manifest_path}")

    # Step 6: Create zip
    if not dry_run:
        zip_path = create_zip(dist_dir, args.version, files, root)
    else:
        zip_name = f"kimi-agent-pack-{args.version}.zip"
        zip_path = dist_dir / zip_name
        log(f"[DRY-RUN] Would create zip: {zip_path}")
        log(f"[DRY-RUN] Would include {len(files)} files, {manifest['total_size_bytes']:,} bytes")

    # Step 7: Generate report
    report = generate_release_report(args.version, check_passed, clean_info, manifest, zip_path)
    report_path = dist_dir / "release-report.json"
    if not dry_run:
        report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    log(f"{'Would write' if dry_run else 'Wrote'} report: {report_path}")

    # Summary
    print()
    print("-" * 40)
    log(f"Release Check: {'PASS' if check_passed else 'FAIL'}")
    log(f"Files: {len(files)}")
    log(f"Size: {manifest['total_size_bytes']:,} bytes")
    log(f"Result: {report['result']}")

    return 0 if check_passed else 1


if __name__ == "__main__":
    sys.exit(main())
