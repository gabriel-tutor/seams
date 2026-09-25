# 05: Specs, tickets and builds keep the progress file

**What to build:** `to-spec`, `to-tickets`, `implement`, `finishing-a-development-branch` and `release` keep the feature's progress file current (stage, next step, ticket in progress, candidate, done), and commit it with the work it describes. A ticket then continues exactly where it stopped after `/clear` or compaction. See ADR 0003.

**Blocked by:** 04 (Progress file and resume note, end to end through the grill)

**Status:** done

- [x] **`to-spec`:** sets the stage to designed and points to the spec. After the publish yes, it commits by name the spec, the progress file, and the grill's glossary and ADR changes. Its question names that commit.
- [x] **`to-tickets`:** records the ticket list and the next unblocked ticket. After the approval, it commits the tickets and the progress file by name.
- [x] **`implement`:** records the ticket in progress, the candidate SHA and the stage reached, and commits the progress file with the ticket's commit. After the last ticket it sets `Status: done`, unless the spec has a Release section.
- [x] **`release`:** sets `done` at its operations handover.
- [x] **`finishing-a-development-branch`:** records integration.
- [x] Must not happen: a skill acts on the resume note without re-reading the spec, the tickets and the git state; or a mismatch between the note and the real state is acted on instead of reported.
- [x] Must not happen: a progress file gains a secret, a token or personal data. The skills write decisions and pointers only.
- [x] Every edited skill stays within the size bound.
- [x] A new eval case: a fresh session over a fixture with a mid-ticket progress file continues that ticket.
- [x] Headless compaction shows the same.

**How to verify:**
- `scripts/test.sh`.
- The new case through the routing harness and `claude plugin eval`. The eval run is paid, so ask first.
- A headless run: build part of a ticket in a fixture, start a fresh session (equivalent to `/clear`), and confirm the next session continues the same ticket.

## Comments

Built 2026-09-25 on local `main`, not pushed. The commits:
- `9d52d13`, the build.
- `9e14539`, the review fixes. The harness and the headless run used this candidate.
- `c56a84f`, the case's corrected expectation. The eval used this candidate; its skills and hooks are the same as `9e14539`'s.
- `efebcf4`, the fixes from the live runs.
- The commit carrying this record.

**What shipped.**
- **`to-spec`:** `Stage: designed`, the spec under `## Spec`, and the commit named in its publish question and then made by name.
- **`to-tickets`:** the ticket list under `## Tickets` and the first unblocked ticket. Its approval question names the commit.
- **`implement`:**
  - `Ticket` from the gate's yes, and `Next` naming the branch at every commit.
  - `Candidate`: the commit under review, since a commit can't name itself.
  - The findings to fix, under `## Review`.
  - A record commit before the definition of done: the stage reached, the next ticket, or `Status: done` after the last ticket unless the spec has a Release section. An unmet row puts the ticket back.
  - A ticket in progress resumes without the gate question when the file and git agree (decision 20). A mismatch is reported and asked about. A typed answer invokes `implement` again first.
- **`finishing-a-development-branch`,** now Seams' adaptation of its Superpowers copy (decision 19), records integration after a local merge. The notices record the original's checksum; the other three copies stay byte-identical.
- **`release`:** the stage reached at its operations handover, and `Status: done` once the last environment the spec's Release section names is verified. Its readiness row accepts the candidate as `finishing-a-development-branch` integrated and recorded it.
- **The resume note** names a ticket in progress (at most 60 characters) and says `implement` continues it (decision 21, made in the build, not the user's).
- **The case `resume-ticket`,** and the harness's `reads` list and `changes` expectation.

**Evidence** (`docs/plugin-behavior-tests.md`, "3.3, ticket 05"):
- **The deterministic suites:** `scripts/test.sh` passes 9 of 9 with 0 skipped, on Python 3.14.6 and 3.9.6. The unit and hook suites also pass on 3.12.13.
- **The routing harness:** 3 of 3 after `c56a84f`, re-judged from the same streams; the first judgement was 0 of 3, on a pattern that was wrong. Every run re-read the state, asked no gate question, and began with the failing test the recorded finding calls for.
- **The headless run:**
  - a fresh session fixed the finding and committed it;
  - `/compact` re-injected the note with the ticket;
  - a planted commit was reported as a mismatch, and nothing was acted on;
  - after the answer came the record commit, the definition of done and the handover.
- **`claude plugin eval`:** 0.86 with the plugin and 0.86 without, Δ 0. It ran without a shell, because this machine's Bash sandbox refuses to start, so the git-state grader could not pass. The baseline found the right progress file on its own.

**Review.** The two-axis review of `9d52d13` found six spec findings and two soft standards findings, plus smells. All were acted on in `9e14539` except the hook's feature dicts, which predate this ticket, and the test's inline JSON, a single use. The hook change was kept and recorded as decision 21.

**Open.**
- The wording `efebcf4` changed in `implement` has only the static test behind it; no paid run has been made on it.
- The eval with a shell, on a machine whose Bash sandbox starts.
- A case that shows the note is needed: Δ is 0 in both resume cases.
