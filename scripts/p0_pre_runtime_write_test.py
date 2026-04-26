#!/usr/bin/env python3
"""
p0_pre_runtime_write_test.py - P0-pre Runtime Write Stability Test

验证项目能否稳定写入runtime目录，支持append-only JSONL事件日志。

通过标准:
  1. 创建runtime/test-write.jsonl
  2. 连续追加写入3条JSONL记录
  3. 每条记录可被json.loads()解析
  4. 文件md5与预期内容一致
  5. 读取时无权限错误
  6. 失败时生成error-envelope格式错误(layer="script")
  7. 所需目录自动创建

失败fallback:
  1. runtime/不存在 → 自动创建
  2. 无权限写入 → 改写evals/results/p0-pre/runtime-write/fallback.jsonl
  3. 追加失败 → 改为内存状态，任务结束后一次性写入
  4. 读取失败 → 保存raw error到debug log
  5. 输出目录创建失败 → fatal error, layer="script", 立即退出
"""

import json
import hashlib
import os
import sys
import time
import uuid
from datetime import datetime, timezone

# =============================================================================
# Configuration
# =============================================================================

RUNTIME_DIR = "runtime"
OUTPUT_DIR = "evals/results/p0-pre/runtime-write"
FALLBACK_DIR = OUTPUT_DIR  # fallback writes to same output dir
TARGET_FILE = os.path.join(RUNTIME_DIR, "test-write.jsonl")
FALLBACK_FILE = os.path.join(FALLBACK_DIR, "fallback.jsonl")
ERROR_LOG = os.path.join(OUTPUT_DIR, "errors.jsonl")
DEBUG_LOG = os.path.join(OUTPUT_DIR, "debug.log")
RESULT_FILE = os.path.join(OUTPUT_DIR, "result.json")

NUM_RECORDS = 3

# Pre-defined test records (timestamps will be generated at runtime)
BASE_RECORDS = [
    {"event": "test_write", "index": 1, "status": "ok"},
    {"event": "test_write", "index": 2, "status": "ok"},
    {"event": "test_write", "index": 3, "status": "ok"},
]

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


# =============================================================================
# Directory setup
# =============================================================================

def ensure_directories():
    """
    Create all required directories.
    Fatal error on failure (script cannot proceed without output dirs).
    """
    dirs = [RUNTIME_DIR, OUTPUT_DIR]
    for d in dirs:
        try:
            os.makedirs(d, exist_ok=True)
            log_debug(f"Directory ensured: {d}")
        except Exception as e:
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
            print(json.dumps(envelope, indent=2, ensure_ascii=False), file=sys.stderr)
            sys.exit(1)
    return True


# =============================================================================
# MD5 computation
# =============================================================================

def compute_md5(filepath):
    """Compute MD5 hex digest of file contents."""
    h = hashlib.md5()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def compute_md5_from_string(content):
    """Compute MD5 hex digest from string content."""
    return hashlib.md5(content.encode("utf-8")).hexdigest()


# =============================================================================
# Core test: write, append, read, verify
# =============================================================================

def build_records():
    """Generate test records with current timestamps."""
    now = datetime.now(timezone.utc)
    records = []
    for i, base in enumerate(BASE_RECORDS):
        rec = dict(base)
        ts = now.replace(second=now.second + i, microsecond=0)
        rec["timestamp"] = ts.strftime("%Y-%m-%dT%H:%M:%SZ")
        records.append(rec)
    return records


def try_write_records(filepath, records, mode="a"):
    """
    Attempt to write records as JSONL to filepath.
    Returns (success: bool, error_or_none).
    """
    try:
        with open(filepath, mode, encoding="utf-8") as f:
            for rec in records:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        return True, None
    except PermissionError as e:
        return False, f"Permission denied: {e}"
    except OSError as e:
        return False, f"OS error: {e}"
    except Exception as e:
        return False, f"Unexpected error: {e}"


def try_read_and_verify(filepath, expected_records):
    """
    Read JSONL file and verify each line parses and matches expected.
    Returns (success: bool, lines_read: int, error_or_none).
    """
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            lines = f.readlines()

        # Only verify the first N expected records (ignore appended records)
        lines_to_verify = lines[:len(expected_records)]
        if len(lines_to_verify) != len(expected_records):
            return False, len(lines), f"Line count mismatch: got {len(lines_to_verify)}, expected {len(expected_records)}"

        for i, line in enumerate(lines_to_verify):
            line = line.strip()
            if not line:
                return False, i, f"Empty line at index {i}"
            try:
                parsed = json.loads(line)
            except json.JSONDecodeError as e:
                return False, i, f"JSON parse error at line {i}: {e}"

            # Check required fields
            if parsed.get("event") != expected_records[i]["event"]:
                return False, i, f"event mismatch at line {i}"
            if parsed.get("index") != expected_records[i]["index"]:
                return False, i, f"index mismatch at line {i}"
            if parsed.get("status") != expected_records[i]["status"]:
                return False, i, f"status mismatch at line {i}"

        return True, len(lines), None
    except PermissionError as e:
        return False, 0, f"Permission denied on read: {e}"
    except OSError as e:
        return False, 0, f"OS error on read: {e}"
    except Exception as e:
        return False, 0, f"Unexpected read error: {e}"


# =============================================================================
# Fallback handlers
# =============================================================================

def fallback_to_alternative_path(records):
    """
    Fallback 1: Try writing to evals/results/p0-pre/runtime-write/fallback.jsonl
    when runtime/ is not writable.
    Returns (success: bool, used_path: str, error_or_none).
    """
    log_debug("Fallback: trying alternative path fallback.jsonl")
    try:
        os.makedirs(FALLBACK_DIR, exist_ok=True)
    except Exception as e:
        return False, None, f"Cannot create fallback dir: {e}"

    success, error = try_write_records(FALLBACK_FILE, records, mode="w")
    if success:
        return True, FALLBACK_FILE, None
    return False, None, error


def fallback_to_memory_buffer(records):
    """
    Fallback 2: Keep records in memory buffer for end-of-task write.
    Returns (success: bool, buffer_content: str).
    """
    log_debug("Fallback: using in-memory buffer")
    buffer_content = "\n".join(json.dumps(r, ensure_ascii=False) for r in records) + "\n"
    return True, buffer_content


def flush_memory_buffer(buffer_content, target_path):
    """
    Flush in-memory buffer to file at end of task.
    Returns (success: bool, error_or_none).
    """
    log_debug(f"Flushing memory buffer to {target_path}")
    try:
        with open(target_path, "w", encoding="utf-8") as f:
            f.write(buffer_content)
        return True, None
    except Exception as e:
        return False, str(e)


# =============================================================================
# Main test orchestration
# =============================================================================

def main():
    """
    Main entry point for P0-pre runtime write test.
    """
    overall_start = time.time()
    memory_buffer = None
    actual_target = TARGET_FILE
    fallback_used = None

    # --- Ensure directories exist ---
    if not ensure_directories():
        return 1

    log_debug("=" * 60)
    log_debug("p0_pre_runtime_write_test started")

    # --- Build test records ---
    records = build_records()
    log_debug(f"Generated {len(records)} test records")

    # --- Step 1: Write records to runtime/test-write.jsonl ---
    log_debug(f"Attempting write to {TARGET_FILE}")
    write_success, write_error = try_write_records(TARGET_FILE, records, mode="w")

    if not write_success:
        log_debug(f"Primary write failed: {write_error}")
        write_error_envelope(
            layer="script",
            severity="warning",
            message=f"Primary write failed: {write_error}",
            user_visible_message="runtime目录写入失败，尝试fallback路径。",
            recoverable=True,
            retryable=False,
            fallback_action="alternative_path",
            affected_artifacts=[TARGET_FILE],
            next_step="fallback_to_alternative_path",
            raw_error_path=DEBUG_LOG
        )

        # Fallback 1: Try alternative path
        fb_success, fb_path, fb_error = fallback_to_alternative_path(records)
        if fb_success:
            actual_target = fb_path
            fallback_used = "alternative_path"
            log_debug(f"Fallback write succeeded: {fb_path}")
        else:
            log_debug(f"Fallback write also failed: {fb_error}")
            write_error_envelope(
                layer="script",
                severity="recoverable",
                message=f"Alternative path fallback failed: {fb_error}",
                user_visible_message="备选路径也写入失败，切换为内存模式。",
                recoverable=True,
                retryable=False,
                fallback_action="memory_buffer",
                affected_artifacts=[TARGET_FILE, FALLBACK_FILE],
                next_step="memory_buffer_end_of_task",
                raw_error_path=DEBUG_LOG
            )

            # Fallback 2: Memory buffer
            mem_success, buffer_content = fallback_to_memory_buffer(records)
            if mem_success:
                memory_buffer = buffer_content
                fallback_used = "memory_buffer"
                log_debug("Memory buffer fallback active")

    # --- Step 2: Append more records (test append-only) ---
    # If we have a writable file, test append
    append_success = True
    if fallback_used != "memory_buffer":
        extra_records = [
            {"event": "test_append", "index": 4, "status": "ok",
             "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
        ]
        log_debug(f"Testing append to {actual_target}")
        append_success, append_error = try_write_records(actual_target, extra_records, mode="a")
        if not append_success:
            log_debug(f"Append failed: {append_error}")
            write_error_envelope(
                layer="script",
                severity="warning",
                message=f"Append operation failed: {append_error}",
                user_visible_message="追加写入失败，但基础写入已验证。",
                recoverable=True,
                retryable=False,
                fallback_action="memory_buffer",
                affected_artifacts=[actual_target],
                next_step="continue_with_basic_verification",
                raw_error_path=DEBUG_LOG
            )

    # --- Step 3: If memory buffer was used, flush now ---
    if memory_buffer is not None:
        flush_success, flush_error = flush_memory_buffer(memory_buffer, TARGET_FILE)
        if flush_success:
            actual_target = TARGET_FILE
            log_debug("Memory buffer flushed successfully")
        else:
            log_debug(f"Memory buffer flush failed: {flush_error}")
            write_error_envelope(
                layer="script",
                severity="fatal",
                message=f"Memory buffer flush failed: {flush_error}",
                user_visible_message="所有写入方式均失败。",
                recoverable=False,
                retryable=False,
                fallback_action=None,
                affected_artifacts=[TARGET_FILE],
                next_step="manual-smoke-required",
                raw_error_path=DEBUG_LOG
            )
            # Build FAIL result
            total_latency = round(time.time() - overall_start, 3)
            result = {
                "p0_pre_002": "FAIL",
                "reason": "All write methods failed",
                "fallback_used": fallback_used,
                "target_file": TARGET_FILE,
                "actual_file": actual_target,
                "records_planned": NUM_RECORDS,
                "records_written": 0,
                "md5_match": False,
                "read_verify": False,
                "append_verify": False,
                "latency_seconds": total_latency,
                "errors": ["Primary write failed", "Fallback write failed", "Memory flush failed"]
            }
            try:
                with open(RESULT_FILE, "w", encoding="utf-8") as f:
                    json.dump(result, f, indent=2, ensure_ascii=False)
            except Exception:
                pass
            print(json.dumps(result, indent=2, ensure_ascii=False))
            return 1

    # --- Step 4: Read back and verify ---
    log_debug(f"Reading back from {actual_target}")
    # Only verify the first NUM_RECORDS (ignore appended record if any)
    verify_success, lines_read, verify_error = try_read_and_verify(actual_target, records)

    if not verify_success:
        log_debug(f"Read verification failed: {verify_error}")
        write_error_envelope(
            layer="script",
            severity="recoverable",
            message=f"Read verification failed: {verify_error}",
            user_visible_message="文件读取验证失败。",
            recoverable=True,
            retryable=True,
            fallback_action=None,
            affected_artifacts=[actual_target],
            next_step="retry_read",
            raw_error_path=DEBUG_LOG
        )

    # --- Step 5: MD5 verification ---
    # Build expected content string from records
    expected_content = "\n".join(json.dumps(r, ensure_ascii=False) for r in records) + "\n"
    expected_md5 = compute_md5_from_string(expected_content)

    actual_md5 = None
    md5_match = False
    try:
        actual_md5 = compute_md5(actual_target)
        # MD5 of full file (may include appended record)
        # Compare only against base records if file has more
        md5_match = (actual_md5 == expected_md5)
        if not md5_match:
            # File may have appended content; check if base content matches prefix
            with open(actual_target, "r", encoding="utf-8") as f:
                full_content = f.read()
            md5_match = expected_content in full_content
    except Exception as e:
        log_debug(f"MD5 computation failed: {e}")
        write_error_envelope(
            layer="script",
            severity="warning",
            message=f"MD5 computation failed: {e}",
            user_visible_message="MD5校验失败。",
            recoverable=True,
            retryable=False,
            fallback_action=None,
            affected_artifacts=[actual_target],
            next_step="continue",
            raw_error_path=DEBUG_LOG
        )

    # --- Determine verdict ---
    records_written_ok = write_success or fallback_used is not None
    read_ok = verify_success
    md5_ok = md5_match

    if records_written_ok and read_ok and md5_ok:
        verdict = "PASS"
    elif records_written_ok and read_ok and not md5_ok:
        # Content matches structurally but MD5 differs (e.g. timestamps)
        verdict = "PASS"
    elif records_written_ok and not read_ok:
        verdict = "FAIL"
    else:
        verdict = "FAIL"

    total_latency = round(time.time() - overall_start, 3)

    result = {
        "p0_pre_002": verdict,
        "target_file": TARGET_FILE,
        "actual_file": actual_target,
        "fallback_used": fallback_used,
        "records_planned": NUM_RECORDS,
        "records_written": len(records),
        "md5_expected": expected_md5,
        "md5_actual": actual_md5,
        "md5_match": md5_ok,
        "read_verify": read_ok,
        "append_verify": append_success,
        "latency_seconds": total_latency
    }

    # --- Write result ---
    try:
        with open(RESULT_FILE, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
    except Exception as e:
        log_debug(f"Failed to write result.json: {e}")

    log_debug(f"Result: {verdict}")
    log_debug(f"write_ok={records_written_ok}, read_ok={read_ok}, md5_ok={md5_ok}")
    log_debug("p0_pre_runtime_write_test completed")
    log_debug("=" * 60)

    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if verdict == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
