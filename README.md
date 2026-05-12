# M_Skills

个人常用 Skills 收集仓库 — 记录和沉淀日常使用的脚本、工具链、工作流与配置模板。

## 目录结构

```
M_Skills/
├── .agents/          # Agent 上下文配置
├── .claude/          # Claude Code 配置
├── skills/           # Skill 文档
│   ├── dev/          #   开发相关
│   ├── ops/          #   运维相关
│   ├── ai/           #   AI/LLM 相关
│   └── life/         #   日常生活
├── scripts/          # 可执行脚本
└── templates/        # 配置模板
```

## 使用方式

- **浏览 Skill**：进入 `skills/` 查看分类文档
- **运行脚本**：`scripts/` 下直接执行
- **复用模板**：`templates/` 下复制修改

## 新增 Skill

复制模板，填写场景、步骤、验证方法即可：

```markdown
# Skill 标题

## 场景
什么情况下使用

## 步骤
1. xxx
2. xxx

## 验证
如何确认
```
