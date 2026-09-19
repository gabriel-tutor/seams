#!/usr/bin/env bash
# Prepare one routing-test run workspace.
#   scripts/prepare_run.sh <scenario> <run-dir>
# Produces <run-dir>/workspace (the scenario's scaffold applied: a fresh fixture copy at a git baseline
# with setup.sh run, node_modules a symlink to the shared install), <run-dir>/baseline.txt (HEAD after
# setup), <run-dir>/outputs/.
set -euo pipefail
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCENARIO="${1:?usage: prepare_run.sh <scenario> <run-dir>}"
RUN_DIR="$(mkdir -p "${2:?usage: prepare_run.sh <scenario> <run-dir>}" && cd "$2" && pwd)"
CASE="$REPO/plugin/evals/$SCENARIO"
[[ -f "$CASE/setup.sh" ]] || { echo "no such scenario: $SCENARIO" >&2; exit 1; }
NODE_MODULES="$("$REPO/scripts/fixture_deps.sh")"

WS="$RUN_DIR/workspace"
rm -rf "$WS"
mkdir -p "$WS" "$RUN_DIR/outputs"
(cd "$WS" && SEAMS_FIXTURE_NODE_MODULES="$NODE_MODULES" bash "$REPO/plugin/evals/_scaffold.sh" "$CASE" && git rev-parse HEAD > "$RUN_DIR/baseline.txt")
echo "prepared $SCENARIO in $WS (baseline $(cat "$RUN_DIR/baseline.txt"))"
