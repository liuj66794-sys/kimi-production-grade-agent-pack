# Claim-Evidence Map 格式规范 v1.2

## 1. 地图结构模板

```markdown
# Claim-Evidence Map: [主题]

## Claim 1: [声明文本]
- **认知层次**: [Fact / Analysis / Inference / Assumption]
- **置信度**: [High / Medium / Low / Indeterminate]
- **冲突解决状态**: [resolved / unresolved / under_review]

### 支撑Evidence
| 证据ID | 来源编号 | 证据摘要 | 直接/间接 | 质量 |
|--------|---------|---------|----------|------|
| E1 | S3 | ... | 直接 | A |
| E2 | S5 | ... | 间接 | B |

### 冲突Evidence（如有）
| 证据ID | 来源编号 | 冲突描述 | 解决策略 | 解决结果 |
|--------|---------|---------|---------|---------|
| E3 | S7 | ... | [来源质量矩阵优先级] | [保留/排除/标注] |

### 推理路径（Inference必填）
```
前提1 (Fact) → 前提2 (Analysis) → Claim 1 (Inference)
```

### 假设前提（Assumption必填）
- **假设A**: [描述]；若假设不成立，则Claim变为[替代状态]
- **风险等级**: [high / medium / low]
- **关联风险**: [风险描述]

---

## Claim 2: [声明文本]
...
```

## 2. 四种认知层次定义与标注规则

### 2.1 Fact（事实）

| 属性 | 定义 |
|------|------|
| **定义** | 有来源直接支撑的事实陈述，可直接验证的客观数据 |
| **判断标准** | 有原始数据/原文/官方记录/直接观测支撑 |
| **证据要求** | 至少1个A级来源或2个B级来源直接支撑 |
| **标注规则** | 必须标注来源编号和具体位置（段落/页码） |
| **示例** | "2024年Q1 GDP为29.63万亿元"（来源：国家统计局[S1:表1]） |

**Fact标注格式**:
```
[Fact] 2024年Q1 GDP为29.63万亿元
来源: S1:表1 (国家统计局, 官方数据, 质量A)
验证状态: ✓ 可直接验证
```

### 2.2 Analysis（分析）

| 属性 | 定义 |
|------|------|
| **定义** | 基于事实的合理推断，对事实的处理、比较、归类 |
| **判断标准** | 基于Fact但未引入新因果关系 |
| **证据要求** | 至少2个来源支撑，必须列出依赖的所有Facts |
| **标注规则** | 必须标注依赖的Fact ID列表 |
| **示例** | "GDP同比增长5.3%，增速高于预期0.1个百分点" |

**Analysis标注格式**:
```
[Analysis] GDP同比增长5.3%，增速高于预期0.1个百分点
依赖Facts: [F1: 2024Q1 GDP=29.63万亿], [F2: 2023Q1 GDP=28.12万亿], [F3: 预期增速5.2%]
来源: S1:表1, S2:摘要 (计算得出)
推理类型: 同比计算 + 与预期比较
```

### 2.3 Inference（推论）

| 属性 | 定义 |
|------|------|
| **定义** | 进一步推导得出的结论，包含因果、预测、判断 |
| **判断标准** | 从Fact/Analysis出发引入新因果或预测 |
| **证据要求** | 至少3个来源，必须展示完整推理路径 |
| **标注规则** | 必须标注confidence level和推理路径 |
| **示例** | "预计下半年消费将继续复苏" |

**Inference标注格式**:
```
[Inference] 预计下半年消费将继续复苏
Confidence: Medium (60-75%)
推理路径: F4(社零增长4.7%) → A2(消费信心指数回升) → I1(消费继续复苏)
前提假设: 政策环境保持稳定 (Assumption A1, 风险等级: low)
反方证据: E5 (出口下滑可能拖累消费)
若假设不成立: 改为"消费复苏存在不确定性"
```

### 2.4 Assumption（假设）

| 属性 | 定义 |
|------|------|
| **定义** | 无直接支撑但任务必需的假设前提 |
| **判断标准** | 为推理所依赖但无直接证据验证 |
| **证据要求** | 无直接证据要求，但必须显式声明 |
| **标注规则** | 必须显式声明 + 关联风险等级 + 说明若不成立的替代状态 |
| **示例** | "假设美联储2024年不降息" |

**Assumption标注格式**:
```
[Assumption] 假设美联储2024年不降息
风险等级: HIGH
声明理由: 当前市场主流预期，但存在分歧
若不成立: 资本外流压力可能增大，Inference I2 的confidence降为Low
替代情景: 若9月启动降息周期，则...
来源说明: 无直接来源，基于CME FedWatch工具的市场预期 (间接参考)
```

**v1.2强制规则**: 所有Assumption必须关联风险等级 (high/medium/low)

## 3. 认知层次判断决策树

```
是否有来源直接支撑？
├─ 否 → 是否为推理所必需的前提？
│   ├─ 是 → Assumption
│   └─ 否 → 删除或标记为Indeterminate
└─ 是 → 是否引入新因果/预测？
    ├─ 是 → 是否基于已验证的Fact/Analysis？
    │   ├─ 是 → Inference
    │   └─ 否 → 降级为Analysis或添加Assumption
    └─ 否 → 是否进行比较/归类/计算？
        ├─ 是 → Analysis
        └─ 否 → Fact
```

## 4. 冲突处理流程（按来源质量矩阵）

### 4.1 来源质量矩阵

| 等级 | 来源类型 | 示例 | 权重 |
|------|---------|------|------|
| A | 官方/权威 | 政府统计局、央行、国际组织官方数据 | 4 |
| B | 学术/研究 | 顶级期刊论文、知名研究机构报告 | 3 |
| C | 行业报告 | 投行研报、咨询公司报告 | 2 |
| D | 主流媒体 | Reuters、Bloomberg、知名财经媒体 | 1 |
| E | 一般媒体/个人 | 自媒体、博客、社交媒体 | 0.5 |
| F | 间接引用 | 无法追溯到原始来源的二手信息 | 0.25 |

### 4.2 冲突检测规则

当以下情况出现时，标记为冲突：
1. 两个或多个来源对同一Claim给出矛盾的支撑/反对结论
2. 同一来源内部存在自相矛盾的数据
3. 时间序列数据出现无法解释的断裂
4. 定量数据差异超过5%或定性判断完全相反

### 4.3 冲突解决优先级（按来源质量矩阵）

```
Step 1: 计算冲突双方的质量总分
  A级来源 x4 → B级 x3 → C级 x2 → D级 x1 → E级 x0.5 → F级 x0.25

Step 2: 质量差距 >= 2个等级
  → 采纳高质量来源，低质量来源标注为"已排除但有记录"

Step 3: 质量差距 < 2个等级
  → 保留冲突，要求writer在报告中明确说明

Step 4: 同等级冲突
  → 优先采纳更新来源
  → 若时间相同，保留冲突并标注unresolved
```

### 4.4 冲突处理策略表

| 场景 | 处理策略 | Map标注 |
|------|---------|---------|
| 高质量 vs 低质量，差距>=2级 | 采纳高质量 | `resolved: favor_high_quality` |
| 同等级，时间不同 | 采纳更新的 | `resolved: favor_recent` |
| 同等级，时间相同 | 保留冲突 | `unresolved: requires_human_review` |
| 间接证据 vs 直接证据 | 采纳直接证据 | `resolved: favor_direct` |
| 官方数据 vs 市场估计 | 采纳官方数据 | `resolved: favor_official` |
| 任何Inference声称推翻Fact | 拒绝，Fact优先 | `resolved: fact_over_inference` |

### 4.5 冲突处理在Map中的显式标注（v1.2新增）

每条冲突必须在Map中显式标注：
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

## 5. 不确定性语言规范

### 5.1 置信度标注要求

| 置信度 | 适用场景 | 标注位置 |
|--------|---------|---------|
| **High** | 多源强一致，直接证据充分 | Claim头部 + Evidence表格 |
| **Medium** | 证据一致但有限，或间接证据 | Claim头部 + 需附说明 |
| **Low** | 单一来源、间接证据、或存在冲突 | Claim头部 + 必须说明原因 |
| **Indeterminate** | 证据不足或矛盾无法判断 | Claim头部 + 必须声明信息缺口 |

### 5.2 置信度与认知层次的交叉约束

|  | High | Medium | Low | Indeterminate |
|--|------|--------|-----|---------------|
| Fact | ✓ 允许 | ✓ 允许 | △ 需说明 | ✗ 不应出现 |
| Analysis | ✓ 允许 | ✓ 允许 | ✓ 允许 | △ 尽量避免 |
| Inference | △ 需强证据链 | ✓ 允许 | ✓ 允许 | ✗ 不应出现 |
| Assumption | ✗ 不应出现 | ✗ 不应出现 | ✗ 不应出现 | ✓ 允许（声明即可） |

### 5.3 不确定性声明模板

```
对于Low/Indeterminate的Claim，必须附加：

**不确定性说明**:
- 信息缺口: [具体描述缺少什么信息]
- 当前最佳判断: [在现有信息下的最佳结论]
- 影响范围: [如果这个判断错误，会影响哪些其他Claim]
- 建议补充: [需要什么样的证据可以提高置信度]
```

## 6. JSON输出格式（claim-evidence-map.json）

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
      "reasoning_path": "前提1 → 前提2 → 结论 (仅inference)",
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

## 7. 完整性校验清单

在输出claim-evidence-map前，必须检查：

- [ ] 每个Claim都有claim_type标注（4选1）
- [ ] 每个Analysis都列出了依赖的Fact ID
- [ ] 每个Inference都有推理路径和confidence level
- [ ] 每个Assumption都有风险等级和替代状态说明
- [ ] 每个冲突都在Map中有显式标注（v1.2新增）
- [ ] 所有Assumption都关联了风险等级（v1.2新增）
- [ ] 每个Fact都有至少1个支撑Evidence
- [ ] 引用链可追溯到原始来源
- [ ] 冲突未隐藏，已解决的有处理说明，未解决的有标注
