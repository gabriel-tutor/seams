# Progress: pr-review faster, the same quality

Status: active
Stage: designing
Next: The user's confirmation; then built through seams:implement in a new worktree, three slices, as 5.2.0.
Updated: 2026-10-09

## Decisions

1. The bar (the user's words, 2026-10-09): "preserve the senior like quality review, i want to optimize only the speed without affecting the quality output". Every check still runs locally on the pull request's tree, findings are still proven, flaky checks still re-run; nothing is skipped or trusted from elsewhere for speed. The user's standing rule holds: don't ruin pr-review.
2. Posting (the user's choice): each review posts as soon as its pull request is fully verified, paced under GitHub's rate limit; only reviews that need the user's yes, or a recheck of a flaky check on a quiet machine, wait for the end of the batch.
3. Baseline (the user's choice): one baseline per distinct base commit in a batch, shared by every pull request on that commit, failures included (the same commit gives the same result); today it re-runs per pull request and shares only passing runs.

4. Takeover (the user's choice): several pull requests are taken over at once, each fixed by its own builder in its own worktree, every check still re-run after the fix; the user approves the list of pushes once, at the end.
5. Installs (the user's choice): the first install for a lockfile is kept and cloned (APFS copy-on-write) into every other tree with the identical lockfile; a pull request that changes the lockfile installs fresh.
6. Load (the user's choice): as many pull-request agents run at once as there are check slots (half the cores), the next starting as one finishes, instead of up to 20.
7. Mine, the user may overrule them: posting's rate pacing persists in the batch folder, so posts made at different moments stay under GitHub's limit together; the shared baseline runs first for its commit, and the flaky-check reruns and the comparison of failing test names work as today; a takeover's push still goes through takeover.py behind Claude Code's permission prompt; tests first on pr-review's existing suites, so nothing changes but speed; built through implement in a worktree in three slices (posting and load, baseline and installs, takeover), released together as 5.2.0.

## Open questions

- None; the user's confirmation.

## Facts

- 2026-10-09 scouts: in a batch, checkout and worktrees are made serially in the main session (git locks); one subagent per pull request, up to 20 at once; `run_checks.py` runs a pull request's checks one after another, both trees together when not service-like, holding one slot (cores/2) for its whole run; a failing check runs up to 4 times; nothing posts until the last subagent finishes (batch.md:20-21), then post_reviews.py posts serially, paced 40 a minute; a single review uses code-review plus a risk reviewer (3 reviewers); takeover is sequential and re-runs every check after the fix, with the user asked before the push. `--share` reuses only passing baseline runs, never installs or builds.
- Timings: the user's 12-PR clarewood batch ran in waves, 15-20 minutes per pull request (the full suite plus two Postgres suites, on both trees); a 15-PR batch put 13 reviewers at once and the load average at 53.5 on 14 cores, and two Postgres verdicts were relabelled flaky by hand; GitHub's secondary rate limit refused posts after 10 in 34 s.
