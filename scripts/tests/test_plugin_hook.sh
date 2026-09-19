#!/usr/bin/env bash
# The plugin's SessionStart hook, run against fixture homes, working directories and a
# fixture copy of the plugin. The real ~/.claude is never touched.
set -euo pipefail
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
HOOK="$REPO/plugin/hooks/session-start"
TMP="$(mktemp -d)"; trap 'rm -rf "$TMP" "$HOMES_BASE"' EXIT
fail() { echo "FAIL: $*" >&2; exit 1; }
[[ -x "$HOOK" ]] || fail "hook missing or not executable: $HOOK"
# The fixture homes sit under a path of exactly 47 characters, so the byte counts the budget guard
# prints are the same on every machine (mktemp's own directory is 63 characters on macOS, 19 on
# Ubuntu), and longer than any real home (/Users/<name>, /home/<name>, a CI runner's).
HOMES_BASE="$(mktemp -d /tmp/seams.XXXXXXXX)"
HOMES="$HOMES_BASE/$(printf '%0*d' $((46 - ${#HOMES_BASE})) 0 | tr 0 h)"; mkdir -p "$HOMES"
[[ ${#HOMES} -eq 47 ]] || fail "fixture home base is ${#HOMES} characters, not 47: $HOMES"

# A fixture copy of the plugin whose bootstrap body is a known literal.
FIX="$TMP/plugin"
mkdir -p "$FIX/hooks" "$FIX/skills/using-matt-pocock-skills"
cp "$HOOK" "$FIX/hooks/session-start"; cp "$REPO/plugin/hooks/seams_gate.py" "$FIX/hooks/"
cat > "$FIX/skills/using-matt-pocock-skills/SKILL.md" <<'MD'
---
name: using-matt-pocock-skills
description: fixture description that must not be injected
---

Fixture routing policy line.
Routing details: ${CLAUDE_PLUGIN_ROOT}/skills/using-matt-pocock-skills/references/routing.md
MD
FIX_REAL=$(cd "$FIX" && pwd -P)

# The nine skills the bootstrap routes to; a home counts as installed only when every one is there.
REQUIRED=(grilling domain-modeling tdd diagnosing-bugs code-review codebase-design setup-matt-pocock-skills setup-pre-commit setup-ts-deep-modules)
# skills <dir> [name...]: SKILL.md files for the named skills (all nine by default) under <dir>.
skills() { local dir="$1"; shift; local names=("$@"); [[ $# -eq 0 ]] && names=("${REQUIRED[@]}")
           local n; for n in "${names[@]}"; do mkdir -p "$dir/$n"; : > "$dir/$n/SKILL.md"; done; }
MP_HOME="$HOMES/home-mp"; skills "$MP_HOME/.claude/skills"
PARTIAL_HOME="$HOMES/home-partial"                      # a realistic partial: two skills he added since the install
skills "$PARTIAL_HOME/.claude/skills" grilling domain-modeling tdd diagnosing-bugs code-review setup-matt-pocock-skills setup-pre-commit
BARE_HOME="$HOMES/home-bare"; mkdir -p "$BARE_HOME/.claude/skills"
CUSTOM_CONFIG="$HOMES/custom config dir"; skills "$CUSTOM_CONFIG/skills"                # CLAUDE_CONFIG_DIR, with spaces
# skills.sh installs each skill as a symlink into its own store; some people link the whole directory.
MANAGER="$TMP/manager/skills"; skills "$MANAGER"
LINK_HOME="$HOMES/home-links"; mkdir -p "$LINK_HOME/.claude/skills"
for n in "${REQUIRED[@]}"; do ln -s "$MANAGER/$n" "$LINK_HOME/.claude/skills/$n"; done
DIRLINK_HOME="$HOMES/home-dirlink"; mkdir -p "$DIRLINK_HOME/.claude"; ln -s "$MANAGER" "$DIRLINK_HOME/.claude/skills"
unset CLAUDE_CONFIG_DIR   # the caller's shell must not decide where the hook looks
PLAIN="$TMP/plain"; mkdir -p "$PLAIN"
REPO_UNSET="$TMP/repo-unset"; mkdir -p "$REPO_UNSET/sub/dir"; git -C "$REPO_UNSET" init -q
REPO_SET="$TMP/repo-set"; mkdir -p "$REPO_SET/docs/agents"; git -C "$REPO_SET" init -q
: > "$REPO_SET/docs/agents/issue-tracker.md"

# context <plugin-dir> <home> <cwd> [config-dir] [root]: the injected context, or nothing when the
# hook prints nothing. The fourth argument, when given, is the session's CLAUDE_CONFIG_DIR; the
# fifth, the CLAUDE_PLUGIN_ROOT Claude Code would supply.
context() {
  local out event="{\"hook_event_name\":\"SessionStart\",\"source\":\"startup\",\"cwd\":\"$3\"}"
  out=$(env HOME="$2" ${4:+CLAUDE_CONFIG_DIR="$4"} ${5:+CLAUDE_PLUGIN_ROOT="$5"} "$1/hooks/session-start" <<< "$event") \
    || fail "hook exited non-zero"
  [[ -z "$out" ]] && return 0
  python3 -c '
import json, sys
h = json.loads(sys.stdin.read())["hookSpecificOutput"]
assert h["hookEventName"] == "SessionStart", h
print(h["additionalContext"])' <<< "$out" || fail "malformed hook output: $out"
}

# The injection wraps the bootstrap body, without its frontmatter.
C=$(context "$FIX" "$MP_HOME" "$PLAIN")
[[ "$C" == "<EXTREMELY_IMPORTANT>"* && "$C" == *"</EXTREMELY_IMPORTANT>" ]] || fail "wrapper missing: $C"
[[ "$C" == *"Fixture routing policy line."* ]] || fail "bootstrap body missing: $C"
[[ "$C" != *"fixture description"* && "$C" != *"name: using-matt-pocock-skills"* ]] || fail "frontmatter leaked: $C"

# ${CLAUDE_PLUGIN_ROOT} in the body becomes the plugin's absolute path, so the injected
# bootstrap can point at its own reference files.
[[ "$C" == *"Routing details: $FIX_REAL/skills/using-matt-pocock-skills/references/routing.md"* ]] \
  || fail "plugin root not substituted: $C"
[[ "$C" != *'${CLAUDE_PLUGIN_ROOT}'* ]] || fail "placeholder left in the injection: $C"

# When Claude Code supplies CLAUDE_PLUGIN_ROOT, that root wins over the hook's own location:
# a plugin installed from a local directory runs from that directory, not from the cache copy.
ROOT_OVERRIDE="$TMP/root-override"; mkdir -p "$ROOT_OVERRIDE"
C=$(CLAUDE_PLUGIN_ROOT="$ROOT_OVERRIDE" HOME="$MP_HOME" "$FIX/hooks/session-start" <<< '{}' \
  | python3 -c 'import json, sys; print(json.load(sys.stdin)["hookSpecificOutput"]["additionalContext"])')
[[ "$C" == *"Routing details: $ROOT_OVERRIDE/skills/using-matt-pocock-skills/references/routing.md"* ]] \
  || fail "CLAUDE_PLUGIN_ROOT not honoured: $C"

# The MP line names the installed skills directory when every required skill is there, and
# looks where Claude Code does: CLAUDE_CONFIG_DIR when set (spaces and all), else ~/.claude.
C=$(context "$FIX" "$MP_HOME" "$PLAIN")
[[ "$C" == *"$MP_HOME/.claude/skills"* && "$C" != *"not installed"* && "$C" != *"missing"* ]] || fail "MP location line wrong for an MP home: $C"
C=$(context "$FIX" "$BARE_HOME" "$PLAIN" "$CUSTOM_CONFIG")
[[ "$C" == *"$CUSTOM_CONFIG/skills"* && "$C" != *"not installed"* && "$C" != *"missing"* ]] \
  || fail "CLAUDE_CONFIG_DIR not honoured for the skills directory: $C"

# A partial install is reported as what it is: the missing names and the install command,
# never "installed" on the strength of one sentinel file, and never a present name as missing.
C=$(context "$FIX" "$PARTIAL_HOME" "$PLAIN")
[[ "$C" == *"missing codebase-design, setup-ts-deep-modules"* && "$C" == *"npx skills add mattpocock/skills -g -a claude-code"* ]] \
  || fail "partial install not reported with the missing names and the install command: $C"
[[ "$C" != *"skill files"* ]] || fail "partial install reported as installed: $C"
MISSING_LINE=$(grep missing <<< "$C")
[[ $MISSING_LINE != *grilling* && $MISSING_LINE != *tdd* ]] || fail "a present skill listed as missing: $C"

# Symlinked skill directories, and a symlinked skills directory, count as installed.
for H in "$LINK_HOME" "$DIRLINK_HOME"; do
  C=$(context "$FIX" "$H" "$PLAIN")
  [[ "$C" == *"$H/.claude/skills"* && "$C" != *"not installed"* && "$C" != *"missing"* ]] \
    || fail "symlinked skills not accepted (HOME=$H): $C"
done

# Skills installed at project scope (<repo>/.claude/skills, skills.sh without -g, and what an
# eval run's scaffold provides) count too: a bare home with a project-scope install is installed,
# named by the project path; a bare home with a partial project install is missing the rest.
PROJ_SKILLS="$TMP/proj-skills"; mkdir -p "$PROJ_SKILLS"; (cd "$PROJ_SKILLS" && git init -q)
skills "$PROJ_SKILLS/.claude/skills"
C=$(context "$FIX" "$BARE_HOME" "$PROJ_SKILLS")
[[ "$C" == *"$PROJ_SKILLS/.claude/skills"* && "$C" != *"not installed"* && "$C" != *"missing"* ]] \
  || fail "project-scope skills not counted: $C"
PROJ_PART="$TMP/proj-partial"; mkdir -p "$PROJ_PART"; (cd "$PROJ_PART" && git init -q)
skills "$PROJ_PART/.claude/skills" grilling tdd
C=$(context "$FIX" "$BARE_HOME" "$PROJ_PART")
[[ "$C" == *"missing"* && "$C" == *"codebase-design"* && "$C" != *"skill files"* ]] || fail "partial project-scope install reported as installed: $C"

# No install at all says so, with the install command.
C=$(context "$FIX" "$BARE_HOME" "$PLAIN")
[[ "$C" == *"not installed"* && "$C" == *"npx skills add mattpocock/skills -g -a claude-code"* ]] || fail "MP not-installed line missing for a bare home: $C"

# The repo-setup line appears only inside a git repo that lacks docs/agents/issue-tracker.md.
C=$(context "$FIX" "$MP_HOME" "$REPO_UNSET/sub/dir")
[[ "$C" == *"matt-pocock-workflow:foundations"* ]] || fail "setup line missing in a repo that is not set up: $C"
C=$(context "$FIX" "$MP_HOME" "$REPO_SET")
[[ "$C" != *"matt-pocock-workflow:foundations"* ]] || fail "setup line shown in a set-up repo: $C"
C=$(context "$FIX" "$MP_HOME" "$PLAIN")
[[ "$C" != *"matt-pocock-workflow:foundations"* ]] || fail "setup line shown outside a git repo: $C"

# Without a cwd in the event, the hook falls back to its own working directory.
C=$(cd "$REPO_UNSET" && HOME="$MP_HOME" "$FIX/hooks/session-start" <<< '{}' \
  | python3 -c 'import json, sys; print(json.load(sys.stdin)["hookSpecificOutput"]["additionalContext"])') \
  || fail "hook failed on an event without cwd"
[[ "$C" == *"matt-pocock-workflow:foundations"* ]] || fail "no fallback to the process working directory: $C"

# Fail open: bad input or a broken plugin prints nothing on stdout and exits 0; the traceback
# goes to stderr, which Claude Code keeps for the debug log and never shows the user.
OUT=$(HOME="$MP_HOME" "$FIX/hooks/session-start" <<< 'not json' 2> "$TMP/err") \
  || fail "hook exited non-zero on garbage stdin"
[[ -z "$OUT" ]] || fail "hook printed to stdout on garbage stdin: $OUT"
grep -q 'Traceback' "$TMP/err" || fail "hook should write the traceback to stderr on garbage stdin"
BROKEN="$TMP/broken"; cp -R "$FIX" "$BROKEN"; rm "$BROKEN/skills/using-matt-pocock-skills/SKILL.md"
OUT=$(HOME="$MP_HOME" "$BROKEN/hooks/session-start" <<< '{}' 2> "$TMP/err") \
  || fail "hook exited non-zero without its bootstrap file"
[[ -z "$OUT" ]] || fail "hook printed to stdout without its bootstrap file: $OUT"
UNREADABLE="$TMP/unreadable"; cp -R "$FIX" "$UNREADABLE"; chmod 000 "$UNREADABLE/skills/using-matt-pocock-skills/SKILL.md"
if [[ ! -r "$UNREADABLE/skills/using-matt-pocock-skills/SKILL.md" ]]; then   # root can read anything
  OUT=$(HOME="$MP_HOME" "$UNREADABLE/hooks/session-start" <<< '{}' 2> "$TMP/err") \
    || fail "hook exited non-zero with an unreadable bootstrap file"
  [[ -z "$OUT" ]] || fail "hook printed to stdout with an unreadable bootstrap file: $OUT"
fi
chmod 644 "$UNREADABLE/skills/using-matt-pocock-skills/SKILL.md"   # so the trap can remove it

# Guard: the real bootstrap, injected from a cache-length plugin path (120 characters) with both
# dynamic lines, stays at or under 2,900 bytes: the 3,000-byte budget less 100 bytes of headroom.
# Every MP-line variant: installed, a realistic partial (two names missing), not installed,
# symlinked, and a custom config directory. The fixture homes' fixed length keeps the counts the
# same on every machine.
ROOT120="/$(printf '%0119d' 0 | tr 0 a)"; [[ ${#ROOT120} -eq 120 ]] || fail "ROOT120 is ${#ROOT120} characters"
budget() {   # budget <home> [config-dir]
  local C N; C=$(context "$REPO/plugin" "$1" "$REPO_UNSET" "${2:-}" "$ROOT120")
  [[ "$C" == *"$ROOT120/skills/using-matt-pocock-skills/references/routing.md"* ]] || fail "the 120-character root was not injected: $C"
  N=$(printf '%s' "$C" | wc -c | tr -d ' ')
  (( N <= 2900 )) || fail "injection is $N bytes from a 120-character plugin path, over 2,900 (3,000 less 100 headroom) (HOME=$1${2:+ CLAUDE_CONFIG_DIR=$2})"
  echo "  $N bytes: HOME=$(basename "$1")${2:+ CLAUDE_CONFIG_DIR=$(basename "$2")}"
}
for H in "$MP_HOME" "$PARTIAL_HOME" "$BARE_HOME" "$LINK_HOME" "$DIRLINK_HOME"; do budget "$H"; done
budget "$BARE_HOME" "$CUSTOM_CONFIG"

# The bootstrap injects even when the gate module is missing beside the hook (the ledger is
# skipped, the traceback goes to stderr, the context still comes out).
LONE="$TMP/lone"; mkdir -p "$LONE/hooks"; cp -R "$FIX/skills" "$LONE/skills"; cp "$HOOK" "$LONE/hooks/session-start"
C=$(printf '{"cwd":"%s","source":"startup","session_id":"lone"}' "$PLAIN" | CLAUDE_PLUGIN_ROOT="$LONE" HOME="$MP_HOME" "$LONE/hooks/session-start" 2>/dev/null \
    | python3 -c 'import json,sys; print(json.load(sys.stdin)["hookSpecificOutput"]["additionalContext"])')
grep -q 'Fixture routing policy line' <<< "$C" || fail "bootstrap should inject without seams_gate.py"

echo "test_plugin_hook: OK"
