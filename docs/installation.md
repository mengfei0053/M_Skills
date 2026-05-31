# Installation

## 安装文档说明

本文档说明 M_Skills 的安装策略、适用范围和可复制执行的安装命令。

## 安装策略

| Skill 来源目录 | 安装级别 | 目标位置 | 适用场景 |
|---|---|---|---|
| `skills/user/` | 用户级别 | Agent 通用、Claude、OpenCode、Cursor 的用户配置目录 | 通用 Git / worktree / 自动提交等跨项目技能 |
| `skills/harmonyos/` | 当前项目级别 | 当前项目内的 Agent / Claude / OpenCode / Cursor 配置目录 | 仅在 HarmonyOS / OpenHarmony 项目中启用 |

## 为什么要区分

- `skills/user/` 是通用能力，适合安装到用户级别，所有项目都可以复用。
- `skills/harmonyos/` 是技术栈专用能力，只应安装到当前 HarmonyOS 项目，避免污染非鸿蒙项目上下文。
- 安装文档负责说明策略；安装命令负责提供可执行脚本和命令。

## 前置条件

| 依赖 | 说明 |
|---|---|
| Git | 用于克隆仓库和同步更新 |
| Bash | 用于执行安装脚本 |
| `curl` | 拉取 IMA agent-interface 页面与 skills 压缩包 |
| `unzip` | 解压 IMA skills 压缩包 |
| Claude / OpenCode / Cursor | 按需安装，脚本会写入对应配置目录 |

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
├── skills/           # Skill 文档
│   ├── harmonyos/    # 安装到当前项目
│   └── user/         # 安装到用户级别
└── templates/        # 配置模板
```

## 安装入口

| 目标 | 命令 |
|---|---|
| 安装用户级 Skills | `bash scripts/install-user-skills.sh` |
| 安装 HarmonyOS Skills 到当前项目 | `bash scripts/install-project-harmonyos-skills.sh /path/to/project` |

`install-user-skills.sh` 在完成 `skills/user/` 同步后，还会：

1. 从 [ima.qq.com/agent-interface](https://ima.qq.com/agent-interface) 页面解析最新 `ima-skills` 压缩包地址并下载安装到用户级 skills 目录（含 `ima-skill` 完整目录树）。
2. 交互提示输入 IMA **Client ID** 与 **API Key**，写入 `~/.config/ima/client_id` 与 `~/.config/ima/api_key`（已存在则跳过）。

## 验证安装

安装命令执行后，可按目标检查文件：

```bash
find ~/.agents/skills -maxdepth 3 -name SKILL.md 2>/dev/null | sort
find ~/.claude/skills -maxdepth 3 -name SKILL.md 2>/dev/null | sort
find ~/.config/opencode/skills -maxdepth 3 -name SKILL.md 2>/dev/null | sort
find ~/.cursor/rules -maxdepth 1 -name 'm-skills-*.mdc' 2>/dev/null | sort
find ~/.agents/skills/ima-skill -maxdepth 2 -name 'SKILL.md' 2>/dev/null | sort
ls -la ~/.config/ima/ 2>/dev/null
```

项目级 HarmonyOS 安装可在目标项目中检查：

```bash
find .agents .claude .opencode .cursor -maxdepth 4 2>/dev/null | sort
```
