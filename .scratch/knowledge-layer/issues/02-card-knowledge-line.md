# 02: The start card's knowledge line

**What to build:** Every session start, resume, clear and compaction in a configured repository shows one knowledge line on the card: how many raw sources are not distilled, changed since distilled, or cited by an entry but missing.

**Blocked by:** 01 (the knowledge config and the knowledge index).

**Status:** ready-for-agent

- [ ] The line comes from the script's quick report, within the card's existing cap and the injection's byte bound.
- [ ] Must not happen: the line shown with no config or with every count zero; the card hashing files; a slow or failing script delaying the start (the line is dropped instead).

**How to verify:** `scripts/test.sh` (the session-start hook's output with sample inboxes).
