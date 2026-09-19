import { expect, it } from "vitest";
import { addLine, createCart } from "../src/cart";
import { applyCoupon } from "../src/pricing";

function cart(units: number, unitPriceCents: number) {
  return addLine(createCart(), { sku: "W", name: "Widget", unitPriceCents, qty: units });
}

it("AC1 SAVE10 subtracts 10% of the post-tier total", () => {
  expect(applyCoupon(cart(10, 1000), "SAVE10")).toBe(9000);
});
it("AC2 FLAT5 subtracts 500 when the subtotal is at least 2000", () => {
  expect(applyCoupon(cart(10, 200), "FLAT5")).toBe(1500);
});
it("AC3 FLAT5 below the threshold throws", () => {
  expect(() => applyCoupon(cart(1, 1999), "FLAT5")).toThrow();
});
it("AC3m FLAT5 below the threshold says not applicable", () => {
  expect(() => applyCoupon(cart(1, 1999), "FLAT5")).toThrow(/not applicable/i);
});
it("AC4 an unknown code throws", () => {
  expect(() => applyCoupon(cart(1, 1000), "BOGUS")).toThrow();
});
it("AC4m an unknown code says unknown coupon", () => {
  expect(() => applyCoupon(cart(1, 1000), "BOGUS")).toThrow(/unknown coupon/i);
});
it("AC5 codes are case-insensitive", () => {
  expect(applyCoupon(cart(10, 1000), "save10")).toBe(9000);
});
it("AC6 coupons stack after the tier discount", () => {
  expect(applyCoupon(cart(25, 100), "SAVE10")).toBe(2137);
});
