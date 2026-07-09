#!/usr/bin/env python3
"""Install user-level skills from M_Skills. Supports Windows, Linux, and macOS."""

from __future__ import annotations

import getpass
import json
import os
import platform
import re
import shutil
import stat
import subprocess
import sys
from subprocess import TimeoutExpired
import tarfile
import tempfile
import zipfile
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from urllib.error import URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

SUPPORTED_SYSTEMS = frozenset({"Windows", "Linux", "Darwin"})
GITHUB_CLI_INSTALL_LINUX_URL = (
    "https://github.com/cli/cli/blob/trunk/docs/install_linux.md"
)
GITHUB_CLI_SKILL_MANUAL_URL = "https://cli.github.com/manual/gh_skill"
BITWARDEN_CLI_DOWNLOAD_URL = "https://github.com/bitwarden/clients/releases"
GITLAB_CLI_RELEASES_URL = "https://gitlab.com/gitlab-org/cli/-/releases"
GITLAB_CLI_LATEST_API_URL = (
    "https://gitlab.com/api/v4/projects/gitlab-org%2Fcli/releases/permalink/latest"
)
M_SKILLS_RAW_BASE_URL = (
    "https://raw.githubusercontent.com/mengfei0053/M_Skills/refs/heads/main"
)
M_SKILLS_CONTENTS_API_URL = (
    "https://api.github.com/repos/mengfei0053/M_Skills/contents/skills?ref=main"
)
PLAYWRIGHT_CLI_REPO_URL = "https://github.com/microsoft/playwright-cli"
ZENTAO_CLI_PACKAGE = "zentao-cli"
ZENTAO_CLI_COMMAND = "zentao"
IMA_AGENT_INTERFACE_URL = "https://ima.qq.com/agent-interface"
JS_BUNDLE_RE = re.compile(
    r"https://static\.ima\.qq\.com/ima/assets/agent-interface/assets/index-[A-Za-z0-9_-]+\.js"
)
IMA_SKILLS_ZIP_RE = re.compile(
    r"https://app-dl\.ima\.qq\.com/skills/ima-skills-[0-9.]+\.zip"
)
IMA_SUBSKILL_FRONTMATTERS = {
    "notes/SKILL.md": """---
name: ima-notes
description: Manage IMA personal notes through OpenAPI, including searching, listing, reading, creating, and appending notes with privacy and UTF-8 safety rules.
version: 1.1.7
author: IMA OpenAPI Skill
license: MIT
metadata:
  hermes:
    tags: [ima, notes, openapi, personal-knowledge]
    related_skills: [ima-skill]
---

""",
    "knowledge-base/SKILL.md": """---
name: ima-knowledge-base
description: Manage IMA knowledge bases through OpenAPI, including file uploads, URL imports, note imports, browsing, and searching with upload safety gates.
version: 1.1.7
author: IMA OpenAPI Skill
license: MIT
metadata:
  hermes:
    tags: [ima, knowledge-base, openapi, file-upload]
    related_skills: [ima-skill]
---

""",
}
USER_AGENT = "M_Skills-install-user-skills/1.0"
TARGET_ENV_VAR = "M_SKILLS_INSTALL_TARGETS"
REPO_DIR_ENV_VAR = "M_SKILLS_REPO_DIR"
SKIP_PLAYWRIGHT_BROWSERS_ENV_VAR = "M_SKILLS_SKIP_PLAYWRIGHT_BROWSERS"
GITLAB_HOST_ENV_VAR = "M_SKILLS_GITLAB_HOST"
GITLAB_API_PROTOCOL_ENV_VAR = "M_SKILLS_GITLAB_API_PROTOCOL"
PLAYWRIGHT_INSTALL_TIMEOUT_SECONDS = 300
ALLOWED_DOWNLOAD_HOSTS = frozenset(
    {
        "api.github.com",
        "raw.githubusercontent.com",
        "ima.qq.com",
        "static.ima.qq.com",
        "app-dl.ima.qq.com",
        "gitlab.com",
    }
)


@dataclass(frozen=True)
class TargetOption:
    key: str
    label: str
    root: Callable[[], Path]
    repo_skill: bool = False
    tree_skill: bool = False


@dataclass
class InstallReport:
    repo_skills: list[str] = field(default_factory=list)
    tree_skills: dict[str, bool] = field(default_factory=dict)
    selected_targets: list[str] = field(default_factory=list)
    installed_rows: list[tuple[str, str, str]] = field(default_factory=list)
    tools: dict[str, str] = field(default_factory=dict)
    ima_credentials_configured: bool = False
    gh_token_configured: bool = False
    glab_token_configured: bool = False


def agents_root() -> Path:
    return home() / ".agents" / "skills"


def claude_root() -> Path:
    return home() / ".claude" / "skills"


def opencode_root() -> Path:
    return home() / ".config" / "opencode" / "skills"


def openclaw_root() -> Path:
    return home() / ".openclaw" / "skills"


def cursor_skills_root() -> Path:
    return home() / ".cursor" / "skills"


def target_options() -> list[TargetOption]:
    return [
        TargetOption("agent", "Agent", agents_root, repo_skill=True, tree_skill=True),
        TargetOption("claude", "Claude", claude_root, repo_skill=True, tree_skill=True),
        TargetOption(
            "opencode", "OpenCode", opencode_root, repo_skill=True, tree_skill=True
        ),
        TargetOption("openclaw", "OpenClaw", openclaw_root, tree_skill=True),
        TargetOption(
            "cursor_skill", "Cursor Skill", cursor_skills_root, tree_skill=True
        ),
    ]


def target_option_map() -> dict[str, TargetOption]:
    return {option.key: option for option in target_options()}


def home() -> Path:
    return Path.home()


def has_skills_dir(path: Path) -> bool:
    skills_dir = path / "skills"
    return skills_dir.is_dir() and any(
        child.is_dir() and (child / "SKILL.md").is_file()
        for child in skills_dir.iterdir()
    )


def candidate_repo_dirs() -> list[Path]:
    script_path = Path(__file__).resolve()
    candidates = [
        script_path.parent,
        script_path.parent.parent,
        Path.cwd(),
        *Path.cwd().parents,
    ]
    seen: set[Path] = set()
    unique: list[Path] = []
    for candidate in candidates:
        try:
            resolved = candidate.expanduser().resolve()
        except OSError:
            resolved = candidate.expanduser()
        if resolved not in seen:
            seen.add(resolved)
            unique.append(resolved)
    return unique


def find_repo_dir(*, strict_env: bool = True) -> Path | None:
    env_value = os.environ.get(REPO_DIR_ENV_VAR, "").strip()
    if env_value:
        configured = Path(env_value).expanduser()
        if has_skills_dir(configured):
            return configured.resolve()
        if strict_env:
            raise FileNotFoundError(
                f"{REPO_DIR_ENV_VAR} does not contain skills/<skill>/SKILL.md entries: {configured}"
            )
        return None

    for candidate in candidate_repo_dirs():
        if has_skills_dir(candidate):
            return candidate
    return None


def repo_dir() -> Path:
    found = find_repo_dir()
    if found is not None:
        return found

    checked = ", ".join(format_path(path) for path in candidate_repo_dirs())
    raise FileNotFoundError(
        "Skills directory not found. Run this script from the M_Skills repository, "
        f"set {REPO_DIR_ENV_VAR}=/path/to/M_Skills, or run the official curl install path. "
        f"Checked: {checked}"
    )


def skills_dir() -> Path:
    return repo_dir() / "skills"


def ima_config_dir() -> Path:
    return home() / ".config" / "ima"


def m_skill_auths_dir() -> Path:
    return home() / ".config" / "m_skill_auths"


def gh_token_file() -> Path:
    return m_skill_auths_dir() / "gh_token"


def glab_token_file() -> Path:
    return m_skill_auths_dir() / "glab_token"


def bw_session_file() -> Path:
    return m_skill_auths_dir() / "bw_session"


def redacted_secret(value: str, *, visible: int = 6) -> str:
    if len(value) <= visible * 2:
        return "*" * len(value)
    return f"{value[:visible]}...{value[-visible:]}"


def persist_bw_session(session: str) -> None:
    session_path = bw_session_file()
    secure_dir(session_path.parent)
    secure_write(session_path, session + "\n")
    os.environ["BW_SESSION"] = session


def load_persisted_bw_session() -> bool:
    session_path = bw_session_file()
    try:
        session = session_path.read_text(encoding="utf-8").strip()
    except OSError:
        return False

    if not session:
        return False

    os.environ["BW_SESSION"] = session
    print(f"BW_SESSION 已从 {session_path} 载入当前安装进程。")
    return True


def parse_target_keys(raw: str) -> set[str]:
    value = raw.strip().lower()
    if value in {"all", "*", ""}:
        return set(target_option_map())
    keys: set[str] = set()
    aliases = {
        "agents": "agent",
        "cursor": "cursor_skill",
        "cursor-skills": "cursor_skill",
        "cursor_skills": "cursor_skill",
    }
    for part in re.split(r"[\s,]+", value):
        if not part:
            continue
        if part.isdigit():
            try:
                index = int(part) - 1
            except ValueError as exc:
                raise ValueError(f"invalid install target number: {part}") from exc
            options = target_options()
            if 0 <= index < len(options):
                keys.add(options[index].key)
            continue
        normalized = aliases.get(part, part)
        if normalized not in target_option_map():
            raise ValueError(f"unknown install target: {part}")
        keys.add(normalized)
    if not keys:
        raise ValueError("no install targets selected")
    return keys


def prompt_install_targets() -> set[str]:
    env_value = os.environ.get(TARGET_ENV_VAR, "").strip()
    if env_value:
        keys = parse_target_keys(env_value)
        print(f"Install targets from {TARGET_ENV_VAR}: {', '.join(sorted(keys))}")
        return keys

    if not sys.stdin.isatty():
        keys = set(target_option_map())
        print("Non-interactive mode: installing to all targets.")
        return keys

    options = target_options()
    print("\n请选择要安装到的配置目录：")
    render_table(
        "可选目标",
        ["编号", "目标", "路径"],
        [
            [str(index), option.label, format_path(option.root())]
            for index, option in enumerate(options, start=1)
        ],
    )
    print("输入编号（可多选，逗号分隔），或输入 all 全选；直接回车默认 all。")
    while True:
        choice = input("请选择 [all]: ").strip()
        try:
            return parse_target_keys(choice or "all")
        except ValueError as exc:
            print(f"无效选择: {exc}")


def selected_target_options(keys: set[str]) -> list[TargetOption]:
    return [option for option in target_options() if option.key in keys]


def check_platform() -> str:
    system = platform.system()
    label = {"Darwin": "macOS"}.get(system, system)
    if system in SUPPORTED_SYSTEMS:
        print(f"Platform: {label} (supported)")
    else:
        print(
            f"Warning: platform '{label}' is not officially tested; "
            f"supported platforms are Windows, Linux, and macOS.",
            file=sys.stderr,
        )
    return system


def validate_download_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname not in ALLOWED_DOWNLOAD_HOSTS:
        raise ValueError(f"Refusing to fetch untrusted URL: {url}")
    return url


def http_get_text(url: str) -> str:
    safe_url = validate_download_url(url)
    request = Request(safe_url, headers={"User-Agent": USER_AGENT})
    # nosemgrep: URL was validated by validate_download_url() before this call.
    with urlopen(request, timeout=60) as response:
        return response.read().decode("utf-8", errors="replace")


def format_bytes(size: int) -> str:
    units = ["B", "KiB", "MiB", "GiB"]
    try:
        value = float(size)
    except (TypeError, ValueError):
        return "unknown size"
    for unit in units:
        if value < 1024 or unit == units[-1]:
            return f"{value:.1f} {unit}" if unit != "B" else f"{size} B"
        value /= 1024
    return f"{size} B"


def render_download_progress(label: str, downloaded: int, total: int | None) -> None:
    if total and total > 0:
        percent = downloaded / total * 100
        message = (
            f"Downloading {label}: {format_bytes(downloaded)} / "
            f"{format_bytes(total)} ({percent:.1f}%)"
        )
    else:
        message = f"Downloading {label}: {format_bytes(downloaded)}"
    print(f"\r{message}", end="", flush=True)


def http_download(url: str, dest: Path) -> None:
    safe_url = validate_download_url(url)
    request = Request(safe_url, headers={"User-Agent": USER_AGENT})
    print(f"Downloading: {safe_url}")
    # nosemgrep: URL was validated by validate_download_url() before this call.
    with urlopen(request, timeout=120) as response, dest.open("wb") as handle:
        total_header = response.headers.get("Content-Length")
        try:
            total = int(total_header) if total_header else None
        except ValueError:
            total = None
        downloaded = 0
        label = dest.name
        while True:
            chunk = response.read(1024 * 256)
            if not chunk:
                break
            handle.write(chunk)
            downloaded += len(chunk)
            render_download_progress(label, downloaded, total)
    print(f"\nDownloaded {dest}: {format_bytes(downloaded)}")


def secure_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    if os.name != "nt":
        path.chmod(stat.S_IRUSR | stat.S_IWUSR)


def secure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    if os.name != "nt":
        path.chmod(stat.S_IRWXU)


def which(command: str) -> str | None:
    return shutil.which(command)


def format_path(path: Path) -> str:
    try:
        return str(path.expanduser().resolve())
    except OSError:
        return str(path.expanduser())


def render_table(title: str, headers: list[str], rows: list[list[str]]) -> None:
    if not rows:
        rows = [["（无）"] + [""] * (len(headers) - 1)]

    widths = [len(header) for header in headers]
    for row in rows:
        for index, cell in enumerate(row):
            widths[index] = max(widths[index], len(cell))

    def border(left: str, mid: str, right: str, fill: str) -> str:
        return left + mid.join(fill * (width + 2) for width in widths) + right

    def format_row(cells: list[str]) -> str:
        padded = [cell.ljust(widths[index]) for index, cell in enumerate(cells)]
        return "│ " + " │ ".join(padded) + " │"

    print(f"\n{title}")
    print(border("┌", "┬", "┐", "─"))
    print(format_row(headers))
    print(border("├", "┼", "┤", "─"))
    for row in rows:
        print(format_row(row))
    print(border("└", "┴", "┘", "─"))


def run_command(
    args: list[str],
    *,
    cwd: Path | None = None,
    check: bool = True,
    env: dict[str, str] | None = None,
    timeout: int | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=str(cwd) if cwd else None,
        check=check,
        text=True,
        env=env,
        timeout=timeout,
    )


def run_bash_command(
    command: str, *, check: bool = True
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["bash", "-lc", command], check=check, text=True)


def command_succeeds(args: list[str]) -> bool:
    return (
        subprocess.run(
            args,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            text=True,
            check=False,
        ).returncode
        == 0
    )


def parse_bitwarden_status(raw_status: str) -> str:
    value = raw_status.strip()
    if not value:
        return ""

    lowered = value.lower()
    if lowered in {"locked", "unlocked", "unauthenticated"}:
        return lowered

    try:
        payload = json.loads(value)
    except json.JSONDecodeError as exc:
        _ = exc
        return lowered

    if isinstance(payload, dict) and isinstance(payload.get("status"), str):
        return payload["status"].strip().lower()
    return lowered


def bitwarden_session_status(bw_path: str, session: str) -> str:
    if not session.strip():
        return ""

    try:
        result = subprocess.run(
            [bw_path, "status", "--raw", "--session", session],
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
        )
    except OSError:
        return ""
    except TimeoutExpired:
        return ""

    if result.returncode != 0:
        return ""
    return parse_bitwarden_status(result.stdout)


def bitwarden_session_is_unlocked(bw_path: str, session: str, label: str) -> bool:
    status = bitwarden_session_status(bw_path, session)
    if status == "unlocked":
        return True
    if status:
        print(
            f"警告: {label} 中的 BW_SESSION 状态为 {status}，"
            "将尝试其他 session 或重新解锁。",
            file=sys.stderr,
        )
    else:
        print(
            f"警告: {label} 中的 BW_SESSION 不可用或已过期，"
            "将尝试其他 session 或重新解锁。",
            file=sys.stderr,
        )
    return False


def should_read_bitwarden_password_from_tty() -> bool:
    return os.name != "nt" and not sys.stdin.isatty()


def unlock_bitwarden_vault(bw_path: str) -> bool:
    print("Bitwarden vault 当前为 locked，正在执行 `bw unlock --raw`。")
    print("请按 Bitwarden CLI 提示输入主密码。")
    try:
        if should_read_bitwarden_password_from_tty():
            with Path("/dev/tty").open("r", encoding="utf-8") as stdin_handle:
                result = subprocess.run(
                    [bw_path, "unlock", "--raw"],
                    stdin=stdin_handle,
                    stdout=subprocess.PIPE,
                    text=True,
                    check=False,
                    timeout=120,
                )
        else:
            result = subprocess.run(
                [bw_path, "unlock", "--raw"],
                stdout=subprocess.PIPE,
                text=True,
                check=False,
                timeout=120,
            )
    except OSError:
        error = sys.exc_info()[1]
        print(f"错误: 无法执行 `bw unlock --raw`: {error}", file=sys.stderr)
        if should_read_bitwarden_password_from_tty():
            print(
                "当前命令的标准输入不是交互式终端，且无法打开 /dev/tty 读取主密码。",
                file=sys.stderr,
            )
            print(
                "请先在本地终端执行 `export BW_SESSION=$(bw unlock --raw)`，再重新运行安装脚本；"
                f"或确认 {bw_session_file()} 中保存的是未过期 session。",
                file=sys.stderr,
            )
        return False
    except TimeoutExpired:
        error = sys.exc_info()[1]
        print(f"错误: 无法执行 `bw unlock --raw`: {error}", file=sys.stderr)
        return False

    if result.returncode != 0:
        print(
            "错误: `bw unlock --raw` 执行失败，请确认主密码正确后重试。",
            file=sys.stderr,
        )
        return False

    session = result.stdout.strip()
    if not session:
        print("错误: `bw unlock --raw` 未返回 BW_SESSION。", file=sys.stderr)
        return False

    persist_bw_session(session)
    print(f"Bitwarden unlock 返回的 session（脱敏）: {redacted_secret(session)}")
    print(f"Bitwarden vault 已解锁，完整 session 已写入: {bw_session_file()}")
    print("BW_SESSION 已设置到当前安装进程，后续 Bitwarden 读取会自动复用。")
    return True


def ensure_bw_session(bw_path: str, *, force_unlock: bool = False) -> bool:
    if force_unlock:
        return unlock_bitwarden_vault(bw_path)

    env_session = os.environ.get("BW_SESSION", "").strip()
    if env_session and bitwarden_session_is_unlocked(
        bw_path, env_session, "环境变量 BW_SESSION"
    ):
        return True

    if load_persisted_bw_session():
        file_session = os.environ.get("BW_SESSION", "").strip()
        if bitwarden_session_is_unlocked(
            bw_path, file_session, str(bw_session_file())
        ):
            return True

    return unlock_bitwarden_vault(bw_path)


def require_bitwarden_cli(report: InstallReport) -> bool:
    bw_path = which("bw")
    if bw_path is None:
        print(
            "错误: 未找到 Bitwarden CLI 命令 `bw`。这是运行安装脚本的必需前置条件。",
            file=sys.stderr,
        )
        print(
            f"请下载并安装 Bitwarden CLI: {BITWARDEN_CLI_DOWNLOAD_URL}",
            file=sys.stderr,
        )
        print("安装后运行 `bw login` 完成登录，再重新执行本脚本。", file=sys.stderr)
        report.tools["bw"] = "not found"
        return False

    report.tools["bw"] = bw_path
    try:
        result = subprocess.run(
            [bw_path, "status", "--raw"],
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        print(f"错误: 无法检测 Bitwarden CLI 登录状态: {exc}", file=sys.stderr)
        print("请确认 `bw status --raw` 可正常执行后重试。", file=sys.stderr)
        report.tools["bw"] = f"status check failed: {exc}"
        return False

    status = parse_bitwarden_status(result.stdout)
    if result.returncode != 0:
        stderr = result.stderr.strip() or "unknown error"
        print(f"错误: `bw status --raw` 执行失败: {stderr}", file=sys.stderr)
        print("请先运行 `bw login` 完成登录，再重新执行本脚本。", file=sys.stderr)
        report.tools["bw"] = f"status failed: {stderr}"
        return False

    if status == "unauthenticated" or not status:
        print("错误: Bitwarden CLI 已安装，但当前尚未登录。", file=sys.stderr)
        print("请先运行 `bw login` 完成登录，再重新执行本脚本。", file=sys.stderr)
        report.tools["bw"] = status or "empty status"
        return False

    if status not in {"locked", "unlocked"}:
        print(
            f"错误: 无法识别 Bitwarden CLI 登录状态: {status!r}。",
            file=sys.stderr,
        )
        print(
            "请确认 `bw status --raw` 输出为 locked/unlocked，或 JSON 中包含 status=locked/unlocked 后重试。",
            file=sys.stderr,
        )
        report.tools["bw"] = f"unexpected status: {status}"
        return False

    if status == "locked":
        if not ensure_bw_session(bw_path):
            report.tools["bw"] = "locked"
            return False
        status = "unlocked"
    elif status == "unlocked" and not ensure_bw_session(bw_path):
        report.tools["bw"] = "unlocked; session unavailable"
        return False

    report.tools["bw"] = f"{bw_path} ({status})"
    print(f"Bitwarden CLI: {bw_path} ({status})")
    return True


def sudo_args() -> list[str] | None:
    if os.name != "nt" and hasattr(os, "geteuid") and os.geteuid() == 0:
        return []
    if which("sudo") is not None:
        return ["sudo"]
    return None


def sudo_prefix() -> str | None:
    args = sudo_args()
    if args is None:
        return None
    return " ".join(args) + (" " if args else "")


def glab_archive_arch() -> str | None:
    machine = platform.machine().lower()
    if machine in {"x86_64", "amd64"}:
        return "amd64"
    if machine in {"aarch64", "arm64"}:
        return "arm64"
    if machine in {"i386", "i686", "x86"}:
        return "386"
    if machine.startswith("armv6"):
        return "armv6"
    if machine in {"ppc64le", "s390x"}:
        return machine
    return None


def glab_windows_installer_arch() -> str | None:
    archive_arch = glab_archive_arch()
    if archive_arch == "amd64":
        return "x86_64"
    if archive_arch == "arm64":
        return "arm64"
    return None


def latest_glab_release() -> tuple[str, dict[str, str]]:
    try:
        payload = json.loads(http_get_text(GITLAB_CLI_LATEST_API_URL))
    except json.JSONDecodeError as exc:
        raise RuntimeError("Invalid GitLab CLI latest release response") from exc

    tag_name = payload.get("tag_name")
    links = payload.get("assets", {}).get("links", [])
    if not isinstance(tag_name, str) or not isinstance(links, list):
        raise RuntimeError("Unexpected GitLab CLI latest release response")

    assets: dict[str, str] = {}
    for link in links:
        if not isinstance(link, dict):
            continue
        name = link.get("name")
        url = link.get("direct_asset_url") or link.get("url")
        if isinstance(name, str) and isinstance(url, str):
            assets[name] = url

    if not assets:
        raise RuntimeError("No GitLab CLI release assets found")
    return tag_name.lstrip("v"), assets


def glab_asset_url(assets: dict[str, str], asset_name: str) -> str:
    url = assets.get(asset_name)
    if url is None:
        raise RuntimeError(f"GitLab CLI release asset not found: {asset_name}")
    return url


def download_glab_asset(assets: dict[str, str], asset_name: str, dest: Path) -> Path:
    url = glab_asset_url(assets, asset_name)
    dest.mkdir(parents=True, exist_ok=True)
    asset_path = dest / asset_name
    http_download(url, asset_path)
    return asset_path


def install_glab_tarball(archive_path: Path) -> Path:
    with tempfile.TemporaryDirectory() as tmp:
        extract_dir = Path(tmp)
        with tarfile.open(archive_path, "r:gz") as archive:
            archive.extractall(extract_dir)

        candidates: list[Path] = []
        for path in extract_dir.rglob("glab"):
            try:
                if path.is_file() and os.access(path, os.X_OK):
                    candidates.append(path)
            except OSError:
                continue
        if not candidates:
            raise RuntimeError(f"glab binary not found in {archive_path}")

        source = candidates[0]
        sudo = sudo_args()
        if sudo is not None:
            dest = Path("/usr/local/bin/glab")
            run_command([*sudo, "install", "-m", "755", str(source), str(dest)])
            return dest

        user_bin = home() / ".local" / "bin"
        user_bin.mkdir(parents=True, exist_ok=True)
        dest = user_bin / "glab"
        shutil.copy2(source, dest)
        dest.chmod(stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)
        os.environ["PATH"] = f"{user_bin}{os.pathsep}{os.environ.get('PATH', '')}"
        return dest


def install_glab_linux_package(
    version: str, assets: dict[str, str], tmp_dir: Path
) -> bool:
    arch = glab_archive_arch()
    if arch is None:
        raise RuntimeError(
            f"Unsupported Linux architecture for glab: {platform.machine()}"
        )

    sudo = sudo_args()
    if sudo is not None and which("apt") is not None and which("dpkg") is not None:
        package = download_glab_asset(
            assets, f"glab_{version}_linux_{arch}.deb", tmp_dir
        )
        run_command([*sudo, "apt", "install", "-y", str(package)])
        return True

    if sudo is not None and which("dnf") is not None:
        package = download_glab_asset(
            assets, f"glab_{version}_linux_{arch}.rpm", tmp_dir
        )
        run_command([*sudo, "dnf", "install", "-y", str(package)])
        return True

    if sudo is not None and which("yum") is not None:
        package = download_glab_asset(
            assets, f"glab_{version}_linux_{arch}.rpm", tmp_dir
        )
        run_command([*sudo, "yum", "install", "-y", str(package)])
        return True

    if sudo is not None and which("zypper") is not None:
        package = download_glab_asset(
            assets, f"glab_{version}_linux_{arch}.rpm", tmp_dir
        )
        run_command([*sudo, "zypper", "install", "-y", str(package)])
        return True

    if sudo is not None and which("apk") is not None:
        package = download_glab_asset(
            assets, f"glab_{version}_linux_{arch}.apk", tmp_dir
        )
        run_command([*sudo, "apk", "add", "--allow-untrusted", str(package)])
        return True

    archive = download_glab_asset(
        assets, f"glab_{version}_linux_{arch}.tar.gz", tmp_dir
    )
    installed_path = install_glab_tarball(archive)
    print(f"glab installed from tarball: {installed_path}")
    return True


def install_glab_windows_package(
    version: str, assets: dict[str, str], tmp_dir: Path
) -> bool:
    arch = glab_windows_installer_arch()
    if arch is None:
        raise RuntimeError(
            f"Unsupported Windows architecture for glab: {platform.machine()}"
        )

    installer = download_glab_asset(
        assets, f"glab_{version}_Windows_{arch}_installer.exe", tmp_dir
    )
    run_command([str(installer), "/S"], timeout=300)
    return True


def install_glab_cli(report: InstallReport, system: str) -> bool:
    glab_path = which("glab")
    if glab_path is not None:
        report.tools["glab"] = glab_path
        print(f"GitLab CLI already installed: {glab_path}")
        return True

    print("")
    print("Installing GitLab CLI (glab) ...")
    try:
        if system == "Darwin":
            if which("brew") is None:
                raise RuntimeError(
                    "Homebrew is required to install glab on macOS. "
                    f"Install Homebrew or download glab from {GITLAB_CLI_RELEASES_URL}."
                )
            run_command(["brew", "install", "glab"])
        else:
            version, assets = latest_glab_release()
            with tempfile.TemporaryDirectory() as tmp:
                tmp_dir = Path(tmp)
                if system == "Linux":
                    install_glab_linux_package(version, assets, tmp_dir)
                elif system == "Windows":
                    install_glab_windows_package(version, assets, tmp_dir)
                else:
                    raise RuntimeError(
                        f"Automatic glab installation is unsupported on {system}. "
                        f"Download from {GITLAB_CLI_RELEASES_URL}."
                    )
    except (OSError, RuntimeError, subprocess.CalledProcessError, URLError) as exc:
        print(f"Failed to install GitLab CLI (glab): {exc}", file=sys.stderr)
        print(f"Download manually: {GITLAB_CLI_RELEASES_URL}", file=sys.stderr)
        report.tools["glab"] = "not found"
        return False

    glab_path = which("glab")
    report.tools["glab"] = glab_path or "installed; restart shell if not on PATH"
    if glab_path is None:
        print("glab installed, but it is not currently on PATH.", file=sys.stderr)
        return False

    print(f"GitLab CLI installation completed: {glab_path}")
    return True

def install_zentao_cli(report: InstallReport) -> bool:
    zentao_path = which(ZENTAO_CLI_COMMAND)
    if zentao_path is not None:
        report.tools["zentao"] = zentao_path
        print(f"ZenTao CLI already installed: {zentao_path}")
        return True

    bun_path = which("bun")
    report.tools["bun"] = bun_path or "not found"
    if bun_path is None:
        print(
            "Bun is required to install ZenTao CLI. Install Bun, then run `bun install -g zentao-cli`.",
            file=sys.stderr,
        )
        report.tools["zentao"] = "not found"
        return False

    print("")
    print("Installing ZenTao CLI (bun install -g zentao-cli) ...")
    try:
        run_command([bun_path, "install", "-g", ZENTAO_CLI_PACKAGE])
    except (OSError, subprocess.CalledProcessError) as exc:
        print(f"Failed to install ZenTao CLI: {exc}", file=sys.stderr)
        report.tools["zentao"] = "not found"
        return False

    zentao_path = which(ZENTAO_CLI_COMMAND)
    report.tools["zentao"] = zentao_path or "installed; restart shell if not on PATH"
    if zentao_path is None:
        print(
            "ZenTao CLI installed, but `zentao` is not currently on PATH.",
            file=sys.stderr,
        )
        return False

    print(f"ZenTao CLI installation completed: {zentao_path}")
    return True


def env_flag_enabled(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes", "on"}


def playwright_linux_host_platform_fallback() -> str | None:
    if platform.system() != "Linux":
        return None
    machine = platform.machine().lower()
    if machine in {"x86_64", "amd64"}:
        return "ubuntu24.04-x64"
    if machine in {"aarch64", "arm64"}:
        return "ubuntu24.04-arm64"
    return None


def playwright_install_env() -> tuple[dict[str, str] | None, str | None]:
    fallback = playwright_linux_host_platform_fallback()
    if fallback is None:
        return None, None
    install_env = os.environ.copy()
    install_env.setdefault("PLAYWRIGHT_HOST_PLATFORM_OVERRIDE", fallback)
    return install_env, install_env["PLAYWRIGHT_HOST_PLATFORM_OVERRIDE"]


def record_install(report: InstallReport, label: str, skill: str, dest: Path) -> None:
    report.installed_rows.append((label, skill, format_path(dest)))


def file_content_matches(src: Path, dest: Path) -> bool:
    try:
        return dest.is_file() and src.read_bytes() == dest.read_bytes()
    except OSError:
        return False


def bytes_content_matches(content: bytes, dest: Path) -> bool:
    try:
        return dest.is_file() and content == dest.read_bytes()
    except OSError:
        return False


def tree_file_map(root: Path) -> dict[Path, bytes] | None:
    files: dict[Path, bytes] = {}
    try:
        for path in root.rglob("*"):
            if path.is_dir():
                continue
            if not path.is_file():
                return None
            files[path.relative_to(root)] = path.read_bytes()
    except OSError:
        return None
    return files


def skill_tree_matches(src: Path, dest: Path) -> bool:
    if not dest.is_dir():
        return False
    src_files = tree_file_map(src)
    dest_files = tree_file_map(dest)
    return src_files is not None and src_files == dest_files


def install_skill_file(src: Path, dest: Path) -> None:
    if file_content_matches(src, dest):
        print(f"already installed: {dest}")
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)
    print(f"installed: {dest}")


def install_skill_content(content: str, dest: Path) -> None:
    encoded = content.encode("utf-8")
    if bytes_content_matches(encoded, dest):
        print(f"already installed: {dest}")
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(encoded)
    print(f"installed: {dest}")


def install_skill_tree(src: Path, dest: Path) -> None:
    if skill_tree_matches(src, dest):
        print(f"already installed: {dest}")
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(src, dest)
    except OSError as exc:
        raise RuntimeError(
            f"Failed to install skill tree from {src} to {dest}: {exc}"
        ) from exc
    print(f"installed: {dest}")


def install_repo_user_skills_from_local(
    report: InstallReport,
    targets: set[str],
    skills_root: Path,
) -> None:
    options = selected_target_options(targets)
    for skill_dir in sorted(skills_root.iterdir()):
        if not skill_dir.is_dir():
            continue
        src = skill_dir / "SKILL.md"
        if not src.is_file():
            continue
        skill_name = skill_dir.name
        report.repo_skills.append(skill_name)
        for option in options:
            if option.repo_skill:
                dest = option.root() / skill_name / "SKILL.md"
                install_skill_file(src, dest)
                record_install(report, option.label, skill_name, dest)
            elif option.tree_skill:
                dest = option.root() / skill_name
                install_skill_tree(skill_dir, dest)
                record_install(report, option.label, skill_name, dest)


def fetch_remote_user_skill_names() -> list[str]:
    try:
        payload = json.loads(http_get_text(M_SKILLS_CONTENTS_API_URL))
    except json.JSONDecodeError as exc:
        raise RuntimeError("Invalid GitHub contents API response for skills") from exc
    if not isinstance(payload, list):
        raise RuntimeError("Unexpected GitHub contents API response for skills")
    skill_names = sorted(
        item["name"]
        for item in payload
        if isinstance(item, dict)
        and item.get("type") == "dir"
        and isinstance(item.get("name"), str)
    )
    if not skill_names:
        raise RuntimeError("No remote skills found in M_Skills")
    return skill_names


def fetch_remote_user_skill(skill_name: str) -> str:
    return http_get_text(f"{M_SKILLS_RAW_BASE_URL}/skills/{skill_name}/SKILL.md")


def install_repo_user_skills_from_remote(
    report: InstallReport, targets: set[str]
) -> None:
    print(
        "Local skills directory not found; installing user skills from GitHub raw content."
    )
    options = selected_target_options(targets)
    for skill_name in fetch_remote_user_skill_names():
        try:
            content = fetch_remote_user_skill(skill_name)
        except URLError as exc:
            raise RuntimeError(
                f"Failed to fetch remote skill {skill_name}: {exc}"
            ) from exc
        report.repo_skills.append(skill_name)
        for option in options:
            dest = option.root() / skill_name / "SKILL.md"
            install_skill_content(content, dest)
            record_install(report, option.label, skill_name, dest)


def install_repo_user_skills(report: InstallReport, targets: set[str]) -> None:
    root = find_repo_dir(strict_env=True)
    if root is None:
        install_repo_user_skills_from_remote(report, targets)
    else:
        install_repo_user_skills_from_local(report, targets, root / "skills")

    print("User-level skills installation completed.")


def install_tree_skill(
    report: InstallReport,
    targets: set[str],
    skill_name: str,
    skill_src: Path,
) -> None:
    for option in selected_target_options(targets):
        if not option.tree_skill:
            continue
        dest = option.root() / skill_name
        install_skill_tree(skill_src, dest)
        record_install(report, option.label, skill_name, dest)

def tree_skill_installed_in_targets(targets: set[str], skill_name: str) -> bool:
    options = [option for option in selected_target_options(targets) if option.tree_skill]
    return all((option.root() / skill_name / "SKILL.md").is_file() for option in options)


def local_skill_target_matches(
    local_repo: Path, option: TargetOption, skill_name: str
) -> bool:
    skill_dir = local_repo / "skills" / skill_name
    if option.repo_skill:
        return file_content_matches(
            skill_dir / "SKILL.md", option.root() / skill_name / "SKILL.md"
        )
    if option.tree_skill:
        return skill_tree_matches(skill_dir, option.root() / skill_name)
    return True


def has_yaml_frontmatter(path: Path) -> bool:
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return False

    if not text.startswith("---\n"):
        return False

    return "\n---\n" in text[4:]


def ensure_ima_subskill_frontmatters(skill_src: Path) -> None:
    for relative_path, frontmatter in IMA_SUBSKILL_FRONTMATTERS.items():
        skill_file = skill_src / relative_path
        if not skill_file.is_file() or has_yaml_frontmatter(skill_file):
            continue

        content = skill_file.read_text(encoding="utf-8")
        skill_file.write_text(frontmatter + content, encoding="utf-8")


def install_github_cli(report: InstallReport, system: str) -> bool:
    gh_path = which("gh")
    if gh_path is not None:
        report.tools["gh"] = gh_path
        print(f"GitHub CLI already installed: {gh_path}")
        return True

    if system == "Darwin":
        if which("brew") is None:
            print(
                "GitHub CLI (gh) is not installed and Homebrew was not found. "
                "Install Homebrew or install gh manually from cli.github.com.",
                file=sys.stderr,
            )
            report.tools["gh"] = "not found"
            return False
        print("")
        print("Installing GitHub CLI (gh) with Homebrew (brew install gh) ...")
        try:
            run_command(["brew", "install", "gh"])
        except subprocess.CalledProcessError as exc:
            print(f"Failed to install GitHub CLI (gh): {exc}", file=sys.stderr)
            report.tools["gh"] = "not found"
            return False
    elif system == "Linux":
        sudo = sudo_prefix()
        if sudo is None:
            print(
                "GitHub CLI installation requires root privileges or sudo.",
                file=sys.stderr,
            )
            report.tools["gh"] = "not found"
            return False

        print("")
        print(
            f"Installing GitHub CLI (gh) using official Linux package guidance ({GITHUB_CLI_INSTALL_LINUX_URL}) ..."
        )
        try:
            if which("apt") is not None and which("dpkg") is not None:
                run_bash_command(
                    f"(type -p wget >/dev/null || ({sudo}apt update && {sudo}apt install wget -y)) "
                    f"&& {sudo}mkdir -p -m 755 /etc/apt/keyrings "
                    "&& out=$(mktemp) && wget -nv -O$out https://cli.github.com/packages/githubcli-archive-keyring.gpg "
                    f"&& cat $out | {sudo}tee /etc/apt/keyrings/githubcli-archive-keyring.gpg > /dev/null "
                    f"&& {sudo}chmod go+r /etc/apt/keyrings/githubcli-archive-keyring.gpg "
                    f"&& {sudo}mkdir -p -m 755 /etc/apt/sources.list.d "
                    '&& echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" '
                    f"| {sudo}tee /etc/apt/sources.list.d/github-cli.list > /dev/null "
                    f"&& {sudo}apt update "
                    f"&& {sudo}apt install gh -y"
                )
            elif which("dnf") is not None:
                run_command(
                    [
                        *(sudo.split() if sudo else []),
                        "dnf",
                        "install",
                        "dnf-command(config-manager)",
                        "-y",
                    ]
                )
                run_command(
                    [
                        *(sudo.split() if sudo else []),
                        "dnf",
                        "config-manager",
                        "--add-repo",
                        "https://cli.github.com/packages/rpm/gh-cli.repo",
                    ]
                )
                run_command(
                    [*(sudo.split() if sudo else []), "dnf", "install", "gh", "-y"]
                )
            elif which("yum") is not None:
                run_command(
                    [
                        *(sudo.split() if sudo else []),
                        "yum",
                        "install",
                        "yum-utils",
                        "-y",
                    ]
                )
                run_command(
                    [
                        *(sudo.split() if sudo else []),
                        "yum-config-manager",
                        "--add-repo",
                        "https://cli.github.com/packages/rpm/gh-cli.repo",
                    ]
                )
                run_command(
                    [*(sudo.split() if sudo else []), "yum", "install", "gh", "-y"]
                )
            elif which("zypper") is not None:
                run_command(
                    [
                        *(sudo.split() if sudo else []),
                        "zypper",
                        "addrepo",
                        "https://cli.github.com/packages/rpm/gh-cli.repo",
                    ]
                )
                run_command([*(sudo.split() if sudo else []), "zypper", "ref"])
                run_command(
                    [*(sudo.split() if sudo else []), "zypper", "install", "-y", "gh"]
                )
            else:
                print(
                    "No supported Linux package manager found for automatic gh installation.",
                    file=sys.stderr,
                )
                report.tools["gh"] = "not found"
                return False
        except subprocess.CalledProcessError as exc:
            print(f"Failed to install GitHub CLI (gh): {exc}", file=sys.stderr)
            report.tools["gh"] = "not found"
            return False
    else:
        print(
            "GitHub CLI (gh) is not installed; automatic installation is enabled on macOS and Linux only. "
            f"See {GITHUB_CLI_INSTALL_LINUX_URL} for Linux and cli.github.com for other platforms.",
            file=sys.stderr,
        )
        report.tools["gh"] = "not found"
        return False

    gh_path = which("gh")
    report.tools["gh"] = gh_path or "not found"
    if gh_path is None:
        print("gh not found in PATH after installation", file=sys.stderr)
        return False

    print(f"GitHub CLI installation completed: {gh_path}")
    return True


def install_repo_user_skills_with_gh(report: InstallReport, targets: set[str]) -> bool:
    local_repo = find_repo_dir(strict_env=False)
    if local_repo is None:
        report.tools["gh skill"] = "skipped (no local repo)"
        print(
            "Skipping gh skill install because no local M_Skills repository was found."
        )
        return True

    gh_path = which("gh")
    if gh_path is None:
        report.tools["gh skill"] = "gh not found"
        return False
    if not command_succeeds([gh_path, "skill", "--help"]):
        report.tools["gh skill"] = "not available"
        print(
            f"GitHub CLI is installed, but 'gh skill' is unavailable. See {GITHUB_CLI_SKILL_MANUAL_URL}.",
            file=sys.stderr,
        )
        return False

    print("")
    print(
        f"Installing local user skills through 'gh skill install' ({GITHUB_CLI_SKILL_MANUAL_URL}) ..."
    )
    ok = True
    attempted = 0
    skipped = 0
    for skill_name in report.repo_skills:
        for option in selected_target_options(targets):
            if local_skill_target_matches(local_repo, option, skill_name):
                print(f"gh skill skipped: {option.label} / {skill_name} already installed")
                skipped += 1
                continue
            attempted += 1
            try:
                run_command(
                    [
                        gh_path,
                        "skill",
                        "install",
                        str(local_repo),
                        skill_name,
                        "--from-local",
                        "--dir",
                        str(option.root()),
                        "--force",
                    ]
                )
                print(f"gh skill installed: {option.label} / {skill_name}")
            except subprocess.CalledProcessError as exc:
                print(
                    f"Failed to install {skill_name} with gh skill for {option.label}: {exc}",
                    file=sys.stderr,
                )
                ok = False
    if attempted == 0 and skipped > 0:
        report.tools["gh skill"] = "skipped (already installed)"
    else:
        report.tools["gh skill"] = "available" if ok else "failed"
    return ok


def fetch_ima_skills_download_url(page_url: str) -> str:
    html = http_get_text(page_url)
    js_matches = [
        match for match in JS_BUNDLE_RE.findall(html) if "legacy" not in match
    ]
    if not js_matches:
        raise RuntimeError(f"Failed to locate agent-interface JS bundle on {page_url}")
    js_url = js_matches[0]

    js_text = http_get_text(js_url)
    zip_matches = IMA_SKILLS_ZIP_RE.findall(js_text)
    if not zip_matches:
        raise RuntimeError(f"Failed to locate IMA skills zip URL in {js_url}")
    return zip_matches[0]


def install_playwright_cli_and_skills(report: InstallReport, targets: set[str]) -> bool:
    playwright_cli = which("playwright-cli")
    cli_already_installed = playwright_cli is not None
    node_path = which("node")
    npm_path = which("npm")
    if node_path is not None:
        report.tools["node"] = node_path
    if npm_path is not None:
        report.tools["npm"] = npm_path

    if cli_already_installed:
        report.tools["playwright-cli"] = playwright_cli or "not found"
        print(f"Playwright CLI already installed: {playwright_cli}")
    else:
        if npm_path is None:
            print(
                f"npm is required to install playwright-cli ({PLAYWRIGHT_CLI_REPO_URL})",
                file=sys.stderr,
            )
            return False
        if node_path is None:
            print("Node.js 18+ is required to install playwright-cli", file=sys.stderr)
            return False

        print("")
        print(f"Installing @playwright/cli globally ({PLAYWRIGHT_CLI_REPO_URL}) ...")
        try:
            run_command([npm_path, "install", "-g", "@playwright/cli@latest"])
        except subprocess.CalledProcessError as exc:
            print(f"Failed to install @playwright/cli: {exc}", file=sys.stderr)
            return False

        report.tools["node"] = which("node") or "not found"
        report.tools["npm"] = which("npm") or "not found"

        playwright_cli = which("playwright-cli")
        report.tools["playwright-cli"] = playwright_cli or "not found"
        if playwright_cli is None:
            print(
                "playwright-cli not found in PATH after npm global install",
                file=sys.stderr,
            )
            print(
                "Ensure the npm global bin directory is on PATH, then re-run.",
                file=sys.stderr,
            )
            report.tree_skills["playwright-cli"] = False
            return False

    if cli_already_installed and tree_skill_installed_in_targets(
        targets, "playwright-cli"
    ):
        print("playwright-cli skill already installed in selected directories.")
        report.tools["playwright browsers"] = "skipped (playwright-cli already installed)"
        report.tree_skills["playwright-cli"] = True
        return True

    npm_path = which("npm")
    if npm_path is None:
        print(
            "npm is required to locate the installed playwright-cli skill bundle.",
            file=sys.stderr,
        )
        report.tree_skills["playwright-cli"] = False
        return False

    try:
        npm_root = subprocess.check_output([npm_path, "root", "-g"], text=True).strip()
    except (OSError, subprocess.CalledProcessError) as exc:
        print(f"Failed to locate npm global root: {exc}", file=sys.stderr)
        report.tree_skills["playwright-cli"] = False
        return False

    skill_src = Path(npm_root) / "@playwright" / "cli" / "skills" / "playwright-cli"
    if not (skill_src / "SKILL.md").is_file():
        print(f"playwright-cli skill bundle not found at {skill_src}", file=sys.stderr)
        report.tree_skills["playwright-cli"] = False
        return False

    print("Installing playwright-cli skill to selected directories ...")
    install_tree_skill(report, targets, "playwright-cli", skill_src)

    if cli_already_installed:
        print(
            "Skipping Playwright browser dependencies because playwright-cli was already installed."
        )
        report.tools["playwright browsers"] = "skipped (playwright-cli already installed)"
        report.tree_skills["playwright-cli"] = True
        return True

    if env_flag_enabled(SKIP_PLAYWRIGHT_BROWSERS_ENV_VAR):
        print(
            f"Skipping Playwright browser dependencies because {SKIP_PLAYWRIGHT_BROWSERS_ENV_VAR}=1."
        )
        report.tools["playwright browsers"] = "skipped by env"
        report.tree_skills["playwright-cli"] = True
        print("playwright-cli installation completed.")
        return True

    install_env, fallback = playwright_install_env()
    if fallback is None:
        print(
            "Bootstrapping Playwright browser dependencies (playwright-cli install) ..."
        )
    else:
        print(
            "Bootstrapping Playwright browser dependencies "
            f"(PLAYWRIGHT_HOST_PLATFORM_OVERRIDE={fallback} playwright-cli install) ..."
        )

    try:
        run_command(
            [playwright_cli, "install"],
            cwd=home(),
            env=install_env,
            timeout=PLAYWRIGHT_INSTALL_TIMEOUT_SECONDS,
        )
        report.tools["playwright browsers"] = (
            f"installed via {fallback} fallback" if fallback else "installed"
        )
    except subprocess.TimeoutExpired as exc:
        print(
            "Warning: playwright-cli install timed out after "
            f"{PLAYWRIGHT_INSTALL_TIMEOUT_SECONDS}s; CLI and skill are installed, "
            "but browser dependencies may be missing. Re-run manually or set "
            f"{SKIP_PLAYWRIGHT_BROWSERS_ENV_VAR}=1 to skip this step. ({exc})",
            file=sys.stderr,
        )
        report.tools["playwright browsers"] = "timed out/skipped"
    except subprocess.CalledProcessError as exc:
        print(
            "Warning: playwright-cli install failed; CLI and skill are installed, "
            "but browser dependencies may be missing. Re-run manually or set "
            f"{SKIP_PLAYWRIGHT_BROWSERS_ENV_VAR}=1 to skip this step. ({exc})",
            file=sys.stderr,
        )
        report.tools["playwright browsers"] = "failed/skipped"

    report.tree_skills["playwright-cli"] = True
    print("playwright-cli installation completed.")
    return True


def install_ima_skills(report: InstallReport, targets: set[str]) -> bool:
    if tree_skill_installed_in_targets(targets, "ima-skill"):
        print("IMA skill already installed in selected directories.")
        report.tree_skills["ima-skill"] = True
        return True

    print("")
    print(f"Installing IMA skills from {IMA_AGENT_INTERFACE_URL} ...")
    try:
        download_url = fetch_ima_skills_download_url(IMA_AGENT_INTERFACE_URL)
    except (URLError, RuntimeError) as exc:
        print(f"IMA skills download URL lookup failed: {exc}", file=sys.stderr)
        report.tree_skills["ima-skill"] = False
        return False

    print(f"IMA skills download URL: {download_url}")

    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        zip_path = tmp_dir / "ima-skills.zip"
        try:
            http_download(download_url, zip_path)
        except URLError as exc:
            print(f"Failed to download IMA skills zip: {exc}", file=sys.stderr)
            report.tree_skills["ima-skill"] = False
            return False

        try:
            with zipfile.ZipFile(zip_path) as archive:
                archive.extractall(tmp_dir)
        except zipfile.BadZipFile as exc:
            print(f"Failed to extract IMA skills zip: {exc}", file=sys.stderr)
            report.tree_skills["ima-skill"] = False
            return False

        skill_src = tmp_dir / "ima-skill"
        if not skill_src.is_dir():
            print(
                "Unexpected IMA skills zip layout: ima-skill/ not found",
                file=sys.stderr,
            )
            report.tree_skills["ima-skill"] = False
            return False

        ensure_ima_subskill_frontmatters(skill_src)
        install_tree_skill(report, targets, "ima-skill", skill_src)

    report.tree_skills["ima-skill"] = True
    print("IMA skills installation completed.")
    return True


def can_prompt_from_terminal() -> bool:
    if sys.stdin.isatty():
        return True

    if os.name == "nt":
        return False

    try:
        with Path("/dev/tty").open("r", encoding="utf-8"):
            return True
    except OSError:
        return False


def prompt_optional(label: str, *, secret: bool = False) -> str:
    if secret:
        return getpass.getpass(label).strip()
    return prompt_line_with_tty(label).strip()


def prompt_line_with_tty(label: str, default: str = "") -> str:
    if sys.stdin.isatty():
        value = input(label).strip()
        return value or default

    if os.name != "nt":
        try:
            print(label, end="", flush=True)
            with Path("/dev/tty").open("r", encoding="utf-8") as tty_input:
                value = tty_input.readline().strip()
            return value or default
        except OSError as exc:
            print(f"无法打开 /dev/tty 读取输入: {exc}", file=sys.stderr)

    return default


def prompt_yes_no_with_tty(question: str, *, default: bool = False) -> bool:
    suffix = "[Y/n]" if default else "[y/N]"
    default_text = "y" if default else "n"
    answer = prompt_line_with_tty(f"{question} {suffix}: ", default_text).lower()
    return answer in {"y", "yes", "是"}


def prompt_gitlab_hostname() -> str:
    default_host = os.environ.get(GITLAB_HOST_ENV_VAR, "").strip() or "gitlab.com"
    return prompt_line_with_tty(f"GitLab hostname [{default_host}]: ", default_host)


def normalize_gitlab_api_protocol(raw: str) -> str:
    protocol = raw.strip().lower()
    if protocol in {"http", "https"}:
        return protocol
    raise ValueError("GitLab API protocol must be http or https")


def default_gitlab_api_protocol() -> str:
    configured = os.environ.get(GITLAB_API_PROTOCOL_ENV_VAR, "").strip()
    if not configured:
        return "https"
    try:
        return normalize_gitlab_api_protocol(configured)
    except ValueError:
        print(
            f"警告: {GITLAB_API_PROTOCOL_ENV_VAR}={configured!r} 无效，使用默认 https。",
            file=sys.stderr,
        )
        return "https"


def prompt_gitlab_api_protocol() -> str:
    default_protocol = default_gitlab_api_protocol()
    while True:
        answer = prompt_line_with_tty(
            f"GitLab API protocol [{default_protocol}] (http/https): ",
            default_protocol,
        )
        try:
            return normalize_gitlab_api_protocol(answer)
        except ValueError as exc:
            print(f"无效 GitLab API protocol: {exc}")


def github_cli_is_authenticated(gh_path: str) -> bool:
    return command_succeeds([gh_path, "auth", "status"])


def login_github_cli_with_token(token_path: Path) -> bool:
    gh_path = which("gh")
    if gh_path is None:
        print(
            "错误: 未找到 GitHub CLI `gh`，无法检测或执行 GitHub 登录。",
            file=sys.stderr,
        )
        return False

    if github_cli_is_authenticated(gh_path):
        print("GitHub CLI 已登录，跳过 `gh auth login --with-token`。")
        return True

    try:
        with token_path.open("r", encoding="utf-8") as token_handle:
            result = subprocess.run(
                [gh_path, "auth", "login", "--with-token"],
                stdin=token_handle,
                capture_output=True,
                text=True,
                check=False,
                timeout=60,
            )
    except (OSError, subprocess.TimeoutExpired) as exc:
        print(f"错误: 无法执行 `gh auth login --with-token`: {exc}", file=sys.stderr)
        return False

    if result.returncode != 0:
        stderr = result.stderr.strip() or "unknown error"
        print(f"错误: `gh auth login --with-token` 执行失败: {stderr}", file=sys.stderr)
        return False

    print("GitHub CLI 已通过 ~/.config/m_skill_auths/gh_token 登录。")
    return True


def gitlab_cli_is_authenticated(glab_path: str, hostname: str) -> bool:
    return command_succeeds([glab_path, "auth", "status", "--hostname", hostname])


def login_gitlab_cli_with_token(
    token_path: Path, hostname: str, api_protocol: str
) -> bool:
    glab_path = which("glab")
    if glab_path is None:
        print(
            "错误: 未找到 GitLab CLI `glab`，无法检测或执行 GitLab 登录。",
            file=sys.stderr,
        )
        return False

    if gitlab_cli_is_authenticated(glab_path, hostname):
        print(f"GitLab CLI 已登录 {hostname}，跳过 `glab auth login --stdin`。")
        return True

    try:
        with token_path.open("r", encoding="utf-8") as token_handle:
            result = subprocess.run(
                [
                    glab_path,
                    "auth",
                    "login",
                    "--hostname",
                    hostname,
                    "--api-protocol",
                    api_protocol,
                    "--stdin",
                ],
                stdin=token_handle,
                capture_output=True,
                text=True,
                check=False,
                timeout=60,
            )
    except (OSError, subprocess.TimeoutExpired) as exc:
        print(f"错误: 无法执行 `glab auth login --stdin`: {exc}", file=sys.stderr)
        return False

    if result.returncode != 0:
        stderr = result.stderr.strip() or "unknown error"
        print(f"错误: `glab auth login --stdin` 执行失败: {stderr}", file=sys.stderr)
        return False

    print(
        f"GitLab CLI 已通过 ~/.config/m_skill_auths/glab_token 登录 {api_protocol}://{hostname}。"
    )
    return True


def sync_bitwarden_vault(bw_path: str, bw_session: str) -> bool:
    print("正在执行 `bw sync` 同步 Bitwarden vault ...")
    try:
        result = subprocess.run(
            [bw_path, "sync", "--session", bw_session],
            capture_output=True,
            text=True,
            check=False,
            timeout=120,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        print(f"错误: 无法执行 `bw sync`: {exc}", file=sys.stderr)
        return False

    if result.returncode != 0:
        stderr = result.stderr.strip() or "unknown error"
        print(f"错误: `bw sync` 执行失败: {stderr}", file=sys.stderr)
        return False

    print("Bitwarden vault 同步完成。")
    return True


def export_github_token_from_bitwarden(report: InstallReport) -> bool:
    gh_path = which("gh")
    if gh_path is None:
        print(
            "错误: 未找到 GitHub CLI `gh`，无法检测或执行 GitHub 登录。",
            file=sys.stderr,
        )
        return False

    if github_cli_is_authenticated(gh_path):
        print("GitHub CLI 已登录，跳过 Bitwarden GitHub token 导出。")
        report.gh_token_configured = True
        return True

    bw_path = which("bw")
    if bw_path is None:
        print(
            "错误: 未找到 Bitwarden CLI `bw`，无法导出 GitHub token。", file=sys.stderr
        )
        return False
    bw_session = os.environ.get("BW_SESSION", "").strip()
    if not bw_session:
        if not ensure_bw_session(bw_path):
            print(
                "错误: 无法获取 BW_SESSION，无法从 Bitwarden 读取 github_gh_token。",
                file=sys.stderr,
            )
            return False
        bw_session = os.environ.get("BW_SESSION", "").strip()

    if not bw_session:
        print(
            "错误: BW_SESSION 仍为空，无法从 Bitwarden 读取 github_gh_token。",
            file=sys.stderr,
        )
        return False

    if not sync_bitwarden_vault(bw_path, bw_session):
        return False

    try:
        result = subprocess.run(
            [bw_path, "get", "password", "github_gh_token", "--session", bw_session],
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        print(f"错误: 无法从 Bitwarden 读取 GitHub token: {exc}", file=sys.stderr)
        return False

    if result.returncode != 0:
        stderr = result.stderr.strip() or "unknown error"
        print(
            f"警告: `bw get password github_gh_token` 执行失败: {stderr}",
            file=sys.stderr,
        )
        print(
            "尝试重新执行 `bw unlock --raw` 后再次读取 GitHub token。", file=sys.stderr
        )
        if not ensure_bw_session(bw_path, force_unlock=True):
            return False
        bw_session = os.environ.get("BW_SESSION", "").strip()
        if not sync_bitwarden_vault(bw_path, bw_session):
            return False
        result = subprocess.run(
            [bw_path, "get", "password", "github_gh_token", "--session", bw_session],
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
        )
        if result.returncode != 0:
            stderr = result.stderr.strip() or "unknown error"
            print(
                f"错误: `bw get password github_gh_token` 重试失败: {stderr}",
                file=sys.stderr,
            )
            return False

    token = result.stdout.strip()
    if not token:
        print(
            "错误: Bitwarden 条目 github_gh_token 的 password 为空。", file=sys.stderr
        )
        return False

    token_path = gh_token_file()
    secure_dir(token_path.parent)
    secure_write(token_path, token + "\n")
    print(f"GitHub token 已写入: {token_path}")

    if not login_github_cli_with_token(token_path):
        return False

    report.gh_token_configured = True
    return True


def export_gitlab_token_from_bitwarden(
    report: InstallReport, hostname: str, api_protocol: str
) -> bool:
    glab_path = which("glab")
    if glab_path is None:
        print(
            "错误: 未找到 GitLab CLI `glab`，无法检测或执行 GitLab 登录。",
            file=sys.stderr,
        )
        return False

    if gitlab_cli_is_authenticated(glab_path, hostname):
        print(f"GitLab CLI 已登录 {hostname}，跳过 Bitwarden GitLab token 导出。")
        report.glab_token_configured = True
        return True

    bw_path = which("bw")
    if bw_path is None:
        print(
            "错误: 未找到 Bitwarden CLI `bw`，无法导出 GitLab token。", file=sys.stderr
        )
        return False
    bw_session = os.environ.get("BW_SESSION", "").strip()
    if not bw_session:
        if not ensure_bw_session(bw_path):
            print(
                "错误: 无法获取 BW_SESSION，无法从 Bitwarden 读取 gitlab_glab_token。",
                file=sys.stderr,
            )
            return False
        bw_session = os.environ.get("BW_SESSION", "").strip()

    if not bw_session:
        print(
            "错误: BW_SESSION 仍为空，无法从 Bitwarden 读取 gitlab_glab_token。",
            file=sys.stderr,
        )
        return False

    if not sync_bitwarden_vault(bw_path, bw_session):
        return False

    try:
        result = subprocess.run(
            [bw_path, "get", "password", "gitlab_glab_token", "--session", bw_session],
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        print(f"错误: 无法从 Bitwarden 读取 GitLab token: {exc}", file=sys.stderr)
        return False

    if result.returncode != 0:
        stderr = result.stderr.strip() or "unknown error"
        print(
            f"警告: `bw get password gitlab_glab_token` 执行失败: {stderr}",
            file=sys.stderr,
        )
        print(
            "尝试重新执行 `bw unlock --raw` 后再次读取 GitLab token。", file=sys.stderr
        )
        if not ensure_bw_session(bw_path, force_unlock=True):
            return False
        bw_session = os.environ.get("BW_SESSION", "").strip()
        if not sync_bitwarden_vault(bw_path, bw_session):
            return False
        result = subprocess.run(
            [bw_path, "get", "password", "gitlab_glab_token", "--session", bw_session],
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
        )
        if result.returncode != 0:
            stderr = result.stderr.strip() or "unknown error"
            print(
                f"错误: `bw get password gitlab_glab_token` 重试失败: {stderr}",
                file=sys.stderr,
            )
            return False

    token = result.stdout.strip()
    if not token:
        print(
            "错误: Bitwarden 条目 gitlab_glab_token 的 password 为空。", file=sys.stderr
        )
        return False

    token_path = glab_token_file()
    secure_dir(token_path.parent)
    secure_write(token_path, token + "\n")
    print(f"GitLab token 已写入: {token_path}")

    if not login_gitlab_cli_with_token(token_path, hostname, api_protocol):
        return False

    report.glab_token_configured = True
    return True


def prompt_ima_api_credentials(report: InstallReport) -> bool:
    config_dir = ima_config_dir()
    client_id_file = config_dir / "client_id"
    api_key_file = config_dir / "api_key"
    secure_dir(config_dir)

    def credential_file_is_non_empty(path: Path) -> bool:
        return path.is_file() and path.stat().st_size > 0

    if credential_file_is_non_empty(client_id_file) and credential_file_is_non_empty(
        api_key_file
    ):
        print(
            f"IMA 凭证已存在 ({config_dir})，如需更新请删除 client_id / api_key 后重新运行。"
        )
        report.ima_credentials_configured = True
        return True

    if not can_prompt_from_terminal():
        print(
            "未检测到交互式终端或可用 /dev/tty，跳过可选 IMA API 凭证配置。"
        )
        return True

    print("")
    print("=== IMA API 凭证配置（可选，可直接回车跳过）===")
    print(f"请在浏览器打开 {IMA_AGENT_INTERFACE_URL} 获取 Client ID 与 API Key。")
    print(f"凭证将保存到 {config_dir}/（client_id、api_key）。")
    print("留空会跳过 IMA 凭证配置，后续可重新运行本脚本或手动写入。")
    print("")

    if not credential_file_is_non_empty(client_id_file):
        client_id = prompt_optional("请输入 IMA Client ID（可留空跳过）: ")
        if client_id:
            secure_write(client_id_file, client_id)

    if not credential_file_is_non_empty(api_key_file):
        api_key = prompt_optional("请输入 IMA API Key（可留空跳过）: ", secret=True)
        if api_key:
            secure_write(api_key_file, api_key)

    if credential_file_is_non_empty(client_id_file) and credential_file_is_non_empty(
        api_key_file
    ):
        print(f"IMA 凭证已保存到 {config_dir}。")
        report.ima_credentials_configured = True
    else:
        print("IMA 凭证未完整配置，已跳过。")
    return True


def print_install_summary(report: InstallReport) -> None:
    print("\n" + "=" * 72)
    print("安装摘要".center(72))
    print("=" * 72)

    tool_labels = {
        "bw": "Bitwarden CLI (bw)",
        "gh": "GitHub CLI (gh)",
        "gh skill": "gh skill",
        "glab": "GitLab CLI (glab)",
        "bun": "Bun",
        "zentao": "ZenTao CLI (zentao)",
        "node": "Node.js",
        "npm": "npm",
        "playwright-cli": "Playwright CLI",
        "playwright browsers": "Playwright browser deps",
    }
    tool_rows = []
    for key in (
        "bw",
        "gh",
        "gh skill",
        "glab",
        "bun",
        "zentao",
        "node",
        "npm",
        "playwright-cli",
        "playwright browsers",
    ):
        value = (
            report.tools.get(key)
            or (which(key) if " " not in key else None)
            or "未安装"
        )
        tool_rows.append([tool_labels.get(key, key), value])
    render_table("工具", ["工具", "路径 / 状态"], tool_rows)

    skill_rows: list[list[str]] = []
    for skill in report.repo_skills:
        skill_rows.append([skill, "M_Skills", "已安装"])
    for skill, ok in report.tree_skills.items():
        skill_rows.append([skill, "外部", "已安装" if ok else "失败"])
    render_table("Skills", ["Skill", "来源", "状态"], skill_rows)

    selected = set(report.selected_targets)
    target_rows = [
        [option.label, format_path(option.root())]
        for option in target_options()
        if option.key in selected
    ]
    render_table("已选目标目录", ["目标", "路径"], target_rows)

    install_rows = [
        [label, skill, path] for label, skill, path in report.installed_rows
    ]
    render_table("Skill 安装明细", ["目标", "Skill", "路径"], install_rows)

    ima_dir = ima_config_dir()
    ima_status = "已配置" if report.ima_credentials_configured else "未配置"
    render_table(
        "IMA 配置",
        ["项目", "路径 / 状态"],
        [
            ["凭证目录", format_path(ima_dir)],
            ["Client ID", format_path(ima_dir / "client_id")],
            ["API Key", format_path(ima_dir / "api_key")],
            ["配置状态", ima_status],
        ],
    )

    auth_dir = m_skill_auths_dir()
    gh_token_status = "已配置" if report.gh_token_configured else "未配置"
    glab_token_status = "已配置" if report.glab_token_configured else "未配置"
    render_table(
        "M_Skills Auths",
        ["项目", "路径 / 状态"],
        [
            ["凭证目录", format_path(auth_dir)],
            ["Bitwarden session", format_path(bw_session_file())],
            ["GitHub token", format_path(gh_token_file())],
            ["GitLab token", format_path(glab_token_file())],
            ["GitHub 配置状态", gh_token_status],
            ["GitLab 配置状态", glab_token_status],
        ],
    )

    print("=" * 72)


def main() -> int:
    report = InstallReport()
    if not require_bitwarden_cli(report):
        return 1

    system = check_platform()
    targets = prompt_install_targets()
    report.selected_targets = sorted(targets)
    print(
        f"\n将安装到: {', '.join(option.label for option in selected_target_options(targets))}"
    )

    install_repo_user_skills(report, targets)

    if install_github_cli(report, system):
        if not install_repo_user_skills_with_gh(report, targets):
            print(
                "gh skill installation failed; direct file-copy installation has already completed.",
                file=sys.stderr,
            )
    else:
        print(
            "GitHub CLI installation failed or was skipped; direct file-copy installation has already completed.",
            file=sys.stderr,
        )

    if not install_glab_cli(report, system):
        print(
            f"GitLab CLI (glab) installation failed; install manually from {GITLAB_CLI_RELEASES_URL}",
            file=sys.stderr,
        )

    if not install_zentao_cli(report):
        print(
            "ZenTao CLI installation failed; install manually: bun install -g zentao-cli",
            file=sys.stderr,
        )

    if not install_playwright_cli_and_skills(report, targets):
        print(
            "playwright-cli installation failed; install manually: "
            "npm install -g @playwright/cli@latest && playwright-cli install",
            file=sys.stderr,
        )

    if not install_ima_skills(report, targets):
        print(
            "IMA skills installation failed; configure credentials manually after fixing the error.",
            file=sys.stderr,
        )

    if not prompt_ima_api_credentials(report):
        print_install_summary(report)
        return 1

    if not export_github_token_from_bitwarden(report):
        print_install_summary(report)
        return 1

    if prompt_yes_no_with_tty(
        "是否使用 Bitwarden 中的 gitlab_glab_token 登录 GitLab CLI (glab)?"
    ):
        hostname = prompt_gitlab_hostname()
        api_protocol = prompt_gitlab_api_protocol()
        if not export_gitlab_token_from_bitwarden(report, hostname, api_protocol):
            print_install_summary(report)
            return 1
    else:
        print("已跳过 GitLab CLI (glab) 登录。")

    print_install_summary(report)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\nInstallation cancelled.", file=sys.stderr)
        raise SystemExit(130) from None
