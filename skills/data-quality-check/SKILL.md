---
name: data-quality-check
version: 2.3.0
description: Evaluate data quality across completeness, consistency, and accuracy dimensions
triggers:
  - user requests "check data quality", "validate this data", "is this data clean"
  - user asks about data integrity, consistency, or accuracy
  - orchestrator requests quality validation after analysis
input_required:
  - path to CSV/Excel file, or analysis results
output:
  - data-quality-report.md
schema: schemas/data-quality-result.schema.json
---

# data-quality-check — Skill Definition

## 1. Overview

This skill evaluates tabular data across three quality dimensions:
**Completeness** (missing data), **Consistency** (format/semantic consistency),
and **Accuracy** (value plausibility). Produces a scored quality report.

## 2. Quality Dimensions

### 2.1 Completeness Checks
- **Null ratio per column**: count and percentage of missing values
- **Empty string detection**: distinguish null from empty string ""
- **Row completeness**: percentage of rows that are fully populated
- **Column-level flag**: columns with >50% nulls marked "incomplete"
- **Overall completeness score**: weighted average of column completeness

### 2.2 Consistency Checks
- **Type consistency**: values in a column should conform to declared/inferred type
- **Format consistency**: string values should follow consistent patterns
  - Date formats (e.g., mixed "2024-01-01" and "01/01/2024")
  - Currency formats (e.g., mixed "$100" and "100 USD")
- **Unit consistency**: numeric columns should use consistent units
- **Categorical consistency**: check for typos/variants in categorical values
  - Example: "USA", "U.S.A.", "United States", "US" → flag as inconsistent
- **Cross-column consistency**: foreign-key-like relationships between columns

### 2.3 Accuracy Checks
- **Range validation**: numeric values within reasonable bounds
- **Date plausibility**: dates not in the future (unless expected), not too far in the past
- **Out-of-range detection**: values exceeding domain-specific thresholds
- **Duplicate detection**: exact duplicate rows, near-duplicate rows
- **Referential integrity**: cross-column references that should be consistent

## 3. Scoring System

Each dimension scored 0-100:
- **90-100**: Excellent
- **70-89**: Good
- **50-69**: Fair
- **30-49**: Poor
- **0-29**: Critical

**Overall score**: weighted average (Completeness 0.4, Consistency 0.3, Accuracy 0.3)

## 4. Output Format — data-quality-report.md

```markdown
# Data Quality Report: {filename}

## Overall Score: {score}/100 ({rating})

## Dimension: Completeness — {score}/100
| Column | Null Count | Null Ratio | Status |
|--------|-----------|------------|--------|
| ...    | ...       | ...        | ...    |

### Issues
- {issue description}

## Dimension: Consistency — {score}/100
| Check | Result | Details |
|-------|--------|---------|
| ...   | ...    | ...     |

### Issues
- {issue description}

## Dimension: Accuracy — {score}/100
| Check | Result | Details |
|-------|--------|---------|
| ...   | ...    | ...     |

### Issues
- {issue description}

## Recommendations
1. {actionable recommendation}
2. {actionable recommendation}
```

## 5. Hard-Fail Rules

| ID | Rule | Consequence |
|----|------|-------------|
| HF-DQ-01 | Must not fabricate quality scores — all scores derived from actual data | Termination |
| HF-DQ-02 | Must report every column with nulls, no omissions | Termination |
| HF-DQ-03 | Must flag type/format inconsistencies when detected | Termination |
| HF-DQ-04 | Overall score must be computable; if not, report "unable to score" | Termination |
