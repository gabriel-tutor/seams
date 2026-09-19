# Spec: coupon codes — APPROVED 2026-09-10

## Interface

`applyCoupon(cart: Cart, code: string): number`, exported from `src/pricing.ts`. Returns the total in integer cents after the tier discount and then the coupon. `totalCents` is unchanged.

## Acceptance criteria

1. `SAVE10` subtracts 10% of the post-tier total, rounded with `Math.round`.
2. `FLAT5` subtracts 500 cents from the post-tier total, only when the cart **subtotal** (before the tier discount) is at least 2000 cents.
3. `FLAT5` on a cart whose subtotal is below 2000 cents throws an `Error` whose message contains `not applicable`.
4. An unknown code throws an `Error` whose message contains `unknown coupon`.
5. Codes are case-insensitive: `save10` behaves like `SAVE10`.
6. Coupons stack after the tier discount: 25 units at 100 cents → subtotal 2500 → tier 5% → 2375 → `SAVE10` → 2137.

## Test seam

Tests exercise `applyCoupon` through the public module interface with carts built via `createCart` / `addLine`. No internal helpers are tested directly.

## Out of scope

Multiple coupons per cart; persistence; UI.
