---
type: llm
focus: { source: file, path: src/format.ts }
weight: 2
---

This is src/format.ts after the run. The user asked for `formatReceipt(cart: Cart): string`: each cart line exactly as `formatLine` prints it, one per line, then a last line `Total: $1,234.56`, the cart's subtotal in dollars with thousands separators and two decimals. The codebase already has `formatLine` in this file and `subtotalCents` in src/cart.ts, and JavaScript's standard library groups thousands (`Intl.NumberFormat`, `toLocaleString`).

PASS if `formatReceipt` exists and all of these hold: it builds the lines by calling the existing `formatLine`; it takes the total from `subtotalCents` or a single sum over the lines; it gets the thousands separators from the standard library rather than a hand-written grouping loop, regex or string slicing; and it adds no unrequested abstraction (no class, no options, currency or locale parameter, no new exported function besides `formatReceipt`).

FAIL if `formatReceipt` is missing, if it re-implements what `formatLine` or `subtotalCents` already do, if it groups the thousands by hand, or if it adds an unrequested abstraction.
