---
name: memory-candidate
description: >
  从任务执行中提取可复用经验，生成结构化memory候选。
  触发条件：任务完成且有价值可沉淀时（如：发现新pattern、踩坑经验、有效模板、重要参考资料）。
type: skill
---

# Memory Candidate 生成 Skill

## 触发条件
以下情况应触发memory-candidate生成：
- 任务完成后，发现有可复用的解决模式（pattern）
- 踩坑/试错后获得的经验教训（lesson）
- 生成了高质量的、可复用的模板（template）
- 发现了重要的规则或约束（rule）
- 收集到了有价值的参考资料（reference）

## 输入
- 任务执行记录（task log）
- 任务产物（artifacts）
- 执行过程中的反馈/纠错记录
- 最终交付物路径

## 输出
- `memory-candidate-{candidate_id}.json`
- 存储位置：`memory/candidates/`

## 输出字段说明

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| candidate_id | string | 是 | 唯一标识，格式：`cand-{timestamp}-{hash}` |
| source_task | string | 是 | 来源任务ID |
| source_agent | string | 是 | 执行该任务的agent名称 |
| content_type | string | 是 | 内容类型：pattern/template/rule/reference/lesson |
| content | string | 是 | 经验内容的详细描述 |
| source | string | 是 | 具体来源（文件路径/对话轮次/任务记录） |
| confidence | string | 是 | 可靠程度：high/medium/low |
| risk | string | 是 | 误用风险：low/medium/high/critical |
| created_at | string | 是 | ISO 8601格式时间戳 |

## Risk等级定义

| 等级 | 定义 | 示例 |
|------|------|------|
| low | 误用不会导致严重后果 | 代码风格偏好、命名规范 |
| medium | 误用可能导致低效或需返工 | 特定框架的配置方式 |
| high | 误用可能导致错误输出或系统故障 | 安全相关配置、数据处理方式 |
| critical | 误用可能导致数据丢失、安全漏洞或合规风险 | 权限控制、数据删除操作、加密配置 |

## Confidence等级定义

| 等级 | 条件 |
|------|------|
| high | 经过多次验证，有强证据支持，在多个类似场景中有效 |
| medium | 经过一次成功验证，证据充分但场景有限 |
| low | 基于推理或单次经验，尚未充分验证 |

## 核心约束
1. **只能生成candidate，不能直接写入memory-index**
2. **必须经过memory-review流程才能进入长期记忆**
3. **不允许生成没有source_task的candidate**
4. **content必须具体可操作，禁止空泛描述**

## 示例

```json
{
  "candidate_id": "cand-20250115-a1b2c3",
  "source_task": "task-build-auth-system",
  "source_agent": "backend-dev",
  "content_type": "lesson",
  "content": "使用JWT时，refresh token的过期时间应设置为access token的5-10倍，且必须存储在httpOnly cookie中以防止XSS攻击。",
  "source": "/mnt/agents/output/task-build-auth-system/implementation.md 第45-62行",
  "confidence": "high",
  "risk": "critical",
  "created_at": "2025-01-15T08:30:00Z"
}
```
