---
name: build-web-app-flow
description: 构建Web应用Flow：从需求到可部署Web应用的完整流程
type: flow
---

# Build Web App Flow

## 目的
编排多个Skill的调用顺序，实现从输入到交付的完整工作流。

## 触发条件
- 任务类型匹配本Flow定义的场景时自动触发
- 用户显式指定使用本Flow时
- task-intake输出匹配Flow的入口条件时

## 调用方式

### 自动触发
当task-intake的结构化任务单满足以下条件时，系统自动路由到本Flow：
- task-intake：定义应用需求和约束
- swarm-orchestrator：分解为产品、前端、后端、测试子任务
- deep-research：技术选型和最佳实践调研
- product-builder：输出PRD和功能规格
- 并行开发：前端、后端、测试用例同时开发
- 集成与审查：代码集成和质量审查
- final-packaging：输出部署包和文档

### 显式调用
用户可通过指令指定："使用 build-web-app-flow 处理此任务"

## 流程图

```mermaid

flowchart TD
    BEGIN([BEGIN]) --> INTAKE[task-intake]
    INTAKE --> ORCH[swarm-orchestrator]
    ORCH --> RESEARCH[deep-research<br/>技术选型]
    RESEARCH --> SPEC[product-builder<br/>产品规格]
    SPEC --> ORCH2{并行开发}
    ORCH2 --> FRONT[code-builder<br/>前端]
    ORCH2 --> BACK[code-builder<br/>后端]
    ORCH2 --> TEST[code-builder<br/>测试]
    FRONT --> INTEGRATE[集成]
    BACK --> INTEGRATE
    TEST --> INTEGRATE
    INTEGRATE --> REVIEW[quality-review]
    REVIEW --> PASS{审查通过?}
    PASS -->|是| PACKAGE[final-packaging<br/>部署包]
    PASS -->|否| FIX[返回修正]
    FIX --> ORCH2
    PACKAGE --> END([END])

```

## 步骤说明

### Step 1: task-intake
定义应用需求和约束
### Step 2: swarm-orchestrator
分解为产品、前端、后端、测试子任务
### Step 3: deep-research
技术选型和最佳实践调研
### Step 4: product-builder
输出PRD和功能规格
### Step 5: 并行开发
前端、后端、测试用例同时开发
### Step 6: 集成与审查
代码集成和质量审查
### Step 7: final-packaging
输出部署包和文档

## 输出契约
- Flow执行完成后输出最终交付物
- 每个中间步骤的输出作为下一步输入
- 质量审查节点为强制gate，fail时触发修正循环

## 失败处理
- 任意Skill节点返回fail时，Flow进入修正分支
- 修正后从最近的safe checkpoint重新执行
- 连续3次fail时升级到用户决策
