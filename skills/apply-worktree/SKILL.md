---
name: apply-worktree
description: Use when merging completed Git worktree development back into the main project branch, validating the result, then safely removing the worktree directory and deleting the completed worktree branch.
version: 1.0.0
author: Mengfei / Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [git, worktree, merge, cleanup, branch, validation]
    related_skills: [worktree, auto-commit-push]
---

# Apply Worktree

## Overview

本 Skill 用于把 Git worktree 中完成的开发内容回合并到主项目分支。流程包括：检查 worktree 状态、确认任务分支提交完整、切回主项目分支、同步远程基线、合并任务分支、运行验证、清理 worktree，并删除任务分支。

核心目标：

- 合并前确认 worktree 内容已提交且可验证；
- 合并时保护主项目分支和用户未提交改动；
- 合并后执行测试或验收命令；
- 合并成功后清理 worktree 和任务分支；
- 遇到冲突或测试失败时暂停，不擅自删除 worktree。

## When to Use

- 一个通过 `worktree` 创建的任务分支已经开发完成。
- 需要把 worktree 中的提交合并回主项目主分支。
- 合并完成后需要自动清理 worktree 目录和任务分支。
- 需要在合并前后执行专业验证，确保主项目可用。

Don't use for:

- worktree 中仍有未提交改动且用户未确认。
- 任务分支测试失败或未执行关键验证。
- 合并存在冲突且需要业务判断。
- 任务分支尚需保留用于后续开发、Code Review 或远程协作。

## Required Inputs

| 输入 | 说明 |
|---|---|
| main project path | 主项目目录，即最终要合并到的仓库工作区 |
| worktree path | 任务 worktree 目录 |
| task branch | worktree 使用的任务分支 |
| target branch | 主项目目标分支，默认当前主项目分支 |
| validation command | 合并后需要运行的测试或验收命令 |

## Pre-Merge Checklist

### 1. 检查 worktree 状态

在 worktree 目录执行：

```bash
git rev-parse --show-toplevel
git branch --show-current
git status --short
git log --oneline -5
```

要求：

- 当前分支是任务分支；
- 工作区干净，或仅存在用户明确允许的未提交改动；
- 任务分支至少包含本次需求提交；
- 测试已执行，或记录未执行原因。

如果 worktree 有未提交改动，默认处理：

```bash
git status --short
git diff
git diff --cached
```

然后暂停，让用户决定是否提交、丢弃或继续开发。

### 2. 检查主项目状态

在主项目目录执行：

```bash
git branch --show-current
git status --short
git remote -v
git log --oneline -5
```

要求：

- 主项目工作区干净；
- 当前分支是目标合并分支；
- 如有远程，先同步目标分支。

```bash
TARGET_BRANCH="$(git branch --show-current)"
REMOTE="origin"

git fetch "$REMOTE"
git pull --ff-only "$REMOTE" "$TARGET_BRANCH"
```

若主项目存在未提交改动，必须暂停，不能覆盖或混合合并。

## Merge Workflow

### 1. 确认任务分支可被主项目识别

```bash
git worktree list
git branch --list
```

如果任务分支只存在于 worktree 中，主项目仍可直接合并该本地分支。

### 2. 合并任务分支

默认使用非快进合并，保留需求边界：

```bash
TASK_BRANCH="feat/example-task"
git merge --no-ff "$TASK_BRANCH" -m "merge: apply $TASK_BRANCH"
```

如果仓库偏好线性历史，也可以使用 rebase/fast-forward 策略，但必须遵循项目约定。

### 3. 冲突处理

如果合并冲突：

1. 立即暂停；
2. 输出冲突文件：

   ```bash
   git diff --name-only --diff-filter=U
   ```

3. 不清理 worktree；
4. 不删除任务分支；
5. 等待用户解决冲突并完成合并。

可取消合并：

```bash
git merge --abort
```

## Post-Merge Validation

合并成功后必须执行验证，命令按项目技术栈选择：

```bash
npm test
pnpm test
pytest
cargo test
go test ./...
```

验证结果处理：

| 结果 | 处理 |
|---|---|
| 通过 | 进入清理阶段 |
| 失败 | 暂停，保留 worktree 和任务分支，报告失败命令与错误摘要 |
| 无法自动验证 | 明确说明原因，并提供人工验收清单 |

## Cleanup Workflow

只有在**合并成功且验证通过**后，才允许清理。

### 1. 删除 worktree

```bash
WORKTREE_PATH="../repo.worktrees/feat-example-task"
git worktree remove "$WORKTREE_PATH"
```

如果目录已不存在或元数据异常：

```bash
git worktree prune
```

### 2. 删除任务分支

确认任务分支已合并：

```bash
git branch --merged | grep "TASK_BRANCH"
```

删除本地任务分支：

```bash
git branch -d "$TASK_BRANCH"
```

如果任务分支曾推送远程，且用户明确要求删除远程分支：

```bash
git push origin --delete "$TASK_BRANCH"
```

默认不删除远程分支，除非用户明确确认。

### 3. 最终确认

```bash
git status --short
git worktree list
git branch --list
```

## Safety Rules

| 规则 | 要求 |
|---|---|
| 合并前不清理 | 未合并或未验证通过时，不删除 worktree 和分支 |
| 冲突不猜测 | 冲突时停止并报告，不自动解决业务冲突 |
| 测试失败不清理 | 验证失败保留现场，便于修复 |
| 不覆盖用户改动 | 主项目或 worktree 有未确认改动时暂停 |
| 默认不删远程分支 | 删除远程分支必须用户明确要求 |
| 禁止强推 | 不使用 `push --force` 或 `--force-with-lease` |

## One-Shot Recipe

```bash
# 在主项目目录执行
TARGET_BRANCH="$(git branch --show-current)"
TASK_BRANCH="feat/example-task"
WORKTREE_PATH="../repo.worktrees/feat-example-task"
REMOTE="origin"

# 1. 检查 worktree
cd "$WORKTREE_PATH"
git status --short
git branch --show-current

# 2. 回到主项目并同步目标分支
cd -
git status --short
git fetch "$REMOTE"
git pull --ff-only "$REMOTE" "$TARGET_BRANCH"

# 3. 合并任务分支
git merge --no-ff "$TASK_BRANCH" -m "merge: apply $TASK_BRANCH"

# 4. 运行项目测试
# 替换为项目真实命令
npm test

# 5. 清理 worktree 和本地任务分支
git worktree remove "$WORKTREE_PATH"
git branch -d "$TASK_BRANCH"

git status --short
git worktree list
```

## Common Pitfalls

1. **worktree 未提交就合并。** 主项目只能合并提交，未提交改动不会自动进入目标分支。
2. **合并后未测试就清理。** 一旦清理，现场消失，失败定位成本增加。
3. **冲突后继续清理。** 冲突时必须保留 worktree 和任务分支。
4. **主项目有未提交改动仍合并。** 会混淆合并结果，必须先处理主项目工作区。
5. **误删远程分支。** 默认只删除本地任务分支，远程删除需明确确认。
6. **使用 `rm -rf` 删除 worktree。** 应使用 `git worktree remove`，必要时再 `git worktree prune`。
7. **删除未合并分支。** 使用 `git branch -d` 而不是 `-D`，让 Git 阻止未合并分支被删除。

## Verification Checklist

- [ ] 已确认 worktree 路径、任务分支、主项目路径和目标分支。
- [ ] worktree 工作区干净，任务提交完整。
- [ ] 主项目工作区干净。
- [ ] 已同步目标分支远程最新状态，或记录跳过原因。
- [ ] 已合并任务分支到目标分支。
- [ ] 合并无冲突；如有冲突，已暂停并报告。
- [ ] 已运行项目验证命令。
- [ ] 验证通过后才执行清理。
- [ ] 已使用 `git worktree remove` 删除 worktree。
- [ ] 已使用 `git branch -d` 删除本地任务分支。
- [ ] 已确认 `git status --short` 干净。
- [ ] 已确认 `git worktree list` 不再包含已清理 worktree。
