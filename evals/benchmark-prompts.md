# Benchmark Prompts for Kimi Production-Grade Agent Pack v1.0
# ============================================================

This document contains the core evaluation prompts used in smoke testing.
Each prompt is designed to test a specific agent capability.

---

## SM-01: Fuzzy Requirement to Task Brief

**Category**: Task Decomposition
**Expected Schema**: task-brief.schema.json

### Prompt
```
I need you to help me research the current state of AI agent frameworks.
I want something comprehensive that covers the major players, their approaches,
and what's working well vs. not. Make it actionable.
```

### Evaluation Criteria
- Output must be a valid task-brief.schema.json
- Must include: goal, deliverables, input_materials, constraints
- Must set need_web=true, need_code=false
- Must identify required_capabilities (at minimum: web_search, web_browse)
- Must include a minimal_plan with at least 3 steps

---

## SM-02: Single-Topic Deep Research

**Category**: Deep Research
**Expected Schema**: evidence-map.schema.json

### Prompt
```
Conduct deep research on "Retrieval-Augmented Generation (RAG) architecture patterns
in production systems as of 2024". I need you to:

1. Find and analyze at least 5 authoritative sources
2. Extract specific architectural patterns and their trade-offs
3. Map claims to evidence with confidence ratings
4. Identify any conflicting information across sources
5. Provide a final evidence map

Produce an evidence-map.schema.json output.
```

### Evaluation Criteria
- Output must be a valid evidence-map.schema.json
- Must contain at least 5 claims
- Each claim must have at least one evidence_refs entry
- Must include source reliability ratings
- Claims must have confidence ratings

---

## SM-03: Multi-Source Evidence Synthesis

**Category**: Evidence Synthesis
**Expected Schema**: evidence-map.schema.json

### Prompt
```
I have conflicting information about the effectiveness of different
LLM fine-tuning approaches. Here are three sources with different conclusions:

Source A (Research Paper): "LoRA achieves 95% of full fine-tuning performance
with only 0.1% of trainable parameters"

Source B (Industry Blog): "In production, full fine-tuning consistently
outperforms LoRA by 15-20% on domain-specific tasks"

Source C (Benchmark Study): "QLoRA matches full fine-tuning on most benchmarks
while using 4x less GPU memory"

Synthesize these sources, resolve the conflicts, and produce an evidence map.
```

### Evaluation Criteria
- Must detect and document conflicts between sources
- Must provide resolution reasoning for each conflict
- Must assign appropriate confidence levels considering source conflicts
- Must include all three sources in the evidence map

---

## SM-04: Code Fix with Validation

**Category**: Code Execution
**Expected Artifacts**: Fixed code file, test output

### Prompt
```
The following Python function has a bug. Fix it and validate your fix:

```python
def calculate_moving_average(data, window):
    result = []
    for i in range(len(data)):
        start = max(0, i - window)
        subset = data[start:i]
        result.append(sum(subset) / len(subset))
    return result
```

1. Identify the bug
2. Fix the code
3. Write tests covering normal case, edge case, and error case
4. Run the tests and confirm all pass
5. Provide the fixed code and test results
```

### Evaluation Criteria
- Bug must be correctly identified (off-by-one in window/range)
- Fix must be correct
- Tests must cover normal, edge, and error cases
- All tests must pass
- Code must be provided as a file artifact

---

## SM-05: PPT Outline Generation

**Category**: Content Generation
**Expected Artifacts**: ppt_outline.json

### Prompt
```
Create a structured PPT outline for a presentation titled
"Building Production-Grade AI Agents: Architecture and Best Practices".

The presentation should:
1. Target technical leads and senior engineers
2. Be 12-15 slides
3. Include a clear narrative arc
4. Each slide must have a page-level key message
5. Include speaker notes for key slides
6. Follow a logical structure: problem -> solution -> implementation -> results

Output as a structured JSON file.
```

### Evaluation Criteria
- Must have 12-15 slides
- Each slide must have a clear key message
- Must follow the requested structure
- Must include speaker notes
- Output must be valid JSON with proper structure

---

## SM-06: Table Model Generation

**Category**: Structured Data
**Expected Schema**: evidence-map.schema.json (for source traceability)

### Prompt
```
Create a comparison table of 5 major AI agent frameworks:
LangChain, AutoGen, CrewAI, LlamaIndex, and Semantic Kernel.

For each framework, include columns for:
- Primary language
- Key abstractions
- Strengths (2-3 points)
- Weaknesses (2-3 points)
- Best use cases
- Community size/activity
- Latest release date

Every cell must cite its source. Produce both the table and an evidence map
showing source traceability for each data point.
```

### Evaluation Criteria
- Table must have all specified columns
- Every data point must have a source reference
- Evidence map must link table cells to sources
- Sources must have reliability ratings
- Must include at least 5 unique sources

---

## SM-07: Quality Review Execution

**Category**: Quality Assurance
**Expected Schema**: quality-review.schema.json

### Prompt
```
Perform a quality review of the following agent output:

[OUTPUT TO REVIEW]
{
  "task_id": "research-123",
  "agent": "research-agent",
  "conclusions": [
    "Kubernetes is the most widely used container orchestration platform",
    "Serverless computing eliminates all operational overhead"
  ],
  "evidence": [
    {
      "claim": "Kubernetes leads the market",
      "source": "https://example.com/survey",
      "confidence": "high"
    }
  ],
  "artifacts": [
    {"type": "document", "path": "report.md"}
  ]
}
[/OUTPUT TO REVIEW]

Review against all 10 quality dimensions and produce a quality-review.schema.json.
Flag any hard fails.
```

### Evaluation Criteria
- Output must be valid quality-review.schema.json
- Must evaluate all 10 dimensions
- Must identify the unsupported claim ("eliminates ALL overhead")
- Must flag hard fails where applicable
- Must provide actionable remediation notes

---

## SM-08: Sub-Agent Context Snapshot Check

**Category**: Sub-agent Output
**Expected Schema**: subagent-result.schema.json

### Prompt
```
Simulate a sub-agent that has just completed a research task.
The sub-agent searched the web for "2024 AI agent benchmarks",
read 3 documents (agent-bench-2024.pdf, mlcommons.pdf, blog-post.md),
and used web_search and file_read tools.

Produce a subagent-result.schema.json that includes:
1. Complete context_snapshot with all input files, search queries, and tools used
2. At least 3 conclusions with evidence
3. At least 2 artifacts
4. Any assumptions made
5. A recommended next step
```

### Evaluation Criteria
- Must be valid subagent-result.schema.json
- context_snapshot must include ALL input files
- context_snapshot must include ALL search queries
- context_snapshot must include ALL tools used
- Must have at least 3 conclusions
- Must have at least 2 artifacts
- Must include next_step recommendation

---

## Appendix: Prompt Metadata

| ID | Category | Schema | Max Steps | Critical |
|----|----------|--------|-----------|----------|
| SM-01 | Task Decomposition | task-brief | 15 | Yes |
| SM-02 | Deep Research | evidence-map | 20 | Yes |
| SM-03 | Evidence Synthesis | evidence-map | 20 | Yes |
| SM-04 | Code Execution | N/A | 20 | Yes |
| SM-05 | Content Generation | N/A | 15 | Yes |
| SM-06 | Structured Data | evidence-map | 15 | No |
| SM-07 | Quality Assurance | quality-review | 15 | Yes |
| SM-08 | Sub-agent Output | subagent-result | 10 | Yes |
