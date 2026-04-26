---
name: multimodal-review
version: 2.4.0
description: Analyze uploaded images, screenshots, and design mockups for visual quality and content
triggers:
  - user uploads image, screenshot, or design mockup and requests analysis
  - user asks to "review this image", "analyze this screenshot", "what do you see"
  - user requests visual inspection, design review, or layout analysis
input_required:
  - image file (PNG, JPG, JPEG, WEBP, GIF, BMP, TIFF) or video file (MP4, MOV, AVI)
output:
  - multimodal-review-report.md
  - visual-evidence-extraction.json (when charts/data present)
hard_fail_on:
  - hallucinating visual details
  - fabricating conclusions from unclear visuals
  - failing to flag visual uncertainty
schema: schemas/multimodal-review.schema.json
---

# multimodal-review — Skill Definition

## 1. Overview

This skill is activated when the user uploads an image, screenshot, or design
mockup and asks for analysis. The agent examines the visual content, identifies
UI elements, analyzes layout, extracts chart data, and compares designs to
implementations.

## 2. Capability Range

### 2.1 Identify UI Elements
- Recognize common UI components: buttons, inputs, dropdowns, modals, cards, tabs, navigation
- Identify text labels, headings, and body copy
- Detect icons and iconography (by shape, not by exact identity unless clear)
- Recognize form elements and their states (active, disabled, error)

### 2.2 Analyze Design Layout
- Assess overall layout structure (grid, flexbox, fixed positioning)
- Evaluate spacing and alignment between elements
- Identify visual hierarchy (heading sizes, color emphasis)
- Detect responsive behavior indicators (if multiple viewports shown)
- Note color scheme and contrast ratios (where distinguishable)

### 2.3 Extract Chart Data
- Identify chart type: bar, line, pie, scatter, area, histogram
- Read axis labels and units (where legible)
- Estimate data values from visual encoding (bar heights, line positions)
- Extract legend entries and color mappings
- Note: always mark extracted values with confidence level

### 2.4 Compare Design vs Implementation
- When given both design mockup and implementation screenshot:
  - Identify visual differences (color, spacing, font, alignment)
  - Flag missing elements or extra elements
  - Note responsive discrepancies
  - Report overall fidelity score (high/medium/low)

## 3. Confidence Annotation System

Every visual observation MUST be annotated with confidence:

| Level | Indicator | Usage |
|-------|-----------|-------|
| High | [confirmed] | Clearly visible, unambiguous |
| Medium | [likely] | Visible but some detail unclear |
| Low | [uncertain] | May be present, partially visible |
| None | [not visible] | Cannot determine |

## 4. Hard-Fail Rules

| ID | Rule | Consequence |
|----|------|-------------|
| HF-MM-01 | **No hallucinated details** — must not describe elements not actually visible | Immediate termination |
| HF-MM-02 | **No fabricated conclusions** — must not state certainty about unclear elements | Immediate termination |
| HF-MM-03 | **Uncertainty must be flagged** — every low-confidence observation marked with indicator | Immediate termination |

## 5. Output Format

### multimodal-review-report.md

```markdown
# Multimodal Review: {filename}

## Overview
- File type: {type}
- Dimensions: {width}x{height}
- Overall assessment: {1-2 sentence summary}

## UI Elements Detected
| Element | Location | Confidence | Notes |
|---------|----------|------------|-------|
| ...     | ...      | [confirmed]/[likely]/[uncertain] | ... |

## Layout Analysis
{description of layout structure, spacing, hierarchy}

## Chart/Data Extraction (if applicable)
- Chart type: {type}
- Axes: {labels and ranges}
- Extracted data points: {values with confidence}

## Issues Found
| Severity | Description | Confidence |
|----------|-------------|------------|
| critical/high/medium/low | ... | ... |

## Comparison Results (if design+implementation provided)
- Fidelity: {high/medium/low}
- Differences: {list}

## Confidence Summary
- High confidence observations: {count}
- Medium confidence observations: {count}
- Low/uncertain observations: {count}
```

## 6. Degradation Handling

| Scenario | Action |
|----------|--------|
| Image too low resolution | Request higher resolution; only analyze clear regions |
| Image partially corrupted | Analyze undamaged portions; note corruption |
| Text too small to read | Mark as [not visible]; do not guess text content |
| Chart data too dense | Provide approximate ranges; mark low confidence |
| Color information unclear | Describe relative darkness/lightness; avoid exact color names |
