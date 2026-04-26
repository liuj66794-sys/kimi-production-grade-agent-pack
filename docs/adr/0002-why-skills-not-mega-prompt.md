# ADR-0002: Why Skills Instead of Mega-Prompt

## Status
Accepted

## Context

When building the agent pack, we needed to decide how to encode agent capabilities. Two primary approaches emerged:

1. **Mega-Prompt** - A single, comprehensive prompt that contains all instructions, examples, and constraints
2. **Skills** - Modular, composable capability definitions that can be loaded on demand

## Decision

We chose the **Skills-based approach** over the Mega-Prompt approach for the following reasons:

### 1. Composability
Skills can be mixed and matched based on task requirements. The coordinator can load only the skills needed for a given task, rather than including all possible instructions in every prompt.

### 2. Maintainability
Individual skills can be updated, tested, and versioned independently. A change to one skill doesn't require reviewing the entire prompt.

### 3. Precision
Each skill can be precisely tuned for its specific purpose. A "web_search" skill can be optimized for search tasks without affecting a "code_execution" skill.

### 4. Token Efficiency
Loading only relevant skills reduces prompt size and token usage. This improves both latency and cost.

### 5. Testability
Skills can be unit-tested in isolation. The eval suite includes unit-smoke tests for individual skills (US-01 through US-08).

### 6. Extensibility
New skills can be added without modifying existing ones. Third-party contributors can add skills by following the skill schema.

## Consequences

### Positive
- Modular architecture supports incremental development
- Skills can be shared across different agent configurations
- Reduced cognitive load when modifying specific capabilities
- Better alignment with software engineering best practices

### Negative
- Requires a skill management and discovery mechanism
- Skill composition adds a small runtime overhead
- Need to handle skill version compatibility
- Potential for skill conflicts if not carefully designed

### Mitigations
- Skills are organized in a `skills/` directory with clear naming
- Skill dependencies are explicitly declared
- Integration tests verify skill composition works correctly
- Schema validation ensures skill definitions are well-formed
