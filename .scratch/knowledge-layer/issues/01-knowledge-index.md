# 01: The knowledge config and the knowledge index

**What to build:** A repository that opts in with a knowledge config gets a tracked knowledge index of every raw source in its inbox and its configured source homes, kept current by a script, which reports what is undistilled, changed, missing or not on this machine. A repository without a config is untouched.

**Blocked by:** None (can start immediately).

**Status:** ready-for-agent

- [ ] A config names the inbox, the index, the approved home and how an approved entry is recognised, the entry format, the owner's escalation tag, and the other source homes.
- [ ] The script builds and updates the index: one sorted row per source, holding its id, date, topics (kept as distill wrote them), a holds-secrets flag and the entries that cite it (read from the entries); each source's path, old paths, size, modified time and hashes stay in a gitignored file inside the inbox (decision 18), which is refused unless git ignores the inbox.
- [ ] Its quick report reads the index, the entries and each file's size and modified time, never hashing; its full report hashes a source only when its size or time moved. Both give the counts: sources new to the index, not distilled, changed since distilled, entries citing a missing source, sources not on this machine.
- [ ] A source matching a credential pattern is flagged, and no matched value, phone number, address or personal detail appears in the index or any output.
- [ ] Must not happen: a run with no config writing anything; a malformed config crashing (it is reported in one line); a source missing on this machine counted as changed or stale; a network call.

**How to verify:** `scripts/test.sh` (the script's command-line tests on sample inboxes), then the script's quick report on a sample repository.
