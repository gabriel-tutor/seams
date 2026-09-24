# 01: Release 3.2.1

**What to build:** The `pr-review` fixes from the first real batch reach users before phase 1 starts. They are 3.2.1: candidate `c740fd3` on `main`, 13 commits ahead of `origin/main`. `matt-pocock-workflow:release` runs on that candidate:
- readiness;
- the push, on the user's explicit yes naming the target and the candidate;
- verification that the target now serves exactly that candidate;
- an operations handover.

**Blocked by:** None (can start immediately)

**Status:** done

- [x] Readiness rows are met on the candidate:
  - CI is green on macOS and Ubuntu, and `scripts/test.sh` is green on both Pythons.
  - The CHANGELOG has the 3.2.1 entry, and both manifests say 3.2.1.
  - The README's evidence matches the candidate.
- [x] Nothing is pushed without a yes that names the target (`gabriel-tutor/seams`, branch `main`) and the candidate SHA.
- [x] Must not happen: phase-1 design files (the spec, tickets, progress file, ADR 0003, the new glossary terms) go out as part of 3.2.1 without the user saying so.
- [x] After the push, `origin/main` is the candidate, and the `plugin.json` it serves says 3.2.1.
- [x] The operations handover names what to watch and the stage reached.

**How to verify:** `git fetch`, then `git rev-parse origin/main` equals the candidate; CI's run for that SHA is green; `git show origin/main:plugin/.claude-plugin/plugin.json` shows 3.2.1.

## Comments

Readiness blocker found 2026-09-25, while verifying the spec and tickets. `scripts/test.sh --fast` fails 1 of 147 unit tests on both Pythons: `test_pr_review.RunChecksTest.test_checks_run_in_the_newest_bash_found_and_the_table_names_its_version` expects the newest bash to be the test's fake 5.2.37, but `run_checks.py` also searches the usual install places, and Homebrew bash 5.3.20 is now installed at `/opt/homebrew/bin/bash` (its Cellar folder is dated 2026-09-24 07:21). So the test depends on which bash the machine has. It passed when 3.2.1 was finished. The plugin's behaviour is unaffected. Fix the test (route: `diagnosing-bugs`, red-green) before the 3.2.1 readiness check; the fix becomes part of the 3.2.1 candidate.

Released on 2026-09-25 as `3a234bd`: 3.2.1 plus two test-only fixes, both found by this release.
- **`b8ed4b6`:** the newest-bash test lost to Homebrew bash 5.3.20 on this machine.
- **`3a234bd`:** the `CI=1` test inherited GitHub Actions' `CI=true`. The first CI run on PR #11 (at `b8ed4b6`) failed on both OSes, so `main` was not touched until it was fixed.

Readiness evidence, from a clean checkout of `3a234bd`:
- `scripts/test.sh` gave 9 passed, 0 failed, 0 skipped, both plain and with `CI=true`.
- `claude plugin validate plugin --strict` passed.
- A pattern scan of `aea109b..3a234bd` found no secrets and no client names.
- The plugin's Python uses the standard library only.
- `npm audit` on the eval fixture found 0 vulnerabilities.

Staged: PR #11 CI run 36051890146 passed at `3a234bd` (macOS 8/0/1, Ubuntu 5/0/2; the skipped suite is `test_plugin`, which needs the claude CLI).

Deployed on the user's yes: `main` was fast-forwarded from `aea109b` to `3a234bd` (15 commits, no force push), and PR #11 shows as merged.

Verified:
- `origin/main` is `3a234bd`, and both manifests say 3.2.1.
- CI on the push to `main` (run 36052922617) passed on macOS and Ubuntu.
- A fresh install from GitHub into a throwaway config folder reports 3.2.1, with 14 skills and 5 hook events, byte-identical to `plugin/` at `3a234bd` apart from Claude Code's `.in_use` marker.

Stage reached: deployed.

