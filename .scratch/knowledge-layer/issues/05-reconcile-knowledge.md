# 05: Reconcile's knowledge check, and the night's distill

**What to build:** Reconcile checks the knowledge too, and an unattended night distills right after it reconciles, so the morning summary lists the night's drafts and the questions for the owner.

**Blocked by:** 04 (`/seams:distill`).

**Status:** ready-for-agent

- [ ] Reconcile gains a fourth check: it runs the script's full report and sorts each finding as Confirmed, Corrected (an index row fixed, with the command that settled it) or Unsettled (a contradiction or a missing source, marked for the owner).
- [ ] The shared rules' Unattended mode runs `seams:distill` right after `seams:reconcile`, drafts only, and the morning summary lists the drafts and the owner questions.
- [ ] Must not happen: reconcile approving, deleting or rewriting an entry; the night approving anything.

**How to verify:** `scripts/test.sh` (text pins for reconcile's fourth check and the unattended order).
