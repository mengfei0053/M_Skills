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
import tempfile
import zipfile
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen

SUPPORTED_SYSTEMS = frozenset({"Windows", "Linux", "Darwin"})
GITHUB_CLI_INSTALL_LINUX_URL = (
    "https://github.com/cli/cli/blob/trunk/docs/install_linux.md"
)
GITHUB_CLI_SKILL_MANUAL_URL = "https://cli.github.com/manual/gh_skill"
M_SKILLS_RAW_BASE_URL = "https://raw.githubusercontent.com/mengfei0053/M_Skills/refs/heads/main"
M_SKILLS_USER_CONTENTS_API_URL = "https://api.github.com/repos/mengfei0053/M_Skills/contents/skills/user?ref=main"
PLAYWRIGHT_CLI_REPO_URL = "https://github.com/microsoft/playwright-cli"
IMA_AGENT_INTERFACE_URL = "https://ima.qq.com/agent-interface"
JS_BUNDLE_RE = re.compile(
    r"https://static\.ima\.qq\.com/ima/assets/agent-interface/assets/index-[A-Za-z0-9_-]+\.js"
)
IMA_SKILLS_ZIP_RE = re.compile(
    r"https://app-dl\.ima\.qq\.com/skills/ima-skills-[0-9.]+\.zip"
)
USER_AGENT = "M_Skills-install-user-skills/1.0"
TARGET_ENV_VAR = "M_SKILLS_INSTALL_TARGETS"
REPO_DIR_ENV_VAR = "M_SKILLS_REPO_DIR"


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


def has_user_skills_dir(path: Path) -> bool:
    return (path / "skills" / "user").is_dir()


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
        if has_user_skills_dir(configured):
            return configured.resolve()
        if strict_env:
            raise FileNotFoundError(
                f"{REPO_DIR_ENV_VAR} does not contain skills/user: {configured}"
            )
        return None

    for candidate in candidate_repo_dirs():
        if has_user_skills_dir(candidate):
            return candidate
    return None


def repo_dir() -> Path:
    found = find_repo_dir()
    if found is not None:
        return found

    checked = ", ".join(format_path(path) for path in candidate_repo_dirs())
    raise FileNotFoundError(
        "User skills directory not found. Run this script from the M_Skills repository, "
        f"set {REPO_DIR_ENV_VAR}=/path/to/M_Skills, or run the official curl install path. "
        f"Checked: {checked}"
    )


def user_skills_dir() -> Path:
    return repo_dir() / "skills" / "user"


def ima_config_dir() -> Path:
    return home() / ".config" / "ima"


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
            index = int(part) - 1
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


def http_get_text(url: str) -> str:
    request = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(request, timeout=60) as response:
        return response.read().decode("utf-8", errors="replace")


def http_download(url: str, dest: Path) -> None:
    request = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(request, timeout=120) as response, dest.open("wb") as handle:
        shutil.copyfileobj(response, handle)


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
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=str(cwd) if cwd else None,
        check=check,
        text=True,
    )


def run_shell_command(
    command: str, *, check: bool = True
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, shell=True, check=check, text=True)


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


def sudo_prefix() -> str | None:
    if os.name != "nt" and hasattr(os, "geteuid") and os.geteuid() == 0:
        return ""
    if which("sudo") is not None:
        return "sudo "
    return None


def record_install(report: InstallReport, label: str, skill: str, dest: Path) -> None:
    report.installed_rows.append((label, skill, format_path(dest)))


def install_skill_file(src: Path, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)
    print(f"installed: {dest}")


def install_skill_content(content: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(content, encoding="utf-8")
    print(f"installed: {dest}")


def install_skill_tree(src: Path, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(src, dest)
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
    payload = json.loads(http_get_text(M_SKILLS_USER_CONTENTS_API_URL))
    if not isinstance(payload, list):
        raise RuntimeError("Unexpected GitHub contents API response for skills/user")
    skill_names = sorted(
        item["name"]
        for item in payload
        if isinstance(item, dict)
        and item.get("type") == "dir"
        and isinstance(item.get("name"), str)
    )
    if not skill_names:
        raise RuntimeError("No remote user skills found in M_Skills")
    return skill_names


def fetch_remote_user_skill(skill_name: str) -> str:
    return http_get_text(
        f"{M_SKILLS_RAW_BASE_URL}/skills/user/{skill_name}/SKILL.md"
    )


def install_repo_user_skills_from_remote(report: InstallReport, targets: set[str]) -> None:
    print(
        "Local skills/user directory not found; installing user skills from GitHub raw content."
    )
    options = selected_target_options(targets)
    for skill_name in fetch_remote_user_skill_names():
        try:
            content = fetch_remote_user_skill(skill_name)
        except URLError as exc:
            raise RuntimeError(f"Failed to fetch remote skill {skill_name}: {exc}") from exc
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
        install_repo_user_skills_from_local(report, targets, root / "skills" / "user")

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


def install_github_cli(report: InstallReport, system: str) -> bool:
    gh_path = which("gh")
    if gh_path is not None:
        report.tools["gh"] = gh_path
        print(f"GitHub CLI already installed: {gh_path}")
        return True

    if system != "Linux":
        print(
            "GitHub CLI (gh) is not installed; automatic installation is only enabled on Linux. "
            f"See {GITHUB_CLI_INSTALL_LINUX_URL} for Linux and cli.github.com for other platforms.",
            file=sys.stderr,
        )
        report.tools["gh"] = "not found"
        return False

    sudo = sudo_prefix()
    if sudo is None:
        print(
            "GitHub CLI installation requires root privileges or sudo.", file=sys.stderr
        )
        report.tools["gh"] = "not found"
        return False

    print("")
    print(
        f"Installing GitHub CLI (gh) using official Linux package guidance ({GITHUB_CLI_INSTALL_LINUX_URL}) ..."
    )
    try:
        if which("apt") is not None and which("dpkg") is not None:
            run_shell_command(
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
            run_command([*(sudo.split() if sudo else []), "dnf", "install", "gh", "-y"])
        elif which("yum") is not None:
            run_command(
                [*(sudo.split() if sudo else []), "yum", "install", "yum-utils", "-y"]
            )
            run_command(
                [
                    *(sudo.split() if sudo else []),
                    "yum-config-manager",
                    "--add-repo",
                    "https://cli.github.com/packages/rpm/gh-cli.repo",
                ]
            )
            run_command([*(sudo.split() if sudo else []), "yum", "install", "gh", "-y"])
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
    except subprocess.CalledProcessError:
        print("Failed to install GitHub CLI (gh)", file=sys.stderr)
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
        print("Skipping gh skill install because no local M_Skills repository was found.")
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
    for skill_name in report.repo_skills:
        skill_path = f"skills/user/{skill_name}/SKILL.md"
        for option in selected_target_options(targets):
            try:
                run_command(
                    [
                        gh_path,
                        "skill",
                        "install",
                        str(local_repo),
                        skill_path,
                        "--from-local",
                        "--dir",
                        str(option.root()),
                        "--force",
                    ]
                )
                print(f"gh skill installed: {option.label} / {skill_name}")
            except subprocess.CalledProcessError:
                print(
                    f"Failed to install {skill_name} with gh skill for {option.label}",
                    file=sys.stderr,
                )
                ok = False
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
    if which("npm") is None:
        print(
            f"npm is required to install playwright-cli ({PLAYWRIGHT_CLI_REPO_URL})",
            file=sys.stderr,
        )
        return False
    if which("node") is None:
        print("Node.js 18+ is required to install playwright-cli", file=sys.stderr)
        return False

    print("")
    print(f"Installing @playwright/cli globally ({PLAYWRIGHT_CLI_REPO_URL}) ...")
    try:
        run_command(["npm", "install", "-g", "@playwright/cli@latest"])
    except subprocess.CalledProcessError:
        print("Failed to install @playwright/cli", file=sys.stderr)
        return False

    report.tools["node"] = which("node") or "not found"
    report.tools["npm"] = which("npm") or "not found"

    playwright_cli = which("playwright-cli")
    report.tools["playwright-cli"] = playwright_cli or "not found"
    if playwright_cli is None:
        print(
            "playwright-cli not found in PATH after npm global install", file=sys.stderr
        )
        print(
            "Ensure the npm global bin directory is on PATH, then re-run.",
            file=sys.stderr,
        )
        report.tree_skills["playwright-cli"] = False
        return False

    npm_root = subprocess.check_output(["npm", "root", "-g"], text=True).strip()
    skill_src = Path(npm_root) / "@playwright" / "cli" / "skills" / "playwright-cli"
    if not (skill_src / "SKILL.md").is_file():
        print(f"playwright-cli skill bundle not found at {skill_src}", file=sys.stderr)
        report.tree_skills["playwright-cli"] = False
        return False

    print("Installing playwright-cli skill to selected directories ...")
    install_tree_skill(report, targets, "playwright-cli", skill_src)

    print("Bootstrapping Playwright browser dependencies (playwright-cli install) ...")
    try:
        run_command([playwright_cli, "install"], cwd=home())
    except subprocess.CalledProcessError:
        print(
            "Warning: playwright-cli install failed; CLI is installed but browsers may be missing.",
            file=sys.stderr,
        )
        report.tree_skills["playwright-cli"] = False
        return False

    report.tree_skills["playwright-cli"] = True
    print("playwright-cli installation completed.")
    return True


def install_ima_skills(report: InstallReport, targets: set[str]) -> bool:
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
        except zipfile.BadZipFile:
            print("Failed to extract IMA skills zip", file=sys.stderr)
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

        install_tree_skill(report, targets, "ima-skill", skill_src)

    report.tree_skills["ima-skill"] = True
    print("IMA skills installation completed.")
    return True


def require_interactive_terminal() -> bool:
    if sys.stdin.isatty():
        return True
    print("错误: 需要交互式终端才能输入 IMA API Key。", file=sys.stderr)
    print("请在本地终端执行: python scripts/install-user-skills.py", file=sys.stderr)
    return False


def prompt_non_empty(label: str, *, secret: bool = False) -> str:
    while True:
        if secret:
            value = getpass.getpass(label)
        else:
            value = input(label)
        if value.strip():
            return value.strip()
        print("输入不能为空，请重新输入。")


def prompt_ima_api_credentials(report: InstallReport) -> bool:
    if not require_interactive_terminal():
        return False

    config_dir = ima_config_dir()
    client_id_file = config_dir / "client_id"
    api_key_file = config_dir / "api_key"
    secure_dir(config_dir)

    if (
        client_id_file.is_file()
        and client_id_file.stat().st_size > 0
        and api_key_file.is_file()
        and api_key_file.stat().st_size > 0
    ):
        print(
            f"IMA 凭证已存在 ({config_dir})，如需更新请删除 client_id / api_key 后重新运行。"
        )
        report.ima_credentials_configured = True
        return True

    print("")
    print("=== IMA API 凭证配置（交互式输入）===")
    print(f"请在浏览器打开 {IMA_AGENT_INTERFACE_URL} 获取 Client ID 与 API Key。")
    print(f"凭证将保存到 {config_dir}/（client_id、api_key）。")
    print("")

    if not (client_id_file.is_file() and client_id_file.stat().st_size > 0):
        secure_write(client_id_file, prompt_non_empty("请输入 IMA Client ID: "))

    if not (api_key_file.is_file() and api_key_file.stat().st_size > 0):
        secure_write(
            api_key_file, prompt_non_empty("请输入 IMA API Key: ", secret=True)
        )

    print(f"IMA 凭证已保存到 {config_dir}。")
    report.ima_credentials_configured = True
    return True


def print_install_summary(report: InstallReport) -> None:
    print("\n" + "=" * 72)
    print("安装摘要".center(72))
    print("=" * 72)

    tool_labels = {
        "gh": "GitHub CLI (gh)",
        "gh skill": "gh skill",
        "node": "Node.js",
        "npm": "npm",
        "playwright-cli": "playwright-cli",
    }
    tool_rows = []
    for key in ("gh", "gh skill", "node", "npm", "playwright-cli"):
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

    print("=" * 72)


def main() -> int:
    report = InstallReport()
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

    if not install_playwright_cli_and_skills(report, targets):
        print(
            "playwright-cli installation failed; install manually: "
            "npm install -g @playwright/cli@latest && playwright-cli install --skills",
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

    print_install_summary(report)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\nInstallation cancelled.", file=sys.stderr)
        raise SystemExit(130) from None
