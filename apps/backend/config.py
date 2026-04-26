"""
Kimi Agent Pack Dashboard API - Configuration Module

Contains all application settings including:
- Allowed script whitelist
- Database path configuration
- CORS settings
- Timeout and concurrency limits

Security: ALL script execution paths go through ALLOWED_SCRIPTS.
UI must NEVER call scripts directly - always use /api/jobs/run-script endpoint.
"""

import os
from typing import List, Set


# =============================================================================
# Security - Script Execution Whitelist
# =============================================================================
# CRITICAL: Only scripts in this list may be executed via /api/jobs/run-script.
# UI must NEVER bypass this list by calling scripts directly.
# Adding a script here requires security review.
ALLOWED_SCRIPTS: List[str] = [
    # L1 - Research & Report Pipeline
    "release_check.py",
    "regression_runner.py",
    "eval_runner.py",
    "check_hard_fail.py",
    "validate_artifacts.py",
    "guided_run.py",
    "check_report_quality.py",

    # L2 - Multi-Agent & Memory Pipeline
    "l2_pre_gate.py",
    "l2_release_check.py",
    "l2_regression_runner.py",

    # L3 - Production-Grade Pipeline (future)
    # "l3_release_check.py",
    # "l3_regression_runner.py",
]

# Fast lookup set
ALLOWED_SCRIPTS_SET: Set[str] = set(ALLOWED_SCRIPTS)

# =============================================================================
# Paths
# =============================================================================
# Base directory (repo root, two levels up from apps/backend/)
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

# Database
# Priority: DATABASE_URL (production PostgreSQL) > KIMI_DB_PATH (legacy/local SQLite)
DATABASE_URL = os.environ.get("DATABASE_URL")
DB_PATH = os.environ.get(
    "KIMI_DB_PATH",
    os.path.join(os.path.dirname(__file__), "data", "dashboard.db")
)
if not DATABASE_URL:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

# Scripts directory (relative to BASE_DIR)
SCRIPTS_DIR = os.path.join(BASE_DIR, "scripts")

# Runtime directory
RUNTIME_DIR = os.path.join(BASE_DIR, "runtime")

# Memory directory
MEMORY_DIR = os.path.join(BASE_DIR, "memory")

# Skills directory
SKILLS_DIR = os.path.join(BASE_DIR, "skills")

# Eval results directory
EVALS_DIR = os.path.join(BASE_DIR, "evals", "results")

# Artifacts directory
ARTIFACTS_DIR = os.path.join(BASE_DIR, "artifacts")

# =============================================================================
# CORS Configuration
# =============================================================================
CORS_ORIGINS: List[str] = [
    "http://localhost:3000",   # Next.js dev server
    "http://localhost:8501",   # Streamlit dev server
    "http://localhost:5173",   # Vite dev server
]

# Allow additional origins from environment
_extra_origins = os.environ.get("KIMI_CORS_ORIGINS", "")
if _extra_origins:
    CORS_ORIGINS.extend([o.strip() for o in _extra_origins.split(",") if o.strip()])

CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_METHODS = ["*"]
CORS_ALLOW_HEADERS = ["*"]

# =============================================================================
# Execution Limits
# =============================================================================
# Maximum concurrent script executions (SQLite single-table queue)
MAX_CONCURRENT_JOBS = int(os.environ.get("KIMI_MAX_CONCURRENT_JOBS", "3"))

# Script execution timeout in seconds
SCRIPT_TIMEOUT = int(os.environ.get("KIMI_SCRIPT_TIMEOUT", "300"))

# Job queue orphan cleanup threshold (seconds)
JOB_ORPHAN_THRESHOLD = int(os.environ.get("KIMI_JOB_ORPHAN_THRESHOLD", "600"))

# Maximum stdout/stderr capture length
MAX_STDOUT_LENGTH = int(os.environ.get("KIMI_MAX_STDOUT_LENGTH", "5000"))
MAX_STDERR_LENGTH = int(os.environ.get("KIMI_MAX_STDERR_LENGTH", "2000"))

# =============================================================================
# API Settings
# =============================================================================
API_TITLE = "Kimi Agent Pack Dashboard API"
API_VERSION = "3.0.0"
API_HOST = os.environ.get("KIMI_API_HOST", "0.0.0.0")
API_PORT = int(os.environ.get("KIMI_API_PORT", "8000"))

# =============================================================================
# Project Defaults
# =============================================================================
DEFAULT_PROJECT_NAME = "default"
DEFAULT_PROJECT_STAGE = "l1"  # l1 | l2 | l3
DEFAULT_PROJECT_STATUS = "active"
