# 02: No test sleeps, each behavior tested once

**What to build:** no test spends time waiting on nothing: a test that sleeps to let time pass uses a fake clock, and one that waits for another process waits on a condition with a bound. The gate's rules are tested once in process, and each hook event once through its command line; the other duplicates (two scenario-file checks, two longest-note guards, the twice-prepared fixture) are merged.

**Blocked by:** 01 (A suite that runs in under a minute).

**Status:** ready-for-agent

- [ ] No fixed sleep or fixed-length timeout remains where a fake clock or a bounded wait can stand in; the remaining real waits are listed with why.
- [ ] Every behavior the merged duplicates covered is still covered once.
- [ ] Must not happen: a test that passes only because a machine is fast, or one that fails only because it is slow.
- [ ] The suite's time drops by the sleeps removed, measured before and after.

**How to verify:** `scripts/test.sh` green twice in a row, its reported time lower than after ticket 01.
