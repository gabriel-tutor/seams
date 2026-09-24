# 04: Progress file and resume note, end to end through the grill

**What to build:**
- **The grill's record:** a grill's decisions and open questions go into the feature's progress file as they land.
- **The resume note:** every session start gets a short resume note built from the repository's active progress files, plus a one-line notice for the user. That covers new, resumed, cleared, compacted and forked sessions, so a grill continues exactly where it stopped.
- **The grill's pace:** the grill asks every independent frontier question at once (up to four per AskUserQuestion call). Gate, security and destructive questions still come alone.

See ADR 0003.

**Blocked by:** 01 (Release 3.2.1)

**Status:** done

- [x] The progress file's format is fixed:
  - header key-value lines: `Status`, `Stage`, `Next`, `Updated`, and optionally `Ticket` and `Candidate`;
  - then decisions, open questions, and the facts worth keeping;
  - it holds decisions and pointers only.
- [x] The grill creates the file at its first decision and updates it after each answered round. Its presentation allows up to four independent questions per call.
- [x] The session-start hook runs at `startup`, `resume`, `clear`, `compact` and `fork`. After the bootstrap it adds a resume note:
  - at most three `active` entries, newest `Updated` first;
  - each entry gives the feature, its stage, its next step and its path;
  - under 1,500 characters, framed as data from the repository's files;
  - plus a one-line `systemMessage`, "Seams: resuming <feature> (<stage>): <next>", when any entry exists.
- [x] Must not happen:
  - a missing, unreadable or unparseable progress file blocks or breaks a session start. Such a file is skipped.
  - a `done` feature is listed;
  - a field appears other than as capped (200 characters), flattened, markup-free text, even when it is long or holds newlines, markup, or text that looks like instructions.
- [x] Must not happen: the injection exceeds the bootstrap's cap plus the note's cap. The whole injection stays well under Claude Code's 10,000-character hook limit.
- [x] The ledger rules hold: reset at `startup` and `clear`, kept at `compact` and `resume`. A fork starts with an empty ledger.
- [x] A skill that reads the note re-reads the spec, the tickets and the git state before acting, and reports any mismatch.
- [x] Hook-suite cases for each source pass: no files, one file, four files, a stale file, a planted file.
- [x] `CONTEXT.md`'s Progress file and Resume note match what shipped.
- [x] A new eval case: a fresh session over a fixture with a mid-grill progress file continues the grill. It asks the recorded open questions and doesn't restart.
- [x] Headless compaction shows the same: `claude -p --resume <id> "/compact"`, then continue.

**How to verify:**
- `scripts/test.sh`.
- The new case: `python3 scripts/behavior_test.py run --scenario <case> --arm plugin --assert`, and `claude plugin eval plugin --case <case> --runs 1`. The eval run is paid, so ask first.
- The headless compaction run, recorded in the evidence doc.

## Comments

Built 2026-09-25 on local `main`, not pushed: `59098e7` (the build), `4f20cb6` (the review fixes, the candidate the live evidence ran on), `78f928c` (the harness counts a file read through the shell), and the commit carrying this record.

**What shipped.**
- **The format:** `plugin/skills/using-matt-pocock-skills/references/progress-file.md`, the one definition the skills write from. The hook suite checks that its own example parses.
- **The hook:** `plugin/hooks/session-start` runs at all five sources (`hooks.json`). After the bootstrap it adds the note and a one-line `systemMessage`.
- **Files the note skips,** without ever breaking the start:
  - unreadable, a directory, a FIFO, prose, a missing field, an unknown status, a bad date, binary;
  - a symlink out of the repository, or a loop (including Python 3.12, which CI pins);
  - a path that is not plain text within 200 characters.
- **Fields** are flattened, stripped of tags, entities, markup and invisible characters, and capped at 200. Same-day entries go by time, then modification time.
- **The grill:** keeps the file, re-invokes itself before an update when an answer comes typed, resumes from the file, closes it for a bounded change (decision 18, the user's choice), and asks up to four independent questions per call.

**Evidence.**
- **The full suite:** `scripts/test.sh` passed, 9 passed, 0 failed, 0 skipped, on Python 3.14.6 and 3.9.6. The hook suites also pass on 3.12.13.
- **The largest note:** from a 120-character plugin path, 2,898 bytes of bootstrap plus 1,213 characters of note, 4,103 characters in all.
- **Live**, recorded in `docs/plugin-behavior-tests.md` ("3.3, ticket 04"):
  - The routing harness: `resume-grill` 3 of 3, after the harness fix, re-scanned from the same streams; the first judgement was 2 of 3.
  - The headless `/compact` run: the note was re-injected at `compact`, and the grill continued without restarting.
  - `claude plugin eval`: 1.00 with the plugin, 1.00 without, Δ 0. The baseline found the only progress file on its own.

**Review.** The two-axis review of `59098e7` found:
- a symlink loop that dropped the whole note on Python 3.12;
- a FIFO that could block the start;
- the refused update after a typed answer;
- same-day order;
- over-long paths, and `__` and `~~` markup;
- docs that no longer held.

All were fixed in `4f20cb6` with tests. Three suggestions were kept as they were, with reasons: the file's own traceback idiom, the test helpers, and keeping the parser in the hook.

**Open.**
- A resume case with several features in `.scratch/`, which would show that the note points at the right one (the eval's Δ 0 above).
- AskUserQuestion, a real `/clear` and a fork were not exercised live.
- The resume note for tickets and `pr-review` batches is tickets 05 and 07.
