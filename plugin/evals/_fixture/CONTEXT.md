# OrderKit domain context

- **Cart** — an unsaved collection of Lines. Immutable: `addLine` returns a new Cart.
- **Line** — one SKU in a Cart with a quantity and the unit price captured when it was added.
- **Subtotal** — sum of unit price × quantity across Lines, before any discount.
- **Tier discount** — a percentage off the subtotal based on total units in the Cart: 20+ units → 5%, 50+ units → 10%.
- **Coupon** — a code the customer enters that changes the total. Not implemented yet.
- **Reservation** — a promise from Inventory that stock is held for a checkout. Over-selling (more reservations than stock) is a defect.
- **Order** — the result of a successful checkout: an id, the total in cents, and the lines.

All money is integer cents. Rounding uses `Math.round`.
