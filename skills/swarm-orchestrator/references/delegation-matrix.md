# 子Agent分派矩阵

## 分派决策表

| 子任务类型 | 推荐子Agent | 备用方案 | 触发条件 |
|-----------|------------|---------|---------|
| 深度研究 | deep-research | 通用研究Agent | 需要外部信息源 |
| 资料整合 | evidence-synthesis | deep-research | 多源信息需要结构化 |
| 报告撰写 | document-writer | 通用写作Agent | 需要结构化报告 |
| 代码开发 | code-builder | 通用编程Agent | 需要代码交付 |
| 数据分析 | spreadsheet-model | code-builder | 需要数值分析 |
| 演示文稿 | slide-deck | document-writer | 需要幻灯片 |
| 质量审查 | quality-review | 自检清单 | 交付前强制审查 |
| 产品规划 | product-builder | document-writer | 需要产品方案 |
| 视觉分析 | multimodal-analysis | 通用Agent | 需要图像/视频分析 |
| Skill内化 | document-to-skill | document-writer | 需要沉淀方法论 |

## 分派原则
1. **能力匹配优先**：子任务需求与Agent专长相符
2. **负载均衡**：避免单一Agent过载
3. **依赖最小化**：优先分配无依赖的子任务并行执行
4. **输出可组合**：确保各Agent输出格式可整合

## 重写规则
- 当推荐Agent不可用时，使用备用方案
- 当任务跨越多个类型时，拆分为多个子任务分别分派
- 紧急任务可标记为high-priority优先调度
