# 04: The guard asks GitHub before a merge, and the two takeover modes

**What to build:** no overnight merge happens on the session's word: the guard checks the facts on GitHub itself, and the night's takeover mode decides whether a pull request awaiting its owner's acceptance may merge.

**Blocked by:** 03 (the same guard).

**Status:** ready-for-agent

- [ ] Before any merge the guard asks GitHub for the pull request's checks on its exact head, its merge state and its review decision; it allows the merge only when every check passed, the branch is up to date and conflict-free, and no review is asking for changes.
- [ ] The night's mode (`takeover -soft`, `takeover -hard`, or neither) is set where the session can't change it; awaiting acceptance blocks a merge unless the mode is hard.
- [ ] A lookup that fails, times out or returns something unreadable refuses the merge.
- [ ] Must not happen: a merge with a failed or pending check; a merge on a head other than the one checked; a soft-night merge of a pull request awaiting acceptance.

**How to verify:** the guard's suite with a stand-in `gh` answering each case.
