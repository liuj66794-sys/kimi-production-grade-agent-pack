# unit-smoke-001-task-intake

## test_title
Task Intake — Natural Language to Structured Task Order

## test_objective
Verify that the task-intake agent can transform a natural language requirement into a structured task order (task ticket). The output must preserve the original intent, extract actionable goals, identify deliverables, surface constraints, and flag resource needs — all without rewriting the request as a report or exposing internal module names.

## min_input
帮我研究 Kimi Code CLI 是否适合个人开发者构建 Agent Pack。

## expected_structured_output

```json
{
  "goal": "研究 Kimi Code CLI 对个人开发者构建 Agent Pack 的适用性",
  "deliverables": [
    "对比分析文档（功能、成本、学习曲线）",
    "可行性结论（推荐 / 有条件推荐 / 不推荐）",
    "PoC 代码片段（如适用）"
  ],
  "input_materials": [
    "Kimi Code CLI 官方文档链接",
    "个人开发者使用场景描述"
  ],
  "constraints": [
    "需考虑个人开发者的预算限制",
    "需评估学习曲线是否在可接受范围"
  ],
  "need_web": true,
  "need_code": true,
  "need_file_write": false,
  "need_subagents": false,
  "risk_assumptions": [
    "假设 Kimi Code CLI 已有公开文档",
    "假设 Agent Pack 构建流程有明确文档",
    "假设个人开发者具备基础 Python 能力"
  ],
  "minimal_plan": [
    "检索 Kimi Code CLI 官方文档与社区评测",
    "对比同类工具（如 Cursor、Windsurf、Claude Code）",
    "评估个人开发者场景下的功能覆盖度与成本",
    "输出可行性分析报告"
  ]
}
```

Expected fields (evaluator checks for existence):
- `goal` (string, non-empty)
- `deliverables` (array, at least 1 item)
- `input_materials` (array, exists)
- `constraints` (array, exists)
- `need_web` (boolean)
- `need_code` (boolean)
- `need_file_write` (boolean)
- `need_subagents` (boolean)
- `risk_assumptions` (array)
- `minimal_plan` (array, at least 3 steps)

## raw_output_requirements

The `raw_output` section must contain:
1. A brief reasoning paragraph explaining how the requirement was interpreted.
2. Confirmation that the task was decomposed, not rewritten as a report.
3. No internal module names (e.g., "task_intake_v2", "router_agent").
4. The structured_output JSON block embedded correctly.

## hard_fail_conditions

1. 没有明确goal：输出中没有定义清晰的goal字段，或goal为空字符串。
2. 没有deliverables：deliverables数组为空或缺失。
3. 把需求改写成报告而非任务单：输出是一份完整的调研报告，而非结构化的任务单。
4. 暴露内部模块名：raw_output中出现了如 task_intake_v2、router_agent、delegator 等内部模块名。

## acceptance_criteria

- [ ] `goal` 字段非空且语义完整
- [ ] `deliverables` 包含至少一项可验证的交付物
- [ ] `input_materials` 和 `constraints` 字段存在（可为空数组）
- [ ] 所有 `need_*` 布尔字段存在且类型正确
- [ ] `risk_assumptions` 为数组，列出了至少一项假设
- [ ] `minimal_plan` 包含至少3个可执行步骤
- [ ] raw_output 中不出现内部模块名
- [ ] 输出格式为任务单而非报告

## technical_assumptions

- 输入语言为中文，输出 structured_output 可为中文
- 任务单格式遵循 v1.1 规范
- 评估时不验证具体内容准确性，只验证字段存在性与格式合规性

## failure_fallback

If the task-intake agent fails to produce a valid structured_output:
1. Fall back to manual task decomposition using the template in `templates/task-intake-fallback.md`.
2. Log the failure reason to `errors.jsonl` with code `E001_TASK_INTAKE_FAIL`.
3. Use the last known good task schema as a starting point.
