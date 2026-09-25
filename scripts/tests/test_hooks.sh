#!/usr/bin/env bash
# The gate hooks, fed JSON on stdin the way Claude Code feeds them. Runs in a private TMPDIR so the
# ledger never touches the real one. PYTHON=/usr/bin/python3 runs them under another interpreter.
set -euo pipefail
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
HOOKS="$REPO/plugin/hooks"
PY="${PYTHON:-python3}"
TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
export TMPDIR="$TMP/tmpdir"; mkdir -p "$TMPDIR"
export CLAUDE_CONFIG_DIR="$TMP/config"; mkdir -p "$CLAUDE_CONFIG_DIR"
PROJ="$TMP/proj"; mkdir -p "$PROJ/src"
fail() { echo "FAIL: $*" >&2; exit 1; }

hook() { "$PY" "$HOOKS/$1"; }                      # stdin: the event; stdout: the hook's output
ev()   { printf '{"session_id":"s1","cwd":"%s","hook_event_name":"%s",%s}' "$PROJ" "$1" "$2"; }
pre_edit()   { ev PreToolUse "\"tool_name\":\"Edit\",\"tool_input\":{\"file_path\":\"$1\",\"old_string\":\"a\",\"new_string\":\"b\"}" | hook pre-tool-use; }
pre_bash()   { ev PreToolUse "\"tool_name\":\"Bash\",\"tool_input\":{\"command\":\"$1\"}" | hook pre-tool-use; }
post_skill() { ev PostToolUse "\"tool_name\":\"Skill\",\"tool_input\":{\"skill\":\"$1\"},\"tool_response\":{}" | hook post-tool-use; }
prompt()     { ev UserPromptSubmit "\"prompt\":\"$1\"" | hook user-prompt-submit; }
start()      { ev SessionStart "\"source\":\"$1\"" | hook session-start >/dev/null; }
stop()       { ev Stop "\"stop_hook_active\":$1,\"last_assistant_message\":\"done\"" | hook stop; }
denied()  { grep -q '"permissionDecision": *"deny"' <<< "$1"; }
blocked() { grep -q '"decision": *"block"' <<< "$1"; }
LEDGER="$TMPDIR/seams-$(id -u)/s1.json"

for h in pre-tool-use post-tool-use user-prompt-submit session-start stop; do
  [[ -x "$HOOKS/$h" ]] || fail "hook missing or not executable: $h"
done

# 1. A project edit with no declaration is refused, and the reason names the routes.
OUT=$(pre_edit "$PROJ/src/a.ts")
denied "$OUT" || fail "edit without a declaration should be denied: $OUT"
grep -q 'Seams gate' <<< "$OUT" || fail "reason should say Seams gate"
grep -q 'matt-pocock-workflow:trivial' <<< "$OUT" || fail "reason should name the trivial route"
grep -q 'diagnosing-bugs' <<< "$OUT" || fail "reason should name diagnosing-bugs"

# 2. A shell mutation is refused by its label; a read-only command is not.
OUT=$(pre_bash "sed -i s/a/b/ src/a.ts"); denied "$OUT" || fail "sed -i should be denied"
grep -q 'sed -i' <<< "$OUT" || fail "reason should name sed -i"
OUT=$(pre_bash "cat src/a.ts"); [[ -z "$OUT" ]] || fail "cat should pass silently: $OUT"
OUT=$(pre_bash "git status"); [[ -z "$OUT" ]] || fail "git status should pass silently: $OUT"

# 3. A write under the temp dir or the config dir is not a project change.
OUT=$(pre_edit "$TMPDIR/scratch.py"); [[ -z "$OUT" ]] || fail "temp-dir write should pass: $OUT"
OUT=$(pre_edit "$CLAUDE_CONFIG_DIR/memory/note.md"); [[ -z "$OUT" ]] || fail "config-dir write should pass: $OUT"
OUT=$(pre_bash "mkdir -p $TMPDIR/evid/checks && echo ok > $TMPDIR/evid/checks/x.log"); [[ -z "$OUT" ]] || fail "a shell write confined to the temp dir should pass: $OUT"
OUT=$(pre_bash "cp $TMPDIR/evid/checks/x.log $PROJ/src/x.log"); denied "$OUT" || fail "a copy into the project should still be denied: $OUT"
[[ ! -e "$LEDGER" ]] || ! grep -q '"label"' "$LEDGER" || fail "a temp-only shell write should not be recorded as a change"

# 4. A declaration opens the gate, and the allowed change is recorded (path, no content).
post_skill "matt-pocock-workflow:grill"
OUT=$(pre_edit "$PROJ/src/a.ts"); [[ -z "$OUT" ]] || fail "edit after a declaration should pass: $OUT"
grep -q '"path": *"'"$PROJ"'/src/a.ts"' "$LEDGER" || fail "ledger should record the change path"
grep -q 'old_string\|new_string' "$LEDGER" && fail "ledger must not record edit content"
grep -q '"skill": *"matt-pocock-workflow:grill"' "$LEDGER" || fail "ledger should record the declaration"

# 5. A Superpowers or domain skill is not a declaration.
prompt "add a feature"
post_skill "superpowers:brainstorming"
OUT=$(pre_edit "$PROJ/src/a.ts"); denied "$OUT" || fail "superpowers skill should not open the gate"
post_skill "frontend-design"
OUT=$(pre_edit "$PROJ/src/a.ts"); denied "$OUT" || fail "domain skill should not open the gate"

# 6. A new prompt starts a new request; a go-ahead keeps it; a typed slash command declares.
post_skill "tdd"
prompt "yes, go ahead"
OUT=$(pre_edit "$PROJ/src/a.ts"); [[ -z "$OUT" ]] || fail "a go-ahead should keep the declaration: $OUT"
prompt "[SYSTEM NOTIFICATION - NOT USER INPUT] a background task finished"
OUT=$(pre_edit "$PROJ/src/a.ts"); [[ -z "$OUT" ]] || fail "a machine-generated notice should keep the declaration: $OUT"
prompt '<agent-message from=\"a1\">\n[Subagent hand-back] #12: request changes\n</agent-message>'
OUT=$(pre_edit "$PROJ/src/a.ts"); [[ -z "$OUT" ]] || fail "a subagent's hand-back should keep the declaration: $OUT"
prompt "now fix the bug in pricing"
OUT=$(pre_edit "$PROJ/src/a.ts"); denied "$OUT" || fail "a new request should need a new declaration"
grep -q 'fix the bug' "$LEDGER" && fail "ledger must not record prompt text"
prompt "/to-spec"
OUT=$(pre_edit "$PROJ/src/a.ts"); [[ -z "$OUT" ]] || fail "a typed /to-spec should declare: $OUT"
prompt "/superpowers:brainstorming"
OUT=$(pre_edit "$PROJ/src/a.ts"); denied "$OUT" || fail "a typed superpowers command should not declare"
prompt "/pr-review 42"
OUT=$(pre_edit "$PROJ/src/a.ts"); [[ -z "$OUT" ]] || fail "a typed bare /pr-review (a Seams skill, manual only) should declare: $OUT"
grep -q '"skill": *"matt-pocock-workflow:pr-review"' "$LEDGER" || fail "the bare /pr-review should be recorded under its full name"
prompt "/using-matt-pocock-skills"
OUT=$(pre_edit "$PROJ/src/a.ts"); denied "$OUT" || fail "typing the routing policy itself should not declare"
prompt "/using-git-worktrees"
OUT=$(pre_edit "$PROJ/src/a.ts"); denied "$OUT" || fail "a bare Superpowers-copy name should not declare (the original shares it)"

# 7. A subagent's call is judged by the same session ledger.
post_skill "matt-pocock-workflow:implement"
OUT=$(printf '{"session_id":"s1","cwd":"%s","hook_event_name":"PreToolUse","agent_id":"a1","agent_type":"general-purpose","tool_name":"Write","tool_input":{"file_path":"%s/src/b.ts","content":"x"}}' "$PROJ" "$PROJ" | hook pre-tool-use)
[[ -z "$OUT" ]] || fail "subagent edit after the parent's declaration should pass: $OUT"

# 8. Session start: clear and startup reset the ledger; compact and resume keep it; a fork is a new
# session, which starts with an empty ledger and leaves its parent's alone.
start compact
OUT=$(pre_edit "$PROJ/src/a.ts"); [[ -z "$OUT" ]] || fail "compact should keep the ledger: $OUT"
start resume
OUT=$(pre_edit "$PROJ/src/a.ts"); [[ -z "$OUT" ]] || fail "resume should keep the ledger: $OUT"
printf '{"session_id":"s2","cwd":"%s","hook_event_name":"SessionStart","source":"fork"}' "$PROJ" | hook session-start >/dev/null
OUT=$(printf '{"session_id":"s2","cwd":"%s","hook_event_name":"PreToolUse","tool_name":"Edit","tool_input":{"file_path":"%s/src/a.ts","old_string":"a","new_string":"b"}}' "$PROJ" "$PROJ" | hook pre-tool-use)
denied "$OUT" || fail "a forked session should start with an empty ledger: $OUT"
OUT=$(pre_edit "$PROJ/src/a.ts"); [[ -z "$OUT" ]] || fail "a fork should leave its parent's ledger alone: $OUT"
start clear
OUT=$(pre_edit "$PROJ/src/a.ts"); denied "$OUT" || fail "clear should reset the ledger"
post_skill "tdd"; start startup
OUT=$(pre_edit "$PROJ/src/a.ts"); denied "$OUT" || fail "startup should reset the ledger"

# 9. Old ledgers are swept at session start; the session's own is kept.
post_skill "tdd"
OLD="$TMPDIR/seams-$(id -u)/old-session.json"; cp "$LEDGER" "$OLD"; touch -t 202001010000 "$OLD"
start compact
[[ ! -e "$OLD" ]] || fail "an eight-day-old ledger should be removed"
[[ -e "$LEDGER" ]] || fail "the live ledger should be kept"

# 10. The done-check: a turn that changed code cannot end until verification ran; once per turn.
prompt "change the label"; post_skill "tdd"
OUT=$(stop false); [[ -z "$OUT" ]] || fail "stop with no changes should pass: $OUT"
pre_edit "$PROJ/src/a.ts" >/dev/null
OUT=$(stop false); blocked "$OUT" || fail "stop after an unverified code change should block: $OUT"
grep -q 'Seams done-check' <<< "$OUT" || fail "block reason should say Seams done-check"
grep -q "$PROJ/src/a.ts" <<< "$OUT" || fail "block reason should name the file"
grep -q 'verification-before-completion' <<< "$OUT" || fail "block reason should name the verification skill"
OUT=$(stop true); [[ -z "$OUT" ]] || fail "the second stop of the turn should pass: $OUT"
post_skill "matt-pocock-workflow:verification-before-completion"
OUT=$(stop false); [[ -z "$OUT" ]] || fail "stop after verification should pass: $OUT"
pre_edit "$PROJ/README.md" >/dev/null
OUT=$(stop false); [[ -z "$OUT" ]] || fail "a documentation-only change should not block: $OUT"
pre_bash "sed -i s/a/b/ src/a.ts" >/dev/null
OUT=$(stop false); blocked "$OUT" || fail "an unverified shell mutation should block: $OUT"
grep -q 'sed -i' <<< "$OUT" || fail "block reason should name the shell label"
post_skill "superpowers:verification-before-completion"
OUT=$(stop false); [[ -z "$OUT" ]] || fail "Superpowers' verification copy should count: $OUT"
pre_bash "git commit -m x" >/dev/null
OUT=$(stop false); [[ -z "$OUT" ]] || fail "a commit after verification should not re-block: $OUT"

# 11. Every shell tool is gated. A Monitor watch's command is judged as a Bash command is, and a
# WebSocket watch runs nothing; a PowerShell command is a change unless it is on the read-only list.
# A write under the hook input's scratchpad_dir is scratch; without the field the temp rules stand.
pre_tool() { ev PreToolUse "\"tool_name\":\"$1\",\"tool_input\":$2${3:+,$3}" | hook pre-tool-use; }
WATCH='{"command":"tail -f server.log | tee src/copy.txt","description":"copy","timeout_ms":300000}'
REMOVE='{"command":"Remove-Item src -Recurse","description":"clean"}'
prompt "watch the server"
OUT=$(pre_tool Monitor "$WATCH"); denied "$OUT" || fail "a Monitor watch writing to the project should be denied: $OUT"
grep -q 'a shell command (`tee`)' <<< "$OUT" || fail "the refusal should name the watch's label: $OUT"
OUT=$(pre_tool Monitor '{"command":"tail -f server.log | grep --line-buffered ERROR","description":"errors","timeout_ms":300000}')
[[ -z "$OUT" ]] || fail "a read-only Monitor watch should pass: $OUT"
OUT=$(pre_tool Monitor '{"ws":{"url":"wss://events.example.com/stream"},"description":"events","timeout_ms":300000}')
[[ -z "$OUT" ]] || fail "a WebSocket watch should pass: $OUT"
OUT=$(pre_tool PowerShell "$REMOVE"); denied "$OUT" || fail "PowerShell outside the read-only list should be denied: $OUT"
grep -q 'Get-ChildItem' <<< "$OUT" || fail "the PowerShell refusal should name the read-only list: $OUT"
for C in "Get-Content README.md" "Get-ChildItem -Recurse" "Select-String -Path src -Pattern TODO" "git status" "git diff" "git log --oneline"; do
  OUT=$(pre_tool PowerShell "{\"command\":\"$C\",\"description\":\"read\"}"); [[ -z "$OUT" ]] || fail "PowerShell '$C' should pass: $OUT"
done
SP="/seams-hook-test-scratchpad/s1/scratchpad"      # outside every temp root: only the field makes it scratch
OUT=$(pre_tool Bash "{\"command\":\"echo ok > $SP/log.txt\"}" "\"scratchpad_dir\":\"$SP\"")
[[ -z "$OUT" ]] || fail "a shell write under scratchpad_dir should pass: $OUT"
OUT=$(pre_tool Edit "{\"file_path\":\"$SP/notes.py\",\"old_string\":\"a\",\"new_string\":\"b\"}" "\"scratchpad_dir\":\"$SP\"")
[[ -z "$OUT" ]] || fail "an edit under scratchpad_dir should pass: $OUT"
OUT=$(pre_tool Bash "{\"command\":\"echo ok > $SP/log.txt\"}"); denied "$OUT" || fail "without scratchpad_dir that write should be denied: $OUT"
OUT=$(pre_tool Bash "{\"command\":\"echo x > $PROJ/src/a.ts\"}" "\"scratchpad_dir\":\"$PROJ\"")
denied "$OUT" || fail "the working directory is never scratch, whatever scratchpad_dir says: $OUT"
post_skill "matt-pocock-workflow:implement"
OUT=$(pre_tool Monitor "$WATCH"); [[ -z "$OUT" ]] || fail "after a declaration the watch should pass: $OUT"
OUT=$(pre_tool PowerShell "$REMOVE"); [[ -z "$OUT" ]] || fail "after a declaration PowerShell should pass: $OUT"
grep -q '"tool": *"Monitor"' "$LEDGER" || fail "the ledger should record the Monitor change"
grep -q '"tool": *"PowerShell"' "$LEDGER" || fail "the ledger should record the PowerShell change"
grep -q 'Remove-Item\|server.log' "$LEDGER" && fail "the ledger must not record a command's text"

# 12. Garbage in: every hook exits 0 with no stdout.
for h in pre-tool-use post-tool-use user-prompt-submit session-start stop; do
  OUT=$(echo '{not json' | hook "$h" 2>/dev/null) || fail "$h should exit 0 on garbage"
  [[ -z "$OUT" ]] || fail "$h should print nothing on garbage: $OUT"
done

# 13. The ledger is private to the user. The mode is read through the interpreter rather than
# stat: BSD stat takes -f as a format, GNU stat as "file-system status", which prints a block for
# the file operand and exits 1 for the format operand, so the BSD-first fallback caught both.
MODE=$("$PY" -c 'import os, sys; print(oct(os.stat(sys.argv[1]).st_mode & 0o777)[-3:])' "$LEDGER")
[[ "$MODE" == "600" ]] || fail "ledger should be mode 600, is $MODE"

# 14. The hook config. PreToolUse sees every tool that edits or runs a shell, and every entry is in
# exec form (args), run as Claude Code spawns it: command and args with ${CLAUDE_PLUGIN_ROOT} put in
# as plain strings, no shell. Run that way from a plugin root whose path holds a space, under the
# interpreter being tested, each hook gives its usual answer.
SPACED="$TMP/plugin root"; mkdir -p "$SPACED"; cp -R "$HOOKS" "$REPO/plugin/skills" "$SPACED/"
BIN="$TMP/bin"; mkdir -p "$BIN"; ln -s "$(command -v "$PY")" "$BIN/python3"
PATH="$BIN:$PATH" "$PY" - "$HOOKS/hooks.json" "$SPACED" "$PROJ" <<'PY' || fail "the hook config should run in exec form"
import json, os, subprocess, sys
config, root, proj = sys.argv[1:]
hooks = json.load(open(config))["hooks"]
tools = {t for entry in hooks["PreToolUse"] for t in (entry.get("matcher") or "").split("|")}
missing = {"Edit", "Write", "MultiEdit", "NotebookEdit", "Bash", "PowerShell", "Monitor"} - tools
assert not missing, f"PreToolUse does not match {sorted(missing)}"
# One session through every event, in the config's order: each hook's answer is known.
steps = {"SessionStart": ({"source": "startup"}, '"additionalContext"'),
         "UserPromptSubmit": ({"prompt": "add a feature"}, ""),
         "PreToolUse": ({"tool_name": "Edit", "tool_input": {"file_path": f"{proj}/src/a.ts", "old_string": "a",
                                                             "new_string": "b"}}, '"permissionDecision": "deny"'),
         "PostToolUse": ({"tool_name": "Skill", "tool_input": {"skill": "tdd"}, "tool_response": {}}, ""),
         "Stop": ({"stop_hook_active": False}, "")}
assert list(hooks) == list(steps), f"the config's events changed: {list(hooks)}"
put = lambda text: text.replace("${CLAUDE_PLUGIN_ROOT}", root)
for event, entries in hooks.items():
    for entry in entries:
        for hook in entry["hooks"]:
            assert isinstance(hook.get("args"), list), f"{event} is not in exec form: {hook}"
            fields, expected = steps[event]
            run = subprocess.run([put(hook["command"])] + [put(a) for a in hook["args"]], cwd=proj, timeout=60,
                                 input=json.dumps(dict(fields, session_id="exec", cwd=proj, hook_event_name=event)),
                                 capture_output=True, text=True, env=dict(os.environ, CLAUDE_PLUGIN_ROOT=root))
            assert run.returncode == 0, f"{event} exited {run.returncode}: {run.stderr}"
            assert (expected in run.stdout) if expected else not run.stdout, f"{event} answered: {run.stdout!r} {run.stderr}"
PY

echo "test_hooks ($($PY --version 2>&1)): OK"
