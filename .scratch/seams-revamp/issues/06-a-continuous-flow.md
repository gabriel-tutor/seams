# 06: A continuous flow

**What to build:** once the user confirms a design, the flow runs on through spec, tickets, build, review and release without asking before each step. It stops for the user's decisions, before integrating a branch (merge, pull request, keep or discard is still asked), before pushes, deploys and publishes, before anything destructive, and before paid runs. The bootstrap states the flow in place of "each step asks before it starts", and the flow skills drop the opening questions the chain no longer needs.

**Blocked by:** 03 (Wording pins shrink to the contracts), 04 (A route lasts).

**Status:** ready-for-agent

- [ ] The bootstrap's routing rules state the continuous flow and the real gates; it stays inside its size bound.
- [ ] to-spec, to-tickets and implement start without an opening question when the flow reached them from a confirmed design; asked directly by the user, they still start at once.
- [ ] The questions before publishing, integrating a branch, pushing, deploying, destroying and paying stay in every skill that has them.
- [ ] Must not happen: a push, deploy, publish, branch integration, destructive action or paid run without the user's yes.
- [ ] Progress files still note every step the flow takes (context management stays).

**How to verify:** `scripts/test.sh` green; the routing eval scenarios still pass with `claude plugin eval` (run once, asked first, as part of ticket 08's proof or alone if the user wants it earlier).
