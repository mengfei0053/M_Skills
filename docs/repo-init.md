# Repository Init Notes

> 更新时间：2026-05-12
> 用途：给后续 Agent / 人工维护者快速接手本仓库，并明确“后续修改及时更新”的同步规则。

## 项目定位

M_Skills 是个人常用 Skills 收集仓库，用于沉淀可复用的工作流、脚本、工具链说明和配置模板。

核心原则：

- Skill 以文档为主，每个 Skill 独立目录内使用 `SKILL.md`。
- 通用能力放在 `skills/user/`，技术栈专用能力放在对应分类目录，例如 `skills/harmonyos/`。
- 安装脚本只负责复制/生成目标文件；安装策略与命令说明放在 `docs/`。
- 任何结构、Skill 清单、安装路径、脚本行为变化，都要同步更新相关文档。

## 当前目录快照

| 路径 | 说明 | 维护要求 |
|---|---|---|
| `AGENTS.md` | OMX 生成的仓库级 Agent 指导文件 | 在保留 managed 区域的前提下，只在 Local Notes 写项目级约定 |
| `.gitignore` | 忽略本地运行态文件 | 当前忽略 `.omx/`，避免提交会话状态 |
| `README.md` | 仓库入口说明与 Skill 清单 | 新增/删除/重命名 Skill 时必须更新 |
| `docs/installation.md` | 安装策略说明 | 安装范围、目标目录变化时更新 |
| `docs/repo-init.md` | 深度初始化记录 | 后续结构或规则变化时更新 |
| `scripts/install-user-skills.py` | 跨平台安装 `skills/user/` 到用户级工具配置；在 Linux 上按 GitHub CLI 官方说明安装/检查 `gh` 并尝试用 `gh skill install --from-local` 安装本地 skills；安装 [playwright-cli](https://github.com/microsoft/playwright-cli) 与 skill；从 [ima agent-interface](https://ima.qq.com/agent-interface) 安装 `ima-skill` 并提示 `~/.config/ima/` 凭证 | 修改后运行 `python3 -m py_compile scripts/install-user-skills.py` |
| `scripts/install-project-harmonyos-skills.sh` | 安装 `skills/harmonyos/` 到目标项目 | 修改后运行 `bash -n scripts/*.sh` |
| `skills/user/` | 用户级通用 Skills | 保持 README 与本文件 Skill 清单同步 |
| `skills/harmonyos/` | HarmonyOS / OpenHarmony 项目级 Skills | 只安装到具体项目，不安装到全局用户级 |
| `templates/` | 可复用模板预留目录 | 新增模板后补充用途说明 |

## 当前 Skills 清单

| Skill | 路径 | 分类 | 用途 |
|---|---|---|---|
| `apply-worktree` | `skills/user/apply-worktree/SKILL.md` | 用户级通用 | 将 worktree 开发内容合并回主项目分支，验证后清理 worktree 和任务分支 |
| `auto-commit-push` | `skills/user/auto-commit-push/SKILL.md` | 用户级通用 | 安全提交当前任务相关改动并推送，处理 fetch / rebase / 分叉场景 |
| `programming-standards` | `skills/user/programming-standards/SKILL.md` | 用户级通用 | 通用代码质量、命名、错误处理、测试性和 Review 标准 |
| `karpathy-guidelines` | `skills/user/karpathy-guidelines/SKILL.md` | 用户级通用 | 减少 LLM 常见编码失误：先思考、保持简单、精准改动、目标驱动验证 |
| `deeb-init` | `skills/user/deeb-init/SKILL.md` | 用户级通用 | 深度扫描项目并生成/刷新根目录及 scoped 子目录 `AGENTS.md` |
| `worktree` | `skills/user/worktree/SKILL.md` | 用户级通用 | 为单个需求创建隔离 Git worktree 与任务分支 |
| `harmonyos-performance-optimization` | `skills/harmonyos/harmonyos-performance-optimization/SKILL.md` | HarmonyOS 项目级 | 指导 HarmonyOS / OpenHarmony 应用性能分析、优化、验证 |

## 安装策略

| 来源 | 安装级别 | 目标 |
|---|---|---|
| `skills/user/` | 用户级 | `~/.agents/skills/`、`~/.claude/skills/`、`~/.config/opencode/skills/`、`~/.cursor/skills/` |
| `skills/harmonyos/` | 项目级 | 目标项目内 `.agents/skills/`、`.claude/skills/`、`.opencode/skills/`、`.cursor/rules/` |

安装入口：

```bash
python scripts/install-user-skills.py
bash scripts/install-project-harmonyos-skills.sh /path/to/harmonyos-project
```

## 修改同步规则

后续修改请按影响范围同步更新：

| 变更类型 | 必须同步更新 |
|---|---|
| 新增 / 删除 / 重命名 Skill | `README.md`、`docs/repo-init.md` |
| 调整 Skill 分类或安装级别 | `README.md`、`docs/installation.md`、`docs/repo-init.md` |
| 修改安装脚本参数或目标路径 | `docs/installation.md`、`docs/repo-init.md` |
| 新增模板 | `README.md` 或 `docs/repo-init.md` |
| 修改 Agent 约定 | `AGENTS.md` Local Notes、必要时相关子目录 `AGENTS.md` |

## 验证命令

当前仓库没有语言包管理器或自动化测试框架。修改后优先执行：

```bash
bash -n scripts/*.sh
find skills -mindepth 2 -maxdepth 3 -name SKILL.md | sort
find docs scripts skills -maxdepth 3 -type f | sort
```

如果改动安装脚本，建议在临时目录或明确目标目录做 smoke test，避免覆盖用户真实配置。

## 维护注意事项

- 不要把 `.omx/` 运行态文件当作项目文档维护；它是本地会话状态。
- `AGENTS.md` 为 OMX managed 文件，刷新时会保留 Local Notes；项目约定尽量写在 Local Notes 区块。
- 用户级 Cursor 安装为完整 skill 目录树（`~/.cursor/skills/<skill>/`），源文件仍以 `SKILL.md` 为准。
