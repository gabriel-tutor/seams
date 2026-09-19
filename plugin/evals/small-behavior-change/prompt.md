---
description: "a routing scenario: the expected skill first, nothing changed before it, no refusal"
tags: [routing]
allowed_tools: [Read, Glob, Grep, Skill]
max_turns: 15
timeout_seconds: 300
---

Add coupon support to OrderKit. `applyCoupon(cart, code)` in src/pricing.ts should return the new total in cents. SAVE10 takes 10% off. FLAT5 takes $5 off, but only when the subtotal is at least $20. Unknown codes should throw. Keep the existing tier discounts working.
