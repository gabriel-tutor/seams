#!/usr/bin/env bash
# The shop-basics feature, as to-spec and to-tickets leave it, committed in the workspace (run from its root):
# a spec with three small additions to OrderKit in three different modules, three tickets none of which is
# blocked, and the progress file naming all three. Parallel-ticket scenarios start from here
# (lean-and-durable ticket 12): each ticket touches a module and a test file of its own, so their merges
# never conflict.
set -euo pipefail
mkdir -p docs/agents .scratch/shop-basics/issues
[[ -f docs/agents/issue-tracker.md ]] || cat > docs/agents/issue-tracker.md <<'MD'
# Issue tracker: Local Markdown

Issues and specs live as markdown files in `.scratch/<feature>/`: the spec is `spec.md`, tickets are `issues/NN-slug.md`.
MD
cat > .scratch/shop-basics/spec.md <<'MD'
# Spec: shop basics (approved 2026-09-24)

Three small additions to OrderKit, independent of each other.

## Acceptance criteria

1. `formatCents(cents: number): string`, exported from `src/format.ts`, renders integer cents with two decimals (`1234` gives `"12.34"`) and a minus sign before a negative amount (`-5` gives `"-0.05"`).
2. `Inventory.release(sku: string, qty: number): void`, in `src/inventory.ts`, returns `qty` units of `sku` to stock, as when a checkout is cancelled: `available(sku)` grows by `qty`. A `qty` that is not a positive whole number throws an `Error` whose message contains `positive whole quantity`.
3. `removeLine(cart: Cart, sku: string): Cart`, exported from `src/cart.ts`, returns a new Cart without that SKU's line and leaves the given cart unchanged; for a SKU the cart doesn't hold, it returns an equal cart.

## Testing decisions

Each function is tested through its module's public interface, in a test file of its own under `tests/`.

## Out of scope

Currency symbols and thousands separators; reservations that expire; removing part of a line.
MD
ticket() {   # $1 = file stem, $2 = title, $3 = what to build, $4 = criteria (markdown list)
  cat > ".scratch/shop-basics/issues/$1.md" <<MD
# ${1%%-*}: $2

**What to build:** $3

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

$4

**How to verify:** \`npm test\` and \`npm run typecheck\`.
MD
}
ticket 01-format-cents "formatCents" "\`formatCents(cents)\` in \`src/format.ts\` (spec criterion 1), tested in \`tests/format-cents.test.ts\`." \
  $'- [ ] `formatCents(1234)` is `"12.34"`.\n- [ ] `formatCents(-5)` is `"-0.05"`.'
ticket 02-inventory-release "Inventory.release" "\`Inventory.release(sku, qty)\` in \`src/inventory.ts\` (spec criterion 2), tested in \`tests/inventory-release.test.ts\`." \
  $'- [ ] After `setStock("A", 2)` and `release("A", 3)`, `available("A")` is 5.\n- [ ] `release("A", 0)` and `release("A", 1.5)` throw an error whose message contains `positive whole quantity`.'
ticket 03-remove-line "removeLine" "\`removeLine(cart, sku)\` in \`src/cart.ts\` (spec criterion 3), tested in \`tests/remove-line.test.ts\`." \
  $'- [ ] Removing a SKU the cart holds returns a cart without its line, and the given cart still has it.\n- [ ] Removing a SKU the cart doesn\'t hold returns a cart equal to the given one.'
cat > .scratch/shop-basics/progress.md <<'MD'
# Progress: shop basics

Status: active
Stage: designed
Next: Implement the unblocked tickets 01, 02 and 03 through seams:implement.
Updated: 2026-09-24

## Spec
.scratch/shop-basics/spec.md

## Tickets
- 01 formatCents (blocked by: none)
- 02 Inventory.release (blocked by: none)
- 03 removeLine (blocked by: none)

## Decisions
1. The three additions are independent: no ticket blocks another (the spec).
MD
git add docs/agents/issue-tracker.md .scratch/shop-basics
git commit -qm "Shop basics: spec, tickets and progress file"
