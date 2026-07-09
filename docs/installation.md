# Installation

## 安装文档说明

本文档说明 M_Skills 的安装策略、适用范围和可复制执行的安装命令。

## 安装策略

| Skill 来源目录 | 安装级别 | 目标位置 | 适用场景 |
|---|---|---|---|
| `skills/` | 用户级别 | Agent 通用、Claude、OpenCode、OpenClaw、Cursor 的用户配置目录 | 通用 Git / worktree / 自动提交等跨项目技能 |

M_Skills 现在只维护用户级通用 Skills。每个 Skill 直接位于 `skills/<skill-name>/SKILL.md`，不再使用旧的用户级分层目录或项目级技术栈安装目录。

## 前置条件

| 依赖 | 说明 |
|---|---|
| Git | 用于克隆仓库和同步更新 |
| Python 3.8+ | 执行 `scripts/install-user-skills.py`（支持 Windows / Linux / macOS） |
| Bitwarden CLI `bw` | 必需前置条件；需已安装并通过 `bw login` 登录。未安装时从 <https://github.com/bitwarden/clients/releases> 下载 |
| GitHub CLI `gh` | 脚本会检查/安装；macOS 用 `brew install gh`，Linux 按官方包安装说明安装，并用预览版 `gh skill` 进行本地 skill 安装 |
| GitLab CLI `glab` | 脚本会检查/安装；macOS 用 `brew install glab`，Linux / Windows 从 <https://gitlab.com/gitlab-org/cli/-/releases> 最新 release 自动下载匹配安装包 |
| Node.js 18+ | 安装 `@playwright/cli` |
| `npm` | 全局安装 `@playwright/cli` |
| Agent / Claude / OpenCode / OpenClaw / Cursor | 按需安装，脚本会写入对应配置目录 |

## 克隆仓库

```bash
git clone https://github.com/mengfei0053/M_Skills.git
cd M_Skills
```

## 目录说明

```text
M_Skills/
├── docs/             # 安装、使用与说明文档
├── scripts/          # 安装脚本与辅助脚本
├── skills/           # 安装到用户级别的 Skill 文档
└── templates/        # 配置模板
```

## 安装入口

| 目标 | 命令 |
|---|---|
| 安装用户级 Skills（本地仓库） | `python scripts/install-user-skills.py` |
| 安装用户级 Skills（远程单文件） | `curl -fsSL https://raw.githubusercontent.com/mengfei0053/M_Skills/refs/heads/main/scripts/install-user-skills.py \| python3` |

`install-user-skills.py` 会先检查必需前置条件：`bw` 命令必须存在，且 `bw status --raw` 必须输出 `locked` / `unlocked`，或返回 JSON 且其中 `status` 字段为 `locked` / `unlocked`。如果未安装，脚本会提示从 <https://github.com/bitwarden/clients/releases> 下载；如果尚未登录，脚本会提示先运行 `bw login`；如果 vault 为 `locked`，脚本会先尝试复用环境变量 `BW_SESSION` 或 `~/.config/m_skill_auths/bw_session` 中未过期的 session，仍不可用时才执行 `bw unlock --raw` 让用户输入主密码。

`install-user-skills.py` 在完成 `skills/` 直接文件同步后，还会：

1. 安装或检查 `gh`：已存在则跳过；macOS 使用 `brew install gh`；Linux 按 [GitHub CLI 官方 Linux 安装说明](https://github.com/cli/cli/blob/trunk/docs/install_linux.md)（Debian/Ubuntu `apt`、RPM `dnf`/`yum`、openSUSE `zypper`）；Windows 提示手动安装。
2. 参考 [`gh skill`](https://cli.github.com/manual/gh_skill) 与 [`gh skill install`](https://cli.github.com/manual/gh_skill_install) 预览能力，用 `gh skill install <repo> <skill-name> --from-local --dir <target> --force` 将本仓库 skills 安装到所选目标目录；目标内容已一致则跳过；若 `gh skill` 不可用，保留前一步直接文件同步结果并提示。
3. 检查/安装 [GitLab CLI `glab`](https://gitlab.com/gitlab-org/cli/-/releases)：已存在则跳过；macOS 使用 `brew install glab`，Linux / Windows 从最新 release 下载匹配安装包并安装。
4. 检查/安装 ZenTao CLI `zentao`：已存在则跳过；未安装时通过 `bun install -g zentao-cli` 安装，缺少 Bun 时提示用户先安装 Bun。
5. 检查/安装 [@playwright/cli](https://github.com/microsoft/playwright-cli)：`playwright-cli` 已存在则跳过全局 npm 安装；对应 skill 已存在则跳过复制；仅首次安装 CLI 时执行 `playwright-cli install` 引导浏览器依赖。Linux 会预先使用 `PLAYWRIGHT_HOST_PLATFORM_OVERRIDE=ubuntu24.04-<arch>` 避免 Ubuntu 26.04 ffmpeg 不支持报错。该步骤有 300 秒超时；如需完全跳过，可设置 `M_SKILLS_SKIP_PLAYWRIGHT_BROWSERS=1`，脚本不会把 CLI 与 skill 安装标为失败。
6. 检查/安装 [ima.qq.com/agent-interface](https://ima.qq.com/agent-interface) 官方 `ima-skill`：所选目标已存在则跳过下载；否则解析最新 `ima-skills` 压缩包地址并下载安装到用户级 skills 目录（含 `ima-skill` 完整目录树）。
7. 可选配置 IMA **Client ID** 与 **API Key**：交互式 stdin 或 `/dev/tty` 可用时提示输入，直接回车可跳过；已配置时写入 `~/.config/ima/client_id` 与 `~/.config/ima/api_key`（已存在则跳过）。
8. 安装完成后先检查 `gh auth status`；如果 GitHub CLI 已登录，跳过 `bw sync`、`bw get password github_gh_token`、写入 `~/.config/m_skill_auths/gh_token` 和 `gh auth login`。仅未登录时才通过 `BW_SESSION` 同步 Bitwarden vault，读取并写入 GitHub token 后登录 `gh`。
9. 询问是否登录 GitLab CLI；如果用户选择登录，先检查 `glab auth status --hostname <host>`；如果目标 GitLab 已登录，跳过 `bw sync`、`bw get password gitlab_glab_token`、写入 `~/.config/m_skill_auths/glab_token` 和 `glab auth login`。仅未登录时才从 Bitwarden 读取 token，并执行 `glab auth login --hostname <host> --api-protocol <http|https> --stdin < ~/.config/m_skill_auths/glab_token`。host 默认 `gitlab.com`，填裸主机名或 `host:port`，不要带协议；API protocol 默认 `https`，可交互选择或用 `M_SKILLS_GITLAB_API_PROTOCOL` 预设。

脚本开始时会交互选择安装目标（Agent / Claude / OpenCode / OpenClaw / Cursor Skill）。脚本会从脚本所在目录、当前工作目录及其父目录自动查找包含 `skills/<skill>/SKILL.md` 的 M_Skills 仓库根目录；如果脚本被复制、软链或通过 `curl` 单文件运行且本地没有仓库，会从 GitHub raw/API 拉取 `skills/` 内容安装。可用 `M_SKILLS_REPO_DIR` 显式指定本地仓库根目录。

通过 `curl | python3` 等管道运行时，安装目标选择会自动进入非交互默认值；需要人工输入的 Bitwarden unlock、GitLab 登录确认和 hostname 会优先从 `/dev/tty` 读取，因此普通本地终端管道运行可继续完成。IMA 凭证配置是可选项，可直接回车跳过；当前环境没有可用 `/dev/tty` 时也会自动跳过 IMA 凭证配置。如果 Bitwarden vault 为 `locked`，脚本会先尝试验证并复用环境变量 `BW_SESSION` 或 `~/.config/m_skill_auths/bw_session`，仍不可用时重新执行 `bw unlock --raw`；解锁成功后会打印脱敏后的 session 预览，将完整 session 写入 `~/.config/m_skill_auths/bw_session`，并设置当前安装进程的 `BW_SESSION`。当前环境没有可用 `/dev/tty` 且 Bitwarden 也没有可用 session 时，请先在本地终端执行 `export BW_SESSION=$(bw unlock --raw)`，或下载脚本后用本地终端直接运行。脚本执行下载时会显示下载 URL、目标文件名、已下载大小和百分比（当服务端返回总大小时）。

非交互环境可通过环境变量预设，例如：

```bash
M_SKILLS_INSTALL_TARGETS=agent,claude,cursor_skill python scripts/install-user-skills.py
M_SKILLS_REPO_DIR=/path/to/M_Skills M_SKILLS_INSTALL_TARGETS=agent python /path/to/install-user-skills.py
curl -fsSL https://raw.githubusercontent.com/mengfei0053/M_Skills/refs/heads/main/scripts/install-user-skills.py | M_SKILLS_INSTALL_TARGETS=agent python3
```

## 验证安装

安装命令执行后，可按目标检查文件：

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
find ~/.agents/skills/playwright-cli -maxdepth 2 -name 'SKILL.md' 2>/dev/null | sort
command -v playwright-cli && playwright-cli --help | head -5
find ~/.agents/skills/ima-skill -maxdepth 2 -name 'SKILL.md' 2>/dev/null | sort
ls -la ~/.config/ima/ 2>/dev/null
```
