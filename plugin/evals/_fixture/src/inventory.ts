/**
 * In-memory stock ledger. `reserve` is async because production hits a database;
 * the simulated I/O gap models that round trip.
 */
export class Inventory {
  private stock = new Map<string, number>();

  setStock(sku: string, qty: number): void {
    this.stock.set(sku, qty);
  }

  available(sku: string): number {
    return this.stock.get(sku) ?? 0;
  }

  /** Holds `qty` units of `sku` for a checkout. Resolves false when stock is insufficient. */
  async reserve(sku: string, qty: number): Promise<boolean> {
    const current = this.available(sku);
    if (current < qty) return false;
    await simulateIo();
    this.stock.set(sku, current - qty);
    return true;
  }
}

function simulateIo(): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, 1));
}
