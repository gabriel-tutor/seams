import { describe, expect, it } from "vitest";
import { addLine, createCart } from "../src/cart";
import { Inventory } from "../src/inventory";
import { checkout } from "../src/orders";

describe("checkout", () => {
  it("rejects an empty cart", async () => {
    const result = await checkout(createCart(), new Inventory());
    expect(result).toEqual({ ok: false, reason: "empty-cart" });
  });

  it("creates an order when stock is available", async () => {
    const inv = new Inventory();
    inv.setStock("A", 10);
    const cart = addLine(createCart(), { sku: "A", name: "Apple", unitPriceCents: 150, qty: 2 });
    const result = await checkout(cart, inv);
    expect(result.ok).toBe(true);
    if (result.ok) expect(result.order.totalCents).toBe(300);
    expect(inv.available("A")).toBe(8);
  });

  it("fails with the offending sku when stock is short", async () => {
    const inv = new Inventory();
    inv.setStock("A", 1);
    const cart = addLine(createCart(), { sku: "A", name: "Apple", unitPriceCents: 150, qty: 2 });
    expect(await checkout(cart, inv)).toEqual({ ok: false, reason: "out-of-stock", sku: "A" });
  });
});
