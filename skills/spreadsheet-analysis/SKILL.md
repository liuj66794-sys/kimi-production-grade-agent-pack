---
name: spreadsheet-analysis
version: 2.3.0
description: Analyze CSV/Excel files to produce structured statistical reports
triggers:
  - user uploads CSV/Excel file and requests analysis
  - user asks to "analyze this data", "explore this spreadsheet", "get stats"
  - user requests "summary statistics", "data profile", "column analysis"
input_required:
  - path to CSV or Excel file (.csv, .xlsx, .xls)
output:
  - analysis-report.md
  - data-quality-report.md
  - processed-{timestamp}.csv (when transformations are applied)
hard_fail_on:
  - fabricated data
  - undisclosed missing values
  - unsaved processing results
  - missing data quality report
schema: schemas/spreadsheet-analysis.schema.json
---

# spreadsheet-analysis — Skill Definition

## 1. Overview

This skill is activated when the user uploads a CSV or Excel file and asks for
analysis. The agent reads the file, computes summary statistics, detects missing
values and outliers, and emits a structured `analysis-report.md` plus a
`data-quality-report.md`.

## 2. Capability Range

### 2.1 Read CSV/Excel
- Support `.csv`, `.xlsx`, `.xls` formats
- Auto-detect encoding (UTF-8, GBK, Latin-1 fallback)
- Read with `pandas.read_csv()` or `pandas.read_excel()`
- Parse headers from the first non-empty row

### 2.2 Generate Summary
For the entire dataset, compute:
- **Row count** (total rows, data rows excluding header)
- **Column count**
- **Column names and inferred types** (numeric, string, datetime, boolean, mixed)
- **Per-column null count and null ratio** (`null_count / total_rows`)
- **Per-column unique count and unique ratio**
- **Basic statistics for numeric columns**: min, max, mean, median, std
- **Basic statistics for string columns**: max length, min length, sample values
- **Basic statistics for datetime columns**: earliest, latest, date range

### 2.3 Check Missing Values
- Report null count and null ratio per column
- Flag columns with null ratio > 50% as "highly incomplete"
- Flag columns with null ratio > 0% as "has missing values"
- Never silently ignore missing values

### 2.4 Check Outliers
Provide both methods (configurable):
- **IQR method**: Q1, Q3, IQR; outlier bounds = [Q1 - 1.5×IQR, Q3 + 1.5×IQR]
- **Z-score method**: |z| > threshold (default 3.0) flagged as outlier
- Report: column name, outlier count, outlier ratio, example outlier values (bounded)

### 2.5 Output analysis-report.md
Structured markdown report with sections:
1. File Info (filename, format, encoding, size)
2. Dataset Summary (rows, columns, memory estimate)
3. Column Profiles (one section per column with stats)
4. Missing Value Analysis (table of null counts/ratios)
5. Outlier Analysis (table of outlier findings)
6. Correlation Matrix (for numeric columns, Pearson correlation)
7. Recommendations (data cleaning suggestions)

## 3. Hard-Fail Rules

| ID | Rule | Consequence |
|----|------|-------------|
| HF-SS-01 | **No fabricated data** — every statistic must be computed from actual file contents | Immediate termination |
| HF-SS-02 | **Missing-value disclosure mandatory** — every column with nulls must be reported | Immediate termination |
| HF-SS-03 | **Processed results must be saved** — any transformation/cleaning must be persisted to disk | Immediate termination |
| HF-SS-04 | **Data-quality report required** — `data-quality-report.md` must accompany every analysis | Immediate termination |

## 4. Workflow

1. **Read** the uploaded file with pandas
2. **Profile** each column (type, nulls, uniques, stats)
3. **Detect** missing values and compute null ratios
4. **Detect** outliers via IQR and/or Z-score
5. **Compute** correlation matrix (numeric columns only)
6. **Write** `analysis-report.md` (structured markdown)
7. **Write** `data-quality-report.md` (completeness/consistency/accuracy)
8. **If transformations applied**, write `processed-{timestamp}.csv`
9. **Validate** against `schemas/spreadsheet-analysis.schema.json`
10. **Return** file paths to orchestrator

## 5. Degradation (Large Files)

If file > 100MB or > 1M rows:
- Use streaming: read first 10,000 rows + random sample of 10,000 + last 1,000
- Report sampling strategy in the analysis output
- Include a prominent note: "⚠️ Sampled analysis due to file size"

## 6. Error Handling

| Error | Response |
|-------|----------|
| File not found | Report error, request correct path |
| Unsupported format (.pdf, .doc) | Report error, list supported formats |
| Encoding detection failure | Try common encodings in order (UTF-8 → GBK → Latin-1) |
| Empty file | Report "empty dataset" with zero-row summary |
| All columns null | Report degenerate dataset, no further analysis |
| Out of memory | Switch to chunked reading, report sampling strategy |
