#!/usr/bin/env python3
"""
eval_runner.py — Kimi Production-Grade Agent Pack v1.1
=======================================================
Execute test prompts, save model output, and perform structured field checks.

Supports three execution modes:
  1. sdk     — Use the Kimi SDK programmatic API
  2. cli     — Use a CLI-based runner (e.g., subprocess to another tool)
  3. manual  — Read pre-stored raw-output.md and perform validation only

Usage:
    python scripts/eval_runner.py --suite unit-smoke --output evals/results/unit-smoke
    python scripts/eval_runner.py --suite unit-smoke --output evals/results/unit-smoke --dry-run
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import re
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ─── Constants ────────────────────────────────────────────────────────────────

PACK_VERSION = "v1.1.0"
DEFAULT_MODEL = "kimi-k2.6"
BENCHMARK_PROMPTS_PATH = "evals/benchmark-prompts.md"
UNIT_SMOKE_DIR = "evals/unit-smoke"

RUNNER_PRIORITY = ["sdk", "cli", "manual"]

ERROR_CODES = {
    "E001_FILE_NOT_FOUND": "Required file not found",
    "E002_JSON_PARSE_FAIL": "Failed to parse JSON in structured_output",
    "E003_FIELD_MISSING": "Required field missing from structured_output",
    "E004_STRUCTURED_OUTPUT_PARSE_FAIL": "Failed to extract structured_output block",
    "E005_RUNNER_UNAVAILABLE": "No suitable runner available",
    "E006_HARD_FAIL_TRIGGERED": "Hard-fail condition detected",
    "E007_INVALID_SUITE": "Invalid suite name specified",
    "E008_CARD_PARSE_FAIL": "Failed to parse test card",
    "E009_EXECUTION_ERROR": "Error during test execution",
}

# ─── Data Models ──────────────────────────────────────────────────────────────


@dataclass
class TestCard:
    """Represents a single unit-smoke test card."""

    eval_id: str
    title: str
    objective: str
    min_input: str
    expected_fields: List[str] = field(default_factory=list)
    hard_fail_conditions: List[str] = field(default_factory=list)
    acceptance_criteria: List[str] = field(default_factory=list)
    technical_assumptions: List[str] = field(default_factory=list)
    failure_fallback: str = ""
    raw: str = ""  # Full raw content of the card


@dataclass
class EvalResult:
    """Result of a single evaluation run."""

    eval_id: str = ""
    pack_version: str = PACK_VERSION
    runner: str = "manual"
    model_name: str = DEFAULT_MODEL
    run_timestamp: str = ""
    prompt_hash: str = ""
    skill_hash: str = ""
    agent_config_hash: str = ""
    pass_: bool = False  # 'pass' is a keyword
    hard_fail: bool = False
    score: int = 0
    missing_fields: List[str] = field(default_factory=list)
    notes: str = ""
    variance_note: str = "single_run"
    error_code: str = ""
    error_message: str = ""

    def to_dict(self) -> dict:
        d = asdict(self)
        d["pass"] = d.pop("pass_")
        return d


@dataclass
class RunMetadata:
    """Metadata about the evaluation run."""

    pack_version: str = PACK_VERSION
    suite: str = ""
    runner_used: str = ""
    model_name: str = DEFAULT_MODEL
    run_timestamp: str = ""
    total_tests: int = 0
    passed: int = 0
    failed: int = 0
    hard_fails: int = 0
    dry_run: bool = False
    duration_seconds: float = 0.0
    errors: List[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


# ─── Logging Setup ────────────────────────────────────────────────────────────


def setup_logging(output_dir: Path) -> logging.Logger:
    """Configure logging to file and console."""
    log_file = output_dir / "debug.log"
    log_file.parent.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("eval_runner")
    logger.setLevel(logging.DEBUG)

    # File handler
    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    file_fmt = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )
    fh.setFormatter(file_fmt)
    logger.addHandler(fh)

    # Console handler
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    console_fmt = logging.Formatter("[%(levelname)s] %(message)s")
    ch.setFormatter(console_fmt)
    logger.addHandler(ch)

    return logger


# ─── Error Envelope ───────────────────────────────────────────────────────────


def write_error_envelope(
    output_dir: Path,
    error_code: str,
    message: str,
    context: dict | None = None,
) -> None:
    """Write an error-envelope entry to errors.jsonl."""
    errors_file = output_dir / "errors.jsonl"
    envelope = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "error_code": error_code,
        "error_name": ERROR_CODES.get(error_code, "Unknown"),
        "message": message,
        "context": context or {},
    }
    with open(errors_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(envelope, ensure_ascii=False) + "\n")


# ─── Hash Utilities ───────────────────────────────────────────────────────────


def sha256_str(content: str) -> str:
    """Compute SHA-256 hash of a string."""
    return f"sha256:{hashlib.sha256(content.encode('utf-8')).hexdigest()}"


def sha256_file(path: Path) -> str:
    """Compute SHA-256 hash of a file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return f"sha256:{h.hexdigest()}"


# ─── Test Card Discovery & Parsing ────────────────────────────────────────────


def discover_test_cards(suite: str) -> List[Path]:
    """Discover test card files for the given suite."""
    cards: List[Path] = []

    if suite == "unit-smoke":
        unit_dir = Path(UNIT_SMOKE_DIR)
        if unit_dir.is_dir():
            cards = sorted(unit_dir.glob("unit-smoke-*.md"))
    elif suite == "smoke":
        # Smoke suite reads from benchmark-prompts.md
        bench = Path(BENCHMARK_PROMPTS_PATH)
        if bench.is_file():
            cards = [bench]
    elif suite == "integration-smoke":
        # Integration smoke can also use unit-smoke cards combined
        unit_dir = Path(UNIT_SMOKE_DIR)
        if unit_dir.is_dir():
            cards = sorted(unit_dir.glob("*.md"))
    else:
        raise ValueError(f"Unknown suite: {suite}")

    return cards


def parse_test_card(path: Path) -> TestCard:
    """Parse a test card markdown file into a TestCard object."""
    content = path.read_text(encoding="utf-8")

    # Extract eval_id from filename or front matter
    eval_id = path.stem

    # Parse sections
    sections = {}
    current_section = None
    current_lines: List[str] = []

    for line in content.splitlines():
        header_match = re.match(r"^##\s+(.+)$", line)
        if header_match:
            if current_section:
                sections[current_section] = "\n".join(current_lines).strip()
            current_section = header_match.group(1).strip().lower().replace(" ", "_")
            current_lines = []
        elif current_section:
            current_lines.append(line)

    if current_section:
        sections[current_section] = "\n".join(current_lines).strip()

    # Extract fields
    def get_section(name: str) -> str:
        return sections.get(name, "")

    # Parse expected fields from structured_output / expected_structured_output section
    expected_fields: List[str] = []
    structured_output_raw = get_section("structured_output") or get_section("expected_structured_output")
    if structured_output_raw:
        # Try to extract JSON schema or field list
        json_match = re.search(r"```json\s*(\{.*?\})\s*```", structured_output_raw, re.DOTALL)
        if json_match:
            try:
                schema = json.loads(json_match.group(1))
                expected_fields = list(schema.keys())
            except json.JSONDecodeError:
                # Fallback: extract field names from bullet list
                pass
        if not expected_fields:
            # Extract from bullet points like "- field_name: description"
            for line in structured_output_raw.splitlines():
                m = re.match(r"^\s*[-*]\s*(\w+)\s*[:\(]", line)
                if m:
                    expected_fields.append(m.group(1))

    # Parse hard fail conditions
    hard_fail_conditions: List[str] = []
    hard_fail_raw = get_section("hard_fail_conditions")
    if hard_fail_raw:
        for line in hard_fail_raw.splitlines():
            line = line.strip()
            if line and line.startswith(("-", "*", "1.", "2.", "3.", "4.", "5.", "6.", "7.", "8.")):
                hard_fail_conditions.append(re.sub(r"^[-*\d.\s]+", "", line).strip())

    # Parse acceptance criteria
    acceptance_criteria: List[str] = []
    ac_raw = get_section("acceptance_criteria")
    if ac_raw:
        for line in ac_raw.splitlines():
            line = line.strip()
            if line and line.startswith(("-", "*", "1.", "2.", "3.", "4.", "5.")):
                acceptance_criteria.append(re.sub(r"^[-*\d.\s]+", "", line).strip())

    # Parse technical assumptions
    technical_assumptions: List[str] = []
    ta_raw = get_section("technical_assumptions")
    if ta_raw:
        for line in ta_raw.splitlines():
            line = line.strip()
            if line and line.startswith(("-", "*", "1.", "2.", "3.")):
                technical_assumptions.append(re.sub(r"^[-*\d.\s]+", "", line).strip())

    return TestCard(
        eval_id=eval_id,
        title=get_section("test_title") or eval_id,
        objective=get_section("test_objective"),
        min_input=get_section("min_input"),
        expected_fields=expected_fields,
        hard_fail_conditions=hard_fail_conditions,
        acceptance_criteria=acceptance_criteria,
        technical_assumptions=technical_assumptions,
        failure_fallback=get_section("failure_fallback"),
        raw=content,
    )


# ─── Runner Selection ─────────────────────────────────────────────────────────


def check_sdk_runner() -> bool:
    """Check if the Kimi SDK runner is available."""
    try:
        # Check for Kimi SDK or openai compatible SDK
        import importlib
        return importlib.util.find_spec("openai") is not None
    except Exception:
        return False


def check_cli_runner() -> bool:
    """Check if a CLI runner is available."""
    # Check for known CLI tools
    cli_tools = ["kimi", "kimi-cli", "python -m kimi"]
    for tool in cli_tools:
        try:
            result = subprocess.run(
                tool.split() + ["--version"],
                capture_output=True,
                timeout=5,
            )
            if result.returncode == 0:
                return True
        except (FileNotFoundError, subprocess.TimeoutExpired):
            continue
    return False


def select_runner() -> str:
    """Select the best available runner following the priority chain."""
    if check_sdk_runner():
        return "sdk"
    if check_cli_runner():
        return "cli"
    return "manual"


# ─── Structured Output Extraction ─────────────────────────────────────────────


def extract_structured_output(raw_text: str) -> Tuple[Optional[dict], str]:
    """
    Extract the structured_output JSON block from raw model output.

    Returns:
        (parsed_dict, error_code): The parsed dict and any error code.
    """
    # Strategy 1: Match ```json ... ``` block
    json_pattern = re.compile(r"```json\s*(.*?)\s*```", re.DOTALL)
    matches = json_pattern.findall(raw_text)

    for match in matches:
        cleaned = match.strip()
        if not cleaned:
            continue
        try:
            return json.loads(cleaned), ""
        except json.JSONDecodeError:
            # Strategy 2: Try regex boundary extraction
            # Find the outermost { ... } or [ ... ]
            obj_match = re.search(r"(\{[\s\S]*\})|(\[[\s\S]*\])", cleaned)
            if obj_match:
                try:
                    return json.loads(obj_match.group(0)), ""
                except json.JSONDecodeError:
                    continue

    # Strategy 3: Look for bare JSON object/array in the text
    bare_match = re.search(r"(\{[\s\S]*\})|(\[[\s\S]*\])", raw_text)
    if bare_match:
        try:
            parsed = json.loads(bare_match.group(0))
            if isinstance(parsed, dict) and parsed:
                return parsed, ""
        except json.JSONDecodeError:
            pass

    return None, "E004_STRUCTURED_OUTPUT_PARSE_FAIL"


# ─── Field Validation ─────────────────────────────────────────────────────────


def validate_fields(
    structured_output: dict,
    expected_fields: List[str],
) -> Tuple[List[str], str]:
    """
    Validate that all expected fields are present in structured_output.

    Returns:
        (missing_fields, notes)
    """
    if not isinstance(structured_output, dict):
        return expected_fields, "structured_output is not a JSON object"

    missing: List[str] = []
    for field in expected_fields:
        # Support nested field paths like "evidence[].claim"
        if "." in field and "[" not in field:
            parts = field.split(".")
            current = structured_output
            for part in parts:
                if isinstance(current, dict) and part in current:
                    current = current[part]
                else:
                    missing.append(field)
                    break
        elif "[" in field:
            # Handle bracket notation like "evidence[]" or "artifacts[{type}]"
            base_name = field.split("[")[0]
            if base_name not in structured_output:
                missing.append(field)
        else:
            if field not in structured_output:
                missing.append(field)

    if missing:
        notes = f"Missing {len(missing)} required field(s): {', '.join(missing)}"
    else:
        notes = "All required fields present."

    return missing, notes


# ─── Hard Fail Checking ───────────────────────────────────────────────────────


def check_hard_fail_conditions(
    structured_output: dict,
    hard_fail_conditions: List[str],
    raw_text: str,
) -> Tuple[bool, List[str]]:
    """
    Check if any hard-fail conditions are triggered.

    Returns:
        (is_hard_fail, triggered_rules)
    """
    triggered: List[str] = []

    for condition in hard_fail_conditions:
        condition_lower = condition.lower()

        # Rule: 没有来源 / no sources
        if "没有来源" in condition or "no source" in condition_lower:
            evidence = structured_output.get("evidence", [])
            if not evidence:
                triggered.append(condition)

        # Rule: 核心交付物缺失 / missing core deliverable
        if "交付物" in condition or "deliverable" in condition_lower:
            deliverables = structured_output.get("deliverables", [])
            artifacts = structured_output.get("artifacts", [])
            if not deliverables and not artifacts:
                triggered.append(condition)

        # Rule: 代码声称测试通过但未运行测试 / claimed tests passed but no test run
        if "测试" in condition and "未运行" in condition:
            test_results = structured_output.get("test_results", {})
            if isinstance(test_results, dict):
                passed = test_results.get("passed", False)
                ran = test_results.get("ran", False)
                if passed and not ran:
                    triggered.append(condition)

        # Rule: 没有明确goal / no clear goal
        if "goal" in condition_lower or "目标" in condition:
            goal = structured_output.get("goal", "")
            if not goal or (isinstance(goal, str) and len(goal.strip()) < 3):
                triggered.append(condition)

        # Rule: 没有搜索查询记录 / no search query recorded
        if "搜索" in condition and "查询" in condition:
            queries = structured_output.get("search_queries", [])
            if not queries:
                # Check in evidence for source_type
                evidence = structured_output.get("evidence", [])
                has_search_source = any(
                    e.get("source_type") in ("web", "search", "api")
                    for e in evidence
                    if isinstance(e, dict)
                )
                if evidence and not has_search_source:
                    pass  # Don't trigger if evidence exists with other types

        # Rule: 新增未经evidence支撑的事实 / new facts without evidence
        if "evidence" in condition_lower and "支撑" in condition:
            conclusion = structured_output.get("conclusion", [])
            evidence = structured_output.get("evidence", [])
            if conclusion and not evidence:
                triggered.append(condition)

        # Rule: 把假设写成确定事实 / assumptions written as facts
        if "假设" in condition and "事实" in condition:
            assumptions = structured_output.get("assumptions", [])
            confidence = structured_output.get("confidence", 1.0)
            if not assumptions and confidence == 1.0:
                # If there are no assumptions marked but confidence is 100%,
                # this might be overstating certainty
                pass

        # Rule: 没有审查维度评分 / no dimension scores
        if "维度" in condition and "评分" in condition:
            dimensions = structured_output.get("dimensions", [])
            if not dimensions:
                triggered.append(condition)

        # Rule: 有hard_fail但未标记 / hard_fail present but not flagged
        if "hard_fail" in condition_lower and "未标记" in condition:
            hard_fails = structured_output.get("hard_fails", [])
            # This is checked elsewhere

        # Rule: 无overall结论 / no overall conclusion
        if "overall" in condition_lower or "结论" in condition:
            overall_notes = structured_output.get("overall_notes", "")
            status = structured_output.get("status", "")
            if not overall_notes and status not in ("pass", "fail", "pass_with_notes"):
                triggered.append(condition)

        # Rule: 报告结构缺失关键部分 / missing report structure parts
        if "结构" in condition and "缺失" in condition:
            report_structure = structured_output.get("report_structure", {})
            if isinstance(report_structure, dict) and not report_structure:
                triggered.append(condition)

        # Rule: 无artifact输出 / no artifact output
        if "artifact" in condition_lower and "输出" in condition:
            artifacts = structured_output.get("artifacts", [])
            if not artifacts:
                triggered.append(condition)

    return len(triggered) > 0, triggered


# ─── Model Execution ──────────────────────────────────────────────────────────


def run_with_sdk(prompt: str, model_name: str) -> str:
    """Execute a prompt using the Kimi/OpenAI SDK."""
    try:
        from openai import OpenAI

        client = OpenAI(
            api_key=os.environ.get("KIMI_API_KEY", os.environ.get("OPENAI_API_KEY", "")),
            base_url=os.environ.get("KIMI_BASE_URL", "https://api.moonshot.cn/v1"),
        )

        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": "You are a helpful AI assistant."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
        )
        return response.choices[0].message.content or ""
    except Exception as e:
        raise RuntimeError(f"SDK execution failed: {e}") from e


def run_with_cli(prompt: str, model_name: str) -> str:
    """Execute a prompt using a CLI tool."""
    # Try kimi CLI
    kimi_cmd = ["kimi", "chat", "--model", model_name, prompt]
    try:
        result = subprocess.run(
            kimi_cmd,
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode == 0:
            return result.stdout
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    # Fallback to python -m kimi
    try:
        result = subprocess.run(
            ["python", "-m", "kimi", "chat", "--model", model_name, prompt],
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode == 0:
            return result.stdout
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    raise RuntimeError("CLI runner failed: no available CLI tool")


def run_manual(card: TestCard, output_dir: Path, logger: logging.Logger) -> str:
    """
    Manual runner: read pre-stored raw-output.md if available,
    otherwise create a placeholder for manual filling.
    """
    raw_output_path = output_dir / "raw-output.md"

    if raw_output_path.is_file():
        logger.info(f"Reading pre-stored raw output: {raw_output_path}")
        return raw_output_path.read_text(encoding="utf-8")

    # Create a template for manual execution
    logger.info("No pre-stored raw-output.md found; creating template for manual fill.")
    template = f"""# Manual Raw Output — {card.eval_id}

## Input
{card.min_input}

## Instructions
1. Run the above input through the agent manually.
2. Paste the agent's complete raw output below.
3. Ensure the output contains a `structured_output` JSON block.

## structured_output

```json
{{
  "eval_id": "{card.eval_id}"
}}
```

## raw_output

(Paste agent output here)
"""
    raw_output_path.write_text(template, encoding="utf-8")
    logger.info(f"Template written to {raw_output_path}")
    return template


# ─── Single Test Execution ────────────────────────────────────────────────────


def execute_single_test(
    card: TestCard,
    runner: str,
    output_dir: Path,
    model_name: str,
    dry_run: bool,
    logger: logging.Logger,
) -> EvalResult:
    """Execute a single test card and produce an EvalResult."""
    result = EvalResult(
        eval_id=card.eval_id,
        pack_version=PACK_VERSION,
        runner=runner,
        model_name=model_name,
        run_timestamp=datetime.now(timezone.utc).isoformat(),
        prompt_hash=sha256_str(card.min_input),
        skill_hash=sha256_str(card.raw),
        agent_config_hash=sha256_str(json.dumps({"runner": runner, "model": model_name})),
    )

    if dry_run:
        result.notes = f"[DRY-RUN] Would execute {card.eval_id} with runner={runner}"
        result.pass_ = True  # Dry-run doesn't fail
        result.score = 0
        logger.info(result.notes)
        return result

    # Step 1: Get raw output
    raw_text = ""
    try:
        if runner == "sdk":
            raw_text = run_with_sdk(card.min_input, model_name)
        elif runner == "cli":
            raw_text = run_with_cli(card.min_input, model_name)
        elif runner == "manual":
            raw_text = run_manual(card, output_dir, logger)

        # Save raw output
        raw_output_path = output_dir / "raw-output.md"
        raw_output_path.write_text(raw_text, encoding="utf-8")
        logger.debug(f"Raw output saved to {raw_output_path}")

    except Exception as e:
        error_msg = f"Execution failed for {card.eval_id}: {e}"
        logger.error(error_msg)
        result.error_code = "E009_EXECUTION_ERROR"
        result.error_message = str(e)
        result.notes = error_msg
        write_error_envelope(output_dir, result.error_code, error_msg, {"eval_id": card.eval_id})
        return result

    # Step 2: Extract structured_output
    structured_output, error_code = extract_structured_output(raw_text)

    if error_code:
        result.error_code = error_code
        result.error_message = ERROR_CODES[error_code]
        result.notes = f"Failed to extract structured_output: {error_code}"
        write_error_envelope(
            output_dir,
            error_code,
            result.notes,
            {"eval_id": card.eval_id},
        )
        return result

    # Step 3: Validate expected fields
    missing_fields, field_notes = validate_fields(structured_output, card.expected_fields)
    result.missing_fields = missing_fields

    # Step 4: Check hard-fail conditions
    is_hard_fail, triggered_rules = check_hard_fail_conditions(
        structured_output,
        card.hard_fail_conditions,
        raw_text,
    )
    result.hard_fail = is_hard_fail

    # Step 5: Calculate score
    if missing_fields:
        result.pass_ = False
        # Deduct 10 points per missing field, minimum 0
        result.score = max(0, 100 - len(missing_fields) * 10)
        result.notes = field_notes
        if is_hard_fail:
            result.score = min(result.score, 60)
            result.notes += f" | Hard-fail triggered: {', '.join(triggered_rules)}"
    else:
        result.pass_ = True
        if is_hard_fail:
            result.score = 60
            result.notes = f"All fields present but hard-fail triggered: {', '.join(triggered_rules)}"
        else:
            result.score = 100
            result.notes = "All required fields present."

    logger.info(
        f"Test {card.eval_id}: pass={result.pass_}, hard_fail={result.hard_fail}, "
        f"score={result.score}, missing={len(missing_fields)}"
    )

    return result


# ─── Result Persistence ───────────────────────────────────────────────────────


def save_results(
    output_dir: Path,
    results: List[EvalResult],
    metadata: RunMetadata,
    logger: logging.Logger,
) -> None:
    """Save all evaluation results to the output directory."""
    output_dir.mkdir(parents=True, exist_ok=True)

    # Save individual eval results as a combined JSON
    eval_results = [r.to_dict() for r in results]
    eval_result_path = output_dir / "eval-result.json"
    with open(eval_result_path, "w", encoding="utf-8") as f:
        json.dump(eval_results, f, ensure_ascii=False, indent=2)
    logger.info(f"Saved eval-result.json ({len(results)} results)")

    # Save run metadata
    metadata_path = output_dir / "run-metadata.json"
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata.to_dict(), f, ensure_ascii=False, indent=2)
    logger.info(f"Saved run-metadata.json")

    # Save errors.jsonl (already written during execution, ensure it exists)
    errors_file = output_dir / "errors.jsonl"
    if not errors_file.exists():
        errors_file.write_text("", encoding="utf-8")

    # Generate summary
    summary_lines = [
        f"=== Eval Summary ===",
        f"Suite:        {metadata.suite}",
        f"Runner:       {metadata.runner_used}",
        f"Model:        {metadata.model_name}",
        f"Total tests:  {metadata.total_tests}",
        f"Passed:       {metadata.passed}",
        f"Failed:       {metadata.failed}",
        f"Hard fails:   {metadata.hard_fails}",
        f"Duration:     {metadata.duration_seconds:.2f}s",
        f"Output dir:   {output_dir}",
        "====================",
    ]
    summary_text = "\n".join(summary_lines)
    logger.info(summary_text)

    # Also print summary to console
    print("\n" + summary_text)


# ─── Main Entry Point ─────────────────────────────────────────────────────────


def main(argv: list[str] | None = None) -> int:
    """Main entry point for the eval runner."""
    parser = argparse.ArgumentParser(
        description="Kimi Production-Grade Agent Pack — Eval Runner v1.1",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/eval_runner.py --suite unit-smoke --output evals/results/unit-smoke
  python scripts/eval_runner.py --suite unit-smoke --output evals/results/unit-smoke --dry-run
  python scripts/eval_runner.py --suite smoke --model kimi-k2.6 --output evals/results/smoke
        """,
    )

    parser.add_argument(
        "--suite",
        choices=["unit-smoke", "smoke", "integration-smoke"],
        required=True,
        help="Test suite to run",
    )
    parser.add_argument(
        "--output",
        type=str,
        required=True,
        help="Output directory for results",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview what would be executed without running",
    )
    parser.add_argument(
        "--model",
        type=str,
        default=DEFAULT_MODEL,
        help=f"Model name to use (default: {DEFAULT_MODEL})",
    )
    parser.add_argument(
        "--runner",
        type=str,
        choices=RUNNER_PRIORITY,
        default=None,
        help="Force a specific runner (default: auto-select)",
    )

    args = parser.parse_args(argv)

    # Determine output directory with timestamp
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H%M%S")
    output_dir = Path(args.output) / timestamp

    # Setup logging
    logger = setup_logging(output_dir)
    logger.info(f"=== Eval Runner Starting ===")
    logger.info(f"Suite: {args.suite}")
    logger.info(f"Output: {output_dir}")
    logger.info(f"Dry-run: {args.dry_run}")
    logger.info(f"Model: {args.model}")

    # Discover test cards
    try:
        card_paths = discover_test_cards(args.suite)
    except ValueError as e:
        logger.error(f"Invalid suite: {e}")
        write_error_envelope(output_dir, "E007_INVALID_SUITE", str(e))
        return 1

    if not card_paths:
        logger.error(f"No test cards found for suite '{args.suite}'")
        write_error_envelope(
            output_dir,
            "E007_INVALID_SUITE",
            f"No test cards found for suite '{args.suite}'",
        )
        return 1

    logger.info(f"Discovered {len(card_paths)} test card(s)")

    # Select runner
    runner = args.runner or select_runner()
    logger.info(f"Selected runner: {runner}")

    # Initialize metadata
    metadata = RunMetadata(
        suite=args.suite,
        runner_used=runner,
        model_name=args.model,
        run_timestamp=datetime.now(timezone.utc).isoformat(),
        dry_run=args.dry_run,
    )

    # Execute tests
    results: List[EvalResult] = []
    start_time = time.perf_counter()

    for card_path in card_paths:
        logger.info(f"Processing test card: {card_path}")

        try:
            card = parse_test_card(card_path)
        except Exception as e:
            logger.error(f"Failed to parse {card_path}: {e}")
            write_error_envelope(
                output_dir,
                "E008_CARD_PARSE_FAIL",
                str(e),
                {"card_path": str(card_path)},
            )
            continue

        if args.dry_run:
            logger.info(f"[DRY-RUN] Would test: {card.eval_id}")
            logger.info(f"  Objective: {card.objective[:80]}...")
            logger.info(f"  Expected fields: {card.expected_fields}")
            logger.info(f"  Hard fail conditions: {len(card.hard_fail_conditions)}")

        result = execute_single_test(
            card=card,
            runner=runner,
            output_dir=output_dir,
            model_name=args.model,
            dry_run=args.dry_run,
            logger=logger,
        )
        results.append(result)

        if result.pass_:
            metadata.passed += 1
        else:
            metadata.failed += 1
        if result.hard_fail:
            metadata.hard_fails += 1

    elapsed = time.perf_counter() - start_time
    metadata.duration_seconds = round(elapsed, 2)
    metadata.total_tests = len(results)

    # Save all results
    save_results(output_dir, results, metadata, logger)

    # Exit code: 0 if all passed, 1 if any failed
    if metadata.failed > 0:
        logger.info(f"Exiting with code 1 ({metadata.failed} test(s) failed)")
        return 1

    logger.info("All tests passed. Exiting with code 0.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
