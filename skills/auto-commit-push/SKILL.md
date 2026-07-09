---
name: auto-commit-push
description: Use when safely committing current task-related Git changes and pushing them to a remote branch, with automatic fetch/divergence detection, rebase-before-push handling, and explicit conflict stop-and-report behavior.
version: 1.0.0
author: Mengfei / Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [git, commit, push, rebase, automation, safety]
    related_skills: []
---

# Auto Commit Push

## Overview

自动安全提交代码并推送到远程仓库。该流程强调**先审查、再暂存、再提交、再安全推送**，避免无关改动、敏感信息或临时文件被提交。

推送前会先获取远程分支状态，并判断本地与远程的关系：

| 状态 | 处理方式 |
|---|---|
| 本地与远程一致 | 无需推送 |
| 本地落后远程 | 使用 `git pull --ff-only` 快进 |
| 本地领先远程 | 直接推送 |
| 本地与远程分叉 | 先 `git rebase`，成功后再推送 |

若 rebase 发生冲突，流程必须暂停，输出冲突文件列表，等待人工解决，绝不猜测冲突解决方案。

## When to Use

- 需要快速提交当前任务相关改动并推送到远程仓库。
- 团队协作中，推送前需要自动处理远程新增提交导致的分叉。
- 需要作为脚本、hook 或自动化工作流的提交入口。
- 希望统一提交前检查、提交信息风格与安全推送流程。

Don't use for:

- 当前工作树混有多个无关任务且无法明确提交范围。
- 仓库包含未确认的 secrets、密钥、凭据或大文件。
- rebase 冲突需要业务判断但无人处理。
- 需要强推、覆盖远程历史或改写共享分支历史的场景。

## Required Inputs

| 输入 | 默认值 | 说明 |
|---|---|---|
| commit message | 自动按仓库风格生成或由用户指定 | 应聚焦意图，不写文件清单 |
| branch | 当前分支 | 可用 `AUTO_COMMIT_PUSH_BRANCH` 覆盖 |
| remote | `origin` | 可用 `AUTO_COMMIT_PUSH_REMOTE` 覆盖 |
| mode | commit + push | `--push-only` 表示仅推送已提交内容 |

## Required Workflow

### 1. 安全提交

提交前必须完成以下检查：

1. 检查提交范围：

   ```bash
   git status --short
   ```

2. 审查未暂存变更：

   ```bash
   git diff
   ```

3. 审查已暂存变更：

   ```bash
   git diff --cached
   ```

4. 参考最近提交风格：

   ```bash
   git log --oneline -5
   ```

5. 仅暂存与当前任务直接相关的文件：

   ```bash
   git add <相关文件>
   ```

6. 提交前再次审查 staged diff：

   ```bash
   git diff --cached
   ```

7. 使用符合仓库风格的提交信息：

   ```bash
   git commit -m "feat: concise intent"
   ```

8. 提交后确认工作树状态：

   ```bash
   git status --short
   ```

### 2. 安全推送

默认目标：当前分支 + `origin`。可通过环境变量覆盖：

```bash
BRANCH="${AUTO_COMMIT_PUSH_BRANCH:-$(git branch --show-current)}"
REMOTE="${AUTO_COMMIT_PUSH_REMOTE:-origin}"
```

推送流程：

```bash
git fetch "$REMOTE" "$BRANCH"

LOCAL=$(git rev-parse HEAD)
REMOTE_HEAD=$(git rev-parse "$REMOTE/$BRANCH")
BASE=$(git merge-base HEAD "$REMOTE/$BRANCH")

if [ "$LOCAL" = "$REMOTE_HEAD" ]; then
    echo "已是最新，无需推送"
elif [ "$LOCAL" = "$BASE" ]; then
    echo "本地落后远程，执行快进更新"
    git pull --ff-only "$REMOTE" "$BRANCH"
elif [ "$REMOTE_HEAD" = "$BASE" ]; then
    echo "本地领先远程，执行推送"
    git push "$REMOTE" "$BRANCH"
else
    echo "检测到远程有新提交，先 rebase..."
    git rebase "$REMOTE/$BRANCH"
    git push "$REMOTE" "$BRANCH"
fi
```

### 3. 冲突处理

若 rebase 过程中出现冲突：

1. **立即暂停**，不自动解决复杂冲突。
2. 输出冲突文件列表：

   ```bash
   git diff --name-only --diff-filter=U
   ```

3. 明确提示用户手动解决冲突。
4. 用户解决后执行：

   ```bash
   git rebase --continue
   ```

5. rebase 成功后再次执行安全推送流程。

## Safety Rules

| 规则 | 要求 |
|---|---|
| 禁止强推 | 绝不使用 `git push --force` 或 `git push --force-with-lease` |
| 不猜冲突 | rebase 失败时停止并报告，不自动合并复杂冲突 |
| 控制范围 | 只提交当前任务相关文件 |
| 保护敏感信息 | 不提交 secrets、密钥、token、`.env`、临时产物 |
| 保留用户改动 | 发现无关改动混杂时停止并询问用户 |
| 提交信息专业 | 聚焦改动意图，如 `feat:` / `fix:` / `refactor:` / `docs:` |

## Recommended Script Behavior

### CLI Examples

```bash
# 一键提交并推送当前分支
auto-commit-push

# 指定提交信息
auto-commit-push "fix: resolve login timing issue"

# 仅推送，不创建新提交
auto-commit-push --push-only
```

### Pseudocode

```bash
#!/usr/bin/env bash
set -euo pipefail

REMOTE="${AUTO_COMMIT_PUSH_REMOTE:-origin}"
BRANCH="${AUTO_COMMIT_PUSH_BRANCH:-$(git branch --show-current)}"
MESSAGE="${1:-}"

if [ -z "$BRANCH" ]; then
  echo "当前不在有效分支上，停止。"
  exit 1
fi

if [ "${1:-}" != "--push-only" ]; then
  git status --short
  git diff
  git diff --cached
  git log --oneline -5

  # 调用方必须在这里选择任务相关文件，避免 git add . 误提交无关内容。
  # git add <相关文件>

  git diff --cached

  if git diff --cached --quiet; then
    echo "没有已暂存改动，跳过提交。"
  else
    git commit -m "${MESSAGE:-chore: update task changes}"
  fi
fi

git fetch "$REMOTE" "$BRANCH"
LOCAL=$(git rev-parse HEAD)
REMOTE_HEAD=$(git rev-parse "$REMOTE/$BRANCH")
BASE=$(git merge-base HEAD "$REMOTE/$BRANCH")

if [ "$LOCAL" = "$REMOTE_HEAD" ]; then
  echo "已是最新，无需推送"
elif [ "$LOCAL" = "$BASE" ]; then
  git pull --ff-only "$REMOTE" "$BRANCH"
elif [ "$REMOTE_HEAD" = "$BASE" ]; then
  git push "$REMOTE" "$BRANCH"
else
  if ! git rebase "$REMOTE/$BRANCH"; then
    echo "rebase 发生冲突，请手动解决以下文件："
    git diff --name-only --diff-filter=U
    echo "解决后执行：git rebase --continue，然后再次运行 auto-commit-push --push-only"
    exit 1
  fi
  git push "$REMOTE" "$BRANCH"
fi
```

## Test Plan

| 测试场景 | 构造方式 | 预期结果 |
|---|---|---|
| 无改动 | 干净工作树运行 | 不创建提交；推送流程正常判断 |
| 本地领先 | 本地有新提交，远程无新增 | 直接 `git push` |
| 本地落后 | 远程有新增，本地无新增 | `git pull --ff-only` |
| 本地远程分叉且无冲突 | 双方修改不同文件 | `git rebase` 成功后推送 |
| 本地远程分叉且冲突 | 双方修改同一行 | 停止并输出冲突文件 |
| 混合改动 | 工作树存在无关文件 | 停止并要求确认提交范围 |
| secrets 文件 | 存在 `.env` / token | 不暂存并报告风险 |

## Verification Checklist

- [ ] 已查看 `git status --short`，确认提交范围。
- [ ] 已审查 `git diff` 与 `git diff --cached`。
- [ ] 已参考 `git log --oneline -5` 的提交风格。
- [ ] 只暂存当前任务相关文件。
- [ ] 未提交 secrets、临时文件、构建产物或无关改动。
- [ ] 提交信息符合仓库风格并聚焦意图。
- [ ] 推送前已执行 `git fetch`。
- [ ] 已判断本地与远程是否一致、领先、落后或分叉。
- [ ] 分叉时优先 rebase，成功后再推送。
- [ ] rebase 冲突时已停止并输出冲突文件列表。
- [ ] 未使用任何强推命令。

## Common Pitfalls

1. **直接 `git add .`。** 容易提交无关改动、临时文件或 secrets；必须按任务范围选择文件。
2. **未看 diff 就提交。** 会把调试代码、日志或半成品一起提交。
3. **提交信息写文件列表。** 应描述意图，例如 `fix: handle empty login token`，而不是 `update files`。
4. **远程分叉时直接 merge。** 该流程要求先 rebase，保持历史线性。
5. **rebase 冲突自动乱改。** 冲突涉及业务语义，必须暂停并由用户确认。
6. **使用强推。** 本 Skill 明确禁止强推，避免覆盖他人提交。
7. **忽略 push-only 场景。** 已经提交过时应只执行安全推送，不应创建空提交。

## Notes

- 默认使用当前分支名作为推送目标。
- 环境变量 `AUTO_COMMIT_PUSH_BRANCH` 可覆盖目标分支。
- 环境变量 `AUTO_COMMIT_PUSH_REMOTE` 默认 `origin`。
- 当前 Skill 定义的是安全流程；如果落地为真实脚本，应配套增加本地临时仓库测试，覆盖领先、落后、分叉和冲突场景。
