# M_Skills

## Scope

个人常用 Skills 收集仓库，记录和沉淀日常使用的工作流、脚本、配置模板。

## Mission

- 收集并整理可复用的专业 Skill。
- 每条 Skill 需包含：场景描述、前置条件、操作步骤、测试/验证方法、验收标准。
- 开发类需求默认遵循：先分析需求、先设计测试、再实现、最后验证。
- 脚本放在 `scripts/`，可复用配置模板放在 `templates/`。

## 目录

| 分类 | 目录 | 说明 |
|---|---|---|
| Git | `skills/git/` | Git 提交、推送、分支同步与协作自动化 |
| HarmonyOS | `skills/harmonyos/` | HarmonyOS / OpenHarmony 应用开发、性能优化、工程实践 |
| User | `skills/user/` | 用户通用 Skills，不限定具体技术栈，适合跨场景复用 |

## Skill 模板

```markdown
---
name: skill-name
description: Use when ...
version: 1.0.0
author: Mengfei / Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [tag1, tag2]
    related_skills: []
---

# Skill 标题

## Overview
说明 Skill 的目标和适用范围。

## When to Use
- 什么情况下使用。

## Steps
1. 明确需求和验收标准。
2. 设计测试和验证方法。
3. 实施最小可行修改。
4. 执行验证并记录结果。

## Verification Checklist
- [ ] 已完成测试。
- [ ] 已完成验收。
- [ ] 已记录风险和限制。

## Reference
相关链接。
```
