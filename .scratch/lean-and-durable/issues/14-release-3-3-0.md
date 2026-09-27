# 14: Release 3.3.0

**What to build:** The integrated phase-1 candidate ships as 3.3.0 through `matt-pocock-workflow:release`: readiness proven by the spec's measures, the push on the user's yes, and the local install running it.

**Blocked by:** 01–13 (every other ticket)

**Status:** done

- [x] Readiness on the candidate. Each figure is recorded in the evidence doc and the README, and every paid run is asked first. (The paid rows, the evals and the resume cases below, were not run: the user deferred them to ticket 15, decision 46.)
  - CI is green on macOS and Ubuntu.
  - `scripts/test.sh` is green on both Pythons.
  - `claude plugin validate --strict` is green.
  - `claude plugin details` shows every skill at or under 4,000 tokens on invoke, and always-on cost at least 25% below 3.2.1's 1,165 tokens.
  - Every routing and gate eval case scores at or above its recorded score.
  - The new resume cases (grill, ticket, `pr-review` batch) pass after `/clear` and after `/compact`.
- [x] The version is bumped to 3.3.0 in `plugin.json` only, with the CHANGELOG entry dated.
- [x] Nothing is pushed without a yes naming the target, the branch and the candidate SHA.
- [x] After the push, `origin/main` is the candidate, and the local install runs 3.3.0 at the next session start or after `/reload-plugins`.
- [ ] The progress file is set to `done`. The operations handover names what to watch and the stage reached. (The handover is done. The file records `Stage: deployed` but stays `active`: tickets 15 and 16 are open, and the user asked for tickets to come back to, which only an active file keeps in the resume note.)

**How to verify:**
- The `release` skill's readiness table, with each row's command output.
- `git fetch`, then `git rev-parse origin/main`.
- A new session's resume note, and `claude plugin details`, showing 3.3.0.

## Comments

From ticket 08 (2026-09-25, decision 26): quote both always-on figures.
- **By `claude plugin details`:** 3.2.1 (`3a234bd`) was about 1,165 tokens; after ticket 08 it is about 825.
- **What Claude sees:** the listing without `pr-review`, whose description Claude Code keeps out of context (`disable-model-invocation`). It was 2,852 characters in 3.2.1 and is 2,307 after ticket 08, 19% less.
- **The part Seams owns** went from 2,058 to 1,513 characters, 26.5% less. The rest is the three byte-identical Superpowers copies.
- **Measure the candidate the same way, after ticket 09's agents:** `claude --plugin-dir plugin plugin details matt-pocock-workflow`, and the listing the way `scripts/tests/test_plugin.sh` counts it.

Released on 2026-09-27 as `4891cb0`: `main` fast-forwarded from `3a234bd`, 55 commits, no force push, on the user's yes. The plugin is `7c80291`'s; `4891cb0` adds documentation only. The commits the release made:
- `f8b912d`: the version, 3.3.0 in `plugin.json`, the badge and the CHANGELOG's dated heading.
- `ac16b39`: the gate fix the first staging run called for (below).
- `7c80291`: the review's fixes to it.
- `4891cb0`: the release evidence, the compatibility record, and tickets 15 and 16.

**Readiness, on the candidate** (the evidence doc's 3.3.0 section has every figure):
- `scripts/test.sh`: 9 of 9, none skipped, 236 unit tests per interpreter, on Python 3.14.6 with the system 3.9.6, and again on uv's 3.12.13 with `CI=true`. `claude plugin validate --strict` passed.
- `claude plugin details` on 2.1.283: always-on about 857 tokens (bar 873), the largest skill `implement` at about 3.8k (bar 4,000).
- The paid rows were not run: the user needed 3.3.0 in an urgent project and deferred them to ticket 15 (decision 46).
- Migration: a session's gate ledger crossing versions, both ways, 6 of 6 checks each. Rollback: one commit reverting `3a234bd..HEAD`, versioned 3.3.1, restores 3.2.1's tree exactly and passes 3.2.1's own suite, 9 of 9, in a scratch clone.
- What the push publishes, scanned: no credentials, client or organization names, or new emails. The progress file's docs-mirror path lost the home directory (history keeps the old line; the username is already public in the author email).

**Staging** (the throwaway PR #12, each push on its own yes):
1. 36291668848 on `f8b912d`: **red on Ubuntu**, in `test_hooks`. Diagnosed through `diagnosing-bugs` with a Linux container on this Mac: a config directory inside a temp root was scratch, so a read-only agent could write its settings and the main conversation's undeclared shell write there passed (since 3.2.1). The suite had passed on macOS only because `mktemp` puts it under `/var/folders`. Fixed in `ac16b39`, failing closed (decision 47).
2. The fix, sensitive, reviewed by Matt Pocock's `code-review` (Standards, Spec) and a security reviewer. `7c80291` acts on two findings (the refusal names the config directory; the fail-closed case tested). The case-variant bypass on a case-insensitive volume was verified and deferred by the user to ticket 16. The Standards review's two smells are style.
3. 36292620321 on `ac16b39`, green; 36293909837 on `4891cb0`, green: Ubuntu 6 passed, 2 skipped; macOS 9 passed, 1 skipped.

**Verified after the push:**
- `git fetch`: `origin/main` is `4891cb0`, and its `plugin.json` says 3.3.0. PR #12 shows as merged.
- CI on the push to `main`, 36294377210: green, Ubuntu 6 passed, 2 skipped; macOS 9 passed, 1 skipped.
- A fresh install from GitHub (`claude plugin marketplace add gabriel-tutor/seams` into a throwaway config): `claude plugin list` reports 3.3.0, the cached plugin equals `git archive 4891cb0 plugin/` byte for byte, and its gate refuses an undeclared `Write`.
- This machine: `claude plugin update` moved the install record from 3.2.1 to 3.3.0 (`gitCommitSha` `4891cb0`). A new headless session, its API calls pointed at a dead address so it cost nothing, loaded the plugin in place from the repository at 3.3.0, and its session-start note named lean-and-durable at stage release-ready (this record moves it to deployed).

Stage reached: deployed.
