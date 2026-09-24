#!/usr/bin/env bash
# A grill stopped halfway, as /clear leaves it: the repo is set up for Seams (its issue tracker is local
# markdown under .scratch/), and the gift-cards grill's progress file, not yet committed, records three
# settled decisions and two open questions. A fresh session is told about it only by the resume note.
set -euo pipefail
mkdir -p docs/agents
cat > docs/agents/issue-tracker.md <<'MD'
# Issue tracker: Local Markdown

Issues and specs live as markdown files in `.scratch/<feature>/`: the spec is `spec.md`, tickets are `issues/NN-slug.md`.
MD
git add -A
git commit -qm "docs: issue tracker config"

mkdir -p .scratch/gift-cards
cat > .scratch/gift-cards/progress.md <<'MD'
# Progress: gift cards

Status: active
Stage: designing
Next: Ask the two open questions (the tier discount order and the out-of-stock hold), then check the design lens.
Updated: 2026-09-20

## Decisions
1. A gift card is a code with a balance in integer cents; checkout redeems it against the order total.
2. Partial redemption is allowed: what the order doesn't use stays on the card.
3. Checkout holds the redeemed amount the way Inventory holds stock (a Reservation), and the Order records the gift card's code.

## Open questions
- Does the gift card apply before or after the tier discount?
- When checkout fails out of stock after the hold, is the held amount released at once or after a timeout?

## Facts
- All money is integer cents (CONTEXT.md); the tier discount is applied in totalCents (src/pricing.ts).
- checkout reserves stock line by line and stops at the first out-of-stock line (src/orders.ts).
MD
