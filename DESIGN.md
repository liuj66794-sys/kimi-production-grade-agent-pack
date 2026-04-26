---
## 11. 运行策略

### 11.1 运行参数配置

| 参数 | 值 | 说明 |
|------|-----|------|
| **thinking** | auto | 复杂任务启用，简单任务关闭 |
| **tool_choice** | auto | 由 Agent 根据任务自主选择工具 |
| **max_turns** | 50 | 单次 Swarm 会话最大轮次 |
| **context_window** | 128K | 上下文窗口大小 |
| **temperature** | 0.3 | 生成温度（低=确定性高） |
| **timeout_per_agent** | 300s | 单 Agent 超时时间 |
| **max_retries** | 3 | 失败最大重试次数 |

### 11.2 安全审批点

以下操作需要显式用户确认：

| # | 操作类型 | 触发条件 | 确认方式 |
|---|---------|---------|----------|
| 1 | 大量网络搜索 | 单次任务搜索 > 10 次 | 弹窗确认预算 |
| 2 | 代码执行 | 执行用户提供的代码 | 显式确认沙箱环境 |
| 3 | 文件写入 | 写入非临时目录 | 确认路径和内容 |
| 4 | 外部 API 调用 | 调用付费 API | 确认费用预算 |
| 5 | 长时间运行 | 预计执行 > 5 分钟 | 确认是否等待 |
| 6 | 敏感数据访问 | 访问包含密钥/Token 的文件 | 显式授权 |

### 11.3 预算管理

```yaml
BudgetManager:
  tiers:
    - name: free
      daily_limit: "$0.50"
      features: [基础搜索, 代码执行, 文件操作]

    - name: standard
      daily_limit: "$5.00"
      features: [全部核心功能, MCP 工具]

    - name: premium
      daily_limit: "$20.00"
      features: [全部功能, 高频率调用, 优先队列]

  alerts:
    - threshold: 0.5
      action: "控制台警告"
    - threshold: 0.8
      action: "弹窗确认是否继续"
    - threshold: 1.0
      action: "暂停，需用户手动解锁"
```

### 11.4 运行模式

| 模式 | 说明 | 适用场景 |
|------|------|----------|
| **single** | 单 Agent 模式，不启动 Swarm | 简单问答、代码片段 |
| **swarm-lite** | 轻量 Swarm，最多 2 个 Agent | 中等复杂度任务 |
| **swarm-full** | 完整 Swarm，所有 Agent 可用 | 复杂端到端任务 |
| **swarm-review** | 强制 qa-reviewer 审查 | 高质量要求任务 |
---
## 12. 工具、插件、MCP职责边界

### 12.1 职责边界表

| 层级             | 组件       | 职责                            | 不做什么                          | 示例                              |
| ---------------- | ---------- | ------------------------------- | --------------------------------- | --------------------------------- |
| **核心层** | 浏览器工具 | 网页搜索、导航、内容提取        | 不执行网页上的操作（表单提交等）  | web_search, browser_visit         |
|                  | 代码执行   | 沙箱内代码运行、测试            | 不访问外部网络                    | code_execution, unit_test_runner  |
|                  | 文件操作   | 读写项目内文件                  | 不访问系统敏感路径                | read_file, write_file             |
|                  | 记忆管理   | 知识库存取、Skill 知识读取      | 不做自动归纳（memory-curator 做） | memory_read, skill_knowledge_read |
| **MCP 层** | MCP 浏览器 | 增强浏览器能力（JS 执行、截图） | 不替代核心浏览器                  | mcp_browser                       |
|                  | MCP Shell  | 增强命令行能力                  | 不执行危险命令（有白名单）        | mcp_shell                         |
|                  | MCP 自定义 | 第三方 MCP 服务接入             | 不做核心功能替代                  | 视具体 MCP 而定                   |
| **插件层** | 第三方插件 | 扩展特定领域能力                | 不替代 Agent 核心能力             | 见 12.2 节                        |

### 12.2 插件层（Beta）

插件层处于 Beta 状态，提供扩展机制：

```
plugins/
├── README.md              # 插件开发指南
├── registry.yaml          # 插件注册表
├── example-plugin/        # 示例插件
│   ├── manifest.yaml      # 插件清单
│   ├── main.py            # 插件入口
│   └── config.yaml        # 插件配置
└── third-party/           # 第三方插件（用户安装）
    └── .gitkeep
```

**插件规范**:

- 必须提供 `manifest.yaml`，声明名称、版本、依赖、权限
- 权限申请遵循最小必要原则
- 插件运行在沙箱中，不直接访问核心系统
- 插件接口版本与项目版本关联

**首批计划插件**:

- `plugin-web-scraper`: 增强网页抓取能力
- `plugin-code-linter`: 多语言代码静态检查
- `plugin-doc-generator`: 自动生成 API 文档

### 12.3 MCP 集成策略

| 集成方式        | 优先级 | 说明                          |
| --------------- | ------ | ----------------------------- |
| 官方 MCP 适配器 | P0     | 优先使用官方提供的 MCP 适配器 |
| 社区 MCP        | P1     | 经过审核的社区 MCP            |
| 自定义 MCP      | P2     | 用户自定义 MCP（需声明风险）  |

---

## 13. 评测闭环

### 13.1 Eval Runner L1 最低形态

L1 阶段的 Eval Runner 必须实现以下最低功能：

```yaml
# evals/eval-runner.yaml
EvalRunnerL1:
  capabilities:
    - 加载测试用例（YAML 格式）
    - 执行预设评测任务
    - 对比 Agent 输出与预期输出
    - 生成评分报告

  inputs:
    - test_cases: "测试用例文件路径"
    - agent_outputs: "Agent 实际输出"
    - rubric: "评分标准文件"

  outputs:
    - score_report: "评分报告（JSON）"
    - diff_report: "差异报告"
    - pass_fail: "通过/不通过判定"

  min_requirements:
    - "至少覆盖 3 个核心 Skill 的评测"
    - "至少 10 个测试用例"
    - "支持自动化批量执行"
    - "生成可读的结果报告"
```

### 13.2 三层评测体系

| 层级 | 名称               | 频率         | 内容                            | 执行者   |
| ---- | ------------------ | ------------ | ------------------------------- | -------- |
| L1   | **单元评测** | 每次提交     | 单个 Skill/Agent 的输入输出对比 | CI 自动  |
| L2   | **集成评测** | 每日         | 端到端 Flow 的完整执行          | 定时任务 |
| L3   | **回归评测** | 每次版本发布 | 全量基准测试，对比历史版本      | 发布前   |

### 13.3 评分 Rubric

```yaml
# evals/rubric/default-rubric.yaml
Rubric:
  version: "1.0.0"

  dimensions:
    - name: correctness
      description: "正确性"
      weight: 0.30
      levels:
        - score: 5
          description: "完全正确，无任何错误"
        - score: 4
          description: "基本正确，有小瑕疵"
        - score: 3
          description: "部分正确，有 noticeable 问题"
        - score: 2
          description: "多数不正确"
        - score: 1
          description: "完全错误"

    - name: completeness
      description: "完整性"
      weight: 0.25
      levels:
        - score: 5
          description: "完全覆盖所有需求"
        - score: 3
          description: "覆盖大部分需求"
        - score: 1
          description: "大量遗漏"

    - name: quality
      description: "质量"
      weight: 0.25
      levels:
        - score: 5
          description: "超出预期，可直接生产使用"
        - score: 4
          description: "良好，需微调"
        - score: 3
          description: "可接受，需修改"
        - score: 1
          description: "不可接受"

    - name: efficiency
      description: "效率"
      weight: 0.10
      levels:
        - score: 5
          description: "最优路径，无冗余"
        - score: 3
          description: "有少许冗余"
        - score: 1
          description: "严重低效"

    - name: format_compliance
      description: "格式合规"
      weight: 0.10
      levels:
        - score: 5
          description: "完全符合 Schema"
        - score: 3
          description: "基本符合，有小偏差"
        - score: 1
          description: "不符合"

  scoring_method: "weighted_average"
  pass_threshold: 3.5  # 满分 5 分
```

### 13.4 版本管理与 CI

```yaml
# 评测 CI 配置摘要
EvalCI:
  triggers:
    - pull_request
    - daily_cron
    - pre_release

  stages:
    - name: unit_eval
      description: "单元评测"
      condition: "每次 PR"
      timeout: 10m

    - name: integration_eval
      description: "集成评测"
      condition: "每日 + 每次 Release"
      timeout: 30m

    - name: regression_eval
      description: "回归评测"
      condition: "每次 Release"
      timeout: 60m

  reporting:
    - pr_comment: "PR 中自动评论评测结果"
    - dashboard: "评测看板，展示历史趋势"
    - alert: "评分下降 > 10% 时告警"

  baseline_management:
    - "每个版本发布时保存评测基线"
    - "新版本必须与基线对比"
    - "评分下降自动阻断发布"
```

---

## 14. 成熟度分级

### 14.1 L0-L5 成熟度模型

| 级别         | 名称     | Agent 数量 | Skill 数量       | 关键特征                        | 目标用户   |
| ------------ | -------- | ---------- | ---------------- | ------------------------------- | ---------- |
| **L0** | 概念验证 | 1-2        | 0                | 单 Agent 能力验证，无协作       | 内部测试   |
| **L1** | MVP      | 5          | 7 核心 + 4 Flow  | 核心 Agent 协作，基本 Flow 可用 | 早期采用者 |
| **L2** | 扩展     | 7          | +2 核心 + 2 Flow | 增加 slide-maker、spreadsheet   | 技术写作者 |
| **L3** | 完整     | 9          | +2 核心 + 2 Flow | 全量 Agent，memory-curator 启用 | 专业用户   |
| **L4** | 成熟     | 9+         | 社区 Skill       | 社区生态活跃，插件丰富          | 广大开发者 |
| **L5** | 生产级   | 9+         | 生态成熟         | 接近官方 Agent 体验，企业可用   | 所有用户   |

### 14.2 各级升级条件

| 升级路径 | 条件                                           |
| -------- | ---------------------------------------------- |
| L0 → L1 | 核心 Agent 全部可运行，至少 2 个 Flow 可用     |
| L1 → L2 | L1 评测通过（平均分 > 3.5），slide-maker 可用  |
| L2 → L3 | L2 评测通过，memory-curator 可用，用户反馈积极 |
| L3 → L4 | 社区贡献 Skill > 10 个，插件生态初步形成       |
| L4 → L5 | 评测分数稳定在 4.5+，企业级安全合规            |

---

## 15. 最终成品定义

### 15.1 10项组成清单

最终成品包含以下 10 项核心组件：

| #  | 组件                      | 说明                               | 交付物                             |
| -- | ------------------------- | ---------------------------------- | ---------------------------------- |
| 1  | **Agent 角色定义**  | 9 个 Agent 的完整 YAML 配置        | `agents/roles/*.yaml`            |
| 2  | **Swarm 编排配置**  | 主控 Agent 的调度逻辑和配置        | `agents/swarm/swarm-config.yaml` |
| 3  | **核心 Skill 库**   | 7 个核心 Skill 的完整定义          | `skills/core/*/`                 |
| 4  | **Flow Skill 库**   | 4 个 Flow Skill 的完整定义         | `skills/flow/*/`                 |
| 5  | **输出契约 Schema** | 所有 Agent 的 Schema 定义          | `schemas/*.yaml`                 |
| 6  | **系统提示词库**    | 主控 + 子 Agent 的系统提示词       | `prompts/system/*.md`            |
| 7  | **评测体系**        | Eval Runner + Rubric + 测试用例    | `evals/*/`                       |
| 8  | **工具封装层**      | 浏览器、代码执行、文件操作等工具   | `tools/*/`                       |
| 9  | **文档集**          | README、DESIGN、AGENTS、QUICKSTART | 根目录文档                         |
| 10 | **版本管理**        | VERSION 文件 + 变更日志            | `VERSION`, `docs/changelog.md` |

### 15.2 成品质量标准

成品必须通过以下检查才能发布：

- [ ] 所有 YAML 文件通过语法验证
- [ ] 所有 Schema 文件通过校验
- [ ] L1 评测全部通过（>= 3.5 分）
- [ ] 文档完整性检查通过
- [ ] 版本号一致性检查通过
- [ ] 安全审查通过（无敏感信息泄露）

---

## 16. 安装与发现路径

### 16.1 安装路径

```powershell
# 方式 1: 一键安装（推荐）
curl -fsSL https://kimi.moonshot.cn/agents/install.sh | bash

# 方式 2: 手动克隆
git clone https://github.com/moonshot-ai/kimi-production-grade-agent-pack.git
cd kimi-production-grade-agent-pack
./install.sh

# 方式 3: 通过 Kimi  marketplace（L3 阶段）
# 在 Kimi 客户端中搜索 "Production-Grade Agent Pack" 并安装```

### 16.2 发现路径

| 渠道        | 方式                  | 状态    |
| ----------- | --------------------- | ------- |
| GitHub      | 搜索仓库，README 引导 | L1 可用 |
| Kimi 客户端 | Marketplace 浏览/搜索 | L3 可用 |
| 社区推荐    | 技术社区、博客推荐    | L2 起   |
| 官方文档    | Kimi 官方文档引用     | L4 起   |
| 口碑传播    | 用户自发分享          | 持续    |

### 16.3 首次使用引导

```
安装完成 → 自动检测环境 → 加载 5 个 L1 Agent
    → 运行欢迎任务（展示 Swarm 协作）
    → 展示可用 Flow 列表
    → 引导用户完成第一个任务
    → 提示阅读 QUICKSTART.md
```

---

## 17. 最小可行版本与演进路线

### 17.1 L1 MVP 内容

L1 MVP 是项目的最小可行版本，必须包含：

#### Agent（5 个）

- [X] researcher — 检索与来源评估
- [X] analyst — 结构化分析
- [X] coder — 代码实现与测试
- [X] writer — 文档写作
- [X] qa-reviewer — 质量审查

#### Skill（7 核心 + 4 Flow）

- [X] task-intake
- [X] swarm-orchestrator
- [X] deep-research
- [X] evidence-synthesis
- [X] document-writer
- [X] quality-review
- [X] eval-runner
- [X] deep-research-report-flow
- [X] multi-format-deliverable-flow（基础版）
- [X] build-web-app-flow（基础版）
- [X] document-to-skill-flow

#### 基础设施

- [X] Agent YAML 配置体系
- [X] Schema 验证框架
- [X] 工具权限系统
- [X] Eval Runner L1
- [X] 基础 CI 配置
- [X] 完整文档集（README, DESIGN, AGENTS）

### 17.2 版本路线

| 版本              | 目标          | 关键交付                      | 时间   |
| ----------------- | ------------- | ----------------------------- | ------ |
| **v1.0.0**  | 产品蓝图冻结  | 设计文档定稿，规格确认        | 当前   |
| **v1.1.0**  | L1 Agent 实现 | 5 个核心 Agent 可运行         | +2 周  |
| **v1.2.0**  | Flow 完善     | 4 个 Flow 全部可用            | +4 周  |
| **v1.3.0**  | 体验优化      | QUICKSTART.md，首次体验优化   | +6 周  |
| **v1.4.0**  | L2 Agent 上线 | slide-maker, spreadsheet 启用 | +8 周  |
| **v2.0.0**  | L3 完整版     | 全量 9 个 Agent，社区生态启动 | +12 周 |
| **v2.1.0+** | 持续迭代      | 基于用户反馈和社区贡献演进    | 持续   |

### 17.3 里程碑检查点

| 里程碑         | 检查项                    | 通过标准              |
| -------------- | ------------------------- | --------------------- |
| M1: Agent 就绪 | 5 个 L1 Agent 可独立执行  | 各 Agent 单元测试通过 |
| M2: Flow 打通  | 至少 2 个 Flow 端到端可用 | 集成评测 >= 3.5 分    |
| M3: 体验达标   | 用户体验评分达标          | 体验评分 >= 4.0       |
| M4: 社区就绪   | 文档完善，可外部贡献      | 新用户可独立安装使用  |
| M5: L2 就绪    | 7 个 Agent 可用           | 新增 Agent 评测通过   |
| M6: 生态启动   | 社区 Skill 贡献活跃       | 社区贡献 Skill > 5 个 |

### 17.4 风险与缓解

| 风险             | 影响 | 可能性 | 缓解措施                         |
| ---------------- | ---- | ------ | -------------------------------- |
| Agent 协作不稳定 | 高   | 中     | 完善的失败兜底策略，主控接管能力 |
| 上下文管理复杂   | 高   | 高     | 分段处理，上下文压缩，记忆管理   |
| 评测标准主观     | 中   | 中     | 多人标注校准，量化指标优先       |
| 用户需求多样     | 中   | 高     | 优先覆盖高频场景，社区扩展长尾   |
| 性能瓶颈         | 中   | 中     | 并行执行，超时控制，缓存机制     |

---

## 附录 A: 术语表

| 术语                  | 定义                                          |
| --------------------- | --------------------------------------------- |
| **Agent**       | 具有特定角色和能力的 AI 执行单元              |
| **Skill**       | 定义 Agent 行为的方法论和流程规范             |
| **Flow**        | 端到端的任务执行流程，串联多个 Skill 和 Agent |
| **Swarm**       | 多 Agent 协作的执行模式                       |
| **主控 Agent**  | 负责任务调度和 Agent 编排的中央协调者         |
| **Schema**      | Agent 输出的结构化数据格式规范                |
| **Rubric**      | 评测评分标准和维度定义                        |
| **Eval Runner** | 自动化评测执行工具                            |
| **MCP**         | Model Context Protocol，模型上下文协议        |
| **YAML**        | 项目配置文件的格式                            |

## 附录 B: 参考文档

- AGENTS.md — Agent 详细定义与行为规范
- QUICKSTART.md — 快速开始指南（v1.3 阶段补充）
- docs/roadmap.md — 总路线图
- docs/changelog.md — 变更日志

## 附录 C: 变更记录

| 版本   | 日期    | 变更内容                   |
| ------ | ------- | -------------------------- |
| v1.0.0 | 2025-01 | 产品蓝图初始版本，设计冻结 |

---

*本文档为 Kimi Production-Grade Agent Pack 的设计蓝图，所有规格在 v1.0.0 版本冻结。后续变更需通过正式的变更请求流程。*
