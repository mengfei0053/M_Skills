# M_Skills

个人常用 Skills 收集仓库 — 记录和沉淀日常使用的脚本、工具链、工作流与配置模板。

## 目录结构

```
M_Skills/
├── .agents/          # Agent 上下文配置
├── .claude/          # Claude Code 配置
├── skills/           # Skill 文档
│   └── harmonyos/    # HarmonyOS / OpenHarmony 相关技能
├── scripts/          # 可执行脚本
└── templates/        # 配置模板
```

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
