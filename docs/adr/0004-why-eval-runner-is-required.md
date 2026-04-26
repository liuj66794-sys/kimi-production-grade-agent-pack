# ADR-0004: Why Eval Runner Is Required

## Status
Accepted

## Context

We needed to decide whether the evaluation pipeline should be:

1. **External Tool** - Eval is performed by a separate, external system
2. **Built-in Eval Runner** - The agent pack includes its own evaluation runner
3. **Manual Eval** - Human evaluation without automation

## Decision

We chose to include a **built-in Eval Runner** (`scripts/eval_runner.py`) for the following reasons:

### 1. Continuous Integration
An eval runner enables automated testing on every commit. Without it, evals would need to be run manually, leading to regressions going undetected.

### 2. Reproducibility
The eval runner captures all parameters (prompt hash, skill hash, config hash) needed to reproduce results. This ensures that scores are comparable across runs.

### 3. Consistency
A centralized runner applies the same evaluation criteria every time. Manual evals are subject to human inconsistency and bias.

### 4. Fast Feedback Loop
Developers can run evals locally before pushing changes. The `--dry-run` mode enables quick validation without API calls.

### 5. Regression Detection
The eval runner integrates with GitHub Actions to automatically detect regressions. The regression checklist (`evals/regression-checklist.md`) provides a structured framework.

### 6. Artifact Generation
The runner generates structured outputs (`eval-result.json`, `raw-output.md`, `errors.jsonl`) that can be analyzed programmatically.

## Consequences

### Positive
- Automated quality gate on every PR
- Reproducible and comparable evaluation results
- Fast local iteration with `--dry-run`
- Structured output for analysis and dashboards
- Regression prevention through CI integration

### Negative
- Additional code to maintain
- Eval prompts may become stale if not updated
- Runner itself needs testing (meta-testing problem)
- CI minutes cost for running evals

### Mitigations
- Eval prompts are versioned alongside the agent pack
- The runner is kept simple with minimal dependencies
- Smoke tests are fast (< 5 minutes total)
- `--dry-run` mode allows validation without API costs
