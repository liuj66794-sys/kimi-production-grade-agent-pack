---
name: document-writer
description: 把可信结论写成结构化报告。不允许新增未经evidence-synthesis支撑的事实。
type: skill
---

# Document Writer Skill

## 目的
将经过evidence-synthesis验证的结构化结论转化为清晰、完整、可交付的报告文档。

## 触发条件
- evidence-synthesis完成并输出Claim-Evidence Map后
- swarm-orchestrator分配的报告撰写子任务
- 需要生成结构化书面交付物时
- quality-review前的文档草稿阶段

## 输入
- 来自evidence-synthesis的Claim-Evidence Map
- 来自task-intake的deliverables要求
- 报告模板（如指定）
- 目标读者和格式要求

## 输出
- 结构化报告文档（markdown格式为默认）
- 可选：其他格式（PDF、Word、HTML等通过转换）
- 文档元数据（摘要、关键词、版本）

## 工作流
1. **阅读输入材料**：
   - 仔细审阅Claim-Evidence Map
   - 理解目标读者和交付要求
   - 选择或确认报告模板（参考 report-template.md）
2. **规划文档结构**：
   - 按逻辑顺序组织章节
   - 确保每个章节有对应的证据支撑
3. **撰写内容**：
   - 仅使用evidence-synthesis已确认的事实和分析
   - 正确标注认知层次和不确定性
   - 保留完整的引用链
4. **格式化和排版**：
   - 应用模板格式
   - 生成目录、图表、附录
5. **自检**：
   - 检查是否有新增未经支撑的事实
   - 检查引用完整性
6. **输出交付**

## Hard Fail条件
1. 新增未经evidence-synthesis支撑的事实
2. 降低Claim的认知层次（Inference→Fact）
3. 删除或弱化evidence-synthesis标注的冲突信息
4. 未保留引用链导致结论不可追溯
5. 将不确定性声明改为确定性表述

## 不负责
- 不做新的研究（资料已由deep-research提供）
- 不做新的证据分析（分析已由evidence-synthesis完成）
- 不做质量审查（留给quality-review）

## 写作约束
- 每个核心论点必须能追溯到Claim-Evidence Map
- 不得添加"为增强说服力"的额外案例
- 不得使用与证据置信度不匹配的语言强度
- 必须包含"局限性"和"不确定性"章节

## 资源索引
- references/report-template.md — 报告模板规范
- references/boundaries.md — 边界定义与写作红线

---

# ── v1.2 升级规格 ───────────────────────────────────────────────────────

## v1.2 版本说明

版本: v1.2
更新日期: 2024-07
变更类型: 新增输入契约、引用路径检查、语义对齐标记、校验降级

## v1.2 新增：输入契约

document-writer 必须接收以下输入：

### 输入：evidence-synthesis的claim-evidence-map

```json
{
  "task_id": "evidence.001",
  "inputs": [
    "artifacts/integration-smoke-001/researcher-result.json",
    "artifacts/integration-smoke-001/analyst-result.json"
  ],
  "claims": [
    {
      "claim_id": "claim.001",
      "claim": "string",
      "claim_type": "fact | analysis | inference | assumption",
      "supporting_evidence": [...],
      "conflicting_evidence": [...],
      "confidence": "high | medium | low | indeterminate",
      "reasoning_path": "string",
      "assumption_prerequisites": [
        {
          "assumption_id": "A1",
          "description": "string",
          "risk_level": "high | medium | low",
          "alternative_if_false": "string"
        }
      ],
      "caveat": "string"
    }
  ],
  "unresolved_conflicts": [],
  "insufficient_evidence": []
}
```

**输入校验**：
- 在撰写报告前，writer必须确认evidence-map.json文件存在且可解析
- 如果evidence-map缺失或无法解析，writer必须标注blocker并停止
- writer只能使用evidence-map中已验证的claims，不得引入新的事实

### 输入读取责任

```
1. writer 只能读取 evidence-map.json 作为事实来源。
2. writer 不得读取 researcher-result.json 或 analyst-result.json 直接作为写作素材。
3. writer 的所有事实必须已通过 evidence-synthesis 的 claim-evidence-map 验证。
4. writer 可以读取 task-intake 的 deliverables 要求作为结构指导。
```

## v1.2 新增：引用路径检查

### 规则
每个事实陈述在报告中必须可追溯回claim-evidence-map。

### 引用路径检查要求

1. **Inline引用格式**：
   ```markdown
   正文内容 [claim.001, confidence: High]
   或
   正文内容 [Evidence-map: claim.001-claim.005]
   ```

2. **附录引用索引**：
   报告末尾必须包含附录B，列出每个章节引用的Claim ID：
   ```markdown
   ## 附录B: Claim-Evidence Map引用
   
   | 报告章节 | 引用的Claim ID | Claim类型 | Confidence |
   |---------|--------------|-----------|------------|
   | 核心判断1 | claim.001 | Fact | High |
   | 风险分析 | claim.005 | Inference | Low |
   ```

3. **文件路径引用**：
   报告头部必须包含evidence-map文件路径引用：
   ```markdown
   > Evidence-map引用: artifacts/integration-smoke-001/evidence-map.json
   ```

### 引用路径完整性校验清单

- [ ] 报告头部引用了evidence-map文件路径
- [ ] 每个核心判断都关联了claim_id
- [ ] 附录B包含完整的引用索引
- [ ] 没有claim_id引用自evidence-map之外的来源
- [ ] 所有引用的claim_id在evidence-map中真实存在

## v1.2 新增：语义对齐标记

### confidence < high 的事实标记为 requires_human_review

**规则**：
1. 对于confidence为 `medium`、`low` 或 `indeterminate` 的Claim，在报告中必须附加 `requires_human_review` 标记
2. 标记格式：
   ```markdown
   [requires_human_review] 该判断confidence为Medium，建议人工复核。
   Claim: [claim.XXX] — [判断内容]
   复核重点: [需要人工确认的具体方面]
   ```

3. 必须标记requires_human_review的场景：
   - Medium/Low confidence的Inference类Claim
   - 依赖High risk level Assumption的推理
   - unresolved conflicts涉及的Claim
   - insufficient_evidence列表中的Claim

### 语义对齐标记示例

```markdown
## 核心判断

### 判断1: 市场规模评估
**Claim Type**: Inference  
**Confidence**: Medium  
**Evidence-map**: [claim.003]

基于现有数据，预计2024年AI Agent市场规模将达到XX亿美元。

[requires_human_review]
- 该判断基于有限样本的推断（n=15家企业）
- 建议复核: 样本是否具有行业代表性
- 替代情景: 若大型企业未按计划采用，规模可能下调30%
```

## v1.2 新增：校验降级

### 自动检查不通过时降级为人工审查标记

**策略说明**：
v1.2不做语义级事实对齐的自动校验。eval_runner自动校验仅检查：
1. draft-report.md 是否存在
2. draft-report.md 是否包含 evidence-map 引用路径
3. draft-report.md 是否包含结论、依据、风险、不确定性
4. draft-report.md 是否在 QA 前生成
5. final-report.md 是否只在 QA 通过后生成

"不新增事实"的语义级判断由qa-reviewer负责，并标记为requires_human_review。

### 校验降级流程

```
Step 1: 自动校验（eval_runner执行）
  ├─ 检查文件存在性 ✓
  ├─ 检查evidence-map引用 ✓
  ├─ 检查必要章节 ✓
  └─ 检查生成顺序 ✓

Step 2: 语义级校验（qa-reviewer执行）
  ├─ 检查每个事实是否可映射到evidence-map
  ├─ 检查writer是否新增隐含事实
  ├─ 检查writer对evidence的解释是否准确
  └─ 检查confidence标注是否合理

Step 3: 降级标记
  ├─ 自动校验通过 + 语义校验通过 → pass
  ├─ 自动校验通过 + 语义校验有疑虑 → pass_with_notes + requires_human_review
  └─ 自动校验不通过 → fail
```

### 降级后的处理

当自动校验不通过时：
1. 不阻止draft-report.md的生成
2. 在quality-review.json中标注具体的不通过项
3. 如果涉及事实新增嫌疑，标记requires_human_review
4. QA reviewer决定是pass_with_notes还是fail

## v1.2 输出格式要求

### draft-report.md 输出要求

```markdown
# [标题]

> **核心约束声明**: 本报告所有事实均基于claim-evidence-map的已验证结论。
> Evidence-map引用: [evidence-map.json完整路径]

## [Part 2] 一句话结论
...[必须标注整体confidence]...

## [Part 3] 背景
...

## [Part 4] 核心判断
...[每条判断关联claim_id]...

## [Part 5] 依据
...

## [Part 6] 风险
...

## [Part 7] 不确定性
...[所有uncertainty声明完整保留]...

## [Part 8] 下一步建议
...

## [Part 9] Evidence-map引用
...[完整的引用索引附录]...
```

### 生成顺序约束

```
1. draft-report.md 必须在 QA 之前生成
2. final-report.md 只能在 QA 通过（pass 或 pass_with_notes）后生成
3. QA fail 时，只能生成 fix-required.md，禁止生成 final-report.md
```

## v1.2 Hard Fail 条件（补充）

在v1.0基础上新增：
6. 未在报告中引用evidence-map文件路径
7. 未为confidence < high的Claim附加requires_human_review标记
8. 在QA fail后仍生成final-report.md
9. 语义级校验发现问题但未在quality-review中标注

## v1.2 完整性自检清单

输出draft-report前检查：

- [ ] 每个事实陈述都能在evidence-map中找到对应claim
- [ ] 每个claim的引用路径完整（claim → evidence → source）
- [ ] 没有新增evidence-map中没有的事实
- [ ] Inference/Assumption未改写为Fact表述
- [ ] 冲突信息未被隐藏或弱化
- [ ] 不确定性声明完整保留
- [ ] 所有Assumption的风险等级已标注
- [ ] Evidence-map引用附录已包含
- [ ] 引用格式符合citation-policy.md规范
- [ ] confidence < high的Claim已附加requires_human_review标记
- [ ] draft-report.md在QA前生成
