#!/usr/bin/env bash
set -euo pipefail

# Install all skills under skills/user into user-level tool configuration directories.
# Targets:
# - Agent common: ~/.agents/skills/<skill>/SKILL.md
# - Claude Code: ~/.claude/skills/<skill>/SKILL.md
# - OpenCode: ~/.config/opencode/skills/<skill>/SKILL.md
# - Cursor: ~/.cursor/rules/m-skills-<skill>.mdc

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
USER_SKILLS_DIR="$REPO_DIR/skills/user"

if [ ! -d "$USER_SKILLS_DIR" ]; then
  echo "User skills directory not found: $USER_SKILLS_DIR" >&2
  exit 1
fi

install_skill_file() {
  local src="$1"
  local dest="$2"
  mkdir -p "$(dirname "$dest")"
  cp "$src" "$dest"
  echo "installed: $dest"
}

install_cursor_rule() {
  local skill_name="$1"
  local src="$2"
  local dest="$HOME/.cursor/rules/m-skills-${skill_name}.mdc"
  mkdir -p "$(dirname "$dest")"
  {
    echo "---"
    echo "description: M_Skills user skill - ${skill_name}"
    echo "alwaysApply: false"
    echo "---"
    echo
    cat "$src"
  } > "$dest"
  echo "installed: $dest"
}

shopt -s nullglob
for skill_dir in "$USER_SKILLS_DIR"/*; do
  [ -d "$skill_dir" ] || continue
  skill_name="$(basename "$skill_dir")"
  src="$skill_dir/SKILL.md"
  [ -f "$src" ] || continue

  install_skill_file "$src" "$HOME/.agents/skills/$skill_name/SKILL.md"
  install_skill_file "$src" "$HOME/.claude/skills/$skill_name/SKILL.md"
  install_skill_file "$src" "$HOME/.config/opencode/skills/$skill_name/SKILL.md"
  install_cursor_rule "$skill_name" "$src"
done

echo "User-level skills installation completed."

# --- IMA skills (from https://ima.qq.com/agent-interface) ---
IMA_AGENT_INTERFACE_URL="https://ima.qq.com/agent-interface"
IMA_CONFIG_DIR="${HOME}/.config/ima"
IMA_CLIENT_ID_FILE="${IMA_CONFIG_DIR}/client_id"
IMA_API_KEY_FILE="${IMA_CONFIG_DIR}/api_key"

fetch_ima_skills_download_url() {
  local page_url="$1"
  local html js_url download_url

  html="$(curl -fsSL "$page_url")" || return 1
  js_url="$(printf '%s' "$html" | grep -oE 'https://static\.ima\.qq\.com/ima/assets/agent-interface/assets/index-[A-Za-z0-9_-]+\.js' | grep -v legacy | head -1)"
  if [ -z "$js_url" ]; then
    echo "Failed to locate agent-interface JS bundle on ${page_url}" >&2
    return 1
  fi

  download_url="$(curl -fsSL "$js_url" | grep -oE 'https://app-dl\.ima\.qq\.com/skills/ima-skills-[0-9.]+\.zip' | head -1)" || return 1
  if [ -z "$download_url" ]; then
    echo "Failed to locate IMA skills zip URL in ${js_url}" >&2
    return 1
  fi

  printf '%s' "$download_url"
}

install_ima_skill_tree() {
  local src="$1"
  local dest="$2"
  mkdir -p "$(dirname "$dest")"
  rm -rf "$dest"
  cp -R "$src" "$dest"
  echo "installed: $dest"
}

install_ima_skills() {
  local download_url tmp_dir zip_path skill_src

  if ! command -v unzip >/dev/null 2>&1; then
    echo "unzip is required to install IMA skills (brew install unzip)" >&2
    return 1
  fi

  echo ""
  echo "Installing IMA skills from ${IMA_AGENT_INTERFACE_URL} ..."
  download_url="$(fetch_ima_skills_download_url "$IMA_AGENT_INTERFACE_URL")" || return 1
  echo "IMA skills download URL: ${download_url}"

  tmp_dir="$(mktemp -d)"
  zip_path="${tmp_dir}/ima-skills.zip"
  trap 'rm -rf "${tmp_dir}"' RETURN

  curl -fsSL -o "$zip_path" "$download_url" || return 1
  unzip -q "$zip_path" -d "$tmp_dir" || return 1

  skill_src="${tmp_dir}/ima-skill"
  if [ ! -d "$skill_src" ]; then
    echo "Unexpected IMA skills zip layout: ima-skill/ not found" >&2
    return 1
  fi

  install_ima_skill_tree "$skill_src" "$HOME/.agents/skills/ima-skill"
  install_ima_skill_tree "$skill_src" "$HOME/.claude/skills/ima-skill"
  install_ima_skill_tree "$skill_src" "$HOME/.config/opencode/skills/ima-skill"
  install_ima_skill_tree "$skill_src" "$HOME/.openclaw/skills/ima-skill"
  install_ima_skill_tree "$skill_src" "$HOME/.cursor/skills/ima-skill"

  trap - RETURN
  rm -rf "$tmp_dir"
  echo "IMA skills installation completed."
}

require_interactive_tty() {
  if [ ! -r /dev/tty ] || [ ! -w /dev/tty ]; then
    echo "错误: 需要交互式终端才能输入 IMA API Key。" >&2
    echo "请在本地终端执行: bash scripts/install-user-skills.sh" >&2
    return 1
  fi
}

prompt_ima_api_credentials() {
  local ima_client_id="" ima_api_key=""

  require_interactive_tty || return 1

  mkdir -p "$IMA_CONFIG_DIR"
  chmod 700 "$IMA_CONFIG_DIR"

  if [ -s "$IMA_CLIENT_ID_FILE" ] && [ -s "$IMA_API_KEY_FILE" ]; then
    echo "IMA 凭证已存在 (${IMA_CONFIG_DIR})，如需更新请删除 client_id / api_key 后重新运行。"
    return 0
  fi

  {
    echo ""
    echo "=== IMA API 凭证配置（交互式输入）==="
    echo "请在浏览器打开 ${IMA_AGENT_INTERFACE_URL} 获取 Client ID 与 API Key。"
    echo "凭证将保存到 ${IMA_CONFIG_DIR}/（client_id、api_key）。"
    echo ""
  } >/dev/tty

  if [ ! -s "$IMA_CLIENT_ID_FILE" ]; then
    while [ -z "$ima_client_id" ]; do
      read -r -p "请输入 IMA Client ID: " ima_client_id </dev/tty
      if [ -z "$ima_client_id" ]; then
        echo "Client ID 不能为空，请重新输入。" >/dev/tty
      fi
    done
    printf '%s' "$ima_client_id" >"$IMA_CLIENT_ID_FILE"
    chmod 600 "$IMA_CLIENT_ID_FILE"
  fi

  if [ ! -s "$IMA_API_KEY_FILE" ]; then
    while [ -z "$ima_api_key" ]; do
      read -r -s -p "请输入 IMA API Key: " ima_api_key </dev/tty
      echo "" >/dev/tty
      if [ -z "$ima_api_key" ]; then
        echo "API Key 不能为空，请重新输入。" >/dev/tty
      fi
    done
    printf '%s' "$ima_api_key" >"$IMA_API_KEY_FILE"
    chmod 600 "$IMA_API_KEY_FILE"
  fi

  echo "IMA 凭证已保存到 ${IMA_CONFIG_DIR}。" >/dev/tty
}

if install_ima_skills; then
  :
else
  echo "IMA skills installation failed; configure credentials manually after fixing the error." >&2
fi

prompt_ima_api_credentials || exit 1
