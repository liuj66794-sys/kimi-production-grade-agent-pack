# Expected Artifacts by Test Case
# ================================

This document maps each evaluation test to its expected output artifacts.

## Smoke Tests (SM-*)

### SM-01: Fuzzy Requirement to Task Brief
**Expected Artifacts**:
- `task-brief.json` - A valid task-brief.schema.json document
  - Must contain: goal, deliverables, input_materials, constraints
  - Must contain: required_capabilities, need_web, need_code, need_file_write
  - Must contain: risk_assumptions, minimal_plan

### SM-02: Single-Topic Deep Research
**Expected Artifacts**:
- `evidence-map.json` - A valid evidence-map.schema.json document
  - Must contain: >= 5 claims with evidence_refs
  - Must contain: >= 3 sources with reliability ratings
  - Must contain: conflicts array (may be empty)

### SM-03: Multi-Source Evidence Synthesis
**Expected Artifacts**:
- `evidence-map.json` - A valid evidence-map.schema.json document
  - Must contain: conflicts entries showing detected conflicts
  - Must contain: resolution notes for each conflict
  - Must contain: all 3 input sources

### SM-04: Code Fix with Validation
**Expected Artifacts**:
- `fixed_code.py` - The corrected Python function
- `test_code.py` - Unit tests for the function
- `test_results.txt` - Output showing all tests pass
- Must demonstrate: bug fix, test coverage, validation

### SM-05: PPT Outline Generation
**Expected Artifacts**:
- `ppt-outline.json` - Structured PPT outline
  - Must contain: 12-15 slide entries
  - Each slide must have: title, key_message, content_points
  - Key slides must have: speaker_notes
  - Must follow: problem -> solution -> implementation -> results structure

### SM-06: Table Model Generation
**Expected Artifacts**:
- `comparison-table.json` or `comparison-table.md` - The comparison table
- `evidence-map.json` - Source traceability for table data
  - Must link table cells to specific sources
  - Must include reliability ratings for sources

### SM-07: Quality Review Execution
**Expected Artifacts**:
- `quality-review.json` - A valid quality-review.schema.json document
  - Must contain: all 10 dimension scores and notes
  - Must contain: hard_fails array (with entries if applicable)
  - Must contain: overall_notes with summary

### SM-08: Sub-Agent Context Snapshot Check
**Expected Artifacts**:
- `subagent-result.json` - A valid subagent-result.schema.json document
  - Must contain: complete context_snapshot
    - input_files: ["agent-bench-2024.pdf", "mlcommons.pdf", "blog-post.md"]
    - search_queries: ["2024 AI agent benchmarks"]
    - tools_used: ["web_search", "file_read"]
  - Must contain: conclusions, evidence, artifacts, next_step

## Unit Smoke Tests (US-*)

### US-01: Schema Validation Skill
- `validation-report.json` - Results of schema validation

### US-02: Web Search Skill
- `search-results.json` - Structured search results

### US-03: Code Execution Skill
- `execution-output.txt` - Code execution output

### US-04: File I/O Skill
- `file-operations-log.json` - Log of file operations

### US-05: Evidence Extraction Skill
- `extracted-evidence.json` - Extracted claims and evidence

### US-06: Quality Review Skill
- `quality-review.json` - Quality review output

### US-07: Conflict Detection Skill
- `conflict-report.json` - Detected conflicts and resolutions

### US-08: Artifact Packaging Skill
- `artifact-manifest.json` - Manifest of packaged artifacts

## Integration Smoke Tests (IS-*)

### IS-01: Research-to-Report Pipeline
- `evidence-map.json` - Research evidence
- `report.md` - Final report
- `quality-review.json` - Quality review of report

### IS-02: Code Fix and Validate Pipeline
- `fixed_code.py` - Fixed code
- `test_code.py` - Tests
- `test_results.txt` - Test execution results
- `quality-review.json` - Quality review

### IS-03: Multi-Agent Delegation Workflow
- `coordinator-output.json` - Final coordinator output
- `subagent-results/` - Directory of sub-agent results
- `quality-review.json` - Quality review of combined output

### IS-04: End-to-End Content Production
- All intermediate artifacts
- `artifact-manifest.json` - Final manifest
- `release.zip` - Packaged deliverable
