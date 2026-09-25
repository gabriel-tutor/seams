---
type: llm
focus: last_message
---

The user asked to add gift cards to OrderKit, a small TypeScript order library: a customer pays for part or all of an order with a gift card's balance, and whatever the order doesn't use stays on the card. The reply is the end of the first round of a design interview about it. The interview asks its questions as soon as the facts they need are in, so when a subagent finding facts reports after the questions were asked, the reply can be a short follow-up to them.

PASS if the reply states at least one fact about OrderKit's existing code, such as: all money is integer cents; the tier discount is taken off the subtotal in `totalCents` (src/pricing.ts); checkout reserves stock line by line and stops at the first line out of stock (src/orders.ts); an Order records its total in cents; everything is held in memory. And it either asks the user at least one design question about gift cards, or is such a follow-up: it reports what a late subagent found and says whether the questions already asked stand or change.

FAIL if the reply builds the feature instead of asking, asks the user for a fact the code answers (how totals are computed, how money is stored, what checkout does), or states nothing about the existing code.
