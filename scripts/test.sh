#!/usr/bin/env bash
# Run every test suite at once and report each one: scripts/test.sh [--help for the options].
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# No __pycache__ in the plugin: a marketplace added from a local directory loads the plugin folder in place.
export PYTHONDONTWRITEBYTECODE=1
exec python3 "$REPO/scripts/run_suites.py" "$@"
