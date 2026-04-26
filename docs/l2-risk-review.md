# L2 Risk Review Document

## Overview

This document provides a risk assessment for each L2 spike, identifying
potential failures, their impact, and mitigation strategies.

## Risk Matrix

| Likelihood | Impact | Risk Level |
|------------|--------|------------|
| High | High | Critical |
| High | Medium | High |
| Medium | High | High |
| Medium | Medium | Medium |
| Low | High | Medium |
| Low | Medium | Low |

---

## Spike 1: Memory (memory-candidate)

### Risk Assessment

| Risk | Likelihood | Impact | Level |
|------|-----------|--------|-------|
| Data loss during store/retrieve | Low | High | Medium |
| Cross-session data leakage | Low | High | Medium |
| Storage exhaustion (OOM) | Medium | Medium | Medium |
| Concurrent access corruption | Medium | High | High |
| Encryption failure | Low | High | Medium |
| Privacy violation (unencrypted at rest) | Low | Critical | Medium |

### Mitigations

1. **Data loss**: Write-ahead logging, atomic operations, checksum validation
2. **Session leakage**: Strict session_id prefixing in storage keys, runtime assertions
3. **Storage exhaustion**: 1MB per entry limit, 100MB per user limit, LRU eviction
4. **Concurrency**: File-based locking, atomic rename for writes
5. **Encryption**: Fail-closed — if encryption fails, do not store
6. **Privacy**: Mandatory encryption for long-term memory, no plaintext persistence

### Residual Risk
After mitigations: **Medium** — concurrent access remains the highest concern.

---

## Spike 2: Slide Maker (slide-outline)

### Risk Assessment

| Risk | Likelihood | Impact | Level |
|------|-----------|--------|-------|
| Fabricated statistics in slides | Medium | Medium | Medium |
| Output format incompatibility | Medium | Medium | Medium |
| Runaway generation (>50 slides) | Low | Medium | Low |
| Content quality issues | Medium | Low | Low |

### Mitigations

1. **Fabricated data**: Hard-fail rule HF-SL-01 — terminate on fabrication
2. **Format incompatibility**: Strict schema validation, markdown fallback
3. **Runaway generation**: Max 50 slide cap with warning
4. **Content quality**: Outline approval gate before full generation

### Residual Risk
After mitigations: **Low**

---

## Spike 3: Spreadsheet

### Risk Assessment

| Risk | Likelihood | Impact | Level |
|------|-----------|--------|-------|
| Shell escape from restricted execution | Low | Critical | Medium |
| Large file OOM crash | Medium | Medium | Medium |
| Data fabrication in statistics | Medium | High | High |
| Missing value omission | Medium | High | High |
| Unsaved processing results | Low | Medium | Low |

### Mitigations

1. **Shell escape**: Whitelist-only command model, forbidden pattern matching, no network commands
2. **OOM crash**: Streaming reads, sampling for large files, memory monitoring
3. **Data fabrication**: Hard-fail rule HF-SS-01 — terminate immediately
4. **Missing value omission**: Mandatory null reporting per column, schema enforcement
5. **Unsaved results**: WriteFile permission required, validation that outputs exist

### Residual Risk
After mitigations: **Medium** — data quality enforcement relies on agent compliance.

---

## Spike 4: Multimodal

### Risk Assessment

| Risk | Likelihood | Impact | Level |
|------|-----------|--------|-------|
| Hallucination (describing non-existent elements) | High | High | Critical |
| False confidence (claiming certainty when uncertain) | High | Medium | High |
| Inability to process low-quality images | Medium | Low | Low |
| Privacy leak from image content | Low | High | Medium |
| Inappropriate content in uploaded images | Medium | Medium | Medium |

### Mitigations

1. **Hallucination**: Hard-fail rule HF-MM-01 — terminate on hallucination
2. **False confidence**: Mandatory confidence annotation on every observation
3. **Low-quality images**: Degradation strategy — analyze what is clear, flag rest
4. **Privacy leak**: No image storage, analysis only, no image output
5. **Inappropriate content**: Content filtering, refuse analysis of harmful content

### Residual Risk
After mitigations: **High** — visual analysis inherently has subjective elements.
Confidence annotation reduces but does not eliminate this risk.

---

## Cross-Cutting Risks

### Agent Handoff Failures
- **Risk**: Orchestrator fails to route to correct L2 agent
- **Impact**: Wrong agent activated, incorrect output
- **Mitigation**: Strict trigger condition matching, fallback to orchestrator

### Schema Drift
- **Risk**: Agent output no longer matches expected schema
- **Impact**: Downstream consumers break
- **Mitigation**: Schema validation on every output, version pinning

### Tool Permission Escalation
- **Risk**: Agent gains access to tools it should not have
- **Impact**: Security violation, potential data exfiltration
- **Mitigation**: Runtime permission enforcement, denylist hardening

### Performance Degradation
- **Risk**: L2 agents cause overall system slowdown
- **Impact**: SLA breaches, timeout cascades
- **Mitigation**: Per-agent timeouts, degradation strategies, circuit breakers

## Risk Summary by Spike

| Spike | Initial Risk | After Mitigation | Blocking Issue |
|-------|-------------|-------------------|----------------|
| memory-candidate | High | Medium | Concurrent access |
| slide-outline | Medium | Low | None |
| spreadsheet | High | Medium | Data fabrication prevention |
| multimodal | Critical | High | Hallucination control |

## Recommendation

Proceed with spikes in order: memory-candidate → slide-outline → spreadsheet → multimodal.
The multimodal spike should have the most conservative rollout (feature flag, gradual enablement)
due to its residual Critical-class risk.
