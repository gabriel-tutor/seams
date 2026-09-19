import { describe, expect, it } from "vitest";
import { addLine, createCart } from "../src/cart";
import { tierDiscountPercent, totalCents, totalUnits } from "../src/pricing";

function cartWithUnits(units: number, unitPriceCents = 100) {
  return addLine(createCart(), { sku: "W", name: "Widget", unitPriceCents, qty: units });
}

describe("pricing tiers", () => {
  it("applies no discount under 20 units", () => {
    expect(tierDiscountPercent(cartWithUnits(19))).toBe(0);
    expect(totalCents(cartWithUnits(19))).toBe(1900);
  });

  it("applies 5% from 20 units", () => {
    expect(tierDiscountPercent(cartWithUnits(20))).toBe(5);
    expect(totalCents(cartWithUnits(20))).toBe(1900);
  });

  it("applies 10% from 50 units", () => {
    expect(tierDiscountPercent(cartWithUnits(50))).toBe(10);
    expect(totalCents(cartWithUnits(50))).toBe(4500);
  });

  it("counts units across lines", () => {
    let cart = cartWithUnits(10);
    cart = addLine(cart, { sku: "G", name: "Gadget", unitPriceCents: 250, qty: 10 });
    expect(totalUnits(cart)).toBe(20);
  });
});
