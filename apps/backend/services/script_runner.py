"""
Script Runner Service - Secure script execution layer.

This is the ONLY module that directly executes scripts/*.py files.
All execution goes through ALLOWED_SCRIPTS whitelist validation.
UI must NEVER call scripts directly - always use /api/jobs/run-script endpoint.

Security features:
1. Whitelist validation (script name must be in ALLOWED_SCRIPTS)
2. Path validation (script must exist in scripts/ directory)
3. Timeout control (prevent runaway processes)
4. Output truncation (prevent memory exhaustion)
5. Audit logging (all executions recorded)
6. Concurrency limiting (via JobStateService)
"""

import os
import subprocess
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List

# Import config
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import (
    ALLOWED_SCRIPTS_SET,
    SCRIPTS_DIR,
    BASE_DIR,
    SCRIPT_TIMEOUT,
    MAX_STDOUT_LENGTH,
    MAX_STDERR_LENGTH,

)

logger = logging.getLogger(__name__)


class ScriptNotAllowedError(Exception):
    """Raised when a script is not in the whitelist."""
    pass


class ScriptNotFoundError(Exception):
    """Raised when a script file does not exist."""
    pass


class ScriptTimeoutError(Exception):
    """Raised when script execution exceeds timeout."""
    pass


class ScriptRunnerService:
    """
    Secure script execution service.

    All script execution MUST go through this service.
    Never execute scripts directly from router handlers.
    """

    def __init__(
        self,
        scripts_dir: str = SCRIPTS_DIR,
        base_dir: str = BASE_DIR,
        timeout: int = SCRIPT_TIMEOUT,
    ):
        self.scripts_dir = scripts_dir
        self.base_dir = base_dir
        self.timeout = timeout

    def _validate_script(self, script_name: str) -> str:
        """
        Validate script name against whitelist and verify file exists.

        Args:
            script_name: Name of the script (e.g. 'release_check.py')

        Returns:
            Absolute path to the script

        Raises:
            ScriptNotAllowedError: If script not in whitelist
            ScriptNotFoundError: If script file doesn't exist
        """
        # Must end with .py
        if not script_name.endswith(".py"):
            raise ScriptNotAllowedError(
                f"Script must be a .py file: {script_name}"
            )

        # Must be in whitelist
        if script_name not in ALLOWED_SCRIPTS_SET:
            raise ScriptNotAllowedError(
                f"Script '{script_name}' not in allowlist. "
                f"Allowed: {sorted(ALLOWED_SCRIPTS_SET)}"
            )

        # Must exist on disk
        script_path = os.path.join(self.scripts_dir, script_name)
        if not os.path.exists(script_path):
            raise ScriptNotFoundError(
                f"Script file not found: {script_path}"
            )

        # Must be a file (not directory)
        if not os.path.isfile(script_path):
            raise ScriptNotFoundError(
                f"Script path is not a file: {script_path}"
            )

        return script_path

    def _build_command(
        self,
        script_path: str,
        params: Optional[Dict[str, Any]] = None
    ) -> List[str]:
        """
        Build the command list from script path and parameters.

        Args:
            script_path: Absolute path to the script
            params: Dictionary of --key=value parameters

        Returns:
            Command list for subprocess
        """
        # Use relative path from base_dir for cwd context
        rel_script = os.path.relpath(script_path, self.base_dir)
        cmd = ["python", rel_script]

        if params:
            for key, value in params.items():
                # Convert booleans to flags
                if isinstance(value, bool):
                    if value:
                        cmd.append(f"--{key}")
                # Convert lists to repeated flags
                elif isinstance(value, list):
                    for v in value:
                        cmd.append(f"--{key}={v}")
                else:
                    cmd.append(f"--{key}={value}")

        return cmd

    def _log_audit(
        self,
        script_name: str,
        params: Dict[str, Any],
        returncode: Optional[int] = None,
        error: Optional[str] = None,
    ) -> None:
        """
        Record script execution in audit log.

        Args:
            script_name: Name of executed script
            params: Parameters passed to script
            returncode: Process return code if completed
            error: Error message if failed
        """
        try:
            from db import get_connection, execute, commit
            with get_connection() as conn:
                execute(
                    conn,
                    """
                        INSERT INTO audit_log (event_type, actor, action, details)
                        VALUES (?, ?, ?, ?)
                    """,
                    (
                        "script_execution",
                        "dashboard_user",
                        script_name,
                        json.dumps({
                            "params": params,
                            "returncode": returncode,
                            "error": error,
                            "timestamp": datetime.utcnow().isoformat(),
                        }),
                    ),
                )
                commit(conn)
        except Exception as e:
            logger.error(f"Failed to write audit log: {e}")

    def run(
        self,
        script_name: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Execute a whitelisted script with parameters.

        This is the main entry point for script execution.
        ALL callers must go through this method.

        Args:
            script_name: Name of the script (e.g. 'release_check.py')
            params: Dictionary of parameters passed as --key=value

        Returns:
            Dictionary with execution results:
            {
                "script": str,          # Script name
                "returncode": int,      # Process exit code
                "stdout": str,          # Captured stdout (truncated)
                "stderr": str | None,   # Captured stderr (truncated)
                "duration_ms": float,   # Execution time in milliseconds
                "success": bool,        # True if returncode == 0
            }

        Raises:
            ScriptNotAllowedError: If script not in whitelist
            ScriptNotFoundError: If script file doesn't exist
            ScriptTimeoutError: If execution exceeds timeout
        """
        params = params or {}

        # 1. Validate
        script_path = self._validate_script(script_name)

        # 2. Build command
        cmd = self._build_command(script_path, params)

        logger.info(f"Executing: {' '.join(cmd)} in {self.base_dir}")

        # 3. Execute with timeout
        start_time = datetime.utcnow()
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                cwd=self.base_dir,
            )
            duration_ms = (
                datetime.utcnow() - start_time
            ).total_seconds() * 1000

            # 4. Truncate output
            stdout = result.stdout[:MAX_STDOUT_LENGTH] if result.stdout else ""
            stderr = result.stderr[:MAX_STDERR_LENGTH] if result.stderr else None

            # 5. Log audit
            self._log_audit(script_name, params, result.returncode)

            return {
                "script": script_name,
                "returncode": result.returncode,
                "stdout": stdout,
                "stderr": stderr,
                "duration_ms": round(duration_ms, 2),
                "success": result.returncode == 0,
            }

        except subprocess.TimeoutExpired as e:
            duration_ms = (
                datetime.utcnow() - start_time
            ).total_seconds() * 1000
            self._log_audit(
                script_name, params, error=f"Timeout after {self.timeout}s"
            )
            raise ScriptTimeoutError(
                f"Script '{script_name}' timed out after {self.timeout} seconds. "
                f"Partial stdout: {e.stdout[:500] if e.stdout else 'N/A'}"
            )

        except Exception as e:
            self._log_audit(script_name, params, error=str(e))
            raise

    def run_async(
        self,
        script_name: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> subprocess.Popen:
        """
        Start a script asynchronously (non-blocking).

        Args:
            script_name: Name of the script
            params: Dictionary of parameters

        Returns:
            subprocess.Popen object for monitoring

        Raises:
            ScriptNotAllowedError: If script not in whitelist
            ScriptNotFoundError: If script file doesn't exist
        """
        params = params or {}
        script_path = self._validate_script(script_name)
        cmd = self._build_command(script_path, params)

        logger.info(f"Starting async: {' '.join(cmd)}")

        self._log_audit(script_name, params)

        return subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=self.base_dir,
        )


# Singleton instance
script_runner = ScriptRunnerService()
