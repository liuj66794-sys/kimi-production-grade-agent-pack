---
name: slide-review
description: >
  审查PPT演示文稿的质量，确保叙事连贯性、来源标注和风险披露。
  触发条件：slide-content.json生成后必须进行自审查，或由用户发起review请求。
type: skill
---

# Slide Review Skill

## 触发条件
- slide-content.json生成后自动触发自审查
- 用户主动要求审查slides
- 发现slides可能存在质量问题时

## 输入
- `slide-content.json`（待审查）
- `slide-outline.md`（叙事结构参考）
- `final-report.md`（内容来源基准）

## 输出
- `slide-review-{review_id}.json`
- 符合 `schemas/slide-review.schema.json`

## 审查维度

### 1. 叙事连贯性（Narrative Coherence）weight: 25%
- slides是否构成完整的故事线？
- 逻辑递进是否自然？
- 从背景到建议的流程是否清晰？
- 评分：1-5

### 2. 每页一观点（Single Point per Slide）weight: 20%
- 每页是否只有一个核心key message？
- 内容是否都围绕key message展开？
- 是否存在信息过载（单页内容过多）？
- 评分：1-5

### 3. 来源标注（Source Attribution）weight: 20%
- 每个事实性陈述是否标注了来源？
- 来源是否精确（非模糊引用）？
- 来源是否在final-report中存在？
- 评分：1-5

### 4. 风险披露（Risk Disclosure）weight: 20%
- 不确定结论是否使用了适当措辞？
- 是否遗漏了final-report中的风险提示？
- conditional结论是否表述为conditional？
- 评分：1-5

### 5. 视觉与信息设计（Visual Design）weight: 15%
- 信息密度是否合理？
- bullet points是否简洁？
- speaker notes是否有用？
- 评分：1-5

## Hard Fails 检查

必须逐一检查以下hard fail项目，任一触发则整体status为fail：

| Hard Fail | 检查方法 |
|-----------|----------|
| 内容脱离final-report | 逐条对比slide content与final-report |
| 没有来源 | 检查每个事实性statement的source字段 |
| 隐藏风险 | 检查risk/confidence相关措辞 |
| 不确定性写成确定事实 | 检查确定性词汇（"是"、"必然"、"一定"）的使用 |

## 评分标准

- 5: 优秀，无问题
- 4: 良好，minor issues
- 3: 合格，有改进空间
- 2: 不合格，需要修改
- 1: 严重不合格

### 加权总分计算
```
total = narrative × 0.25 + single_point × 0.20 + source × 0.20 + risk × 0.20 + visual × 0.15
```

### 状态判定
| total范围 | status | 说明 |
|-----------|--------|------|
| 4.0-5.0 | pass | 无需修改 |
| 3.0-3.9 | pass_with_notes | 通过但建议改进 |
| 2.0-2.9 | fail | 需修改后重新review |
| 1.0-1.9 | hard_fail | 严重不合格，必须重写 |

**注意**：只要存在任一hard fail，status自动为hard_fail，无视总分。

## Review输出示例

```json
{
  "review_id": "sr-20250115-001",
  "slide_deck_id": "slide-content-20250115",
  "status": "pass",
  "dimensions": [
    {
      "name": "narrative_coherence",
      "score": 5,
      "notes": "故事线清晰，从背景到建议的逻辑递进自然"
    },
    {
      "name": "single_point_per_slide",
      "score": 4,
      "notes": "大部分页面聚焦一个观点，slide-07内容略多"
    },
    {
      "name": "source_attribution",
      "score": 4,
      "notes": "来源标注完整，个别bullet可更精确"
    },
    {
      "name": "risk_disclosure",
      "score": 5,
      "notes": "风险提示充分，措辞恰当"
    },
    {
      "name": "visual_design",
      "score": 4,
      "notes": "信息密度合理，speaker notes详细"
    }
  ],
  "hard_fails": [],
  "weighted_score": 4.4,
  "reviewed_at": "2025-01-15T14:30:00Z"
}
```
