# Report Quality Guidelines

## 版本: v1.4-v1.5

---

## 1. 概述

本文档定义了报告质量的评估标准和使用指南。`check_report_quality.py` 脚本基于本指南自动评估报告质量，生成 `report-quality.json`。

### 质量评分维度

| 维度 | 权重 | 满分 | 说明 |
|------|------|------|------|
| 结构完整性 | 20% | 20 | 9个必需部分是否齐全 |
| 引用规范性 | 20% | 20 | 引用格式和数量 |
| 不确定性标注 | 15% | 15 | 不确定性声明的明确性 |
| 格式统一性 | 15% | 15 | 代码块、表格格式 |
| 内容充实度 | 15% | 15 | 字数、段落丰富度 |
| 可追溯性 | 15% | 15 | 与证据地图的关联 |
| **总计** | **100%** | **100** | |

### 通过阈值

- **PASS**: 总分 >= 70
- **FAIL**: 总分 < 70，需要改进

---

## 2. 结构完整性 (20分)

### 2.1 必需部分清单

报告必须包含以下 9 个部分：

1. **Executive Summary** (执行摘要) - 报告的简明概括
2. **Introduction** (引言) - 背景、目的、范围
3. **Methodology** (方法论) - 研究方法和数据来源
4. **Findings** (主要发现) - 核心研究结果
5. **Evidence Analysis** (证据分析) - 对证据的详细分析
6. **Uncertainties** (不确定性) - 已知的局限和不确定因素
7. **Recommendations** (建议) - 基于发现的建议
8. **Conclusion** (结论) - 总结性陈述
9. **References** (参考文献) - 引用的来源列表

### 2.2 评分规则

```
score = (present_sections / 9) * 20
```

- 9/9 部分 → 20 分
- 7/9 部分 → 15.6 分
- 5/9 部分 → 11.1 分
- < 5 部分 → 需要重写

### 2.3 部分名称变体

脚本支持中英文标题变体检测：

| 标准名称 | 接受的中文变体 |
|----------|--------------|
| executive_summary | 执行摘要、摘要 |
| introduction | 引言、介绍 |
| methodology | 方法论、研究方法 |
| findings | 主要发现、发现、结果 |
| evidence_analysis | 证据分析、数据分析 |
| uncertainties | 不确定性、风险、局限性 |
| recommendations | 建议、推荐 |
| conclusion | 结论、总结 |
| references | 参考文献、引用、来源 |

---

## 3. 引用规范性 (20分)

### 3.1 引用格式

必须使用标准格式：

```markdown
正文引用: [^1^]
参考文献: [^1^]: 来源描述
```

### 3.2 评分构成

| 子项 | 满分 | 规则 |
|------|------|------|
| 引用数量 | 10 | >=10得10分, >=5得7分, >=1得3分 |
| 引用格式 | 10 | 全部正确得10分, 每处错误扣2分 |

### 3.3 常见问题

- `[^1]` - 缺少尾部 `^`
- `[1]` - 缺少两侧的 `^`
- `[来源名]` - 非标准格式
- 有引用正文但无参考文献部分

---

## 4. 不确定性标注 (15分)

### 4.1 标注方式

**推荐方式** (使用 callout):```markdown> [!NOTE] 不确定性声明> 本结论基于有限样本，可能存在偏差。```**可接受方式**:- `> **注意**: 不确定...`
- 明确使用"不确定"、"局限性"、"caveat" 等词汇

### 4.2 评分构成| 子项 | 满分 | 规则 ||------|------|------|| 显式标注 | 8 | 有 [!NOTE] 标注得8分 || 语言使用 | 7 | >=3处得7分, >=1处得4分 |

---

## 5. 格式统一性 (15分)

### 5.1 代码块规范

所有代码块必须有语言标记：

```markdown
推荐:
```python
code here
```

不推荐:
```
code here (无语言标记)
```
```

### 5.2 表格规范

所有表格必须有表头分隔行：

```markdown
推荐:
| 列A | 列B |
|-----|-----|
| 1   | 2   |

不推荐:
| 列A | 列B |
| 1   | 2   | (无分隔行)
```

### 5.3 评分构成| 子项 | 满分 | 规则 ||------|------|------|| 代码块标签 | 7 | 全部有标签得7分, 按比例扣分 || 表格表头 | 8 | 全部有表头得8分, 按比例扣分 |

---

## 6. 内容充实度 (15分)

### 6.1 字数标准

| 等级 | 字数 | 得分 ||------|------|------|| 优秀 | >=2000 | 8分 || 良好 | >=1000 | 6分 || 及格 | >=500 | 4分 || 不足 | <500 | 2分 |

### 6.2 段落结构

| 等级 | 段落数 | 得分 ||------|--------|------|| 良好 | >=10 | 7分 || 及格 | >=5 | 5分 || 不足 | <5 | 2分 |

---

## 7. 可追溯性 (15分)

### 7.1 证据关联

报告应引用 evidence-map.json 中的证据 ID：

```markdown
如: "根据 EVD-001 的研究结果..."
```

### 7.2 评分构成| 子项 | 满分 | 规则 ||------|------|------|| 证据引用率 | 10 | >=50%得10分, >0得5分 || 参考文献内容 | 5 | 有实质性内容得5分 |

---

## 8. 使用流程

### 8.1 基本用法```bash# 评估报告python scripts/check_report_quality.py --report final-report.md

# 带证据地图python scripts/check_report_quality.py --report final-report.md --evidence-map evidence-map.json

# 指定输出路径python scripts/check_report_quality.py --report final-report.md --output artifacts/report-quality.json
```

### 8.2 质量改进流程

```
1. 运行 check_report_quality.py
        ↓
2. 查看总分和维度分
        ↓
3. 针对低分项改进报告
        ↓
4. 重新运行检查
        ↓
5. 确认达到阈值 (>=70)
```

### 8.3 CI 集成

```yaml
# .github/workflows/quality-check.yml 示例
- name: Report Quality Check
  run: |
    python scripts/check_report_quality.py \
      --report artifacts/final-report.md \
      --evidence-map artifacts/evidence-map.json \
      --output report-quality.json
    
    # 检查是否通过
    PASSED=$(python -c "import json; d=json.load(open('report-quality.json')); print(d['passed_threshold'])")
    if [ "$PASSED" != "True" ]; then
      echo "Report quality check FAILED"
      exit 1
    fi
```

---

## 9. 版本历史

| 版本 | 日期 | 变更内容 |
|------|------|---------|
| 1.4 | - | 初始版本，6个评分维度 |
| 1.5 | - | 增加证据地图关联检查，完善评分规则 |
