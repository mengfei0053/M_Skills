#!/usr/bin/env bash
set -euo pipefail

# Install HarmonyOS skills into the current project by default.
# Usage:
#   scripts/install-project-harmonyos-skills.sh
#   scripts/install-project-harmonyos-skills.sh /path/to/project
#
# Targets inside the project:
# - .agents/skills/<skill>/SKILL.md
# - .claude/skills/<skill>/SKILL.md
# - .opencode/skills/<skill>/SKILL.md
# - .cursor/rules/m-skills-<skill>.mdc

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROJECT_DIR="${1:-$PWD}"
HARMONYOS_SKILLS_DIR="$REPO_DIR/skills/harmonyos"

if [ ! -d "$PROJECT_DIR" ]; then
  echo "Project directory not found: $PROJECT_DIR" >&2
  exit 1
fi

if [ ! -d "$HARMONYOS_SKILLS_DIR" ]; then
  echo "HarmonyOS skills directory not found: $HARMONYOS_SKILLS_DIR" >&2
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
  local dest="$PROJECT_DIR/.cursor/rules/m-skills-${skill_name}.mdc"
  mkdir -p "$(dirname "$dest")"
  {
    echo "---"
    echo "description: M_Skills project HarmonyOS skill - ${skill_name}"
    echo "alwaysApply: false"
    echo "---"
    echo
    cat "$src"
  } > "$dest"
  echo "installed: $dest"
}

shopt -s nullglob
for skill_dir in "$HARMONYOS_SKILLS_DIR"/*; do
  [ -d "$skill_dir" ] || continue
  skill_name="$(basename "$skill_dir")"
  src="$skill_dir/SKILL.md"
  [ -f "$src" ] || continue

  install_skill_file "$src" "$PROJECT_DIR/.agents/skills/$skill_name/SKILL.md"
  install_skill_file "$src" "$PROJECT_DIR/.claude/skills/$skill_name/SKILL.md"
  install_skill_file "$src" "$PROJECT_DIR/.opencode/skills/$skill_name/SKILL.md"
  install_cursor_rule "$skill_name" "$src"
done

echo "Project-level HarmonyOS skills installation completed: $PROJECT_DIR"
