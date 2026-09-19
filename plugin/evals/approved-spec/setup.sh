#!/usr/bin/env bash
# Scenario 5: the approved spec is committed; nothing is implemented.
set -euo pipefail
SHARED="$(cd "$(dirname "${BASH_SOURCE[0]}")/../_shared" && pwd)"
mkdir -p docs
cp "$SHARED/spec-coupons.md" docs/spec-coupons.md
git add -A
git commit -qm "docs: approved coupon spec"
