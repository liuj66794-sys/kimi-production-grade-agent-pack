---
name: memory-review
description: >
  审查memory-candidate的质量和准确性，决定是否批准进入memory-index。
  触发条件：有新的memory-candidate提交审查时。
type: skill
---

# Memory Review Skill

## 触发条件
- 新的 `memory-candidate-{candidate_id}.json` 文件出现在 `memory/candidates/` 目录
- 手动发起审查请求

## 输入
- `memory-candidate-{candidate_id}.json`
- 现有 `memory/entries/` 目录下的所有已批准条目（用于冲突检测）

## 输出
- `memory-review-{review_id}.json`
- 存储位置：`memory/reviews/`

## 审查流程

### Step 1: Schema合规性检查
- 验证candidate是否符合 `schemas/memory-candidate.schema.json`
- 检查所有required字段是否存在且非空
- 检查confidence和risk是否为有效枚举值

### Step 2: Source可靠性检查
- source字段是否具体、可追溯？
- 引用的文件路径是否真实存在？
- 是否为直接经验（一手）而非传闻（二手）？

### Step 3: Content质量检查
- 内容是否具体、可操作？
- 是否避免了空泛描述？
- content_type分类是否准确？

### Step 4: Confidence合理性评估
- confidence评级是否与证据强度匹配？
- high confidence是否有多次验证支撑？
- 是否存在over-confidence？

### Step 5: Risk完整性评估
- risk等级是否反映了真实误用后果？
- high/critical risk是否提供了误用场景？
- 是否遗漏了重要的风险维度？

### Step 6: 冲突检测
- 是否与现有memory-entry存在内容矛盾？
- 是否是已有记忆的冗余重复？
- 是否可以与已有记忆merge？

### Step 7: 综合判定
基于以上6个步骤的结果，给出最终status：

| Status | 条件 |
|--------|------|
| approve | 全部维度通过，无冲突或冲突已解决 |
| reject | 任一关键维度（source可靠性、risk评估）不通过，或存在不可调和冲突 |
| request_changes | 部分维度不达标但可以修正，需修改后重新提交 |

## 判定规则

### 自动approve条件（需同时满足）
- Schema合规 ✓
- Source具体且可追溯 ✓
- Content质量合格 ✓
- Confidence合理 ✓
- Risk评估完整 ✓
- 无冲突或冲突已解决 ✓

### 自动reject条件（满足任一）
- Source为空或无法追溯
- Content为空或质量极低
- 与现有approved entry存在不可调和矛盾
- Risk为critical但未提供误用场景说明

### request_changes条件（满足任一）
- Source需要补充更具体的信息
- Confidence评级需要调整
- Risk评估需要完善
- 与现有entry可能存在冲突，需要说明关系

## 审查维度评分

每个审查维度评分1-5：
- 5: 优秀，无可挑剔
- 4: 良好， minor issues
- 3: 合格，需要关注
- 2: 不合格，需要修改
- 1: 严重不合格

总分 = Σ(dimension_score × weight)
- 4.0-5.0: 强烈推荐approve
- 3.0-3.9: 可approve但建议改进
- 2.0-2.9: request_changes
- 1.0-1.9: reject
