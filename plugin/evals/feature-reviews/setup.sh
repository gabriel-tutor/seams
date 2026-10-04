#!/usr/bin/env bash
# A feature ticket at its review, as /clear leaves it once the review has started. The low-stock report has its spec,
# one ticket and a progress file on main; ticket 01 is built and committed, and the progress file names that commit as
# the candidate, not committed yet, as implement leaves it when the review starts. The fixed point is the commit
# before the build. Nothing here is sensitive, and the diff is small.
set -euo pipefail
mkdir -p docs/agents .scratch/low-stock/issues
cat > docs/agents/issue-tracker.md <<'MD'
# Issue tracker: Local Markdown

Issues and specs live as markdown files in `.scratch/<feature>/`: the spec is `spec.md`, tickets are `issues/NN-slug.md`.
MD
cat > .scratch/low-stock/spec.md <<'MD'
# Low-stock report

**Status:** ready-for-agent

## Problem Statement

The shop re-orders stock by hand, and learns that a SKU ran out only when a checkout fails.

## Solution

`Inventory.lowStock(threshold)` lists the SKUs whose available stock is at or below a threshold, so they can be restocked before checkouts fail.

## Acceptance criteria

1. `lowStock(threshold)` returns the SKUs whose available stock is at or below `threshold`, sorted by SKU.
2. A SKU whose stock was never set is not listed: it isn't stocked.
3. A negative or non-integer threshold throws a `RangeError`.

## Testing Decisions

- The seam is `Inventory`'s public methods, tested in `tests/inventory.test.ts`.
MD
cat > .scratch/low-stock/issues/01-low-stock-report.md <<'MD'
# 01: Low-stock report

**What to build:** `Inventory.lowStock(threshold)` in `src/inventory.ts` (spec criteria 1 to 3).

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

- [ ] The SKUs at or below the threshold, sorted by SKU: with A at 2, B at 9 and C at 0, `lowStock(2)` gives `["A", "C"]`.
- [ ] A SKU whose stock was never set is not listed.
- [ ] A negative or non-integer threshold throws a `RangeError`.

**How to verify:** `npm test`.
MD
progress() {   # $1 = Next, $2 = more header lines
  local extra=""; [[ -n "${2:-}" ]] && extra="$2"$'\n'
  cat > .scratch/low-stock/progress.md <<MD
# Progress: low-stock report

Status: active
Stage: designed
Next: $1
Updated: 2026-09-26
${extra}
## Spec
.scratch/low-stock/spec.md

## Tickets
- 01 Low-stock report (blocked by: none)

## Decisions
1. The report lists SKUs by their available stock, the same number reserve checks.
MD
}
progress "Implement ticket 01 (the low-stock report) through seams:implement."
git add docs/agents/issue-tracker.md .scratch/low-stock
git commit -qm "Low-stock report: spec, ticket and progress file"

# Ticket 01, built and committed.
FIXED=$(git rev-parse --short HEAD)
perl -0pi -e 's/(    return true;\n  \}\n)/$1\n  \/** The SKUs whose available stock is at or below `threshold`, sorted by SKU. *\/\n  lowStock(threshold: number): string[] {\n    if (!Number.isInteger(threshold) || threshold < 0) {\n      throw new RangeError(`threshold must be a non-negative integer: \${threshold}`);\n    }\n    return [...this.stock.entries()]\n      .filter(([, qty]) => qty <= threshold)\n      .map(([sku]) => sku)\n      .sort();\n  }\n/' src/inventory.ts
grep -q 'lowStock(threshold: number)' src/inventory.ts || { echo "setup: the build did not apply" >&2; exit 1; }
perl -0pi -e 's/\n\}\);\n\z/\n\n  it("lists the skus at or below the threshold, sorted", () => {\n    const inv = new Inventory();\n    inv.setStock("C", 0);\n    inv.setStock("B", 9);\n    inv.setStock("A", 2);\n    expect(inv.lowStock(2)).toEqual(["A", "C"]);\n  });\n\n  it("leaves out a sku whose stock was never set", () => {\n    const inv = new Inventory();\n    inv.setStock("A", 5);\n    expect(inv.lowStock(10)).toEqual(["A"]);\n  });\n\n  it("refuses a negative or fractional threshold", () => {\n    const inv = new Inventory();\n    expect(() => inv.lowStock(-1)).toThrow(RangeError);\n    expect(() => inv.lowStock(1.5)).toThrow(RangeError);\n  });\n});\n/' tests/inventory.test.ts
grep -q 'refuses a negative or fractional threshold' tests/inventory.test.ts || { echo "setup: the tests did not apply" >&2; exit 1; }
progress "On main: review ticket 01's commit against the fixed point $FIXED." "Ticket: 01"
git add src/inventory.ts tests/inventory.test.ts .scratch/low-stock/progress.md
git commit -qm "Low-stock report (ticket 01)"

# The review has started: the candidate is recorded, not committed yet.
CANDIDATE=$(git rev-parse --short HEAD)
progress "On main: review ticket 01's commit against the fixed point $FIXED." "$(printf 'Ticket: 01\nCandidate: %s' "$CANDIDATE")"
