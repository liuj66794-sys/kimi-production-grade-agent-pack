# Assisted Mode 使用手册

## 版本: v1.4

---

## 1. 什么是 Assisted Mode

Assisted Mode（半自动模式）是一种**用户逐步确认**的任务执行模式。与全自动模式不同，Assisted Mode 在每个关键步骤之间插入用户确认点，让用户能够：

- 审查每一步的产出质量
- 决定是否继续下一步
- 在需要时回退或重试
- 对不确定的部分进行人工干预

### 核心特征

| 特征 | Assisted Mode | Guided Run | 全自动模式 |
|------|--------------|------------|-----------|
| 用户确认 | 每步确认 | 每步确认 | 无 |
| 输出内容 | 完整 Prompt + 产物路径 | 下一步指令 | 直接执行 |
| 适合场景 | 首次运行、复杂任务 | 标准化流程 | 简单重复任务 |
| 错误处理 | 用户介入 | 自动 Fallback | 自动重试 |

---

## 2. Assisted Mode 与 Guided Run 的区别

### Guided Run
- 是 Assisted Mode 的**半自动包装器**
- 提供标准化的步骤推进指令
- 自动管理产物路径和状态
- 内置校验和恢复机制
- 专注于**流程标准化**

### Assisted Mode
- 是更宽泛的概念
- 涵盖所有需要用户逐步确认的执行方式
- 不假设有脚本自动化
- 允许更灵活的人工干预
- 专注于**质量保障**

### 关系
```
Assisted Mode (概念)
    └── Guided Run (具体实现之一)
    └── Manual Step-by-Step (手工逐步执行)
    └── Recovery Runbook (恢复模式下的逐步执行)
```

---

## 3. 步骤概览

Assisted Mode 的任务执行分为 6 个核心步骤：

```
1. task-intake      → 任务理解与需求澄清
2. researcher       → 信息收集与研究
3. analyst          → 数据分析与洞察
4. evidence-synthesis → 证据整合与验证
5. writer           → 报告撰写
6. qa-reviewer      → 质量审查
```

### 状态流转

```
         ┌─────────────┐
    ┌───→│ task-intake │──┐
    │    └─────────────┘  │
    │    ┌─────────────┐  │
    ├────│  researcher │←─┘ (可回退)
    │    └─────────────┘  │
    │    ┌─────────────┐  │
    ├────│   analyst   │←─┘ (可回退)
    │    └─────────────┘  │
    │    ┌────────────────┐ │
    ├────│evidence-synthesis│←┘ (可回退)
    │    └────────────────┘ │
    │    ┌─────────────┐    │
    ├────│   writer    │←───┘ (可回退)
    │    └─────────────┘    │
    │    ┌─────────────┐    │
    ├────│ qa-reviewer │←───┘ (可回退至任一步骤)
    │    └─────────────┘    │
    │           │           │
    │           ▼           │
    │    ┌─────────────┐    │
    └────│   release   │    │
         └─────────────┘    │
```

---

## 4. 每一步的操作指南

### Step 1: Task-Intake

**目标**: 理解用户原始需求，澄清模糊点，定义任务范围

**操作**:
1. 复制 `assisted-mode-prompts.md` 中的 task-intake prompt
2. 将 prompt 粘贴到 Kimi Code 输入框
3. 等待 Kimi 返回结构化输出
4. 检查输出中的 `task-understanding.json` 是否符合预期
5. 确认无误后保存到指定路径

**预期产物**:
```
artifacts/
├── task-understanding.json      # 任务理解文档
├── requirement-clarification.md  # 需求澄清记录
└── scope-definition.json        # 范围定义
```

**Fallback**: 如果输出格式不正确，要求 Kimi 重新输出 JSON 代码块

---

### Step 2: Researcher

**目标**: 基于 task-intake 的理解，进行全面信息收集

**前置条件**: task-understanding.json 已确认存在

**操作**:
1. 检查上一步产物是否存在（`--validate-step task-intake`）
2. 复制 researcher prompt
3. 粘贴到 Kimi Code
4. 审查收集到的证据和引用
5. 确认证据地图（evidence-map.json）完整

**预期产物**:
```
artifacts/
├── evidence-map.json            # 证据地图
├── search-log.json              # 搜索记录
├── raw-evidence/                # 原始证据
│   ├── source-001.md
│   └── ...
└── researcher-notes.md          # 研究员笔记
```

**Fallback**: 如果搜索失败，切换到离线模式或缓存数据

---

### Step 3: Analyst

**目标**: 对 researcher 收集的数据进行分析，提取洞察

**前置条件**: evidence-map.json 已确认存在

**操作**:
1. 验证 researcher 产物完整性
2. 复制 analyst prompt
3. 粘贴到 Kimi Code
4. 审查分析结论是否基于充分证据
5. 检查不确定性标注是否适当

**预期产物**:
```
artifacts/
├── analysis-report.json         # 分析报告
├── insight-summary.md           # 洞察摘要
├── uncertainty-log.json         # 不确定性记录
└── data-visualizations/         # 数据可视化
    └── ...
```

**Fallback**: 如果证据不足，回退到 researcher 步骤补充

---

### Step 4: Evidence-Synthesis

**目标**: 整合所有证据，解决冲突，形成统一观点

**前置条件**: analysis-report.json 已确认存在

**操作**:
1. 验证 analyst 产物
2. 检查证据冲突日志
3. 复制 evidence-synthesis prompt
4. 粘贴到 Kimi Code
5. 审查合成结果，确保冲突已解决

**预期产物**:
```
artifacts/
├── synthesis-report.json        # 合成报告
├── conflict-resolution.md       # 冲突解决记录
├── evidence-hierarchy.json      # 证据层级
└── fact-check-summary.json      # 事实核查摘要
```

**Fallback**: 如果冲突无法自动解决，标记为人工裁决

---

### Step 5: Writer

**目标**: 基于合成结果撰写最终报告

**前置条件**: synthesis-report.json 已确认存在

**操作**:
1. 验证 evidence-synthesis 产物
2. 复制 writer prompt
3. 粘贴到 Kimi Code
4. 审查报告质量和完整性
5. 运行 `check_report_quality.py` 进行自动评分

**预期产物**:
```
artifacts/
├── final-report.md              # 最终报告
├── report-quality.json          # 质量评分
└── draft-versions/              # 草稿版本
    ├── draft-01.md
    └── ...
```

**Fallback**: 如果质量评分低于阈值，回退修改

---

### Step 6: QA-Reviewer

**目标**: 对最终报告进行全面质量审查

**前置条件**: final-report.md 和 report-quality.json 已确认存在

**操作**:
1. 验证 writer 产物
2. 运行 L1 Gate 检查
3. 复制 qa-reviewer prompt
4. 粘贴到 Kimi Code
5. 审查 QA 结果，确认是否通过

**预期产物**:
```
artifacts/
├── qa-review.json               # QA 审查结果
├── qa-findings.md               # 发现的问题
└── qa-recommendations.md        # 改进建议
```

**Fallback**: 如果 QA 未通过，回退到对应步骤修复

---

## 5. 失败 Fallback 机制

### 通用 Fallback 链

```
1. 首先: 要求 Kimi 重新输出（最多重试 2 次）
2. 其次: 使用正则表达式手动提取 JSON
3. 再次: 使用宽松模式解析
4. 最后: 人工介入，手动构造所需 JSON
```

### 步骤级 Fallback

| 步骤 | 主要失败模式 | Fallback 操作 |
|------|------------|--------------|
| task-intake | 需求理解偏差 | 重新澄清需求 |
| researcher | 搜索失败 | 使用缓存/离线数据 |
| analyst | 证据不足 | 回退补充研究 |
| evidence-synthesis | 冲突未解决 | 人工裁决 |
| writer | 质量不达标 | 回退修改 |
| qa-reviewer | 未通过 QA | 回退修复 |

### 状态恢复

如果执行中断，使用以下方式恢复：

```powershell
# 查看当前状态
python scripts/guided_run.py --status

# 从上次继续
python scripts/guided_run.py --resume

# 重置（需确认）
python scripts/guided_run.py --reset --confirm```

---

## 6. 预期产物总路径

```
output/
└── assisted-mode/
    ├── {case_id}/
    │   ├── task-understanding.json
    │   ├── evidence-map.json
    │   ├── analysis-report.json
    │   ├── synthesis-report.json
    │   ├── final-report.md
    │   ├── report-quality.json
    │   ├── qa-review.json
    │   └── run-state.json
```

---

## 7. 注意事项

1. **不要跳过步骤**: 每个步骤都有其存在的理由
2. **保留中间产物**: 即使看起来不需要，也要保存
3. **记录决策理由**: 每个确认点都要记录为什么确认
4. **及时检查**: 发现问题越早回退成本越低
5. **使用 schema 验证**: 每个 JSON 产物都要验证结构
