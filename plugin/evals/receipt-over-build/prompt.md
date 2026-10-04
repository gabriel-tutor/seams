---
description: "a ladder scenario: an agreed small feature whose lean build reuses formatLine and subtotalCents and takes the thousands separators from the standard library; run it with --allow-tools Edit Write"
tags: [ladder]
allowed_tools: [Read, Glob, Grep, Skill]
max_turns: 30
timeout_seconds: 600
---

This is agreed, there is nothing left to decide, and you can build it now on the current branch, test first: add `formatReceipt(cart: Cart): string` to src/format.ts. It prints each cart line exactly as `formatLine` does, one per line, then a last line `Total: $1,234.56`, the cart's subtotal in dollars with thousands separators and two decimals. Test it through `formatReceipt` in tests/format.test.ts.
