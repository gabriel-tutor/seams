#!/usr/bin/env bash
# A ticket stopped halfway, as /clear leaves it. The coupons feature has its spec, two tickets and a
# progress file on main. Ticket 01 (SAVE10 and unknown codes) is done and recorded. Ticket 02 (FLAT5 and
# case-insensitive codes) is committed and reviewed, and the review found one thing to fix: FLAT5's
# minimum is checked against the tier-discounted total instead of the subtotal. Only the progress file
# records that finding; it is not committed yet, as implement leaves it after a commit. An older gift-cards
# grill is unfinished too, so the resume note lists two features and the newest is the one to continue.
set -euo pipefail
SHARED="$(cd "$(dirname "${BASH_SOURCE[0]}")/../_shared" && pwd)"
mkdir -p docs/agents .scratch/gift-cards .scratch/coupons/issues
cat > docs/agents/issue-tracker.md <<'MD'
# Issue tracker: Local Markdown

Issues and specs live as markdown files in `.scratch/<feature>/`: the spec is `spec.md`, tickets are `issues/NN-slug.md`.
MD
cat > .scratch/gift-cards/progress.md <<'MD'
# Progress: gift cards

Status: active
Stage: designing
Next: Ask the open question on the tier discount order, then check the design lens.
Updated: 2026-09-20

## Decisions
1. A gift card is a code with a balance in integer cents; checkout redeems it against the order total.

## Open questions
- Does the gift card apply before or after the tier discount?
MD
git add docs/agents/issue-tracker.md .scratch/gift-cards/progress.md
git commit -qm "Gift cards: the grill so far"

# The coupons spec and its tickets, as to-spec and to-tickets leave them.
cp "$SHARED/spec-coupons.md" .scratch/coupons/spec.md
cat > .scratch/coupons/issues/01-save10-and-unknown-codes.md <<'MD'
# 01: SAVE10 and unknown codes

**What to build:** `applyCoupon(cart, code)` in `src/pricing.ts`: `SAVE10` takes 10% off the post-tier total, rounded with `Math.round`, and an unknown code throws an error whose message contains `unknown coupon` (spec criteria 1, 4 and 6).

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

- [ ] `SAVE10` subtracts 10% of the post-tier total: 25 units at 100 cents give 2137.
- [ ] An unknown code throws an error whose message contains `unknown coupon`.

**How to verify:** `npm test`.
MD
cat > .scratch/coupons/issues/02-flat5-and-case-insensitive-codes.md <<'MD'
# 02: FLAT5 and case-insensitive codes

**What to build:** `FLAT5` takes 500 cents off the post-tier total when the cart's subtotal is at least 2000 cents, and throws an error whose message contains `not applicable` below it; codes are case-insensitive (spec criteria 2, 3 and 5).

**Blocked by:** 01 (SAVE10 and unknown codes)

**Status:** ready-for-agent

- [ ] `FLAT5` subtracts 500 cents only when the subtotal, before the tier discount, is at least 2000 cents.
- [ ] `FLAT5` below that throws an error whose message contains `not applicable`.
- [ ] `save10` behaves like `SAVE10`.

**How to verify:** `npm test`.
MD
progress() {   # $1 = Stage, $2 = Next, $3 = Updated, $4 = the ticket list, $5 = more header lines
  local extra=""; [[ -n "${5:-}" ]] && extra="$5"$'\n'
  cat > .scratch/coupons/progress.md <<MD
# Progress: coupon codes

Status: active
Stage: $1
Next: $2
Updated: $3
${extra}
## Spec
.scratch/coupons/spec.md

## Tickets
$4

## Decisions
1. A coupon applies after the tier discount, one coupon per cart (the spec).
MD
}
TICKETS=$'- 01 SAVE10 and unknown codes (blocked by: none)\n- 02 FLAT5 and case-insensitive codes (blocked by: 01)'
progress designed "Implement ticket 01 (SAVE10 and unknown codes) through matt-pocock-workflow:implement." 2026-09-23 "$TICKETS"
git add .scratch/coupons/spec.md .scratch/coupons/issues .scratch/coupons/progress.md
git commit -qm "Coupon codes: spec, tickets and progress file"

# Ticket 01, built and recorded.
cat >> src/pricing.ts <<'TS'

/** The total after the tier discount and then the coupon, in integer cents. */
export function applyCoupon(cart: Cart, code: string): number {
  const total = totalCents(cart);
  if (code === "SAVE10") return total - Math.round(total * 0.1);
  throw new Error(`unknown coupon: ${code}`);
}
TS
cat > tests/coupons.test.ts <<'TS'
import { describe, expect, it } from "vitest";
import { addLine, createCart } from "../src/cart";
import { applyCoupon } from "../src/pricing";

const cart = (units: number, unitPriceCents = 100) =>
  addLine(createCart(), { sku: "W", name: "Widget", unitPriceCents, qty: units });

describe("applyCoupon", () => {
  it("SAVE10 takes 10% off the post-tier total", () => {
    expect(applyCoupon(cart(25), "SAVE10")).toBe(2137);
  });

  it("rejects an unknown code", () => {
    expect(() => applyCoupon(cart(1), "NOPE")).toThrow(/unknown coupon/);
  });
});
TS
FIXED=$(git rev-parse --short HEAD)
progress designed "On main: review ticket 01's commit against the fixed point $FIXED." 2026-09-23 "$TICKETS" "Ticket: 01"
git add src/pricing.ts tests/coupons.test.ts .scratch/coupons/progress.md
git commit -qm "SAVE10 and unknown codes (ticket 01)"
progress integrated "Implement ticket 02 (FLAT5 and case-insensitive codes); /clear before it." 2026-09-23 \
  $'- 01 SAVE10 and unknown codes (blocked by: none) (done)\n- 02 FLAT5 and case-insensitive codes (blocked by: 01)'
git add .scratch/coupons/progress.md
git commit -qm "Ticket 01 record: integrated"

# Ticket 02, built and committed. The minimum is checked against the post-tier total, which the spec's
# criterion 2 rules out: the review's finding.
FIXED=$(git rev-parse --short HEAD)
perl -0pi -e 's/  if \(code === "SAVE10"\) return total - Math\.round\(total \* 0\.1\);\n  throw new Error\(`unknown coupon: \$\{code\}`\);/  switch (code.toUpperCase()) {\n    case "SAVE10":\n      return total - Math.round(total * 0.1);\n    case "FLAT5":\n      if (total < 2000) throw new Error("coupon FLAT5 not applicable below 2000 cents");\n      return total - 500;\n    default:\n      throw new Error(`unknown coupon: \$\{code\}`);\n  }/' src/pricing.ts
grep -q 'case "FLAT5"' src/pricing.ts || { echo "setup: the ticket 02 edit did not apply" >&2; exit 1; }
perl -0pi -e 's/\n\}\);\n\z/\n\n  it("FLAT5 takes 500 cents off from a 2000-cent subtotal", () => {\n    expect(applyCoupon(cart(25), "FLAT5")).toBe(1875);\n  });\n\n  it("FLAT5 is not applicable below a 2000-cent subtotal", () => {\n    expect(() => applyCoupon(cart(10), "FLAT5")).toThrow(\/not applicable\/);\n  });\n\n  it("reads codes case-insensitively", () => {\n    expect(applyCoupon(cart(25), "save10")).toBe(2137);\n  });\n});\n/' tests/coupons.test.ts
grep -q 'case-insensitively' tests/coupons.test.ts || { echo "setup: the ticket 02 tests did not apply" >&2; exit 1; }
LIST=$'- 01 SAVE10 and unknown codes (blocked by: none) (done)\n- 02 FLAT5 and case-insensitive codes (blocked by: 01)'
progress integrated "On main: review ticket 02's commit against the fixed point $FIXED." 2026-09-24 "$LIST" "Ticket: 02"
git add src/pricing.ts tests/coupons.test.ts .scratch/coupons/progress.md
git commit -qm "FLAT5 and case-insensitive codes (ticket 02)"

# After the review, as implement leaves the file: the candidate, the next step and the finding it acts
# on. Not committed yet; it goes in with the fix.
CANDIDATE=$(git rev-parse --short HEAD)
progress integrated "On main: fix the review finding under Review, test first; then commit the ticket's record and run the definition of done." \
  2026-09-24 "$LIST" "$(printf 'Ticket: 02\nCandidate: %s' "$CANDIDATE")"
cat >> .scratch/coupons/progress.md <<MD

## Review
- src/pricing.ts, applyCoupon: FLAT5's 2000-cent minimum is checked against the tier-discounted total instead of the subtotal, so 20 units at 102 cents (a 2040-cent subtotal, 1938 after the 5% tier) is refused where the spec gives 1438. Acting on it: a failing test first. Reviewed against the fixed point $FIXED.
MD
