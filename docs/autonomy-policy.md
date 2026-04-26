# Autonomy Policy v1.0

## Overview

本文档定义了 Kimi Production-Grade Agent System v4.x L4 半自治层的动作分级策略。
所有动作必须遵循 **default_deny** 原则：未明确允许的动作一律禁止。

---

## 核心安全原则

1. **Default Deny**: 所有未明确 allowlist 的动作默认拒绝
2. **A2 Allowlist 显式控制**: A2 动作必须在显式 allowlist 中才被允许
3. **HITL 审批**: 所有 A3+ 动作必须经 Human-in-the-Loop 审批
4. **A5 超时禁止**: A5 高风险动作不允许通过 accepted_by_timeout 自动批准
5. **Anomaly Counter 降级**: 24h 内 3 次异常降级 A3+，5 次异常暂停 L4
6. **State Atomic Write**: 所有状态修改必须通过原子写入 + 版本冲突检查
7. **Protected Keys**: autonomy_policy、hitl_config、security_rules 等关键配置不可截断

---

## 动作分级

### A0: 完全禁止

以下动作在任何 autonomy_level 下均被严格禁止：

- 修改 autonomy_policy 本身
- 删除 audit log
- 绕过 Autonomy Gate
- 修改 security_rules（需 A5 显式人类批准）

### A1: 只读观察（默认启用）

A1 动作在所有 active 状态下默认允许：

- 读取 project-state
- 读取 roadmap
- 读取 task-events
- 生成 weekly report（只读部分）

### A2: 低风险只读动作（需 allowlist）

**必须显式 allowlist，不在列表中的 A2 动作默认 deny。**

允许的动作：

- 读取 skill definitions
- 查询 artifact index
- 生成 summary/report
- 运行 eval（dry-run 模式）
- 检查 artifact quality

### A3: 低风险写入动作（需 HITL 审批）

- 更新 task status
- 创建 memory-candidate
- 标记 issue 为 completed
- 生成并提交 memory-candidate

### A4: 中风险动作（需 HITL 审批 + 额外验证）

- 修改 roadmap
- 创建 sprint
- 修改 project config（非安全字段）

### A5: 高风险动作（需显式人类批准）

- 修改 autonomy_policy
- 提升 autonomy_level
- 执行 shell 命令
- 修改 security rules
- approve memory（从 candidate 到 index）
- 发布 release

---

## A2 Allowlist

```
read_project_state
read_roadmap
read_task_events
read_artifact_index
read_skill_definitions
generate_summary
generate_weekly_report_draft
run_eval_dry_run
check_artifact_quality
```

---

## A2 Forbidden Patterns

```
write_*_without_approval
modify_autonomy_*
delete_audit_*
bypass_gate
approve_memory
execute_shell
publish_release
```

---

## Default Deny 规则

1. 所有未明确 allowlist 的动作默认 deny
2. 所有 A3+ 动作必须 HITL 审批
3. A5 动作不允许 accepted_by_timeout 自动批准
4. A2 动作不在 allowlist 中 → block
5. 匹配 forbidden pattern 的动作 → block（无论 allowlist）
6. 当前 autonomy_level 不允许的动作级别 → block

---

## Autonomy Level 映射

| autonomy_level | 允许的动作级别 |
|----------------|---------------|
| a0             | 无（完全禁止） |
| a1             | a0, a1         |
| a2             | a0, a1, a2     |
| a3             | a0, a1, a2, a3 |
| a4             | a0, a1, a2, a3, a4 |
| a5             | a0, a1, a2, a3, a4, a5 |

---

## Anomaly Counter 限制

| 指标 | 阈值 | 触发行为 |
|------|------|----------|
| degrade_count_24h | >= 3 | 限制 A3+ 动作 |
| pause_count_24h   | >= 5 | 完全暂停 L4 |

---

## 修订历史

| 版本 | 日期 | 变更 |
|------|------|------|
| 1.0  | 2026-04-25 | 初始版本 |
