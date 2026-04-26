# unit-smoke-004-coder

## test_title
Coder — Code Bug Fix with Test Verification

## test_objective
Verify that the coder agent can complete code bug fixes, provide the corrected code, and include verifiable test results. The output must contain actual code changes (not just descriptions), syntax-correct code, and a record of test execution.

## min_input
Bug 描述：

```python
# 函数 calculate_average 存在 bug：缺少对空列表的处理，且未返回值
def calculate_average(numbers):
    total = 0
    for n in numbers:
        total += n
    # BUG: 缺少 return 语句
    # BUG: 未处理空列表会导致 ZeroDivisionError

# 测试用例
print(calculate_average([1, 2, 3, 4, 5]))  # 期望: 3.0
print(calculate_average([]))                 # 期望: 0 或异常处理
```

任务：
1. 修复上述 bug
2. 为修复后的代码编写单元测试
3. 运行测试并记录结果
4. 输出代码变更说明和测试报告

## expected_structured_output

```json
{
  "task_id": "code-fix-calculate-average",
  "status": "completed",
  "conclusion": [
    "修复了 calculate_average 函数缺少 return 语句的 bug",
    "添加了空列表保护，空输入时返回 0.0",
    "编写了覆盖正常输入、空输入、单元素输入的单元测试",
    "所有测试通过"
  ],
  "artifacts": [
    {
      "type": "code",
      "path": "src/calculate_average.py",
      "description": "修复后的 calculate_average 函数"
    },
    {
      "type": "code",
      "path": "tests/test_calculate_average.py",
      "description": "单元测试文件"
    }
  ],
  "code_changes": [
    {
      "file": "src/calculate_average.py",
      "line": 6,
      "change_type": "add",
      "before": "    # (no return)",
      "after": "    if not numbers:\n        return 0.0\n    return total / len(numbers)",
      "reason": "修复缺少return的bug，并添加空列表保护"
    }
  ],
  "test_results": {
    "ran": true,
    "count": 3,
    "passed": 3,
    "failed": 0,
    "details": [
      {
        "test": "test_average_normal",
        "input": [1, 2, 3, 4, 5],
        "expected": 3.0,
        "actual": 3.0,
        "status": "passed"
      },
      {
        "test": "test_average_empty",
        "input": [],
        "expected": 0.0,
        "actual": 0.0,
        "status": "passed"
      },
      {
        "test": "test_average_single",
        "input": [42],
        "expected": 42.0,
        "actual": 42.0,
        "status": "passed"
      }
    ]
  }
}
```

Expected fields:
- `task_id` (string)
- `status` (string: "completed" | "in_progress" | "failed")
- `conclusion[]` (array of strings describing what was done)
- `artifacts[]` (array with `type:"code"`, `path`, `description`)
- `code_changes[]` (array with `file`, `line`, `change_type`, `before`, `after`, `reason`)
- `test_results` (object with `ran`, `count`, `passed`, `failed`, `details[]`)

## raw_output_requirements

1. Must include the fixed code block (not just a description of the fix).
2. Must include the test code block.
3. Must show actual test execution output (or a clear record of test runs).
4. Must explain the bug and the fix approach.
5. Must include the structured_output JSON block.

## hard_fail_conditions

1. 代码声称修复但未提供：conclusion 声称修复了 bug，但 code_changes 为空或 artifacts 中没有代码。
2. 有语法错误：提供的代码中存在明显的 Python 语法错误（如缩进错误、缺少冒号、括号不匹配）。
3. 声称测试通过但无测试记录：test_results.passed > 0 但 test_results.ran = false 或 test_results.details 为空。

## acceptance_criteria

- [ ] `task_id` 非空
- [ ] `status` 为 completed 或 failed
- [ ] `conclusion[]` 描述修复了什么
- [ ] `artifacts[]` 至少包含一个 type 为 "code" 的条目
- [ ] `code_changes[]` 非空，每条变更都有 `before`, `after`, `reason`
- [ ] `test_results` 包含 `ran`, `count`, `passed`, `failed`
- [ ] 如果 `passed` > 0，则 `ran` 必须为 true
- [ ] `test_results.details[]` 包含至少一条测试详情
- [ ] 提供的代码无语法错误
- [ ] 代码变更确实修复了描述的 bug

## technical_assumptions

- 目标语言为 Python 3.10+
- 代码修复应遵循最小变更原则，只做必要的修改
- 单元测试使用标准库 `unittest` 或 `pytest` 均可
- 如果无法运行测试（无执行环境），test_results.ran 应为 false，且需说明原因

## failure_fallback

If the coder agent fails:
1. Return `status: "failed"` with empty code_changes array.
2. Record `failure_reason` (e.g., "unable to parse source code", "syntax error in generated fix").
3. QA reviewer should flag the failure for human intervention.
4. Log error code `E004_CODE_FIX_FAIL` to errors.jsonl.
