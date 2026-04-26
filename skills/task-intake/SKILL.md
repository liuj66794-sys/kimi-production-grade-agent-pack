---
name: task-intake
description: 将模糊需求转化为结构化任务单。触发条件：用户提出任何任务请求时首先调用。
type: skill
---

# Task Intake Skill

## 目的
将自然语言描述转化为可执行的结构化任务单。

## 触发条件
- 用户提出任何任务请求时首先调用
- 检测到自然语言描述的任务需求时
- 当前没有结构化任务单时

## 输入
用户自然语言请求。

## 输出
结构化任务单，必须包含以下字段：
- goal: 目标
- deliverables: 交付物列表
- input_materials: 输入材料
- constraints: 约束条件
- required_capabilities: 所需能力
- need_web: 是否需要联网
- need_code: 是否需要代码
- need_file_write: 是否需要文件读写
- need_subagents: 是否需要子Agent
- risk_assumptions: 风险假设列表
- minimal_plan: 最小可执行计划（至少3步）

## 工作流
1. 解析用户请求的意图和范围
2. 识别隐含需求和约束
3. 判断是否属于复杂任务（需要Swarm）
4. 输出结构化任务单
5. 标记是否需要进入swarm-orchestrator

## Hard Fail条件
1. 没有明确goal
2. 没有deliverables
3. 把自然语言需求直接改写成报告而非任务单
4. 暴露内部模块名给用户

## 不负责
- 不做研究
- 不写最终报告

## 输出契约
- 输出必须为有效的结构化数据格式
- 不得在输出中包含元评论或解释性文字
- 不得向用户暴露内部模块名称
