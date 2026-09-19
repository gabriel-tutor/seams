#!/usr/bin/env bash
# The fixture's node_modules for the routing harness, kept outside the plugin (a directory-marketplace
# install copies the plugin's working tree, gitignored files included). Installs into
# tests/fixture-deps from the fixture's package files when missing or stale, and prints the path.
set -euo pipefail
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FIXTURE="$REPO/plugin/evals/_fixture"
DEPS="$REPO/tests/fixture-deps"
mkdir -p "$DEPS"
if [[ ! -d "$DEPS/node_modules" ]] || ! cmp -s "$FIXTURE/package-lock.json" "$DEPS/package-lock.json"; then
  cp "$FIXTURE/package.json" "$FIXTURE/package-lock.json" "$DEPS/"
  (cd "$DEPS" && npm ci --silent --no-audit --no-fund)
fi
echo "$DEPS/node_modules"
