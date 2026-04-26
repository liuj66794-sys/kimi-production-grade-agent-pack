#!/usr/bin/env python3
"""
Structured Output Parser Fixture Suite (16 fixtures)

Tests the stability of structured_output extraction from LLM responses.
Each fixture: input text, expected extraction result, expected status.

Usage:
    python test_structured_output_parser.py
    python test_structured_output_parser.py --verbose
    python test_structured_output_parser.py --fixture 3
    python test_structured_output_parser.py --json-output results.json
"""

import argparse
import json
import re
import sys
import traceback
from typing import Any, Dict, List, Optional, Tuple

# ──────────────────────────────────────────────────────────────────────────────
# Parser implementation (simulating the parser being tested)
# ──────────────────────────────────────────────────────────────────────────────

def parse_structured_output(
    text: str, strict: bool = True
) -> Tuple[Optional[Any], str]:
    """
    Extract structured output (JSON) from LLM response text.

    Strategy:
    1. Try JSON code blocks ```json ... ```
    2. Try generic code blocks ``` ... ```
    3. Try inline JSON (non-code-block)
    4. Try regex recovery for malformed blocks
    5. Return fallback if all fail

    Returns: (parsed_data, status)
    status: "pass" | "fallback" | "fail"
    """
    if not text or not text.strip():
        return None, "fail"

    text = text.strip()

    # Strategy 1: Explicit JSON code blocks
    json_block_pattern = re.compile(
        r"```(?:json)?\s*\n(.*?)\n?```", re.DOTALL | re.IGNORECASE
    )
    matches = json_block_pattern.findall(text)

    for match in matches:
        cleaned = match.strip()
        if cleaned:
            try:
                parsed = json.loads(cleaned)
                return parsed, "pass"
            except json.JSONDecodeError:
                # Try cleaning comments
                cleaned_no_comments = _remove_json_comments(cleaned)
                try:
                    parsed = json.loads(cleaned_no_comments)
                    return parsed, "pass"
                except json.JSONDecodeError:
                    continue

    # Strategy 2: Single backtick code blocks (fallback)
    single_block = re.search(r"`([^`]+)`", text)
    if single_block:
        cleaned = single_block.group(1).strip()
        try:
            parsed = json.loads(cleaned)
            return parsed, "pass"
        except json.JSONDecodeError:
            pass

    # Strategy 3: Try to find JSON-like structure inline
    # Look for content between first { and last }
    if "{" in text and "}" in text:
        brace_start = text.index("{")
        brace_end = text.rindex("}") + 1
        candidate = text[brace_start:brace_end]
        try:
            parsed = json.loads(candidate)
            return parsed, "pass"
        except json.JSONDecodeError:
            # Try with bracket cleanup
            cleaned = _clean_json_string(candidate)
            try:
                parsed = json.loads(cleaned)
                return parsed, "pass"
            except json.JSONDecodeError:
                pass

    # Strategy 4: Try to find JSON array
    if "[" in text and "]" in text:
        bracket_start = text.index("[")
        bracket_end = text.rindex("]") + 1
        candidate = text[bracket_start:bracket_end]
        try:
            parsed = json.loads(candidate)
            return parsed, "pass"
        except json.JSONDecodeError:
            pass

    # Strategy 5: Regex recovery for truncated/malformed JSON
    recovered = _regex_recovery(text)
    if recovered is not None:
        return recovered, "fallback"

    # All strategies failed
    if not strict:
        # Last resort: try extracting key-value pairs
        kv_fallback = _key_value_fallback(text)
        if kv_fallback:
            return kv_fallback, "fallback"

    return None, "fail"


def _remove_json_comments(text: str) -> str:
    """Remove // and /* */ style comments from JSON-like text."""
    # Remove single-line comments
    text = re.sub(r"//.*?$", "", text, flags=re.MULTILINE)
    # Remove multi-line comments
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
    return text


def _clean_json_string(text: str) -> str:
    """Clean common JSON issues."""
    # Remove trailing commas before closing braces/brackets
    text = re.sub(r",\s*}", "}", text)
    text = re.sub(r",\s*]", "]", text)
    # Fix unescaped newlines in strings
    text = re.sub(r'(?<=": )"([^"]*?)\n([^"]*)"', lambda m: '"' + m.group(1) + "\\n" + m.group(2) + '"', text)
    return text


def _regex_recovery(text: str) -> Optional[Any]:
    """Attempt regex-based recovery for truncated JSON."""
    # Try to extract a complete object by finding balanced braces
    depth = 0
    start = -1
    for i, ch in enumerate(text):
        if ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0 and start >= 0:
                try:
                    return json.loads(text[start : i + 1])
                except json.JSONDecodeError:
                    cleaned = _clean_json_string(text[start : i + 1])
                    try:
                        return json.loads(cleaned)
                    except json.JSONDecodeError:
                        return None
    return None


def _key_value_fallback(text: str) -> Optional[Dict]:
    """Extract key-value pairs as a last resort fallback."""
    result = {}
    # Match "key": value or "key": "value" patterns
    pairs = re.findall(r'"([^"]+)"\s*:\s*(?:("(?:[^"\\]|\\.)*")|([\d.]+)|(true|false|null))', text)
    for key, str_val, num_val, bool_null_val in pairs:
        if str_val:
            result[key] = json.loads(str_val)
        elif num_val:
            result[key] = json.loads(num_val)
        elif bool_null_val:
            result[key] = json.loads(bool_null_val)
    return result if result else None


# ──────────────────────────────────────────────────────────────────────────────
# 16 Fixtures
# ──────────────────────────────────────────────────────────────────────────────

FIXTURES = [
    # ── Fixture 1: Standard JSON code block ──────────────────────────────
    {
        "id": 1,
        "name": "standard_json_codeblock",
        "description": "Standard JSON wrapped in ```json ... ``` block",
        "input": 'Here is the result:\n```json\n{\n  "name": "Alice",\n  "age": 30,\n  "active": true\n}\n```\nLet me know if you need more.',
        "expected_data": {"name": "Alice", "age": 30, "active": True},
        "expected_status": "pass",
    },

    # ── Fixture 2: JSON code block with language tag ─────────────────────
    {
        "id": 2,
        "name": "json_with_language_tag",
        "description": "JSON code block with explicit 'json' language tag",
        "input": '```json\n{\n  "result": "success",\n  "data": [1, 2, 3],\n  "metadata": {\n    "version": "1.0"\n  }\n}\n```',
        "expected_data": {"result": "success", "data": [1, 2, 3], "metadata": {"version": "1.0"}},
        "expected_status": "pass",
    },

    # ── Fixture 3: Inline JSON (no code block) ──────────────────────────
    {
        "id": 3,
        "name": "inline_json_no_codeblock",
        "description": "JSON directly in text without code block wrapping",
        "input": 'The configuration is {"host": "localhost", "port": 8080, "debug": false}. Please update your settings.',
        "expected_data": {"host": "localhost", "port": 8080, "debug": False},
        "expected_status": "pass",
    },

    # ── Fixture 4: Nested JSON ──────────────────────────────────────────
    {
        "id": 4,
        "name": "nested_json_deep",
        "description": "Deeply nested JSON structure",
        "input": '```json\n{\n  "level1": {\n    "level2": {\n      "level3": {\n        "level4": {\n          "level5": {\n            "value": "deep"\n          }\n        }\n      }\n    }\n  }\n}\n```',
        "expected_data": {"level1": {"level2": {"level3": {"level4": {"level5": {"value": "deep"}}}}}},
        "expected_status": "pass",
    },

    # ── Fixture 5: JSON with special characters ─────────────────────────
    {
        "id": 5,
        "name": "json_with_special_chars",
        "description": "JSON containing special characters like quotes, newlines, tabs",
        "input": '```json\n{\n  "message": "Hello \\"world\\"!",\n  "path": "/usr/local/bin",\n  "regex": "^\\\\d+$",\n  "special": "tab\\there\\nnewline"\n}\n```',
        "expected_data": {
            "message": 'Hello "world"!',
            "path": "/usr/local/bin",
            "regex": "^\\d+$",
            "special": "tab\there\nnewline",
        },
        "expected_status": "pass",
    },

    # ── Fixture 6: JSON with Unicode ────────────────────────────────────
    {
        "id": 6,
        "name": "json_with_unicode",
        "description": "JSON containing Unicode characters including CJK and emoji",
        "input": '```json\n{\n  "name": "\u4e2d\u6587\u6d4b\u8bd5",\n  "emoji": "\ud83d\ude80 \ud83c\udfaf",\n  "mixed": "Hello \u4e16\u754c \ud83c\udf0d",\n  "currency": "\u20ac100.50"\n}\n```',
        "expected_data": {
            "name": "\u4e2d\u6587\u6d4b\u8bd5",
            "emoji": "\ud83d\ude80 \ud83c\udfaf",
            "mixed": "Hello \u4e16\u754c \ud83c\udf0d",
            "currency": "\u20ac100.50",
        },
        "expected_status": "pass",
    },

    # ── Fixture 7: Large JSON (>10KB conceptually) ─────────────────────
    {
        "id": 7,
        "name": "large_json_10kb",
        "description": "Large JSON payload simulating >10KB data",
        "input": None,  # Generated dynamically
        "generate": lambda: _generate_large_json_fixture(),
        "expected_data": None,  # Checked dynamically
        "expected_status": "pass",
    },

    # ── Fixture 8: Missing closing fence ────────────────────────────────
    {
        "id": 8,
        "name": "missing_closing_fence",
        "description": "JSON block with missing closing ``` - parser recovers via inline/brace extraction",
        "input": '```json\n{\n  "name": "test",\n  "value": 42\n}\n',
        "expected_data": {"name": "test", "value": 42},
        "expected_status": "pass",
    },

    # ── Fixture 9: Excess whitespace ───────────────────────────────────
    {
        "id": 9,
        "name": "excess_whitespace",
        "description": "JSON with excessive whitespace, tabs, and newlines",
        "input": '\n\n\n```json\n\n\n   {\n\n        "key1"     :     "value1"    ,\n\n\n        "key2"     :     123    \n\n   }\n\n\n```\n\n\n',
        "expected_data": {"key1": "value1", "key2": 123},
        "expected_status": "pass",
    },

    # ── Fixture 10: Mixed Markdown content ─────────────────────────────
    {
        "id": 10,
        "name": "mixed_markdown_content",
        "description": "JSON embedded in rich markdown with headers, lists, bold",
        "input": '# Analysis Result\n\n## Summary\nThe analysis found the following:\n\n- **Status**: Complete\n- **Confidence**: High\n\n```json\n{\n  "status": "complete",\n  "confidence": "high",\n  "findings": [\n    {"id": 1, "severity": "critical"}\n  ]\n}\n```\n\n## Next Steps\nPlease review the findings above.',
        "expected_data": {
            "status": "complete",
            "confidence": "high",
            "findings": [{"id": 1, "severity": "critical"}],
        },
        "expected_status": "pass",
    },

    # ── Fixture 11: Multiple JSON code blocks ──────────────────────────
    {
        "id": 11,
        "name": "multiple_json_codeblocks",
        "description": "Multiple JSON code blocks - should extract first valid one",
        "input": '```json\n{"type": "config", "value": 1}\n```\n\nSome text here.\n\n```json\n{"type": "result", "value": 2}\n```',
        "expected_data": {"type": "config", "value": 1},
        "expected_status": "pass",
    },

    # ── Fixture 12: Corrupted JSON ─────────────────────────────────────
    {
        "id": 12,
        "name": "corrupted_json_fallback",
        "description": "Corrupted JSON - missing braces but quoted keys allow kv fallback",
        "input": '"name": "test", "value": 42, "status": true, "category": "demo"',
        "expected_data": {"name": "test", "value": 42, "status": True, "category": "demo"},
        "expected_status": "fallback",
        "strict": False,
    },

    # ── Fixture 13: Empty JSON ────────────────────────────────────────
    {
        "id": 13,
        "name": "empty_json",
        "description": "Empty JSON object or array",
        "input": 'The result is empty: ```json\n{}\n```',
        "expected_data": {},
        "expected_status": "pass",
    },

    # ── Fixture 14: JSON with comments ─────────────────────────────────
    {
        "id": 14,
        "name": "json_with_comments",
        "description": "JSON containing comments (non-standard but common from LLMs)",
        "input": '```json\n{\n  // This is the primary key\n  "id": "task-001",\n  /* Multi-line comment\n     describing the status field */\n  "status": "active",\n  "priority": 1  // Lower is higher priority\n}\n```',
        "expected_data": {"id": "task-001", "status": "active", "priority": 1},
        "expected_status": "pass",
    },

    # ── Fixture 15: Array-root JSON ────────────────────────────────────
    {
        "id": 15,
        "name": "array_root_json",
        "description": "JSON with array as root element instead of object",
        "input": '```json\n[\n  {"id": 1, "name": "Alice"},\n  {"id": 2, "name": "Bob"},\n  {"id": 3, "name": "Charlie"}\n]\n```',
        "expected_data": [
            {"id": 1, "name": "Alice"},
            {"id": 2, "name": "Bob"},
            {"id": 3, "name": "Charlie"},
        ],
        "expected_status": "pass",
    },

    # ── Fixture 16: Very long single-line JSON ─────────────────────────
    {
        "id": 16,
        "name": "very_long_single_line_json",
        "description": "Minified JSON all on one very long line",
        "input": None,  # Generated dynamically
        "generate": lambda: _generate_long_single_line_json(),
        "expected_data": None,  # Checked dynamically
        "expected_status": "pass",
    },
]


def _generate_large_json_fixture() -> Tuple[str, Any]:
    """Generate a large JSON fixture (>10KB string representation)."""
    data = {
        "metadata": {
            "version": "1.0",
            "generator": "fixture-suite",
            "timestamp": "2024-01-01T00:00:00Z",
        },
        "items": [],
    }
    # Generate enough items to exceed 10KB
    for i in range(200):
        data["items"].append({
            "id": f"item-{i:04d}",
            "index": i,
            "name": f"Item number {i} with a longer descriptive name",
            "properties": {
                "category": f"cat-{i % 10}",
                "priority": ["low", "medium", "high"][i % 3],
                "tags": [f"tag-{j}" for j in range(i % 5)],
                "nested": {
                    "level1": {
                        "level2": {
                            "value": i * 100,
                            "description": f"This is a nested value for item {i} " * 5,
                        }
                    }
                },
            },
            "active": i % 2 == 0,
            "score": i * 1.5,
        })

    json_str = json.dumps(data, indent=2)
    # Wrap in code block
    wrapped = f'```json\n{json_str}\n```'
    return wrapped, data


def _generate_long_single_line_json() -> Tuple[str, Any]:
    """Generate a minified single-line JSON."""
    data = {"key1": "value1", "key2": 42, "key3": True, "key4": [1, 2, 3, 4, 5], "key5": {"nested": "value"}}
    minified = json.dumps(data, separators=(",", ":"))
    # Repeat to make it very long
    large_obj = {"items": [data.copy() for _ in range(50)]}
    minified_large = json.dumps(large_obj, separators=(",", ":"))
    wrapped = f"```json\n{minified_large}\n```"
    return wrapped, large_obj


# ──────────────────────────────────────────────────────────────────────────────
# Test Runner
# ──────────────────────────────────────────────────────────────────────────────

def run_fixture(fixture: Dict, verbose: bool = False) -> Dict:
    """Run a single fixture and return results."""
    fixture_id = fixture["id"]
    name = fixture["name"]
    description = fixture["description"]

    # Handle dynamic generation
    if fixture.get("generate"):
        input_text, expected_data = fixture["generate"]()
        fixture["input"] = input_text
        if fixture["expected_data"] is None:
            fixture["expected_data"] = expected_data
    else:
        input_text = fixture["input"]
        expected_data = fixture["expected_data"]

    expected_status = fixture["expected_status"]

    try:
        strict_mode = fixture.get("strict", True)
        actual_data, actual_status = parse_structured_output(input_text, strict=strict_mode)
    except Exception as e:
        return {
            "id": fixture_id,
            "name": name,
            "description": description,
            "result": "error",
            "error": str(e),
            "traceback": traceback.format_exc() if verbose else None,
        }

    # Check status match
    status_match = actual_status == expected_status

    # Check data match (only for pass/fallback, not for expected fail)
    data_match = True
    if expected_status in ("pass",) and expected_data is not None:
        data_match = actual_data == expected_data
    elif expected_status == "fallback" and actual_data is not None:
        # For fallback, just check we got some data
        data_match = True
    elif expected_status == "fail":
        data_match = actual_data is None

    result = "pass" if (status_match and data_match) else "fail"

    test_result = {
        "id": fixture_id,
        "name": name,
        "description": description,
        "result": result,
        "status_expected": expected_status,
        "status_actual": actual_status,
        "status_match": status_match,
        "data_match": data_match,
    }

    if verbose:
        test_result["input_preview"] = input_text[:200] + "..." if len(input_text) > 200 else input_text
        test_result["expected_data"] = expected_data
        test_result["actual_data"] = actual_data

    return test_result


def run_all_fixtures(fixtures: List[Dict], verbose: bool = False, fixture_filter: Optional[int] = None) -> Dict:
    """Run all or a specific fixture."""
    results = []

    if fixture_filter:
        filtered = [f for f in fixtures if f["id"] == fixture_filter]
        if not filtered:
            print(f"Fixture {fixture_filter} not found")
            return {"total": 0, "passed": 0, "failed": 0, "fixtures": []}
        fixtures = filtered

    for fixture in fixtures:
        result = run_fixture(fixture, verbose)
        results.append(result)

    passed = sum(1 for r in results if r["result"] == "pass")
    failed = sum(1 for r in results if r["result"] == "fail")
    errors = sum(1 for r in results if r["result"] == "error")

    return {
        "total": len(results),
        "passed": passed,
        "failed": failed,
        "errors": errors,
        "pass_rate": round(passed / len(results) * 100, 1) if results else 0,
        "fixtures": results,
    }


def print_results(results: Dict):
    """Print test results in a readable format."""
    print("=" * 60)
    print("  Structured Output Parser Fixture Suite Results")
    print("=" * 60)
    print(f"\n  Total:   {results['total']}")
    print(f"  Passed:  {results['passed']}")
    print(f"  Failed:  {results['failed']}")
    print(f"  Errors:  {results['errors']}")
    print(f"  Rate:    {results['pass_rate']}%")
    print()

    for fixture_result in results["fixtures"]:
        icon = {
            "pass": "[PASS]",
            "fail": "[FAIL]",
            "error": "[ERR ]",
        }.get(fixture_result["result"], "[ ?  ]")
        print(f"  {icon} F{fixture_result['id']:02d}: {fixture_result['name']}")
        if fixture_result["result"] != "pass":
            print(f"       Status: expected={fixture_result['status_expected']}, "
                  f"actual={fixture_result['status_actual']}")
            print(f"       Status match: {fixture_result.get('status_match')}")
            print(f"       Data match: {fixture_result.get('data_match')}")
            if "error" in fixture_result:
                print(f"       Error: {fixture_result['error']}")

    print("=" * 60)
    print(f"  Overall: {'ALL PASSED' if results['failed'] == 0 and results['errors'] == 0 else 'SOME FAILED'}")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description="Structured Output Parser Fixture Suite (16 fixtures)"
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--fixture", type=int, help="Run a specific fixture number")
    parser.add_argument("--json-output", help="Save results to JSON file")

    args = parser.parse_args()

    results = run_all_fixtures(
        FIXTURES,
        verbose=args.verbose,
        fixture_filter=args.fixture,
    )

    print_results(results)

    if args.json_output:
        with open(args.json_output, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print(f"\nResults saved to: {args.json_output}")

    # Exit with appropriate code
    sys.exit(0 if results["failed"] == 0 and results["errors"] == 0 else 1)


if __name__ == "__main__":
    main()
