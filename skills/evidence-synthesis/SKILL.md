---
name: evidence-synthesis
description: 将分散资料转化为可审查的Claim-Evidence Map。必须区分Fact/Analysis/Inference/Assumption。禁止隐藏冲突信息。
type: skill
---

# Evidence Synthesis Skill

## 目的
将deep-research收集的分散资料转化为结构化、可审查的证据地图，区分不同认知层次，诚实呈现不确定性。

## 触发条件
- deep-research输出结构化结果后
- 需要整合多源证据形成可审查的结论基础
- swarm-orchestrator分配的证据整合子任务
- 检测到多源信息需要结构化分析时

## 输入
- 来自deep-research的结构化来源清单和证据摘要
- 原始研究问题
- 信息缺口清单

## 输出
- Claim-Evidence Map（结构化）
- 认知层次标注（Fact/Analysis/Inference/Assumption）
- 冲突矩阵
- 不确定性声明
- 证据充分度评估

## 工作流
1. **提取核心Claims**：从资料中识别所有关键声明
2. **映射Evidence**：为每个Claim关联支撑证据
3. **认知层次分类**（必须区分）：
   - **Fact**：可直接验证的数据、日期、数值、原文引用
   - **Analysis**：对事实的解释、比较、归类
   - **Inference**：基于证据的推论、预测、因果判断
   - **Assumption**：为推理所依赖但尚未验证的前提
4. **冲突识别**：标记证据间的矛盾和不一致，禁止隐藏
5. **不确定性量化**：对每个Claim标注置信度（高/中/低/不可判定）
6. **证据充分度评估**：判断证据是否足以支撑结论
7. **输出结构化地图**（参考 claim-evidence-map.md）

## Hard Fail条件
1. 未区分Fact/Analysis/Inference/Assumption
2. 隐藏或淡化冲突信息
3. 把单一来源包装成确定结论
4. 未标注不确定性即给出推论
5. 未保留可追溯到原始来源的引用链

## 不负责
- 不做新的搜索（搜索已完成）
- 不写最终报告（留给document-writer）
- 不做超出证据范围的推测

## 输出契约
- 每个Claim必须关联至少一个Evidence
- 每个Evidence必须标注来源编号
- 每个Inference必须列出推理路径
- 每个Assumption必须声明替代可能性

## 资源索引
- references/claim-evidence-map.md — Claim-Evidence Map格式规范
- references/citation-policy.md — 引用策略与格式
- references/uncertainty-language.md — 不确定性表达规范
- references/boundaries.md — 边界定义与证据充分度阈值

---

# ── v1.2 升级规格 ───────────────────────────────────────────────────────

## v1.2 版本说明

版本: v1.2
更新日期: 2024-07
变更类型: 新增输入/输出契约、冲突解决标注要求、Assumption风险等级

## v1.2 新增：输入契约

evidence-synthesis 必须明确接收以下输入格式：

### 输入1：researcher-result.json

```json
{
  "task_id": "research.001",
  "agent": "researcher",
  "status": "done | partial | blocked",
  "conclusion": [
    {
      "statement": "string",
      "source_ids": ["S1", "S2"],
      "confidence": "high | medium | low"
    }
  ],
  "evidence": [
    {
      "evidence_id": "E1",
      "source_id": "S1",
      "type": "quantitative | qualitative | mixed",
      "content": "string",
      "context_snapshot": {
        "url": "string",
        "accessed_at": "ISO-8601",
        "excerpt": "string"
      }
    }
  ],
  "context_snapshot": {
    "input_files": [],
    "search_queries": [],
    "tools_used": []
  },
  "blockers": [],
  "assumptions": [],
  "next_step": "string"
}
```

**输入责任**：researcher-result.json 是主要事实与来源输入。

### 输入2：analyst-result.json

```json
{
  "task_id": "analysis.001",
  "agent": "analyst",
  "status": "done | partial | blocked",
  "analysis_framework": "string",
  "conclusion": [
    {
      "statement": "string",
      "basis_evidence_ids": ["E1", "E2"],
      "claim_type": "analysis | inference | assumption",
      "confidence": "high | medium | low"
    }
  ],
  "evidence_or_basis": [],
  "risks": [
    {
      "risk_id": "R1",
      "description": "string",
      "likelihood": "high | medium | low",
      "impact": "high | medium | low"
    }
  ],
  "assumptions": [
    {
      "assumption_id": "A1",
      "description": "string",
      "basis": "string"
    }
  ],
  "confidence": "high | medium | low",
  "next_step": "string"
}
```

**输入责任**：analyst-result.json 是辅助分析输入，用于交叉验证和风险补充。

### 输入责任划分（v1.2强制）

```
1. researcher-result.json 是主要事实与来源输入。
2. analyst-result.json 是辅助分析输入，用于交叉验证和风险补充。
3. evidence-synthesis 不直接读取 writer 输出。
4. evidence-synthesis 不新增未被 researcher 或 analyst 支撑的事实。
```

## v1.2 新增：输出契约

evidence-synthesis 必须输出以下格式的 claim-evidence-map.json：

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
      "supporting_evidence": [
        {
          "evidence_id": "E1",
          "source_id": "S3",
          "evidence_summary": "string",
          "directness": "direct | indirect",
          "quality": "A | B | C | D | E | F"
        }
      ],
      "conflicting_evidence": [
        {
          "evidence_id": "E3",
          "source_id": "S7",
          "conflict_description": "string",
          "resolution": "resolved | unresolved",
          "resolution_strategy": "string",
          "resolution_notes": "string"
        }
      ],
      "confidence": "high | medium | low | indeterminate",
      "reasoning_path": "前提1 → 前提2 → 结论 (仅inference必填)",
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

**输出校验规则**：
- 每个 Claim 都有 `claim_type` 标注（4选1）
- 每个 Analysis 都列出了依赖的 Fact ID
- 每个 Inference 都有推理路径和 confidence level
- 每个 Assumption 都有风险等级和替代状态说明
- 冲突解决已在 Map 中显式标注
- 所有 Assumption 都关联了风险等级

## v1.2 新增：冲突解决必须在Map中显式标注

**规则**：
1. 任何检测到的冲突必须在 claim-evidence-map.json 的 `conflicting_evidence` 中记录
2. 已解决的冲突必须填写 `resolution: "resolved"` 和 `resolution_strategy`
3. 未解决的冲突必须填写 `resolution: "unresolved"` 和原因
4. 冲突解决必须在 Map 的可读版本（Markdown）中有可见标注

**冲突解决策略优先级**：
```
1. official > academic > industry_report > news_major > news_general > blog_personal > inference
2. 同等级时优先更新来源
3. 高质量来源冲突时保留冲突，并要求 writer 明确说明
4. inference 不得覆盖有来源证据
```

**冲突标注示例**：
```json
{
  "conflict_id": "conflict.001",
  "claim_a": "claim.003",
  "claim_b": "claim.007",
  "source_quality_a": "A",
  "source_quality_b": "C",
  "resolution_strategy": "favor_high_quality",
  "resolution": "a_favored",
  "resolution_notes": "A级官方数据优先于C级行业估计，差距>=2级",
  "map_annotation": {
    "visible_in_map": true,
    "annotation_text": "[已解决冲突] 采纳S1(A级)而非S5(C级)，理由：官方数据优先"
  }
}
```

## v1.2 新增：所有Assumption必须关联风险等级

**规则**：
1. 每个 Assumption 类型的 Claim 必须有 `risk_level` 字段
2. risk_level 取值: `high` / `medium` / `low`
3. risk_level 的判定标准：

| risk_level | 判定条件 |
|-----------|---------|
| **high** | 假设不成立将导致核心结论失效，或产生严重误导 |
| **medium** | 假设不成立将影响部分结论的可靠性 |
| **low** | 假设不成立仅影响边缘细节，不影响核心判断 |

4. 每个 Assumption 必须说明 `alternative_if_false`（假设不成立时的替代状态）

**Assumption标注完整示例**：
```json
{
  "claim_id": "claim.010",
  "claim": "假设美联储2024年不降息",
  "claim_type": "assumption",
  "confidence": "indeterminate",
  "assumption_prerequisites": [
    {
      "assumption_id": "A1",
      "description": "美联储在2024年维持当前利率水平不降息",
      "risk_level": "high",
      "alternative_if_false": "若9月启动降息，则资本外流压力增大，Inference I2 的confidence降为Low",
      "basis": "CME FedWatch市场预期（间接参考，非官方确认）"
    }
  ]
}
```

## v1.2 输出完整性校验清单

在输出 claim-evidence-map 前，必须检查：

- [ ] 每个 Claim 都有 `claim_type` 标注（fact/analysis/inference/assumption 四选一）
- [ ] 每个 Analysis 都列出了依赖的 Fact ID
- [ ] 每个 Inference 都有推理路径和 confidence level
- [ ] 每个 Assumption 都有 `risk_level`（high/medium/low）和 `alternative_if_false`
- [ ] 每个冲突都在 Map 中有显式标注（resolved/unresolved + 处理说明）
- [ ] 所有 Assumption 都关联了风险等级
- [ ] 每个 Fact 都有至少 1 个支撑 Evidence
- [ ] 引用链可追溯到原始来源
- [ ] 冲突未隐藏，已解决的有处理说明，未解决的有标注
- [ ] inputs 字段记录了输入文件路径
