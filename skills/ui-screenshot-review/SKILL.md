---
name: ui-screenshot-review
version: 2.4.0
description: Review UI implementation quality from screenshots against best practices
triggers:
  - user uploads UI screenshot for quality review
  - user asks "how is this UI implemented", "review this interface"
  - user requests UI audit, accessibility check, or implementation review
input_required:
  - UI screenshot image (PNG, JPG, JPEG)
  - optional: design mockup for comparison
output:
  - ui-review-report.md
schema: schemas/multimodal-review.schema.json
---

# ui-screenshot-review — Skill Definition

## 1. Overview

This skill evaluates the quality of a UI implementation from a screenshot.
It checks alignment with design best practices, accessibility guidelines,
layout consistency, and overall visual polish.

## 2. Review Categories

### 2.1 Layout & Alignment
- Check element alignment (horizontal/vertical)
- Verify consistent spacing and padding
- Identify layout shifts or misaligned elements
- Assess responsive behavior (if multiple breakpoints shown)

### 2.2 Typography
- Readability of text at shown size
- Consistent font usage (heading vs body)
- Text truncation or overflow issues
- Line height and paragraph spacing

### 2.3 Color & Contrast
- Sufficient contrast between text and background
- Consistent color palette usage
- Visual feedback for interactive states (hover, active, disabled)
- Color-blind friendly indicators (not relying solely on color)

### 2.4 Accessibility (Visual)
- Focus indicator visibility
- Touch target size adequacy
- Text alternatives for icon-only buttons (where visible)
- Color contrast ratio estimation (WCAG AA compliance)

### 2.5 Component Consistency
- Button style consistency across the UI
- Form input styling uniformity
- Icon set consistency
- Border radius / shadow consistency

### 2.6 Comparison with Design (if mockup provided)
- Pixel-level difference identification
- Color accuracy
- Spacing accuracy
- Missing or extra elements

## 3. Severity Classification

| Severity | Description |
|----------|-------------|
| Critical | Blocks usability, broken functionality, major visual defect |
| High | Significant visual issue, accessibility violation, poor UX |
| Medium | Noticeable inconsistency, minor misalignment |
| Low | Nitpick, polish item, barely noticeable |

## 4. Output Format — ui-review-report.md

```markdown
# UI Screenshot Review: {filename}

## Summary
- Overall score: {X}/100
- Status: {pass/fail/needs improvement}
- Critical issues: {count}
- High issues: {count}
- Medium issues: {count}
- Low issues: {count}

## Layout & Alignment
| Check | Result | Notes |
|-------|--------|-------|
| Element alignment | pass/fail | ... |
| Spacing consistency | pass/fail | ... |

## Typography
| Check | Result | Notes |
|-------|--------|-------|
| Text readability | pass/fail | ... |
| Font consistency | pass/fail | ... |

## Color & Contrast
| Check | Result | Notes |
|-------|--------|-------|
| Contrast adequacy | pass/fail | estimated ratio |
| Color consistency | pass/fail | ... |

## Accessibility
| Check | Result | Notes |
|-------|--------|-------|
| Focus indicators | pass/fail | ... |
| Touch target size | pass/fail | ... |

## Issues
| Severity | Category | Description | Confidence |
|----------|----------|-------------|------------|
| ...      | ...      | ...         | ...        |

## Comparison with Design (if provided)
- Fidelity: {high/medium/low}
- Key differences: {list}

## Recommendations
1. {prioritized recommendation}
```

## 5. Hard-Fail Rules

| ID | Rule | Consequence |
|----|------|-------------|
| HF-UI-01 | Must not invent UI elements not present in the screenshot | Termination |
| HF-UI-02 | Must flag confidence for every observation; no unflagged claims | Termination |
| HF-UI-03 | Must not assign accessibility scores without visible evidence | Termination |
