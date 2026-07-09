# install-user-skills.py

`scripts/install-user-skills.py` 是 M_Skills 的用户级安装入口，用于把仓库中的通用 Skills 安装到当前用户的多种 Agent/IDE 配置目录，并顺带安装外部辅助 skills。

## 功能概览

脚本会执行以下工作：

1. 检查必需前置条件：Bitwarden CLI `bw` 已安装且已登录。
2. 选择安装目标目录（交互式或通过环境变量）。
3. 从本地仓库 `skills/<skill-name>/SKILL.md` 安装 M_Skills 内置 skills。
4. 本地仓库不可用时，从 GitHub raw/API 拉取 `skills/` 内容安装。
5. 检查或安装 GitHub CLI `gh`，并在 `gh skill` 可用时尝试通过官方 skill 命令安装本地 skills。
6. 检查或安装 GitLab CLI `glab`。
7. 全局安装 `@playwright/cli`，同步 `playwright-cli` skill，并引导安装 Playwright 浏览器依赖。
8. 从 IMA agent-interface 下载并安装官方 `ima-skill`。
9. 交互写入 IMA Client ID / API Key 到 `~/.config/ima/`。
10. 打印安装摘要，包括工具状态、安装明细和 IMA 凭证路径。

## 前置条件

Bitwarden CLI 是必需前置条件。运行安装脚本前必须满足：

1. 已安装 `bw` 命令。
2. `bw status --raw` 输出为 `locked` 或 `unlocked`。

如果未安装，请从 Bitwarden clients releases 页面下载并安装：

<https://github.com/bitwarden/clients/releases>

安装后先执行：

```bash
bw login
bw status --raw
```

如果输出为 `unauthenticated`，脚本会停止并提示先登录。

## 快速使用

在仓库根目录执行：

```bash
python3 scripts/install-user-skills.py
```

如果系统默认 `python` 指向 Python 3，也可以使用：

```bash
python scripts/install-user-skills.py
```

不克隆仓库时，可直接运行远程脚本：

```bash
curl -fsSL https://raw.githubusercontent.com/mengfei0053/M_Skills/refs/heads/main/scripts/install-user-skills.py | python3
```

## 安装目标

脚本支持以下目标：

| 目标 key | 显示名称 | 安装目录 |
|---|---|---|
| `agent` | Agent | `~/.agents/skills/` |
| `claude` | Claude | `~/.claude/skills/` |
| `opencode` | OpenCode | `~/.config/opencode/skills/` |
| `openclaw` | OpenClaw | `~/.openclaw/skills/` |
| `cursor_skill` | Cursor Skill | `~/.cursor/skills/` |

非交互环境默认安装到全部目标。交互环境会显示目标列表，可输入编号、key 或 `all`。

## 环境变量

| 变量 | 用途 | 示例 |
|---|---|---|
| `M_SKILLS_INSTALL_TARGETS` | 跳过交互选择，指定安装目标；支持逗号或空格分隔，也支持 `all` | `agent,claude,cursor_skill` |
| `M_SKILLS_REPO_DIR` | 显式指定 M_Skills 仓库根目录 | `/path/to/M_Skills` |
| `M_SKILLS_SKIP_PLAYWRIGHT_BROWSERS` | 跳过 `playwright-cli install` 浏览器依赖安装 | `1` |

示例：

```bash
M_SKILLS_INSTALL_TARGETS=agent,claude python3 scripts/install-user-skills.py
M_SKILLS_REPO_DIR=/path/to/M_Skills M_SKILLS_INSTALL_TARGETS=agent python3 /path/to/install-user-skills.py
M_SKILLS_SKIP_PLAYWRIGHT_BROWSERS=1 python3 scripts/install-user-skills.py
```

## 本地仓库发现逻辑

脚本会按以下顺序查找 M_Skills 仓库：

1. `M_SKILLS_REPO_DIR` 指定的目录。
2. 脚本所在目录。
3. 脚本所在目录的父目录。
4. 当前工作目录。
5. 当前工作目录的所有父目录。

候选目录必须包含至少一个 `skills/<skill-name>/SKILL.md`，才会被视为有效仓库根目录。

## 远程安装模式

当本地仓库不可用时，脚本会从以下远程地址获取 M_Skills skills：

- GitHub contents API：`https://api.github.com/repos/mengfei0053/M_Skills/contents/skills?ref=main`
- GitHub raw：`https://raw.githubusercontent.com/mengfei0053/M_Skills/refs/heads/main/skills/<skill-name>/SKILL.md`

下载 URL 仅允许 HTTPS，并限制在脚本内置白名单域名中，避免 `file://` 或未知主机被 urllib 读取。

## 检查 / 安装的软件总览

| 软件 / 命令 | 脚本会检查什么 | 是否自动安装 | 失败或缺失时行为 |
|---|---|---|---|
| Bitwarden CLI `bw` | `command -v bw` 与 `bw status --raw`；状态必须是 `locked` 或 `unlocked` | 否 | 立即停止；提示从 <https://github.com/bitwarden/clients/releases> 下载并先运行 `bw login` |
| GitHub CLI `gh` | `command -v gh` | 仅 Linux 上尝试自动安装 | Linux 无法安装时提示失败；非 Linux 提示手动安装，但直接文件复制安装仍保留 |
| `gh skill` 子命令 | `gh skill --help` | 否 | 不可用时跳过 `gh skill install`，直接文件复制安装仍保留 |
| GitLab CLI `glab` | `command -v glab` | 是：macOS 通过 `brew install glab`；Linux / Windows 从 GitLab 最新 release 下载匹配安装包 | 自动安装失败时提示从 <https://gitlab.com/gitlab-org/cli/-/releases> 手动下载 |
| Node.js `node` | `command -v node` | 否 | 缺失时跳过 Playwright CLI 安装并提示需要 Node.js 18+ |
| npm | `command -v npm` | 否 | 缺失时跳过 Playwright CLI 安装并提示需要 npm |
| Playwright CLI `playwright-cli` | 全局安装 `@playwright/cli` 后检查 `command -v playwright-cli` | 是，通过 `npm install -g @playwright/cli@latest` | 安装失败或命令不可用时跳过 Playwright skill / 浏览器依赖并提示手动安装 |
| Playwright 浏览器依赖 | 执行 `playwright-cli install` | 是，可用 `M_SKILLS_SKIP_PLAYWRIGHT_BROWSERS=1` 跳过 | 超时或失败时仅记录警告；CLI 与 skill 已安装时仍视为可继续 |
| IMA Skill `ima-skill` | 访问 IMA agent-interface，解析并下载官方 `ima-skills` zip | 是，下载并复制 skill 目录 | 下载、解析或解压失败时记录失败并提示后续手动修复 |
| IMA 凭证目录 | 检查 `~/.config/ima/client_id` 与 `~/.config/ima/api_key` 是否已存在且非空 | 部分自动：创建目录和文件，但凭证需用户输入 | 非交互环境无法输入时打印摘要并以非零状态退出 |

## 外部依赖行为

### Bitwarden CLI

`bw` 是硬性前置条件，脚本不会自动安装或登录 Bitwarden CLI。

- 未找到 `bw`：脚本立即停止，并提示下载地址：<https://github.com/bitwarden/clients/releases>。
- `bw status --raw` 输出 `unauthenticated`：脚本立即停止，并提示先运行 `bw login`。
- `bw status --raw` 输出 `locked` 或 `unlocked`：视为已登录，脚本继续执行。

### GitHub CLI

- 如果 `gh` 已存在，脚本会直接记录路径。
- Linux 上若 `gh` 不存在，脚本会尝试按官方 Linux 安装说明使用 `apt`、`dnf`、`yum` 或 `zypper` 安装。
- 非 Linux 平台不会自动安装 `gh`，只会提示用户手动安装。
- 如果 `gh skill --help` 可用，脚本会额外尝试 `gh skill install --from-local`。
- 即使 `gh skill` 不可用，直接文件复制安装结果仍会保留。

### GitLab CLI

- 如果 `glab` 已存在，脚本会直接记录路径。
- macOS 上会使用 Homebrew 执行 `brew install glab`。
- Linux / Windows 上会访问 GitLab CLI 最新 release API，选择当前系统和 CPU 架构匹配的安装包。
- Linux 优先使用 `.deb` / `.rpm` / `.apk` 包；没有可用包管理器或 sudo 时回退到 `.tar.gz`，安装到 `~/.local/bin/glab`。
- Windows 会下载最新 release 的 silent installer 并以 `/S` 静默安装。
- 自动安装失败时，脚本会提示手动下载：<https://gitlab.com/gitlab-org/cli/-/releases>。

### Playwright CLI

脚本会执行：

```bash
npm install -g @playwright/cli@latest
playwright-cli install
```

并把 `@playwright/cli` 包内的 `skills/playwright-cli` 安装到所选目标目录。

Linux 上会自动设置 `PLAYWRIGHT_HOST_PLATFORM_OVERRIDE=ubuntu24.04-<arch>` 作为主机平台 fallback。浏览器依赖安装有 300 秒超时，可用 `M_SKILLS_SKIP_PLAYWRIGHT_BROWSERS=1` 跳过。

### IMA Skill

脚本会访问 `https://ima.qq.com/agent-interface`，解析官方 `ima-skills` zip 下载地址，安装其中的 `ima-skill`，并提示输入：

- IMA Client ID
- IMA API Key

凭证会保存到：

```text
~/.config/ima/client_id
~/.config/ima/api_key
```

如果凭证文件已存在且非空，脚本会跳过重新输入。

## 验证安装

安装后可检查：

```bash
find ~/.agents/skills -maxdepth 3 -name SKILL.md 2>/dev/null | sort
find ~/.claude/skills -maxdepth 3 -name SKILL.md 2>/dev/null | sort
find ~/.config/opencode/skills -maxdepth 3 -name SKILL.md 2>/dev/null | sort
find ~/.openclaw/skills -maxdepth 3 -name SKILL.md 2>/dev/null | sort
find ~/.cursor/skills -maxdepth 3 -name SKILL.md 2>/dev/null | sort
command -v gh && gh --version
command -v glab && glab --version
command -v playwright-cli && playwright-cli --help | head -5
ls -la ~/.config/ima/ 2>/dev/null
```

## 维护与测试

修改脚本后至少执行：

```bash
python3 -m py_compile scripts/install-user-skills.py
```

建议额外做发现逻辑 smoke test：

```bash
python3 - <<'PY'
import importlib.util
import sys
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "installer", "scripts/install-user-skills.py"
)
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)
repo = mod.find_repo_dir()
skills = sorted(
    p.name
    for p in (repo / "skills").iterdir()
    if p.is_dir() and (p / "SKILL.md").is_file()
)
print(f"repo={repo}")
print("skills=" + ",".join(skills))
assert repo == Path.cwd()
assert skills
PY
```

涉及真实安装路径的 smoke test 建议在临时 HOME 或明确的测试目录中执行，避免覆盖用户现有配置。

## 常见问题

### 非交互环境为什么失败？

直接文件复制、GitHub CLI、Playwright 和 IMA skill 下载可以在非交互环境中运行，但脚本仍要求本机已安装并登录 Bitwarden CLI。IMA 凭证输入需要交互式终端。如果无法输入凭证，脚本会打印摘要并以非零状态退出。

### 为什么跳过了 gh skill？

`gh skill` 是 GitHub CLI 的 skill 子命令。如果本机 `gh` 不存在、版本不支持该命令，或本地仓库不可用，脚本会跳过该步骤。基础的直接文件复制安装不受影响。

### 如何只安装本仓库 skills，不安装 Playwright/IMA？

当前脚本没有提供“只安装本仓库 skills”的开关。可按需修改脚本或在网络/依赖失败后使用已完成的直接文件复制结果。
