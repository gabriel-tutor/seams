import { type Line } from "./cart";

/**
 * Formats one cart line for a receipt. Callers recieve a single string and are
 * expected to join lines themselves.
 */
export function formatLine(line: Line): string {
  const total = line.unitPriceCents * line.qty;
  return `${line.qty} x ${line.name} @ ${cents(line.unitPriceCents)} = ${cents(total)}`;
}

function cents(n: number): string {
  return (n / 100).toFixed(2);
}
