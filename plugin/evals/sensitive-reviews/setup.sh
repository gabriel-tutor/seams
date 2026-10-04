#!/usr/bin/env bash
# A sensitive ticket at its review, as /clear leaves it once the review has started. Manager-only price overrides are a
# permission check, so the change is sensitive, and the ticket says so. It has its spec, one ticket and a progress file
# on main; ticket 01 is built and committed, and the progress file names that commit as the candidate, not committed
# yet, as implement leaves it when the review starts. The fixed point is the commit before the build. There is no
# remote, so /security-review has no origin/HEAD to diff against, and the diff is small.
set -euo pipefail
mkdir -p docs/agents .scratch/price-overrides/issues
cat > docs/agents/issue-tracker.md <<'MD'
# Issue tracker: Local Markdown

Issues and specs live as markdown files in `.scratch/<feature>/`: the spec is `spec.md`, tickets are `issues/NN-slug.md`.
MD
cat > .scratch/price-overrides/spec.md <<'MD'
# Manager-only price overrides

**Status:** ready-for-agent

## Problem Statement

Staff sometimes change a line's price at the till (a damaged item, a price match), and today anyone can, by building a new cart line by hand.

## Solution

`overridePrice(cart, sku, unitPriceCents, actor)` in `src/cart.ts` returns a new cart with that line's unit price replaced, and only a manager may do it. This is a permission check, so the change is sensitive.

## Acceptance criteria

1. A manager (`actor.role === "manager"`) can set a line's unit price; the cart passed in is not changed.
2. Anyone else gets an error whose message contains `not permitted`, and the cart is unchanged.
3. An unknown SKU throws an error whose message contains `no line`.
4. A negative or non-integer price throws a `RangeError`.

## Testing Decisions

- The seam is `src/cart.ts`'s exported functions, tested in `tests/cart.test.ts`.
MD
cat > .scratch/price-overrides/issues/01-manager-only-price-overrides.md <<'MD'
# 01: Manager-only price overrides (sensitive: permissions)

**What to build:** `overridePrice(cart, sku, unitPriceCents, actor)` and the `Actor` type in `src/cart.ts` (spec criteria 1 to 4).

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

- [ ] A manager sets a line's unit price, in a new cart.
- [ ] A clerk gets an error whose message contains `not permitted`.
- [ ] An unknown SKU throws an error whose message contains `no line`.
- [ ] A negative or non-integer price throws a `RangeError`.

**How to verify:** `npm test`.
MD
progress() {   # $1 = Next, $2 = more header lines
  local extra=""; [[ -n "${2:-}" ]] && extra="$2"$'\n'
  cat > .scratch/price-overrides/progress.md <<MD
# Progress: manager-only price overrides

Status: active
Stage: designed
Next: $1
Updated: 2026-09-26
${extra}
## Spec
.scratch/price-overrides/spec.md

## Tickets
- 01 Manager-only price overrides, sensitive (blocked by: none)

## Decisions
1. Only a manager may override a price; the check is on the actor passed in (a permission check, so sensitive).
MD
}
progress "Implement ticket 01 (manager-only price overrides) through seams:implement."
git add docs/agents/issue-tracker.md .scratch/price-overrides
git commit -qm "Price overrides: spec, ticket and progress file"

# Ticket 01, built and committed.
FIXED=$(git rev-parse --short HEAD)
cat >> src/cart.ts <<'TS'

export interface Actor {
  id: string;
  role: "manager" | "clerk";
}

/** A new cart with `sku`'s unit price replaced. Only a manager may override a price. */
export function overridePrice(cart: Cart, sku: string, unitPriceCents: number, actor: Actor): Cart {
  if (actor.role !== "manager") throw new Error(`${actor.id} is not permitted to override prices`);
  if (!Number.isInteger(unitPriceCents) || unitPriceCents < 0) {
    throw new RangeError(`unitPriceCents must be a non-negative integer: ${unitPriceCents}`);
  }
  if (!cart.lines.some((l) => l.sku === sku)) throw new Error(`no line for ${sku}`);
  return { lines: cart.lines.map((l) => (l.sku === sku ? { ...l, unitPriceCents } : l)) };
}
TS
cat > tests/price-overrides.test.ts <<'TS'
import { describe, expect, it } from "vitest";
import { addLine, createCart, overridePrice } from "../src/cart";

const cart = addLine(createCart(), { sku: "W", name: "Widget", unitPriceCents: 500, qty: 2 });
const manager = { id: "m1", role: "manager" as const };
const clerk = { id: "c1", role: "clerk" as const };

describe("overridePrice", () => {
  it("lets a manager set a line's unit price in a new cart", () => {
    const next = overridePrice(cart, "W", 350, manager);
    expect(next.lines[0].unitPriceCents).toBe(350);
    expect(cart.lines[0].unitPriceCents).toBe(500);
  });

  it("refuses anyone who is not a manager", () => {
    expect(() => overridePrice(cart, "W", 350, clerk)).toThrow(/not permitted/);
  });

  it("refuses an unknown sku", () => {
    expect(() => overridePrice(cart, "NOPE", 350, manager)).toThrow(/no line/);
  });

  it("refuses a negative or fractional price", () => {
    expect(() => overridePrice(cart, "W", -1, manager)).toThrow(RangeError);
    expect(() => overridePrice(cart, "W", 1.5, manager)).toThrow(RangeError);
  });
});
TS
progress "On main: review ticket 01's commit against the fixed point $FIXED." "Ticket: 01"
git add src/cart.ts tests/price-overrides.test.ts .scratch/price-overrides/progress.md
git commit -qm "Manager-only price overrides (ticket 01)"

# The review has started: the candidate is recorded, not committed yet.
CANDIDATE=$(git rev-parse --short HEAD)
progress "On main: review ticket 01's commit against the fixed point $FIXED." "$(printf 'Ticket: 01\nCandidate: %s' "$CANDIDATE")"
