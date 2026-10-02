# 09: Release 4.0.0

**What to build:** 4.0.0 reaches the marketplace repository `gabriel-tutor/seams` through `matt-pocock-workflow:release`: a throwaway staging pull request whose CI passes on macOS, Ubuntu and the Python 3.9 job, then `main` fast-forwarded on the user's yes, then verified.

**Blocked by:** 08 (Docs and proof), 10 (The ledger out of an agent's reach), 11 (A `..` after a symlink is not placed).

**Status:** ready-for-agent

- [ ] Every readiness row is ready, with ticket 08's proof as the evidence of quality.
- [ ] CI is green on the staging pull request for the exact candidate.
- [ ] `main` on origin equals the candidate after the user's yes; the local install updated and loading 4.0.0.
- [ ] Must not happen: `main` moved without the user's yes; a force push; a release with a readiness row unmet.
- [ ] Rollback is reinstalling 3.4.0, stated in the handover.

**How to verify:** `git rev-parse origin/main` equals the candidate; the CI runs on the staging pull request and on `main`; `claude plugin list` shows 4.0.0.
