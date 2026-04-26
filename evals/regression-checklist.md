# Regression Checklist for Kimi Production-Grade Agent Pack v1.0
# ==============================================================

This checklist defines L1 core regression tests that must pass before
each release. These tests verify that fundamental capabilities have
not been broken by changes.

## L1 Core Regression Tests

### Schema Compliance
- [ ] task-brief.schema.json validates correctly
- [ ] subagent-result.schema.json validates correctly
- [ ] evidence-map.schema.json validates correctly
- [ ] quality-review.schema.json validates correctly
- [ ] eval-result.schema.json validates correctly

### Task Brief Generation
- [ ] Agent produces valid task-brief from fuzzy requirements
- [ ] Task brief includes all required fields
- [ ] Task brief correctly identifies need_web, need_code flags
- [ ] Task brief includes minimal_plan with >= 3 steps

### Evidence Mapping
- [ ] Agent produces valid evidence-map from research
- [ ] Evidence map contains claims with evidence_refs
- [ ] Sources have reliability ratings
- [ ] Conflicts are detected and documented

### Sub-Agent Output
- [ ] Sub-agent produces valid subagent-result
- [ ] context_snapshot is present and non-empty
- [ ] context_snapshot includes input_files, search_queries, tools_used
- [ ] Evidence items include claim, source, confidence, caveat

### Quality Review
- [ ] Agent produces valid quality-review output
- [ ] All 10 dimensions are scored
- [ ] Hard fails are correctly identified
- [ ] Remediation notes are provided for failures

### Code Execution
- [ ] Agent can execute Python code
- [ ] Code output is captured correctly
- [ ] Errors in code are reported, not hidden

### File Operations
- [ ] Agent can read files from workspace
- [ ] Agent can write files to workspace
- [ ] File paths are correctly resolved

### Web Operations (if applicable)
- [ ] Agent can perform web searches
- [ ] Agent can browse web pages
- [ ] Web results are correctly attributed

### Hard Fail Prevention
- [ ] HF-01: Critical facts always have sources
- [ ] HF-02: Core deliverables are never missing
- [ ] HF-03: Code changes always include validation
- [ ] HF-04: Tables always have source traceability
- [ ] HF-05: PPT outlines always have page-level messages
- [ ] HF-06: User constraints are never ignored
- [ ] HF-07: Tool failures are never hidden
- [ ] HF-08: Sub-agent outputs always have context snapshots

### Eval Pipeline
- [ ] eval_runner.py executes without errors
- [ ] check_hard_fail.py correctly identifies violations
- [ ] validate_schema.py validates schemas correctly
- [ ] GitHub Actions workflow runs successfully

## Regression Test Execution

### Pre-Release Checklist
- [ ] All L1 regression tests pass
- [ ] No hard failures in smoke eval
- [ ] Score >= 80 on smoke eval
- [ ] All schema files validate
- [ ] Scripts execute without errors
- [ ] GitHub Actions workflow is green

### Sign-Off
| Role | Name | Date | Status |
|------|------|------|--------|
| Test Lead | | | |
| Tech Lead | | | |
| Release Manager | | | |
