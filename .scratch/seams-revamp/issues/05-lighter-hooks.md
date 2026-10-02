# 05: Lighter hooks

**What to build:** every tool call waits less on Seams: each hook event loads only the code it needs, with the ledger and path rules shared in one place. A firing takes about 20 ms instead of 37, measured the same way as before. Every hook still fails open.

**Blocked by:** 04 (A route lasts).

**Status:** ready-for-agent

- [ ] Each hook event has a command-line smoke test as Claude Code runs it (payload on stdin, the documented output shape).
- [ ] Measured median time per firing for the pre-tool, prompt and stop hooks, before and after, recorded in the commit; the target is about 20 ms.
- [ ] Must not happen: a hook crash that blocks the user's work; an event whose hook fails to load without a failing test.
- [ ] The repository-facts and resume-note output is unchanged (context management stays).

**How to verify:** `scripts/test.sh` green; the timing script from the grill's measurement run against 3.4.0's hooks and the new ones.
