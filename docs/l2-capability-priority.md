# L2 Capability Priority Document

## Priority Order

1. **P0: Memory** (Spike #1)
2. **P1: Slide Maker** (Spike #2)
3. **P2: Spreadsheet** (Spike #3)
4. **P3: Multimodal** (Spike #4)

## Rationale

### Why Memory First?

Memory is prioritized first (P0) for these reasons:

1. **Foundational Dependency**: Every other L2 agent benefits from persistent context.
   - Slide Maker remembers user's brand preferences
   - Spreadsheet remembers previous analysis context
   - Multimodal remembers user's design system references

2. **Highest Architectural Risk**: Memory touches data persistence, encryption, and
   session isolation — the most security-sensitive areas. Validating this early
   prevents costly rework.

3. **Clear Binary Success Criteria**: Memory either stores/retrieves correctly or
   it doesn't. This clarity makes it ideal as the first spike.

4. **Independent Scope**: Memory can be fully tested without any other L2 agents,
   reducing integration complexity for the first spike.

### Why Slide Maker Second?

Slide Maker is P1 because:

1. **Highest User Visibility**: Presentations are a common, high-value use case
   that users immediately understand and appreciate.

2. **Validates Handoff Pattern**: Slide Maker exercises the orchestrator-to-sub-agent
   handoff with a clear two-phase workflow (outline → content generation).

3. **Lower Risk**: Slide generation is largely stateless — output is deterministic
   given the same inputs, making testing and validation straightforward.

4. **Builds on Memory**: Can leverage memory for user preferences (templates,
   branding) immediately after memory is validated.

### Why Spreadsheet Third?

Spreadsheet is P2 because:

1. **Depends on Established Patterns**: Benefits from the handoff and schema
   enforcement patterns validated by Memory and Slide Maker.

2. **Moderate Complexity**: File I/O, Shell restrictions, and large file handling
   add complexity that is easier to manage after simpler spikes succeed.

3. **Tool Permission Complexity**: Spreadsheet is the first L2 agent with Shell
   access, requiring careful permission modeling that builds on prior learnings.

4. **Natural User Flow**: Users often analyze data before creating presentations,
   so spreadsheet naturally follows slide maker in typical workflows.

### Why Multimodal Last?

Multimodal is P3 because:

1. **Highest Uncertainty**: Visual analysis quality is inherently non-deterministic.
   The confidence annotation system needs real-world validation.

2. **Read-Only Constraint**: Being the first read-only agent, its failure modes
   are different and less understood.

3. **Hallucination Risk**: This is the spike most likely to produce plausible-sounding
   but incorrect output. It requires the most guardrails.

4. **Downstream Dependencies**: Multimodal outputs may feed into other agents
   (e.g., extracted chart data goes to spreadsheet analysis), so its accuracy
   affects the whole system.

## Dependency Graph

```
                    +---------------+
                    |   L1 Base     |
                    +-------+-------+
                            |
              +-------------+-------------+
              |                           |
              v                           v
       +------------+             +------------+
       |  Memory    |             | Orchestrator|
       |   (P0)     |             |   (L1)      |
       +------+-----+             +------+------+
              |                           |
              +-------------+-------------+
                            |
              +-------------+-------------+-------------+
              |                           |             |
              v                           v             v
       +------------+            +------------+  +------------+
       |Slide Maker |            |Spreadsheet |  | Multimodal |
       |   (P1)     |            |   (P2)     |  |   (P3)     |
       +------------+            +------------+  +------------+
              |                           ^             ^
              |                           |             |
              +---------------------------+             |
              | (chart data can flow to spreadsheet)    |
              +-----------------------------------------+
                    | (extracted visuals can feed analysis)
```

## Rollout Strategy

| Phase | Spike | Criteria to Proceed |
|-------|-------|-------------------|
| 1 | Memory | Store/retrieve works, no session leakage, SLA met |
| 2 | Slide Maker | Outline→content pipeline works, schema valid |
| 3 | Spreadsheet | Analysis pipeline works, Shell sandbox secure |
| 4 | Multimodal | Confidence system works, hallucination rate <5% |

## Reversal Criteria

Any spike may be re-prioritized if:
- A P0/P1 spike fails to meet success criteria after 2 iterations
- External requirements change (e.g., multimodal becomes business-critical)
- A downstream spike discovers a blocking dependency on an upstream spike
