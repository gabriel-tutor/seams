# 07: Release Seams 5.4.0

**What to build:** the integrated candidate reaches Gabriel's Mac and the public marketplace, with the sleep-mode files installed in place.

**Blocked by:** 01, 02, 03, 04, 05, 06.

**Status:** ready-for-agent

- [ ] Readiness: the full suite green on the candidate, CI green on the staging pull request, the version and CHANGELOG set.
- [ ] main and the tag v5.4.0 at the CI-green commit, each on Gabriel's yes; his Mac reads the plugin at that commit.
- [ ] The guard and sleep-mode files are in place with backups beside each.
- [ ] Must not happen: a push of records naming a client's people, cards or pull requests (the repository is public).

**How to verify:** `claude plugin list` shows 5.4.0; the staging and main CI runs are green; a `sleepclaude --dry-run` shows the new launch.
