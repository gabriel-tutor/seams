# 04: A route lasts

**What to build:** once a process skill has routed the work, the user's typed replies and the flow's commits do not end the route: the next change goes through without the skill being invoked again. Invoking a different process skill replaces the route; `/clear` and a new session reset it. The gate still refuses work no skill routed, still holds read-only agents to reads, and the done-check still asks for verification once per turn.

**Blocked by:** 01 (A suite that runs in under a minute).

**Status:** ready-for-agent

- [ ] After a declaration, a typed prompt of any length and a commit leave the next project write allowed.
- [ ] Another process skill replaces the declaration; `/clear` and a new session start with none.
- [ ] The prompt hook no longer adds the lapse hint.
- [ ] A per-session ledger written by 3.4.0 is read, or treated as empty; it never causes a refusal.
- [ ] The manual-only declaration path is gone.
- [ ] Must not happen: a project write with no declaration since the session started or was cleared; a read-only agent writing; the done-check skipped for a turn that changed the project.
- [ ] The glossary's Declaration and Gate match the behavior (already updated by the grill); ADR 0005 is linked from the gate's docs.

**How to verify:** the in-process gate tests for the lifetime table; one command-line run of the prompt and pre-tool hooks with a 3.4.0 ledger fixture.
