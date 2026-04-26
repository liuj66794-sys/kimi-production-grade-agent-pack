# unit-smoke-003-analyst

## test_title
Analyst — Structured Analysis with Distinction of Fact/Analysis/Inference/Assumption

## test_objective
Verify that the analyst agent can perform structured analysis on research-provided evidence, correctly distinguishing between Fact (verified data), Analysis (interpretation), Inference (deductive conclusion), and Assumption (unverified premise). The output must include uncertainty annotations and confidence ratings.

## min_input
Researcher 提供的资料摘要：

```
Evidence Summary:
1. [A级来源 - Gartner 2025报告] 全球AI编程助手市场2025年预计达45亿美元，CAGR 32%
2. [B级来源 - TechCrunch] GitHub Copilot 占据 35% 市场份额（基于用户调研，非官方数据）
3. [C级来源 - Reddit讨论] 开发者普遍反映AI助手在复杂架构设计场景下效果有限
4. [A级来源 - Stack Overflow Survey] 62% 的专业开发者已在日常工作中使用AI编程工具
5. [B级来源 - 内部估算] 预计2026年市场将达65亿美元
```

任务：基于以上证据进行结构化分析，输出带有置信度和不确定性标注的结论。

## expected_structured_output

```json
{
  "task_id": "analysis-2025-ai-coding-market",
  "status": "completed",
  "conclusion": [
    {
      "statement": "AI编程助手市场处于快速增长阶段，2025年规模约45亿美元",
      "type": "Fact",
      "basis": "Gartner 2025报告（A级来源）",
      "confidence": 0.90
    },
    {
      "statement": "GitHub Copilot 在市场中占据领先地位，份额约35%",
      "type": "Analysis",
      "basis": "TechCrunch用户调研（B级来源），但非官方数据",
      "confidence": 0.65
    },
    {
      "statement": "AI编程助手在复杂架构设计场景的应用效果可能受限",
      "type": "Inference",
      "basis": "Reddit社区反馈（C级来源），需进一步验证",
      "confidence": 0.55
    },
    {
      "statement": "若当前增长趋势持续，2026年市场可能达到65亿美元",
      "type": "Assumption",
      "basis": "基于32% CAGR的外推估算（B级来源）",
      "confidence": 0.60,
      "uncertainty": "高度依赖当前增长率是否可持续，未考虑技术突破或监管变化"
    },
    {
      "statement": "AI编程工具已成为专业开发者的主流辅助工具",
      "type": "Fact",
      "basis": "Stack Overflow Survey（A级来源），62%使用率",
      "confidence": 0.85
    }
  ],
  "evidence": [
    {
      "id": "EV001",
      "claim": "全球AI编程助手市场2025年预计达45亿美元，CAGR 32%",
      "source": "Gartner 2025报告",
      "source_level": "A",
      "used_in": "结论1, 结论4"
    },
    {
      "id": "EV002",
      "claim": "GitHub Copilot 占据 35% 市场份额",
      "source": "TechCrunch用户调研",
      "source_level": "B",
      "used_in": "结论2"
    },
    {
      "id": "EV003",
      "claim": "开发者在复杂架构设计场景下效果有限",
      "source": "Reddit讨论",
      "source_level": "C",
      "used_in": "结论3"
    },
    {
      "id": "EV004",
      "claim": "62%专业开发者使用AI编程工具",
      "source": "Stack Overflow Survey",
      "source_level": "A",
      "used_in": "结论5"
    }
  ],
  "confidence": 0.72,
  "assumptions": [
    "当前32%的CAGR在未来两年内保持相对稳定",
    "Gartner的预测模型已充分考虑市场波动因素",
    "Stack Overflow Survey的样本具有行业代表性"
  ],
  "next_step": "建议进行更细分的垂直市场分析（如企业级 vs 个人开发者），并验证Reddit反馈在更大样本中的普适性"
}
```

Expected fields:
- `task_id` (string)
- `status` (string)
- `conclusion[]` (array, each entry must have: `statement`, `type` in [Fact, Analysis, Inference, Assumption], `basis`, `confidence`)
- `evidence[]` (array of referenced evidence with cross-references)
- `confidence` (float, overall confidence 0.0-1.0)
- `assumptions[]` (array of explicit assumptions)
- `next_step` (string, recommendation for follow-up)

## raw_output_requirements

1. Must show the classification reasoning for each conclusion (why Fact vs. Analysis vs. Inference vs. Assumption).
2. Must explain how evidence was cross-referenced and weighted.
3. Must highlight areas of uncertainty and their impact on overall confidence.
4. Must include the structured_output JSON block.
5. The next_step should be actionable and specific.

## hard_fail_conditions

1. 把假设写成确定事实：任何 type 为 "Assumption" 的条目被当作确定事实陈述（confidence=1.0 且没有 uncertainty 标注）。
2. 没有uncertainty标注：所有结论的 confidence 均为 1.0，没有任何 uncertainty 或 caveat。
3. analysis无依据：结论条目没有 basis 字段，或 basis 与 evidence 无对应关系。

## acceptance_criteria

- [ ] `task_id` 非空
- [ ] `status` 为 completed、in_progress 或 failed 之一
- [ ] `conclusion[]` 至少包含3条结论
- [ ] 每条结论都有 `statement`, `type`, `basis`, `confidence`
- [ ] conclusion 中的 `type` 取值在 [Fact, Analysis, Inference, Assumption] 中
- [ ] 至少有一条 conclusion 的 type 为 "Assumption"
- [ ] 至少有一条 conclusion 的 confidence < 1.0
- [ ] `evidence[]` 存在且与 conclusion 有交叉引用
- [ ] `confidence` (overall) 为 0.0-1.0 的浮点数
- [ ] `assumptions[]` 非空
- [ ] `next_step` 非空且具体

## technical_assumptions

- 输入 evidence 可能包含冲突信息，analyst 应标注冲突而非掩盖
- confidence 计算应采用加权平均法，A级来源权重 > B级 > C级
- Assumption 类型的结论必须有 uncertainty 字段

## failure_fallback

If the analyst agent fails:
1. Return `status: "failed"` with empty conclusion array.
2. Record `failure_reason` in the output.
3. Writer agent should receive raw evidence instead of structured analysis.
4. Log error code `E003_ANALYSIS_FAIL` to errors.jsonl.
