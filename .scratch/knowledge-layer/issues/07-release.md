# 07: Release Seams 5.5.0

**What to build:** The integrated candidate reaches the public marketplace and Gabriel's Mac.

**Blocked by:** 01, 02, 03, 04, 05, 06 (all).

**Status:** ready-for-agent

- [ ] The readiness table is met: the candidate on main, the suite green on it, the version, badge and CHANGELOG at 5.5.0, `claude plugin validate --strict` passing, a secret scan and a client-detail scan of every commit to be pushed finding nothing.
- [ ] A staging pull request runs CI; main and the tag v5.5.0 at the CI-green commit, each on Gabriel's yes; his Mac reads the plugin at that commit.

**How to verify:** The staging pull request's CI, main's CI run on the tag's commit, and `claude plugin list`.
