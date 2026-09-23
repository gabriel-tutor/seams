#!/usr/bin/env bash
# The docs audit: docs/skill-count.txt must match the skills the plugin ships. The pre-commit hook
# runs it; a count that code changes made stale is caught at pull-request time.
set -euo pipefail
cd "$(dirname "$0")/.."
documented=$(tr -d '[:space:]' < docs/skill-count.txt)
actual=$(find plugin/skills -mindepth 1 -maxdepth 1 -type d | wc -l | tr -d ' ')
if [ "$documented" != "$actual" ]; then
  echo "docs audit: docs/skill-count.txt says $documented, plugin/skills has $actual" >&2
  exit 1
fi
echo "docs audit: $actual skills"
