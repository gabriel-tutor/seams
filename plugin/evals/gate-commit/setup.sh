#!/usr/bin/env bash
# Gate scenario: a commit. The typo fix sits in the working tree, unstaged and uncommitted.
set -euo pipefail
perl -pi -e 's/recieve/receive/' src/format.ts
