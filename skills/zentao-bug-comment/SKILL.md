---
name: zentao-bug-comment
description: >-
  Add a comment/remark to a ZenTao (禅道) bug via session login and the
  action/comment page API. Use when the user asks to comment on a ZenTao bug,
  add 备注/评论 to a bug URL or bugID, or when zentao-cli/MCP lacks a comment
  action.
version: 1.0.0
author: Mengfei
license: MIT
metadata:
  hermes:
    tags: [zentao, 禅道, bug, comment, 备注, api]
    related_skills: [zentao-cli, zentao-bug-resolve]
---

# ZenTao Bug Comment

## Overview

给禅道 Bug 添加备注/评论。`zentao-cli` 与禅道 MCP 的 `bug` 模块通常只有 CRUD / activate / close / resolve，**没有独立 comment 动作**；本 Skill 通过会话登录 + 页面接口完成添加，并用 REST API 校验历史记录。

优先执行本 Skill 自带脚本，不要手写一次性请求，也不要用网页抓取旁路。

需要把 Bug 标为 `resolved` 并附备注时，改用 `zentao-bug-resolve`。

## When to Use

- 用户要求给禅道 Bug 添加评论、备注、留言。
- 输入是 Bug ID，或形如 `...&m=bug&f=view&bugID=1897` 的禅道 Bug URL。
- `zentao bug ...` / MCP `zentao_bug` 无法完成 comment。

Don't use for:

- 解决 / 关闭 Bug（解决并备注用 `zentao-bug-resolve`；关闭用 close 流程）。
- 给任务、需求、测试单等非 Bug 对象加备注（本 Skill 仅覆盖 Bug）。
- 未配置本机禅道认证且无法登录时。

## Required Inputs

| 输入 | 说明 |
|---|---|
| Bug | Bug ID，或包含 `bugID=` 的禅道 URL |
| Comment | 要添加的评论文本 |
| Auth | 默认读取 `~/.config/zentao/auth.json`（`ZENTAO_URL` / `ZENTAO_ACCOUNT` / `ZENTAO_PASSWORD`） |

凭证安全：

- 只读取认证文件用于登录，**不要打印**密码、Token、Cookie。
- 文件不存在时，引导用户执行 `zentao login` 或配置 `~/.config/zentao/auth.json`，不要在对话里收集密码。

## Workflow

1. 确认 Bug ID / URL 与评论内容；用户已明确要求时可直接执行，无需二次确认。
2. 运行脚本（相对本 Skill 目录）：

```bash
python3 scripts/add_bug_comment.py <bugID|bugURL> --comment '<评论内容>'
```

示例：

```bash
python3 scripts/add_bug_comment.py 1897 --comment 'test'
python3 scripts/add_bug_comment.py \
  'http://192.168.3.15/index.php?m=bug&f=view&bugID=1897' \
  --comment '已复现，补充日志'
python3 scripts/add_bug_comment.py 1897 --comment 'test' --format=json
```

3. 根据退出码与输出判定结果；`--format=json` 便于程序化处理。
4. 向用户回报 Bug ID、评论内容，以及验证到的 `actionID` / actor / date（若有）。

### 脚本行为（实现细节）

脚本内部顺序：

1. `GET /index.php?m=api&f=getSessionID&t=json` 建立 `zentaosid`
2. `GET /index.php?m=user&f=login&t=json` 取 `rand`
3. `POST /index.php?m=user&f=login&t=json`，密码为 `md5(md5(password) + rand)`
4. `POST /index.php?m=action&f=comment&objectType=bug&objectID=<id>`，表单字段 `comment=<文本>`
5. 成功响应通常包含 `parent.location.reload(true)`
6. 默认再用 `POST /api.php/v1/tokens` + `GET /api.php/v1/bugs/<id>` 校验最新 `commented` 历史

常用选项：

| 选项 | 说明 |
|---|---|
| `--comment` | 评论文本（推荐） |
| `--auth-file` | 自定义认证文件路径 |
| `--timeout` | HTTP 超时秒数，默认 20 |
| `--skip-verify` | 跳过 REST 历史校验 |
| `--format text\|json` | 输出格式 |

仅依赖 Python 3 标准库，无需额外 pip 包。

## Verification

- 脚本退出码为 `0`
- 文本输出含「已为 Bug #... 添加评论」，或 JSON `status=success`
- 校验到的 action：`action=commented`，`comment` 与提交文本一致（或等价的 `<p>...</p>`）
- 可选：`zentao bug <id> --format=json` 查看详情（历史以脚本 REST 校验为准）

## Safety

- 写操作：会在目标 Bug 上留下真实评论；仅在用户明确要求时执行。
- 不要用 `PUT /api.php/v1/bugs/<id>` 夹带 `comment` 冒充添加备注（通常只会产生空 `edited`）。
- 不要用 Token 直打 `action-comment-bug-*.json` 作为主路径；当前可靠路径是**会话登录 + action/comment**。
- 失败时停止并报告错误信息；不要反复重试导致重复评论。
- 不要展示或回显 `auth.json` 中的敏感字段。

## Troubleshooting

| 现象 | 处理 |
|---|---|
| 认证文件不存在 / 缺字段 | 配置 `~/.config/zentao/auth.json` 或 `zentao login` |
| 会话登录失败 | 检查账号密码、禅道 URL、网络可达性 |
| 评论接口无刷新标记 | 账号可能无「添加备注」权限，或会话未真正登录 |
| REST 校验找不到 commented | 用 `--skip-verify` 仅作排障；成功响应仍在时再查 Bug 页面历史 |
| `zentao bug comment` 不存在 | 预期行为；改用本 Skill 脚本 |
