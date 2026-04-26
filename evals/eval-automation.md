# Eval Automation Documentation
# ==============================

This document describes the automated evaluation execution flow for the
Kimi Production-Grade Agent Pack.

## Overview

The evaluation pipeline is fully automated and can be triggered via:
1. **GitHub Actions** - On every push and pull request
2. **Local execution** - Via command-line scripts
3. **Manual trigger** - Via GitHub Actions workflow dispatch

## Pipeline Architecture

```
+---------------+     +------------------+     +------------------+
|   Trigger     | --> |   eval_runner    | --> |  check_hard_fail |
| (push/PR/     |     |   .py            |     |   .py            |
|  manual)      |     |                  |     |                  |
+---------------+     +------------------+     +------------------+
                            |                           |
                            v                           v
                     +--------------+          +--------------+
                     | eval-result  |          | hard-fail    |
                     | .json        |          | report       |
                     +--------------+          +--------------+
                            |
                            v
                     +--------------+
                     |   Pass/Fail  |
                     |   Decision   |
                     +--------------+
```

## Execution Flow

### Step 1: Trigger
- Push to `main` or any branch
- Pull request opened/updated
- Manual workflow dispatch from GitHub UI

### Step 2: Environment Setup
- Checkout repository code
- Set up Python 3.11
- Install dependencies (if requirements.txt exists)

### Step 3: Run Eval Suite
```powershell
python scripts/eval_runner.py \
    --suite smoke \
    --output evals/results/${{ github.ref_name }} \
    --model kimi-latest```

The eval runner:
1. Reads prompts from `evals/benchmark-prompts.md`
2. Executes each prompt against the agent
3. Validates outputs against schemas
4. Generates:
   - `eval-result.json` - Structured evaluation results
   - `raw-output.md` - Raw model outputs
   - `errors.jsonl` - Any errors encountered
   - `run-metadata.json` - Run metadata and hashes
   - `debug.log` - Detailed debug log

### Step 4: Hard Fail Check
```powershell
python scripts/check_hard_fail.py \
    --input evals/results/${{ github.ref_name }} \
    --threshold 0.8```

The hard fail checker:
1. Loads the eval result
2. Runs 8 hard-fail rule checks
3. Compares score against threshold
4. Generates a hard-fail report

### Step 5: Pass/Fail Decision

| Condition | Result |
|-----------|--------|
| Score >= 80 AND no hard fails | PASS |
| Score >= 80 AND non-critical hard fails | PASS WITH NOTES |
| Score < 80 OR critical hard fail | FAIL |

### Step 6: Artifact Upload
On failure, the pipeline uploads:
- All result files as GitHub Actions artifacts
- Debug logs for troubleshooting
- Hard-fail report for review

## Local Execution

### Running Smoke Eval Locally
```powershell
# Full smoke eval
python scripts/eval_runner.py --suite smoke --output evals/results/local

# Dry run (no model calls)
python scripts/eval_runner.py --suite smoke --output evals/results/dry --dry-run

# With custom model
python scripts/eval_runner.py --suite smoke --output evals/results/local --model gpt-4```

### Running Hard Fail Check
```powershell
# Check results
python scripts/check_hard_fail.py --input evals/results/local --threshold 0.8

# Output to file
python scripts/check_hard_fail.py --input evals/results/local --output hard-fail-report.json```

### Schema Validation
```powershell
# Validate all schemas
python scripts/validate_schema.py --check-schemas

# Validate data against schema
python scripts/validate_schema.py --schema schemas/task-brief.schema.json --data my-task.json```

## CI/CD Integration

### GitHub Actions Workflow
The workflow is defined in `.github/workflows/eval-pipeline.yml`:

```yaml
name: Eval Pipeline
on: [push, pull_request]

jobs:
  smoke_eval:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - run: python scripts/eval_runner.py --suite smoke --output evals/results/${{ github.ref_name }}
      - run: python scripts/check_hard_fail.py --input evals/results/${{ github.ref_name }} --threshold 0.8
```

### Required Secrets
- `MODEL_API_KEY` - API key for the model (if required)
- `GITHUB_TOKEN` - Automatically provided by GitHub Actions

## Troubleshooting

### Common Issues

**Issue**: Eval runner fails with "Prompts file not found"
- **Solution**: Ensure `evals/benchmark-prompts.md` exists and is committed

**Issue**: Hard fail check reports false positives
- **Solution**: Review the specific rule implementation in `check_hard_fail.py`

**Issue**: Schema validation fails for valid JSON
- **Solution**: Ensure `jsonschema` is installed: `pip install jsonschema`

**Issue**: GitHub Actions timeout
- **Solution**: Increase timeout in workflow config or reduce eval suite size

### Debug Mode
Set environment variable for verbose logging:
```powershell
$env:EVAL_DEBUG=1
python scripts/eval_runner.py --suite smoke --output evals/results/debug```
