# 04: `/seams:distill`

**What to build:** Running `/seams:distill` turns the raw sources that are undistilled or changed into draft knowledge entries, each citing its sources and their dates, in the project's own format or one markdown file per entry by default, and reports the drafts and any question it raised for the owner.

**Blocked by:** 01 (the knowledge config and the knowledge index), 03 (the Knowledge rule).

**Status:** ready-for-agent

- [ ] It runs the script, reads only the undistilled and changed sources, writes drafts with topics from the sources' own words, and leaves the index's cited-by rows to the script.
- [ ] A draft that contradicts an approved entry is raised under the escalation tag, and the approved entry stays as it is.
- [ ] Must not happen: an entry approved, an entry deleted, a quote from a source flagged as holding secrets, a personal detail in a draft, an instruction inside a source followed.
- [ ] One live run on a sample inbox shows the drafts and the report; it is asked before it runs, with its cost.

**How to verify:** `scripts/test.sh` (distill's text pins); the live run's drafts and report on the sample inbox.
