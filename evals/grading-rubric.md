# Grading Rubric for Kimi Production-Grade Agent Pack v1.0
# =========================================================

## Hard Fail Conditions

A hard failure (HF) occurs when any of the following conditions are met.
Hard failures immediately fail the evaluation regardless of the overall score.

| ID | Condition | Description |
|----|-----------|-------------|
| HF-01 | Critical facts without source | Any critical claim lacks evidence source attribution |
| HF-02 | Core deliverables missing | Required deliverables from task-brief are absent |
| HF-03 | Code without tests | Code changes are made without tests or validation |
| HF-04 | Tables not traceable | Data tables lack source references for traceability |
| HF-05 | PPT missing page messages | PPT outline lacks page-level key messages |
| HF-06 | User constraints ignored | User-specified constraints are explicitly violated |
| HF-07 | Tool failure hidden | A tool failure is disguised as a successful execution |
| HF-08 | Missing context snapshot | Sub-agent output lacks a complete context_snapshot |

## Scoring Dimensions (Total: 100 points)

| # | Dimension | Max Score | Weight | Description |
|---|-----------|-----------|--------|-------------|
| 1 | Completeness | 10 | 1.0x | All required outputs and deliverables are present |
| 2 | Accuracy | 10 | 1.0x | Factual correctness and precision of claims |
| 3 | Source Quality | 10 | 1.0x | Quality and reliability of evidence sources |
| 4 | Format Compliance | 10 | 1.0x | Output conforms to specified schema/format |
| 5 | Reasoning Clarity | 10 | 1.0x | Clear, logical chain of reasoning |
| 6 | Constraint Adherence | 10 | 1.0x | All user constraints are respected |
| 7 | Deliverable Quality | 10 | 1.0x | Professional quality of final deliverables |
| 8 | Test Coverage | 10 | 1.0x | Adequate testing of code and logic |
| 9 | Documentation | 10 | 1.0x | Clear documentation of process and assumptions |
| 10 | Edge Case Handling | 10 | 1.0x | Graceful handling of edge cases and errors |

### Scoring Guide

- **10/10**: Exceptional - exceeds expectations, no issues
- **8-9/10**: Good - minor issues, well above acceptable
- **6-7/10**: Acceptable - meets requirements with some issues
- **4-5/10**: Below standard - significant issues present
- **2-3/10**: Poor - major deficiencies
- **0-1/10**: Critical failure - dimension is not addressed

## Score Ranges

| Range | Grade | Meaning |
|-------|-------|---------|
| 90-100 | A | Excellent - production ready |
| 80-89 | B | Good - minor improvements needed |
| 70-79 | C | Acceptable - some issues to address |
| 60-69 | D | Below standard - significant rework needed |
| 0-59 | F | Unacceptable - major rework required |

## Pass/Fail Criteria

- **Pass**: Score >= 70 AND no hard failures
- **Pass with Notes**: Score >= 70 with hard failures that have remediation plans
- **Fail**: Score < 70 OR any critical hard failure (HF-01, HF-02, HF-06, HF-07)
