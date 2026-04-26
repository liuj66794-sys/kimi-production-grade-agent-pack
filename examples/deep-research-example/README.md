# Deep Research Example

> **Agent**: `deep-research`  
> **Capability**: Multi-source research with evidence synthesis  
> **Level**: L1 MVP

---

## Objective

Demonstrate the deep-research agent's ability to gather information from multiple sources, synthesize findings, and produce a structured research report with citations.

---

## Input

- **File**: `input.txt` — A research topic or question
- **Format**: Plain text, one topic per file

### Sample Input

```
Research the current state of large language model evaluation benchmarks,
comparing MMLU, HumanEval, and newer benchmarks like SWE-bench and LiveBench.
Focus on what each benchmark measures and their limitations.
```

---

## Expected Output

- **File**: `artifacts/deep-research-report.md`
- **Format**: Markdown with the following sections:
  - Executive Summary
  - Benchmark Comparisons (table)
  - Detailed Analysis per Benchmark
  - Limitations and Gaps
  - Recommendations
  - References (cited sources)

### Output Quality Criteria

- [ ] At least 3 benchmarks covered
- [ ] Each benchmark has description, metrics, and limitations
- [ ] Contains comparison table
- [ ] References section has 3+ citations
- [ ] Total length >= 1000 words

---

## Running the Example

```powershell
# Navigate to project root
cd kimi-production-grade-agent-pack

# Activate virtual environment
# .venv\Scripts\activate   # Windows

# Run with the researcher sub-agent (interactive mode)
kimi --agent-file agents/researcher-sub.yaml --prompt (Get-Content examples/deep-research-example/input.txt -Raw)

# Or run with the production coordinator (full swarm)
kimi --agent-file agents/production-coordinator.yaml --prompt (Get-Content examples/deep-research-example/input.txt -Raw)

# Or run in non-interactive print mode
kimi --agent-file agents/researcher-sub.yaml --print --prompt (Get-Content examples/deep-research-example/input.txt -Raw)
```

---

## Verification

```powershell
# Check output exists and is non-empty
Get-ChildItem -Path 'artifacts/deep-research-report.md'
(Get-Content 'artifacts/deep-research-report.md').Length
# Check QA gate result
Get-Content 'artifacts/qa-gate-result.json' | Select-String -Pattern 'deep-research```'

---

## Notes

- Research quality depends on available search/index capabilities
- Timeout may need adjustment for complex topics: `--timeout 300`
- Use `--output-format json` for structured output
