# unit-smoke-005-writer

## test_title
Writer — Structured Report Generation

## test_objective
Verify that the writer agent can generate a structured report from an evidence-synthesis claim-evidence map. The output must include well-organized artifacts, complete report structure, and all claims must be backed by evidence — no new facts should be introduced without supporting evidence.

## min_input
Evidence-synthesis 提供的 claim-evidence map：

```json
{
  "topic": "AI编程助手市场分析报告",
  "claims": [
    {
      "id": "C001",
      "claim": "2025年全球AI编程助手市场规模预计达45亿美元",
      "evidence": ["EV001-Gartner-2025"],
      "confidence": 0.90,
      "type": "Fact"
    },
    {
      "id": "C002",
      "claim": "GitHub Copilot 占据约35%的市场份额",
      "evidence": ["EV002-TechCrunch-调研"],
      "confidence": 0.65,
      "type": "Analysis"
    },
    {
      "id": "C003",
      "claim": "AI编程助手在复杂架构设计场景效果有限",
      "evidence": ["EV003-Reddit-社区反馈"],
      "confidence": 0.55,
      "type": "Inference"
    },
    {
      "id": "C004",
      "claim": "62%的专业开发者已在日常使用AI编程工具",
      "evidence": ["EV004-StackOverflow-Survey"],
      "confidence": 0.85,
      "type": "Fact"
    },
    {
      "id": "C005",
      "claim": "若CAGR保持32%，2026年市场可达65亿美元",
      "evidence": ["EV001-Gartner-2025", "EV005-内部估算"],
      "confidence": 0.60,
      "type": "Assumption"
    }
  ],
  "recommendations": [
    "关注企业级市场的差异化需求",
    "投资复杂架构场景的AI能力",
    "监控CAGR可持续性风险"
  ]
}
```

任务：基于以上 claim-evidence map 生成一份结构化 Markdown 报告。

## expected_structured_output

```json
{
  "task_id": "writer-ai-coding-market-report",
  "status": "completed",
  "artifacts": [
    {
      "type": "markdown",
      "path": "reports/ai-coding-market-report-2025.md",
      "description": "AI编程助手市场分析报告（2025），包含市场规模、竞争格局、用户采纳率分析和建议"
    }
  ],
  "report_structure": {
    "title": "AI编程助手市场分析报告（2025）",
    "sections": [
      {
        "heading": "执行摘要",
        "content_type": "summary",
        "claims_used": ["C001", "C004"]
      },
      {
        "heading": "市场规模与增长",
        "content_type": "data_analysis",
        "claims_used": ["C001", "C005"]
      },
      {
        "heading": "竞争格局",
        "content_type": "analysis",
        "claims_used": ["C002"]
      },
      {
        "heading": "用户采纳与使用场景",
        "content_type": "analysis",
        "claims_used": ["C003", "C004"]
      },
      {
        "heading": "风险与不确定性",
        "content_type": "risk_assessment",
        "claims_used": ["C003", "C005"]
      },
      {
        "heading": "建议与展望",
        "content_type": "recommendations",
        "claims_used": []
      }
    ],
    "references": [
      "Gartner 2025 报告",
      "TechCrunch 用户调研",
      "Reddit 社区讨论",
      "Stack Overflow 开发者调查"
    ]
  },
  "word_count": 1500
}
```

Expected fields:
- `task_id` (string)
- `status` (string: "completed" | "in_progress" | "failed")
- `artifacts[]` (array with `type:"markdown"`, `path`, `description`)
- `report_structure` (object with `title`, `sections[]`, `references`)
- `word_count` (integer, approximate word count)

## raw_output_requirements

1. Must include the full Markdown report content (or a representative excerpt if too long).
2. Must show how each claim from the input was incorporated into the report.
3. Must include source citations in the report text.
4. Must include the structured_output JSON block.
5. Report must not introduce claims not present in the input evidence.

## hard_fail_conditions

1. 新增未经evidence支撑的事实：报告中出现了不在输入 claim-evidence map 中的新事实，且没有对应的 evidence 引用。
2. 报告结构缺失关键部分：report_structure.sections 缺少以下任一：执行摘要、市场规模与增长、竞争格局、用户采纳、建议与展望。
3. 无artifact输出：artifacts 数组为空或缺失 type="markdown" 的条目。

## acceptance_criteria

- [ ] `task_id` 非空
- [ ] `status` 为 completed 或 failed
- [ ] `artifacts[]` 至少包含一个 type 为 "markdown" 的条目
- [ ] `report_structure.title` 非空
- [ ] `report_structure.sections[]` 至少包含5个部分
- [ ] 每个 section 都有 `heading`, `content_type`, `claims_used`
- [ ] `report_structure.references` 非空
- [ ] `word_count` 为正整数
- [ ] 报告中不引入输入中不存在的新 claim
- [ ] 所有数据性陈述都带有来源引用

## technical_assumptions

- 输出格式为 Markdown
- word_count 为近似值，允许 +/- 10% 误差
- report_structure.sections 中 claims_used 应与输入 claim ID 对应
- 如输入 claim 的 confidence < 0.7，报告中应标注为"需谨慎解读"

## failure_fallback

If the writer agent fails:
1. Return `status: "failed"` with empty artifacts array.
2. Record `failure_reason` in output.
3. Fall back to a basic template report using raw evidence data.
4. Log error code `E005_WRITER_FAIL` to errors.jsonl.
