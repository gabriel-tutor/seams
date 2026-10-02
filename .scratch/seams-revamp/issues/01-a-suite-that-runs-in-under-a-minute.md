# 01: A suite that runs in under a minute

**What to build:** the maintainer runs `scripts/test.sh` and every suite starts at once; the run reports each suite's result and time and fails when it goes over its budget. The macOS system-Python compatibility check runs as one CI job instead of re-running everything locally. The custom eval harness (`behavior_test.py`, its report, `prepare_run.sh`, `fixture_deps.sh`, the Node fixture's dependencies and their two test suites) is removed; the scenarios under `plugin/evals` stay for `claude plugin eval`.

**Blocked by:** None (can start immediately).

**Status:** ready-for-agent

- [ ] One command runs every remaining suite in parallel and prints each one's result and wall time; it exits non-zero when any suite fails.
- [ ] A test fails when the whole run takes longer than its budget (one minute on the user's Mac, a CI value of its own).
- [ ] The local run uses one Python; CI has a job on Python 3.9 that runs the hook and gate tests.
- [ ] The custom harness, its workspace builder, its Node fixture and their tests are gone; nothing left in the repo calls them; the suite needs no Node.
- [ ] `plugin/evals` still validates and runs with `claude plugin eval` (its structure test stays green).
- [ ] Must not happen: a suite failure hidden by the parallel run, or a suite silently skipped.
- [ ] Built in a worktree; nothing CPU-heavy beyond the suite itself runs on the user's Mac.

**How to verify:** `time scripts/test.sh` in the worktree (green, under a minute); make one test fail on purpose and see the run exit non-zero naming it; the CI run on the staging branch shows the Python 3.9 job.
