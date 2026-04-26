---
name: quality-review
description: 多维度质量审查，输出pass/fail/pass_with_notes状态。覆盖完整性、准确性、可追溯性等9个维度。
type: skill
---

# Quality Review Skill

## 目的
在最终交付前执行系统性质量审查，确保输出符合标准，识别风险和缺陷。

## 触发条件
- swarm-orchestrator在最终交付前强制调用
- document-writer完成报告后
- 任何重要交付物输出前的 gates
- 用户显式要求质量审查时

## 输入
- 待审查的交付物
- 原始任务单（来自task-intake）
- 相关的中间产物（如Claim-Evidence Map）
- 审查维度要求

## 输出
- 审查状态：`pass` / `fail` / `pass_with_notes`
- 维度评分表（9个维度）
- 缺陷清单（如有）
- 改进建议（如有）
- 阻塞性问题列表（fail时必填）

## 审查维度（9个）

| # | 维度 | 检查内容 |
|---|------|---------|
| 1 | **完整性** | 是否覆盖任务单所有deliverables |
| 2 | **准确性** | 事实是否正确，引用是否准确 |
| 3 | **可追溯性** | 每个结论是否有来源支撑，引用链是否完整 |
| 4 | **一致性** | 内部逻辑是否一致，有无自相矛盾 |
| 5 | **区分度** | Fact/Analysis/Inference/Assumption是否正确区分 |
| 6 | **不确定性** | 不确定性是否诚实标注，置信度是否匹配 |
| 7 | **冲突处理** | 冲突信息是否被隐藏或淡化 |
| 8 | **格式合规** | 是否符合模板和格式要求 |
| 9 | **安全红线** | 是否触碰Hard Fail条件 |

## 工作流
1. **准备审查**：阅读任务单和交付物
2. **逐维度检查**（参考 review-checklist.md）：
   - 每个维度评分（pass / warn / fail）
   - 记录具体发现
3. **综合判定**：
   - 全部pass → `pass`
   - 有warn但无fail → `pass_with_notes`
   - 有fail → `fail`
4. **输出审查报告**
5. **如fail**：返回修改意见，触发修订流程

## 状态定义
- **pass**：通过审查，可交付
- **pass_with_notes**：通过但有需要注意的事项，交付时需附带说明
- **fail**：未通过审查，必须修正后才能交付

## Hard Fail条件
1. 事实性错误
2. 来源引用造假或不可追溯
3. 隐藏已知冲突信息
4. 新增未经支撑的结论
5. 泄露敏感信息或内部模块名

## 资源索引
- references/review-checklist.md — 逐维度检查清单
- references/boundaries.md — 审查边界与权限

---

# ── v1.2 升级规格 ───────────────────────────────────────────────────────

## v1.2 版本说明

版本: v1.2
更新日期: 2024-07
变更类型: 新增集成门禁、扩展审查范围、artifact-manifest校验、task-events校验

## v1.2 新增：集成门禁

### QA fail后不得进入eval-runner

**规则**：
1. qa-reviewer是进入eval-runner前的强制gate
2. 只有qa_status为 `pass` 或 `pass_with_notes` 时，才允许进入eval-runner
3. qa_status为 `fail` 时，必须阻止后续步骤，只能生成fix-required.md

### 集成门禁流程

```
document-writer 完成 draft-report.md
         ↓
   qa-reviewer 执行审查
         ↓
    ┌────┴────┐
    ↓         ↓         ↓
  pass   pass_with_notes  fail
    ↓         ↓         ↓
 final     final      fix-required.md
report    report      + 修改意见
  +notes    ↓
    ↓    eval-runner  ← 阻止进入
 eval-runner
```

### 门禁判定规则

```json
{
  "qa_status": "pass | pass_with_notes | fail",
  "final_report_allowed": true | false,
  "eval_runner_allowed": true | false,
  "hard_fail": false | true,
  "issues": [],
  "notes_required": true | false
}
```

| qa_status | final_report_allowed | eval_runner_allowed | notes_required |
|-----------|---------------------|--------------------|----------------|
| pass | true | true | false |
| pass_with_notes | true | true | true |
| fail | false | false | false |

## v1.2 新增：审查范围扩展

### 审查范围涵盖L1链路全部产物

v1.2的quality-review不仅审查draft-report.md，还需要检查：

1. **evidence-map.json**：
   - 是否所有claim都有claim_type标注
   - 是否所有assumption都有risk_level
   - 冲突是否在map中显式标注

2. **draft-report.md**：
   - 是否引用了evidence-map路径
   - 是否新增未经支撑的事实
   - 是否对confidence < high的claim附加requires_human_review

3. **artifact-manifest.json**：
   - required产物是否齐全
   - 产物路径是否正确

4. **task-events（间接校验）**：
   - 关键事件是否完整

### 审查范围清单

```markdown
## v1.2 审查范围

### 必审产物
- [ ] evidence-map.json（事实基础完整性）
- [ ] draft-report.md（报告质量）
- [ ] artifact-manifest.json（产物完整性）

### 间接校验
- [ ] task-events完整性（通过artifact-manifest推断）
- [ ] QA门禁执行状态

### 审查重点
| 优先级 | 审查对象 | 关键检查 |
|--------|---------|---------|
| P0 | draft-report.md | 无新增事实、引用完整、冲突未隐藏 |
| P0 | evidence-map.json | claim_type完整、assumption有风险等级 |
| P1 | artifact-manifest.json | required产物齐全 |
| P2 | task-events | 关键事件存在 |
```

## v1.2 新增：artifact-manifest校验

### 校验规则

qa-reviewer必须检查artifact-manifest.json：

1. **文件存在性**：artifact-manifest.json文件是否存在
2. **required产物检查**：所有`required: true`的artifact是否`exists: true`
3. **路径合法性**：artifact路径是否指向项目内路径（非外部路径）
4. **producer标注**：每个artifact是否有producer标注
5. **final-report.md生成顺序**：不在QA fail后生成

### artifact-manifest校验检查项

```markdown
- [ ] AM.1 artifact-manifest.json文件存在
- [ ] AM.2 所有required=true的artifact都有exists=true
- [ ] AM.3 没有artifact路径指向项目外部
- [ ] AM.4 每个artifact都有producer字段
- [ ] AM.5 final-report.md不在QA fail后生成
```

### 校验失败处理

| 失败项 | 处理策略 |
|--------|---------|
| AM.1 (manifest不存在) | fail，标记为hard_fail |
| AM.2 (required缺失) | fail，列出缺失产物 |
| AM.3 (路径外部) | fail，安全红线 |
| AM.4 (producer缺失) | warn，不影响总体判定 |
| AM.5 (final在fail后) | fail，安全红线 |

## v1.2 新增：task-events完整性校验

### 校验规则

qa-reviewer间接校验task-events的完整性（通过检查相关产物和runner输出）：

1. **关键事件存在性**：以下事件类型至少出现一次
   - `task_created`
   - `subtask_done`（每个子任务）
   - `quality_review_started`
   - `quality_review_done`
   - `task_completed` 或 `task_failed`

2. **事件一致性**：
   - `task_completed`和`task_failed`不同时存在
   - `quality_review_started`在`quality_review_done`之前

3. **产物-事件对应**：
   - artifact-manifest中的产物有对应的`artifact_created`事件

### task-events校验检查项

```markdown
- [ ] TE.1 task-events JSONL文件存在
- [ ] TE.2 包含task_created事件
- [ ] TE.3 包含所有subtask的subtask_done事件
- [ ] TE.4 包含quality_review_started事件
- [ ] TE.5 包含quality_review_done事件
- [ ] TE.6 包含task_completed或task_failed（不同时）
- [ ] TE.7 事件时序合理
```

### 校验方法

由于qa-reviewer不直接读取task-events文件（由integration_smoke_runner统一管理），
v1.2通过以下方式间接校验：

1. 检查integration_smoke_runner的输出中是否提及task-events写入成功
2. 检查artifact-manifest中是否包含task-events相关产物
3. 在quality-review.json中标注task-events校验状态

## v1.2 输出格式更新

### quality-review.json 输出格式

```json
{
  "status": "pass | pass_with_notes | fail",
  "hard_fail": false | true,
  "issues": [
    {
      "dimension": "1|2|3|...|9",
      "severity": "critical | major | minor",
      "description": "string",
      "fix_suggestion": "string"
    }
  ],
  "required_fixes": [
    {
      "description": "string",
      "blocking": true | false
    }
  ],
  "risk_level": "low | medium | high",
  "pass_condition": "string",
  "requires_human_review": [
    {
      "claim_id": "claim.XXX",
      "reason": "string"
    }
  ],
  "v1_2_checks": {
    "integration_gate": {
      "eval_runner_allowed": true | false,
      "reason": "string"
    },
    "artifact_manifest_check": {
      "status": "pass | fail | skipped",
      "missing_required": ["string"],
      "notes": "string"
    },
    "task_events_check": {
      "status": "pass | fail | skipped",
      "missing_events": ["string"],
      "notes": "string"
    }
  }
}
```

### 审查报告模板

```markdown
# Quality Review Report v1.2

## 审查对象: [交付物名称]
## 审查日期: [YYYY-MM-DD]
## 审查范围: [L1链路全部产物 / 指定产物]

## 维度评分（9个维度）
| 维度 | 状态 | 检查项通过 | 备注 |
|------|------|-----------|------|
| 1.事实来源可靠性 | pass/warn/fail | X/8 | ... |
| 2.逻辑推理严谨性 | pass/warn/fail | X/8 | ... |
| 3.不确定性说明完整性 | pass/warn/fail | X/8 | ... |
| 4.格式统一性 | pass/warn/fail | X/8 | ... |
| 5.代码测试验证 | pass/warn/fail | X/8 | ... |
| 6.表格可追溯性 | pass/warn/fail | X/8 | ... |
| 7.PPT页级观点 | pass/warn/fail | X/8 | ... |
| 8.文件命名清晰 | pass/warn/fail | X/6 | ... |
| 9.最终产物可用性 | pass/warn/fail | X/8 | ... |

## 综合判定: [pass / pass_with_notes / fail]

## v1.2 集成门禁判定
- QA状态: [pass / pass_with_notes / fail]
- 是否允许生成final-report.md: [是 / 否]
- 是否允许进入eval-runner: [是 / 否]

## v1.2 artifact-manifest校验
- 状态: [pass / fail / skipped]
- missing_required: [...]

## v1.2 task-events完整性校验
- 状态: [pass / fail / skipped]
- missing_events: [...]

## 缺陷清单（fail时必填）
- [ ] 缺陷1: [描述] → [修复建议]（关联维度: X）

## 改进建议（warn/pass_with_notes时）
- [ ] 建议1: [描述]（关联维度: X）

## 安全红线检查
- [ ] R1-R8 全部检查结果...

## 审查者: [qa-reviewer]
## 审查耗时: [N分钟]
```

## v1.2 Hard Fail 条件（补充）

在v1.0基础上新增：
6. QA fail后仍生成final-report.md（违反集成门禁）
7. artifact-manifest中required产物缺失
8. task-events关键事件严重缺失
9. evidence-map中assumption未标注risk_level

## v1.2 自检清单

执行quality-review前检查：

- [ ] 已阅读evidence-map.json
- [ ] 已阅读draft-report.md
- [ ] 已阅读artifact-manifest.json（如存在）
- [ ] 已确认task-events写入状态
- [ ] 9个维度全部检查完成
- [ ] 集成门禁判定已做出
- [ ] artifact-manifest校验已完成
- [ ] task-events完整性校验已完成
- [ ] 安全红线全部检查完成
- [ ] quality-review.json格式符合schema
