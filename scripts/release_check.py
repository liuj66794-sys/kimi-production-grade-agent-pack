#!/usr/bin/env python3
"""
release_check.py — Release validation script for Kimi Agent Pack.

Usage:
    python scripts/release_check.py --level l1
    python scripts/release_check.py --level l1 --strict

Checks:
    - Directory structure completeness
    - Required file existence
    - Python script syntax (py_compile)
    - JSON Schema validity
    - VERSION format
    - SKILL.md frontmatter
    - --strict: agent config completeness, skill references, schema examples, main() functions

Output:
    - Console report
    - release-check-report.json
"""

from __future__ import annotations

import argparse
import json
import os
import py_compile
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

REQUIRED_DIRECTORIES: list[str] = [
    "agents",
    "skills",
    "schemas",
    "scripts",
    "evals",
    "examples",
    "docs",
]

REQUIRED_FILES: list[str] = [
    "README.md",
    "QUICKSTART.md",
    "DESIGN.md",
    "AGENTS.md",
    "SKILL.md",
    "VERSION",
    "requirements.txt",
]

REQUIRED_SCHEMAS: list[str] = [
    "schemas/error-envelope.json",
    "schemas/task-event.json",
]

PYTHON_SCRIPT_DIRS: list[str] = [
    "scripts",
    "evals",
]

L1_AGENTS: list[str] = [
    "agents/deep-research.yaml",
    "agents/ppt-agent.yaml",
    "agents/spreadsheet-agent.yaml",
    "agents/codebase-fix-agent.yaml",
    "agents/document-to-skill.yaml",
]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_project_root() -> Path:
    """Return the project root (parent of scripts/ directory)."""
    return Path(__file__).resolve().parent.parent


def log(msg: str, level: str = "INFO") -> None:
    """Print a formatted log message."""
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")
    print(f"[{timestamp}] [{level}] {msg}")


def check_result(name: str, passed: bool, details: str = "") -> dict[str, Any]:
    """Create a structured check result."""
    return {
        "name": name,
        "status": "PASS" if passed else "FAIL",
        "details": details,
    }


# ---------------------------------------------------------------------------
# Individual Checks
# ---------------------------------------------------------------------------

def check_directory_structure(root: Path) -> dict[str, Any]:
    """Check that all required directories exist."""
    missing: list[str] = []
    for dirname in REQUIRED_DIRECTORIES:
        dpath = root / dirname
        if not dpath.is_dir():
            missing.append(dirname)
    passed = len(missing) == 0
    details = f"Missing: {missing}" if missing else "All required directories present"
    return check_result("Directory Structure", passed, details)


def check_required_files(root: Path) -> dict[str, Any]:
    """Check that all required top-level files exist."""
    missing: list[str] = []
    for filename in REQUIRED_FILES:
        fpath = root / filename
        if not fpath.is_file():
            missing.append(filename)
    passed = len(missing) == 0
    details = f"Missing: {missing}" if missing else "All required files present"
    return check_result("Required Files", passed, details)


def check_python_syntax(root: Path) -> dict[str, Any]:
    """Compile-check all .py files under scripts/ and evals/."""
    errors: list[str] = []
    for dirname in PYTHON_SCRIPT_DIRS:
        dpath = root / dirname
        if not dpath.is_dir():
            continue
        for pyfile in sorted(dpath.rglob("*.py")):
            try:
                py_compile.compile(str(pyfile), doraise=True)
            except py_compile.PyCompileError as exc:
                errors.append(f"{pyfile.relative_to(root)}: {exc}")
    passed = len(errors) == 0
    details = "; ".join(errors) if errors else f"All Python files compile OK"
    return check_result("Python Syntax", passed, details)


def check_json_schemas(root: Path) -> dict[str, Any]:
    """Validate that JSON schema files are valid JSON and contain 'type'/'properties'."""
    errors: list[str] = []
    schema_dir = root / "schemas"
    if not schema_dir.is_dir():
        return check_result("JSON Schemas", False, "schemas/ directory missing")

    for schema_file in sorted(schema_dir.glob("*.schema.json")):
        try:
            content = schema_file.read_text(encoding="utf-8")
            data = json.loads(content)
            if "type" not in data and "properties" not in data and "$schema" not in data:
                errors.append(f"{schema_file.name}: missing schema keywords")
        except json.JSONDecodeError as exc:
            errors.append(f"{schema_file.name}: invalid JSON - {exc}")

    passed = len(errors) == 0
    details = "; ".join(errors) if errors else "All schemas valid"
    return check_result("JSON Schemas", passed, details)


def check_version_format(root: Path) -> dict[str, Any]:
    """Check VERSION file format (semver-like)."""
    vfile = root / "VERSION"
    if not vfile.is_file():
        return check_result("VERSION Format", False, "VERSION file missing")
    version = vfile.read_text(encoding="utf-8").strip()
    # Accept v1.2.3 or 1.2.3 format
    import re
    if not re.match(r"^v?\d+\.\d+\.\d+(-\w+)?$", version):
        return check_result("VERSION Format", False, f"Invalid format: '{version}'")
    return check_result("VERSION Format", True, f"Version: {version}")


def check_skill_frontmatter(root: Path) -> dict[str, Any]:
    """Check that SKILL.md contains YAML frontmatter."""
    skill_file = root / "SKILL.md"
    if not skill_file.is_file():
        return check_result("SKILL.md Frontmatter", False, "SKILL.md not found")
    content = skill_file.read_text(encoding="utf-8")
    if not content.startswith("---"):
        return check_result("SKILL.md Frontmatter", False, "Missing YAML frontmatter (---)")
    # Check for required fields in frontmatter
    try:
        fm_end = content.index("---", 3)
        frontmatter = content[3:fm_end]
        required_keys = ["name", "version"]
        missing = [k for k in required_keys if k not in frontmatter]
        if missing:
            return check_result("SKILL.md Frontmatter", False, f"Missing keys: {missing}")
    except ValueError:
        return check_result("SKILL.md Frontmatter", False, "Unclosed frontmatter block")
    return check_result("SKILL.md Frontmatter", True, "Frontmatter valid")


# ---------------------------------------------------------------------------
# Strict-mode Checks
# ---------------------------------------------------------------------------

def check_l1_agents(root: Path) -> dict[str, Any]:
    """Check all L1 agent configurations are complete."""
    errors: list[str] = []
    for agent_path in L1_AGENTS:
        fpath = root / agent_path
        if not fpath.is_file():
            errors.append(f"{agent_path}: missing")
            continue
        content = fpath.read_text(encoding="utf-8")
        required_sections = ["name", "version", "skills"]
        for section in required_sections:
            if section not in content:
                errors.append(f"{agent_path}: missing section '{section}'")
    passed = len(errors) == 0
    details = "; ".join(errors) if errors else "All L1 agents configured"
    return check_result("L1 Agent Config", passed, details)


def check_skill_references(root: Path) -> dict[str, Any]:
    """Check that each core skill has references in agents/."""
    skills_dir = root / "skills"
    agents_dir = root / "agents"
    if not skills_dir.is_dir():
        return check_result("Skill References", False, "skills/ directory missing")
    if not agents_dir.is_dir():
        return check_result("Skill References", False, "agents/ directory missing")

    skill_names = {d.name for d in skills_dir.iterdir() if d.is_dir()}
    if not skill_names:
        return check_result("Skill References", True, "No skills found (empty)")

    # Check if any agent references each skill
    unreferenced: list[str] = []
    for skill_name in skill_names:
        referenced = False
        for agent_file in agents_dir.glob("*.yaml"):
            content = agent_file.read_text(encoding="utf-8")
            if skill_name in content:
                referenced = True
                break
        if not referenced:
            unreferenced.append(skill_name)

    passed = len(unreferenced) == 0
    details = f"Unreferenced: {unreferenced}" if unreferenced else "All skills referenced"
    return check_result("Skill References", passed, details)


def check_schema_examples(root: Path) -> dict[str, Any]:
    """Check that schemas have example fields or example files."""
    schema_dir = root / "schemas"
    if not schema_dir.is_dir():
        return check_result("Schema Examples", False, "schemas/ directory missing")

    missing_examples: list[str] = []
    for schema_file in sorted(schema_dir.glob("*.schema.json")):
        content = schema_file.read_text(encoding="utf-8")
        data = json.loads(content)
        # Check for examples key or look for companion example file
        has_example = "examples" in data or "example" in data
        example_file = schema_file.with_suffix(".example.json")
        if not has_example and not example_file.is_file():
            missing_examples.append(schema_file.name)

    passed = len(missing_examples) == 0
    details = f"Missing examples: {missing_examples}" if missing_examples else "All schemas have examples"
    return check_result("Schema Examples", passed, details)


def check_scripts_have_main(root: Path) -> dict[str, Any]:
    """Check that all scripts have a main() function."""
    scripts_dir = root / "scripts"
    if not scripts_dir.is_dir():
        return check_result("Scripts main()", False, "scripts/ directory missing")

    missing_main: list[str] = []
    for pyfile in sorted(scripts_dir.glob("*.py")):
        content = pyfile.read_text(encoding="utf-8")
        if "def main(" not in content:
            missing_main.append(pyfile.name)

    passed = len(missing_main) == 0
    details = f"Missing main(): {missing_main}" if missing_main else "All scripts have main()"
    return check_result("Scripts main()", passed, details)


# ---------------------------------------------------------------------------
# Report Generation
# ---------------------------------------------------------------------------

def generate_report(results: list[dict[str, Any]], version: str, level: str, strict: bool) -> dict[str, Any]:
    """Generate the structured JSON report."""
    total = len(results)
    passed = sum(1 for r in results if r["status"] == "PASS")
    failed = total - passed
    return {
        "report_type": "release-check",
        "version": version,
        "level": level,
        "strict": strict,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "total": total,
            "passed": passed,
            "failed": failed,
            "result": "PASS" if failed == 0 else "FAIL",
        },
        "checks": results,
    }


def write_report(report: dict[str, Any], root: Path) -> Path:
    """Write report to release-check-report.json."""
    report_path = root / "release-check-report.json"
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    return report_path


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Release check script for Kimi Agent Pack",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/release_check.py --level l1
  python scripts/release_check.py --level l1 --strict
        """,
    )
    parser.add_argument("--level", default="l1", choices=["l1", "l2"], help="Release level to check")
    parser.add_argument("--strict", action="store_true", help="Enable strict mode checks")
    parser.add_argument("--quiet", action="store_true", help="Minimal output")
    args = parser.parse_args()

    root = get_project_root()
    version = "unknown"
    vfile = root / "VERSION"
    if vfile.is_file():
        version = vfile.read_text(encoding="utf-8").strip()

    if not args.quiet:
        print("=" * 50)
        print("  Kimi Agent Pack — Release Check")
        print(f"  Version: {version}")
        print(f"  Level: {args.level}")
        print(f"  Strict: {args.strict}")
        print("=" * 50)

    results: list[dict[str, Any]] = []

    # Basic checks (always run)
    results.append(check_directory_structure(root))
    results.append(check_required_files(root))
    results.append(check_python_syntax(root))
    results.append(check_json_schemas(root))
    results.append(check_version_format(root))
    results.append(check_skill_frontmatter(root))

    # Strict-mode checks
    if args.strict:
        results.append(check_l1_agents(root))
        results.append(check_skill_references(root))
        results.append(check_schema_examples(root))
        results.append(check_scripts_have_main(root))

    # Display results
    if not args.quiet:
        print()
        for r in results:
            status_icon = "PASS" if r["status"] == "PASS" else "FAIL"
            level_str = "INFO" if r["status"] == "PASS" else "ERROR"
            log(f"[{status_icon}] {r['name']}: {r['details']}", level=level_str)

    # Generate and write report
    report = generate_report(results, version, args.level, args.strict)
    report_path = write_report(report, root)

    # Summary
    summary = report["summary"]
    if not args.quiet:
        print()
        print("-" * 40)
        log(f"Result: {summary['result']} ({summary['passed']}/{summary['total']} checks)")
        log(f"Report written to: {report_path}")

    return 0 if summary["failed"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
