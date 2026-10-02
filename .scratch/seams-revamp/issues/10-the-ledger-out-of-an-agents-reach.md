# 10: The ledger out of an agent's reach

**What to build:** no tool call can write the gate's ledger: a write to the ledger's directory or a ledger file, by an editor tool or a shell command, is a change to the project (refused without a declaration, recorded with one), and a read-only agent's write there is refused like any other. Moving the ledger outside the temp and config directories is an equal fix. A damaged `declarations` field (not a list, or holding entries that are not objects) reads as empty.

**Blocked by:** 05 (Lighter hooks), which splits the gate module this changes.

**Status:** ready-for-agent

- [ ] With an empty ledger, an Edit or Write to `ledger_path(<session>)`, or a shell redirect into the ledger's directory, is refused for want of a declaration; with a declaration it is allowed and recorded as a change.
- [ ] A `reviewer` or `scout` writing there is refused, declared or not.
- [ ] A ledger whose `declarations` is not a list, or holds entries that are not objects, opens nothing.
- [ ] The hooks' own saves of the ledger still work (they write in process, not through a tool call); a 3.4.0 ledger and a ticket 04 ledger still read.
- [ ] Must not happen: a hook crash (the hooks fail open, so a crash would switch the gate off); a refusal of a write outside the ledger that was allowed before.

**How to verify:** in-process gate tests, red before the change: `decide_pre_tool_use` on a Write to `gate.ledger_path(sid)` with an empty ledger, a reviewer's `printf … > <ledger dir>/<sid>.json`, and a ledger with `"declarations": "all"`; then `scripts/test.sh` green.

## Comments

Found by the security review of ticket 04 (fc26a7a) on 2026-10-02, rated medium. The ledger sits under the system temp directory (`seams_gate.py`, `ledger_root()`), and the gate's temp and scratchpad rules let any tool call write there, read-only agents included; so an agent misled by a hostile pull request could forge a declaration that opens the main conversation's gate and erase the done-check's pending changes. The hole predates 4.0; ticket 04 widens it, since a forged route now lasts until `/clear` instead of until the next typed prompt. Ticket 04's builder left it with a reason (Claude Code's permissions are the real boundary; a path check is partial on a case-insensitive volume, lean-and-durable ticket 16). The user chose a new ticket that 4.0.0 waits for. Two lower findings of the same review ride along: a damaged `declarations` field now persists for the session (the third criterion), and the done-check's reason quotes a ledger path into Claude's context (`decide_stop`), which this fix makes unforgeable.
