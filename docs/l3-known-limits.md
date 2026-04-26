# L3 Known Limits

This document tracks known limitations of the Kimi Production-Grade Agent System v3.x L3 layer.

## Current Limits

### KL-L3-001: Audit Log v3.0
- **Description**: Audit Log v3.0 uses a plain-text log format.
- **Impact**: Structured querying and filtering of audit events are limited.
- **Resolution**: Schema-based audit log (v3.1) will be introduced before v3.1 release.
- **Workaround**: Parse text logs with grep/awk for manual inspection.

### KL-L3-002: Streamlit Dashboard Scope
- **Description**: Streamlit dashboard (`apps/dashboard.py`) is provided for local rapid validation only.
- **Impact**: Not suitable for production deployment; no multi-user support; no persistent sessions.
- **Resolution**: Use Next.js frontend (`apps/frontend/`) for production deployments.
- **Workaround**: Run `streamlit run apps/dashboard.py` locally for quick checks.

### KL-L3-003: SQLite Single-Table Storage
- **Description**: v3.0 uses a single SQLite table for state persistence.
- **Impact**: May become a bottleneck for high-concurrency scenarios; limited scalability.
- **Resolution**: Migration to PostgreSQL is planned for v3.x (post-v3.0).
- **Workaround**: Backup SQLite database file regularly; monitor file size.

### KL-L3-004: Memory Review UI Read-Only
- **Description**: The Memory Review UI is read-only and does not support approve/reject operations.
- **Impact**: Memory candidates must be approved/rejected via backend API or CLI.
- **Resolution**: Full approve/reject UI will be added in v3.1.
- **Workaround**: Use the backend API endpoint directly for memory operations.

### KL-L3-005: Next.js Frontend Requires Backend
- **Description**: The Next.js frontend is a pure UI layer and requires the FastAPI backend to be running.
- **Impact**: Frontend cannot function independently; all data flows through `/api/*` endpoints.
- **Resolution**: None required -- this is by design.

### KL-L3-006: No Real-Time WebSocket Updates
- **Description**: v3.0 uses polling for run status and task board updates.
- **Impact**: Updates may have a delay of up to the polling interval (default 5s).
- **Resolution**: WebSocket support will be added in v3.1 for real-time push updates.

### KL-L3-007: Script Console Whitelist Only
- **Description**: The Script Console only supports whitelisted scripts.
- **Impact**: Arbitrary script execution is blocked for security.
- **Resolution**: Expand whitelist via backend configuration as needed.

### KL-L3-008: Browser Automation in CI
- **Description**: Playwright-based browser automation tests require specific container setup.
- **Impact**: CI pipeline must include browser installation step.
- **Resolution**: Documented in `l3-deployment.md`; use `mcr.microsoft.com/playwright` image.

## Historical / Resolved

None yet.

## How to Update

When you encounter a new limit:
1. Open `docs/l3-known-limits.md`
2. Add a new entry following the format above
3. Include: Description, Impact, Resolution/Plan, Workaround
