# 01: The live card at every start

**What to build:** every session start, resume, clear and compaction opens with a card of all the repository's active work, so nothing is forgotten because it isn't among the newest three, and a stale record is flagged before anyone trusts it.

**Blocked by:** None (can start immediately).

**Status:** ready-for-agent

- [ ] The card lists every progress file whose Status is active, newest first, each with its feature, stage and next step; the current branch and commit head it.
- [ ] A file is flagged stale when its branch has commits newer than the file's last change, or the file hasn't changed in three days; each rule is tested on its own.
- [ ] The card reads only local sources (the files, git) and makes no network call.
- [ ] Past the injection budget the plugin's tests set, the remaining files are listed by name only; the card never exceeds the budget.
- [ ] Must not happen: a done or non-active file listed as active; a fact copied into the card (it holds pointers only); a day session without active work shown anything new.

**How to verify:** `scripts/test.sh` (the session-start tests drive the hook's output with active, stale and many files).
