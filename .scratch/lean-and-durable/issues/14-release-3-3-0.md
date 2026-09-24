# 14: Release 3.3.0

**What to build:** The integrated phase-1 candidate ships as 3.3.0 through `matt-pocock-workflow:release`: readiness proven by the spec's measures, the push on the user's yes, and the local install running it.

**Blocked by:** 01–13 (every other ticket)

**Status:** ready-for-agent

- [ ] Readiness on the candidate. Each figure is recorded in the evidence doc and the README, and every paid run is asked first.
  - CI is green on macOS and Ubuntu.
  - `scripts/test.sh` is green on both Pythons.
  - `claude plugin validate --strict` is green.
  - `claude plugin details` shows every skill at or under 4,000 tokens on invoke, and always-on cost at least 25% below 3.2.1's 1,165 tokens.
  - Every routing and gate eval case scores at or above its recorded score.
  - The new resume cases (grill, ticket, `pr-review` batch) pass after `/clear` and after `/compact`.
- [ ] The version is bumped to 3.3.0 in `plugin.json` only, with the CHANGELOG entry dated.
- [ ] Nothing is pushed without a yes naming the target, the branch and the candidate SHA.
- [ ] After the push, `origin/main` is the candidate, and the local install runs 3.3.0 at the next session start or after `/reload-plugins`.
- [ ] The progress file is set to `done`. The operations handover names what to watch and the stage reached.

**How to verify:**
- The `release` skill's readiness table, with each row's command output.
- `git fetch`, then `git rev-parse origin/main`.
- A new session's resume note, and `claude plugin details`, showing 3.3.0.
