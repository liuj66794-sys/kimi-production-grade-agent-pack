# Guided Run 使用手册

## 版本: v1.5

---

## 1. 什么是 Guided Run

Guided Run 是 Assisted Mode 的**半自动包装器**。它不是后台 Swarm，不是全自动调度器，也不是多 Agent 并行系统。

Guided Run 的核心价值是：
- **标准化流程**: 确保每一步都按正确顺序执行
- **状态追踪**: 自动维护 run-state.json
- **校验集成**: 自动调用 integration_smoke_runner.py 校验
- **阻塞保护**: 在 blocked 状态下阻止继续推进
- **Resume 支持**: 中断后可从上次位置继续

### 架构分层

```
┌─────────────────────────────────┐
│        用户交互层               │
│     guided_run.py              │
│  - 显示下一步指令              │
│  - 管理 run-state.json         │
│  - 调用 smoke runner           │
│  - 提供 resume 建议            │
└──────────────┬──────────────────┘
               │
┌──────────────▼──────────────────┐
│        校验与记录层             │
│  integration_smoke_runner.py   │
│  - 步骤校验 (--validate-step)  │
│  - 产物验证                    │
│  - 记录 task-events            │
└─────────────────────────────────┘
```

**分层规则**:
- `guided_run.py` = 用户交互层（不直接写 task-events，不判定 QA Gate，不绕过 integration_smoke_runner）
- `integration_smoke_runner.py` = 校验与记录层

---

## 2. 安装与配置

### 2.1 前置要求

```powershell
# 必需文件
scripts/guided_run.py
scripts/integration_smoke_runner.py  # 可选但推荐
schemas/run-state.schema.json
docs/assisted-mode-prompts.md
docs/recovery-runbook.md```

### 2.2 目录结构

```
runtime/
└── run-state.json              # 自动创建
artifacts/
├── task-understanding.json     # Step 1 产物
├── evidence-map.json           # Step 2 产物
├── analysis-report.json        # Step 3 产物
├── synthesis-report.json       # Step 4 产物
├── final-report.md             # Step 5 产物
├── report-quality.json         # Step 5 产物
├── qa-review.json              # Step 6 产物
└── release-check.json          # Step 7 产物
```

---

## 3. 命令行接口

### 3.1 查看状态

```powershell
python scripts/guided_run.py --status```

输出示例：
```
============================================================
  Guided Run Status
  Case ID: case-2024-001
  Version: 1.5
============================================================
       [RUN ] task-intake
       [WAIT] researcher
       [WAIT] analyst
       [WAIT] evidence-synthesis
       [WAIT] writer
       [WAIT] qa-reviewer
       [WAIT] release

  Current Step: task-intake
  Completed: 0/7
============================================================
```

### 3.2 获取下一步指令

```powershell
python scripts/guided_run.py --next```

输出将包含：
1. 步骤标题和描述
2. Prompt 参考路径
3. 预期产物列表
4. 确认命令

### 3.3 标记步骤完成

```powershell
python scripts/guided_run.py --step task-intake```

此命令会：
1. 调用 `integration_smoke_runner.py --validate-step task-intake`
2. 检查上一步产物是否存在
3. 更新 run-state.json
4. 推进到下一步

### 3.4 恢复执行

```powershell
python scripts/guided_run.py --resume```

如果执行中断，使用 `--resume` 恢复：
- 增加 resume_count
- 显示当前状态
- 给出下一步建议

### 3.5 重置状态

```powershell
python scripts/guided_run.py --reset --confirm```

**必须**使用 `--confirm` 才会真正重置。此操作会：
- 删除 run-state.json
- 清除所有进度

---

## 4. 完整执行流程

### 4.1 首次运行

```powershell
# 1. 创建新运行（自动）
python scripts/guided_run.py --status

# 2. 获取第一步指令
python scripts/guided_run.py --next

# 3. 按照提示执行 Step 1 (task-intake)
#    - 复制 prompt
#    - 粘贴到 Kimi Code
#    - 保存产物

# 4. 确认 Step 1 完成
python scripts/guided_run.py --step task-intake

# 5. 继续下一步
python scripts/guided_run.py --next

# 6-12. 重复步骤 3-5 直到完成```

### 4.2 中断恢复

```powershell
# 查看当前状态
python scripts/guided_run.py --status

# 从上次继续
python scripts/guided_run.py --resume

# 获取下一步指令
python scripts/guided_run.py --next```

### 4.3 处理阻塞

```powershell
# 如果发现步骤被阻塞
python scripts/guided_run.py --status
# 会显示阻塞原因

# 查阅恢复手册
Get-Content 'docs/recovery-runbook.md' | Select-String -Pattern '-A 10 "错误码"'

# 解决问题后，继续
python scripts/guided_run.py --next```

---

## 5. 状态流转图

```
         ┌──────────────┐
         │  not_started │
         └──────┬───────┘
                │ --next
                ▼
         ┌──────────────┐
         │  in_progress │◄──────┐
         └──────┬───────┘       │ --step (retry)
                │               │
        ┌───────┼───────┐       │
        ▼       ▼       ▼       │
   ┌────────┐┌──────┐┌──────┐  │
   │completed││failed││blocked│  │
   └────┬───┘└──┬───┘└──┬───┘  │
        │       │       │      │
        ▼       ▼       ▼      │
   ┌──────────────────────────┐│
   │  --step 标记完成/重试    │┘
   └──────────────────────────┘
                │
                ▼
         ┌──────────────┐
         │   release    │
         └──────────────┘
```

---

## 6. 故障处理

### 6.1 常见错误

| 错误 | 原因 | 解决 |
|------|------|------|
| `Missing prerequisite artifacts` | 上一步产物未保存 | 先完成上一步 |
| `Validation failed` | Smoke runner 校验未通过 | 检查产物完整性 |
| `Step blocked` | 有阻塞问题未解决 | 查阅 recovery-runbook.md |
| `Run state corrupted` | run-state.json 损坏 | `python guided_run.py --reset --confirm` |

### 6.2 手动干预

如果 automated validation 失败但产物实际正确：

```powershell
# 1. 手动验证产物存在
Get-ChildItem -Path 'artifacts/task-understanding.json'

# 2. 手动编辑 run-state.json（不推荐，除非必要）
# 3. 或跳过验证直接标记（未来版本支持 --force）```

---

## 7. 注意事项

1. **不要手动修改 run-state.json** - 使用 `--step` 和 `--resume`
2. **保留所有中间产物** - 用于追溯和恢复
3. **阻塞时立即停止** - 不要绕过 blocked 状态
4. **使用原子写入** - run-state.json 使用原子写入保证一致性
5. **多任务隔离** - 每个 case_id 有独立的运行状态
