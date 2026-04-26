---
name: slide-generation
description: >
  将final-report或结构化结论转化为PPT演示文稿。
  触发条件：用户要求生成PPT或演示文稿时。
type: skill
---

# Slide Generation Skill

## 触发条件
- 用户明确要求"生成PPT"、"制作演示文稿"或"做slides"
- 用户要求将报告转化为演示格式
- 需要向干系人进行口头汇报时

## 输入
- `final-report.md` 或结构化结论文件
- 数据源引用记录
- 分析过程中的中间结论

## 输出
1. `slide-outline.md` — 叙事结构和每页key message
2. `slide-content.json` — 符合 `schemas/slide-content.schema.json`
3. `slide-review.json` — 自审查结果

## 处理流程

### Step 1: 理解final-report
- 通读final-report全文
- 标记核心结论、关键数据、风险提示
- 记录所有数据来源标注

### Step 2: 设计叙事结构 (slide-outline.md)

叙事必须遵循逻辑链：
```
背景(Context) → 问题(Problem) → 分析(Analysis) → 结论(Conclusion) → 建议(Recommendation)
```

每页slide的key message要求：
- 不超过20个中文字符或50个英文字符
- 使用陈述句，避免疑问句
- 表达一个且仅一个核心观点

### Step 3: 生成slide内容 (slide-content.json)

每页slide包含：
- **layout**: 页面布局类型（title/cover/content/two-column/comparison/data/chart/summary）
- **title**: 页面标题
- **content**: 内容元素数组，每个元素含type/text/source/confidence
- **speaker_notes**: 讲解要点

### Step 4: 自审查 (slide-review.json)
根据 `skills/slide-review/SKILL.md` 的审查维度进行自审查。

## Hard Fails（零容忍）

以下任一情况将导致slide不合格：

### 1. slide内容脱离final-report
slide中的任何内容必须在final-report中有明确依据。禁止：
- 添加final-report中没有的结论
- 放大或缩小final-report中的发现
- 引入与final-report矛盾的信息

### 2. slide没有来源
每个事实性陈述必须标注数据来源。禁止：
- 未标注来源的数据
- 模糊来源（如"据研究"、"有数据显示"）

### 3. slide隐藏风险
必须如实反映分析中的不确定性和风险。禁止：
- 将conditional结论表述为确定结论
- 省略final-report中的风险提示

### 4. 把不确定性写成确定事实
禁止：
- 使用"是"、"必然"、"一定"描述推断性结论
- 应使用"数据表明"、"分析显示"、"可能存在"等措辞

## 质量标准

### 叙事连贯性
- slides之间有清晰的逻辑递进关系
- 每页slide的key message构成完整的故事线
- 过渡自然，不跳跃

### 信息密度
- 每页不超过5个bullet points
- 每个bullet不超过2行
- 文字总量控制在30-50个中文字符/页（标题除外）

### 视觉层次
- 标题突出key message
- 内容支撑key message
- 图表优先于大段文字

## 示例：slide-content.json 片段

```json
{
  "slides": [
    {
      "slide_id": "slide-01",
      "layout": "title",
      "title": "Q4用户增长分析报告",
      "content": [
        {
          "type": "text",
          "text": "汇报人：数据分析团队 | 2025年1月",
          "source": null,
          "confidence": null
        }
      ],
      "speaker_notes": "向管理层汇报Q4季度用户增长情况的核心发现。"
    },
    {
      "slide_id": "slide-02",
      "layout": "content",
      "title": "Q4新增用户环比增长23%",
      "content": [
        {
          "type": "bullet",
          "text": "新增注册用户：12.5万（Q3: 10.2万）",
          "source": "final-report.md 表3-1",
          "confidence": "high"
        },
        {
          "type": "bullet",
          "text": "主要增长来源：移动端占比68%",
          "source": "final-report.md 图3-2",
          "confidence": "high"
        },
        {
          "type": "risk",
          "text": "注：1月受春节影响，增长可能放缓",
          "source": "final-report.md 第4.2节",
          "confidence": "medium"
        }
      ],
      "speaker_notes": "强调增长主要来自移动端，但需要提示季节性风险。"
    }
  ]
}
```
