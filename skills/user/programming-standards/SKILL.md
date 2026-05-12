---
name: programming-standards
description: Use when writing, reviewing, or refactoring code and you need concise general programming standards for naming, function design, single responsibility, defensive validation, errors, logs, configuration, boundary cases, async handling, and testability.
version: 1.1.0
author: Mengfei / Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [programming, code-quality, refactoring, single-responsibility, defensive-programming, testing]
    related_skills: []
---

# 通用编程规范

## Overview

用于约束通用代码开发与 Review。目标：职责清晰、函数简短、边界明确、错误可定位、逻辑可测试、结果可维护。

适用于前端、后端、脚本、ArkTS、TypeScript、Python、Java、Go、C++ 等大多数项目。若项目已有更严格规范，优先遵循项目规范。

## Core Rules

| 规范 | 要求 |
|---|---|
| 单一职责 | 一个函数只做一件事；函数名能准确表达唯一职责。 |
| 函数长度 | 函数通常不超过 50 行；过长时按校验、转换、计算、IO、渲染等职责拆分。 |
| 防御性编程 | 函数开始处检查关键参数有效性，如空值、类型、范围、枚举、路径、URL。 |
| 命名 | 使用有业务含义的名称；避免 `data`、`info`、`temp`、`handle`、`process` 等泛化命名。 |
| 注释 | 注释解释“为什么”和业务背景，不重复代码“做了什么”。复杂规则必须说明来源或约束。 |
| 错误处理 | 不静默失败；错误信息要包含上下文，能帮助定位问题。 |
| 日志 | 日志要有级别和关键上下文；禁止输出 token、密码、身份证、手机号等敏感信息。 |
| 配置 | 魔法数字、环境差异、开关参数应提取为常量或配置，并命名清晰。 |
| 边界条件 | 明确处理空值、空数组、超大数据、重复请求、权限不足、资源不存在等情况。 |
| 异步/并发 | 明确超时、取消、重试、竞态、幂等策略，避免重复提交和状态覆盖。 |
| 依赖 | 避免隐式全局依赖；时间、随机数、IO、外部服务应可替换或可 mock。 |
| 安全 | 外部输入必须校验；涉及权限、文件路径、SQL/命令、HTML 时防注入。 |
| 可测试 | 复杂逻辑要有明确输入输出；副作用与纯逻辑尽量分离，便于单元测试。 |

## Function Checklist

写函数时按顺序检查：

1. **职责是否唯一**：是否只做一个动作，如校验、解析、计算、保存、渲染之一。
2. **参数是否防御**：入口是否检查必填值、类型、范围和非法枚举。
3. **逻辑是否简短**：是否超过 50 行，是否有多层嵌套或多个阶段。
4. **副作用是否隔离**：核心计算是否能独立测试，IO 是否放在外层。
5. **错误是否清楚**：失败时是否能知道哪个输入、哪个步骤、为什么失败。

推荐结构：

```ts
function calculateDiscount(price: number, rate: number): number {
  if (!Number.isFinite(price) || price < 0) {
    throw new Error('price must be a non-negative finite number');
  }
  if (!Number.isFinite(rate) || rate < 0 || rate > 1) {
    throw new Error('rate must be between 0 and 1');
  }
  return price * rate;
}
```

## Test Requirements

开发前先明确验证方式，至少覆盖：

| 类型 | 示例 |
|---|---|
| 正常路径 | 合法参数、常规数据量、主流程成功。 |
| 边界条件 | 空值、空数组、0、最大值、最小值、单元素。 |
| 异常输入 | 错误类型、非法枚举、越界数值、格式错误。 |
| 错误处理 | 网络失败、文件不存在、权限不足、外部服务异常。 |
| 并发异步 | 重复点击、重复请求、超时、取消、竞态、重试。 |

## Code Review Checklist

- [ ] 函数职责单一，通常不超过 50 行。
- [ ] 关键参数在函数入口完成有效性检查。
- [ ] 命名清晰，有业务含义，无泛化命名。
- [ ] 复杂规则有必要注释，说明原因和约束。
- [ ] 错误不会被吞掉，错误信息可定位。
- [ ] 日志不泄露敏感信息。
- [ ] 魔法值已提取为常量或配置。
- [ ] 已覆盖边界条件、异常输入和并发异步风险。
- [ ] 纯逻辑与副作用尽量分离，便于测试。
- [ ] 有可执行测试或明确验证方法。

## Common Pitfalls

1. **函数名宽泛**：`handleData`、`process` 往往意味着职责不清。
2. **函数过长**：超过 50 行通常说明混入多个阶段或副作用。
3. **只测正常路径**：边界、异常、并发问题才是高风险来源。
4. **吞异常**：`catch` 后不处理、不记录、不抛出会隐藏问题。
5. **过度抽象**：只抽取稳定、明确、可命名的逻辑，避免无意义层级。

## Completion Response Standard

完成开发或重构后，简洁说明：

| 项目 | 内容 |
|---|---|
| 做了什么 | 实现或重构内容 |
| 改了哪里 | 关键文件或模块 |
| 如何验证 | 执行的测试或无法测试原因 |
| 风险/限制 | 剩余风险、兼容性或后续建议 |
