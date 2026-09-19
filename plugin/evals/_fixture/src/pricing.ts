import { type Cart, subtotalCents } from "./cart";

/** Volume tiers: total units in the cart → percentage off the subtotal. Highest matching tier wins. */
const TIERS: ReadonlyArray<{ minUnits: number; percent: number }> = [
  { minUnits: 50, percent: 10 },
  { minUnits: 20, percent: 5 },
];

export function totalUnits(cart: Cart): number {
  return cart.lines.reduce((n, l) => n + l.qty, 0);
}

export function tierDiscountPercent(cart: Cart): number {
  const units = totalUnits(cart);
  const tier = TIERS.find((t) => units >= t.minUnits);
  return tier ? tier.percent : 0;
}

/** Total after the tier discount, in integer cents. */
export function totalCents(cart: Cart): number {
  const subtotal = subtotalCents(cart);
  const discount = Math.round((subtotal * tierDiscountPercent(cart)) / 100);
  return subtotal - discount;
}
