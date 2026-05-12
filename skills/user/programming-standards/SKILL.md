---
name: programming-standards
description: Use when writing, reviewing, or refactoring code and you need general programming standards for function design, single responsibility, concise functions, defensive validation, testability, and maintainable logic.
version: 1.0.0
author: Mengfei / Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [programming, code-quality, refactoring, single-responsibility, defensive-programming, testing]
    related_skills: []
---

# 通用编程规范

## Overview

本 Skill 用于约束通用代码设计、开发和评审质量。核心目标是让代码具备：职责清晰、函数简短、逻辑可测试、错误尽早暴露、易读易维护。

适用于大多数语言和项目，包括前端、后端、脚本、ArkTS、TypeScript、Python、Java、Go、C++ 等。

## When to Use

- 编写新功能、新模块或新脚本。
- 修改已有业务逻辑、工具函数或公共组件。
- 进行代码 Review、重构或质量检查。
- 需要把复杂逻辑拆分为更小、更可测试的单元。
- 需要定义开发需求的验收标准和代码质量标准。

Don't use for:

- 极短的一次性验证片段，且不会进入主项目代码。
- 项目已有更严格规范时，应优先遵循项目规范，本 Skill 作为补充。

## Core Principles

| 原则 | 要求 | 验收方式 |
|---|---|---|
| 单一职责 | 一个函数只做一件事，并把它做好 | 函数名能准确概括唯一职责 |
| 函数简短 | 通常不超过 50 行，过长函数应拆分 | 检查函数行数与逻辑分支数量 |
| 防御性编程 | 函数开始处检查参数有效性 | 无效输入能被明确拒绝或安全处理 |
| 可测试 | 复杂逻辑应可通过单元测试覆盖 | 有明确输入、输出、边界条件 |
| 低耦合 | 函数尽量少依赖全局状态和外部副作用 | 依赖通过参数或接口传入 |
| 高内聚 | 相关逻辑集中，不相关逻辑拆开 | 单个模块围绕一个稳定主题 |
| 尽早失败 | 不吞掉异常，不隐藏错误 | 错误信息明确，便于定位 |

## Function Design Rules

### 1. 单一职责原则

一个函数只做一件事，并把它做好。

推荐做法：

- 函数名描述动作和对象，例如 `validateUserInput`、`parseOrderRows`、`renderChart`。
- 如果函数名需要使用 `and` / `or`，通常说明职责过多。
- 将“校验、转换、计算、持久化、渲染、发送请求”等不同职责拆开。
- 让每个函数拥有明确输入和输出。

反例：

```ts
function handleOrder(data) {
  // 校验数据
  // 计算金额
  // 写数据库
  // 发送邮件
  // 更新 UI
}
```

推荐拆分：

```ts
function validateOrderInput(data) {}
function calculateOrderAmount(order) {}
function saveOrder(order) {}
function sendOrderNotification(order) {}
function updateOrderView(order) {}
```

### 2. 函数长度控制

函数应保持简短，通常不超过 50 行。超过 50 行时，应优先检查是否存在以下问题：

| 信号 | 处理方式 |
|---|---|
| 多层嵌套 | 使用早返回、拆分条件判断 |
| 多个业务阶段 | 按阶段拆分为独立函数 |
| 大量参数处理 | 提取参数校验函数或配置对象 |
| 重复代码 | 提取公共函数 |
| 同时处理 IO 和计算 | 分离副作用和纯逻辑 |

拆分目标不是机械减少行数，而是让每个函数职责更明确、测试更容易。

### 3. 防御性编程

在函数开始处检查参数有效性，避免无效数据导致程序崩溃或产生错误结果。

检查内容包括：

| 参数类型 | 检查示例 |
|---|---|
| 必填值 | 非 `null` / `undefined` / 空字符串 |
| 数字 | 是否为有限数、是否在合法范围 |
| 数组 | 是否为数组、是否允许为空 |
| 对象 | 必需字段是否存在、类型是否正确 |
| 枚举 | 是否属于允许值集合 |
| 路径/URL | 格式是否安全、是否为空 |

示例：

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

### 4. 控制复杂度

优先使用早返回减少嵌套：

```ts
function getUserName(user?: User): string {
  if (!user) return 'Guest';
  if (!user.profile) return 'Guest';
  if (!user.profile.name) return 'Guest';

  return user.profile.name;
}
```

避免深层嵌套：

```ts
// 不推荐：多层 if 嵌套，阅读和测试成本高
if (user) {
  if (user.profile) {
    if (user.profile.name) {
      return user.profile.name;
    }
  }
}
```

### 5. 分离纯逻辑与副作用

优先把核心业务规则写成纯函数，再由外层函数处理 IO、副作用和框架适配。

| 类型 | 示例 |
|---|---|
| 纯逻辑 | 计算金额、格式化数据、校验规则、筛选排序 |
| 副作用 | 网络请求、数据库读写、文件读写、UI 更新、日志打印 |

这样可以提升可测试性，并降低框架、环境变化对业务逻辑的影响。

## Testability Requirements

开发前先明确测试和验收标准：

1. 正常输入能得到预期输出。
2. 边界输入能被正确处理。
3. 无效输入能被明确拒绝或安全降级。
4. 异常路径有清晰错误信息。
5. 副作用逻辑可被 mock、stub 或隔离验证。

测试用例建议覆盖：

| 类型 | 示例 |
|---|---|
| 正常路径 | 合法参数、常规数据量 |
| 边界条件 | 空数组、0、最大值、最小值、单元素 |
| 异常输入 | null、undefined、错误类型、非法枚举 |
| 错误处理 | 网络失败、文件不存在、权限不足 |
| 回归场景 | 历史 Bug 对应测试 |

## Code Review Checklist

- [ ] 函数是否只做一件事。
- [ ] 函数名是否准确表达唯一职责。
- [ ] 函数通常是否不超过 50 行。
- [ ] 过长函数是否已拆分为更小单元。
- [ ] 函数开头是否检查关键参数有效性。
- [ ] 是否避免深层嵌套和复杂条件表达式。
- [ ] 是否分离纯逻辑和副作用。
- [ ] 是否避免重复代码和重复状态。
- [ ] 错误是否尽早暴露，而不是被静默吞掉。
- [ ] 是否有可执行测试或明确验证方法。

## Common Pitfalls

1. **函数名过于宽泛。** 如 `handleData`、`process`、`doWork`，通常意味着职责不清。
2. **一个函数串完整流程。** 校验、计算、保存、通知混在一起，难测试、难复用。
3. **机械限制 50 行。** 行数是信号，不是唯一目标；关键是职责单一和可读性。
4. **只在调用方校验参数。** 公共函数自身也应防御关键参数，避免被错误复用。
5. **吞掉异常。** `try/catch` 后不处理、不记录、不抛出，会隐藏真实问题。
6. **过度抽象。** 不要为了拆分而制造无意义层级；只抽取稳定、明确、可命名的逻辑。
7. **测试只覆盖正常路径。** 防御性编程必须配合异常输入和边界测试。

## Completion Response Standard

完成相关开发或重构后，结果回复应专业、简洁、明确，建议包含：

| 项目 | 内容 |
|---|---|
| 做了什么 | 简述实现或重构内容 |
| 改了哪里 | 列出关键文件或模块 |
| 如何验证 | 说明执行的测试或无法测试原因 |
| 风险/限制 | 说明剩余风险、兼容性或后续建议 |
