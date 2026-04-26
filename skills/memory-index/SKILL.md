---
name: memory-index
description: >
  管理已批准的长期记忆条目，提供CRUD（受限）和查询能力。
  触发条件：memory-review approve后更新，或需要检索已有记忆时。
type: skill
---

# Memory Index Skill

## 职责
管理经过review批准的记忆条目，维护只读为主的长期记忆库。

## 核心规则
1. **默认read-only**——已批准的entry不可随意修改
2. **仅能通过review流程新增**——新entry必须经过memory-review approve
3. **支持标记deprecated**——过时entry可标记为deprecated但不删除
4. **支持retraction**——错误entry可通过memory-retraction流程撤回
5. **访问追踪**——记录每条entry被检索的次数

## 存储结构
```
memory/
  entries/
    {entry_id}.json          # 单条记忆条目
  index.json                 # 索引文件（标签、类型、状态统计）
```

## Entry生命周期

```
[Candidate] --(review approve)--> [Active] --(deprecate)--> [Deprecated]
                                     |
                                     --(retraction)--> [Retracted]
```

- **Active**: 正常可用状态，可被检索和引用
- **Deprecated**: 已过时，不再推荐使用但保留记录
- **Retracted**: 因错误被撤回，不可引用

## 操作

### 新增Entry
```
前置条件：memory-review结果为approve
操作：
  1. 读取 approved candidate
  2. 生成 entry_id（格式：entry-{timestamp}-{hash}）
  3. 创建 entry 文件，包含 candidate 全部内容 + approval 元数据
  4. 更新 index.json
```

### 查询Entry
```
支持按以下维度查询：
  - content_type（pattern/template/rule/reference/lesson）
  - source_agent
  - status（active/deprecated）
  - tags（标签匹配）
  - 全文搜索（content字段）
```

### 标记Deprecated
```
前置条件：entry状态为active
操作：
  1. 更新 status 为 deprecated
  2. 添加 deprecated_reason
  3. 添加 deprecated_at 时间戳
  4. 更新 index.json
```

### 访问计数
```
每次entry被检索或引用时：
  access_count += 1
  last_accessed_at = 当前时间戳
```

## Index文件结构 (index.json)

```json
{
  "version": "1.0",
  "last_updated": "2025-01-15T10:00:00Z",
  "stats": {
    "total_entries": 42,
    "active": 38,
    "deprecated": 3,
    "retracted": 1
  },
  "by_type": {
    "pattern": 15,
    "template": 8,
    "rule": 12,
    "reference": 4,
    "lesson": 3
  },
  "entries": [
    {
      "entry_id": "entry-20250110-a1b2",
      "content_type": "pattern",
      "status": "active",
      "created_at": "2025-01-10T08:00:00Z",
      "access_count": 5
    }
  ]
}
```
