# Installation

## 安装说明

M_Skills 是个人常用 Skills 收集仓库，主要通过 Git 克隆后在本地阅读、复制或集成到对应 Agent / 工具环境中使用。

## 前置条件

| 依赖 | 说明 |
|---|---|
| Git | 用于克隆仓库和同步更新 |
| Markdown 阅读器 | 用于阅读 `README.md` 与各 Skill 文档 |
| Agent 工具环境 | 按需将 Skill 内容复制或引用到实际使用的 Agent 环境 |

## 克隆仓库

```bash
git clone https://github.com/mengfei0053/M_Skills.git
cd M_Skills
```

## 目录说明

```text
M_Skills/
├── docs/             # 安装、使用与说明文档
├── skills/           # Skill 文档
│   ├── harmonyos/    # HarmonyOS / OpenHarmony 相关技能
│   └── user/         # 用户通用 Skills
├── scripts/          # 可执行脚本
└── templates/        # 配置模板
```

## 使用 Skill

1. 进入 `skills/` 目录。
2. 选择需要的 Skill，例如：

   ```bash
   open skills/user/worktree/SKILL.md
   ```

3. 按 Skill 文档中的 `When to Use`、`Workflow`、`Verification Checklist` 执行。
4. 如果需要集成到其他 Agent 环境，可复制对应 `SKILL.md` 到目标工具支持的 Skills 目录。

## 更新仓库

```bash
git pull --ff-only
```

## 验证安装

```bash
find skills -maxdepth 3 -name SKILL.md | sort
```

能看到 Skill 文档列表即表示仓库已成功获取。
