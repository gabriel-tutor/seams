#!/usr/bin/env bash
# The installer against fixture homes and a stub claude CLI that answers `plugin list` and
# `plugin marketplace list` from a state file, records every call, and fails the subcommand named
# in STUB_FAIL. The real ~/.claude, the network and skills.sh are never touched.
set -euo pipefail
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
fail() { echo "FAIL: $*" >&2; exit 1; }
REQUIRED=(grilling domain-modeling tdd diagnosing-bugs code-review codebase-design setup-matt-pocock-skills setup-pre-commit setup-ts-deep-modules)
PLUGIN_ID="seams@seams"
OLD_ID="matt-pocock-workflow@my-workflow-agent-skills"   # the plugin before 5.0.0 (seams-rename decision 5)
# The one skills.sh command the hook, the installer and the README name, taken from the hook's line.
SKILLS_CMD=$(grep -o 'npx skills add mattpocock/skills[^`]*' "$REPO/plugin/hooks/session-start" | head -1)
[[ $SKILLS_CMD == "npx skills add mattpocock/skills -g -a claude-code" ]] || fail "the hook's install command changed: $SKILLS_CMD"

# The stub: state lines are "marketplace <name>" and "plugin <id> enabled|disabled". Like the CLI,
# install leaves a plugin enabled and enable/disable fail when the plugin is already in that state.
mkdir -p "$TMP/bin"
cat > "$TMP/bin/claude" <<'SH'
#!/usr/bin/env bash
LOG="${STUB_LOG:?}"; STATE="${STUB_STATE:?}"; touch "$STATE"
echo "$*" >> "$LOG"
if [[ -n "${STUB_FAIL:-}" && "$*" == "$STUB_FAIL"* ]]; then echo "✘ Failed: stub says no to \`$STUB_FAIL\`"; exit 1; fi
set_status() { awk -v id="$1" -v s="$2" '$1=="plugin" && $2==id {$3=s} {print}' "$STATE" > "$STATE.tmp" && mv "$STATE.tmp" "$STATE"; }
case "$*" in
  --version) echo "0.0.0 (stub)";;
  "plugin marketplace list")
    echo "Configured marketplaces:"; echo
    awk '$1=="marketplace" {print "  ❯ " $2; print "    Source: Directory (/stub)"; print ""}' "$STATE";;
  "plugin marketplace add "*)
    grep -q "^marketplace seams$" "$STATE" || echo "marketplace seams" >> "$STATE"
    echo "✔ Successfully added marketplace: seams";;
  "plugin marketplace update "*) echo "✔ Successfully updated marketplace: $4";;
  "plugin list")
    grep -q "^plugin " "$STATE" || { echo "No plugins installed. Use \`claude plugin install\` to install a plugin."; exit 0; }
    echo "Installed plugins:"; echo
    awk '$1=="plugin" {print "  ❯ " $2; print "    Version: 0.0.0"; print "    Scope: user"; print "    Status: " ($3=="enabled" ? "✔ enabled" : "✘ disabled"); print ""}' "$STATE";;
  "plugin install "*)
    grep -q "^plugin $3 " "$STATE" && { echo "✔ Plugin \"$3\" is already installed (scope: user)"; exit 0; }
    echo "plugin $3 enabled" >> "$STATE"; echo "✔ Successfully installed plugin: $3 (scope: user)";;
  "plugin update "*)
    grep -q "^plugin $3 " "$STATE" || { echo "✘ Failed to update plugin \"$3\": Plugin not found"; exit 1; }
    echo "✔ $3 is already at the latest version";;
  "plugin enable "*)
    grep -q "^plugin $3 disabled$" "$STATE" || { echo "✘ Failed to enable plugin \"$3\": already enabled"; exit 1; }
    set_status "$3" enabled; echo "✔ Successfully enabled plugin: $3";;
  "plugin disable "*)
    grep -q "^plugin $3 enabled$" "$STATE" || { echo "✘ Failed to disable plugin \"$3\": already disabled"; exit 1; }
    set_status "$3" disabled; echo "✔ Successfully disabled plugin: $3";;
  *) echo "stub: unexpected call: $*" >&2; exit 2;;
esac
SH
chmod +x "$TMP/bin/claude"
# The installer only checks that node is there and prints its version (skills.sh is never run here), so a stand-in
# does: the suite needs no Node of its own.
printf '#!/bin/sh\necho v22.0.0\n' > "$TMP/bin/node"; chmod +x "$TMP/bin/node"
ln -sf "$(command -v python3)" "$TMP/bin/python3"

# home <dir> [skill...]: a fixture home whose Matt Pocock skills are symlinks into a store, the way
# skills.sh lays them out; all nine required ones unless names are given (--none: no skills). Settings
# hold a real rule.
home() {
  local h="$1" n; shift; local names=("$@"); [[ $# -eq 0 ]] && names=("${REQUIRED[@]}"); [[ ${1:-} == --none ]] && names=()
  mkdir -p "$h/.claude/skills" "$h/store"
  for n in ${names[@]+"${names[@]}"}; do mkdir -p "$h/store/$n"; : > "$h/store/$n/SKILL.md"; ln -s "$h/store/$n" "$h/.claude/skills/$n"; done
  echo '{"model":"opus","permissions":{"allow":["Bash(git *)"]}}' > "$h/.claude/settings.json"
}
# run <home> [VAR=value...]: the installer in that home with the stub first on PATH and no
# terminal: it runs in its own session, so /dev/tty is not openable even when this test is started
# from one (otherwise a home without the skills would start the interactive skills.sh step). Sets
# OUT, ERR and CODE, and leaves the stub's log at $LOG and its state at $STATE.
PY="$(command -v python3)"
DETACH='import os, sys
pid = os.fork()
if pid == 0:
    os.setsid(); os.execvp(sys.argv[1], sys.argv[1:])
_, st = os.waitpid(pid, 0)
sys.exit(st >> 8 if os.WIFEXITED(st) else 128 + os.WTERMSIG(st))'
run() {
  local h="$1"; shift
  LOG="$h/claude.log"; STATE="$h/claude.state"; : > "$LOG"; touch "$STATE"; CODE=0
  OUT=$(env -i HOME="$h" CLAUDE_CONFIG_DIR="$h/.claude" PATH="$TMP/bin:/usr/bin:/bin" STUB_LOG="$LOG" STUB_STATE="$STATE" "$@" \
        "$PY" -c "$DETACH" bash "$REPO/scripts/install.sh" </dev/null 2>"$h/stderr") || CODE=$?
  ERR=$(cat "$h/stderr")
}
calls() { grep -c "^$1" "$LOG" || true; }   # how many recorded calls start with $1

# 1. A fresh machine: the marketplace is added and the plugin installed, nothing else is changed.
H="$TMP/fresh"; home "$H"; BEFORE=$(cat "$H/.claude/settings.json")
run "$H"
[[ $CODE -eq 0 ]] || fail "fresh install exited $CODE: $OUT $ERR"
[[ "$(cat "$H/.claude/settings.json")" == "$BEFORE" ]] || fail "settings.json changed: $(cat "$H/.claude/settings.json")"
[[ -z "$(ls "$H/.claude" | grep -v -e '^settings.json$' -e '^skills$')" ]] || fail "the installer wrote into the config dir: $(ls "$H/.claude")"
[[ $(calls "plugin marketplace add ") -eq 1 ]] || fail "expected one marketplace add, log: $(cat "$LOG")"
[[ $(calls "plugin install $PLUGIN_ID") -eq 1 ]] || fail "expected one plugin install, log: $(cat "$LOG")"
[[ $(calls "plugin enable ") -eq 0 ]] || fail "install leaves the plugin enabled; enable should not be issued, log: $(cat "$LOG")"
grep -q "^plugin $PLUGIN_ID enabled$" "$STATE" || fail "the plugin is not installed and enabled in the stub state: $(cat "$STATE")"

# 2. A `claude plugin` command that fails stops the installer there, naming the step and its output.
H="$TMP/broken"; home "$H"
run "$H" STUB_FAIL="plugin install"
[[ $CODE -ne 0 ]] || fail "installer exited 0 although plugin install failed: $OUT"
[[ $ERR == *'`claude plugin install '"$PLUGIN_ID"'` failed (exit 1)'* ]] || fail "the error does not name the failed step: $ERR"
[[ $ERR == *"stub says no"* ]] || fail "the error does not show the command's output: $ERR"
[[ $(calls "plugin enable ") -eq 0 && $(calls "plugin disable ") -eq 0 ]] || fail "steps ran after the failure, log: $(cat "$LOG")"
[[ $OUT != *"Done."* && $OUT != *"plugin installed"* ]] || fail "the installer reported success after a failed step: $OUT"
for listing in "plugin marketplace list" "plugin list"; do
  H="$TMP/broken-$(tr ' ' - <<< "$listing")"; home "$H"
  run "$H" STUB_FAIL="$listing"
  [[ $CODE -ne 0 && $ERR == *'`claude '"$listing"'` failed (exit 1)'* && $ERR == *"stub says no"* ]] \
    || fail "a failing \`claude $listing\` should stop the installer with its output: exit $CODE, $ERR"
  [[ "$(tail -1 "$LOG")" == "$listing" && $(calls "plugin install ") -eq 0 ]] || fail "calls issued after \`claude $listing\` failed, log: $(cat "$LOG")"
done

# 3. A second run in the fresh home: nothing added or installed again, only refreshed; exit 0.
H="$TMP/fresh"; BEFORE=$(cat "$H/.claude/settings.json"); TREE=$(ls -laR "$H/.claude")
run "$H"
[[ $CODE -eq 0 ]] || fail "second run exited $CODE: $OUT $ERR"
[[ "$(cat "$H/.claude/settings.json")" == "$BEFORE" && "$(ls -laR "$H/.claude")" == "$TREE" ]] || fail "second run changed the config dir"
[[ $(calls "plugin marketplace add ") -eq 0 && $(calls "plugin install ") -eq 0 && $(calls "plugin enable ") -eq 0 ]] \
  || fail "second run re-added or re-installed, log: $(cat "$LOG")"
[[ $(calls "plugin marketplace update seams") -eq 1 && $(calls "plugin update $PLUGIN_ID") -eq 1 ]] \
  || fail "second run should refresh the marketplace and update the plugin, log: $(cat "$LOG")"
[[ $OUT == *"already installed; updated"* && $OUT == *"already enabled"* ]] || fail "second run's report: $OUT"

# 4. Without Matt Pocock's skills and without a terminal to pick them in, the installer stops with
# the command to run; a partial install names what is missing. Neither reaches the plugin steps.
H="$TMP/bare"; home "$H" --none
run "$H"
[[ $CODE -ne 0 ]] || fail "installer exited 0 without Matt Pocock's skills and no tty: $OUT"
[[ $ERR == *"\`$SKILLS_CMD\`"* && $ERR == *"no terminal"* ]] || fail "the error does not name the install command: $ERR"
[[ $(calls "plugin ") -eq 0 ]] || fail "plugin steps ran without the skills, log: $(cat "$LOG")"
H="$TMP/partial"; home "$H" grilling
run "$H"
[[ $CODE -ne 0 ]] || fail "installer exited 0 with only grilling installed: $OUT"
[[ $OUT == *"missing from $H/.claude/skills: domain-modeling tdd "* && $OUT == *"setup-ts-deep-modules" && $OUT != *" grilling "* ]] \
  || fail "the missing skills are not named, or carry a trailing space: $OUT"
[[ $ERR == *"\`$SKILLS_CMD\`"* ]] || fail "the partial-install error should name \`$SKILLS_CMD\`: $ERR"

# 5. A python3 older than 3.9 first on PATH (macOS's system interpreter is 3.9.6; older ones exist
# on old Linux images) stops the installer, naming the version it found.
mkdir -p "$TMP/oldpy"; printf '#!/bin/sh\necho "Python 3.8.10"\n' > "$TMP/oldpy/python3"; chmod +x "$TMP/oldpy/python3"
H="$TMP/oldpython"; home "$H"
run "$H" PATH="$TMP/oldpy:$TMP/bin:/usr/bin:/bin"
[[ $CODE -ne 0 ]] || fail "installer exited 0 with python3 3.8.10: $OUT"
[[ $ERR == *"3.8.10"* && $ERR == *"3.9"* ]] || fail "the error does not name the version found and the one needed: $ERR"
[[ $(calls "plugin ") -eq 0 ]] || fail "plugin steps ran with an old python3, log: $(cat "$LOG")"

# 6. A plugin someone disabled is enabled again; Superpowers is disabled only on request, and only
# when it is there to disable.
H="$TMP/disabled"; home "$H"
printf 'marketplace seams\nplugin %s disabled\nplugin superpowers@claude-plugins-official enabled\n' "$PLUGIN_ID" > "$H/claude.state"
run "$H" MPW_DISABLE_SUPERPOWERS=1
[[ $CODE -eq 0 ]] || fail "re-enable run exited $CODE: $OUT $ERR"
[[ $(calls "plugin install ") -eq 0 && $(calls "plugin update $PLUGIN_ID") -eq 1 && $(calls "plugin enable $PLUGIN_ID") -eq 1 ]] \
  || fail "a disabled plugin should be updated and enabled, not installed, log: $(cat "$LOG")"
[[ $(calls "plugin disable superpowers@claude-plugins-official") -eq 1 ]] || fail "Superpowers was not disabled on request, log: $(cat "$LOG")"
grep -q "^plugin $PLUGIN_ID enabled$" "$H/claude.state" && grep -q "^plugin superpowers@claude-plugins-official disabled$" "$H/claude.state" \
  || fail "stub state after the run: $(cat "$H/claude.state")"
run "$H" MPW_DISABLE_SUPERPOWERS=1
[[ $CODE -eq 0 && $(calls "plugin disable ") -eq 0 && $OUT == *"already disabled"* ]] || fail "an already disabled Superpowers should be skipped: $OUT $ERR"
run "$H"
[[ $CODE -eq 0 && $(calls "plugin disable ") -eq 0 && $OUT == *"left as is"* ]] || fail "Superpowers should be left alone by default: $OUT $ERR"

# 6b. The plugin before 5.0.0 still installed, or its marketplace still known: two copies' gates would both run and the
# old one refuses every `seams:` declaration, so the installer stops, removes nothing, and prints the two commands that
# remove the old copy (seams-rename decision 5).
for state in "marketplace my-workflow-agent-skills\nplugin $OLD_ID enabled" "marketplace my-workflow-agent-skills"; do
  H="$TMP/old-$RANDOM"; home "$H"; printf "$state\n" > "$H/claude.state"; BEFORE_STATE=$(cat "$H/claude.state")
  run "$H"
  [[ $CODE -ne 0 ]] || fail "installer exited 0 with the old plugin or marketplace present: $OUT"
  [[ $ERR == *"claude plugin marketplace remove my-workflow-agent-skills"* ]] || fail "the error does not name the marketplace removal: $ERR"
  if [[ $state == *plugin* ]]; then [[ $ERR == *"claude plugin uninstall $OLD_ID"* ]] || fail "the error does not name the uninstall: $ERR"; fi
  [[ $(calls "plugin marketplace add ") -eq 0 && $(calls "plugin install ") -eq 0 && $(calls "plugin uninstall") -eq 0 ]] \
    || fail "the installer changed the plugin list with the old copy present, log: $(cat "$LOG")"
  [[ "$(cat "$H/claude.state")" == "$BEFORE_STATE" ]] || fail "the stub state changed: $(cat "$H/claude.state")"
done

# 7. Static: the installer checks the same skills the session-start hook reports on (and the two
# hook suites use that list); the install command is spelled the same way in the README; nothing
# still describes the settings.json step; the compatibility record exists with its fields and the
# README points at it.
HOOK_LIST=$(python3 - "$REPO/plugin/hooks/session-start" <<'LIST'
import ast, sys
tree = ast.parse(open(sys.argv[1]).read())
for node in ast.walk(tree):
    if isinstance(node, ast.Assign) and any(getattr(t, "id", "") == "REQUIRED_SKILLS" for t in node.targets):
        print(" ".join(ast.literal_eval(node.value)))
LIST
)
INSTALLER_LIST=$(bash -c 'eval "$(sed -n "/^REQUIRED_SKILLS=(/,/)/p" "$1")"; echo "${REQUIRED_SKILLS[*]}"' _ "$REPO/scripts/install.sh")
[[ -n "$HOOK_LIST" && "$HOOK_LIST" == "$INSTALLER_LIST" ]] || fail "the installer's skill list differs from the hook's: [$INSTALLER_LIST] vs [$HOOK_LIST]"
HOOK_SUITE_LIST=$(bash -c 'eval "$(grep -m1 "^REQUIRED=(" "$1")"; echo "${REQUIRED[*]}"' _ "$REPO/scripts/tests/test_plugin_hook.sh")
[[ "$HOOK_LIST" == "${REQUIRED[*]}" && "$HOOK_LIST" == "$HOOK_SUITE_LIST" ]] \
  || fail "a test's skill list differs from the hook's: [${REQUIRED[*]}] / [$HOOK_SUITE_LIST] vs [$HOOK_LIST]"
[[ $(grep -c -F -- "\`$SKILLS_CMD\`" "$REPO/README.md") -ge 1 && $(grep -c "npx skills" "$REPO/README.md") -eq $(grep -c -F -- "$SKILLS_CMD" "$REPO/README.md") ]] \
  || fail "the README should name the install command exactly as the hook does: $SKILLS_CMD"
grep -q 'pre-mpw-install' "$REPO/README.md" "$REPO/scripts/install.sh" && fail "the settings backup is still described somewhere"
COMPAT="$REPO/docs/compatibility.md"
[[ -f "$COMPAT" ]] || fail "docs/compatibility.md is missing"
for needle in "Operating system" "Python" "Claude Code" "Matt Pocock's skills" "Superpowers" "Node" "3cca18b368ae95cdbdebbff572ccafa662551015"; do
  grep -q "$needle" "$COMPAT" || fail "docs/compatibility.md lacks: $needle"
done
grep -q "docs/compatibility.md" "$REPO/README.md" || fail "the README does not point at docs/compatibility.md"

echo "test_install: OK"
