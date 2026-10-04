#!/usr/bin/env bash
# A design the user confirmed, as /clear leaves it (ADR 0006). The gift-cards grill is done: its progress file,
# committed as the grill commits it, records every decision, the agreed seams, the user's confirmation of the
# shared understanding and where implement builds, with Stage: designed and Next naming the spec. Nothing else
# of the feature exists yet: no spec, no tickets. A fresh session is told about it only by the resume note.
set -euo pipefail
mkdir -p docs/agents .scratch/gift-cards
cat > docs/agents/issue-tracker.md <<'MD'
# Issue tracker: Local Markdown

Issues and specs live as markdown files in `.scratch/<feature>/`: the spec is `spec.md`, tickets are `issues/NN-slug.md`.
MD
cat > .scratch/gift-cards/progress.md <<'MD'
# Progress: gift cards

Status: active
Stage: designed
Next: Write the spec through seams:to-spec, then the tickets; the build goes in a new worktree.
Updated: 2026-09-28

## Decisions
1. A gift card is a code with a balance in integer cents; checkout redeems it against the order total.
2. Partial redemption is allowed: what the order doesn't use stays on the card.
3. Checkout holds the redeemed amount the way Inventory holds stock (a Reservation), and the Order records the gift card's code.
4. The gift card applies after the tier discount, to the total that totalCents returns; it never brings a total below zero.
5. When checkout fails out of stock after the hold, the held amount is released at once, in the same call.
6. An unknown code, or a card with no balance left, fails the checkout with its own reason, before any stock is reserved.
7. One gift card per order; a coupon, when coupons exist, applies before it.
8. The seams: checkout() for redemption, holds and releases, and the gift-card store's balance query; no test reaches into the store's internals.
9. Several sessions: a spec, then tickets, then implement per ticket.
10. The user confirmed the shared understanding on 2026-09-28 (the grill's last question): the flow goes on to the spec, and implement builds in a new worktree through seams:using-git-worktrees.

## Open questions
- None.

## Facts
- All money is integer cents (CONTEXT.md); the tier discount is applied in totalCents (src/pricing.ts).
- checkout reserves stock line by line and stops at the first out-of-stock line (src/orders.ts).
MD
git add docs/agents/issue-tracker.md .scratch/gift-cards/progress.md
git commit -qm "Gift cards: the design confirmed"
