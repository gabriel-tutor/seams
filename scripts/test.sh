#!/usr/bin/env bash
# Run every test suite this machine can run, and say which ones it skipped.
#   scripts/test.sh            # all suites
#   scripts/test.sh --fast     # skip the sandbox-workspace suite (needs node and the fixture's node_modules)
set -uo pipefail
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FAST=0; [[ "${1:-}" == "--fast" ]] && FAST=1
pass=(); failed=(); skipped=()
run()  { local name="$1"; shift; echo; echo "== $name"; if "$@"; then pass+=("$name"); else failed+=("$name"); fi; }
skip() { skipped+=("$1: $2"); echo; echo "== $1 (skipped: $2)"; }

run "python unit tests" python3 -m unittest discover -s "$REPO/scripts/tests" -p 'test_*.py'
run "test_plugin_hook"  bash "$REPO/scripts/tests/test_plugin_hook.sh"
run "test_hooks"        bash "$REPO/scripts/tests/test_hooks.sh"
run "test_install"      bash "$REPO/scripts/tests/test_install.sh"

# The hooks run under whichever python3 is first on PATH when Claude Code starts them; on macOS that
# can be the system 3.9. Prove the gate there too whenever that interpreter exists and differs.
SYS_PY=/usr/bin/python3
if [[ -x $SYS_PY && "$($SYS_PY -c 'import sys;print(sys.version_info[:2])')" != "$(python3 -c 'import sys;print(sys.version_info[:2])')" ]]; then
  run "python unit tests ($($SYS_PY --version 2>&1))" $SYS_PY -m unittest discover -s "$REPO/scripts/tests" -p 'test_*.py'
  run "test_hooks ($($SYS_PY --version 2>&1))" env PYTHON=$SYS_PY bash "$REPO/scripts/tests/test_hooks.sh"
  # session-start runs through its shebang, so the system interpreter has to come first on PATH
  run "test_plugin_hook ($($SYS_PY --version 2>&1))" env PATH="$(dirname $SYS_PY):$PATH" bash "$REPO/scripts/tests/test_plugin_hook.sh"
else skip "system-python suites" "no distinct /usr/bin/python3"; fi

if command -v claude >/dev/null; then run "test_plugin" bash "$REPO/scripts/tests/test_plugin.sh"
else skip "test_plugin" "needs the claude CLI for 'claude plugin validate'"; fi

if [[ $FAST == 1 ]]; then skip "test_prepare_run" "--fast"
elif ! command -v node >/dev/null; then skip "test_prepare_run" "needs node"
else
  "$REPO/scripts/fixture_deps.sh" >/dev/null
  run "test_prepare_run" bash "$REPO/scripts/tests/test_prepare_run.sh"
fi

echo; echo "passed: ${#pass[@]}  failed: ${#failed[@]}  skipped: ${#skipped[@]}"
for s in ${skipped[@]+"${skipped[@]}"}; do echo "  skipped  $s"; done   # the +-expansion keeps bash 3.2 happy with set -u
for f in ${failed[@]+"${failed[@]}"};   do echo "  FAILED   $f"; done
[[ ${#failed[@]} -eq 0 ]]
