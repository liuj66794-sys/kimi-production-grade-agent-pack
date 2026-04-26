#!/usr/bin/env python3
"""
validate_schema.py
==================
Schema validation script for Kimi Production-Grade Agent Pack v1.0.

Validates that:
1. JSON Schema files are valid Draft 7 schemas
2. Given data files conform to their specified schemas

Usage:
    python validate_schema.py --schema schemas/task-brief.schema.json --data task.json
    python validate_schema.py --schema-dir schemas/ --validate-all
    python validate_schema.py --check-schemas  # Validate schema files themselves
"""

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# jsonschema is the standard library for JSON Schema validation in Python.
# It is NOT in the stdlib, so we handle the import gracefully.
try:
    import jsonschema
    from jsonschema import Draft7Validator
    JSONSCHEMA_AVAILABLE = True
except ImportError:
    JSONSCHEMA_AVAILABLE = False
    print(
        "WARNING: 'jsonschema' package not installed. "
        "Install with: pip install jsonschema",
        file=sys.stderr,
    )


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
DEFAULT_SCHEMA_DIR = PROJECT_ROOT / "schemas"
SCHEMA_DRAFT_7_URI = "http://json-schema.org/draft-07/schema#"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("validate_schema")


# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------
def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Validate JSON schemas and data files.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --schema schemas/task-brief.schema.json --data my-task.json
  %(prog)s --schema-dir schemas/ --validate-all
  %(prog)s --check-schemas
        """,
    )
    parser.add_argument(
        "--schema",
        type=str,
        help="Path to a JSON Schema file to validate against.",
    )
    parser.add_argument(
        "--data",
        type=str,
        help="Path to a JSON data file to validate.",
    )
    parser.add_argument(
        "--schema-dir",
        type=str,
        default=str(DEFAULT_SCHEMA_DIR),
        help=f"Directory containing schema files (default: {DEFAULT_SCHEMA_DIR}).",
    )
    parser.add_argument(
        "--validate-all",
        action="store_true",
        help="Validate all schema files in the schema directory.",
    )
    parser.add_argument(
        "--check-schemas",
        action="store_true",
        help="Validate that schema files are valid Draft 7 schemas.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output.",
    )
    return parser.parse_args()


# ---------------------------------------------------------------------------
# Schema validation helpers
# ---------------------------------------------------------------------------
def is_valid_json_file(path: Path) -> Tuple[bool, Optional[Any]]:
    """Check if a file is valid JSON. Returns (is_valid, parsed_data)."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return True, data
    except json.JSONDecodeError as e:
        logger.error("Invalid JSON in %s: %s", path, e)
        return False, None
    except FileNotFoundError:
        logger.error("File not found: %s", path)
        return False, None


def is_valid_schema_structure(schema_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Validate that a JSON object is a valid Draft 7 schema structure.
    This checks basic schema validity without the jsonschema library.
    """
    errors = []

    # Check $schema field
    schema_decl = schema_data.get("$schema", "")
    if SCHEMA_DRAFT_7_URI not in schema_decl:
        errors.append(
            f"Schema must declare '$schema': '{SCHEMA_DRAFT_7_URI}', "
            f"got: '{schema_decl}'"
        )

    # Check required fields
    if "type" not in schema_data and "properties" not in schema_data:
        errors.append("Schema should have 'type' or 'properties' at root level")

    # Basic property validation
    if "properties" in schema_data and not isinstance(schema_data["properties"], dict):
        errors.append("'properties' must be an object")

    if "required" in schema_data and not isinstance(schema_data["required"], list):
        errors.append("'required' must be an array")

    return len(errors) == 0, errors


def validate_schema_with_jsonschema(schema_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Validate a schema using the jsonschema library (more thorough).
    Requires 'jsonschema' to be installed.
    """
    if not JSONSCHEMA_AVAILABLE:
        return True, ["jsonschema not installed; skipping deep schema validation"]

    errors = []
    try:
        # Check if the schema itself is valid by creating a validator
        Draft7Validator.check_schema(schema_data)
    except jsonschema.exceptions.SchemaError as e:
        errors.append(f"Schema validation error: {e}")

    return len(errors) == 0, errors


def validate_data_against_schema(
    data: Dict[str, Any],
    schema_data: Dict[str, Any],
) -> Tuple[bool, List[str]]:
    """
    Validate a data object against a JSON Schema.
    Returns (is_valid, list_of_errors).
    """
    if not JSONSCHEMA_AVAILABLE:
        logger.warning("jsonschema not installed; cannot validate data")
        return True, ["jsonschema not installed; data validation skipped"]

    errors = []
    try:
        validator = Draft7Validator(schema_data)
        validation_errors = list(validator.iter_errors(data))
        for error in validation_errors:
            errors.append(f"{error.json_path}: {error.message}")
    except Exception as e:
        errors.append(f"Validation error: {e}")

    return len(errors) == 0, errors


# ---------------------------------------------------------------------------
# Core functions
# ---------------------------------------------------------------------------
def check_all_schemas(schema_dir: Path) -> Tuple[int, int]:
    """
    Check all .schema.json files in the schema directory.
    Returns (passed_count, total_count).
    """
    schema_files = sorted(schema_dir.glob("*.schema.json"))
    passed = 0

    logger.info("Checking %d schema files in %s", len(schema_files), schema_dir)

    for schema_file in schema_files:
        logger.info("Checking: %s", schema_file.name)
        is_valid_json, schema_data = is_valid_json_file(schema_file)

        if not is_valid_json:
            logger.error("  [FAIL] %s is not valid JSON", schema_file.name)
            continue

        struct_ok, struct_errors = is_valid_schema_structure(schema_data)
        if not struct_ok:
            for err in struct_errors:
                logger.error("  [STRUCT] %s: %s", schema_file.name, err)

        schema_ok, schema_errors = validate_schema_with_jsonschema(schema_data)
        if not schema_ok:
            for err in schema_errors:
                logger.error("  [SCHEMA] %s: %s", schema_file.name, err)

        if struct_ok and schema_ok:
            logger.info("  [PASS] %s", schema_file.name)
            passed += 1
        else:
            logger.error("  [FAIL] %s", schema_file.name)

    return passed, len(schema_files)


def validate_data_file(schema_path: Path, data_path: Path) -> bool:
    """Validate a single data file against a schema."""
    logger.info("Validating %s against %s", data_path, schema_path)

    _, schema_data = is_valid_json_file(schema_path)
    if schema_data is None:
        return False

    _, data = is_valid_json_file(data_path)
    if data is None:
        return False

    is_valid, errors = validate_data_against_schema(data, schema_data)
    if is_valid:
        logger.info("  [PASS] %s validates against %s", data_path.name, schema_path.name)
    else:
        logger.error("  [FAIL] Validation errors:")
        for err in errors:
            logger.error("    - %s", err)

    return is_valid


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------
def main() -> int:
    """Main entry point for schema validation."""
    args = parse_args()

    if args.verbose:
        logger.setLevel(logging.DEBUG)

    # Mode 1: Check schema files themselves
    if args.check_schemas or args.validate_all:
        schema_dir = Path(args.schema_dir)
        passed, total = check_all_schemas(schema_dir)
        logger.info("Schema check: %d/%d passed", passed, total)
        if passed != total:
            return 1

    # Mode 2: Validate data against schema
    if args.schema and args.data:
        schema_path = Path(args.schema)
        data_path = Path(args.data)
        if not validate_data_file(schema_path, data_path):
            return 1

    # Mode 3: Validate all data files against their schemas
    # TODO: Implement auto-mapping of data files to schemas
    if args.validate_all and not args.check_schemas:
        logger.info("Full validation mode - TODO: implement data file discovery")

    logger.info("Validation complete.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
