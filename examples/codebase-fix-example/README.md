# Codebase Fix Example

> **Agent**: `codebase-fix`  
> **Capability**: Automated codebase issue detection and fixing  
> **Level**: L1 MVP

---

## Objective

Demonstrate the codebase-fix agent's ability to scan a codebase, identify issues (lint errors, type errors, security vulnerabilities), and propose or apply fixes.

---

## Input

- **Directory**: `codebase/` — Source code directory to analyze
- **Config** (optional): `.codebase-fix-config.yaml` — Configuration for fix rules

### Sample Codebase Structure

```
codebase/
├── src/
│   ├── main.py          # May have lint/type issues
│   ├── utils.py         # May have import issues
│   └── models.py        # May have schema issues
├── tests/
│   └── test_main.py     # May have assertion issues
└── requirements.txt
```

### Sample Config (.codebase-fix-config.yaml)

```yaml
rules:
  - id: unused-import
    severity: warning
    auto_fix: true
  - id: type-error
    severity: error
    auto_fix: false
  - id: deprecated-api
    severity: warning
    auto_fix: true
  - id: security-vulnerability
    severity: critical
    auto_fix: false

exclude:
  - "*/venv/*"
  - "*/__pycache__/*"
  - "*/.git/*"
```

---

## Expected Output

- **Report**: `artifacts/fix-report.json` — Structured report with:
  - Issues found (file, line, rule, severity, message)
  - Fixes applied (file, original, replacement)
  - Fixes requiring manual review
  - Summary statistics

- **Patched Code**: `artifacts/patched-codebase/` — Copy of codebase with auto-fixes applied

### Output Quality Criteria

- [ ] All Python files in codebase are scanned
- [ ] Issues have correct file/line references
- [ ] Severity levels are accurate
- [ ] Auto-fixes do not break syntax
- [ ] Report contains actionable recommendations

---

## Running the Example

```powershell
# Navigate to project root
cd kimi-production-grade-agent-pack

# Activate virtual environment
.venv\Scripts\activate

# Run with coder sub-agent
kimi --agent-file agents/coder-sub.yaml --prompt "Review and fix issues in examples/codebase-fix-example/codebase/"

# Or with production coordinator
kimi --agent-file agents/production-coordinator.yaml --prompt "Review and fix issues in examples/codebase-fix-example/codebase/"
```

---

## Verification

```powershell
# Check report exists
Get-ChildItem -Path 'artifacts/fix-report.json'

# View report summary
python -c "
import json
with open('artifacts/fix-report.json') as f:
    report = json.load(f)
print(f\"Issues found: {report.get('total_issues', 0)}\")
print(f\"Auto-fixed: {report.get('auto_fixed', 0)}\")
print(f\"Need review: {report.get('needs_review', 0)}\")
print('\nTop issues:')
for issue in report.get('issues', [])[:5]:
    print(f\"  [{issue['severity']}] {issue['file']}:{issue['line']} - {issue['rule']}\")
"

# Check patched codebase
Get-ChildItem -Path 'artifacts/patched-codebase/'

# Verify patched files are syntactically valid
python -m py_compile artifacts/patched-codebase/src/main.py && echo "OK" || echo "SYNTAX ERROR"```

---

## Notes

- The agent uses a sandboxed environment for safety
- Auto-fixes are applied to the copy in `artifacts/patched-codebase/`, not the original
- Files with `critical` severity issues require manual review
- Large codebases may take several minutes; use `--timeout 600` if needed
- Supported languages: Python (L1), JavaScript/TypeScript (planned for L2)
