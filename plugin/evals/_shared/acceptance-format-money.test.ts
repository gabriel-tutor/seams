import { expect, it } from "vitest";
import { formatMoney } from "../src/format";

it("FM1 formats dollars and cents", () => {
  expect(formatMoney(1234)).toBe("$12.34");
});
it("FM2 pads cents", () => {
  expect(formatMoney(5)).toBe("$0.05");
});
it("FM3 formats zero", () => {
  expect(formatMoney(0)).toBe("$0.00");
});
