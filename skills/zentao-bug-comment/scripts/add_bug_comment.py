#!/usr/bin/env python3
"""Add a comment to a ZenTao bug via session login + action/comment API.

Reads credentials from ~/.config/zentao/auth.json (or --auth-file).
Does not print passwords, tokens, or cookie values.
"""

from __future__ import annotations

import argparse
import hashlib
import http.client
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from http.cookiejar import CookieJar
from pathlib import Path
from typing import Any, Mapping

DEFAULT_AUTH_FILE = Path.home() / ".config" / "zentao" / "auth.json"
BUG_ID_PATTERN = re.compile(r"(?:bugID=|/bugs/)(\d+)")
SUCCESS_MARKERS = (
    "parent.location.reload",
    "parent.location.reload(true)",
)


class CommentError(RuntimeError):
    """Raised when the comment workflow cannot continue."""


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(
        description="Add a comment to a ZenTao bug.",
    )
    parser.add_argument(
        "bug",
        help="Bug ID or ZenTao bug URL containing bugID=<id>.",
    )
    parser.add_argument(
        "comment",
        nargs="?",
        default=None,
        help="Comment text. Prefer --comment for multi-word text.",
    )
    parser.add_argument(
        "--comment",
        dest="comment_flag",
        default=None,
        help="Comment text (recommended).",
    )
    parser.add_argument(
        "--auth-file",
        type=Path,
        default=DEFAULT_AUTH_FILE,
        help=f"Auth JSON path. Default: {DEFAULT_AUTH_FILE}",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=20.0,
        help="HTTP timeout in seconds. Default: 20.",
    )
    parser.add_argument(
        "--skip-verify",
        action="store_true",
        help="Skip REST verification of the new commented action.",
    )
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Output format. Default: text.",
    )
    return parser.parse_args()


def parse_bug_id(raw_bug: str) -> str:
    """Return a bug ID from a plain ID or a ZenTao bug URL."""
    if raw_bug.isdigit():
        return raw_bug

    parsed = urllib.parse.urlparse(raw_bug)
    query = urllib.parse.parse_qs(parsed.query)
    bug_id = query.get("bugID", [None])[0]
    if bug_id and bug_id.isdigit():
        return bug_id

    match = BUG_ID_PATTERN.search(raw_bug)
    if match:
        return match.group(1)

    raise CommentError(f"无法从输入中解析 bug ID: {raw_bug}")


def resolve_comment(positional: str | None, flagged: str | None) -> str:
    """Resolve comment text from positional or --comment."""
    comment = flagged if flagged is not None else positional
    if comment is None or not str(comment).strip():
        raise CommentError("必须提供评论内容：位置参数或 --comment")
    return str(comment)


def validate_server_url(server: str) -> str:
    """Return a normalized HTTP(S) ZenTao server URL."""
    parsed = urllib.parse.urlparse(server)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise CommentError("ZENTAO_URL 必须是 http(s) URL")
    return server.rstrip("/")


def load_auth(auth_file: Path) -> dict[str, str]:
    """Load auth defaults without printing sensitive values."""
    if not auth_file.exists():
        raise CommentError(
            f"认证文件不存在: {auth_file}\n"
            "请先配置 ~/.config/zentao/auth.json，或运行 zentao login。"
        )

    try:
        auth = json.loads(auth_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise CommentError(f"认证文件无法读取或格式错误: {auth_file}: {error}") from error

    required_keys = ("ZENTAO_URL", "ZENTAO_ACCOUNT", "ZENTAO_PASSWORD")
    missing_keys = [key for key in required_keys if not auth.get(key)]
    if missing_keys:
        raise CommentError("认证文件缺少字段: " + ", ".join(missing_keys))

    loaded = {key: str(auth[key]) for key in required_keys}
    loaded["ZENTAO_URL"] = validate_server_url(loaded["ZENTAO_URL"])
    return loaded


def password_strength(password: str) -> int:
    """Approximate ZenTao passwordStrength value."""
    strength = 1
    if len(password) >= 6:
        strength = 1
    if (
        re.search(r"[A-Z]", password)
        and re.search(r"[a-z]", password)
        and re.search(r"\d", password)
    ):
        strength = 2
    if len(password) >= 8 and re.search(r"[^A-Za-z0-9]", password):
        strength = 3
    return strength


def encrypt_password(password: str, rand: str) -> str:
    """ZenTao web login password: md5(md5(password) + rand)."""
    first = hashlib.md5(password.encode("utf-8")).hexdigest()
    return hashlib.md5((first + rand).encode("utf-8")).hexdigest()


class ZenTaoSession:
    """Minimal cookie-aware HTTP client for ZenTao page APIs."""

    def __init__(self, timeout: float) -> None:
        self.timeout = timeout
        self.cookie_jar = CookieJar()
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(self.cookie_jar)
        )

    def request(
        self,
        url: str,
        *,
        method: str = "GET",
        data: Mapping[str, Any] | None = None,
        headers: Mapping[str, str] | None = None,
        json_body: Mapping[str, Any] | None = None,
    ) -> tuple[int, str, dict[str, str]]:
        """Send an HTTP request and return status, body text, headers."""
        request_headers = {
            "User-Agent": "zentao-bug-comment/1.0",
            "Accept": "*/*",
        }
        if headers:
            request_headers.update(headers)

        body: bytes | None = None
        if json_body is not None:
            body = json.dumps(json_body).encode("utf-8")
            request_headers.setdefault("Content-Type", "application/json")
        elif data is not None:
            body = urllib.parse.urlencode(data).encode("utf-8")
            request_headers.setdefault(
                "Content-Type",
                "application/x-www-form-urlencoded",
            )

        request = urllib.request.Request(
            url,
            data=body,
            headers=request_headers,
            method=method,
        )
        try:
            with self.opener.open(request, timeout=self.timeout) as response:
                raw = response.read()
                status = getattr(response, "status", 200)
                response_headers = {k: v for k, v in response.headers.items()}
        except urllib.error.HTTPError as error:
            raw = error.read()
            status = error.code
            response_headers = {k: v for k, v in error.headers.items()}
        except urllib.error.URLError as error:
            raise CommentError(f"请求失败: {url}: {error}") from error

        text = raw.decode("utf-8", errors="replace")
        return status, text, response_headers

    def request_json(
        self,
        url: str,
        *,
        method: str = "GET",
        data: Mapping[str, Any] | None = None,
        headers: Mapping[str, str] | None = None,
        json_body: Mapping[str, Any] | None = None,
    ) -> Any:
        """Send a request and parse JSON."""
        status, text, _ = self.request(
            url,
            method=method,
            data=data,
            headers=headers,
            json_body=json_body,
        )
        try:
            payload = json.loads(text)
        except json.JSONDecodeError as error:
            raise CommentError(f"响应不是 JSON ({status}): {url}") from error
        return payload


def maybe_parse_embedded_json(value: Any) -> Any:
    """Parse ZenTao responses where data is a JSON string."""
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value
    return value


def session_login(session: ZenTaoSession, auth: Mapping[str, str]) -> None:
    """Establish a ZenTao web session using page login APIs."""
    server = auth["ZENTAO_URL"]
    account = auth["ZENTAO_ACCOUNT"]
    password = auth["ZENTAO_PASSWORD"]

    session_payload = session.request_json(
        f"{server}/index.php?m=api&f=getSessionID&t=json"
    )
    session_data = maybe_parse_embedded_json(session_payload.get("data"))
    if not isinstance(session_data, dict) or not session_data.get("sessionID"):
        raise CommentError("无法获取禅道 sessionID")

    login_page = session.request_json(f"{server}/index.php?m=user&f=login&t=json")
    login_data = maybe_parse_embedded_json(login_page.get("data"))
    if not isinstance(login_data, dict) or login_data.get("rand") is None:
        raise CommentError("无法获取登录 rand")

    rand = str(login_data["rand"])
    encrypted = encrypt_password(password, rand)
    login_result = session.request_json(
        f"{server}/index.php?m=user&f=login&t=json",
        method="POST",
        data={
            "account": account,
            "password": encrypted,
            "passwordStrength": password_strength(password),
            "verifyRand": rand,
            "keepLogin": "off",
        },
        headers={
            "X-Requested-With": "XMLHttpRequest",
            "Referer": f"{server}/index.php?m=user&f=login",
        },
    )

    if login_result.get("status") != "success" or "user" not in login_result:
        message = login_result.get("message") or login_result.get("result") or "登录失败"
        raise CommentError(f"禅道会话登录失败: {message}")


def post_bug_comment(
    session: ZenTaoSession,
    server: str,
    bug_id: str,
    comment: str,
) -> None:
    """Post a bug comment through action/comment page API."""
    status, body, _ = session.request(
        f"{server}/index.php?m=action&f=comment&objectType=bug&objectID={bug_id}",
        method="POST",
        data={"comment": comment},
        headers={
            "X-Requested-With": "XMLHttpRequest",
            "Referer": f"{server}/index.php?m=bug&f=view&bugID={bug_id}",
            "Origin": server,
        },
    )
    if status >= 400:
        raise CommentError(f"评论请求失败 HTTP {status}")
    if not any(marker in body for marker in SUCCESS_MARKERS):
        snippet = body.replace("\n", " ")[:240]
        raise CommentError(f"评论接口未返回成功刷新标记: {snippet}")


def fetch_api_token(auth: Mapping[str, str], timeout: float) -> str:
    """Fetch a short-lived REST API token."""
    server = auth["ZENTAO_URL"]
    body = json.dumps(
        {
            "account": auth["ZENTAO_ACCOUNT"],
            "password": auth["ZENTAO_PASSWORD"],
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        f"{server}/api.php/v1/tokens",
        data=body,
        headers={"Content-Type": "application/json", "User-Agent": "zentao-bug-comment/1.0"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, json.JSONDecodeError, http.client.HTTPException) as error:
        raise CommentError(f"获取 API Token 失败: {error}") from error

    token = payload.get("token") if isinstance(payload, dict) else None
    if not token:
        raise CommentError("登录响应中没有 token")
    return str(token)


def fetch_bug_actions(
    server: str,
    bug_id: str,
    token: str,
    timeout: float,
) -> list[dict[str, Any]]:
    """Fetch bug actions via REST API for verification."""
    request = urllib.request.Request(
        f"{server}/api.php/v1/bugs/{bug_id}",
        headers={"Token": token, "User-Agent": "zentao-bug-comment/1.0"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, json.JSONDecodeError, http.client.HTTPException) as error:
        raise CommentError(f"读取 Bug 详情失败: {error}") from error

    actions = payload.get("actions") if isinstance(payload, dict) else None
    if isinstance(actions, dict):
        items = list(actions.values())
    elif isinstance(actions, list):
        items = actions
    else:
        return []

    return [item for item in items if isinstance(item, dict)]


def find_matching_comment(
    actions: list[dict[str, Any]],
    comment: str,
    actor_account: str | None = None,
) -> dict[str, Any] | None:
    """Find the newest matching commented action."""
    normalized = comment.strip()
    candidates: list[dict[str, Any]] = []
    for action in actions:
        if action.get("action") != "commented":
            continue
        action_comment = str(action.get("comment") or "").strip()
        if action_comment != normalized and action_comment != f"<p>{normalized}</p>":
            continue
        candidates.append(action)

    if not candidates:
        return None

    def sort_key(item: dict[str, Any]) -> tuple[str, int]:
        date = str(item.get("date") or "")
        try:
            action_id = int(item.get("id") or 0)
        except (TypeError, ValueError):
            action_id = 0
        return date, action_id

    return sorted(candidates, key=sort_key)[-1]


def main() -> int:
    """Run the add-comment workflow."""
    args = parse_args()
    try:
        bug_id = parse_bug_id(args.bug)
        comment = resolve_comment(args.comment, args.comment_flag)
        auth = load_auth(args.auth_file)
        server = auth["ZENTAO_URL"]

        session = ZenTaoSession(timeout=args.timeout)
        session_login(session, auth)
        post_bug_comment(session, server, bug_id, comment)

        matched: dict[str, Any] | None = None
        if not args.skip_verify:
            token = fetch_api_token(auth, args.timeout)
            actions = fetch_bug_actions(server, bug_id, token, args.timeout)
            matched = find_matching_comment(actions, comment)
            if matched is None:
                raise CommentError(
                    "评论接口已返回成功，但未能在 Bug 历史中验证到对应 commented 记录"
                )

        result = {
            "status": "success",
            "bugID": int(bug_id),
            "comment": comment,
            "server": server,
            "action": None
            if matched is None
            else {
                "id": matched.get("id"),
                "action": matched.get("action"),
                "actor": matched.get("actor"),
                "date": matched.get("date"),
                "comment": matched.get("comment"),
            },
        }
    except CommentError as error:
        if args.format == "json":
            print(json.dumps({"status": "fail", "error": str(error)}, ensure_ascii=False))
        else:
            print(f"添加评论失败: {error}", file=sys.stderr)
        return 1

    if args.format == "json":
        print(json.dumps(result, ensure_ascii=False))
    else:
        print(f"已为 Bug #{bug_id} 添加评论。")
        if matched:
            print(
                f"actionID={matched.get('id')} actor={matched.get('actor')} "
                f"date={matched.get('date')} comment={matched.get('comment')}"
            )
        print(f"查看: {server}/index.php?m=bug&f=view&bugID={bug_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
