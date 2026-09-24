# 04: Progress file and resume note, end to end through the grill

**What to build:**
- **The grill's record:** a grill's decisions and open questions go into the feature's progress file as they land.
- **The resume note:** every session start gets a short resume note built from the repository's active progress files, plus a one-line notice for the user. That covers new, resumed, cleared, compacted and forked sessions, so a grill continues exactly where it stopped.
- **The grill's pace:** the grill asks every independent frontier question at once (up to four per AskUserQuestion call). Gate, security and destructive questions still come alone.

See ADR 0003.

**Blocked by:** 01 (Release 3.2.1)

**Status:** ready-for-agent

- [ ] The progress file's format is fixed:
  - header key-value lines: `Status`, `Stage`, `Next`, `Updated`, and optionally `Ticket` and `Candidate`;
  - then decisions, open questions, and the facts worth keeping;
  - it holds decisions and pointers only.
- [ ] The grill creates the file at its first decision and updates it after each answered round. Its presentation allows up to four independent questions per call.
- [ ] The session-start hook runs at `startup`, `resume`, `clear`, `compact` and `fork`. After the bootstrap it adds a resume note:
  - at most three `active` entries, newest `Updated` first;
  - each entry gives the feature, its stage, its next step and its path;
  - under 1,500 characters, framed as data from the repository's files;
  - plus a one-line `systemMessage`, "Seams: resuming <feature> (<stage>): <next>", when any entry exists.
- [ ] Must not happen:
  - a missing, unreadable or unparseable progress file blocks or breaks a session start. Such a file is skipped.
  - a `done` feature is listed;
  - a field appears other than as capped (200 characters), flattened, markup-free text, even when it is long or holds newlines, markup, or text that looks like instructions.
- [ ] Must not happen: the injection exceeds the bootstrap's cap plus the note's cap. The whole injection stays well under Claude Code's 10,000-character hook limit.
- [ ] The ledger rules hold: reset at `startup` and `clear`, kept at `compact` and `resume`. A fork starts with an empty ledger.
- [ ] A skill that reads the note re-reads the spec, the tickets and the git state before acting, and reports any mismatch.
- [ ] Hook-suite cases for each source pass: no files, one file, four files, a stale file, a planted file.
- [ ] `CONTEXT.md`'s Progress file and Resume note match what shipped.
- [ ] A new eval case: a fresh session over a fixture with a mid-grill progress file continues the grill. It asks the recorded open questions and doesn't restart.
- [ ] Headless compaction shows the same: `claude -p --resume <id> "/compact"`, then continue.

**How to verify:**
- `scripts/test.sh`.
- The new case: `python3 scripts/behavior_test.py run --scenario <case> --arm plugin --assert`, and `claude plugin eval plugin --case <case> --runs 1`. The eval run is paid, so ask first.
- The headless compaction run, recorded in the evidence doc.
