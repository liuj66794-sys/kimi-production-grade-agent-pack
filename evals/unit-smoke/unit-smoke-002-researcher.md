# unit-smoke-002-researcher

## test_title
Researcher — Information Retrieval and Source Filtering

## test_objective
Verify that the researcher agent can execute information retrieval (web search, document lookup) and perform source quality filtering. The output must include search query records, sourced evidence with confidence ratings, and a context snapshot for downstream agents.

## min_input
研究主题：2025年AI编程助手市场规模

具体任务要求：
1. 搜索2025年AI编程助手的市场规模数据和增长预测
2. 筛选至少3个不同级别的来源（A级：权威机构报告；B级：知名媒体/分析；C级：社区/博客）
3. 对每条关键数据标注来源、置信度和局限性
4. 输出结构化的证据列表和结论摘要

## expected_structured_output

```json
{
  "task_id": "research-2025-ai-coding-market",
  "status": "completed",
  "conclusion": [
    "2025年全球AI编程助手市场规模预计达到X亿美元",
    "年复合增长率（CAGR）预计为Y%",
    "主要增长驱动因素包括：企业采用率提升、IDE集成深化、个人开发者付费意愿增强"
  ],
  "evidence": [
    {
      "claim": "2025年全球AI编程助手市场规模预计达到X亿美元",
      "source": "https://example.com/market-report-2025",
      "source_type": "market_research",
      "source_level": "A",
      "confidence": 0.85,
      "caveat": "预测数据基于当前增长率外推，未考虑重大技术突破或监管变化"
    },
    {
      "claim": "企业采用率从2024年的Z%提升至2025年的W%",
      "source": "https://example.com/tech-media-analysis",
      "source_type": "news",
      "source_level": "B",
      "confidence": 0.70,
      "caveat": "样本量有限，仅覆盖北美和欧洲市场"
    },
    {
      "claim": "个人开发者付费意愿显著增强",
      "source": "https://example.com/dev-survey-2025",
      "source_type": "survey",
      "source_level": "B",
      "confidence": 0.75,
      "caveat": "自报告数据可能存在偏差"
    }
  ],
  "context_snapshot": {
    "search_queries": [
      "2025 AI coding assistant market size",
      "AI programming helper market forecast 2025",
      "GitHub Copilot competitors market share 2025"
    ],
    "sources_consulted": 8,
    "sources_filtered": 3,
    "research_time": "2025-01-15T10:00:00Z"
  },
  "artifacts": [
    {
      "type": "research_notes",
      "path": "research/2025-ai-coding-market-notes.md",
      "description": "完整的研究笔记，包含所有搜索查询和来源评估"
    }
  ]
}
```

Expected fields:
- `task_id` (string)
- `status` (string: "completed" | "in_progress" | "failed")
- `conclusion[]` (array of strings)
- `evidence[]` (array of objects, each with: `claim`, `source`, `source_type`, `confidence`, `caveat`)
- `context_snapshot` (object, must include `search_queries`)
- `artifacts[]` (array of objects with `type`, `path`, `description`)

## raw_output_requirements

1. Must show the search query log (what was searched, in what order).
2. Must include source-level annotations (A/B/C/D/E) for each piece of evidence.
3. Must explain why low-confidence sources were filtered out.
4. Must include the structured_output JSON block.
5. The context_snapshot must be detailed enough for a sub-agent to continue without re-searching.

## hard_fail_conditions

1. 没有搜索查询记录：context_snapshot 中 search_queries 为空或缺失。
2. 没有来源：evidence 数组为空，或所有 claim 都没有 source 字段。
3. 所有来源都是E级：所有 evidence 条目的 source_level 均为 "E"（不可靠来源）。
4. 声称搜索但未记录查询：raw_output 声称进行了搜索，但 search_queries 数组为空。

## acceptance_criteria

- [ ] `task_id` 非空，语义清晰
- [ ] `status` 为 completed、in_progress 或 failed 之一
- [ ] `conclusion[]` 至少包含一条结论
- [ ] `evidence[]` 至少包含一条带来源的证据
- [ ] 每条 evidence 都有 `claim`, `source`, `source_type`, `confidence`, `caveat`
- [ ] `context_snapshot` 包含 `search_queries` 数组
- [ ] `artifacts[]` 存在（可为空）
- [ ] 至少有一个非E级来源
- [ ] search_queries 数组非空

## technical_assumptions

- 研究主题可能有公开数据也可能没有；没有时不编造数据，应明确标注"未找到可靠数据"
- source_level 分级标准：A=权威机构（Gartner/IDC/政府），B=知名媒体/分析，C=社区/博客，D=社交媒体，E=未验证
- 置信度为0.0-1.0的浮点数

## failure_fallback

If the researcher agent fails:
1. Return a `status: "failed"` result with empty evidence array.
2. In `context_snapshot`, record `failure_reason` explaining why search failed.
3. Downstream analyst agent should skip analysis and report "insufficient evidence".
4. Log error code `E002_RESEARCH_FAIL` to errors.jsonl.
