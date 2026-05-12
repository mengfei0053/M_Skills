# M_Skills

个人常用 Skills 收集仓库 — 记录和沉淀日常使用的脚本、工具链、工作流与配置模板。

## 目录结构

```
M_Skills/
├── .agents/          # Agent 上下文配置
├── .claude/          # Claude Code 配置
├── docs/             # 安装、使用与说明文档
├── skills/           # Skill 文档
│   ├── harmonyos/    # HarmonyOS / OpenHarmony 相关技能
│   └── user/         # 用户通用 Skills
├── scripts/          # 可执行脚本
└── templates/        # 配置模板
```

## 安装

| 类型 | 链接 |
|---|---|
| 安装文档 | https://raw.githubusercontent.com/mengfei0053/M_Skills/refs/heads/main/docs/installation.md |
| 安装命令 | https://raw.githubusercontent.com/mengfei0053/M_Skills/refs/heads/main/docs/install-commands.md |

安装策略：`skills/user/` 安装到用户级别的 Claude / OpenCode / Cursor 配置中；`skills/harmonyos/` 安装到当前项目中。

## 使用方式

- **浏览 Skill**：进入 `skills/` 查看分类文档。
- **运行脚本**：`scripts/` 下直接执行。
- **复用模板**：`templates/` 下复制修改。

## 新增 Skill 规范

每条 Skill 建议包含：

| 模块 | 说明 |
|---|---|
| 场景 | 什么情况下使用 |
| 前置条件 | 需要什么环境、工具或权限 |
| 步骤 | 可执行的操作流程 |
| 测试 | 优先定义测试或验证方法 |
| 验收 | 如何确认需求完成 |
| 参考 | 相关文档链接 |

## 已有 Skills

| Skill | 路径 | 用途 |
|---|---|---|
| HarmonyOS 应用性能优化 | `skills/harmonyos/harmonyos-performance-optimization/` | 分析、设计、评审和验证 HarmonyOS / OpenHarmony 应用性能优化方案 |
| 用户通用 Skills | `skills/user/` | 存放不限定具体技术栈、可跨场景复用的用户通用技能 |
| Auto Commit Push | `skills/user/auto-commit-push/` | 自动安全提交代码并推送远程，分叉时先 rebase，冲突时停止并报告 |
| Worktree | `skills/user/worktree/` | 为单个需求创建独立 Git worktree 和任务分支，隔离开发并保持主分支干净 |
| Apply Worktree | `skills/user/apply-worktree/` | 将 worktree 开发内容合并回主项目分支，验证通过后清理 worktree 和任务分支 |
