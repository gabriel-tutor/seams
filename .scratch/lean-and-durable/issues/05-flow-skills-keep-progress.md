# 05: Specs, tickets and builds keep the progress file

**What to build:** `to-spec`, `to-tickets`, `implement`, `finishing-a-development-branch` and `release` keep the feature's progress file current (stage, next step, ticket in progress, candidate, done), and commit it with the work it describes. A ticket then continues exactly where it stopped after `/clear` or compaction. See ADR 0003.

**Blocked by:** 04 (Progress file and resume note, end to end through the grill)

**Status:** ready-for-agent

- [ ] **`to-spec`:** sets the stage to designed and points to the spec. After the publish yes, it commits by name the spec, the progress file, and the grill's glossary and ADR changes. Its question names that commit.
- [ ] **`to-tickets`:** records the ticket list and the next unblocked ticket. After the approval, it commits the tickets and the progress file by name.
- [ ] **`implement`:** records the ticket in progress, the candidate SHA and the stage reached, and commits the progress file with the ticket's commit. After the last ticket it sets `Status: done`, unless the spec has a Release section.
- [ ] **`release`:** sets `done` at its operations handover.
- [ ] **`finishing-a-development-branch`:** records integration.
- [ ] Must not happen: a skill acts on the resume note without re-reading the spec, the tickets and the git state; or a mismatch between the note and the real state is acted on instead of reported.
- [ ] Must not happen: a progress file gains a secret, a token or personal data. The skills write decisions and pointers only.
- [ ] Every edited skill stays within the size bound.
- [ ] A new eval case: a fresh session over a fixture with a mid-ticket progress file continues that ticket.
- [ ] Headless compaction shows the same.

**How to verify:**
- `scripts/test.sh`.
- The new case through the routing harness and `claude plugin eval`. The eval run is paid, so ask first.
- A headless run: build part of a ticket in a fixture, start a fresh session (equivalent to `/clear`), and confirm the next session continues the same ticket.
