import { describe, expect, it } from "vitest";
import { Inventory } from "../src/inventory";

describe("inventory", () => {
  it("reserves when stock is sufficient", async () => {
    const inv = new Inventory();
    inv.setStock("A", 5);
    await expect(inv.reserve("A", 3)).resolves.toBe(true);
    expect(inv.available("A")).toBe(2);
  });

  it("refuses when stock is insufficient", async () => {
    const inv = new Inventory();
    inv.setStock("A", 2);
    await expect(inv.reserve("A", 3)).resolves.toBe(false);
    expect(inv.available("A")).toBe(2);
  });

  it("treats unknown skus as out of stock", async () => {
    const inv = new Inventory();
    await expect(inv.reserve("ZZZ", 1)).resolves.toBe(false);
  });
});
