# Quick Start Guide

> **Version**: v1.3.0 (L1 MVP Release)  
> **Estimated Time**: 10 minutes  
> **Prerequisites**: Python 3.11+, Kimi Code CLI

---

## Step 1: Environment Preparation

### Check Python Version

```powershell
python --version
# Must be 3.11 or higher```

### Check Kimi Code CLI

```powershell
kimi --version
# Should show latest stable version```

### Verify Git

```powershell
git --version```

---

## Step 2: Install the Agent Pack

### Clone Repository

```powershell
git clone <repository-url> kimi-production-grade-agent-pack
cd kimi-production-grade-agent-pack```

### Create Virtual Environment

```powershell
python -m venv .venv
.venv\Scripts\activate```

### Install Dependencies

```powershell
pip install --upgrade pip
pip install -r requirements.txt```

### Verify Directory Structure

```powershell
Get-ChildItem -Path 'agents/ skills/ schemas/ scripts/ evals/ examples/```'

You should see all directories listed without errors.

---

## Step 3: First Run (Guided Mode)

The guided-run mode walks you through your first agent execution.

### Run Guided Setup

```powershell
python scripts/release_check.py --level l1```

Expected output:
```
=== Kimi Agent Pack Release Check ===
Version: v1.3.0
Level: l1
[INFO] Checking directory structure... PASS
[INFO] Checking required files... PASS
[INFO] Checking Python scripts... PASS
[INFO] Checking JSON schemas... PASS
[INFO] Checking VERSION format... PASS
[INFO] Checking SKILL.md frontmatter... PASS
----------------------------------------
Result: PASS (6/6 checks)
Exit code: 0
```

### Run a Single Agent

The `kimi` CLI does not have a `run` subcommand. Use `--agent-file` to load a custom agent specification:

```powershell
# Interactive mode with researcher agent
kimi --agent-file agents/researcher-sub.yaml --prompt (Get-Content examples/deep-research-example/input.txt -Raw)

# Non-interactive print mode
kimi --agent-file agents/researcher-sub.yaml --print --prompt (Get-Content examples/deep-research-example/input.txt -Raw)

# Or use the production coordinator for full multi-agent orchestration
kimi --agent-file agents/production-coordinator.yaml --prompt (Get-Content examples/deep-research-example/input.txt -Raw)
```

Follow the interactive prompts to complete your first run.

---

## Step 4: Run Unit-Smoke Tests

Unit-smoke tests verify individual components in isolation.

### Run All Unit-Smoke Tests

```powershell
python -m pytest evals/unit-smoke/ -v --tb=short```

### Run a Specific Test

```powershell
python -m pytest evals/unit-smoke/test_error_envelope.py -v```

### Expected Output

```
========================= test session starts ==========================
platform linux -- Python 3.11.x
collected 12 items

evals/unit-smoke/test_error_envelope.py::test_schema_valid ... PASSED
evals/unit-smoke/test_task_event.py::test_event_creation ... PASSED
evals/unit-smoke/test_qa_gate.py::test_gate_pass ... PASSED
...
========================== 12 passed in 0.5s ==========================
```

---

## Step 5: Run Integration-Smoke Tests

Integration-smoke tests verify end-to-end workflows.

### Run Integration Tests

```powershell
python evals/integration-smoke-runner.py --output evals/results/integration-smoke```

### Run with Verbose Output

```powershell
python evals/integration-smoke-runner.py --verbose```

### Expected Output

```
=== Integration Smoke Runner ===
[INFO] Loading task suite from evals/task-suite.yaml
[INFO] Found 5 integration tests
[INFO] Running test: deep-research-e2e ... PASS
[INFO] Running test: ppt-generation-e2e ... PASS
[INFO] Running test: spreadsheet-e2e ... PASS
[INFO] Running test: codebase-fix-e2e ... PASS
[INFO] Running test: document-to-skill-e2e ... PASS
----------------------------------------
Results: 5/5 passed
Exit code: 0
```

---

## Step 6: View Results

### Check Generated Artifacts

```powershell
Get-ChildItem -Path 'artifacts/```'

### View Test Reports

```powershell
Get-Content 'evals/results/integration-smoke/report.json```'
### View Debug Log

```powershell
Get-Content 'runtime/debug.log | tail -50```'
### Check QA Gate Results

```powershell
Get-Content 'artifacts/qa-gate-result.json```'
---

## Step 7: Common Issues & Fixes

### Issue: `ModuleNotFoundError` on test run

**Fix:**
```powershell
pip install -r requirements.txt
$env:PYTHONPATH="${env:PYTHONPATH};$(Get-Location)"
```

### Issue: Permission denied on scripts

**Fix:**
```powershell
# PowerShell: 脚本无需 chmod 即可直接运行
```

### Issue: JSON schema validation fails

**Fix:**
```powershell
pip install jsonschema
python -c "import jsonschema; print(jsonschema.__version__)"
```

### Issue: Kimi CLI not found

**Fix:**
```powershell
# The Kimi Code CLI is installed by the VS Code extension.
# Add it to your PATH (Windows):
$kimiPath = "$env:USERPROFILE\AppData\Roaming\Code\User\globalStorage\moonshot-ai.kimi-code\bin\kimi"
[Environment]::SetEnvironmentVariable("Path", $env:Path + ";$kimiPath", "User")

# Or use the full path directly:
& "$env:USERPROFILE\AppData\Roaming\Code\User\globalStorage\moonshot-ai.kimi-code\bin\kimi\kimi.exe" --version
```

---

## Next Steps

- Read [DESIGN.md](DESIGN.md) for architecture details
- Explore [examples/](examples/) for usage patterns
- Read [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for advanced debugging
- Run `python scripts/release_check.py --strict` for full validation

---

## Quick Reference

| Command | Purpose |
|---------|---------|
| `python scripts/release_check.py --level l1` | Basic validation |
| `python scripts/release_check.py --strict` | Full validation |
| `python -m pytest evals/unit-smoke/ -v` | Unit smoke tests |
| `python evals/integration-smoke-runner.py` | Integration tests |
| `python scripts/regression_runner.py --suite l1-regression` | Regression suite |
| `python scripts/clean_runtime_artifacts.py --dry-run` | Preview cleanup |
| `python scripts/package_l1_release.py --version v1.3.0` | Package release |

---

*Got issues? See [TROUBLESHOOTING.md](TROUBLESHOOTING.md)*

