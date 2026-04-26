# Recovery Runbook - 故障恢复手册

## 版本: v1.5

---

## 概述

本手册覆盖 E003-E018 常见失败的诊断和恢复步骤。每个条目包含：症状 → 诊断步骤 → 恢复操作 → 预防措施。

**使用方式**: 当 guided_run.py 报告错误时，查找对应的错误代码，按步骤执行恢复操作。

---

## 错误代码速查

| 代码 | 错误类型 | 严重程度 | 恢复难度 |
|------|---------|---------|---------|
| E003 | Schema validation failed | High | Medium |
| E004 | Structured output parse fail | High | Low |
| E005 | Hard fail detected | Critical | High |
| E006 | QA Gate blocked | High | Medium |
| E007 | Task event write failed | Medium | Low |
| E008 | Artifact validation failed | High | Medium |
| E009 | Coder sandbox timeout | Medium | Low |
| E010 | Resume state corrupted | High | Medium |
| E011 | Runner fallback exhausted | Medium | Medium |
| E012 | Evidence conflict unresolved | Medium | High |
| E013 | Writer fact check failed | Medium | Medium |
| E014 | Network search failed | Low | Low |
| E015 | Memory write rejected | Medium | Low |
| E016 | Plugin execution failed | Low | Low |
| E017 | Regression test failed | High | High |
| E018 | Release check strict failed | High | High |

---

## E003: Schema Validation Failed

### 症状
- `guided_run.py` 报告 schema validation error
- 产物 JSON 不符合预期结构
- 出现 `ValidationError` 或类似错误信息

### 诊断步骤

```powershell
# 1. 检查 schema 版本
python -c "import json; s=json.load(open('schemas/run-state.schema.json')); print(s.get('$id', 'unknown'))"

# 2. 验证产物 JSON 格式
try { Get-Content 'artifacts/<artifact>.json' | ConvertFrom-Json | Out-Null; Write-Output 'Valid JSON' } catch { Write-Output 'Invalid JSON' }

# 3. 对比 schema 要求
$expected = python -c \"import json; print(list(json.load(open('artifacts/<artifact>.json')).keys()))\"
$actual   = python -c \"import json; print(list(json.load(open('schemas/<schema>.json'))['properties'].keys()))\"
Compare-Object $expected $actual```

### 恢复操作

1. **检查 schema 版本**: 确认 schema 和产物版本匹配
2. **降级到宽松模式**: 如果 schema 过于严格，使用 `--strict false` 参数
3. **修复产物**: 根据 schema 要求手动或通过脚本修复 JSON
4. **重试**: `python scripts/guided_run.py --step <current-step>`

### 预防措施
- 使用 `check_report_quality.py` 提前验证
- 保持 schema 版本与代码版本同步
- 在关键步骤添加 schema 兼容性检查

---

## E004: Structured Output Parse Fail

### 症状
- Kimi 返回的内容无法解析为 JSON
- 出现 `JSONDecodeError` 或解析超时
- 结构化输出不完整或被截断

### 诊断步骤

```powershell
# 1. 运行 parser fixture suite 测试解析器
python scripts/test_structured_output_parser.py --verbose

# 2. 检查输入内容格式
python -c "
import sys
text = open(sys.argv[1]).read()
print(f'Length: {len(text)}')
print(f'Has json block: {chr(96)+chr(96)+chr(96)+'json' in text}')
print(f'Has braces: {text.count(chr(123))} open, {text.count(chr(125))} close')
" artifacts/<raw-output>.txt```

### 恢复操作

1. **切换正则提取**: 使用 `--parse-mode regex` 启用宽松解析
2. **人工辅助**: 手动从输出中提取 JSON 部分
3. **要求重新输出**: 将 prompt 复制回 Kimi，要求重新生成 JSON
4. **使用 fallback 模式**: `python scripts/test_structured_output_parser.py` 测试不同的解析策略

```powershell
# 使用正则提取
python -c "
import re, json
text = open('artifacts/<raw>.txt').read()
m = re.search(r'\{\{.*\}\}', text, re.DOTALL)
if m:
    data = json.loads(m.group())
    print(json.dumps(data, indent=2))
"```

### 预防措施
- 在 prompt 中明确指定 JSON 格式要求
- 使用 `structured_output 约束` 部分
- 运行 parser fixture suite 验证解析器稳定性

---

## E005: Hard Fail Detected

### 症状
- `guided_run.py` 报告 hard fail
- 某个 Agent 步骤完全失败，无有效输出
- hard-fail-report.json 被生成

### 诊断步骤

```powershell
# 1. 查看 hard fail 报告
Get-Content 'artifacts/hard-fail-report.json'
# 2. 定位失败的 Agent
python -c "
import json
data = json.load(open('artifacts/hard-fail-report.json'))
print(f'Failed step: {data.get(\"step\", \"unknown\")}')
print(f'Error: {data.get(\"error\", \"unknown\")}')
print(f'Agent: {data.get(\"agent\", \"unknown\")}')
"

# 3. 查看对应步骤的日志
Get-ChildItem -Path 'artifacts/*<step-name>*```'

### 恢复操作

1. **查看 hard-fail-report**: 了解失败原因
2. **定位问题 Agent**: 确定哪个步骤失败
3. **修复根因**: 根据错误类型采取对应措施
4. **从失败步骤重试**: `python scripts/guided_run.py --step <failed-step>`

```powershell
# 如果需要跳过当前步骤（不推荐）
# 1. 手动修复产物
# 2. 编辑 run-state.json 标记为完成（最后的手段）```

### 预防措施
- 每个步骤添加详细的错误处理
- 使用 `--validate-step` 提前校验
- 保持 prompt 的清晰和一致性

---

## E006: QA Gate Blocked

### 症状
- QA-Reviewer 步骤报告未通过
- `qa-review.json` 中 `gate_result` 为 "fail"
- 存在 blocking issues

### 诊断步骤

```powershell
# 1. 查看 QA 审查结果
Get-Content 'artifacts/qa-review.json'
# 2. 提取 blocking issues
python -c "
import json
data = json.load(open('artifacts/qa-review.json'))
for f in data.get('findings', []):
    if f.get('severity') in ('critical', 'major'):
        print(f'[{f[\"severity\"]}] {f[\"id\"]}: {f[\"description\"]}')
"

# 3. 查看报告质量评分
Get-Content 'artifacts/report-quality.json```'
### 恢复操作

1. **查看 qa-review.json**: 了解具体问题
2. **修复对应问题**: 根据 finding 的 recommendation 修复
3. **重新运行 QA**: `python scripts/guided_run.py --step qa-reviewer`

```powershell
# 常见修复：
# - 结构问题 → 补充缺失部分
# - 引用问题 → 修正引用格式
# - 事实错误 → 回退到 evidence-synthesis 或 researcher
# - 格式问题 → 修正格式后重试```

### 预防措施
- 运行 `check_report_quality.py` 预检
- 确保所有引用可追溯
- Writer 阶段遵循 prompt 模板

---

## E007: Task Event Write Failed

### 症状
- 无法写入 task-events.json 或 run-state.json
- 出现 `PermissionError` 或 `IOError`
- 磁盘空间不足警告

### 诊断步骤

```powershell
# 1. 检查磁盘空间
Get-Volume
# 2. 检查目录权限
Get-ChildItem -Path 'runtime/'

# 3. 测试写入
New-Item -Path 'runtime/test-write' -ItemType File
Remove-Item 'runtime/test-write'
Write-Output "Write OK"

### 恢复操作

1. **检查磁盘空间**: `Get-Volume`，清理不必要的文件
2. **检查权限**: `icacls 'runtime/' /grant Users:F` 修复权限
3. **切换内存缓冲**: 如果磁盘不可用，使用内存缓冲模式
4. **手动创建目录**: `New-Item -Path 'runtime/', 'artifacts/' -ItemType Directory -Force`

```powershell
# 快速修复
icacls 'runtime/' /grant Users:F
icacls 'artifacts/' /grant Users:F
Get-ChildItem 'runtime/*.json' | ForEach-Object { icacls $_.FullName /grant Users:F }
```

### 预防措施
- 定期检查磁盘空间
- 使用原子写入（temp file + rename）
- 添加写入前检查

---

## E008: Artifact Validation Failed

### 症状
- Smoke runner 校验产物失败
- 产物文件不存在或为空
- 产物内容不符合预期

### 诊断步骤

```powershell
# 1. 检查产物是否存在
Get-ChildItem -Path 'artifacts/'

# 2. 检查产物大小
find artifacts/ -type f -exec ls -la {} \;

# 3. 验证 JSON 格式（如果是 JSON 产物）
try { Get-Content 'artifacts/<artifact>.json' | ConvertFrom-Json | Out-Null; Write-Output 'Valid' } catch { Write-Output 'Invalid' }

# 4. 检查产物内容
(Get-Content 'artifacts/<artifact>.md').Length  # for markdown
(Get-Content 'artifacts/<artifact>.json').Length  # for json
```

### 恢复操作

1. **检查产物路径**: 确认文件保存在正确位置
2. **重新生成**: 重新执行当前步骤生成产物
3. **手动修复**: 如果内容有问题，手动修正后保存

```powershell
# 从当前步骤重新开始
python scripts/guided_run.py --step <current-step>```

### 预防措施
- 使用标准产物路径
- 保存后立即验证文件存在
- 添加文件大小检查

---

## E009: Coder Sandbox Timeout

### 症状
- 代码执行超时
- 复杂查询或测试运行时间过长
- Sandbox 资源限制

### 诊断步骤

```powershell
# 1. 检查超时设置
echo $TIMEOUT  # or whatever env var is used

# 2. 测试代码执行时间
time python -c "<test code>"

# 3. 检查资源使用
top  # or htop```

### 恢复操作

1. **增加超时时间**: 设置更长的 timeout
2. **简化测试**: 使用更简单的测试用例
3. **分批执行**: 将大任务拆分成小批次
4. **本地执行**: 在本地环境而非 sandbox 中运行

```powershell
# 增加超时
$env:AGENT_TIMEOUT=300  # 5 minutes
python scripts/guided_run.py --step <current-step>```

### 预防措施
- 设置合理的超时时间
- 优化代码性能
- 使用增量测试

---

## E010: Resume State Corrupted

### 症状
- run-state.json 无法解析
- 状态信息缺失或不一致
- Resume 后进入错误状态

### 诊断步骤

```powershell
# 1. 检查 run-state.json
python -m json.tool runtime/run-state.json > /dev/null && echo "Valid JSON" || echo "Corrupted"

# 2. 检查关键字段
python -c "
import json
try:
    data = json.load(open('runtime/run-state.json'))
    required = ['case_id', 'current_step', 'completed_steps', 'step_status']
    for k in required:
        print(f'{k}: {\"OK\" if k in data else \"MISSING\"} ')
except Exception as e:
    print(f'Error: {e}')
"

# 3. 备份当前状态
cp runtime/run-state.json runtime/run-state.json.bak.$((Get-Date -UFormat %s))```

### 恢复操作

1. **备份当前状态**: `cp runtime/run-state.json ...`
2. **重置 run-state**: `python scripts/guided_run.py --reset --confirm`
3. **从头执行**: 从第一步重新开始
4. **手动修复**（高级）: 编辑 JSON 修复特定字段

```powershell
# 重置并重新开始
python scripts/guided_run.py --reset --confirm
# 然后按正常流程执行```

### 预防措施
- 使用原子写入保存状态
- 定期备份 run-state.json
- 添加 JSON 格式验证

---

## E011: Runner Fallback Exhausted

### 症状
- 所有 fallback 策略都已尝试
- 自动化恢复全部失败
- 进入手动恢复模式

### 诊断步骤

```powershell
# 1. 查看 runner 日志
Get-Content 'artifacts/runner-log.json 2>/dev/null || echo "No runner log"'
# 2. 查看已尝试的 fallback
Select-String -Path '"fallback\|retry" artifacts/*.json 2>/dev/null' -Pattern '-i'
# 3. 检查 runner 状态
python scripts/guided_run.py --status```

### 恢复操作

1. **使用 manual runner**: 完全手动执行当前步骤
2. **绕过自动化**: 手动创建产物并保存
3. **更新状态**: 手动标记步骤完成

```powershell
# 手动执行步骤
# 1. 查看 docs/assisted-mode-prompts.md 中的对应 prompt
# 2. 复制到 Kimi Code 手动执行
# 3. 保存产物到 artifacts/
# 4. 更新 run-state.json（如需）```

### 预防措施
- 维护 fallback 链的完整性
- 每个 fallback 都有明确的触发条件
- 记录所有尝试的恢复操作

---

## E012: Evidence Conflict Unresolved

### 症状
- Evidence-synthesis 无法自动解决冲突
- 多个证据源给出矛盾结论
- conflict-resolution.md 标记为未解决

### 诊断步骤

```powershell
# 1. 查看冲突记录
Get-Content 'artifacts/conflict-resolution.md'
# 2. 提取冲突证据
python -c "
import json
data = json.load(open('artifacts/synthesis-report.json'))
for c in data.get('conflict_resolution', []):
    print(f'{c[\"conflict_id\"]}: {c[\"resolution\"]}')
"

# 3. 查看原始证据
Select-String -Path '5 -B 5 "矛盾\|conflict\|disagree" artifacts/evidence-map.json```' -Pattern '-A'
### 恢复操作

1. **人工裁决**: 由人工判断哪个证据更可靠
2. **补充研究**: 回退到 researcher 步骤收集更多证据
3. **标记不确定性**: 在报告中明确标注冲突未解决

```powershell
# 补充研究
python scripts/guided_run.py --step researcher

# 然后重新分析
python scripts/guided_run.py --step analyst```

### 预防措施
- 建立证据可信度评分标准
- 多来源交叉验证
- 早期识别潜在冲突

---

## E013: Writer Fact Check Failed

### 症状
- Writer 步骤中的事实与 evidence 不符
- QA 发现事实性错误
- 引用与证据内容不匹配

### 诊断步骤

```powershell
# 1. 对比报告和证据
python -c "
import json
evidence = json.load(open('artifacts/evidence-map.json'))
# Check if report citations match evidence
"

# 2. 查看 QA 发现
Select-String -Path '"fact\|incorrect\|wrong" artifacts/qa-review.json```' -Pattern '-i'
### 恢复操作

1. **回退到 evidence-synthesis**: 重新确认事实
2. **修正引用**: 确保引用与证据内容一致
3. **补充证据**: 如需要，回退到 researcher

```powershell
# 回退到 evidence-synthesis
python scripts/guided_run.py --step evidence-synthesis

# 修正后重新 writer
python scripts/guided_run.py --step writer```

### 预防措施
- 所有事实必须有证据支持
- 引用时核对证据原文
- QA 阶段重点检查事实

---

## E014: Network Search Failed

### 症状
- 网络搜索请求失败
- 超时或连接错误
- 搜索结果为空

### 诊断步骤

```powershell
# 1. 检查网络连接
ping -c 1 8.8.8.8

# 2. 检查 DNS
curl -I https://www.google.com

# 3. 检查代理设置
echo $HTTP_PROXY $http_proxy```

### 恢复操作

1. **使用缓存**: 使用之前搜索的缓存结果
2. **离线模式**: 切换到离线工作模式
3. **重试**: 等待网络恢复后重试

```powershell
# 使用缓存模式
$env:USE_CACHE=true
python scripts/guided_run.py --step researcher```

### 预防措施
- 保存搜索结果缓存
- 离线模式支持
- 网络健康检查

---

## E015: Memory Write Rejected

### 症状
- 无法写入记忆/上下文文件
- 权限不足
- 存储配额已满

### 诊断步骤

```powershell
# 1. 检查权限
Get-ChildItem -Path 'memory/ 2>/dev/null || ls -la .'

# 2. 检查配额
quota 2>/dev/null || echo "No quota system"

# 3. 测试写入
echo "test" > memory/test.txt 2>&1 && echo "OK" || echo "Failed"```

### 恢复操作

1. **检查权限**: `chmod` 修复文件权限
2. **记录到临时文件**: 使用 /tmp 或其他可写位置
3. **内存模式**: 仅在内存中维护状态

```powershell
# 使用临时目录
$env:MEMORY_DIR=/tmp/agent-memory
New-Item -Path '$MEMORY_DIR' -ItemType Directory -Force
python scripts/guided_run.py --step <current-step>```

### 预防措施
- 启动时检查写入权限
- 备用存储位置
- 定期清理旧数据

---

## E016: Plugin Execution Failed

### 症状
- 插件加载失败
- 插件运行时错误
- 插件返回异常结果

### 诊断步骤

```powershell
# 1. 查看插件列表
Get-ChildItem -Path 'plugins/'

# 2. 查看插件日志
Get-Content 'artifacts/plugin-log.json 2>/dev/null'
# 3. 测试插件导入
python -c "import <plugin_name>" 2>&1```

### 恢复操作

1. **禁用插件**: 在配置中禁用问题插件
2. **使用 fallback**: 使用内置功能替代插件
3. **更新插件**: 检查插件版本兼容性

```powershell
# 禁用插件
$env:DISABLE_PLUGINS=true
python scripts/guided_run.py --step <current-step>```

### 预防措施
- 插件版本管理
- 沙箱隔离
- Fallback 机制

---

## E017: Regression Test Failed

### 症状
- 回归测试未通过
- 新更改破坏了已有功能
- 与 baseline 不一致

### 诊断步骤

```powershell
# 1. 查看测试结果
Get-Content 'artifacts/regression-test-results.json 2>/dev/null'
# 2. 对比 baseline
diff artifacts/baseline/ artifacts/current/

# 3. 查看具体失败
Select-String -Path '"fail\|error\|regression" artifacts/*.json```' -Pattern '-i'
### 恢复操作

1. **对比 baseline**: 找出退化点
2. **定位更改**: 找出导致退化的具体更改
3. **回退或修复**: 回退更改或修复问题

```powershell
# 运行回归测试
python scripts/regression_test.py --compare-baseline

# 定位退化点
python scripts/regression_test.py --diff --show-changes```

### 预防措施
- 每次更改前运行回归测试
- 维护 baseline
- 增量测试

---

## E018: Release Check Strict Failed

### 症状
- release_check.py --strict 未通过
- 存在未解决的 strict 级别问题
- 不符合发布标准

### 诊断步骤

```powershell
# 1. 查看 release check 结果
Get-Content 'artifacts/release-check.json'
# 2. 列出 strict 失败项
Select-String -Path '"strict\|fail" artifacts/release-check.json' -Pattern '-i'
# 3. 逐项检查
python scripts/release_check.py --level l1 --strict```

### 恢复操作

1. **逐项修复**: 逐一解决每个 strict 失败项
2. **重新运行**: 修复后重新运行 release check
3. **记录例外**: 如果无法修复，记录原因和风险

```powershell
# 查看具体失败
python scripts/release_check.py --level l1 --strict --verbose

# 逐项修复后重新检查
python scripts/release_check.py --level l1 --strict```

### 预防措施
- 开发过程中持续运行 strict check
- 使用 pre-release checklist
- 自动化 CI 检查

---

## 通用恢复流程

```
1. 识别错误代码 (E003-E018)
        ↓
2. 查阅本手册对应条目
        ↓
3. 按诊断步骤执行
        ↓
4. 按恢复操作修复
        ↓
5. 验证修复结果
        ↓
6. 继续 guided_run.py 执行
        ↓
7. 如果仍失败，记录并升级
```

---

## 升级路径

如果上述恢复操作均无法解决问题：

1. 记录完整错误日志
2. 保存当前状态备份
3. 联系维护团队
4. 考虑使用 `--reset --confirm` 从头开始

---

## 附录：快捷命令

```powershell
# 查看状态
python scripts/guided_run.py --status

# 重置
python scripts/guided_run.py --reset --confirm

# 继续
python scripts/guided_run.py --resume

# 检查质量
python scripts/check_report_quality.py --report artifacts/final-report.md

# 运行 parser 测试
python scripts/test_structured_output_parser.py

# 历史审查
python scripts/repeatability_runner.py --historical-review```
