#!/usr/bin/env python3
"""
package_artifacts.py
====================
Artifact packaging script for Kimi Production-Grade Agent Pack v1.0.

Collects artifacts from a specified directory, generates an artifact manifest,
and packages everything into a zip file.

Usage:
    python package_artifacts.py --input ./output --output ./releases/v1.0.0.zip
    python package_artifacts.py --input ./output --manifest-only
    python package_artifacts.py --input ./output --output ./release.zip --exclude "*.tmp"
"""

import argparse
import hashlib
import json
import logging
import os
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
DEFAULT_INPUT_DIR = PROJECT_ROOT / "output"
DEFAULT_OUTPUT_FILE = PROJECT_ROOT / "releases" / "agent-pack-artifacts.zip"
MANIFEST_FILENAME = "artifact-manifest.json"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("package_artifacts")


# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------
def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Package agent artifacts into a distributable zip.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --input ./output --output ./release.zip
  %(prog)s --input ./output --manifest-only
  %(prog)s --input ./output --output release.zip --exclude "*.log" "*.tmp"
        """,
    )
    parser.add_argument(
        "--input",
        type=str,
        required=True,
        help="Directory containing artifacts to package.",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=str(DEFAULT_OUTPUT_FILE),
        help=f"Output zip file path (default: {DEFAULT_OUTPUT_FILE}).",
    )
    parser.add_argument(
        "--manifest-only",
        action="store_true",
        help="Only generate the artifact manifest without creating a zip.",
    )
    parser.add_argument(
        "--exclude",
        nargs="*",
        default=["*.tmp", "*.log", ".gitkeep"],
        help="Patterns to exclude from packaging (default: *.tmp, *.log, .gitkeep).",
    )
    parser.add_argument(
        "--include-schemas",
        action="store_true",
        help="Include schema files in the package.",
    )
    parser.add_argument(
        "--version",
        type=str,
        default="1.0.0",
        help="Version tag for the artifact package (default: 1.0.0).",
    )
    return parser.parse_args()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def should_exclude(file_path: Path, exclude_patterns: List[str]) -> bool:
    """Check if a file matches any exclusion pattern."""
    name = file_path.name
    for pattern in exclude_patterns:
        if pattern.startswith("*"):
            suffix = pattern.lstrip("*")
            if name.endswith(suffix):
                return True
        elif name == pattern:
            return True
    return False


def compute_file_hash(file_path: Path) -> str:
    """Compute SHA-256 hash of a file."""
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


def collect_artifacts(
    input_dir: Path,
    exclude_patterns: List[str],
) -> List[Dict[str, Any]]:
    """
    Recursively collect all artifacts from the input directory.

    Returns a list of artifact metadata dicts with:
        - path: relative path within the input directory
        - size_bytes: file size
        - hash: SHA-256 hash (truncated)
        - type: inferred artifact type
        - description: auto-generated description
    """
    artifacts = []

    if not input_dir.exists():
        logger.error("Input directory does not exist: %s", input_dir)
        return artifacts

    for root, _, files in os.walk(input_dir):
        for filename in files:
            file_path = Path(root) / filename
            rel_path = file_path.relative_to(input_dir)

            if should_exclude(file_path, exclude_patterns):
                logger.debug("Excluding: %s", rel_path)
                continue

            file_size = file_path.stat().st_size
            file_hash = compute_file_hash(file_path)

            # Infer artifact type from extension
            ext = file_path.suffix.lower()
            type_map = {
                ".json": "json",
                ".md": "markdown",
                ".py": "python",
                ".yaml": "yaml",
                ".yml": "yaml",
                ".csv": "table",
                ".txt": "text",
                ".html": "html",
                ".png": "image",
                ".jpg": "image",
                ".jpeg": "image",
                ".pptx": "presentation",
            }
            artifact_type = type_map.get(ext, "file")

            artifacts.append({
                "path": str(rel_path),
                "size_bytes": file_size,
                "hash": file_hash,
                "type": artifact_type,
                "description": f"{artifact_type} artifact: {rel_path}",
            })

    logger.info("Collected %d artifacts from %s", len(artifacts), input_dir)
    return artifacts


def generate_manifest(
    artifacts: List[Dict[str, Any]],
    version: str,
    input_dir: Path,
) -> Dict[str, Any]:
    """Generate the artifact-manifest.json structure."""
    total_size = sum(a["size_bytes"] for a in artifacts)

    return {
        "manifest_version": "1.0",
        "pack_version": version,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_directory": str(input_dir),
        "total_artifacts": len(artifacts),
        "total_size_bytes": total_size,
        "artifacts": artifacts,
    }


def create_zip_package(
    input_dir: Path,
    output_path: Path,
    manifest: Dict[str, Any],
    exclude_patterns: List[str],
) -> None:
    """Create a zip archive containing all artifacts and the manifest."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
        # 1. Write the manifest
        manifest_content = json.dumps(manifest, indent=2, ensure_ascii=False)
        zf.writestr(MANIFEST_FILENAME, manifest_content)
        logger.info("Added %s to zip", MANIFEST_FILENAME)

        # 2. Write all artifact files
        for artifact in manifest["artifacts"]:
            file_path = input_dir / artifact["path"]
            if file_path.exists():
                zf.write(file_path, artifact["path"])
                logger.debug("Added: %s", artifact["path"])
            else:
                logger.warning("File not found, skipping: %s", file_path)

    logger.info("Created zip package: %s (%d bytes)", output_path, output_path.stat().st_size)


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------
def main() -> int:
    """Main entry point for artifact packaging."""
    args = parse_args()
    input_dir = Path(args.input)
    output_path = Path(args.output)

    logger.info("=" * 60)
    logger.info("Artifact Packager v%s", args.version)
    logger.info("Input: %s | Output: %s", input_dir, output_path)
    logger.info("=" * 60)

    # 1. Collect artifacts
    artifacts = collect_artifacts(input_dir, args.exclude)
    if not artifacts:
        logger.warning("No artifacts found in %s", input_dir)
        return 1

    # 2. Generate manifest
    manifest = generate_manifest(artifacts, args.version, input_dir)
    manifest_path = input_dir / MANIFEST_FILENAME
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    logger.info("Generated manifest: %s", manifest_path)

    if args.manifest_only:
        logger.info("Manifest-only mode; skipping zip creation.")
        return 0

    # 3. Create zip package
    create_zip_package(input_dir, output_path, manifest, args.exclude)

    # 4. Summary
    logger.info("-" * 60)
    logger.info("Packaging complete:")
    logger.info("  Artifacts: %d", len(artifacts))
    logger.info("  Total size: %d bytes", manifest["total_size_bytes"])
    logger.info("  Output: %s", output_path)
    logger.info("-" * 60)

    return 0


if __name__ == "__main__":
    sys.exit(main())
