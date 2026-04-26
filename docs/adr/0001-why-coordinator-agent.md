# ADR-0001: Why Coordinator Agent Pattern

## Status
Accepted

## Context

The agent pack needs a mechanism to handle complex, multi-step tasks that may require different capabilities, tools, and sub-tasks. We evaluated several architectural patterns for orchestrating agent workflows:

1. **Single Monolithic Agent** - One agent handles everything
2. **Coordinator Agent Pattern** - A coordinator delegates to specialized sub-agents
3. **Pure Pipeline** - Fixed sequence of processing steps
4. **Event-Driven Architecture** - Agents react to events

## Decision

We chose the **Coordinator Agent Pattern** for the following reasons:

### 1. Separation of Concerns
The coordinator handles planning, delegation, and synthesis while sub-agents focus on execution. This separation makes the system more maintainable and easier to reason about.

### 2. Scalability
New capabilities can be added by introducing new sub-agent types without modifying the coordinator's core logic. The coordinator only needs to know how to delegate, not how to perform every task.

### 3. Failure Isolation
If a sub-agent fails, the coordinator can retry, re-delegate, or report the failure without affecting other parts of the workflow. This provides better resilience.

### 4. Context Management
The coordinator maintains a unified view of the task while sub-agents work with focused contexts. The `context_snapshot` mechanism in sub-agent results ensures traceability.

### 5. Proven Pattern
The coordinator pattern is well-established in multi-agent systems (e.g., AutoGen, CrewAI) and has demonstrated effectiveness in production environments.

## Consequences

### Positive
- Clear separation of planning and execution
- Sub-agents can be developed and tested independently
- Easy to add new skills by adding new sub-agents
- Centralized error handling and retry logic

### Negative
- Additional latency due to delegation overhead
- Coordinator becomes a single point of failure
- More complex debugging (need to trace across agent boundaries)
- Requires careful design of inter-agent communication protocol

### Mitigations
- Sub-agents are stateless; all state flows through the coordinator
- `context_snapshot` provides full traceability
- Hard-fail rules (HF-08) enforce complete context reporting
- Timeout and retry policies prevent coordinator blocking
