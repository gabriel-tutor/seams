#!/usr/bin/env bash
# Scenario 6: a pre-existing type error makes `npm run typecheck` fail at baseline; tests still pass.
set -euo pipefail
cat > src/legacy.ts <<'EOF'
// Legacy price table kept from the v0 importer. Nobody has finished the migration.
export const LEGACY_PRICES_CENTS: Record<string, number> = {
  APPLE: 150,
  WIDGET: "100",
};
EOF
git add -A
git commit -qm "chore: keep legacy price table for the unfinished migration"
