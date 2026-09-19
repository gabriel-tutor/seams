import { describe, expect, it } from "vitest";
import { formatLine } from "../src/format";

describe("formatLine", () => {
  it("renders qty, name, unit price and line total", () => {
    expect(formatLine({ sku: "A", name: "Apple", unitPriceCents: 150, qty: 2 })).toBe("2 x Apple @ 1.50 = 3.00");
  });
});
