#!/usr/bin/env bash
# Scenario 4: a partial coupon implementation is committed (no >= 2000 threshold, no case folding),
# then an untracked file and an unstaged edit are left in the working tree.
set -euo pipefail
SHARED="$(cd "$(dirname "${BASH_SOURCE[0]}")/../_shared" && pwd)"
mkdir -p docs
cp "$SHARED/spec-coupons.md" docs/spec-coupons.md
cat >> src/pricing.ts <<'EOF'

/** Applies a coupon code to the post-tier total. */
export function applyCoupon(cart: Cart, code: string): number {
  const base = totalCents(cart);
  switch (code) {
    case "SAVE10":
      return base - Math.round(base * 0.1);
    case "FLAT5":
      return base - 500;
    default:
      throw new Error(`unknown coupon: ${code}`);
  }
}
EOF
cat > tests/coupons.test.ts <<'EOF'
import { describe, expect, it } from "vitest";
import { addLine, createCart } from "../src/cart";
import { applyCoupon } from "../src/pricing";

describe("applyCoupon", () => {
  it("SAVE10 takes 10% off", () => {
    const cart = addLine(createCart(), { sku: "W", name: "Widget", unitPriceCents: 1000, qty: 10 });
    expect(applyCoupon(cart, "SAVE10")).toBe(9000);
  });
});
EOF
git add -A
git commit -qm "feat: coupon codes (SAVE10, FLAT5)"
# Leave the tree dirty on purpose: one untracked file, one unstaged edit.
printf 'export const scratch = 1;\n' > src/scratch.ts
perl -pi -e 's/join lines themselves\./join lines themselves. TODO: tidy this comment./' src/format.ts
