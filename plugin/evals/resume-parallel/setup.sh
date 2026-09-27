#!/usr/bin/env bash
# A parallel run stopped halfway, as /clear leaves it (lean-and-durable ticket 12). The shop-basics feature has
# its spec and three tickets, none blocked, and the user picked all three, two building at once. Ticket 01 is
# integrated: its merge is on main, and its worktree and branch are gone. Ticket 02 is built: its builder
# committed it on its branch, in its worktree, and ended. Ticket 03 is pending, its worktree made at the
# run's base, waiting for a slot. The progress file, which the main conversation keeps current in the main
# checkout during a run and commits with the run's record, says all of this and is not committed.
set -euo pipefail
bash "$(cd "$(dirname "${BASH_SOURCE[0]}")/../_shared" && pwd)/shop-basics.sh"
ROOT="$(pwd)"

# The run's setup: the worktrees' directory ignored, the base noted, one worktree per ticket from it.
printf '.claude/worktrees/\n' >> .gitignore
git add .gitignore
git commit -qm "Ignore Claude Code's worktrees"
BASE=$(git rev-parse --short HEAD)
for stem in 01-format-cents 02-inventory-release 03-remove-line; do
  n=${stem%%-*}
  git worktree add -q -b "shop-basics/$stem" ".claude/worktrees/shop-basics-$n" "$BASE"
  ln -s "$ROOT/node_modules" ".claude/worktrees/shop-basics-$n/node_modules"
done

# Ticket 01, built by its builder and integrated: the merge made in its worktree, main fast-forwarded to it.
W1=.claude/worktrees/shop-basics-01
cat >> "$W1/src/format.ts" <<'TS'

/** Integer cents as a money string: two decimals, a minus sign before a negative amount. */
export function formatCents(cents: number): string {
  const sign = cents < 0 ? "-" : "";
  return `${sign}${(Math.abs(cents) / 100).toFixed(2)}`;
}
TS
cat > "$W1/tests/format-cents.test.ts" <<'TS'
import { describe, expect, it } from "vitest";
import { formatCents } from "../src/format";

describe("formatCents", () => {
  it("renders two decimals", () => {
    expect(formatCents(1234)).toBe("12.34");
  });

  it("puts a minus sign before a negative amount", () => {
    expect(formatCents(-5)).toBe("-0.05");
  });
});
TS
git -C "$W1" add src/format.ts tests/format-cents.test.ts
git -C "$W1" commit -qm "formatCents (ticket 01)"
git -C "$W1" checkout -q --detach main
git -C "$W1" merge -q --no-ff --no-edit -m "Integrate ticket 01: formatCents" shop-basics/01-format-cents
M1=$(git -C "$W1" rev-parse --short HEAD)
git merge -q --ff-only "$M1"
git worktree remove "$W1"
git branch -q -d shop-basics/01-format-cents

# Ticket 02, built: committed on its branch, its worktree clean.
W2=.claude/worktrees/shop-basics-02
perl -0pi -e 's/(\n  \/\*\* Holds `qty` units)/\n  \/** Returns `qty` held units of `sku` to stock, as when a checkout is cancelled. *\/\n  release(sku: string, qty: number): void {\n    if (!Number.isInteger(qty) || qty <= 0) throw new Error(`release needs a positive whole quantity: \${qty}`);\n    this.stock.set(sku, this.available(sku) + qty);\n  }\n$1/' "$W2/src/inventory.ts"
grep -q 'release(sku: string' "$W2/src/inventory.ts" || { echo "setup: the ticket 02 edit did not apply" >&2; exit 1; }
cat > "$W2/tests/inventory-release.test.ts" <<'TS'
import { describe, expect, it } from "vitest";
import { Inventory } from "../src/inventory";

describe("Inventory.release", () => {
  it("returns units to stock", () => {
    const inventory = new Inventory();
    inventory.setStock("A", 2);
    inventory.release("A", 3);
    expect(inventory.available("A")).toBe(5);
  });

  it("refuses a quantity that is not a positive whole number", () => {
    const inventory = new Inventory();
    expect(() => inventory.release("A", 0)).toThrow(/positive whole quantity/);
    expect(() => inventory.release("A", 1.5)).toThrow(/positive whole quantity/);
  });
});
TS
git -C "$W2" add src/inventory.ts tests/inventory-release.test.ts
git -C "$W2" commit -qm "Inventory.release (ticket 02)"
B2=$(git -C "$W2" rev-parse --short HEAD)

# The progress file as the run left it, current in the main checkout and not committed.
cat > .scratch/shop-basics/progress.md <<MD
# Progress: shop basics

Status: active
Stage: designed
Next: Parallel run on main: start the pending tickets as slots free up and integrate each built one; each ticket's state is under Parallel.
Updated: 2026-09-26
Ticket: 01, 02, 03

## Spec
.scratch/shop-basics/spec.md

## Tickets
- 01 formatCents (blocked by: none)
- 02 Inventory.release (blocked by: none)
- 03 removeLine (blocked by: none)

## Parallel
Base: main at $BASE, 2 at once
- 01: integrated at $M1
- 02: built at $B2, branch shop-basics/02-inventory-release, worktree .claude/worktrees/shop-basics-02
- 03: pending, branch shop-basics/03-remove-line, worktree .claude/worktrees/shop-basics-03

## Decisions
1. The three additions are independent: no ticket blocks another (the spec).
2. The user picked 01, 02 and 03 to build at once, two at a time.
MD
