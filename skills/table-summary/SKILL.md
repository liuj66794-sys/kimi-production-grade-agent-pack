---
name: table-summary
version: 2.3.0
description: Generate human-readable summaries and descriptions of tabular data
triggers:
  - user requests "summarize this table", "describe this data", "what is in this spreadsheet"
  - user asks for a "human-readable summary" or "data overview in plain language"
  - orchestrator requests a narrative summary after analysis completes
input_required:
  - path to CSV/Excel file, or pre-computed analysis results
output:
  - table-summary.md
schema: schemas/table-summary.schema.json
---

# table-summary — Skill Definition

## 1. Overview

This skill generates a natural-language, human-readable summary of tabular data.
It translates raw statistics into plain-language descriptions that non-technical
stakeholders can understand.

## 2. Capability Range

### 2.1 Dataset Overview
- Write a 2-3 sentence summary of what the dataset contains
- Mention approximate row/column count in plain terms (e.g., "about 50,000 rows")
- Identify the likely purpose or domain of the data (sales, user metrics, inventory, etc.)

### 2.2 Column Narratives
- For each column, write 1 sentence describing what it likely represents
- Include data type, typical value range, and completeness
- Example: "The 'revenue' column contains numeric values ranging from $0 to $1.2M,
  with an average of $45K and about 3% missing values."

### 2.3 Data Quality Narrative
- Summarize overall data health in 2-3 sentences
- Highlight the most significant quality issues (if any)
- Use qualitative terms: "excellent", "good", "fair", "poor" based on null ratios

### 2.4 Key Insights (auto-generated)
- Identify top 3 most interesting findings from the data
- Examples: unexpected distributions, highly correlated columns, columns with extreme missing rates

## 3. Output Format — table-summary.md

```markdown
# Table Summary: {filename}

## Overview
{2-3 sentence natural language summary}

## Columns ({count} total)
| Column | Description | Type | Completeness | Notes |
|--------|-------------|------|--------------|-------|
| {name} | {narrative} | {type} | {X%} | {any notable observations} |
...

## Data Quality
{overall quality narrative}

## Key Insights
1. {insight 1}
2. {insight 2}
3. {insight 3}

## Notable Observations
{any additional observations worth highlighting}
```

## 4. Quality Heuristics

| Null Ratio | Completeness Rating |
|------------|-------------------|
| 0% | Excellent |
| 0-5% | Good |
| 5-20% | Fair |
| 20-50% | Poor |
| >50% | Critical |

## 5. Hard-Fail Rules

| ID | Rule | Consequence |
|----|------|-------------|
| HF-TS-01 | Summary must be based on actual computed statistics, not fabricated | Termination |
| HF-TS-02 | Must not omit mention of columns with missing values | Termination |
| HF-TS-03 | Must include at minimum: Overview, Columns table, Data Quality sections | Termination |
