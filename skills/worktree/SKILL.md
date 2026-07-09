---
name: worktree
description: Use when starting an isolated development task with Git worktree, creating a dedicated task branch and separate working directory so the main project branch stays clean and testable.
version: 1.0.0
author: Mengfei / Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [git, worktree, branch, isolated-development, test-first]
    related_skills: [apply-worktree, auto-commit-push]
---

# Worktree

## Overview

本 Skill 用于在主项目之外创建独立的 Git worktree，用专用分支完成一个需求、修复或实验。目标是让开发过程具备以下特性：

- 主项目分支保持干净；
- 每个需求对应独立目录和独立分支；
- 支持先写测试、再实现；
- 支持并行开发多个需求；
- 完成后可通过 `apply-worktree` 回合并到主项目分支并清理。

## When to Use

- 需要开始一个明确的开发需求、Bug 修复或重构任务。
- 主分支已有稳定状态，不希望开发过程污染当前工作区。
- 需要并行推进多个需求，避免频繁切分支。
- 需要保留主项目可随时运行、测试或发布。

Don't use for:

- 非 Git 仓库。
- 只读查看文件，不会产生开发改动。
- 当前主项目工作区存在未处理改动，且无法判断是否属于当前任务。
- 需要直接在当前分支快速修改且用户明确要求不创建 worktree。

## Requirement Analysis

创建 worktree 前，先明确需求边界：

| 项目 | 要求 |
|---|---|
| 需求目标 | 明确要完成的业务能力、修复点或验证目标 |
| 验收标准 | 明确哪些测试、页面、命令或行为证明需求完成 |
| 影响范围 | 明确涉及模块、接口、数据、配置或文档 |
| 分支命名 | 使用可读、可追踪的任务分支名 |
| 回合并策略 | 默认由 `apply-worktree` 统一合并、清理 |

## Naming Convention

推荐命名：

| 类型 | 分支名示例 | worktree 目录示例 |
|---|---|---|
| 功能 | `feat/login-cache` | `../repo.worktrees/feat-login-cache` |
| 修复 | `fix/startup-crash` | `../repo.worktrees/fix-startup-crash` |
| 重构 | `refactor/state-model` | `../repo.worktrees/refactor-state-model` |
| 实验 | `spike/render-trace` | `../repo.worktrees/spike-render-trace` |

目录名应避免 `/`，可将分支名中的 `/` 替换为 `-`。

## Required Workflow

### 1. 检查主项目状态

在主项目根目录执行：

```bash
git rev-parse --show-toplevel
git branch --show-current
git status --short
git remote -v
git log --oneline -5
```

要求：

- 确认当前位于目标主项目；
- 确认当前分支是要基于的主分支；
- 工作区如果存在无关改动，先暂停并让用户确认；
- 不自动提交或覆盖用户未确认的改动。

### 2. 同步基线分支

如果存在远程分支，先同步基线：

```bash
BASE_BRANCH="$(git branch --show-current)"
REMOTE="origin"

git fetch "$REMOTE"
git pull --ff-only "$REMOTE" "$BASE_BRANCH"
```

如果没有远程或用户明确要求离线开发，可以跳过 pull，但需要记录该限制。

### 3. 创建任务分支和 worktree

```bash
TASK_BRANCH="feat/example-task"
WORKTREE_ROOT="../$(basename "$(git rev-parse --show-toplevel)").worktrees"
WORKTREE_DIR="$WORKTREE_ROOT/${TASK_BRANCH//\//-}"

mkdir -p "$WORKTREE_ROOT"
git worktree add -b "$TASK_BRANCH" "$WORKTREE_DIR" "$BASE_BRANCH"
```

创建后进入 worktree：

```bash
cd "$WORKTREE_DIR"
git status --short
git branch --show-current
```

### 4. 在 worktree 中测试优先开发

开发需求默认遵循：

1. 明确验收标准；
2. 先补充或设计失败测试；
3. 实现最小可行修改；
4. 运行相关测试；
5. 更新必要文档；
6. 提交 worktree 分支变更。

建议命令：

```bash
# 按项目实际技术栈选择
npm test
pnpm test
pytest
cargo test
go test ./...
```

### 5. 提交 worktree 分支

```bash
git status --short
git diff
git add <当前需求相关文件>
git diff --cached
git commit -m "feat: concise task intent"
```

提交完成后，该 worktree 可交给 `apply-worktree` 合并回主项目。

## Safety Rules

| 规则 | 要求 |
|---|---|
| 不污染主项目 | 开发修改必须发生在 worktree 目录中 |
| 不隐藏未提交改动 | 主项目有未确认改动时暂停 |
| 不复用混乱分支 | 每个需求使用独立任务分支 |
| 不自动强推 | 本流程不需要强推 |
| 不提交无关文件 | 仅提交当前需求相关文件 |
| 测试优先 | 能写测试则先写测试，至少要有可复现验证命令 |

## One-Shot Recipe

```bash
# 在主项目根目录执行
BASE_BRANCH="$(git branch --show-current)"
TASK_BRANCH="feat/example-task"
REMOTE="origin"
ROOT="$(git rev-parse --show-toplevel)"
WORKTREE_ROOT="$(dirname "$ROOT")/$(basename "$ROOT").worktrees"
WORKTREE_DIR="$WORKTREE_ROOT/${TASK_BRANCH//\//-}"

git status --short
git fetch "$REMOTE"
git pull --ff-only "$REMOTE" "$BASE_BRANCH"
mkdir -p "$WORKTREE_ROOT"
git worktree add -b "$TASK_BRANCH" "$WORKTREE_DIR" "$BASE_BRANCH"
cd "$WORKTREE_DIR"
git status --short
```

## Common Pitfalls

1. **主项目有未提交改动仍创建 worktree。** 会让需求边界不清，应先处理或确认这些改动。
2. **worktree 目录建在仓库内部。** 容易被项目工具扫描或误提交，建议放在同级 `.worktrees` 目录。
3. **多个需求共用一个分支。** 会导致合并和回滚困难，一个需求一个分支。
4. **只开发不测试。** worktree 仍要执行项目相关测试，不能因为隔离目录就跳过验证。
5. **忘记提交 worktree 改动。** `apply-worktree` 合并前应确认任务分支包含完整提交。
6. **手动删除 worktree 目录。** 应优先使用 `git worktree remove`，避免 Git 元数据残留。

## Verification Checklist

- [ ] 已确认主项目根目录和基线分支。
- [ ] 已检查主项目 `git status --short`。
- [ ] 已同步远程基线分支，或明确记录跳过原因。
- [ ] 已创建独立任务分支。
- [ ] 已创建独立 worktree 目录。
- [ ] 已确认当前目录位于新 worktree。
- [ ] 已按测试优先方式开发或记录无法自动测试的原因。
- [ ] 已提交任务分支改动。
- [ ] 已准备交给 `apply-worktree` 合并和清理。
