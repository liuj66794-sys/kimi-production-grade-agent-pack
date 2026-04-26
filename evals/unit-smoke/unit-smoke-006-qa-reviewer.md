# unit-smoke-006-qa-reviewer

## test_title
QA Reviewer — Quality Review with Dimension Scoring

## test_objective
Verify that the qa-reviewer agent can complete a quality review of a writer-generated report, providing dimension-level scores, identifying hard fails, and delivering an overall verdict. The review must be evidence-based and each dimension score must include explanatory notes.

## min_input
Writer 生成的报告（摘要）：

```markdown
# AI编程助手市场分析报告（2025）

## 执行摘要
全球AI编程助手市场2025年预计达45亿美元，62%的专业开发者已日常使用AI编程工具。

## 市场规模与增长
根据Gartner 2025报告，市场规模为45亿美元，CAGR 32%。若此增长率持续，2026年可达65亿美元。

## 竞争格局
GitHub Copilot 占据约35%的市场份额，基于TechCrunch用户调研数据。

## 用户采纳与使用场景
62%的专业开发者使用AI编程工具（Stack Overflow Survey）。
开发者反馈AI助手在复杂架构设计场景下效果有限（Reddit讨论）。

## 建议与展望
关注企业级市场的差异化需求，投资复杂架构场景的AI能力。
```

原始 claim-evidence map（用于对比审查）：

```json
{
  "claims": [
    {"id": "C001", "claim": "2025年市场45亿美元", "evidence": ["EV001"], "confidence": 0.90},
    {"id": "C002", "claim": "Copilot占35%份额", "evidence": ["EV002"], "confidence": 0.65},
    {"id": "C003", "claim": "复杂架构场景效果有限", "evidence": ["EV003"], "confidence": 0.55},
    {"id": "C004", "claim": "62%开发者使用AI工具", "evidence": ["EV004"], "confidence": 0.85}
  ]
}
```

任务：对以上报告进行质量审查，从以下维度评分并输出审查结论。

## expected_structured_output

```json
{
  "task_id": "qa-review-market-report",
  "status": "pass_with_notes",
  "dimensions": [
    {
      "name": "事实准确性",
      "score": 90,
      "max_score": 100,
      "notes": "报告中的数据性陈述与输入 evidence 一致。45亿美元（Gartner）和62%使用率（Stack Overflow）引用正确。Copilot 35%份额标注了来源（TechCrunch），符合其0.65的置信度。"
    },
    {
      "name": "来源引用完整性",
      "score": 75,
      "max_score": 100,
      "notes": "主要数据点均标注了来源。建议：为'复杂架构设计场景效果有限'这一推断性结论添加更多限定词，因其来源为C级（Reddit讨论，confidence=0.55）。"
    },
    {
      "name": "报告结构完整性",
      "score": 85,
      "max_score": 100,
      "notes": "报告包含执行摘要、市场规模、竞争格局、用户采纳和建议五个部分，结构完整。缺少独立的'风险与不确定性'部分，建议补充。"
    },
    {
      "name": "分析深度",
      "score": 70,
      "max_score": 100,
      "notes": "报告进行了数据呈现和简单对比，但缺乏对竞争格局的深入分析（如进入壁垒、差异化策略）。建议部分较为笼统，可更具体。"
    },
    {
      "name": "证据忠实度",
      "score": 95,
      "max_score": 100,
      "notes": "未发现报告引入输入中不存在的新 claim。所有陈述均可追溯到原始 evidence。低置信度结论（C003, C005）的呈现方式与其置信度相符。"
    },
    {
      "name": "可读性",
      "score": 88,
      "max_score": 100,
      "notes": "报告语言简洁、结构清晰、适合目标读者。Markdown 格式规范。"
    }
  ],
  "hard_fails": [
    {
      "rule_id": "HF001",
      "triggered": false,
      "details": "未发现无来源的确定事实"
    },
    {
      "rule_id": "HF002",
      "triggered": false,
      "details": "核心交付物（报告）存在"
    },
    {
      "rule_id": "HF005",
      "triggered": false,
      "details": "输出为Markdown报告而非PPT"
    }
  ],
  "overall_notes": "报告整体质量良好（平均分约84分），事实准确且来源引用完整。主要改进空间：1）为低置信度结论添加限定词；2）补充风险与不确定性部分；3）深化竞争分析和建议的具体性。建议 status: pass_with_notes。"
}
```

Expected fields:
- `task_id` (string)
- `status` (string: "pass" | "fail" | "pass_with_notes")
- `dimensions[]` (array, each with: `name`, `score`, `max_score`, `notes`)
- `hard_fails[]` (array, each with: `rule_id`, `triggered`, `details`)
- `overall_notes` (string, comprehensive summary)

## raw_output_requirements

1. Must show the review methodology (what was checked and how).
2. Must provide specific, actionable feedback for each dimension.
3. Must reference specific evidence IDs when making claims about accuracy.
4. Must include the structured_output JSON block.
5. The overall_notes should justify the final status decision.

## hard_fail_conditions

1. 没有审查维度评分：dimensions 数组为空或缺失。
2. 有hard_fail但未标记：实际触发了 hard-fail 规则（如 HF001-HF008），但 hard_fails 中对应条目的 triggered 为 false。
3. 无overall结论：overall_notes 为空或缺失，无法判断最终审查结论。

## acceptance_criteria

- [ ] `task_id` 非空
- [ ] `status` 为 pass、fail 或 pass_with_notes 之一
- [ ] `dimensions[]` 至少包含4个审查维度
- [ ] 每个 dimension 都有 `name`, `score`, `max_score`, `notes`
- [ ] 每个 `score` 为 0-100 的整数
- [ ] `hard_fails[]` 非空，至少检查了3条 hard-fail 规则
- [ ] 每个 hard_fail 条目都有 `rule_id`, `triggered`, `details`
- [ ] `overall_notes` 非空，包含对报告的总结评价和 status 决策依据
- [ ] 评分与 notes 中的说明一致

## technical_assumptions

- 审查标准基于 v1.1 QA Reviewer 规范
- score 为整数，范围 0-100
- status 决策逻辑：所有维度 score >= 80 且 hard_fails 全为 false → "pass"；任一 hard_fail 为 true → "fail"；其他情况 → "pass_with_notes"
- dimensions 应至少覆盖：事实准确性、来源引用、结构完整性、分析深度、证据忠实度、可读性

## failure_fallback

If the qa-reviewer agent fails:
1. Return `status: "fail"` with minimal dimensions array.
2. Record `failure_reason` explaining why review could not be completed.
3. Fall back to a basic checklist review using the template in `templates/qa-checklist.md`.
4. Log error code `E006_QA_REVIEW_FAIL` to errors.jsonl.
