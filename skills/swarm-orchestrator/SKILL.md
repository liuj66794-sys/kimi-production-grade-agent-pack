---
name: swarm-orchestrator
description: 复杂任务自动分派与多Agent协同编排。触发条件：task-intake标记为swarm任务时自动调用。
type: skill
---

# Swarm Orchestrator Skill

## 目的
将复杂任务分解为多Agent协作执行，管理依赖关系、冲突解决和结果整合。

## 触发条件
- task-intake标记为swarm任务时自动调用
- 用户显式要求多Agent协作时
- 任务需要5个以上独立信息源时
- 任务涉及多领域/多格式/多角色时

## 输入
来自task-intake的结构化任务单。

## 输出
- 完整执行任务树（含状态标记）
- 冲突清单及解决方案
- 统一核心结论
- 交付物汇总

## 工作流
1. **建立任务树**：将复杂任务分解为可独立执行的子任务
2. **标记依赖**：识别子任务间的执行顺序和依赖关系
3. **分配子Agent**：根据子任务类型分配专门化Agent（参考 delegation-matrix.md）
4. **指定输出契约**：为每个子Agent定义明确的输出格式和标准（参考 subagent-output-contract.md）
5. **收集结果**：按依赖顺序收集各子Agent的执行结果
6. **建立冲突清单**：识别并记录结果间的冲突和不一致（参考 conflict-resolution.md）
7. **补充缺失任务**：检查覆盖度，补充未预见任务
8. **统一核心结论**：整合所有子任务结果为一致的整体结论
9. **调用后续Skill**：根据交付物类型调用document-writer或对应下游Skill
10. **调用quality-review**：在最终交付前触发质量审查

## Hard Fail条件
1. 未建立完整的任务树即开始执行
2. 未标记子任务依赖关系
3. 未定义子Agent输出契约
4. 发现冲突但未记录到冲突清单
5. 跳过quality-review直接输出最终交付物

## 不负责
- 不执行具体研究或编码任务（委托给子Agent）
- 不代替子Agent做专业判断
- 不凭空补充未经验证的结论

## 资源索引
- references/delegation-matrix.md — 子Agent分派矩阵
- references/subagent-output-contract.md — 子Agent输出契约模板
- references/conflict-resolution.md — 冲突解决策略
- references/boundaries.md — 边界定义与复杂度阈值
