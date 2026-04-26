---
name: memory-retraction
description: >
  处理已批准记忆条目的错误修正和撤回。
  触发条件：发现memory-entry存在事实错误、安全风险或过时内容时。
type: skill
---

# Memory Retraction Skill

## 触发条件
- 发现已批准的memory-entry包含事实错误
- 发现entry的安全风险被低估
- 发现entry内容已过时（技术栈/工具版本变更）
- 发现entry与多个后续approved entry存在系统性冲突

## 核心规则
1. **已批准的entry不可直接修改**——只能通过retraction流程处理
2. **retraction必须有明确理由和证据**
3. **retraction后原entry标记为retracted但不删除**——保留审计追踪
4. **retraction后可选择创建修正后的新candidate**

## Retraction流程

### Step 1: 提交Retraction请求
创建 `memory-retraction-request-{req_id}.json`：
```json
{
  "request_id": "req-20250115-x1y2",
  "target_entry_id": "entry-20250110-a1b2",
  "requested_by": "memory-reviewer",
  "reason": "factual_error",
  "reason_detail": "该entry中关于JWT refresh token的过期时间建议存在安全隐患...",
  "evidence": "/mnt/agents/output/audit/jwt-security-review.md",
  "proposed_action": "retract_and_replace",
  "replacement_candidate": "cand-20250115-new1",
  "submitted_at": "2025-01-15T09:00:00Z"
}
```

### Step 2: Retraction Review
由memory-reviewer审核retraction请求：
- 检查reason是否成立
- 验证evidence是否充分
- 评估proposed_action是否合理

### Step 3: 执行Retraction
审核通过后：
1. 更新原entry状态为 `retracted`
2. 添加retraction元数据：
   ```json
   {
     "status": "retracted",
     "retracted_at": "2025-01-15T10:00:00Z",
     "retracted_by": "memory-reviewer",
     "retraction_reason": "factual_error",
     "retraction_detail": "...",
     "replacement_entry": "entry-20250115-new2"
   }
   ```
3. 更新index.json
4. 如需要，创建replacement candidate并进入review流程

## Retraction原因分类

| 原因 | 说明 |
|------|------|
| factual_error | 事实性错误 |
| security_risk | 安全风险被低估 |
| outdated | 内容已过时 |
| conflicting | 与多个后续entry系统性冲突 |
| superseded | 被更好的entry取代 |

## 约束
- 只有memory-reviewer可以批准retraction
- retracted entry不可被检索或引用（在查询中过滤掉）
- 必须保留完整的retraction审计记录
- 如执行retract_and_replace，replacement entry必须通过完整review流程
