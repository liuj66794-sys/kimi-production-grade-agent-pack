---
name: final-packaging
description: 将多个交付物整合为最终输出包，包含目录、说明和格式化整理。
type: skill
---

# Final Packaging Skill

## 目的
将所有交付物整合为结构清晰、易于使用的最终输出包。

## 触发条件
- 任务所有子任务完成
- quality-review通过后
- 需要向用户呈现完整交付物

## 输入
- 所有中间和最终交付物
- 任务单中的deliverables要求
- 用户格式偏好

## 输出
- 整合的交付物包
- 目录索引（README/导航）
- 使用说明（如有必要）

## 工作流
1. 收集所有相关交付物
2. 验证完整性（对照deliverables）
3. 生成目录和索引
4. 格式化统一
5. 添加使用说明和元信息
6. 输出最终包

## 不负责
- 不修改已通过quality-review的内容
- 不做新的内容创作
- 不替代具体生产Skill
