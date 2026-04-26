# Integration Smoke Test Card: integration-smoke-001-deep-research-minimal

## Metadata

| Field | Value |
|-------|-------|
| **Test ID** | `integration-smoke-001-deep-research-minimal` |
| **Version** | 1.2 |
| **Test Suite** | integration-smoke |
| **Priority** | P0 (Critical) |
| **Created** | 2025-01-01 |
| **Author** | kimi-production-grade-agent-pack |

---

## Objective

Verify that the L1 complete research pipeline can execute end-to-end without errors, producing all expected artifacts at each stage, passing schema validation, and achieving a successful QA review.

---

## Test Input

```
研究AI编程助手2025年市场格局
```

English translation: "Research the 2025 market landscape for AI programming assistants."

---

## Pipeline Under Test

```
task-intake → researcher → analyst → evidence-synthesis → writer → qa-reviewer
```

**Note:** `swarm-orchestrator` and `eval-runner` are part of the full L1 main link but are excluded from this minimal test scope.

---

## Step-by-Step Expectations

### 1. task-intake
- **Agent:** `task-intake-agent`
- **Input:** Research topic string
- **Expected Output:** `task-brief.json`
- **Schema Requirements:**
  - Must contain `task_id` (string)
  - Must contain `title` (string)
  - Must contain `description` (string)
  - Must contain `requirements` (array of strings)
  - Must contain `created_at` (ISO-8601 timestamp)

### 2. researcher
- **Agent:** `researcher-agent`
- **Input:** `task-brief.json`
- **Expected Output:** `research-notes.md`
- **Schema Requirements:**
  - Must be valid Markdown
  - Minimum 5 lines of content
  - Must contain at least one `## ` section header

### 3. analyst
- **Agent:** `analyst-agent`
- **Input:** `research-notes.md`
- **Expected Output:** `analysis-report.md`
- **Schema Requirements:**
  - Must be valid Markdown
  - Minimum 5 lines of content
  - Must contain at least one `## ` section header

### 4. evidence-synthesis
- **Agent:** `evidence-synthesis-agent`
- **Input:** `analysis-report.md` + `research-notes.md`
- **Expected Output:** `claim-evidence-map.json`
- **Schema Requirements:**
  - Must contain `claims` (array of claim objects)
  - Must contain `evidence_map` (object mapping claim IDs to evidence IDs)
  - Each claim should have `id`, `text`, and `confidence` fields

### 5. writer
- **Agent:** `writer-agent`
- **Input:** `claim-evidence-map.json` + previous artifacts
- **Expected Output:** `final-report.md`
- **Schema Requirements:**
  - Must be valid Markdown
  - Minimum 10 lines of content
  - Must contain `# ` title header
  - Must contain at least one `## ` section header

### 6. qa-reviewer
- **Agent:** `qa-reviewer-agent`
- **Input:** `final-report.md` + all previous artifacts
- **Expected Output:** `qa-review.json`
- **Schema Requirements:**
  - Must contain `review_status` (string: one of `pass`, `pass_with_notes`, `fail`, `hard_fail`)
  - Must contain `findings` (array of strings)
  - Must contain `scored_categories` (object with score values 0.0-1.0)

---

## Expected Artifacts

| # | Artifact | Producing Step | Format | Min Size |
|---|----------|---------------|--------|----------|
| 1 | `task-brief.json` | task-intake | JSON | > 0 B |
| 2 | `research-notes.md` | researcher | Markdown | > 0 B |
| 3 | `analysis-report.md` | analyst | Markdown | > 0 B |
| 4 | `claim-evidence-map.json` | evidence-synthesis | JSON | > 0 B |
| 5 | `final-report.md` | writer | Markdown | > 0 B |
| 6 | `qa-review.json` | qa-reviewer | JSON | > 0 B |

---

## Pass Criteria

1. **All Artifacts Exist** — All 6 expected artifacts are created and non-empty.
2. **Schema Compliance** — Each artifact validates against its defined schema.
3. **QA Review Pass** — `qa-review.json` has `review_status` of `pass` or `pass_with_notes`.
4. **Complete Event Log** — `task-events` JSONL records all subtask lifecycle events (`subtask_created`, `subtask_started`, `subtask_done`) for each step.
5. **No Hard Failures** — No `hard_fail` recorded in task events or QA review.

---

## Fail Criteria

| Condition | Severity | Action |
|-----------|----------|--------|
| Missing artifact | BLOCKER | Test fails |
| Empty artifact (0 bytes) | BLOCKER | Test fails |
| Schema validation error | BLOCKER | Test fails |
| `review_status` = `fail` | BLOCKER | Test fails |
| `review_status` = `hard_fail` | BLOCKER | Test fails, pipeline must halt |
| Incomplete task-events | WARNING | Flag for review |
| `pass_with_notes` with minor findings | OK | Test passes with notes |

---

## QA Gate Rules

- If QA review result is `hard_fail`: **Pipeline must not produce `final-report.md` for delivery.**
- If QA review result is `fail`: Writer must revise and resubmit.
- If QA review result is `pass_with_notes`: Writer should address notes but delivery is not blocked.
- QA review results must be recorded in `task-events` as `quality_review_done` event.

---

## Task Events Requirements

The following event types must appear in `task-events-{task_id}.jsonl`:

| Event Type | Required | Description |
|------------|----------|-------------|
| `task_created` | Yes | Initial task creation |
| `subtask_created` | Per step | Each step's subtask creation |
| `subtask_started` | Per step | Each step's execution start |
| `subtask_done` | Per step | Each step's completion |
| `artifact_created` | Per artifact | Each artifact generation |
| `quality_review_started` | Yes | QA review initiation |
| `quality_review_done` | Yes | QA review completion with result |
| `task_completed` | Yes (on success) | Final task completion |

Each event must contain:
- `event_id` (UUID v4)
- `task_id` (string)
- `event_type` (enum)
- `timestamp` (ISO-8601)
- `agent` (string)
- `status` (string)
- `payload` (object)
- `error` (string or null)

---

## Run Commands

### Execute Full Pipeline (dry-run preview)
```powershell
python scripts/integration_smoke_runner.py \
  --task-id root.integration_smoke_001 \
  --dry-run```

### Execute Step by Step
```powershell
# Step 1
python scripts/integration_smoke_runner.py --step task-intake

# Step 2
python scripts/integration_smoke_runner.py --step researcher

# Step 3
python scripts/integration_smoke_runner.py --step analyst

# Step 4
python scripts/integration_smoke_runner.py --step evidence-synthesis

# Step 5
python scripts/integration_smoke_runner.py --step writer

# Step 6
python scripts/integration_smoke_runner.py --step qa-reviewer```

### Validate Step Prerequisites
```powershell
python scripts/integration_smoke_runner.py --validate-step```

### Validate Artifacts
```powershell
python scripts/validate_artifacts.py \
  --artifacts-dir artifacts/integration-smoke-001/```

### Replay Task Events
```powershell
python scripts/replay_task_events.py \
  --task-id root.integration_smoke_001 \
  --format summary```

---

## Recovery Procedures

### Resume from a Specific Step
```powershell
python scripts/integration_smoke_runner.py --resume-from-step analyst```

### Re-validate from Existing Manifest
```powershell
python scripts/validate_artifacts.py --manifest artifact-manifest.json```

---

## Output Locations

| Output | Path Pattern |
|--------|-------------|
| Task Events | `runtime/task-events-{task_id}.jsonl` |
| Run State | `runtime/run-state.json` |
| Artifacts | `artifacts/integration-smoke-001/` |
| Eval Results | `evals/results/integration-smoke/{timestamp}/eval-result.json` |
| Replay Report | `runtime/task-replay-{task_id}.md` |
| Artifact Manifest | `artifact-manifest.json` |
