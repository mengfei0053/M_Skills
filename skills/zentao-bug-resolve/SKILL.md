---
name: zentao-bug-resolve
description: >-
  Resolve a ZenTao (禅道) bug to status resolved and attach a remark via session
  login and the bug/resolve page API. Use when the user asks to mark a bug as
  resolved/已解决/已处理, fix a bug with a comment, or when zentao-cli/MCP
  resolve is unavailable or fails on the target server.
version: 1.0.0
author: Mengfei
license: MIT
metadata:
  hermes:
    tags: [zentao, 禅道, bug, resolve, resolved, 已解决, 已处理, comment, 备注]
    related_skills: [zentao-cli, zentao-bug-comment]
---

# ZenTao Bug Resolve

## Overview

把禅道 Bug 标记为 `resolved`（已解决），并可在同一次操作中附加备注。部分环境下 REST `PUT /api.php/v1|v2/bugs/{id}/resolve` 会返回空响应且不生效；`zentao bug resolve` 也可能失败。本 Skill 使用**会话登录 + 页面 resolve 接口**，这是当前已验证可靠的路径。

优先执行本 Skill 自带脚本，不要手写一次性请求，也不要用网页抓取旁路。

仅需添加备注、不改变状态时，改用 `zentao-bug-comment`。

## When to Use

- 用户要求把 Bug 标为 resolved / 已解决 / 已处理。
- 解决 Bug 的同时要写备注（如 `备注 1`、`comment=1`）。
- 输入是 Bug ID，或形如 `...&m=bug&f=view&bugID=1950` 的禅道 Bug URL。
- `zentao bug resolve` 或 MCP resolve 不可用、报错、或未真正改状态。

Don't use for:

- 只加评论、不改状态 → `zentao-bug-comment`
- 关闭 Bug（`closed`）→ 另走 close 流程，不在本 Skill 范围
- 激活已解决 Bug → `zentao bug activate` / MCP
- 未配置本机禅道认证且无法登录时

## Required Inputs

| 输入 | 说明 |
|---|---|
| Bug | Bug ID，或包含 `bugID=` 的禅道 URL |
| Comment | 可选；解决时附带的备注，用户给了就传 |
| Resolution | 可选；默认 `fixed`（已解决） |
| Auth | 默认读取 `~/.config/zentao/auth.json` |

凭证安全：

- 只读取认证文件用于登录，**不要打印**密码、Token、Cookie。
- 文件不存在时，引导用户执行 `zentao login` 或配置 `~/.config/zentao/auth.json`，不要在对话里收集密码。

## Workflow

1. 确认 Bug ID/URL；确认备注与解决方案（默认 `fixed`）。用户已明确要求时可直接执行。
2. 运行脚本（相对本 Skill 目录）：

```bash
python3 scripts/resolve_bug.py <bugID|bugURL> --comment '<备注>'
```

示例：

```bash
python3 scripts/resolve_bug.py 1950 --comment '1'
python3 scripts/resolve_bug.py \
  'http://192.168.3.15/index.php?m=bug&f=view&bugID=1950' \
  --comment '1'
python3 scripts/resolve_bug.py 1950 --resolution=notrepro --comment '无法复现'
python3 scripts/resolve_bug.py 1950 --comment '1' --format=json
```

3. 根据退出码与输出判定结果；向用户回报 Bug ID、`status=resolved`、`resolution`、备注，以及验证到的 `actionID`。

### 脚本行为

1. `GET /index.php?m=api&f=getSessionID&t=json`
2. `GET/POST /index.php?m=user&f=login&t=json`（密码 `md5(md5(password)+rand)`）
3. `GET /index.php?m=bug&f=resolve&bugID=<id>&t=json` 读取默认 `assignedTo`、`builds`
4. `POST /index.php?m=bug&f=resolve&bugID=<id>`，表单字段：
   - `resolution`（默认 `fixed`）
   - `resolvedBuild`（默认表单首个 build，否则 `trunk`）
   - `assignedTo`（默认表单值 / 创建人）
   - `comment`
5. 成功响应通常含 `"result":"success"` / `保存成功`
6. 默认再用 REST `GET /api.php/v1/bugs/<id>` 校验 `status=resolved` 与 `resolved` 历史

常用选项：

| 选项 | 说明 |
|---|---|
| `--comment` | 备注文本 |
| `--resolution` | `fixed` / `notrepro` / `bydesign` / `duplicate` / `external` / `postponed` / `willnotfix` / `tostory` |
| `--resolved-build` | 解决版本，默认表单或 `trunk` |
| `--assigned-to` | 解决后指派给，默认表单 `assignedTo` |
| `--duplicate-bug` | `resolution=duplicate` 时必填 |
| `--auth-file` | 自定义认证文件 |
| `--skip-verify` | 跳过 REST 校验 |
| `--format text\|json` | 输出格式 |

仅依赖 Python 3 标准库。

## Verification

- 脚本退出码为 `0`
- Bug `status=resolved`，`resolution` 与请求一致
- 历史中有 `action=resolved`；若传了备注，则 `comment` 一致（或等价 `<p>...</p>`）
- 文本输出含「已将 Bug #... 标记为 resolved」，或 JSON `status=success`

## Safety

- 写操作：会改变 Bug 状态并可能通知指派人；仅在用户明确要求时执行。
- **不要**把 REST `PUT /bugs/{id}/resolve` 当作主路径（本环境常见空 200 且不改状态）。
- **不要**用 `PUT /bugs/{id}` 夹带 `comment` 冒充解决。
- 失败时停止并报告；不要反复重试导致重复 resolved 记录。
- 不要展示或回显 `auth.json` 中的敏感字段。

## Troubleshooting

| 现象 | 处理 |
|---|---|
| 认证文件不存在 | 配置 `~/.config/zentao/auth.json` 或 `zentao login` |
| 会话登录失败 | 检查账号密码、URL、网络 |
| 打开解决表单失败 | 无权限、Bug 不存在，或会话未真正登录 |
| `zentao bug resolve` 报 2008/空错误 | 预期可能失败；改用本 Skill 脚本 |
| REST 校验状态仍非 resolved | 查看脚本错误原文；确认账号有「解决问题」权限 |
