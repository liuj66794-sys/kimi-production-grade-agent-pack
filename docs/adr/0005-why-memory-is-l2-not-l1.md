# ADR-0005: Why Memory Is L2, Not L1

## Status
Accepted

## Context

We needed to decide the priority level for memory capabilities in the agent pack:

- **L1 (Core/Foundation)** - Must have; essential for basic operation
- **L2 (Advanced)** - Important but not required for initial functionality
- **L3 (Optional)** - Nice to have; can be added later

## Decision

We classified **Memory as L2 (Advanced)** rather than L1 (Core) for the following reasons:

### 1. L1 Scope Definition
L1 capabilities must enable the agent to complete basic tasks without any external dependencies. The core L1 loop is: receive task -> plan -> execute -> deliver. Memory enhances this but is not required for it.

### 2. Stateless by Default
The agent operates correctly in a stateless mode. Each task is self-contained with all necessary context provided in the task brief. Memory is an optimization, not a requirement.

### 3. Complexity Cost
Memory systems introduce significant complexity:
- Storage backend selection and configuration
- Retrieval mechanisms (semantic search, keyword matching)
- Memory lifecycle (what to remember, what to forget)
- Conflict resolution (conflicting memories)
- Privacy and security concerns

### 4. Progressive Enhancement
Placing memory at L2 allows the agent pack to deliver value immediately while memory capabilities are developed and refined. Users can start with L1 and upgrade to L2 when needed.

### 5. Clear Interfaces
Even though memory is L2, the interfaces are defined from the start. The `memory-mcp.json` configuration and `memory_access` capability are specified so that L1 can seamlessly transition to L2.

### What L1 Includes Instead
- Task brief generation and parsing
- Basic tool use (web search, code execution, file I/O)
- Sub-agent delegation
- Evidence tracking (in-task only, not cross-task)
- Quality review

## Consequences

### Positive
- Faster time to first working version
- Simpler initial architecture
- Clear separation between core and advanced features
- Memory can be designed properly without rushing

### Negative
- Agent cannot recall information from previous tasks
- Cross-task learning is not possible at L1
- User may need to re-provide context for related tasks

### Mitigations
- L1 preserves full context within a single task via `context_snapshot`
- Evidence maps can be saved as artifacts for manual reference
- L2 memory will be backward-compatible with L1 task structures
- Upgrade path from L1 to L2 is clearly documented
