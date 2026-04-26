# ADR-0006: Why Direction Locking Mechanism

## Status
Accepted

## Context

In complex agent workflows, we observed a failure mode where the agent would:
1. Start with a clear plan
2. Encounter an unexpected result or tool failure
3. Pivot to a different approach without updating the overall plan
4. End up with fragmented, inconsistent outputs

This "drift" problem led us to consider a **Direction Locking Mechanism**.

## Decision

We implemented a **Direction Locking Mechanism** for the following reasons:

### 1. Plan Coherence
Once a task brief and minimal_plan are established, the agent must not deviate from the core direction without explicit replanning. This ensures the output remains aligned with the original goal.

### 2. Preventing Scope Creep
Without direction locking, agents tend to expand scope when they encounter interesting but tangential information. Locking prevents this by requiring explicit approval for scope changes.

### 3. Predictable Outputs
Users can rely on the agent following the agreed-upon plan. This predictability is essential for production use where outputs feed into downstream processes.

### 4. Error Recovery
When a tool fails or unexpected data is encountered, the agent must report the issue and propose a replan rather than silently changing direction. This makes failures visible and recoverable.

### How It Works

1. **Lock Acquisition**: When the coordinator approves a plan, a direction lock is established
2. **Lock Scope**: The lock covers: goal, deliverables, constraints, and minimal_plan
3. **Lock Violation Detection**: The agent checks proposed actions against the lock before executing
4. **Explicit Replanning**: To change direction, the agent must:
   - Report the need for change
   - Propose a new plan
   - Wait for coordinator approval
   - Only then release the old lock and acquire a new one

### Lock Enforcement Points

- Before executing any tool call
- Before delegating to a sub-agent
- Before modifying deliverables
- When encountering unexpected results

## Consequences

### Positive
- Consistent, predictable agent behavior
- Reduced scope creep
- Clear audit trail when plans change
- Better alignment with user expectations
- Easier debugging (plan deviations are explicit)

### Negative
- Reduced agent autonomy in dynamic situations
- Potential for rigid behavior when flexibility is needed
- Additional overhead for legitimate plan changes
- Requires careful tuning to avoid being overly restrictive

### Mitigations
- Direction locks are scoped, not absolute
- Sub-agents have more freedom within their delegated tasks
- Emergency override mechanism for critical situations
- Confidence thresholds determine lock strictness
- User can explicitly unlock/replan at any time
