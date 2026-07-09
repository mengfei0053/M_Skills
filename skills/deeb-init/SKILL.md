---
name: deeb-init
description: Deep-scan a project and bootstrap AGENTS.md at the project root (and scoped subdirectories when warranted). Use when onboarding an agent to a repo, initializing agent guidance, or refreshing project layout notes after structural changes.
version: 1.0.0
author: Mengfei / Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [agents, bootstrap, project-init, deep-scan, documentation, onboarding]
    related_skills: [programming-standards, karpathy-guidelines]
---

# Deeb Init

## Overview

本 Skill 用于**深度扫描目标项目**，并在项目目录中生成或刷新 `AGENTS.md`，让后续 Agent 快速理解项目结构、技术栈、运行方式和维护约定。

目标：

- 基于仓库实际内容生成，不臆造模块或命令；
- 根目录 `AGENTS.md` 作为项目级 Agent 操作契约；
- 对重要子目录按需生成 scoped `AGENTS.md`，避免重复根级 orchestration 内容；
- 若已有 `AGENTS.md`，保留人工维护区块，只更新可推导的布局摘要。

## When to Use

- 新项目或存量项目缺少 `AGENTS.md`，需要 Agent 快速上手。
- 项目结构、技术栈或维护约定发生变化，需要刷新 Agent 指导文件。
- 用户明确要求「深度扫描项目并初始化 AGENTS.md」。

Don't use for:

- 非代码仓库或纯二进制/数据 dump 目录。
- 用户明确要求不要创建或修改 `AGENTS.md`。
- 当前目录不是目标项目根目录，且无法确认应扫描哪一层。
- 仓库含 secrets、凭据或未脱敏敏感路径，尚未确认可写入文档。

## Required Inputs

| 输入 | 默认值 | 说明 |
|---|---|---|
| project root | 当前工作目录或 `git rev-parse --show-toplevel` | 必须明确扫描根目录 |
| scope | root + significant subdirs | 可限定仅根目录或指定子目录 |
| refresh mode | merge | 已有文件时保留 Local Notes，更新布局摘要 |
| language | 中文为主，保留项目原有英文术语 | 与项目 README 语言保持一致 |

## Deep Scan Checklist

在生成 `AGENTS.md` 前，必须完成以下扫描并记录证据。

### 1. 定位项目根

```bash
git rev-parse --show-toplevel 2>/dev/null || pwd
ls -la
```

确认：是否为 monorepo、是否存在 `.git`、根目录标志性文件。

### 2. 目录与模块结构

```bash
find . -maxdepth 3 \
  \( -path './.git/*' -o -path './node_modules/*' -o -path './.omx/*' \
     -o -path './dist/*' -o -path './build/*' -o -path './.venv/*' \) -prune \
  -o -type d -print 2>/dev/null | head -80

find . -maxdepth 2 -type f \
  \( -name 'package.json' -o -name 'pyproject.toml' -o -name 'Cargo.toml' \
     -o -name 'go.mod' -o -name 'pom.xml' -o -name 'build.gradle*' \
     -o -name 'CMakeLists.txt' -o -name 'oh-package.json5' \
     -o -name 'hvigorfile.ts' -o -name 'Makefile' \) 2>/dev/null
```

记录：顶层目录、主要源码目录、测试目录、脚本目录、文档目录。

### 3. 技术栈与工具链

优先读取并摘要：

| 信号文件 | 提取内容 |
|---|---|
| `package.json` / `pnpm-lock.yaml` / `yarn.lock` | 包管理器、scripts、主要依赖 |
| `pyproject.toml` / `requirements.txt` | Python 工具链与测试框架 |
| `Cargo.toml` / `go.mod` | Rust / Go 模块信息 |
| `oh-package.json5` / `hvigorfile.ts` | HarmonyOS / OpenHarmony 工程特征 |
| `Dockerfile` / `docker-compose*.yml` | 容器化与本地运行方式 |
| `.github/workflows/*` / `.gitlab-ci.yml` | CI 命令与质量门禁 |
| `Makefile` / `justfile` | 常用构建/测试入口 |

### 4. 现有 Agent / 规范文档

```bash
find . -maxdepth 4 \( -name 'AGENTS.md' -o -name 'CLAUDE.md' -o -name 'CONTRIBUTING.md' \
  -o -path '*/.cursor/rules/*' -o -path '*/.agents/*' \) 2>/dev/null | head -40
```

记录：已有约定、Cursor rules、Claude skills、禁止覆盖的人工说明。

### 5. 测试与验证入口

从 README、CI、scripts 中归纳可执行验证命令，例如：

```bash
npm test
pnpm test
pytest
cargo test
go test ./...
hvigorw assembleHap
bash -n scripts/*.sh
```

无法确认时写「未检测到标准测试入口」，不要编造。

### 6. Git 与协作上下文

```bash
git remote -v 2>/dev/null
git branch --show-current 2>/dev/null
git log --oneline -5 2>/dev/null
```

记录：默认分支、最近提交风格、是否 fork/monorepo 子包。

## AGENTS.md Generation Rules

### Root `AGENTS.md` 结构

根目录文件应简洁、可执行，推荐结构：

```markdown
# <Project Name>

<1-3 句项目定位：做什么、面向谁、核心约束>

## Project Layout

### Top-Level Directories
- `src/` — ...
- `docs/` — ...

### Key Entry Files
- `package.json` — ...
- `README.md` — ...

## Tech Stack
- Language/runtime: ...
- Package manager: ...
- Test framework: ...
- CI: ...

## Common Commands
```bash
# install
...

# test
...

# lint / build
...
```

## Working Agreements
- 改动前先读相关模块与现有测试。
- 保持 diff 小且聚焦；不要顺手重构无关代码。
- 修改脚本/安装路径/目录结构后，同步更新 README 与相关文档。
- 提交前运行项目可执行的验证命令。

## Verification
- [ ] 相关测试通过
- [ ] lint / typecheck 通过（若项目存在）
- [ ] 文档与目录结构仍一致

## Local Notes
<!-- 项目维护者人工补充区：业务边界、发布流程、禁改目录、环境变量说明 -->
```

### Subdirectory `AGENTS.md`

对以下目录可生成 scoped 文件：`src/`、`apps/`、`packages/`、`services/`、`scripts/`、`docs/` 等**有独立职责**的目录。

子目录文件规则：

- 首行注明父级：`<!-- Parent: ../AGENTS.md -->`（路径按层级调整）。
- 只写该目录特有约定，不重复根级 orchestration。
- 包含 `## Current Layout`：列出该目录下关键文件/子目录（基于扫描结果）。
- 包含 `## Local Notes` 人工维护区。

### OMX / oh-my-codex 项目

若检测到 `omx`、`<!-- OMX:AGENTS-INIT:MANAGED -->` 或 `.omx/`：

- 遵循 OMX managed 区块约定；
- **不要删除或覆盖** `<!-- OMX:AGENTS-INIT:MANUAL:START -->` 到 `<!-- OMX:AGENTS-INIT:MANUAL:END -->` 之间内容；
- 仅刷新 managed 区域的 layout summary；
- 项目约定写入 Local Notes。

## Required Workflow

### 1. 确认目标与边界

- 明确项目根目录绝对路径；
- 确认是新建还是刷新；
- 若已有 `AGENTS.md`，先读取全文，标记需保留的 Local Notes。

### 2. 执行深度扫描

按 Deep Scan Checklist 收集证据。扫描深度默认 3–4 层；monorepo 可加深到 5 层，但跳过 `node_modules`、`.git`、构建产物、虚拟环境。

### 3. 生成扫描摘要（内部）

在写文件前先整理：

| 字段 | 内容 |
|---|---|
| 项目定位 | 一句话 + 证据来源 |
| 主要目录 | 列表 + 职责 |
| 技术栈 | 语言、框架、包管理、CI |
| 常用命令 | 安装 / 测试 / 构建 / 运行 |
| 现有约定 | README、CONTRIBUTING、rules |
| 风险点 | secrets 目录、生成物、禁改路径 |

### 4. 写入 `AGENTS.md`

- 根目录优先；
- 再写 scoped 子目录（如有独立模块且对用户有价值）；
- 使用 Write 工具创建或精确更新；避免无意义全盘重写。

### 5. 验证输出

- 确认路径正确：`AGENTS.md` 位于目标项目根目录；
- 确认命令来自实际文件，不是猜测；
- 确认未泄露 secrets、token、私钥、内网地址；
- 确认 Local Notes 已保留或留空待填。

## Refresh / Merge Behavior

| 场景 | 行为 |
|---|---|
| 不存在 `AGENTS.md` | 新建完整文件 |
| 已存在且无 manual 区块 | 更新 layout/commands，保留标题与项目定位若仍准确 |
| 已存在且有 Local Notes | **只更新** layout summary 与 commands；Local Notes 原样保留 |
| 用户要求完全重写 | 先备份或确认，再整体替换 |

## Safety Rules

| 规则 | 要求 |
|---|---|
| 证据优先 | 所有命令、路径、技术栈必须来自扫描结果 |
| 不臆造 | 未发现的测试/构建命令不要写入 |
| 不泄露 secrets | 跳过 `.env`、凭据、密钥内容 |
| 尊重已有约定 | 已有 AGENTS/CONTRIBUTING/rules 时先合并而非覆盖 |
| 最小 diff | 刷新时只改必要段落 |
| 停止条件 | 无法确定项目根或存在冲突文档版本时暂停并询问 |

## Verification Checklist

- [ ] 已确认项目根目录绝对路径。
- [ ] 已完成目录、技术栈、CI、测试入口扫描。
- [ ] 已检查现有 `AGENTS.md` / rules / CONTRIBUTING。
- [ ] 根目录 `AGENTS.md` 已创建或刷新。
- [ ] 关键子目录 scoped 文件已按需生成。
- [ ] Local Notes 已保留或明确留空。
- [ ] 未写入 secrets 或未经证实的命令。
- [ ] 输出中的路径、命令与仓库实际一致。

## Common Pitfalls

1. **只读 README 不读仓库。** 会漏掉 scripts、CI、monorepo 子包；必须交叉验证。
2. **把 OMX 模板硬套到普通项目。** 非 OMX 项目应使用轻量通用结构。
3. **覆盖 Local Notes。** 人工维护区是长期约定，刷新时必须保留。
4. **子目录 AGENTS 重复根内容。** scoped 文件应只写局部约定。
5. **扫描过深纳入构建产物。** 必须排除 `node_modules`、`dist`、`build`、`.git` 等。
6. **编造 test/build 命令。** 没有证据就标注「未检测到」，不要猜。

## One-Shot Recipe

```bash
# 1) 定位根目录
ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$ROOT"

# 2) 快速结构扫描
ls -la
find . -maxdepth 2 -type f \( -name 'README*' -o -name 'package.json' -o -name 'pyproject.toml' \
  -o -name 'Cargo.toml' -o -name 'go.mod' -o -name 'Makefile' \) 2>/dev/null

# 3) 检查现有 AGENTS
find . -maxdepth 4 -name 'AGENTS.md' 2>/dev/null

# 4) 由 Agent 基于扫描结果写入/刷新 AGENTS.md
# 5) 验证：路径、命令、Local Notes、无 secrets
```
