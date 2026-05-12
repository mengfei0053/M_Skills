#!/usr/bin/env bash
set -euo pipefail

# Install all skills under skills/user into user-level tool configuration directories.
# Targets:
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

  install_skill_file "$src" "$HOME/.claude/skills/$skill_name/SKILL.md"
  install_skill_file "$src" "$HOME/.config/opencode/skills/$skill_name/SKILL.md"
  install_cursor_rule "$skill_name" "$src"
done

echo "User-level skills installation completed."
