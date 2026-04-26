# ADR-0003: Why Flow Skills Are in the Skills Directory

## Status
Accepted

## Context

There was a debate about where to place "flow skills" (higher-level orchestration patterns like "research_flow", "code_review_flow") - should they be:

1. In a separate `flows/` directory
2. In the `skills/` directory alongside regular skills
3. Embedded in the coordinator logic

## Decision

We chose to place **Flow Skills in the `skills/` directory** for the following reasons:

### 1. Unified Skill Interface
Flow skills implement the same interface as regular skills. From the coordinator's perspective, there is no difference between invoking a "web_search" skill and a "research_flow" skill. Both are callable capabilities.

### 2. Recursive Composition
Flow skills can compose other skills (including other flow skills). Placing them in the same directory makes this composition natural and avoids cross-directory imports.

### 3. Discovery Mechanism
A single directory makes skill discovery straightforward. The coordinator can enumerate all available skills from one location without needing to merge results from multiple directories.

### 4. Consistent Testing
Flow skills can be tested using the same unit-smoke test framework as regular skills. No special handling is needed.

### 5. Gradual Complexity
Regular skills and flow skills exist on a spectrum of complexity. A "simple" skill might become a "flow" skill as it grows. Having them in the same directory avoids unnecessary moves.

### Naming Convention
Flow skills are distinguished by the `-flow` suffix in their filename:
- `web_search.py` - Regular skill
- `research_flow.py` - Flow skill

## Consequences

### Positive
- Simpler mental model: everything callable is a skill
- No special-casing for flow skills in the coordinator
- Easy to promote a regular skill to a flow skill
- Single discovery and loading mechanism

### Negative
- Skills directory can become large as flows are added
- Less visual distinction between atomic and composite skills
- Risk of confusion about skill granularity

### Mitigations
- Naming convention (`-flow` suffix) provides clear identification
- Sub-directories within `skills/` can be used for organization
- Documentation clearly distinguishes skill types
