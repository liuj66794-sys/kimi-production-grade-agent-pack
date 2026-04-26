# L2 Runtime SLA Document

## Overview

This document defines the Service Level Agreements (SLAs) for L2 agent runtime
performance, including response time targets, timeout thresholds, and fallback
strategies.

## SLA Metrics Summary

| Metric | Target | Warning Threshold | Critical Threshold | Unit |
|--------|--------|-------------------|-------------------|------|
| Agent activation latency | 500 | 1000 | 3000 | ms |
| Response time (simple) | 5000 | 10000 | 30000 | ms |
| Response time (complex) | 30000 | 60000 | 120000 | ms |
| Error rate | 1 | 3 | 5 | % |
| Timeout rate | 0.5 | 2 | 5 | % |
| Availability | 99.9 | 99.5 | 99.0 | % |

## Per-Agent SLA

### Memory Agent (v2.1)

| Operation | Target | Timeout | Fallback |
|-----------|--------|---------|----------|
| Store | 50ms | 500ms | Return error, suggest retry |
| Retrieve (exact) | 20ms | 200ms | Return null |
| Search (text) | 100ms | 1000ms | Return empty results |
| Search (semantic) | 500ms | 3000ms | Fall back to text search |
| Delete | 20ms | 200ms | Log error, continue |

### Slide Maker Agent (v2.2)

| Operation | Target | Timeout | Fallback |
|-----------|--------|---------|----------|
| Outline generation | 5000ms | 15000ms | Return basic outline template |
| Full deck generation | 30000ms | 60000ms | Return partial deck with [TBD] markers |
| Format conversion | 2000ms | 10000ms | Return unformatted markdown |

### Spreadsheet Agent (v2.3)

| Operation | Target | Timeout | Fallback |
|-----------|--------|---------|----------|
| File read (<10MB) | 2000ms | 10000ms | Return error with file size note |
| File read (10-100MB) | 10000ms | 30000ms | Switch to streaming/sampling |
| Analysis (<100K rows) | 15000ms | 60000ms | Return partial analysis |
| Analysis (100K-1M rows) | 60000ms | 120000ms | Return sampled analysis |
| Report generation | 2000ms | 10000ms | Return minimal summary |

### Multimodal Agent (v2.4)

| Operation | Target | Timeout | Fallback |
|-----------|--------|---------|----------|
| Image analysis (standard) | 10000ms | 30000ms | Return degraded analysis |
| Image analysis (high-res) | 20000ms | 45000ms | Downsample and retry |
| Chart extraction | 15000ms | 30000ms | Return chart type only |
| Design comparison | 20000ms | 45000ms | Return single-image analysis |

## Enforcement Rules

### Rule 1: Timeout Handling
- Every L2 agent operation has a defined timeout
- On timeout: execute fallback strategy, log incident
- Never block indefinitely

### Rule 2: Circuit Breaker
- After 3 consecutive failures, agent enters "open" state
- In open state: reject new requests for 30 seconds
- After cooldown: allow 1 probe request
- If probe succeeds: close circuit; if fails: extend cooldown

### Rule 3: Graceful Degradation
- When SLA target is exceeded but timeout not reached:
  - Switch to simplified processing
  - Add [degraded] marker to output
  - Include explanation of limitations

### Rule 4: Error Classification
- **Transient errors** (timeout, temporary resource shortage): retryable
- **Permanent errors** (schema violation, hard-fail trigger): not retryable
- **Agent errors**: return error to orchestrator, log for investigation

### Rule 5: Monitoring & Alerting
- **Warning**: Metric exceeds target but below critical threshold
- **Critical**: Metric exceeds critical threshold
- **Page**: Availability drops below 99% for >2 minutes

## Fallback Strategies

### Strategy 1: Simplified Output
When full analysis times out, return:
- Basic metadata (file size, row count)
- High-level summary only
- Note: "Full analysis timed out; partial results provided"

### Strategy 2: Alternative Agent
When primary agent fails:
- For Spreadsheet: return raw file metadata
- For Slide Maker: return outline template
- For Multimodal: return file metadata only
- For Memory: operate in ephemeral mode (no persistence)

### Strategy 3: User Notification
When fallback is activated:
- Inform user that degraded mode is active
- Explain what functionality is limited
- Simplify request or try again later

## SLA Measurement

### Data Collection
- All agent operations are timed (start → response)
- Outcomes logged: success, timeout, error, degraded
- Metrics aggregated per minute, hour, day

### Reporting
- Real-time dashboard: current status vs SLA
- Daily report: SLA compliance percentage
- Weekly report: trend analysis, top violations

### SLA Violation Response
| Severity | Response Time | Action |
|----------|--------------|--------|
| Warning | 4 hours | Review, document |
| Critical | 1 hour | Investigate, apply fixes |
| Outage | 15 minutes | Emergency response, disable affected agent |

## Revision History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2024-01-01 | Initial SLA definition |
| 1.1 | 2024-02-15 | Added circuit breaker rules |
| 2.0 | 2024-06-01 | L2-specific SLAs added |
