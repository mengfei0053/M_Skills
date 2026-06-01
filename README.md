# M_Skills

个人常用 Skills 收集仓库，用来沉淀可复用的 Agent 工作流、脚本和配置模板。

## 适用范围

本仓库把 Skills 分成两类：

| 类型 | 目录 | 安装位置 | 适用场景 |
|---|---|---|---|
| 用户级通用 Skills | `skills/user/` | 当前用户的 Claude / OpenCode / Cursor 配置 | Git、worktree、提交、编程规范等跨项目能力 |
| 项目级 HarmonyOS Skills | `skills/harmonyos/` | 指定 HarmonyOS / OpenHarmony 项目内部 | ArkTS、ArkUI、性能优化等技术栈专项能力 |

这样可以让通用能力在所有项目中复用，同时避免 HarmonyOS 专项上下文污染其他项目。

## 快速安装

```bash
git clone https://github.com/mengfei0053/M_Skills.git
cd M_Skills
```

安装用户级通用 Skills：

```bash
python scripts/install-user-skills.py
```

Windows / Linux / macOS 均支持；若 `python` 不可用，请改用 `python3`。

脚本末尾还会：

1. 按 GitHub CLI 官方 Linux 安装说明安装/检查 [`gh`](https://github.com/cli/cli/blob/trunk/docs/install_linux.md)（非 Linux 平台提示手动安装）。
2. 参考 [`gh skill`](https://cli.github.com/manual/gh_skill) 预览能力，用 `gh skill install --from-local --dir ... --force` 将本仓库用户级 skills 安装到所选目标目录（直接文件复制仍作为基础安装路径）。
3. 从 [playwright-cli](https://github.com/microsoft/playwright-cli) 全局安装 `@playwright/cli`，并将 `playwright-cli` skill 同步到用户级 skills 目录。
4. 从 [ima.qq.com/agent-interface](https://ima.qq.com/agent-interface) 安装官方 `ima-skill`，并提示配置 IMA Client ID / API Key（写入 `~/.config/ima/`）。

安装 HarmonyOS Skills 到指定项目：

```bash
bash scripts/install-project-harmonyos-skills.sh /path/to/harmonyos-project
```

如果当前目录就是目标 HarmonyOS 项目，也可以直接执行：

```bash
/path/to/M_Skills/scripts/install-project-harmonyos-skills.sh "$PWD"
```

更多说明见：

| 文档 | 地址 |
|---|---|
| 安装策略 | `docs/installation.md` |
| 深度初始化记录 | `docs/repo-init.md` |

## 安装目标

用户级 Skills 会安装到：

| 工具 | 位置 |
|---|---|
| Agent 通用 | `~/.agents/skills/<skill>/SKILL.md` |
| Claude | `~/.claude/skills/<skill>/SKILL.md` |
| OpenCode | `~/.config/opencode/skills/<skill>/SKILL.md` |
| Cursor | `~/.cursor/skills/<skill>/`（完整 skill 目录树） |

HarmonyOS 项目级 Skills 会安装到目标项目内：

| 工具 | 位置 |
|---|---|
| Agent 通用 | `<project>/.agents/skills/<skill>/SKILL.md` |
| Claude | `<project>/.claude/skills/<skill>/SKILL.md` |
| OpenCode | `<project>/.opencode/skills/<skill>/SKILL.md` |
| Cursor | `<project>/.cursor/rules/m-skills-<skill>.mdc` |

## 目录结构

```text
M_Skills/
├── docs/             # 安装、使用与说明文档
├── scripts/          # 安装脚本与辅助脚本
├── skills/           # Skill 文档
│   ├── harmonyos/    # HarmonyOS / OpenHarmony 项目级 Skills
│   └── user/         # 用户级通用 Skills
└── templates/        # 可复用配置或文档模板
```

## 已有 Skills

| Skill | 路径 | 用途 |
|---|---|---|
| HarmonyOS Performance Optimization | `skills/harmonyos/harmonyos-performance-optimization/` | 分析、设计、评审和验证 HarmonyOS / OpenHarmony 应用性能优化方案 |
| Apply Worktree | `skills/user/apply-worktree/` | 将 Git worktree 中完成的任务分支合并回主项目，并在验证后清理 worktree |
| Auto Commit Push | `skills/user/auto-commit-push/` | 安全审查、提交并推送当前任务相关改动，分叉时先 rebase，冲突时停止报告 |
| Programming Standards | `skills/user/programming-standards/` | 通用编程规范，覆盖职责、命名、防御性编程、错误处理、日志和可测试性 |
| Karpathy Guidelines | `skills/user/karpathy-guidelines/` | 减少 LLM 常见编码失误的行为准则：先思考、保持简单、精准改动、目标驱动验证 |
| Deeb Init | `skills/user/deeb-init/` | 深度扫描项目结构与技术栈，生成或刷新根目录及子目录 `AGENTS.md` |
| Worktree | `skills/user/worktree/` | 为单个需求创建独立 Git worktree 和任务分支，隔离开发过程 |

## 使用方式

- 浏览 `skills/`，按目录选择需要的 Skill。
- 执行 `python scripts/install-user-skills.py` 同步用户级通用 Skills。
- 执行 `scripts/install-project-harmonyos-skills.sh` 把 HarmonyOS Skills 安装到指定项目。
- 在 `templates/` 中维护可复用模板；新增模板后同步补充用途说明。

## 维护约定

- 新增、删除、重命名 Skill 时，同步更新本 README 的 Skills 清单与 `docs/repo-init.md`。
- 调整安装路径、脚本参数或安装策略时，同步更新 `docs/installation.md` 与 `docs/repo-init.md`。
- 修改 Bash 脚本后至少执行 `bash -n scripts/*.sh`；修改 `install-user-skills.py` 后执行 `python3 -m py_compile scripts/install-user-skills.py`。

## 新增 Skill 规范

新增 Skill 建议使用独立目录，并提供 `SKILL.md`：

```text
skills/<category>/<skill-name>/SKILL.md
```

`SKILL.md` 建议包含：

| 模块 | 说明 |
|---|---|
| 元数据 | `name`、`description`、`version`、`author`、`license` |
| Overview | 说明 Skill 目标和核心原则 |
| When to Use | 明确适用场景和不适用场景 |
| Required Inputs | 列出执行前必须知道的信息 |
| Workflow | 给出可执行步骤 |
| Verification | 定义测试、检查或验收方式 |
| Safety | 说明必须停止、升级或人工判断的边界 |

## 验证安装

检查用户级安装结果：

```bash
find ~/.agents/skills -maxdepth 3 -name SKILL.md 2>/dev/null | sort
find ~/.claude/skills -maxdepth 3 -name SKILL.md 2>/dev/null | sort
find ~/.config/opencode/skills -maxdepth 3 -name SKILL.md 2>/dev/null | sort
find ~/.cursor/skills -maxdepth 3 -name SKILL.md 2>/dev/null | sort
command -v gh && gh --version
command -v gh && gh skill --help | head -5
```

检查项目级 HarmonyOS 安装结果：

```bash
cd /path/to/harmonyos-project
find .agents .claude .opencode .cursor -maxdepth 4 2>/dev/null | sort
```
