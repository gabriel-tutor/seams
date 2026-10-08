# Progress: pr-review faster, the same quality

Status: active
Stage: built
Next: Built on seams-5.2/pr-review-speed (from 0d2a84f; reviewed, findings fixed at b2c3068). Next: seams:finishing-a-development-branch to integrate into main (the user's yes), then seams:release for 5.2.0 (version bump, CHANGELOG, staging PR for CI, main and tag v5.2.0 on the user's yes).
Updated: 2026-10-09

## Decisions

1. The bar (the user's words, 2026-10-09): "preserve the senior like quality review, i want to optimize only the speed without affecting the quality output". Every check still runs locally on the pull request's tree, findings are still proven, flaky checks still re-run; nothing is skipped or trusted from elsewhere for speed. The user's standing rule holds: don't ruin pr-review.
2. Posting (the user's choice): each review posts as soon as its pull request is fully verified, paced under GitHub's rate limit; only reviews that need the user's yes, or a recheck of a flaky check on a quiet machine, wait for the end of the batch.
3. Baseline (the user's choice): one baseline per distinct base commit in a batch, shared by every pull request on that commit, failures included (the same commit gives the same result); today it re-runs per pull request and shares only passing runs.

4. Takeover (the user's choice): several pull requests are taken over at once, each fixed by its own builder in its own worktree, every check still re-run after the fix; the user approves the list of pushes once, at the end.
5. Installs (the user's choice): the first install for a lockfile is kept and cloned (APFS copy-on-write) into every other tree with the identical lockfile; a pull request that changes the lockfile installs fresh.
6. Load (the user's choice): as many pull-request agents run at once as there are check slots (half the cores), the next starting as one finishes, instead of up to 20.
7. Mine, the user may overrule them: posting's rate pacing persists in the batch folder, so posts made at different moments stay under GitHub's limit together; the shared baseline runs first for its commit, and the flaky-check reruns and the comparison of failing test names work as today; a takeover's push still goes through takeover.py behind Claude Code's permission prompt; tests first on pr-review's existing suites, so nothing changes but speed; built through implement in a worktree in three slices (posting and load, baseline and installs, takeover), released together as 5.2.0.

8. The user confirmed on 2026-10-09: build it through seams:implement in a new worktree, three slices, released together as 5.2.0.

9. Slice 2 changed (the user's choice, 2026-10-09, on the evidence below): no install sharing (installs took 0-4 s); instead make baseline sharing work: run_checks.py gives each run $SEAMS_SIDE (base or head) and a $SEAMS_RUN unique to the review and side, the checks instructions keep a check's command the same text on every pull request (no evidence paths, database names from $SEAMS_RUN), and a baseline failure confirmed by a second run alone is shared like a pass.

10. Mine, within decision 4: a take-over's baseline comes from its review's own checks (`run_checks.py --base-from`), a pass or a confirmed failure, since it is the same tree at the same commit; the fixed tree runs every check. The pushes ticked in the one question go out in one Bash call, so Claude Code's permission prompt (still the push's own yes) comes once.

11. The review (2026-10-09), acted on: a shared baseline failure is used only beside a passing candidate (a pull request's code could forge one), and a take-over takes only its check's own logs; a review's own baseline pass is shared over a failure seen once; a block and a post-dated ledger entry expire with the hour; the post lock waits --lock-wait seconds (90) and says so, in a folder checked to be the user's alone; `--auto` holds a check broken by the PR that has not run alone while its batch is open; the end of a batch posts every review not yet on GitHub. The ledger is per machine, not per batch as decision 7 said: GitHub's limit is the account's (a `ceiling:` comment marks two accounts on one machine).

## Open questions

- None.

## Facts

- 2026-10-09, this Mac's evidence (222 reviews): install 0-4 s a tree; test ~660 s a tree; a failing gate 959 s on the baseline, 516 s on the head; the rest under 25 s. ClareCap-Underwriting-Engine: 98 reviews over 16 distinct baselines (up to 24 on one). Its reviewers wrote each pull request's evidence path and database name into the commands (`DB=r9c_1586_head`), so the share key (commit, name, command, shell) never matched, and they skipped the baseline for the heavy checks ("NOT RUN on the baseline").

- 2026-10-09 scouts: in a batch, checkout and worktrees are made serially in the main session (git locks); one subagent per pull request, up to 20 at once; `run_checks.py` runs a pull request's checks one after another, both trees together when not service-like, holding one slot (cores/2) for its whole run; a failing check runs up to 4 times; nothing posts until the last subagent finishes (batch.md:20-21), then post_reviews.py posts serially, paced 40 a minute; a single review uses code-review plus a risk reviewer (3 reviewers); takeover is sequential and re-runs every check after the fix, with the user asked before the push. `--share` reuses only passing baseline runs, never installs or builds.
- Timings: the user's 12-PR clarewood batch ran in waves, 15-20 minutes per pull request (the full suite plus two Postgres suites, on both trees); a 15-PR batch put 13 reviewers at once and the load average at 53.5 on 14 cores, and two Postgres verdicts were relabelled flaky by hand; GitHub's secondary rate limit refused posts after 10 in 34 s.
