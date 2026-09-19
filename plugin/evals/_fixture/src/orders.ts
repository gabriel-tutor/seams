import { type Cart } from "./cart";
import { Inventory } from "./inventory";
import { totalCents } from "./pricing";

export interface Order {
  id: string;
  totalCents: number;
  lines: Cart["lines"];
}

export type CheckoutResult =
  | { ok: true; order: Order }
  | { ok: false; reason: "empty-cart" | "out-of-stock"; sku?: string };

let nextId = 1;

export async function checkout(cart: Cart, inventory: Inventory): Promise<CheckoutResult> {
  if (cart.lines.length === 0) return { ok: false, reason: "empty-cart" };
  for (const line of cart.lines) {
    const reserved = await inventory.reserve(line.sku, line.qty);
    if (!reserved) return { ok: false, reason: "out-of-stock", sku: line.sku };
  }
  return {
    ok: true,
    order: { id: `ord_${nextId++}`, totalCents: totalCents(cart), lines: cart.lines },
  };
}
