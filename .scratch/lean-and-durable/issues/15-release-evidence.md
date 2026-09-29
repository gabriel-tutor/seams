# 15: 3.3.0's release evidence, deferred at the release

**What to build:** The paid evidence that 3.3.0 shipped without (decision 46), run on the released plugin and recorded in the evidence doc's "3.3.0: the release evidence" section, where each cell it fills now says "not run: ticket 15". The plugin under test is `7c80291`'s `plugin/`, the released plugin, which the release's docs commit leaves unchanged. A case that drops below its bar is a regression: route it through `diagnosing-bugs`, and its fix ships as 3.3.1 through `release`.

**Blocked by:** 14 (Release 3.3.0)

**Status:** ready-for-agent

- [ ] Every paid run is asked first, with its estimated cost.
- [ ] The routing and gate evals: `claude plugin eval plugin --tag routing --tag gate --scaffold --allow-tools Edit Write -j 3 --no-publish`, three runs per arm, with `--model claude-opus-5` and with `--model claude-sonnet-5`, as ticket 08 ran them (about $20 and $12.50, 25 minutes each). Every case scores at or above its recorded 1.00; `pr-review-routing`, added in 3.3.1, has no recorded bar yet, so its first pass sets one.
- [ ] The two `shell` cases through the harness, which the eval's sandbox can't run on this Mac: `python3 scripts/behavior_test.py run --scenario gate-shell-write --scenario gate-commit --arm plugin --runs 3 --assert`, 3 of 3 each.
- [ ] Resume after `/clear`, a fresh session over the progress file: `resume-grill` and `resume-ticket` through the harness, 3 of 3 each; and a `pr-review` batch of closed pull requests #5, #6 and #7, killed after one draft and resumed in a fresh session, which reviews only #6 and #7 and reuses #5's draft byte for byte.
- [ ] Resume after `/compact`, headless `--resume` as tickets 04 and 05 ran it: the grill and the ticket continue without starting over; and the same `pr-review` batch, killed after one draft, then `claude -p --resume <id> "/compact"` and a continuing prompt, reviews only the unfinished pull requests. The batch has never been resumed through `/compact`.
- [ ] Every GitHub write in the batch runs is refused by the shims, and the clone's status and worktree list end as they started.
- [ ] Must not happen: a case's bar lowered to fit a result, or a result from an earlier SHA quoted as this plugin's.

**How to verify:**
- The eval result JSON under the gitignored `tests/runs/evals/ticket-15/`, and `scripts/eval_report.py` on it for the doc's table.
- The harness's `report` on its `results.jsonl` records.
- The batch runs' streams and the driver's JSON lines (the kit is below).

## Comments

Deferred at the 3.3.0 release on 2026-09-27, the user's choice: they needed 3.3.0 in an urgent project and asked for a ticket to come back to (decision 46). The reasons it was judged safe to ship first are in decision 46 and in the evidence doc's 3.3.0 section.

The kit for the batch runs is ticket 07's live-run harness, copied into the gitignored `tests/runs/lean-15-kit/` (its scratchpad is lost at a reboot):
- `drive.py`: one `claude -p` session per call, killed once the batch's progress file counts a drafted review; `env.sh`, `settings.json` and `shims/` refuse every GitHub write and log every `gh` and `git` call;
- `analyze.py`: what each session did, from its stream.

The `/compact` run needs one step `drive.py` lacks: after session 1's kill, `claude -p --resume <session 1's id> "/compact"`, then a continuing prompt on the same id, each with the same environment. Session 1's id is in its stream's init event. Ticket 07's record, in the evidence doc, gives the setup it used: a fresh clone, `--plugin-dir` at a `git archive` export of the plugin under test, `--permission-mode default`, and `TMPDIR` set to the run's own directory.

The routing harness switches off only `superpowers@claude-plugins-official`. On this account `claude plugin list` shows `superpowers@synced` held back only because that one takes precedence, so a harness run may load it: read each run's init event for its plugins, and record what loaded.
