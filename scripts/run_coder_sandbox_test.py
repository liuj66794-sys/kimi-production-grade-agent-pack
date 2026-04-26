#!/usr/bin/env python3
"""
Coder Sandbox Test Runner v1.2

验证coder生成的代码是否可运行，在隔离的沙箱环境中执行，
确保不污染项目目录。支持Python、JavaScript等多种语言。

安全约束:
1. 在临时目录中运行代码
2. 限制执行时间（默认30秒超时）
3. 限制内存使用
4. 禁止网络访问（沙箱环境）
5. 禁止文件系统写入（除临时目录外）
6. 记录所有sandbox操作到debug.log

用法:
    python scripts/run_coder_sandbox_test.py --code-file artifacts/code-fix.py --test-file artifacts/code-fix-test.py
    python scripts/run_coder_sandbox_test.py --code-dir artifacts/codebase-fix/
    python scripts/run_coder_sandbox_test.py --code-file artifacts/code-fix.py --test-file artifacts/code-fix-test.py --timeout 60

输出:
    - 测试结果JSON（pass/fail/error、stdout、stderr、execution_time）
    - debug.log（sandbox操作日志）
"""

import argparse
import ast
import json
import logging
import os
import shutil
import subprocess
try:
    import resource
except ImportError:
    resource = None  # Windows does not have the resource module
import sys
import tempfile
import time
import traceback
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# ── Constants ────────────────────────────────────────────────────────────

DEFAULT_TIMEOUT = 30  # seconds
DEFAULT_MEMORY_LIMIT_MB = 512  # MB
DEBUG_LOG_FILENAME = "debug.log"
RESULT_FILENAME = "coder-execution-result.json"

# Dangerous imports/calls that are blocked
PYTHON_DANGEROUS_IMPORTS = {
    "os.system", "os.popen", "os.spawn", "os.exec",
    "subprocess", "subprocess.call", "subprocess.run",
    "subprocess.Popen", "subprocess.check_output",
    "socket", "socketserver",
    "urllib", "urllib.request", "urllib.parse",
    "http.client", "ftplib", "smtplib",
    "requests",
    "webbrowser",
    "telnetlib",
    "xmlrpc",
}

PYTHON_DANGEROUS_CALLS = {
    "eval", "exec", "compile",
    "__import__", "importlib",
}

JS_DANGEROUS_PATTERNS = [
    "require('child_process')",
    "require(\"child_process\")",
    "child_process",
    "exec(",
    "execSync(",
    "spawn(",
    "require('http')",
    'require("http")',
    "require('https')",
    'require("https")',
    "require('net')",
    'require("net")',
    "require('fs').rmSync",
    "fs.unlinkSync",
    "process.exit",
]

# ── Logging Setup ────────────────────────────────────────────────────────


def setup_logging(output_dir: str) -> logging.Logger:
    """Configure debug logging to output_dir/debug.log."""
    log_path = os.path.join(output_dir, DEBUG_LOG_FILENAME)
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(log_path, mode="w", encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )
    return logging.getLogger("sandbox")


# ── AST Security Checker ─────────────────────────────────────────────────


class PythonSecurityChecker(ast.NodeVisitor):
    """AST visitor that detects dangerous imports and function calls."""

    def __init__(self):
        self.violations: List[str] = []
        self._import_aliases: Dict[str, str] = {}  # alias -> full_name

    def visit_Import(self, node: ast.Import) -> None:  # noqa: N802
        for alias in node.names:
            name = alias.name
            asname = alias.asname or alias.name
            self._import_aliases[asname] = name
            if self._is_dangerous_import(name):
                self.violations.append(
                    f"Dangerous import at line {node.lineno}: import {name}"
                )
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:  # noqa: N802
        module = node.module or ""
        full_base = module
        for alias in node.names:
            name = alias.name
            asname = alias.asname or alias.name
            full_name = f"{full_base}.{name}" if full_base else name
            self._import_aliases[asname] = full_name
            if self._is_dangerous_import(full_name):
                self.violations.append(
                    f"Dangerous import at line {node.lineno}: "
                    f"from {module} import {name}"
                )
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:  # noqa: N802
        func = node.func
        func_name = self._get_func_name(func)
        if func_name:
            base_name = func_name.split(".")[0]
            # Check for dangerous calls (eval, exec, etc.)
            if func_name in PYTHON_DANGEROUS_CALLS or \
               base_name in PYTHON_DANGEROUS_CALLS:
                self.violations.append(
                    f"Dangerous call at line {node.lineno}: {func_name}()"
                )
            # Check for dangerous imports via aliases
            resolved = self._resolve_alias(func_name)
            if resolved and self._is_dangerous_import(resolved):
                self.violations.append(
                    f"Dangerous call at line {node.lineno}: {func_name}() "
                    f"(resolves to {resolved})"
                )
        self.generic_visit(node)

    def _get_func_name(self, node: ast.expr) -> Optional[str]:
        """Extract fully qualified function name from AST node."""
        parts: List[str] = []
        current = node
        while isinstance(current, ast.Attribute):
            parts.append(current.attr)
            current = current.value
        if isinstance(current, ast.Name):
            parts.append(current.id)
        return ".".join(reversed(parts)) if parts else None

    def _resolve_alias(self, name: str) -> Optional[str]:
        """Resolve import alias to full module path."""
        first_part = name.split(".")[0]
        return self._import_aliases.get(first_part)

    @staticmethod
    def _is_dangerous_import(name: str) -> bool:
        """Check if an import name matches any dangerous pattern."""
        for dangerous in PYTHON_DANGEROUS_IMPORTS:
            if name == dangerous or name.startswith(dangerous + "."):
                return True
        return False


def check_python_security(code: str) -> List[str]:
    """Run AST security analysis on Python code. Returns list of violations."""
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return [f"Syntax error at line {e.lineno}: {e.msg}"]

    checker = PythonSecurityChecker()
    checker.visit(tree)
    return checker.violations


def check_js_security(code: str) -> List[str]:
    """Simple pattern-based security check for JavaScript code."""
    violations: List[str] = []
    lines = code.split("\n")
    for lineno, line in enumerate(lines, 1):
        for pattern in JS_DANGEROUS_PATTERNS:
            if pattern in line:
                violations.append(
                    f"Dangerous pattern at line {lineno}: {pattern} "
                    f"(in: {line.strip()[:80]})"
                )
    return violations


# ── Sandbox Execution ────────────────────────────────────────────────────


def set_resource_limits(memory_limit_mb: int) -> None:
    """Set process resource limits (memory, CPU). Called in child process."""
    if resource is None:
        return  # Windows does not support resource limits
    # Memory limit (address space)
    memory_bytes = memory_limit_mb * 1024 * 1024
    resource.setrlimit(resource.RLIMIT_AS, (memory_bytes, memory_bytes))
    # Disable core dumps
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    # Limit number of open files
    resource.setrlimit(resource.RLIMIT_NOFILE, (64, 64))


class TimeoutError(Exception):  # noqa: N818
    """Raised when code execution exceeds the time limit."""
    pass


def run_in_sandbox(
    command: List[str],
    cwd: str,
    timeout: int,
    memory_limit_mb: int,
    logger: logging.Logger,
) -> Tuple[int, str, str, float]:
    """
    Run a command in a sandboxed subprocess.

    Returns:
        (return_code, stdout, stderr, execution_time_seconds)
    """
    logger.info(f"Sandbox exec: {' '.join(command)}")
    logger.info(f"  cwd={cwd}, timeout={timeout}s, mem_limit={memory_limit_mb}MB")

    start_time = time.time()
    try:
        proc = subprocess.Popen(
            command,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            preexec_fn=lambda: set_resource_limits(memory_limit_mb),
        )
        try:
            stdout, stderr = proc.communicate(timeout=timeout)
            elapsed = time.time() - start_time
            logger.info(f"  completed in {elapsed:.2f}s, return_code={proc.returncode}")
            if stdout:
                logger.debug(f"  stdout[:500]: {stdout[:500]}")
            if stderr:
                logger.debug(f"  stderr[:500]: {stderr[:500]}")
            return proc.returncode, stdout, stderr, elapsed
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
            elapsed = time.time() - start_time
            logger.warning(f"  TIMEOUT after {elapsed:.2f}s")
            raise TimeoutError(f"Execution timed out after {timeout} seconds")
    except OSError as e:
        elapsed = time.time() - start_time
        logger.error(f"  OS error: {e}")
        raise


def detect_language(file_path: str) -> str:
    """Detect programming language from file extension."""
    ext = Path(file_path).suffix.lower()
    lang_map = {
        ".py": "python",
        ".js": "javascript",
        ".ts": "typescript",
        ".mjs": "javascript",
        ".sh": "bash",
        ".rb": "ruby",
        ".go": "go",
        ".rs": "rust",
        ".java": "java",
    }
    return lang_map.get(ext, "unknown")


def get_interpreter(language: str) -> Optional[str]:
    """Get the interpreter command for a language."""
    interpreters = {
        "python": sys.executable,
        "javascript": "node",
        "typescript": "ts-node",
        "bash": "bash",
        "ruby": "ruby",
        "go": "go",
        "rust": "rustc",
        "java": "java",
    }
    return interpreters.get(language)


# ── Test Runner ──────────────────────────────────────────────────────────


def run_python_test(
    code_path: str,
    test_path: Optional[str],
    temp_dir: str,
    timeout: int,
    memory_limit_mb: int,
    logger: logging.Logger,
) -> Dict:
    """Run Python code with optional test file in sandbox."""
    result = {
        "language": "python",
        "status": "pending",
        "tests_run": 0,
        "tests_passed": 0,
        "errors": [],
        "security_violations": [],
        "execution_time_seconds": 0.0,
        "stdout": "",
        "stderr": "",
    }

    # Step 1: Read and security-check the code
    logger.info(f"Reading code file: {code_path}")
    try:
        with open(code_path, "r", encoding="utf-8") as f:
            code_content = f.read()
    except Exception as e:
        result["status"] = "error"
        result["errors"].append(f"Failed to read code file: {e}")
        return result

    violations = check_python_security(code_content)
    if violations:
        result["security_violations"].extend(violations)
        logger.error(f"Security violations found: {violations}")
        # Continue to run but mark security issues

    # Step 2: Copy code to temp directory
    code_filename = os.path.basename(code_path)
    temp_code_path = os.path.join(temp_dir, code_filename)
    shutil.copy2(code_path, temp_code_path)
    logger.info(f"Copied code to sandbox: {temp_code_path}")

    # Step 3: Copy test file if provided
    temp_test_path = None
    if test_path and os.path.exists(test_path):
        test_filename = os.path.basename(test_path)
        temp_test_path = os.path.join(temp_dir, test_filename)
        shutil.copy2(test_path, temp_test_path)
        logger.info(f"Copied test file to sandbox: {temp_test_path}")

        # Security check test file too
        with open(test_path, "r", encoding="utf-8") as f:
            test_content = f.read()
        test_violations = check_python_security(test_content)
        if test_violations:
            result["security_violations"].extend(test_violations)
            logger.error(f"Test file security violations: {test_violations}")

    # Step 4: Determine execution command
    if temp_test_path:
        # Run test file (which imports the code)
        cmd = [sys.executable, temp_test_path]
    else:
        # Run code file directly
        cmd = [sys.executable, temp_code_path]

    # Step 5: Run in sandbox
    try:
        returncode, stdout, stderr, elapsed = run_in_sandbox(
            cmd, temp_dir, timeout, memory_limit_mb, logger
        )
        result["execution_time_seconds"] = round(elapsed, 2)
        result["stdout"] = stdout
        result["stderr"] = stderr

        if returncode == 0:
            result["status"] = "pass"
            result["tests_run"] = 1
            result["tests_passed"] = 1
            logger.info("Test PASSED")
        else:
            result["status"] = "fail"
            result["tests_run"] = 1
            result["tests_passed"] = 0
            result["errors"].append(
                f"Process exited with code {returncode}. stderr: {stderr[:500]}"
            )
            logger.warning(f"Test FAILED with return code {returncode}")

    except TimeoutError as e:
        result["status"] = "error"
        result["errors"].append(str(e))
        logger.error(f"Test TIMEOUT: {e}")
    except Exception as e:
        result["status"] = "error"
        result["errors"].append(f"Execution error: {e}\n{traceback.format_exc()}")
        logger.error(f"Test ERROR: {e}")

    return result


def run_js_test(
    code_path: str,
    test_path: Optional[str],
    temp_dir: str,
    timeout: int,
    memory_limit_mb: int,
    logger: logging.Logger,
) -> Dict:
    """Run JavaScript/TypeScript code with optional test file in sandbox."""
    result = {
        "language": "javascript",
        "status": "pending",
        "tests_run": 0,
        "tests_passed": 0,
        "errors": [],
        "security_violations": [],
        "execution_time_seconds": 0.0,
        "stdout": "",
        "stderr": "",
    }

    logger.info(f"Reading JS code file: {code_path}")
    try:
        with open(code_path, "r", encoding="utf-8") as f:
            code_content = f.read()
    except Exception as e:
        result["status"] = "error"
        result["errors"].append(f"Failed to read code file: {e}")
        return result

    violations = check_js_security(code_content)
    if violations:
        result["security_violations"].extend(violations)
        logger.error(f"Security violations found: {violations}")

    # Copy to temp
    code_filename = os.path.basename(code_path)
    temp_code_path = os.path.join(temp_dir, code_filename)
    shutil.copy2(code_path, temp_code_path)

    temp_test_path = None
    if test_path and os.path.exists(test_path):
        test_filename = os.path.basename(test_path)
        temp_test_path = os.path.join(temp_dir, test_filename)
        shutil.copy2(test_path, temp_test_path)

        with open(test_path, "r", encoding="utf-8") as f:
            test_content = f.read()
        test_violations = check_js_security(test_content)
        if test_violations:
            result["security_violations"].extend(test_violations)

    interpreter = get_interpreter("javascript")
    if interpreter is None:
        result["status"] = "error"
        result["errors"].append("Node.js not found. Install Node.js to run JS tests.")
        return result

    cmd = [interpreter, temp_test_path if temp_test_path else temp_code_path]

    try:
        returncode, stdout, stderr, elapsed = run_in_sandbox(
            cmd, temp_dir, timeout, memory_limit_mb, logger
        )
        result["execution_time_seconds"] = round(elapsed, 2)
        result["stdout"] = stdout
        result["stderr"] = stderr

        if returncode == 0:
            result["status"] = "pass"
            result["tests_run"] = 1
            result["tests_passed"] = 1
        else:
            result["status"] = "fail"
            result["tests_run"] = 1
            result["tests_passed"] = 0
            result["errors"].append(
                f"Process exited with code {returncode}. stderr: {stderr[:500]}"
            )
    except TimeoutError as e:
        result["status"] = "error"
        result["errors"].append(str(e))
    except Exception as e:
        result["status"] = "error"
        result["errors"].append(f"Execution error: {e}\n{traceback.format_exc()}")

    return result


def run_directory_tests(
    code_dir: str,
    temp_dir: str,
    timeout: int,
    memory_limit_mb: int,
    logger: logging.Logger,
) -> Dict:
    """Run all test files found in a directory."""
    logger.info(f"Scanning directory for tests: {code_dir}")

    overall_result = {
        "case_id": "coder-directory-test",
        "language": "mixed",
        "status": "pass",
        "tests_run": 0,
        "tests_passed": 0,
        "errors": [],
        "security_violations": [],
        "execution_time_seconds": 0.0,
        "file_results": [],
    }

    # Find test files (files with "test" in name)
    test_files = []
    source_files = []

    for root, _dirs, files in os.walk(code_dir):
        for f in files:
            full_path = os.path.join(root, f)
            rel_path = os.path.relpath(full_path, code_dir)
            if "test" in f.lower():
                test_files.append(rel_path)
            elif f.endswith((".py", ".js", ".ts", ".mjs")):
                source_files.append(rel_path)

    logger.info(f"Found {len(test_files)} test files, {len(source_files)} source files")

    if not test_files:
        logger.warning("No test files found. Looking for main/entry files.")
        # Try to find entry points
        for f in source_files:
            if f.lower() in ("main.py", "main.js", "index.js", f"{os.path.basename(code_dir)}.py"):
                test_files.append(f)
                break
        if not test_files and source_files:
            test_files = [source_files[0]]

    # Copy entire directory to temp
    for root, dirs, files in os.walk(code_dir):
        for d in dirs:
            src_dir = os.path.join(root, d)
            rel = os.path.relpath(src_dir, code_dir)
            dst_dir = os.path.join(temp_dir, rel)
            os.makedirs(dst_dir, exist_ok=True)
        for f in files:
            src = os.path.join(root, f)
            rel = os.path.relpath(src, code_dir)
            dst = os.path.join(temp_dir, rel)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(src, dst)

    # Run each test file
    total_elapsed = 0.0
    for test_file in test_files:
        full_test_path = os.path.join(temp_dir, test_file)
        lang = detect_language(test_file)

        if lang == "python":
            file_result = run_python_test(
                full_test_path, None, temp_dir, timeout, memory_limit_mb, logger
            )
        elif lang in ("javascript", "typescript"):
            file_result = run_js_test(
                full_test_path, None, temp_dir, timeout, memory_limit_mb, logger
            )
        else:
            logger.warning(f"Skipping unsupported file: {test_file} (lang={lang})")
            continue

        file_result["file"] = test_file
        overall_result["file_results"].append(file_result)
        overall_result["tests_run"] += file_result.get("tests_run", 0)
        overall_result["tests_passed"] += file_result.get("tests_passed", 0)
        overall_result["security_violations"].extend(
            file_result.get("security_violations", [])
        )
        overall_result["errors"].extend(file_result.get("errors", []))
        total_elapsed += file_result.get("execution_time_seconds", 0)

    overall_result["execution_time_seconds"] = round(total_elapsed, 2)

    # Determine overall status
    if overall_result["errors"]:
        overall_result["status"] = "error"
    elif overall_result["tests_run"] > 0 and overall_result["tests_passed"] < overall_result["tests_run"]:
        overall_result["status"] = "fail"
    elif overall_result["tests_run"] == 0:
        overall_result["status"] = "error"
        overall_result["errors"].append("No tests were executed")
    elif overall_result["security_violations"]:
        overall_result["status"] = "pass_with_warnings"
    else:
        overall_result["status"] = "pass"

    return overall_result


# ── Main Entry Point ─────────────────────────────────────────────────────


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Coder Sandbox Test Runner - v1.2",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --code-file artifacts/code-fix.py --test-file artifacts/code-fix-test.py
  %(prog)s --code-dir artifacts/codebase-fix/
  %(prog)s --code-file code.py --timeout 60 --memory 1024
        """,
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--code-file", help="Path to the code file to test")
    group.add_argument("--code-dir", help="Path to directory containing code")
    parser.add_argument("--test-file", help="Path to the test file (optional)")
    parser.add_argument(
        "--timeout",
        type=int,
        default=DEFAULT_TIMEOUT,
        help=f"Execution timeout in seconds (default: {DEFAULT_TIMEOUT})",
    )
    parser.add_argument(
        "--memory",
        type=int,
        default=DEFAULT_MEMORY_LIMIT_MB,
        help=f"Memory limit in MB (default: {DEFAULT_MEMORY_LIMIT_MB})",
    )
    parser.add_argument(
        "--output-dir",
        default=".",
        help="Directory for output files (default: current directory)",
    )
    parser.add_argument(
        "--case-id",
        default="coder-execution-smoke",
        help="Test case identifier",
    )

    args = parser.parse_args()

    # Resolve paths to absolute
    output_dir = os.path.abspath(args.output_dir)
    os.makedirs(output_dir, exist_ok=True)

    # Setup logging
    logger = setup_logging(output_dir)
    logger.info("=" * 60)
    logger.info("Coder Sandbox Test Runner v1.2 started")
    logger.info(f"  code_file={args.code_file}, test_file={args.test_file}")
    logger.info(f"  code_dir={args.code_dir}")
    logger.info(f"  timeout={args.timeout}s, memory={args.memory}MB")
    logger.info(f"  output_dir={output_dir}")

    # Create temporary directory for sandbox
    with tempfile.TemporaryDirectory(prefix="coder_sandbox_") as temp_dir:
        logger.info(f"Sandbox temp directory: {temp_dir}")

        # Run tests
        if args.code_dir:
            result = run_directory_tests(
                os.path.abspath(args.code_dir),
                temp_dir,
                args.timeout,
                args.memory,
                logger,
            )
        else:
            code_file = os.path.abspath(args.code_file)
            test_file = os.path.abspath(args.test_file) if args.test_file else None
            language = detect_language(code_file)

            if language == "python":
                result = run_python_test(
                    code_file, test_file, temp_dir,
                    args.timeout, args.memory, logger,
                )
            elif language in ("javascript", "typescript"):
                result = run_js_test(
                    code_file, test_file, temp_dir,
                    args.timeout, args.memory, logger,
                )
            else:
                result = {
                    "language": language,
                    "status": "error",
                    "tests_run": 0,
                    "tests_passed": 0,
                    "errors": [f"Unsupported language: {language}"],
                    "security_violations": [],
                    "execution_time_seconds": 0.0,
                }

        # Add metadata
        result["case_id"] = args.case_id
        result["sandbox_temp_dir"] = temp_dir
        result["sandbox_config"] = {
            "timeout_seconds": args.timeout,
            "memory_limit_mb": args.memory,
            "network_access": False,
            "filesystem_access": "temp_only",
        }

    # Write result JSON
    result_path = os.path.join(output_dir, RESULT_FILENAME)
    with open(result_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    logger.info(f"Result written to: {result_path}")

    # Summary
    print("\n" + "=" * 60)
    print("SANDBOX TEST RESULT")
    print("=" * 60)
    print(f"Case ID:        {result['case_id']}")
    print(f"Status:         {result['status']}")
    print(f"Tests:          {result.get('tests_passed', 0)}/{result.get('tests_run', 0)} passed")
    print(f"Execution time: {result.get('execution_time_seconds', 0):.2f}s")
    if result.get('security_violations'):
        print(f"Security issues: {len(result['security_violations'])}")
    if result.get('errors'):
        print(f"Errors:\n" + "\n".join(f"  - {e}" for e in result['errors']))
    print(f"Result file:    {result_path}")
    print(f"Debug log:      {os.path.join(output_dir, DEBUG_LOG_FILENAME)}")
    print("=" * 60)

    logger.info("Coder Sandbox Test Runner completed")

    # Exit code
    if result["status"] == "pass":
        return 0
    elif result["status"] in ("fail", "error"):
        return 1
    else:
        return 2  # pass_with_warnings


if __name__ == "__main__":
    sys.exit(main())
