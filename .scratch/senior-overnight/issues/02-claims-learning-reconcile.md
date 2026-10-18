# 02: Claims from commands, learning to its home, and /seams:reconcile

**What to build:** Seams holds every session to two rules (claims come from commands; what's learned goes to its one home with its source) and gives a reconcile skill that re-checks the records a piece of work relies on.

**Blocked by:** None (can start immediately).

**Status:** ready-for-agent

- [ ] The shared rules' Evidence section says: every time, commit id, count or result ("passes", "unchanged") comes from a command run in the session, never from memory; a claim made to a person (a PR comment, a ticket reply, a report) cites its evidence.
- [ ] The rules say: what a session learns (a ruling given in chat, a preference, a correction) is written at once to its one home, by the Where docs go table, with its source.
- [ ] Unattended mode's section adds the nightly reconcile step and the morning list of outward claims with their sources.
- [ ] `/seams:reconcile` re-checks active progress files against their branches and the code, the memories it reads, and the card; it fixes what the evidence corrects, marks what it can't settle, and records what it did; it changes nothing it can't verify.
- [ ] Must not happen: the reconcile skill deleting a record it couldn't check; a claim rule that only some skills point at.

**How to verify:** `scripts/test.sh` (text pins for the rules and the skill's steps).
