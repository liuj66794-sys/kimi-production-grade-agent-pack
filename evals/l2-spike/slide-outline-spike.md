# Slide Outline Spike — Test Card

## Spike Information

| Field | Value |
|-------|-------|
| **Spike ID** | slide-outline-spike |
| **Version** | 2.2.0 |
| **Priority** | P1 |
| **Order** | #2 (second L2 spike) |
| **Agent** | slide-maker-sub |
| **Objective** | Validate slide outline generation and content creation pipeline |

## Dependencies

- L1 orchestrator (base)
- Memory module (optional — for user preferences)

## Success Criteria

- [ ] Can generate structured outline from topic
- [ ] Outline includes slide count and types
- [ ] Can generate full deck from approved outline
- [ ] Output conforms to slide-deck schema
- [ ] No fabricated statistics

## Test Cases

### TC-SLD-0001: Generate outline from topic
**Precondition**: Agent initialized
**Steps**:
1. Request outline for topic "AI in Healthcare"
2. Specify audience: "executive team"
3. Specify duration: "15 minutes"
**Expected**: Returns SlideOutline with 5-8 slides, includes title, content, and closing slides
**Priority**: P0

### TC-SLD-0002: Outline structure validation
**Precondition**: Outline generated from TC-SLD-0001
**Steps**:
1. Validate outline against schema
**Expected**: All required fields present, slide count within limits
**Priority**: P0

### TC-SLD-0003: Generate full deck from outline
**Precondition**: Approved outline exists
**Steps**:
1. Call `generate-slides(outline)` with approved outline
**Expected**: Returns complete slide deck in markdown format
**Priority**: P0

### TC-SLD-0004: Slide type variety
**Precondition**: Topic requires mixed content
**Steps**:
1. Request deck about "Q4 Sales Results"
**Expected**: Contains at least: 1 title, 2+ content, 1 data (table), 1 closing
**Priority**: P1

### TC-SLD-0005: Max slide cap enforcement
**Precondition**: Agent configured with max_slides=50
**Steps**:
1. Request outline for extremely broad topic
2. Request 100 slides
**Expected**: Outline capped at 50 slides, warning issued
**Priority**: P1

### TC-SLD-0006: Hard-fail HF-SL-01 (no fabrication)
**Precondition**: Topic mentions specific data points
**Steps**:
1. Request deck about "Our Product" with no data provided
2. Check if statistics are invented
**Expected**: No specific statistics without source data; uses placeholders or general statements
**Priority**: P0 (hard-fail rule)

### TC-SLD-0007: Hard-fail HF-SL-02 (outline before content)
**Precondition**: Direct content generation request
**Steps**:
1. Request full deck without outline approval
**Expected**: Agent generates outline first, requests approval
**Priority**: P0

### TC-SLD-0008: Speaker notes quality
**Precondition**: Full deck generated
**Steps**:
1. Inspect speaker notes on each slide
**Expected**: Notes add value beyond slide content, not verbatim repetition
**Priority**: P1

### TC-SLD-0009: Markdown output validity
**Precondition**: Deck generated
**Steps**:
1. Validate markdown syntax
2. Check frontmatter format
**Expected**: Valid markdown with proper YAML frontmatter
**Priority**: P0

### TC-SLD-0010: Format conversion fallback
**Precondition**: Full deck in markdown
**Steps**:
1. Request conversion to unavailable format
**Expected**: Falls back to markdown, provides conversion instructions
**Priority**: P2

## Hard-Fail Rules Under Test

| Rule ID | Description | Test Coverage |
|---------|-------------|---------------|
| HF-SL-01 | No fabricated data | TC-SLD-0006 |
| HF-SL-02 | Outline before content | TC-SLD-0007 |
| HF-SL-03 | Schema compliance | TC-SLD-0002, TC-SLD-0009 |
| HF-SL-04 | No verbatim speaker notes | TC-SLD-0008 |

## Known Limitations During Spike

- No real-time collaboration
- Image references must be local paths
- Template system not yet implemented (markdown only)
- No automatic chart/image generation

## Spike Duration

**Target**: 1 sprint (2 weeks)
**Actual**: TBD

## Exit Criteria

All P0 test cases (TC-SLD-0001, TC-SLD-0002, TC-SLD-0003, TC-SLD-0006, TC-SLD-0007, TC-SLD-0009) must pass.
P1 test cases are stretch goals.

## Spike Result

| Status | Date | Notes |
|--------|------|-------|
| TBD | - | - |
