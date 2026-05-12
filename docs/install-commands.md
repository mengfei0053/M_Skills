# Install Commands

## 安装命令说明

本文件只放可执行安装命令；安装策略说明请查看：

https://raw.githubusercontent.com/mengfei0053/M_Skills/refs/heads/main/docs/installation.md

## 1. 获取仓库

```bash
git clone https://github.com/mengfei0053/M_Skills.git
cd M_Skills
```

如果已经克隆过：

```bash
cd M_Skills
git pull --ff-only
```

## 2. 安装 `skills/user/` 到用户级别

适用范围：通用 Skills，例如 `auto-commit-push`、`worktree`、`apply-worktree`。

安装目标：

| 工具 | 用户级安装位置 |
|---|---|
| Claude | `~/.claude/skills/<skill>/SKILL.md` |
| OpenCode | `~/.config/opencode/skills/<skill>/SKILL.md` |
| Cursor | `~/.cursor/rules/m-skills-<skill>.mdc` |

执行命令：

```bash
bash scripts/install-user-skills.sh
```

验证：

```bash
find ~/.claude/skills -maxdepth 3 -name SKILL.md 2>/dev/null | sort
find ~/.config/opencode/skills -maxdepth 3 -name SKILL.md 2>/dev/null | sort
find ~/.cursor/rules -maxdepth 1 -name 'm-skills-*.mdc' 2>/dev/null | sort
```

## 3. 安装 `skills/harmonyos/` 到当前项目

适用范围：HarmonyOS / OpenHarmony 项目专用 Skills。

安装目标位于**当前项目内部**：

| 工具 | 项目级安装位置 |
|---|---|
| Agent 通用 | `<project>/.agents/skills/<skill>/SKILL.md` |
| Claude | `<project>/.claude/skills/<skill>/SKILL.md` |
| OpenCode | `<project>/.opencode/skills/<skill>/SKILL.md` |
| Cursor | `<project>/.cursor/rules/m-skills-<skill>.mdc` |

在目标项目目录中执行：

```bash
# 假设当前目录就是 HarmonyOS 项目
/path/to/M_Skills/scripts/install-project-harmonyos-skills.sh "$PWD"
```

或者在 M_Skills 仓库中指定项目路径：

```bash
bash scripts/install-project-harmonyos-skills.sh /path/to/harmonyos-project
```

验证：

```bash
cd /path/to/harmonyos-project
find .agents .claude .opencode .cursor -maxdepth 4 2>/dev/null | sort
```

## 4. 一键示例

```bash
git clone https://github.com/mengfei0053/M_Skills.git
cd M_Skills
bash scripts/install-user-skills.sh
bash scripts/install-project-harmonyos-skills.sh /path/to/harmonyos-project
```
