#!/usr/bin/env bash
# Install the Seams plugin (`seams@seams`) on this machine, end to end.
#
#   curl -fsSL https://raw.githubusercontent.com/gabriel-tutor/seams/main/scripts/install.sh | bash
#   # or, from a clone:  scripts/install.sh
#
# What it does, in order (each step is skipped when already done, so re-running is safe):
#   1. Checks for the claude CLI, Node, and python3 at 3.9 or newer.
#   2. Installs Matt Pocock's skills into the Claude config directory's skills/ via skills.sh
#      (npx skills add mattpocock/skills -g -a claude-code) when any required one is missing.
#      Needs a terminal.
#   3. Adds this repo as a plugin marketplace and installs, updates and enables seams from it. The
#      plugin before 5.0.0, matt-pocock-workflow@my-workflow-agent-skills, stops the installer while it
#      or its marketplace is still there, with the two commands that remove it: two copies' gates would
#      both run. The first `claude plugin` command that fails stops the installer, with its output.
#   4. Optionally disables the Superpowers plugin (MPW_DISABLE_SUPERPOWERS=1); by default it is left alone.
#
# It changes nothing but the plugin list and, in step 2, the skills directory: it writes nothing
# itself (the `claude plugin` commands record the marketplace and the enabled plugin in
# settings.json, as they do when run by hand), adds no permission rules, never edits Matt Pocock's
# files and never removes anything. It either succeeds or says exactly which step did not. The
# config directory is CLAUDE_CONFIG_DIR, else ~/.claude; the installer, the hook and skills.sh honour it.
set -euo pipefail

REPO="${MPW_REPO:-gabriel-tutor/seams}"
MARKETPLACE="${MPW_MARKETPLACE:-seams}"
PLUGIN="seams"
# The plugin and marketplace before 5.0.0 (seams-rename decision 5).
OLD_MARKETPLACE="my-workflow-agent-skills"
OLD_PLUGIN="matt-pocock-workflow@$OLD_MARKETPLACE"
CLAUDE_HOME="${CLAUDE_CONFIG_DIR:-$HOME/.claude}"
# The Matt Pocock skills the plugin invokes with the Skill tool: the same list as REQUIRED_SKILLS in
# plugin/hooks/session-start, which reports the missing ones at every session start.
REQUIRED_SKILLS=(grilling domain-modeling tdd diagnosing-bugs code-review codebase-design
                 setup-matt-pocock-skills setup-pre-commit setup-ts-deep-modules)
# The skills.sh command, the one the hook and the README name too: global (without -g skills.sh
# installs into the current project), for Claude Code only.
SKILLS_ADD=(skills add mattpocock/skills -g -a claude-code)
COMPATIBILITY="https://github.com/gabriel-tutor/seams/blob/main/docs/compatibility.md"

say()  { printf '\n\033[1m%s\033[0m\n' "$*"; }
ok()   { printf '  ok   %s\n' "$*"; }
skip() { printf '  skip %s\n' "$*"; }
die()  { printf '\n  error: %s\n' "$*" >&2; exit 1; }
# claude_plugin <args...>: `claude plugin <args...>`, its output kept in OUT for the callers that
# read it; the first failure stops the installer, naming the command, its exit code and everything
# it printed. Called as a plain command, never inside $(...), so the exit reaches the installer.
claude_plugin() {
  local code=0
  OUT=$(claude plugin "$@" 2>&1) || code=$?
  [[ $code -eq 0 ]] && return 0
  printf '\n  error: `claude plugin %s` failed (exit %s):\n' "$*" "$code" >&2
  printf '%s\n' "$OUT" | sed 's/^/    /' >&2
  exit 1
}
# status_of <plugin@marketplace>: enabled, disabled, or nothing when it is not installed, read from
# the last `claude_plugin list`.
status_of() {
  awk -v id="$1" '$1 == "❯" && $2 == id {found = 1; next} found && $1 == "Status:" {print ($0 ~ /enabled/ ? "enabled" : "disabled"); exit}' <<< "$OUT"
}
# marketplace_known <name>: whether the last `claude_plugin marketplace list` names it.
marketplace_known() { awk -v m="$1" '$1 == "❯" && $2 == m {found = 1} END {exit !found}' <<< "$OUT"; }
missing_skills() {
  local n missing=()
  for n in "${REQUIRED_SKILLS[@]}"; do [[ -f "$CLAUDE_HOME/skills/$n/SKILL.md" ]] || missing+=("$n"); done
  echo "${missing[*]:-}"
}

# 1. Prerequisites
say "1. Prerequisites"
command -v claude >/dev/null || die "the claude CLI is not on PATH. Install Claude Code first: https://code.claude.com"
ok "claude $(claude --version 2>/dev/null | head -1)"
command -v node >/dev/null || die "node is not on PATH; skills.sh needs it to install Matt Pocock's skills"
ok "node $(node --version)"
command -v python3 >/dev/null || die "python3 is not on PATH; the plugin's hooks need it"
PY_REPORT="$(python3 --version 2>&1)" || die "\`python3 --version\` failed: $PY_REPORT"
PY_VERSION="${PY_REPORT#Python }"
IFS=. read -r PY_MAJOR PY_MINOR _ <<< "$PY_VERSION"
[[ $PY_MAJOR =~ ^[0-9]+$ && $PY_MINOR =~ ^[0-9]+$ ]] || die "cannot read a version from \`python3 --version\`: $PY_REPORT"
[[ $PY_MAJOR -gt 3 || ( $PY_MAJOR -eq 3 && $PY_MINOR -ge 9 ) ]] \
  || die "python3 on PATH is $PY_VERSION; the plugin's hooks need Python 3.9 or newer first on PATH"
ok "python3 $PY_VERSION"

# 2. Matt Pocock's skills
say "2. Matt Pocock's skills"
MISSING="$(missing_skills)"
if [[ -z "$MISSING" ]]; then
  skip "all ${#REQUIRED_SKILLS[@]} required skills are at $CLAUDE_HOME/skills"
else
  echo "  missing from $CLAUDE_HOME/skills: $MISSING"
  { : </dev/tty; } 2>/dev/null \
    || die "no terminal to pick skills in. Run \`npx ${SKILLS_ADD[*]}\` yourself (add --skill '*' -y to take all of them), then re-run this installer"
  echo "  installing with skills.sh (interactive: pick the skills you want; keep the ones listed above)"
  npx --yes "${SKILLS_ADD[@]}" </dev/tty || die "skills.sh failed; see https://github.com/mattpocock/skills#installation"
  MISSING="$(missing_skills)"
  [[ -z "$MISSING" ]] || die "still missing from $CLAUDE_HOME/skills after skills.sh: $MISSING. Re-run \`npx ${SKILLS_ADD[*]}\` and pick them"
  ok "installed"
fi

# 3. The plugin
say "3. The $PLUGIN plugin"
claude_plugin list
OLD_STATUS="$(status_of "$OLD_PLUGIN")"
claude_plugin marketplace list
if [[ -n "$OLD_STATUS" ]] || marketplace_known "$OLD_MARKETPLACE"; then
  REMOVE=""
  [[ -n "$OLD_STATUS" ]] && REMOVE+=$'\n'"    claude plugin uninstall $OLD_PLUGIN"
  marketplace_known "$OLD_MARKETPLACE" && REMOVE+=$'\n'"    claude plugin marketplace remove $OLD_MARKETPLACE"
  die "Seams was renamed in 5.0.0, and the old copy is still here; its gate would refuse every seams: skill. Remove it, then run this installer again:$REMOVE"
fi
if marketplace_known "$MARKETPLACE"; then
  claude_plugin marketplace update "$MARKETPLACE"; skip "marketplace $MARKETPLACE already known; refreshed"
else
  claude_plugin marketplace add "$REPO"; ok "marketplace $MARKETPLACE added from $REPO"
fi
claude_plugin list
case "$(status_of "$PLUGIN@$MARKETPLACE")" in
  enabled|disabled) claude_plugin update "$PLUGIN@$MARKETPLACE"; ok "plugin already installed; updated to the latest version" ;;
  *)                claude_plugin install "$PLUGIN@$MARKETPLACE"; ok "plugin installed" ;;
esac
claude_plugin list
case "$(status_of "$PLUGIN@$MARKETPLACE")" in
  enabled)  skip "plugin already enabled" ;;
  disabled) claude_plugin enable "$PLUGIN@$MARKETPLACE"; ok "plugin enabled" ;;
  *)        die "$PLUGIN@$MARKETPLACE is not in \`claude plugin list\` after the install:"$'\n'"$OUT" ;;
esac

# 4. Superpowers
say "4. Superpowers"
SP="superpowers@claude-plugins-official"
if [[ "${MPW_DISABLE_SUPERPOWERS:-0}" != "1" ]]; then
  skip "left as is (set MPW_DISABLE_SUPERPOWERS=1 to disable it; Matt Pocock's skills lead either way, see the README)"
else
  claude_plugin list
  if [[ "$(status_of "$SP")" == enabled ]]; then claude_plugin disable "$SP"; ok "disabled (one bootstrap per session)"
  else skip "not installed or already disabled"; fi
fi

say "Done. Restart Claude Code, then in any repo:"
cat <<TXT
  - say "check what this repo has and what it's missing"  -> the foundations survey (once per repo)
  - describe a feature, a bug, or a change                -> the workflow routes it
  - to confirm it's live: ask "which skill applies before a bug fix?" (expect: diagnosing-bugs)
Tested on macOS and Ubuntu; the versions of each, of Python, Node and Claude Code, and what passed
where, are recorded in docs/compatibility.md: $COMPATIBILITY
Windows is not supported.
TXT
