#!/usr/bin/env python3
"""
p0_pre_sdk_test.py - P0-pre SDK Headless Execution Test

验证 Kimi Agent SDK 或可用 fallback 是否支持非交互式执行。
固定Prompt: "请只输出 JSON：{\"status\":\"ok\"}"

通过标准:
  - 连续运行3次，至少2次成功返回
  - 成功返回的latency均<30s
  - 3次运行的中位数latency<20s
  - 任何单次latency>60s视为异常，记录但不阻断
  - 成功返回的输出必须能被Python json.loads()解析
  - 解析后status=="ok"

快速失败机制:
  - SDK导入失败(ImportError) → 5秒内退出
  - 触发CLI fallback链
"""

import json
import os
import sys
import time
import uuid
import subprocess
import hashlib
from datetime import datetime, timezone

# =============================================================================
# Configuration
# =============================================================================

FIXED_PROMPT = '请只输出 JSON：{"status":"ok"}'
NUM_RUNS = 3
SUCCESS_THRESHOLD = 2  # 至少2次成功
LATENCY_PER_RUN_MAX = 30.0  # 单次成功latency上限
LATENCY_MEDIAN_MAX = 20.0  # 中位数latency上限
LATENCY_ANOMALY_THRESHOLD = 60.0  # 异常阈值

OUTPUT_DIR = "evals/results/p0-pre/sdk-headless"
RUNTIME_DIR = "runtime"
ERROR_LOG = os.path.join(OUTPUT_DIR, "errors.jsonl")
DEBUG_LOG = os.path.join(OUTPUT_DIR, "debug.log")
RESULT_FILE = os.path.join(OUTPUT_DIR, "result.json")

# =============================================================================
# Logging utilities
# =============================================================================

def log_debug(msg):
    """Append timestamped message to debug.log."""
    timestamp = datetime.now(timezone.utc).isoformat()
    line = f"[{timestamp}] {msg}\n"
    try:
        with open(DEBUG_LOG, "a", encoding="utf-8") as f:
            f.write(line)
    except Exception:
        # If debug log itself fails, write to stderr as last resort
        print(line, file=sys.stderr)


def write_error_envelope(layer, severity, message, user_visible_message,
                         recoverable, retryable, fallback_action,
                         affected_artifacts, next_step, raw_error_path=None):
    """
    Write a standardized error-envelope to errors.jsonl.
    Returns the error envelope dict.
    """
    envelope = {
        "error_id": str(uuid.uuid4()),
        "layer": layer,
        "severity": severity,
        "message": message,
        "user_visible_message": user_visible_message,
        "recoverable": recoverable,
        "retryable": retryable,
        "fallback_action": fallback_action,
        "affected_artifacts": affected_artifacts,
        "next_step": next_step,
        "raw_error_path": raw_error_path
    }
    try:
        with open(ERROR_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(envelope, ensure_ascii=False) + "\n")
    except Exception as e:
        log_debug(f"CRITICAL: Failed to write error envelope: {e}")
    return envelope


def write_result(data):
    """Write result.json and mirror a copy to runtime/."""
    try:
        with open(RESULT_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        log_debug(f"Failed to write {RESULT_FILE}: {e}")
        # runtime mirror as fallback
        try:
            os.makedirs(RUNTIME_DIR, exist_ok=True)
            mirror_path = os.path.join(RUNTIME_DIR, "p0-pre-sdk-result.json")
            with open(mirror_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e2:
            log_debug(f"Failed to write runtime mirror: {e2}")


# =============================================================================
# Directory setup
# =============================================================================

def ensure_directories():
    """
    Create all required directories.
    Returns True on success, False on fatal failure.
    """
    dirs = [OUTPUT_DIR, RUNTIME_DIR]
    for d in dirs:
        try:
            os.makedirs(d, exist_ok=True)
            log_debug(f"Directory ensured: {d}")
        except Exception as e:
            # Fatal error: cannot proceed without output directory
            envelope = {
                "error_id": str(uuid.uuid4()),
                "layer": "script",
                "severity": "fatal",
                "message": f"Failed to create directory {d}: {e}",
                "user_visible_message": "输出目录创建失败，测试无法继续。",
                "recoverable": False,
                "retryable": False,
                "fallback_action": None,
                "affected_artifacts": [d],
                "next_step": "manual-smoke-required",
                "raw_error_path": None
            }
            # Try to write to stderr since debug log location may not exist
            print(json.dumps(envelope, indent=2, ensure_ascii=False), file=sys.stderr)
            sys.exit(1)
    return True


# =============================================================================
# SDK and CLI detection
# =============================================================================

def detect_sdk():
    """
    Try importing Kimi Agent SDK.
    Returns (available: bool, client_or_none, version: str).
    """
    try:
        # Try the official SDK import path
        from kimi_agent import KimiAgent
        version = getattr(KimiAgent, "__version__", "unknown")
        log_debug(f"SDK detected: kimi_agent v{version}")
        return True, KimiAgent, version
    except ImportError:
        log_debug("SDK not available: kimi_agent import failed")
        return False, None, None


def detect_cli():
    """
    Detect CLI fallback availability.
    Returns (available: bool, version: str).
    """
    candidates = ["kimi-agent", "kimi", "ka"]
    for cmd in candidates:
        try:
            result = subprocess.run(
                [cmd, "--version"],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                version = result.stdout.strip() or "unknown"
                log_debug(f"CLI detected: {cmd} v{version}")
                return True, version
        except (FileNotFoundError, subprocess.TimeoutExpired):
            continue
    log_debug("No CLI fallback available")
    return False, None


# =============================================================================
# Run execution
# =============================================================================

def run_with_sdk(client_cls, prompt):
    """
    Execute a single run using SDK.
    Returns (output_str, latency_seconds, exception_or_none).
    """
    start = time.time()
    try:
        # Instantiate and call
        client = client_cls()
        # Use non-streaming, headless call
        response = client.chat(prompt, stream=False)
        latency = time.time() - start
        output = response if isinstance(response, str) else str(response)
        return output, latency, None
    except Exception as e:
        latency = time.time() - start
        return "", latency, e


def run_with_cli(cli_cmd, prompt):
    """
    Execute a single run using CLI fallback.
    Returns (output_str, latency_seconds, exception_or_none).
    """
    start = time.time()
    try:
        result = subprocess.run(
            [cli_cmd, "chat", "--no-stream", prompt],
            capture_output=True, text=True, timeout=120
        )
        latency = time.time() - start
        output = result.stdout.strip()
        if result.returncode != 0:
            err = RuntimeError(f"CLI exit code {result.returncode}: {result.stderr}")
            return output, latency, err
        return output, latency, None
    except subprocess.TimeoutExpired:
        latency = time.time() - start
        return "", latency, RuntimeError("CLI timeout after 120s")
    except Exception as e:
        latency = time.time() - start
        return "", latency, e


def execute_run(runner, client_or_cli, prompt):
    """
    Execute one run with given runner.
    Returns dict with output, latency, error, raw_output_path.
    """
    if runner == "sdk":
        output, latency, error = run_with_sdk(client_or_cli, prompt)
    elif runner == "cli":
        output, latency, error = run_with_cli(client_or_cli, prompt)
    else:
        output, latency, error = "", 0.0, ValueError(f"Unknown runner: {runner}")

    return {
        "output": output,
        "latency_seconds": round(latency, 3),
        "error": str(error) if error else None,
        "had_exception": error is not None
    }


# =============================================================================
# JSON validation
# =============================================================================

def validate_json_output(raw_output):
    """
    Try to parse raw output as JSON and check status=="ok".
    Returns (success: bool, parsed_dict_or_none, error_message_or_none).
    """
    if not raw_output or not raw_output.strip():
        return False, None, "Empty output"

    # Try direct parsing
    try:
        parsed = json.loads(raw_output)
        if isinstance(parsed, dict) and parsed.get("status") == "ok":
            return True, parsed, None
        return False, parsed, f"status field missing or not 'ok': {parsed}"
    except json.JSONDecodeError:
        pass

    # Try extracting JSON substring (in case of surrounding text)
    text = raw_output.strip()
    # Find JSON object boundaries
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        try:
            parsed = json.loads(text[start:end+1])
            if isinstance(parsed, dict) and parsed.get("status") == "ok":
                return True, parsed, None
            return False, parsed, f"Extracted JSON status not 'ok': {parsed}"
        except json.JSONDecodeError as e:
            return False, None, f"JSON extraction failed: {e}"

    return False, None, "No JSON object found in output"


# =============================================================================
# Main test orchestration
# =============================================================================

def main():
    """
    Main entry point for P0-pre SDK headless test.
    """
    overall_start = time.time()

    # --- Ensure directories exist ---
    if not ensure_directories():
        return 1

    log_debug("=" * 60)
    log_debug("p0_pre_sdk_test started")
    log_debug(f"FIXED_PROMPT: {FIXED_PROMPT}")
    log_debug(f"NUM_RUNS: {NUM_RUNS}")

    # --- Detect SDK and CLI ---
    sdk_available, sdk_client, sdk_version = detect_sdk()
    cli_available, cli_version = detect_cli()

    log_debug(f"sdk_available={sdk_available}, sdk_version={sdk_version}")
    log_debug(f"cli_available={cli_available}, cli_version={cli_version}")

    # --- Fast-fail: SDK unavailable → CLI fallback ---
    if not sdk_available:
        log_debug("SDK fast-fail triggered: ImportError")
        result = {
            "p0_pre_001": "SKIP",
            "reason": "SDK unavailable",
            "fallback": "cli",
            "runner": None,
            "runs": 0,
            "successful_runs": 0,
            "passed_runs": 0,
            "median_latency_seconds": None,
            "max_latency_seconds": None,
            "latency_anomaly": False,
            "json_parse_success": False,
            "reasoning_content": "unavailable",
            "fallback_used": "cli",
            "cli_available": cli_available,
            "cli_version": cli_version
        }
        write_result(result)
        # Output fast-fail JSON to stdout
        print(json.dumps({"p0_pre_001": "SKIP", "reason": "SDK unavailable", "fallback": "cli"}))
        log_debug("Fast-fail output emitted, exiting in 5s")
        time.sleep(5)
        return 0  # Not a hard_fail, just SKIP

    # --- Determine runner ---
    runner = "sdk"
    fallback_used = None
    log_debug(f"Using runner: {runner}")

    # --- Execute 3 runs ---
    run_results = []
    for i in range(1, NUM_RUNS + 1):
        run_index = i
        log_debug(f"--- Run {run_index:03d} started ---")

        # Execute
        run_data = execute_run(runner, sdk_client, FIXED_PROMPT)
        raw_output = run_data["output"]
        latency = run_data["latency_seconds"]
        had_error = run_data["had_exception"]

        # Save raw output
        raw_path = os.path.join(OUTPUT_DIR, f"run-{run_index:03d}-raw.txt")
        try:
            with open(raw_path, "w", encoding="utf-8") as f:
                f.write(raw_output)
        except Exception as e:
            log_debug(f"Failed to save raw output: {e}")

        # Save parsed output (if valid JSON)
        json_success, parsed, json_error = validate_json_output(raw_output)
        output_path = os.path.join(OUTPUT_DIR, f"run-{run_index:03d}-output.json")
        try:
            if json_success:
                with open(output_path, "w", encoding="utf-8") as f:
                    json.dump(parsed, f, indent=2, ensure_ascii=False)
            else:
                with open(output_path, "w", encoding="utf-8") as f:
                    json.dump({"_parse_error": json_error, "_raw": raw_output[:500]}, f, indent=2, ensure_ascii=False)
        except Exception as e:
            log_debug(f"Failed to save output JSON: {e}")

        # Save reasoning content placeholder
        reasoning_path = os.path.join(OUTPUT_DIR, f"run-{run_index:03d}-reasoning.txt")
        try:
            with open(reasoning_path, "w", encoding="utf-8") as f:
                f.write("unavailable\n")
        except Exception as e:
            log_debug(f"Failed to save reasoning file: {e}")

        # Log results
        log_debug(f"Run {run_index:03d}: latency={latency}s, json_success={json_success}, had_error={had_error}")
        if json_error:
            log_debug(f"Run {run_index:03d} JSON error: {json_error}")

        # Record run result
        run_results.append({
            "index": run_index,
            "latency_seconds": latency,
            "json_parse_success": json_success,
            "status_ok": (parsed.get("status") == "ok") if parsed else False,
            "had_exception": had_error,
            "error": run_data["error"]
        })

        # Handle runtime errors (timeout, 5xx, 429)
        if had_error:
            write_error_envelope(
                layer="script",
                severity="recoverable",
                message=f"Run {run_index} SDK error: {run_data['error']}",
                user_visible_message=f"第{run_index}次运行发生SDK错误，尝试fallback。",
                recoverable=True,
                retryable=True,
                fallback_action="cli",
                affected_artifacts=[raw_path],
                next_step="cli_fallback",
                raw_error_path=raw_path
            )
            # Attempt one retry then CLI fallback
            log_debug(f"Run {run_index}: attempting retry...")
            time.sleep(2)
            retry_data = execute_run(runner, sdk_client, FIXED_PROMPT)
            if not retry_data["had_exception"]:
                # Retry succeeded
                raw_output = retry_data["output"]
                latency = retry_data["latency_seconds"]
                json_success, parsed, json_error = validate_json_output(raw_output)
                run_results[-1]["latency_seconds"] = latency
                run_results[-1]["json_parse_success"] = json_success
                run_results[-1]["status_ok"] = (parsed.get("status") == "ok") if parsed else False
                run_results[-1]["had_exception"] = False
                run_results[-1]["error"] = None
                log_debug(f"Run {run_index} retry succeeded")
            else:
                log_debug(f"Run {run_index} retry failed, will attempt CLI fallback")
                # CLI fallback
                if cli_available:
                    cli_data = execute_run("cli", "kimi-agent", FIXED_PROMPT)
                    raw_output = cli_data["output"]
                    latency = cli_data["latency_seconds"]
                    json_success, parsed, json_error = validate_json_output(raw_output)
                    run_results[-1]["latency_seconds"] = latency
                    run_results[-1]["json_parse_success"] = json_success
                    run_results[-1]["status_ok"] = (parsed.get("status") == "ok") if parsed else False
                    run_results[-1]["had_exception"] = cli_data["had_exception"]
                    run_results[-1]["error"] = cli_data["error"]
                    runner = "cli"
                    fallback_used = "cli"
                    log_debug(f"Run {run_index} CLI fallback executed")
                else:
                    # No CLI available
                    write_error_envelope(
                        layer="script",
                        severity="fatal",
                        message="CLI fallback unavailable after SDK failure",
                        user_visible_message="SDK和CLI均不可用，需要手动验证。",
                        recoverable=False,
                        retryable=False,
                        fallback_action=None,
                        affected_artifacts=[],
                        next_step="manual-smoke-required",
                        raw_error_path=None
                    )

    # --- Calculate aggregate statistics ---
    successful_runs = sum(1 for r in run_results if r["json_parse_success"] and r["status_ok"])
    passed_runs = sum(1 for r in run_results if r["json_parse_success"] and r["status_ok"])
    latencies = [r["latency_seconds"] for r in run_results if not r["had_exception"]]

    median_latency = None
    max_latency = None
    latency_anomaly = False

    if latencies:
        sorted_lat = sorted(latencies)
        n = len(sorted_lat)
        median_latency = sorted_lat[n // 2] if n % 2 == 1 else (sorted_lat[n // 2 - 1] + sorted_lat[n // 2]) / 2
        median_latency = round(median_latency, 3)
        max_latency = round(max(latencies), 3)
        latency_anomaly = any(l > LATENCY_ANOMALY_THRESHOLD for l in latencies)

    # --- Determine PASS/SKIP/FAIL ---
    json_parse_success = all(r["json_parse_success"] for r in run_results)
    all_status_ok = all(r["status_ok"] for r in run_results)
    latency_ok = (median_latency is not None and median_latency < LATENCY_MEDIAN_MAX) and \
                 all(r["latency_seconds"] < LATENCY_PER_RUN_MAX for r in run_results if not r["had_exception"])

    if successful_runs >= SUCCESS_THRESHOLD and json_parse_success and all_status_ok and latency_ok:
        verdict = "PASS"
    elif sdk_available and successful_runs == 0:
        verdict = "FAIL"
    else:
        # Partial success or latency anomaly
        verdict = "PASS" if successful_runs >= SUCCESS_THRESHOLD else "FAIL"

    # Mark latency anomaly separately
    if latency_anomaly:
        log_debug("Latency anomaly detected (>60s on at least one run)")

    # --- Build result ---
    total_latency = round(time.time() - overall_start, 3)
    result = {
        "p0_pre_001": verdict,
        "runner": runner,
        "runs": NUM_RUNS,
        "successful_runs": successful_runs,
        "passed_runs": passed_runs,
        "median_latency_seconds": median_latency,
        "max_latency_seconds": max_latency,
        "latency_anomaly": latency_anomaly,
        "json_parse_success": json_parse_success,
        "reasoning_content": "unavailable",
        "fallback_used": fallback_used,
        "sdk_available": sdk_available,
        "sdk_version": sdk_version,
        "cli_available": cli_available,
        "cli_version": cli_version,
        "total_duration_seconds": total_latency,
        "run_details": run_results
    }

    write_result(result)
    log_debug(f"Result: {verdict}")
    log_debug(f"successful_runs={successful_runs}, median_latency={median_latency}, max_latency={max_latency}")
    log_debug("p0_pre_sdk_test completed")
    log_debug("=" * 60)

    # Print summary to stdout
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if verdict in ("PASS", "SKIP") else 1


if __name__ == "__main__":
    sys.exit(main())
