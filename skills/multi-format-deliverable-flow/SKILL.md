---
name: multi-format-deliverable-flow
description: 多格式交付Flow：同一份内容生成报告、幻灯片、表格等多种格式交付物
type: flow
---

# Multi Format Deliverable Flow

## 目的
编排多个Skill的调用顺序，实现从输入到交付的完整工作流。

## 触发条件
- 任务类型匹配本Flow定义的场景时自动触发
- 用户显式指定使用本Flow时
- task-intake输出匹配Flow的入口条件时

## 调用方式

### 自动触发
当task-intake的结构化任务单满足以下条件时，系统自动路由到本Flow：
- task-intake：定义多格式交付需求
- swarm-orchestrator：建立并行子任务树
- deep-research：统一信息收集
- evidence-synthesis：共享证据基础
- 并行生成：document-writer + slide-deck + spreadsheet-model同时执行
- quality-review：统一质量审查
- final-packaging：整合多格式交付物

### 显式调用
用户可通过指令指定："使用 multi-format-deliverable-flow 处理此任务"

## 流程图

```mermaid

flowchart TD
    BEGIN([BEGIN]) --> INTAKE[task-intake]
    INTAKE --> ORCH[swarm-orchestrator]
    ORCH --> RESEARCH[deep-research]
    RESEARCH --> SYNTH[evidence-synthesis]
    SYNTH --> ORCH2{并行分派}
    ORCH2 --> WRITE[document-writer<br/>报告]
    ORCH2 --> SLIDE[slide-deck<br/>幻灯片]
    ORCH2 --> SHEET[spreadsheet-model<br/>数据表]
    WRITE --> REVIEW[quality-review]
    SLIDE --> REVIEW
    SHEET --> REVIEW
    REVIEW --> PASS{全部通过?}
    PASS -->|是| PACKAGE[final-packaging]
    PASS -->|否| FIX[返回修正]
    FIX --> ORCH2
    PACKAGE --> END([END])

```

## 步骤说明

### Step 1: task-intake
定义多格式交付需求
### Step 2: swarm-orchestrator
建立并行子任务树
### Step 3: deep-research
统一信息收集
### Step 4: evidence-synthesis
共享证据基础
### Step 5: 并行生成
document-writer + slide-deck + spreadsheet-model同时执行
### Step 6: quality-review
统一质量审查
### Step 7: final-packaging
整合多格式交付物

## 输出契约
- Flow执行完成后输出最终交付物
- 每个中间步骤的输出作为下一步输入
- 质量审查节点为强制gate，fail时触发修正循环

## 失败处理
- 任意Skill节点返回fail时，Flow进入修正分支
- 修正后从最近的safe checkpoint重新执行
- 连续3次fail时升级到用户决策
