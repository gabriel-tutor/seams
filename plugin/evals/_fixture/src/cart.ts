export interface Line {
  sku: string;
  name: string;
  unitPriceCents: number;
  qty: number;
}

export interface Cart {
  lines: Line[];
}

export function createCart(): Cart {
  return { lines: [] };
}

export function addLine(cart: Cart, line: Line): Cart {
  if (line.qty <= 0) throw new Error(`qty must be positive for ${line.sku}`);
  if (line.unitPriceCents < 0) throw new Error(`unitPriceCents must be >= 0 for ${line.sku}`);
  const existing = cart.lines.find((l) => l.sku === line.sku);
  if (existing) {
    return {
      lines: cart.lines.map((l) => (l.sku === line.sku ? { ...l, qty: l.qty + line.qty } : l)),
    };
  }
  return { lines: [...cart.lines, { ...line }] };
}

export function subtotalCents(cart: Cart): number {
  return cart.lines.reduce((sum, l) => sum + l.unitPriceCents * l.qty, 0);
}
