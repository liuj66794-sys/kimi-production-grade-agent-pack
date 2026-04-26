# Memory Candidate Spike — Test Card

## Spike Information

| Field | Value |
|-------|-------|
| **Spike ID** | memory-candidate-spike |
| **Version** | 2.1.0 |
| **Priority** | P0 |
| **Order** | #1 (first L2 spike) |
| **Agent** | memory-sub |
| **Objective** | Validate basic memory store/retrieve functionality |

## Success Criteria

- [x] Can store a key-value pair
- [x] Can retrieve by exact key
- [x] Can retrieve by semantic query
- [x] Memory respects TTL (time-to-live)
- [ ] No data leakage between user sessions

## Test Cases

### TC-MEM-0001: Store and retrieve by exact key
**Precondition**: Memory agent initialized, empty store
**Steps**:
1. Call `memory_store(key="project_name", value="Alpha", type="short_term")`
2. Call `memory_retrieve(key="project_name")`
**Expected**: Returns MemoryEntry with value "Alpha"
**Priority**: P0

### TC-MEM-0002: Retrieve with missing key
**Precondition**: Store does not contain key "nonexistent"
**Steps**:
1. Call `memory_retrieve(key="nonexistent")`
**Expected**: Returns null (not an error)
**Priority**: P0

### TC-MEM-0003: TTL expiry
**Precondition**: Clock is functional
**Steps**:
1. Store with TTL=2 seconds
2. Retrieve immediately → should return value
3. Wait 3 seconds
4. Retrieve again → should return null
**Expected**: Entry expired and removed
**Priority**: P0

### TC-MEM-0004: Session isolation
**Precondition**: Two different session IDs
**Steps**:
1. Store `key="secret"` with session_id="session_A"
2. Retrieve with session_id="session_B"
**Expected**: Returns null (no cross-session access)
**Priority**: P0 (hard-fail if fails)

### TC-MEM-0005: JSON serialization validation
**Precondition**: Various data types
**Steps**:
1. Store a nested object
2. Store a list
3. Store a datetime string
**Expected**: All stored successfully, types preserved on retrieve
**Priority**: P1

### TC-MEM-0006: Semantic search
**Precondition**: Multiple entries stored
**Steps**:
1. Store "The project deadline is Friday"
2. Store "Team standup is at 10am"
3. Search "when is the deadline"
**Expected**: Returns first entry as top result
**Priority**: P1

### TC-MEM-0007: Hard-fail HF-MEM-01 (data loss)
**Precondition**: Normal operation
**Steps**:
1. Store a value
2. Verify immediate retrieval succeeds
3. Simulate graceful shutdown and restart
4. Retrieve same key
**Expected**: Long-term memory value preserved; short-term may be lost
**Priority**: P0

### TC-MEM-0008: Storage limits
**Precondition**: Clean state
**Steps**:
1. Attempt to store 1.5MB entry
**Expected**: Rejected with "entry exceeds 1MB limit"
**Priority**: P1

## Hard-Fail Rules Under Test

| Rule ID | Description | Test Coverage |
|---------|-------------|---------------|
| HF-MEM-01 | No data loss | TC-MEM-0007 |
| HF-MEM-02 | No cross-session leakage | TC-MEM-0004 |
| HF-MEM-03 | Respect TTL | TC-MEM-0003 |
| HF-MEM-04 | Encrypt at rest | Security review |
| HF-MEM-05 | JSON validation | TC-MEM-0005 |

## Known Limitations During Spike

- Semantic search uses simple keyword matching (not embeddings)
- TTL cleanup is passive (checked at access time only)
- No distributed memory (single instance)

## Spike Duration

**Target**: 1 sprint (2 weeks)
**Actual**: TBD

## Exit Criteria

All P0 test cases (TC-MEM-0001 through TC-MEM-0004, TC-MEM-0007) must pass.
P1 test cases are stretch goals.

## Spike Result

| Status | Date | Notes |
|--------|------|-------|
| TBD | - | - |
