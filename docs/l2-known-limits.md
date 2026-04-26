# L2 Known Limitations Document

## Overview

This document lists known limitations of the L2 capability layer. These are
acknowledged constraints that users and integrators should be aware of.

## General L2 Limitations

### 1. Agent Concurrency
- **Limit**: Only one L2 agent can be active per orchestrator session at a time
- **Impact**: Sequential processing of multi-domain requests
- **Workaround**: Orchestrator queues requests and processes serially

### 2. No Cross-Agent Memory
- **Limit**: L2 agents do not share working memory with each other
- **Impact**: Context from one agent is not automatically available to another
- **Workaround**: Use Memory module (v2.1) for persistent context sharing

### 3. Stateless by Default
- **Limit**: L2 agents (except Memory) do not persist state between invocations
- **Impact**: Each request starts fresh; no learning from previous interactions
- **Workaround**: Explicit memory_store/memory_retrieve calls

## Memory (v2.1) Limitations

### 4. Storage Size Limits
- **Limit**: 1MB per entry, 100MB per user
- **Impact**: Large datasets cannot be stored as single entries
- **Workaround**: Chunk large data, store references to external files

### 5. No Distributed Memory
- **Limit**: Memory is local to a single agent instance
- **Impact**: Multi-instance deployments have separate memory stores
- **Workaround**: Shared storage backend (future enhancement)

### 6. Semantic Search Quality
- **Limit**: Semantic search depends on embedding quality
- **Impact**: May return irrelevant results for ambiguous queries
- **Workaround**: Combine with exact-key retrieval for precision

### 7. TTL Precision
- **Limit**: TTL expiry is checked at access time, not proactively
- **Impact**: Expired entries may persist briefly if never accessed
- **Workaround**: Acceptable for most use cases; proactive sweeper planned

## Slide Maker (v2.2) Limitations

### 8. No Real-Time Collaboration
- **Limit**: Single-user editing model
- **Impact**: No concurrent editing or commenting
- **Workaround**: Generate and share static files

### 9. Image Inclusion Restrictions
- **Limit**: Only local file paths or data URIs; no URL-based images
- **Impact**: Cannot reference external image URLs directly
- **Workaround**: Download and include as local files

### 10. Template Dependency
- **Limit**: Output formatting depends on available templates
- **Impact**: Custom styling requires template modification
- **Workaround**: Markdown output is customizable; template system planned

## Spreadsheet (v2.3) Limitations

### 11. Large File Handling
- **Limit**: Files >100MB require sampling; full analysis not guaranteed
- **Impact**: Statistics may be approximate for very large datasets
- **Workaround**: Pre-filter or sample data before upload

### 12. Encoding Detection
- **Limit**: Auto-detection tries UTF-8 → GBK → Latin-1; may fail for other encodings
- **Impact**: Rare encodings may produce garbled output
- **Workaround**: Convert to UTF-8 before upload

### 13. Excel Formula Evaluation
- **Limit**: Formulas in .xlsx files are not evaluated; raw values only
- **Impact**: Cells with formulas show cached values, not computed results
- **Workaround**: Open and save in Excel to cache values before upload

### 14. Shell Sandbox Limitations
- **Limit**: Shell access is restricted to whitelisted commands
- **Impact**: Advanced data processing (e.g., custom Python libraries) may not work
- **Workaround**: Use allowed packages only; request package additions

## Multimodal (v2.4) Limitations

### 15. Visual Analysis Subjectivity
- **Limit**: Visual interpretation is inherently subjective
- **Impact**: Analysis results may vary for ambiguous visual content
- **Workaround**: Confidence annotations indicate reliability levels

### 16. No OCR (Text Extraction from Images)
- **Limit**: Text in images is read via visual reasoning, not dedicated OCR
- **Impact**: Small or stylized text may not be accurately transcribed
- **Workaround**: Provide high-resolution images; expect approximation

### 17. Chart Data Extraction Accuracy
- **Limit**: Extracted chart values are estimates based on visual position
- **Impact**: Values may have ±2-10% error depending on chart quality
- **Workaround**: Treat extracted data as approximate; verify critical values

### 18. Color Analysis Limitations
- **Limit**: Color names and hex codes are approximate
- **Impact**: Exact color matching is not guaranteed
- **Workaround**: Use relative descriptions (darker, lighter, similar)

### 19. Read-Only Constraint
- **Limit**: Multimodal agent cannot modify or create images
- **Impact**: Cannot generate annotated screenshots or corrected versions
- **Workaround**: Use external tools for image modification

## Runtime Limitations

### 20. Timeout Constraints
- **Limit**: Each L2 agent has a maximum execution time
- **Impact**: Long-running analyses may be interrupted
- **Workaround**: Break large tasks into smaller requests

### 21. No Retry for Failed Agents
- **Limit**: If an L2 agent fails, the request fails; no automatic retry
- **Impact**: Transient errors affect user experience
- **Workaround**: Manual retry by user; circuit breaker prevents cascading failures

### 22. Resource Contention
- **Limit**: Multiple L2 agents compete for the same compute resources
- **Impact**: Performance degradation under heavy load
- **Workaround**: Rate limiting and queue management

## Planned Improvements

| Limitation | Planned Resolution | Target Version |
|------------|-------------------|----------------|
| No cross-agent memory | Shared memory bus | v2.6 |
| TTL precision | Proactive sweeper | v2.1.1 |
| Large file sampling | Streaming engine | v2.3.1 |
| No OCR | Integrated OCR pipeline | v2.4.1 |
| Chart extraction accuracy | Calibration mode | v2.4.2 |
| Distributed memory | Shared backend | v2.6 |
