---
name: github-search
description: Use when searching GitHub repositories, code, issues, pull requests, or commits through GitHub CLI `gh search` with safe query construction, filters, JSON fields, and result triage.
version: 1.0.0
author: Mengfei / Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [github, gh, search, repositories, code, issues, pull-requests, commits]
    related_skills: []
---

# GitHub Search

## Overview

本 Skill 用于通过 GitHub CLI `gh search` 搜索 GitHub 上的仓库、代码、Issue、Pull Request 和 Commit。目标是快速构造正确查询，优先返回可引用、可筛选、可复现的结果，而不是在浏览器中手动试错。

核心命令族：

```bash
gh search repos <query> [flags]
gh search code <query> [flags]
gh search issues <query> [flags]
gh search prs <query> [flags]
gh search commits <query> [flags]
```

## When to Use

- 需要在 GitHub 上查找项目、库、示例实现或竞品仓库。
- 需要搜索公开或有权限访问的代码片段、文件名、路径或语言实现。
- 需要查找某个 Bug、报错、Issue、PR 或 Commit 历史。
- 需要用 `gh` 获取结构化 JSON 结果，供后续筛选、引用或自动化处理。

Don't use for:

- 当前本地仓库内部搜索；本地代码搜索应使用仓库搜索工具。
- 需要浏览网页 UI、截图或交互式 GitHub 页面时。
- 没有安装或未认证 `gh`，且任务依赖私有仓库结果时；先完成 `gh auth status` / `gh auth login`。
- 大规模抓取或绕过 GitHub rate limit 的任务。

## Required Checks

搜索前先确认：

```bash
gh --version
gh auth status
```

如果只搜索公开内容，`gh auth status` 失败不一定阻断；如果搜索私有仓库、组织内部内容或需要更高 rate limit，应先登录。

## Search Target Selection

| 目标 | 命令 | 常用场景 |
|---|---|---|
| 仓库 | `gh search repos` | 找项目、库、topic、语言、stars、维护状态 |
| 代码 | `gh search code` | 找 API 用法、文件名、路径、具体符号或报错字符串 |
| Issue | `gh search issues` | 找 Bug、报错、需求讨论、状态和标签 |
| PR | `gh search prs` | 找修复方案、迁移代码、review 讨论、已合并实现 |
| Commit | `gh search commits` | 找某个变更何时引入、hash、作者、提交信息 |

## Query Construction Rules

1. 先选搜索目标，再选过滤器；不要把所有条件塞进一个自由文本字符串。
2. 精确短语用引号：`"error handling"`。
3. 原始 GitHub search qualifier 可以直接作为参数：`topic:github`、`stars:>5000`、`path:pkg`。
4. 排除型 qualifier 以 `-` 开头时，在 Unix-like shell 中必须加 `--` 防止被当成 flag：

   ```bash
   gh search issues -- "panic -label:question"
   gh search repos -- -topic:linux
   ```

5. 需要机器可读结果时优先用 `--json`，再用 `--jq` 或 `--template` 缩小输出。
6. 默认 limit 是 30；先用小 `--limit` 探索，再按需要扩大。
7. 搜索敏感字符串时不要粘贴 token、密码、私钥或内部凭证明文。

## Repositories

常用过滤：

```bash
# 关键词 + stars + 语言
gh search repos "agent framework" --language=python --stars=">100" --sort=stars --limit=20

# owner / visibility
gh search repos --owner=microsoft --visibility=public --limit=20

# topic / license / forks
gh search repos --topic=cli --license=mit --include-forks=false --sort=stars

# JSON 输出
gh search repos "github cli" \
  --json fullName,description,stargazersCount,updatedAt,url \
  --limit=10
```

常用 JSON 字段：

```text
fullName, description, language, stargazersCount, forksCount, updatedAt, pushedAt, url, license, isArchived, isFork, visibility
```

## Code

注意：`gh search code` 使用 GitHub API 的 legacy code search，结果可能与 github.com 新代码搜索不完全一致，不支持网页端新 regex 能力。

常用过滤：

```bash
# 指定语言
gh search code "FastAPI" --language=python --limit=20

# 指定仓库
gh search code "useQuery" --repo TanStack/query --limit=20

# 指定 owner、文件名、扩展名、路径匹配
gh search code "logger" --owner=microsoft --filename package.json
gh search code "panic" --language=go --match=file
gh search code "workflow_dispatch" --extension=yml --match=path

# JSON 输出
gh search code "github-search" \
  --json repository,path,url,textMatches \
  --limit=10
```

常用 JSON 字段：

```text
repository, path, url, sha, textMatches
```

## Issues

常用过滤：

```bash
# open bug issues
gh search issues "crash on startup" --state=open --label=bug --limit=20

# 指定 repo / owner
gh search issues "rate limit" --repo cli/cli --state=open
gh search issues "authentication" --owner=github --state=closed

# include PRs when searching discussions around a topic
gh search issues "token expired" --include-prs --owner=cli --limit=20

# JSON 输出
gh search issues "broken login" \
  --state=open \
  --json repository,number,title,state,labels,updatedAt,url \
  --limit=10
```

常用 JSON 字段：

```text
repository, number, title, state, labels, author, assignees, commentsCount, createdAt, updatedAt, url, isPullRequest
```

## Pull Requests

常用过滤：

```bash
# 已合并修复
gh search prs "fix auth token" --merged --sort=updated --limit=20

# 指定 repo、状态和 review 条件
gh search prs "cache" --repo cli/cli --state=open --review=required
gh search prs --review-requested=@me --state=open

# 分支 / checks / draft
gh search prs --repo owner/repo --base=main --checks=failure
gh search prs --repo owner/repo --draft

# JSON 输出
gh search prs "migration" \
  --merged \
  --json repository,number,title,state,isDraft,updatedAt,url \
  --limit=10
```

常用 JSON 字段：

```text
repository, number, title, state, isDraft, labels, author, assignees, commentsCount, createdAt, updatedAt, url
```

## Commits

常用过滤：

```bash
# 提交信息关键词
gh search commits "fix null pointer" --repo owner/repo --limit=20

# 作者 / 日期 / hash
gh search commits "readme" --author=monalisa
gh search commits --author-date="<2024-01-01" --repo owner/repo
gh search commits --hash=8dd03144ffdc6c0d486d6b705f9c7fba871ee7c3

# JSON 输出
gh search commits "security" \
  --json repository,sha,commit,author,committer,url \
  --limit=10
```

常用 JSON 字段：

```text
repository, sha, commit, author, committer, parents, url
```

## Output Patterns

### Compact human-readable result

```bash
gh search repos "terminal ui" \
  --language=go \
  --sort=stars \
  --limit=10 \
  --json fullName,stargazersCount,description,url \
  --template '{{range .}}{{printf "%s ★%v\n%s\n%s\n\n" .fullName .stargazersCount .description .url}}{{end}}'
```

### JSON for downstream processing

```bash
gh search issues "timeout" \
  --repo owner/repo \
  --state=open \
  --json number,title,updatedAt,url \
  --limit=50
```

### `--jq` filtering

```bash
gh search repos "agent" \
  --json fullName,stargazersCount,url \
  --jq '.[] | select(.stargazersCount > 1000) | {name: .fullName, url}'
```

## Triage Workflow

1. Pick target: repos/code/issues/prs/commits.
2. Start with 1-3 terms and `--limit=10`.
3. Add scope: `--repo`, `--owner`, `--language`, `--state`, `--label`, `--sort`.
4. Switch to `--json` once results are relevant.
5. Report results with repo/name, number/path/sha, URL, and why each hit matters.
6. If results are noisy, tighten with `--match`, `--filename`, `--extension`, `--state`, or raw qualifiers.

## Safety Rules

| 规则 | 要求 |
|---|---|
| 不泄露秘密 | 不搜索 token、password、private key、内部 URL 明文 |
| 不过度抓取 | 使用合理 `--limit`，避免无目的大规模查询 |
| 不假设完整性 | 说明 `gh search code` 与网页新代码搜索可能不同 |
| 不混淆本地搜索 | 本地仓库问题先用本地工具，GitHub 搜索只查远端 GitHub |
| 保留可复现性 | 最终说明使用的命令或关键过滤条件 |

## Common Pitfalls

1. **忘记 `--` 处理排除 qualifier。** `-label:bug` 会被 shell/CLI 当作 flag；用 `gh search issues -- "query -label:bug"`。
2. **hostname / auth 问题误判为无结果。** 私有内容需要 `gh auth status` 成功。
3. **代码搜索期望 regex。** `gh search code` 是 legacy API，不等同于 github.com 新代码搜索。
4. **结果未限定范围。** 搜索报错时先加 `--repo` 或 `--owner`，否则噪声高。
5. **只看标题不看 URL/上下文。** 对 Issue/PR/Commit 至少输出 URL，必要时再用 `gh issue view` / `gh pr view` / `gh api` 深挖。

## Verification Checklist

- [ ] 已确认是否需要 `gh auth status`。
- [ ] 已选择正确 search target。
- [ ] 已用合适 limit 控制结果量。
- [ ] 已使用必要的 owner/repo/language/state/label/sort 过滤。
- [ ] 对排除 qualifier 使用 `--`。
- [ ] 结果包含 URL 和必要上下文。
- [ ] 说明了搜索命令或关键过滤条件，保证可复现。
