#!/usr/bin/env bash
# The workspace for one scenario, the same for the routing harness and for `claude plugin eval`.
#   _scaffold.sh <case-dir>        run in the (empty) workspace directory
# Copies the OrderKit fixture from beside the cases, provides its dependencies (a symlink to
# $SEAMS_FIXTURE_NODE_MODULES when set, the harness's shared install; else `npm ci` here), makes the
# workspace a git repo at a baseline commit, applies the case's setup.sh, and, for an eval run,
# gives the run's config directory the nine Matt Pocock skills the plugin invokes (see below).
set -euo pipefail
CASE="$(cd "${1:?usage: _scaffold.sh <case-dir>}" && pwd)"
EVALS="$(cd "$CASE/.." && pwd)"
REQUIRED=(grilling domain-modeling tdd diagnosing-bugs code-review codebase-design setup-matt-pocock-skills setup-pre-commit setup-ts-deep-modules)

rsync -a --exclude node_modules "$EVALS/_fixture/" ./
if [[ -n "${SEAMS_FIXTURE_NODE_MODULES:-}" ]]; then
  ln -s "$SEAMS_FIXTURE_NODE_MODULES" node_modules
else
  npm ci --silent --no-audit --no-fund --prefer-offline
fi

export GIT_AUTHOR_NAME=bench GIT_AUTHOR_EMAIL=bench@example.com
export GIT_COMMITTER_NAME=bench GIT_COMMITTER_EMAIL=bench@example.com
git init -q -b main
git add -A
git commit -qm "baseline: OrderKit fixture"
bash "$CASE/setup.sh"

# Matt Pocock's skills for an eval run. A run loads nothing from the runner's config, and nothing
# at project scope either, but it does load user skills from its own config directory: the runner
# gives this scaffold a throwaway $HOME whose sibling `config` becomes that directory (observed on
# Claude Code 2.1.278; it writes its settings.json there after the scaffold has run). So when $HOME
# is not the account's real home, the nine required skills are copied from the runner's config into
# <run>/config/skills, symlinks resolved. The runner's config is what Claude Code's is: CLAUDE_CONFIG_DIR
# when set, else the account's ~/.claude, and never the other when the one set lacks them (a machine
# without the skills must look the same to the suite as to a run). A harness run (a real $HOME) needs
# nothing: the runner's own config already holds them. Missing skills are named on stderr and the
# scaffold goes on, so the run then shows what that machine has.
REAL_HOME="$(python3 -c 'import os, pwd; print(pwd.getpwuid(os.getuid()).pw_dir)' 2>/dev/null || true)"
if [[ -n "$REAL_HOME" && "$HOME" != "$REAL_HOME" ]]; then
  SKILLS="${CLAUDE_CONFIG_DIR:-$REAL_HOME/.claude}/skills"
  TARGET="$(dirname "$HOME")/config/skills"
  missing=()
  for s in "${REQUIRED[@]}"; do
    if [[ -n "$SKILLS" && -f "$SKILLS/$s/SKILL.md" ]]; then
      mkdir -p "$TARGET"
      [[ -e "$TARGET/$s" ]] || cp -RL "$SKILLS/$s" "$TARGET/$s"
    else
      missing+=("$s")
    fi
  done
  if (( ${#missing[@]} )); then
    echo "scaffold: Matt Pocock skills not found on this machine, not provided to the run: ${missing[*]}" >&2
  fi
fi
