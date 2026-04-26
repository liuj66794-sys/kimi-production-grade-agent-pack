---
name: skill-specification-format
version: "1.0.0"
description: Top-level skill specification format for the Kimi Agent Pack
---

# Skill Specification Format

This document defines the standard format for all skill specifications in the Kimi Agent Pack.

## File Location

Each skill is defined in its own directory under `skills/<skill-name>/` with a primary `SKILL.md` file.

## Required Structure

Every `SKILL.md` must contain:

1. **YAML Frontmatter** — Metadata enclosed between `---` delimiters:
   - `name` — Unique skill identifier (kebab-case)
   - `version` — SemVer version string
   - `description` — Short human-readable description
   - `type` — Always `skill`

2. **Purpose (目的)** — What this skill does and its responsibilities

3. **Trigger Conditions (触发条件)** — When this skill should be invoked

4. **Inputs (输入)** — Expected input data and parameters

5. **Outputs (输出)** — Expected output format and deliverables

6. **Workflow (工作流)** — Step-by-step execution flow

7. **Hard Fail Conditions** — Conditions that must cause immediate termination

8. **Out of Scope (不负责)** — Boundaries of this skill's responsibility

9. **Output Contract (输出契约)** — Validation rules for output quality

10. **Resource Index (资源索引)** — Links to related schemas, examples, and references

## Example

```yaml
---
name: example-skill
version: "1.0.0"
description: An example skill demonstrating the standard format
type: skill
---

# Example Skill

## 目的
Demonstrate the skill specification format.

## 触发条件
- When the orchestrator assigns a matching task

## 输入
- Task description
- Context data

## 输出
- Structured result document

## 工作流
1. Validate inputs
2. Execute core logic
3. Validate outputs
4. Return result

## Hard Fail Conditions
- Missing required inputs
- Validation failures

## 不负责
- Tasks outside the defined scope

## 输出契约
- Output must be valid JSON
- All required fields present

## 资源索引
- `schemas/task-event.json`
- `examples/example-skill/`
```

## Validation

All skill specifications are validated by `scripts/release_check.py` for:
- Presence of YAML frontmatter
- Required frontmatter keys (`name`, `version`)
- Valid JSON schemas in referenced files
