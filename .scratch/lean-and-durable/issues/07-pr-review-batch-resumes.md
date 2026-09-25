# 07: A pr-review batch resumes

**What to build:**
- **Batch progress:** a `pr-review` batch keeps a progress file with its evidence, listing the pinned pull requests and each one's step.
- **Resume:** re-invoking `/pr-review` on the same pull requests continues the batch:
  - finished reviews at an unchanged head are reused;
  - unfinished ones restart from their last completed step;
  - a pull request whose head moved is reviewed afresh.
- **The note:** the resume note lists an unfinished batch from the same repository.

**Blocked by:** 04 (Progress file and resume note, end to end through the grill); 06 (pr-review under the cap, scripts without prompts)

**Status:** done

- [x] The batch progress file sits at the batch's evidence root, in the progress-file shape. It is updated as each pull request is checked, reviewed, drafted and posted.
- [x] Re-invoking with the same pull requests reuses finished ones at the same head and restarts unfinished ones from their last completed step.
- [x] Must not happen:
  - a pull request whose head moved reuses old evidence;
  - a batch from another repository, or a finished batch, appears in the resume note;
  - a review is posted twice (the existing duplicate check still runs).
- [x] The resume note lists an unfinished batch with its count and next step, within the note's caps.
- [x] Unit tests for choosing what to resume pass. Hook-suite cases for the batch entry pass.
- [x] A live headless run: a batch of three throwaway pull requests, interrupted after one and continued after `/clear`, reviews only the remaining two.

**How to verify:**
- `scripts/test.sh`.
- The live headless run on throwaway pull requests in this repository, with writes to GitHub blocked until the user answers. Record it in the evidence doc.

## Comments

Built 2026-09-26 on local `main`, not pushed. The commits:
- `8573c3b`, the build.
- `7186f58`, the review fixes. The live run used this candidate.
- `c069cf3`, a fix the live run found: the next step names the batch's pull requests by number and repository.
- The commit carrying this record.

**What shipped.**
- **`evidence.py`, a fifth script,** is pre-approved in `allowed-tools` and named in the core. At checkout, `evidence.py pin --pr <url> <head> <baseline> ...` pins every pull request in one call.
  - It names each `$EVID` the same way on every run, and writes its marker as JSON.
  - It says where the review starts:
    - **new** or **afresh**: every step runs;
    - **continue with its checks**: `checks/` is kept, and every other step runs, including Understand, Try it and Security;
    - **continue at Draft**: `review.json` is kept;
    - **reuse**: the draft is kept and goes to Post; a posted one has nothing left to post.
  - It removes everything else an earlier run left, so nothing but finished work at the same head and baseline stands in for the review. It makes the diff again before any step reads it.
  - It says which worktrees to keep, remove or make, judged by `run_checks.py`'s own rules, and never touches a worktree itself.
  - It refuses, with nothing pinned, a directory that isn't the review's own: no marker, a link, another user's, or another pull request's.
  - Only the user's own files count. The root, each `$EVID` and the batch file are the user's alone (0700 and 0600), whatever the umask.
  - `afresh` in the request (`--afresh`) reuses nothing.
- **The batch's progress file,** `progress-<repository>-<hash>.md`, sits at the evidence root. It is named after the session's repository and the batch's pull requests.
  - It has the progress-file shape. Stage counts the pull requests by step, Updated carries the time, and `Repository` and `Evidence` name the session's repository and the evidence directories. A Continue section holds the exact command.
  - `run_checks.py`, `review_payload.py` and `post_reviews.py` bring it up to date as their steps end.
  - `batch_report.py --close` closes it at the final handover, once every review in it is drafted or posted. The headless table before the post question leaves it open.
- **The resume note** lists the newest open batch of the session's repository among its three entries, in the spec's forms:
  - the entry: "- pr-review batch: stage 3 pull requests: 1 drafted, 2 pinned, updated …; next: The user types /pr-review again with pull requests 5, 6 and 7 of gabriel-tutor/seams to continue it: 2 of 3 unfinished. File: …";
  - the notice: "Seams: resuming pr-review batch (…): …".

  It reads only the user's own regular files, in a root that isn't a link and that other users can't write to. A file that doesn't parse, a NUL in its path included, drops out alone, and the features are listed all the same.
- **Text:**
  - `checkout.md`: pin first, remove what `evidence.py` names, record the user's state leaving out the review's own kept worktrees, then make what it asks for;
  - `batch.md`: the progress file, and questions and reviewers only for what still runs;
  - `checks.md`: continuing with its checks;
  - `draft-and-post.md`: a posted review isn't asked about again, and the headless table runs without `--close`;
  - `progress-file.md`: the batch variant;
  - `CONTEXT.md`: Progress file and Resume note;
  - ADR 0003: the exception;
  - README: the pr-review section.
- **Sizes:** `pr-review`'s core is 10,985 bytes, 15 under the bound.

**Evidence** (`docs/plugin-behavior-tests.md`, "3.3, ticket 07"):
- **The deterministic suites:** `scripts/test.sh` passes 9 of 9 with 0 skipped, on Python 3.14.6 and 3.9.6. The unit and hook suites also pass on 3.12.13, CI's version.
  - `EvidenceTest` has 25 tests of the resume choices through the scripts' command lines.
  - The hook suite's batch cases cover:
    - the entry and the notice, at every source;
    - another repository's batch, and a finished one;
    - the order among the three entries;
    - links, and an open root;
    - planted and malformed files;
    - what `evidence.py` writes;
    - the cap.
  - The tests came before the code they cover, slice by slice. A few passed at once, because earlier code already held. Four of those were mutation-checked, by breaking the code they guard, and each then failed:
    - the step's kept files;
    - the moved head;
    - the root's permissions;
    - the malformed batch file.
- **The live run,** on `7186f58`, at the user's yes. Closed PRs #5, #6 and #7 of this repository, from a fresh clone, with `gh` and `git` shims blocking every write.
  - Session 1 was killed once #5 was drafted. Session 2, fresh as `/clear` leaves one, typed the command the batch file gives. It started reviewers for #6 and #7 only; #5's draft files were byte-identical before and after.
  - 363 shim calls, none a write. The clone's status and worktree list were identical before and after.
  - Session 2 cost $2.72 over 596 s in one turn. Session 1's cost is not in its stream: it was killed before its result.

**Review of `8573c3b`.** Matt Pocock's `code-review` (Standards and Spec) and a correctness and security reviewer, as three subagents. Each finding was checked against the code.
- **Acted on in `7186f58`:**
  - **A kept tree read as off.** `git()` stripped the porcelain's first column, so a tracked file a check had changed made its tree "off". `evidence.py` now asks `run_checks.py` itself.
  - **A 0-byte `pr.diff` was kept.** A failed diff leaves one. The diff is now made again, from the repository, before any step reads it.
  - **A second batch erased the first,** since there was one batch file per repository. Each batch now has its own file, named after its pull requests.
  - **The batch closed too early.** Any report covering it closed it, including the headless table before the post question. Now only `--close` at the final handover closes it, and only when every review is drafted or posted.
  - **Resuming skipped unrecorded work.** "Continue at Review" skipped Understand, Try it and Security; now only the checks that ran are skipped.
  - **A NUL in a batch file cost the whole note.** Each file now drops out alone, and the features are always kept.
  - **Posted reviews and permissions:**
    - a posted review without `review.md` lost `posted.json`;
    - `$EVID` came out group-writable under umask 002, and its files were trusted by the folder's owner;
    - `import evidence` failed under `PYTHONSAFEPATH`.
  - **Format and records:**
    - Stage and the notice took the spec's forms, and the batch variant is documented;
    - the glossary and ADR 0003 name the exception;
    - the docstrings and the hook comment were corrected.
  - **Decision 27** (reuse for a single review) was flagged as scope. The user kept it and chose `afresh` as the way out.
  - Of the smells, the duplicated header check in the hook and the copied tree judgment were removed, and the batch functions renamed.
- **Not acted on,** per decision 12:
  - "Reviewed" shows when `review_payload.py` reads `review.json`, seconds after the same Draft step writes it; a separate call would add nothing.
  - The Bash sandbox case can't run on this Mac; the README states it.
  - The remaining smells, judgement calls:
    - several tables share one set of step keys;
    - `(path, status, repo, names)` travel together;
    - `evidence.py` does two jobs.

**Open.**
- **The fan-out's turn.** Both live sessions started the batch's reviewers in the foreground, all in one message, and session 2 stayed in one turn. The core says to keep subagents in the foreground; `batch.md` step 3 says "in the background" and "The fan-out ends this turn", which ticket 06 wrote and the static test holds. The run suggests a batch can keep its pre-approval through the handover. Aligning `batch.md` is a follow-up for the user to decide.
- **Whether the skill's grant covers a subagent's own script calls** is still unknown: the run's settings allowed the scripts.
- **Not exercised live:**
  - `/compact` (ticket 14's readiness);
  - a posted review reused;
  - `afresh`;
  - a head that moved;
  - an interactive session with AskUserQuestion;
  - the Bash sandbox.
- **Headroom:** `pr-review`'s core has 15 bytes left; a later ticket that adds to it moves text into a reference.
