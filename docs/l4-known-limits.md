# L4 Known Limits

## KL-L4-001: Protected Keys Token Budget

**描述**: protected_keys（autonomy_policy、hitl_config、security_rules 等）在 context pack 中不可截断。当这些配置内容较大时，可能接近 50KB token 预算。

**影响**: 在极端情况下，protected keys 占用大量热层空间，留给实际任务上下文的 token 较少。

**缓解措施**: 
- 保持 autonomy policy 简洁
- 使用摘要而非完整日志
- 监控 protected keys 大小

**预计解决版本**: v4.2+

---

## KL-L4-002: Anomaly Counter 依赖 Audit Log 复核

**描述**: v4.0 的 anomaly_counter 在触发 degrade/pause 后，需要人工复核 audit log 确认异常是否真实存在。自动检测的准确度有限。

**影响**: 可能出现误报（正常行为被标记为异常）或漏报（异常未被检测到）。

**缓解措施**:
- 设置合理的阈值（degrade: 3, pause: 5）
- 所有异常事件记录详细上下文
- 提供人工覆写机制

**预计解决版本**: v4.3+

---

## KL-L4-003: HITL 单点审批瓶颈

**描述**: 当前 HITL 系统依赖单一审批流程，高频率的 A3+ 请求可能导致审批积压。

**影响**: Agent 执行效率降低，pending approvals 队列增长。

**缓解措施**:
- 批处理相似请求
- 设置合理的 timeout
- 考虑分级审批（不同风险级别不同审批者）

**预计解决版本**: v4.5+

---

## KL-L4-004: Context Pack 无持久缓存

**描述**: Context Pack 每次对话都重新编译，没有缓存机制。

**影响**: 重复计算开销，响应延迟增加。

**缓解措施**:
- 添加 context pack 缓存层
- 增量更新机制

**预计解决版本**: v4.5+

---

## KL-L4-005: Long-running Task 未实现

**描述**: v4.0 仅实现基础自治框架，long-running task 管理计划在 v4.7 实现。

**影响**: Agent 无法处理需要持续运行的任务。

**缓解措施**:
- 将长任务拆分为短任务
- 手动管理任务状态

**预计解决版本**: v4.7
