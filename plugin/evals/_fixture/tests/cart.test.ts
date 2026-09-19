import { describe, expect, it } from "vitest";
import { addLine, createCart, subtotalCents } from "../src/cart";

describe("cart", () => {
  it("starts empty with a zero subtotal", () => {
    const cart = createCart();
    expect(cart.lines).toEqual([]);
    expect(subtotalCents(cart)).toBe(0);
  });

  it("adds lines immutably and sums the subtotal", () => {
    const cart = createCart();
    const withOne = addLine(cart, { sku: "A", name: "Apple", unitPriceCents: 150, qty: 2 });
    expect(cart.lines).toHaveLength(0);
    expect(withOne.lines).toHaveLength(1);
    expect(subtotalCents(withOne)).toBe(300);
  });

  it("merges quantities for a repeated sku", () => {
    let cart = createCart();
    cart = addLine(cart, { sku: "A", name: "Apple", unitPriceCents: 150, qty: 2 });
    cart = addLine(cart, { sku: "A", name: "Apple", unitPriceCents: 150, qty: 3 });
    expect(cart.lines).toEqual([{ sku: "A", name: "Apple", unitPriceCents: 150, qty: 5 }]);
  });

  it("rejects non-positive quantities", () => {
    expect(() => addLine(createCart(), { sku: "A", name: "Apple", unitPriceCents: 150, qty: 0 })).toThrow(/qty/);
  });
});
