# 07: A pr-review batch resumes

**What to build:**
- **Batch progress:** a `pr-review` batch keeps a progress file with its evidence, listing the pinned pull requests and each one's step.
- **Resume:** re-invoking `/pr-review` on the same pull requests continues the batch:
  - finished reviews at an unchanged head are reused;
  - unfinished ones restart from their last completed step;
  - a pull request whose head moved is reviewed afresh.
- **The note:** the resume note lists an unfinished batch from the same repository.

**Blocked by:** 04 (Progress file and resume note, end to end through the grill); 06 (pr-review under the cap, scripts without prompts)

**Status:** ready-for-agent

- [ ] The batch progress file sits at the batch's evidence root, in the progress-file shape. It is updated as each pull request is checked, reviewed, drafted and posted.
- [ ] Re-invoking with the same pull requests reuses finished ones at the same head and restarts unfinished ones from their last completed step.
- [ ] Must not happen:
  - a pull request whose head moved reuses old evidence;
  - a batch from another repository, or a finished batch, appears in the resume note;
  - a review is posted twice (the existing duplicate check still runs).
- [ ] The resume note lists an unfinished batch with its count and next step, within the note's caps.
- [ ] Unit tests for choosing what to resume pass. Hook-suite cases for the batch entry pass.
- [ ] A live headless run: a batch of three throwaway pull requests, interrupted after one and continued after `/clear`, reviews only the remaining two.

**How to verify:**
- `scripts/test.sh`.
- The live headless run on throwaway pull requests in this repository, with writes to GitHub blocked until the user answers. Record it in the evidence doc.
