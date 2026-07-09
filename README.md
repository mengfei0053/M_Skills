# M_Skills

个人常用 Skills 收集仓库，用来沉淀可复用的 Agent 工作流、脚本和配置模板。

## 适用范围

本仓库目前维护用户级通用 Skills，所有 Skill 直接放在 `skills/<skill-name>/` 下，并通过 `scripts/install-user-skills.py` 安装到当前用户的 Agent / Claude / OpenCode / OpenClaw / Cursor 配置目录。

| 类型 | 目录 | 安装位置 | 适用场景 |
|---|---|---|---|
| 用户级通用 Skills | `skills/` | 当前用户的 Agent / Claude / OpenCode / OpenClaw / Cursor 配置 | Git、worktree、提交、编程规范等跨项目能力 |

## 密钥管理

本项目使用 Bitwarden 管理各类密钥、API Key、Token 和登录凭证。安装脚本不会把密钥写入仓库；运行前要求本机已安装并登录 Bitwarden CLI `bw`，以确保后续凭证读取、同步或人工配置都有统一的密钥来源。

请勿把密钥、`.env`、Token 或凭证明文提交到本仓库。需要配置凭证时，优先存入 Bitwarden，并只在本地安全路径中生成运行所需文件。

## 快速安装

```bash
git clone https://github.com/mengfei0053/M_Skills.git
cd M_Skills
```

安装用户级通用 Skills：

```bash
python scripts/install-user-skills.py
```

也可以不克隆仓库，直接拉取 main 分支脚本运行：

```bash
curl -fsSL https://raw.githubusercontent.com/mengfei0053/M_Skills/refs/heads/main/scripts/install-user-skills.py | python3
```

Windows / Linux / macOS 均支持；若 `python` 不可用，请改用 `python3`。

脚本要求已安装并登录 Bitwarden CLI `bw`；未安装时请从 <https://github.com/bitwarden/clients/releases> 下载，安装后运行 `bw login`。如果 Bitwarden vault 是 `locked`，脚本会先复用环境变量 `BW_SESSION` 或 `~/.config/m_skill_auths/bw_session` 中未过期的 session；仍不可用时才执行 `bw unlock --raw`，让用户输入主密码，打印脱敏后的 session 预览，把完整 session 写入 `~/.config/m_skill_auths/bw_session`，并设置当前安装进程的 `BW_SESSION`。

通过 `curl | python3` 等管道运行时，安装目标选择会自动进入非交互默认值；Bitwarden unlock、GitLab 登录确认等必须人工输入的步骤会从 `/dev/tty` 读取，因此普通本地终端中仍可完成。IMA Client ID / API Key 为可选配置，可直接回车跳过；当前环境没有可用 `/dev/tty` 时也会自动跳过 IMA 凭证配置。脚本会自动查找包含 `skills/<skill>/SKILL.md` 的仓库根目录；如果脚本被复制、软链或通过 `curl` 单文件运行且本地没有仓库，会从 GitHub raw/API 拉取 `skills/` 内容安装；也可设置 `M_SKILLS_REPO_DIR=/path/to/M_Skills` 显式指定本地仓库。

脚本末尾还会：

1. 安装/检查 [`gh`](https://cli.github.com/)：已存在则跳过；macOS 通过 `brew install gh`，Linux 按 GitHub CLI 官方包安装说明安装，Windows 提示手动安装。
2. 参考 [`gh skill`](https://cli.github.com/manual/gh_skill) 预览能力，用 `gh skill install --from-local --dir ... --force` 将本仓库 skills 安装到所选目标目录；目标内容已一致则跳过（直接文件复制仍作为基础安装路径）。
3. 检查/安装 [GitLab CLI `glab`](https://gitlab.com/gitlab-org/cli/-/releases)：已存在则跳过；macOS 通过 Homebrew，Linux / Windows 从最新 release 下载匹配安装包。
4. 检查/安装 ZenTao CLI `zentao`：已存在则跳过；未安装时通过 `bun install -g zentao-cli` 安装。
5. 检查/安装 [playwright-cli](https://github.com/microsoft/playwright-cli)：`playwright-cli` 已存在则跳过全局 npm 安装；对应 skill 已存在则跳过复制；仅首次安装 CLI 时引导浏览器依赖。
6. 检查/安装 [ima.qq.com/agent-interface](https://ima.qq.com/agent-interface) 官方 `ima-skill`：所选目标已存在则跳过下载；并可选配置 IMA Client ID / API Key（直接回车或无可用 TTY 时跳过，已配置时写入 `~/.config/ima/`）。
7. 安装完成后先检查 `gh auth status`；如果 GitHub CLI 已登录，跳过 `bw sync`、读取 `github_gh_token`、写入 `~/.config/m_skill_auths/gh_token` 和 `gh auth login`。仅未登录时才通过 `BW_SESSION` 同步 Bitwarden vault，读取并写入 GitHub token 后登录 `gh`。
8. 询问是否登录 GitLab CLI；如果用户选择登录，先检查 `glab auth status --hostname <host>`；如果目标 GitLab 已登录，跳过 `bw sync`、读取 `gitlab_glab_token`、写入 `~/.config/m_skill_auths/glab_token` 和 `glab auth login`。仅未登录时才从 Bitwarden 读取 token，并执行 `glab auth login --hostname <host> --api-protocol <http|https> --stdin < ~/.config/m_skill_auths/glab_token`。`host` 填裸主机名或 `host:port`，不要带 `http://` / `https://`。

## 安装软件清单

`scripts/install-user-skills.py` 会检查或安装以下软件：

| 软件 / 命令 | 用途 | 是否自动安装 | 安装 / 获取方式 |
|---|---|---|---|
| Bitwarden CLI `bw` | 密钥、Token、凭证统一管理；读取 `github_gh_token` | 否，必需前置条件 | 手动从 <https://github.com/bitwarden/clients/releases> 下载并运行 `bw login`；vault 为 `locked` 时脚本会先复用有效 `BW_SESSION`，否则执行 `bw unlock --raw` |
| GitHub CLI `gh` | GitHub 认证、`gh skill install` 辅助安装 | macOS / Linux 自动安装；Windows 提示手动安装 | macOS 用 `brew install gh`；Linux 按 GitHub CLI 官方包安装说明；Windows 需用户自行安装 |
| `gh skill` 子命令 | 使用 GitHub CLI skill 机制安装本仓库 skills | 否 | 已随支持该命令的 `gh` 提供；不可用时跳过 |
| GitLab CLI `glab` | GitLab 命令行工具 | 是 | macOS 用 `brew install glab`；Linux / Windows 从 GitLab 最新 release 下载匹配安装包 |
| Bun `bun` | 安装 ZenTao CLI 的运行时前置条件 | 否 | 用户自行安装 Bun；缺失时跳过 ZenTao CLI 自动安装并提示 |
| ZenTao CLI `zentao` | 禅道命令行工具 | 是 | 已存在则跳过；未安装时执行 `bun install -g zentao-cli` |
| Node.js `node` | 安装 Playwright CLI 的运行时前置条件 | 否 | 用户自行安装 Node.js 18+ |
| npm | 全局安装 `@playwright/cli` | 否 | 通常随 Node.js 安装；缺失时用户自行安装 |
| Playwright CLI `playwright-cli` | 浏览器自动化工具及对应 skill 来源 | 是 | 已存在则跳过全局 npm 安装；缺失时执行 `npm install -g @playwright/cli@latest` |
| Playwright 浏览器依赖 | Playwright 运行所需浏览器与依赖 | 是，可跳过 | 仅首次安装 `playwright-cli` 后执行 `playwright-cli install`；已安装 CLI 或设置 `M_SKILLS_SKIP_PLAYWRIGHT_BROWSERS=1` 时跳过 |
| IMA Skill `ima-skill` | IMA 笔记和知识库 OpenAPI skill | 是 | 所选目标已存在 `ima-skill/SKILL.md` 则跳过；否则从 <https://ima.qq.com/agent-interface> 解析官方 zip 并安装 |

脚本执行下载时会显示下载 URL、目标文件名、已下载大小和百分比（如果服务端返回总大小）。

更多说明见：

| 文档 | 地址 |
|---|---|
| 安装策略 | `docs/installation.md` |
| 安装脚本说明 | `scripts/README.md` |
| 深度初始化记录 | `docs/repo-init.md` |

## 安装目标

用户级 Skills 会安装到：

| 工具 | 位置 |
|---|---|
| Agent 通用 | `~/.agents/skills/<skill>/SKILL.md` |
| Claude | `~/.claude/skills/<skill>/SKILL.md` |
| OpenCode | `~/.config/opencode/skills/<skill>/SKILL.md` |
| OpenClaw | `~/.openclaw/skills/<skill>/`（完整 skill 目录树） |
| Cursor Skill | `~/.cursor/skills/<skill>/`（完整 skill 目录树） |

## 目录结构

```text
M_Skills/
├── docs/             # 安装、使用与说明文档
├── scripts/          # 安装脚本、辅助脚本与脚本说明
├── skills/           # 用户级通用 Skill 文档
│   ├── apply-worktree/
│   ├── auto-commit-push/
│   ├── deeb-init/
│   ├── github-search/
│   ├── karpathy-guidelines/
│   ├── programming-standards/
│   └── worktree/
└── templates/        # 可复用配置或文档模板
```

## 已有 Skills

| Skill | 路径 | 用途 |
|---|---|---|
| Apply Worktree | `skills/apply-worktree/` | 将 Git worktree 中完成的任务分支合并回主项目，并在验证后清理 worktree |
| Auto Commit Push | `skills/auto-commit-push/` | 安全审查、提交并推送当前任务相关改动，分叉时先 rebase，冲突时停止报告 |
| Deeb Init | `skills/deeb-init/` | 深度扫描项目结构与技术栈，生成或刷新根目录及子目录 `AGENTS.md` |
| GitHub Search | `skills/github-search/` | 通过 GitHub CLI `gh search` 搜索仓库、代码、Issue、PR 和 Commit，并规范过滤与输出 |
| Karpathy Guidelines | `skills/karpathy-guidelines/` | 减少 LLM 常见编码失误的行为准则：先思考、保持简单、精准改动、目标驱动验证 |
| Programming Standards | `skills/programming-standards/` | 通用编程规范，覆盖职责、命名、防御性编程、错误处理、日志和可测试性 |
| Worktree | `skills/worktree/` | 为单个需求创建独立 Git worktree 和任务分支，隔离开发过程 |

## 使用方式

- 浏览 `skills/`，按目录选择需要的 Skill。
- 执行 `python scripts/install-user-skills.py` 同步用户级通用 Skills。
- 在 `templates/` 中维护可复用模板；新增模板后同步补充用途说明。

## 维护约定

- 新增、删除、重命名 Skill 时，同步更新本 README 的 Skills 清单与 `docs/repo-init.md`。
- 调整安装路径、脚本参数或安装策略时，同步更新 `docs/installation.md` 与 `docs/repo-init.md`。
- 修改 `install-user-skills.py` 后执行 `python3 -m py_compile scripts/install-user-skills.py`。
- 新增 Bash 脚本后至少执行 `bash -n scripts/*.sh`。

## 新增 Skill 规范

新增 Skill 建议使用独立目录，并提供 `SKILL.md`：

```text
skills/<skill-name>/SKILL.md
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
find ~/.openclaw/skills -maxdepth 3 -name SKILL.md 2>/dev/null | sort
find ~/.cursor/skills -maxdepth 3 -name SKILL.md 2>/dev/null | sort
command -v bw && bw status --raw
command -v gh && gh --version
command -v gh && gh skill --help | head -5
command -v glab && glab --version
command -v bun && bun --version
command -v zentao && zentao --version
gh auth status
ls -la ~/.config/m_skill_auths/ 2>/dev/null
test -s ~/.config/m_skill_auths/bw_session && echo bw_session configured
test -s ~/.config/m_skill_auths/gh_token && echo gh_token configured
test -s ~/.config/m_skill_auths/glab_token && echo glab_token configured
glab auth status 2>/dev/null || true
```
