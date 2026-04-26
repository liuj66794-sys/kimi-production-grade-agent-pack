# Troubleshooting Guide

> **Version**: v1.3.0  
> **Scope**: Error diagnosis, recovery procedures, and debug techniques

---

## Error Taxonomy (E001-E010)

### E001: SDK Unavailable → CLI Fallback

| Field | Description |
|-------|-------------|
| **Symptom** | `ModuleNotFoundError: kimi_sdk` or `SDK connection timeout` |
| **Error Code** | `E001` |
| **Severity** | Warning |

**Root Causes:**
1. Kimi SDK not installed in virtual environment
2. SDK version mismatch between agent pack and installed SDK
3. Network issue preventing SDK initialization
4. Corrupted SDK installation

**Resolution Steps:**

```powershell
# Step 1: Verify SDK installation
pip list | Select-String -Pattern 'kimi'
# Step 2: Reinstall SDK if missing
pip install --upgrade kimi-sdk

# Step 3: Verify version compatibility
python -c "import kimi_sdk; print(kimi_sdk.__version__)"

# Step 4: Check network connectivity
python -c "import kimi_sdk; kimi_sdk.ping()"```

**CLI Fallback:**

If SDK remains unavailable, the system automatically falls back to CLI mode:

```powershell
$env:KIMI_MODE=cli
kimi --agent-file agents/<agent-name>.yaml --prompt (Get-Content <input-file> -Raw)```

**Verification:**

```powershell
python -c "from agents.utils import sdk_available; print(sdk_available())"
# Expected: False (with fallback active)```

---

### E002: Runtime Write Permission Denied

| Field | Description |
|-------|-------------|
| **Symptom** | `PermissionError: [Errno 13] Permission denied: 'runtime/...'` |
| **Error Code** | `E002` |
| **Severity** | Error |

**Root Causes:**
1. Directory owned by different user
2. Read-only filesystem
3. SELinux/AppArmor restrictions
4. Directory permissions not set correctly

**Resolution Steps:**

```powershell
# Step 1: Check directory ownership
Get-ChildItem -Path 'runtime/', 'artifacts/'

# Step 2: Fix ownership (if needed)
# PowerShell: 以管理员身份运行或确认目录权限

# Step 3: Fix permissions
icacls 'runtime/' /grant Users:F
icacls 'artifacts/' /grant Users:F

# Step 4: Verify write access
New-Item -Path 'runtime/.write_test' -ItemType File
Remove-Item 'runtime/.write_test'
```

**Alternative:** Use custom directories:

```powershell
$env:KIMI_RUNTIME_DIR="$env:TEMP\kimi-runtime"
$env:KIMI_ARTIFACTS_DIR="$env:TEMP\kimi-artifacts"
New-Item -Path $env:KIMI_RUNTIME_DIR -ItemType Directory -Force
New-Item -Path $env:KIMI_ARTIFACTS_DIR -ItemType Directory -Force
---

### E003: Schema Validation Failed

| Field | Description |
|-------|-------------|
| **Symptom** | `jsonschema.ValidationError: 'field' is a required property` |
| **Error Code** | `E003` |
| **Severity** | Error |

**Root Causes:**
1. Agent output missing required fields
2. Schema version mismatch (agent uses old schema)
3. Custom schema not registered
4. Type mismatch in output values

**Resolution Steps:**

```powershell
# Step 1: Identify failing schema
Get-Content 'runtime/errors.jsonl' | Select-String -Pattern 'E003'

# Step 2: Validate specific file against schema
python -c "
import json, jsonschema
with open('schemas/error-envelope.json') as f:
    schema = json.load(f)
with open('artifacts/output.json') as f:
    data = json.load(f)
jsonschema.validate(data, schema)
print('Valid!')
"

# Step 3: Check schema version
Get-Content 'schemas/error-envelope.json' | Select-String -Pattern 'version```'

**Fix invalid output:**

```python
# Add missing required fields
from agents.utils import validate_output
output = validate_output(raw_output, schema_name="error-envelope")
```

---

### E004: Structured Output Parse Fail

| Field | Description |
|-------|-------------|
| **Symptom** | `JSONDecodeError: Expecting property name enclosed in double quotes` |
| **Error Code** | `E004` |
| **Severity** | Error |

**Root Causes:**
1. LLM output is not valid JSON
2. Output contains markdown formatting (```json blocks)
3. Truncated output due to token limits
4. Special characters not properly escaped

**Resolution Steps:**

```powershell
# Step 1: View raw output
Get-Content 'artifacts/raw-output.txt

# Step 2: Try parsing with cleanup
python -c "
import json, re
text = open('artifacts/raw-output.txt').read()
# Remove markdown code blocks
text = re.sub(r'\`\`\`json\s*', '', text)
text = re.sub(r'\`\`\`\s*$', '', text)
data = json.loads(text)
print(json.dumps(data, indent=2))
"```

**Parser fallback:**

```python
from agents.utils import parse_structured_output
result = parse_structured_output(raw_text, schema_hint="json")
```

---

### E005: Hard Fail Detected

| Field | Description |
|-------|-------------|
| **Symptom** | `HARD_FAIL: Critical error in agent execution pipeline` |
| **Error Code** | `E005` |
| **Severity** | Critical |

**Root Causes:**
1. Unhandled exception in agent core logic
2. Dependency service unavailable (LLM API, file system)
3. Invalid agent configuration
4. Timeout on critical operation

**Resolution Steps:**

```powershell
# Step 1: Check the full error trace
Get-Content 'runtime/errors.jsonl | grep E005 | tail -1' | ConvertFrom-Json | ConvertTo-Json
# Step 2: Check debug log for context
Get-Content 'runtime/debug.log' | Select-String -Pattern '-A 20 "HARD_FAIL"'

# Step 3: Verify agent configuration
python -c "
import yaml
with open('agents/researcher-sub.yaml') as f:
    config = yaml.safe_load(f)
print(yaml.dump(config, default_flow_style=False))
"```

**Recovery:**

```powershell
# Retry with increased timeout
$env:KIMI_TIMEOUT=300
kimi --agent-file agents/<agent>.yaml --prompt (Get-Content <file> -Raw)```

---

### E006: QA Gate Blocked

| Field | Description |
|-------|-------------|
| **Symptom** | `QA_GATE_BLOCKED: Quality checks failed` |
| **Error Code** | `E006` |
| **Severity** | Warning |

**Root Causes:**
1. Output does not meet minimum quality threshold
2. Missing required sections in output
3. Evidence insufficient for claims
4. Format compliance check failed

**Resolution Steps:**

```powershell
# Step 1: View QA gate results
Get-Content 'artifacts/qa-gate-result.json' | ConvertFrom-Json | ConvertTo-Json
# Step 2: Check which checks failed
Get-Content 'artifacts/qa-gate-result.json' | ConvertFrom-Json | Select-Object -Property '.failed_checks'
# Step 3: Run with lower threshold (dev only)
$env:QA_GATE_THRESHOLD=0.6  # default: 0.8
kimi --agent-file agents/<agent>.yaml --prompt (Get-Content <file> -Raw)```

---

### E007: Task Event Write Failed

| Field | Description |
|-------|-------------|
| **Symptom** | `OSError: Cannot write task event: disk full or permission denied` |
| **Error Code** | `E007` |
| **Severity** | Error |

**Root Causes:**
1. Disk full
2. Task events directory not writable
3. File descriptor limit reached
4. Concurrent access conflict

**Resolution Steps:**

```powershell
# Step 1: Check disk space
Get-Volume
# Step 2: Check inode usage
# PowerShell: Get-Volume (no direct inode equivalent)

# Step 3: Clean old events
python scripts/clean_runtime_artifacts.py --confirm

# Step 4: Check open file handles (PowerShell equivalent)
# PowerShell: 无直接等效命令 (Linux-only)
```

---

### E008: Artifact Validation Failed

| Field | Description |
|-------|-------------|
| **Symptom** | `ArtifactValidationError: Output artifact does not match specification` |
| **Error Code** | `E008` |
| **Severity** | Error |

**Root Causes:**
1. Generated artifact has wrong format
2. Required artifact files missing
3. Artifact size exceeds limits
4. Checksum mismatch for verified artifacts

**Resolution Steps:**

```powershell
# Step 1: List expected artifacts
Get-Content 'artifacts/manifest.json' | ConvertFrom-Json | Select-Object -Property '.expected_files'
# Step 2: List actual artifacts
Get-ChildItem -Path 'artifacts/'

# Step 3: Validate artifact format
python -c "
from agents.utils import validate_artifact
result = validate_artifact('artifacts/output.pptx', expected_type='pptx')
print(result)
"```

---

### E009: Coder Sandbox Timeout

| Field | Description |
|-------|-------------|
| **Symptom** | `TimeoutError: Coder sandbox execution exceeded 60s limit` |
| **Error Code** | `E009` |
| **Severity** | Error |

**Root Causes:**
1. Code execution takes too long
2. Infinite loop in generated code
3. Network request blocking execution
4. Resource-intensive computation

**Resolution Steps:**

```powershell
# Step 1: Review the code that timed out
Get-Content 'runtime/sandbox/code.py'
# Step 2: Increase timeout (if needed)
$env:KIMI_SANDBOX_TIMEOUT=120  # seconds

# Step 3: Run with resource limits
kimi --agent-file agents/coder-sub.yaml --prompt (Get-Content <file> -Raw)
```

---

### E010: Resume State Corrupted

| Field | Description |
|-------|-------------|
| **Symptom** | `ValueError: Resume state file corrupted or incompatible` |
| **Error Code** | `E010` |
| **Severity** | Error |

**Root Causes:**
1. Previous run terminated abnormally
2. State file partially written
3. Version mismatch in state format
4. Manual modification of state file

**Resolution Steps:**

```powershell
# Step 1: View state file (if readable)
Get-Content 'runtime/resume-state.json' | ConvertFrom-Json | ConvertTo-Json
# Step 2: Reset state and restart
Remove-Item 'runtime/resume-state.json'
kimi --agent-file agents/<agent>.yaml --prompt (Get-Content <file> -Raw) --fresh-start

# Step 3: Backup and clear all runtime state
Move-Item 'runtime/' "runtime.bak.$(Get-Date -UFormat %s)"
New-Item -Path 'runtime' -ItemType Directory -Force
```

---

## Debug Guide

### Debug Log (`runtime/debug.log`)

The debug log contains detailed execution traces:

```powershell
# View last 100 lines
Get-Content 'runtime/debug.log' -Tail 100
# Filter by component
Select-String -Path 'runtime/debug.log' -Pattern '"ERROR"'
Select-String -Path 'runtime/debug.log' -Pattern '"qa-gate"'
# Follow log in real-time
Get-Content 'runtime/debug.log```' -Wait
Log format:
```
[YYYY-MM-DD HH:MM:SS] [LEVEL] [COMPONENT] Message
```

### Task Events (`runtime/task-events/`)

Task events record every step of execution:

```powershell
# List all task events
Get-ChildItem -Path 'runtime/task-events/' | Sort-Object LastWriteTime -Descending

# View specific event
Get-Content 'runtime/task-events/event-001.json' | ConvertFrom-Json | ConvertTo-Json
# Count events by type
Get-Content 'runtime/task-events/*.json' | Select-String -Pattern ''"type"' | sort | uniq -c```'

Event types:
- `agent.start` - Agent execution started
- `agent.step` - Agent step completed
- `skill.invoke` - Skill called
- `qa.check` - Quality check performed
- `error.raised` - Error occurred
- `agent.end` - Agent execution completed

### Error Records (`runtime/errors.jsonl`)

Structured error log in JSON Lines format:

```powershell
# View all errors
Get-Content 'runtime/errors.jsonl' | ForEach-Object { $_ | ConvertFrom-Json | ConvertTo-Json }'
# Filter by error code
Get-Content 'runtime/errors.jsonl' | Select-String -Pattern ''"code":"E001"''

# Get error count by code
Get-Content 'runtime/errors.jsonl | python -c "'
import sys, json
from collections import Counter
codes = [json.loads(line)['code'] for line in sys.stdin]
for code, count in Counter(codes).most_common():
    print(f'{code}: {count}')
"```

### Full Diagnostic Report

Generate a comprehensive diagnostic report:

```powershell
python -c "
import json, os, glob
from datetime import datetime

report = {
    'generated_at': datetime.now().isoformat(),
    'version': open('VERSION').read().strip(),
    'environment': {
        'python': os.popen('python --version').read().strip(),
        'cwd': os.getcwd(),
        'user': os.getenv('USERNAME'),
    },
    'files': {
        'debug_log_lines': len(open('runtime/debug.log').readlines()) if os.path.exists('runtime/debug.log') else 0,
        'error_count': len(open('runtime/errors.jsonl').readlines()) if os.path.exists('runtime/errors.jsonl') else 0,
        'task_events': len(glob.glob('runtime/task-events/*.json')),
        'artifacts': len(glob.glob('artifacts/*')),
    }
}
print(json.dumps(report, indent=2))
"```

---

## Quick Fix Index

| Error | Quick Fix Command |
|-------|-------------------|
| E001 | `pip install --upgrade kimi-sdk` |
| E002 | `icacls 'runtime/' /grant Users:F` |
| E003 | `jsonschema.validate(data, schema)` |
| E004 | Clean markdown from JSON output |
| E005 | Check debug.log, retry with `--retry` |
| E006 | Review `artifacts/qa-gate-result.json` |
| E007 | Clean runtime: `scripts/clean_runtime_artifacts.py --confirm` |
| E008 | Check `artifacts/manifest.json` vs actual files |
| E009 | Increase `KIMI_SANDBOX_TIMEOUT` |
| E010 | Remove `runtime/resume-state.json`, restart fresh |

---

*Still stuck? Check [README.md](README.md) for support channels.*
