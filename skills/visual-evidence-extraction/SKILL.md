---
name: visual-evidence-extraction
version: 2.4.0
description: Extract structured data from charts, graphs, and data visualizations in images
triggers:
  - user uploads chart, graph, or data visualization and asks for data extraction
  - user requests "get the data from this chart", "extract values from this graph"
  - user asks to convert a visual chart into tabular data
input_required:
  - image containing chart/graph (PNG, JPG, JPEG)
output:
  - visual-evidence-extraction.json
  - chart-data.csv (extracted tabular data)
schema: schemas/visual-evidence.schema.json
---

# visual-evidence-extraction — Skill Definition

## 1. Overview

This skill extracts structured numerical data from static chart images.
It identifies the chart type, reads axes and labels, and estimates data
values from the visual encoding. Output is a structured JSON file plus
an optional CSV.

## 2. Supported Chart Types

- **Bar chart** (vertical, horizontal, grouped, stacked)
- **Line chart** (single series, multi-series, area fill)
- **Pie/Donut chart**
- **Scatter plot**
- **Histogram**
- **Box plot** (basic: median, Q1, Q3, whiskers)

## 3. Extraction Steps

### 3.1 Chart Type Identification
1. Examine overall visual structure
2. Identify primary encoding (bars → bar chart, lines → line chart, etc.)
3. Note: mark confidence as [confirmed] only when unambiguous

### 3.2 Axis & Scale Extraction
- Read X-axis label and tick values
- Read Y-axis label and tick values
- Identify scale type (linear, logarithmic, categorical)
- Note units (%, $, count, etc.)
- Flag: [uncertain] if text is illegible

### 3.3 Data Value Estimation
For each data point:
- Estimate value based on pixel position relative to axis scale
- Record confidence: high (clear), medium (readable but approximate), low (estimated)
- For bar charts: read height relative to Y-axis
- For line charts: read point position; note interpolation between points
- For pie charts: estimate angle/proportion

### 3.4 Legend & Series Mapping
- Extract legend entries
- Map colors/patterns to series names
- Apply mapping to all extracted data points

## 4. Confidence Levels for Extracted Data

| Level | Precision | Annotation |
|-------|-----------|------------|
| High | ±2% of axis range | [high] |
| Medium | ±5% of axis range | [medium] |
| Low | ±10% of axis range or estimated | [low] |

## 5. Output Format

### visual-evidence-extraction.json

```json
{
  "media_file": "chart.png",
  "chart_type": "bar",
  "chart_type_confidence": "confirmed",
  "axes": {
    "x": {
      "label": "Month",
      "type": "categorical",
      "categories": ["Jan", "Feb", "Mar"]
    },
    "y": {
      "label": "Revenue ($)",
      "type": "linear",
      "min": 0,
      "max": 100000,
      "unit": "$"
    }
  },
  "series": [
    {
      "name": "Product A",
      "color": "#3b82f6",
      "data_points": [
        { "x": "Jan", "y": 45000, "confidence": "high" },
        { "x": "Feb", "y": 52000, "confidence": "high" }
      ]
    }
  ],
  "extracted_data": [
    {
      "type": "numeric",
      "value": 45000,
      "confidence": "high",
      "region": "bar-jan-product-a",
      "context": "January revenue for Product A"
    }
  ]
}
```

### chart-data.csv
```csv
Series,Category,Value,Confidence
Product A,Jan,45000,high
Product A,Feb,52000,high
```

## 6. Hard-Fail Rules

| ID | Rule | Consequence |
|----|------|-------------|
| HF-VE-01 | Must not fabricate data values — every value estimated from visual position | Termination |
| HF-VE-02 | Must annotate confidence for every extracted data point | Termination |
| HF-VE-03 | Must state when chart type cannot be determined | Termination |
| HF-VE-04 | Illegible axis labels must be marked [not readable], not guessed | Termination |
