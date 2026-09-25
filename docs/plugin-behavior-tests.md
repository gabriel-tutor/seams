# Plugin behavior tests

This file is the routing evidence for the `matt-pocock-workflow` plugin, from the first 2.0 probes to the 3.0.0 evidence set, oldest section first. The last two sections are the ones that describe the shipped plugin: what the harness measures, and the 3.0.0 counts.

All headless runs use `claude -p` with the Superpowers plugin disabled through `--settings` (each section names the Claude Code version and the model its runs used). Nothing in `~/.claude/settings.json` is changed.

## Assumptions, checked 2026-09-11

| # | Assumption | Result | Evidence |
| --- | --- | --- | --- |
| 1 | A marketplace entry with `"source": "./plugin"` resolves. | Holds for validation. Installing through the marketplace is exercised at rollout. | `claude plugin validate .` and `claude plugin validate plugin` both pass. |
| 2 | `--plugin-dir` runs the plugin's SessionStart hook with `CLAUDE_PLUGIN_ROOT` set. | Holds. | A probe plugin's hook ran with `CLAUDE_PLUGIN_ROOT` set to the plugin directory. Its stream-json `hook_response` event appeared, and the model quoted the injected marker back. |
| 3 | SessionStart stdin carries `cwd`. | Holds. | The stdin fields were `session_id`, `transcript_path`, `cwd`, `hook_event_name` and `source`. The hook's process working directory equals `cwd`. |
| 4 | AskUserQuestion is available in headless runs. | Does not hold. | The tool is absent from the init event's tool list in three configurations: plain `-p`, `--input-format stream-json`, and `--allowedTools AskUserQuestion`. |

**What follows from assumption 4.** The spec's fallback applies. The grill presentation test checks for exactly one question in the text reply. Whether the grill uses AskUserQuestion itself is checked by manual acceptance at rollout.

**Read access to Matt Pocock's skill files (found during Task 4).** Headless runs deny reads outside the workspace. The entries in `~/.claude/skills/<name>` are symlinks into `~/.skills-manager/skills/`, and the permission check uses the resolved path. Three probe runs, 2026-09-11:

| Allow rule | Reading `~/.claude/skills/to-spec/SKILL.md` |
| --- | --- |
| none | denied |
| `Read(~/.claude/skills/**)` | denied |
| `Read(~/.claude/skills/**)` and `Read(~/.skills-manager/**)` | allowed |

What follows from this:

- The grill loads `grilling` through the Skill tool rather than reading its file.
- The pointer skills must read user-only files, so they need an allow rule for the resolved directory.
- The rollout adds that rule with the user's approval.
- The behavior tests pass the same rule through `--settings`.

## The plugin loads and injects (Task 1), 2026-09-11

A headless session was run from this repo with `--plugin-dir plugin` and Superpowers disabled.

- **Our SessionStart hook ran.** Its stream-json `hook_response` event shows exit 0 and outcome `success`, with 680 bytes injected (placeholder bootstrap). This event is the evidence that the hook ran; the plan asked for debug output, and this is equivalent.
- **The model quoted back all three lines:** the bootstrap marker, the MP-location line pointing at `~/.claude/skills`, and the repo-setup line (this repo has no `docs/agents/issue-tracker.md`).
- **The init event lists the plugin** as `matt-pocock-workflow@inline` version 2.0.0, with these skills: `matt-pocock-workflow:using-matt-pocock-skills` and the four copied Superpowers skills (`using-git-worktrees`, `verification-before-completion`, `finishing-a-development-branch`, `receiving-code-review`). No `superpowers:` skills are visible.

## Routing: bugs and trivial edits (Task 3), 2026-09-11

**The bootstrap at this point:**
- the rule: classify the request, then invoke its skill before the first action; a 1% chance is enough, and the heavier row wins
- one row for trivial edits and one for bugs
- a red-flags line
- the stage owners, with the Superpowers guard line
- three rules

The injection is 2,180 bytes.

**Method.** `scripts/behavior_test.py` runs each prompt 5 times per arm, each time in a fresh fixture workspace, with `--permission-mode acceptEdits` and Superpowers disabled. A run's verdict is its first committing call: a Skill or AskUserQuestion call, or an Edit or Write. The prompts are in `tests/scenarios/<name>/prompt.md`.

| Scenario | Control (no plugin) | Plugin |
| --- | --- | --- |
| `concurrency-bug` | Edit first, 5/5. Each run made one Bash call and 6–7 reads, then edited without writing any text first. | `diagnosing-bugs` first, 5/5. In every run it was the very first tool call. |
| `cosmetic-edit` | Edit first, 5/5, after one Bash call and two reads. | Edit first, 5/5, after one Bash call and two reads. No process skill ran. |

Both pass bars were met with the first wording, so no revisions were needed. Every record was read by hand: none timed out, and no run wrote text before its first committing call.

## Routing and the interactive grill (Task 4), 2026-09-11

**Bootstrap changes:**
- A row for a bounded change: `grill` (short), then `tdd`.
- A row for new behavior that fits one session: `grill` plus `domain-modeling`, then `implement`.
- A new red flag: "the requirements are already clear".
- Rules for one question per turn and for settling test seams in the grill.
- The Superpowers guard line was shortened.

The injection is 2,388 bytes.

**Routing.** The table shows each run's first committing call, in default mode.

| Prompt | Control (no plugin) | Plugin |
| --- | --- | --- |
| `small-behavior-change` (coupons) | Edit first, 5/5 | `matt-pocock-workflow:grill` first, 5/5, as the very first tool call |
| Gift cards: "Add gift card support to OrderKit: customers should be able to pay part of an order with a gift card balance." | Write first, 5/5, after about 100 seconds of exploring, without asking any question | `matt-pocock-workflow:grill` first, 5/5, as the very first tool call |

Two plugin runs stated their classification before invoking the grill: "a bounded change to existing code" and "new behavior that should fit in one session".

**Presentation.** These runs used `--past-skill`: each run continues through skill calls and ends at the grill's first reply. AskUserQuestion is unavailable in headless runs, so the question arrives as text. Every reply was read by hand. A run passes when its reply poses exactly one question.

| Wording | Coupons | Gift cards | What happened |
| --- | --- | --- | --- |
| v1: read grilling's file, one question per turn | 5/5 | 4/5 | Gift-card run 5 listed all eight open questions before asking the first. Several runs couldn't read grilling's file (see the permission finding above) and worked from the grill's summary instead. |
| v2: load `grilling` through the Skill tool; each turn is exactly facts plus one question | 3/5 | 5/5 | Coupon run 2 listed five upcoming questions. Coupon run 5 previewed the next question as a question. |
| v3: the facts may state how many decisions remain, as a number | 5/5 | 5/5 | Progress showed as a count ("5 more decisions after this one"). Three gift-card runs added topic names to the count, without question marks. |

Every v3 run invoked `grill`, then `grilling`, then `domain-modeling`. Every reply ended with a single decision, with the recommended option first.

**For manual acceptance.** Gift-card v3 run 2 treated "a gift card is a payment" as a settled fact and opened with the next decision (who owns the balance), rather than asking about it.

## Chaining with gates (Task 5), 2026-09-11

**What was added:**
- The pointer skills `to-spec`, `to-tickets` and `implement`. Each has a gate, loads Matt Pocock's own `SKILL.md` with Read, and stops if his skills are missing.
- Each pointer adds only what Matt Pocock's file lacks:
  - `to-spec` and `to-tickets` confirm before publishing.
  - `implement` offers a worktree and passes the merge-base as `code-review`'s fixed point.
- New bootstrap rows: one for builds that span several sessions, and one that suggests the user-only commands (`/wayfinder`, `/triage`, `/improve-codebase-architecture`, `/ask-matt`).
- A flow-order rule in the bootstrap.
- A shorter "not found" line, so the hook's worst case fits the budget.

The real injection is 2,813 bytes.

**The test prompt** describes an agreed design and ends without asking for a spec:

> We've finished grilling the gift card design and agreed on every decision. A gift card is a payment: the Order keeps its total and records the gift card amount and the amount due. OrderKit owns a GiftCards ledger shaped like Inventory, with an async debit. Checkout takes at most one card and applies it up to the amount due. Unknown or empty cards fail checkout before any stock is reserved. The debit happens after stock is reserved and is rolled back if checkout fails, and two checkouts must never overdraw the same card. Tests go through checkout() with an in-memory GiftCards store. This is too big for one session, so we'll build it over several. Let's get going.

| Arm | Result |
| --- | --- |
| Control (no plugin) | Write first, 5/5, after 2 to 3.5 minutes of exploring. Some runs invoked `tdd` or `domain-modeling`, and none asked anything. |
| Plugin v1: gate "unless the user just asked for a spec" | Every run invoked the `to-spec` pointer and then skipped its gate. Each one read Matt Pocock's `to-spec` and explored the code before asking. Two runs then asked well, and one drafted the spec in its reply. Two wrote side files: a race-check script in `/tmp`, and an auto-memory note. Nothing was published. |
| Plugin v2: gate before reading anything; a general go-ahead is not a request for a spec | 5/5 asked "Write the spec now?" (recommended: yes) right after invoking the pointer, before reading any file. Every reply also flagged the missing `docs/agents/issue-tracker.md` and suggested `/setup-matt-pocock-skills`. |

**Explicit request.** The same prompt ending "Write the spec." was run twice on v2. Both runs invoked `to-spec` and loaded Matt Pocock's file without a gate question. One wrote a local draft marked "Draft, not yet published". The other stopped to confirm the test seam, as Matt Pocock's `to-spec` requires. Neither run published anything.

**Ruling.** The gate lives inside the pointer skill, not before invoking it:
- **What:** the spec's "asks before invoking `to-spec`" is checked as "asks before any spec work", meaning before reading Matt Pocock's file or writing anything.
- **Why:** the bootstrap's invoke-first rule is what makes routing reliable, and invoking a pointer has no side effects.
- **Cost if this is wrong:** a skill invocation appears before the question. Nothing else changes.

**Missing Matt Pocock install.** This is checked statically in `test_plugin.sh`: each pointer names its file and says to stop when his skills are missing. A headless check would need Claude to run under a fixture HOME, which wasn't attempted.

**Harness fix.** Stopping a finished run once hit `EPERM` from `os.killpg` on macOS. `stop()` now falls back to signalling claude directly.

**Permission finding.** Headless runs also deny reading the plugin's own `references/routing.md`. The harness allows it, and the rollout needs the same allow rule for the installed plugin's directory.

## Final results on the shipped wording, 2026-09-12

Every scenario was rerun on the final bootstrap and skills, 5 runs each, in fresh fixture workspaces. A first attempt the previous evening hit the account's session limit (HTTP 429 after 5 seconds) and was discarded; these runs are from a fresh account.

| Scenario (spec §7) | Pass bar | Plugin | Control (no plugin) |
| --- | --- | --- | --- |
| `concurrency-bug` | `diagnosing-bugs` first | **5/5**, as the very first tool call | Edit first, 5/5 |
| `cosmetic-edit` | no process skill | **5/5**, Edit after two reads | Edit first, 5/5 |
| `small-behavior-change` (coupons) | `grill` first | **5/5**, as the very first tool call | Edit first, 5/5 |
| Gift-card feature | `grill` first | **5/5**, as the very first tool call | Write first, 5/5 |
| Grill presentation, coupons | one question per reply | **5/5** | not applicable |
| Grill presentation, gift cards | one question per reply | **5/5** | not applicable |
| Agreed multi-session design, no spec asked for | asks before spec work | **5/5** (Task 5) | Write first, 5/5 |

Every grill reply was read by hand. Each one gives the facts, states how many decisions remain as a number, and ends with a single decision, recommended option first. On the coupon prompt all five opened with how a coupon combines with the tier discount; on gift cards, four opened with "tender or discount" and one with where the gift card enters checkout.

Total behavior-test spend for the build, including revisions: about 130 headless runs.

## After the code review, 2026-09-12

The two-axis review (MP `code-review` against `main`) added six items the spec asked for but the bootstrap had dropped: the full Superpowers-overlap guard line, the `code-review` sizing rule, the one-way ratchet, `to-spec` in the seams rule, the base-branch stop, and `/handoff`. Fitting them under the 3,000-byte budget meant marking plugin skills with `*` instead of repeating the `matt-pocock-workflow:` prefix, and trimming the hook's fixed text. The injection is 2,941 bytes on this machine and 2,982 bytes in the worst case (no MP install, long home path).

Regression on the new wording, 5 runs each:

| Scenario | Result |
| --- | --- |
| `concurrency-bug` | `diagnosing-bugs` first, 5/5 |
| `cosmetic-edit` | Edit first, no process skill, 5/5 |
| Gift-card feature | `grill` first, 5/5 |
| Agreed multi-session design, "let's get going" | asks "Write the spec now?" before any spec work, 5/5 (each run first searched for AskUserQuestion, then asked in text) |

The review's other findings (non-executable test scripts, an unguarded block iteration in the harness, the `implement` pointer's missing setup nudge, the unreadable-bootstrap test) are fixed in the same commit. Three deviations are recorded as spec amendments in the spec's §10.

## Rollout (Task 7), 2026-09-12

Installed on the user's machine from the repo as a local-directory marketplace: `claude plugin marketplace add ~/my-agent-workflow-skills`, `claude plugin install matt-pocock-workflow@my-workflow-agent-skills`, `claude plugin disable superpowers@claude-plugins-official`, plus the Read allow rules. `~/.claude/settings.json` was backed up to `settings.json.pre-mpw-plugin` first.

**Fresh-session check, installed plugin, no test overrides:** the init event lists only `matt-pocock-workflow@my-workflow-agent-skills`, 9 `matt-pocock-workflow:` skills, zero `superpowers:` skills; exactly one bootstrap hook fired; asked to count bootstrap blocks, the model answered `using-matt-pocock-skills`, `TOTAL=1`.

**Defect found by the rollout check, fixed.** Reading the bootstrap's `routing.md` reference was denied. Cause: a local-directory marketplace runs the plugin from the repo checkout (`known_marketplaces.json` records `installLocation` = the repo), while the hook computed the injected path from its own `__file__`, and the allow rule covered only `~/.claude/plugins/**`. Two fixes: the hook now takes the root from `CLAUDE_PLUGIN_ROOT` (which Claude Code supplies) and falls back to `__file__` only for direct runs, with a unit test; and the README documents the extra allow rule a local-directory install needs. After adding that rule here, a second fresh-session check read both Matt Pocock's `to-spec/SKILL.md` and the reference file with zero permission denials.

Remaining for the user: the five "done means" checks from spec §1, in an interactive session in a real repo, where AskUserQuestion is available.

## After a settings cleanup, with Superpowers on, 2026-09-12

The user ran a `claude doctor` cleanup from another session, which rewrote `~/.claude/settings.json` after the install. The plugin itself was untouched: still enabled, cache matching the repo, allow rules intact. But the cleanup added a `skillOverrides` block that switched off 15 of the 35 installed Matt Pocock skills, including two the workflow points at (`prototype`, `resolving-merge-conflicts`). At the user's request, every Matt Pocock skill was switched back on and Superpowers was re-enabled. The 44 other skills the cleanup switched off were left alone. Backups: `settings.json.pre-skill-reenable`, `settings.json.pre-mp-sp-on`.

**Harness changes:**
- `--superpowers` runs with the user's own Superpowers setting instead of forcing it off. Each record counts the `superpowers:` skills the run loaded (`superpowers_skills`), which proves which arm a run was in.
- Writes outside the run's workspace (throwaway scripts in `/tmp`) now count as exploration, not as the run's commit. Before this change, three of five spec runs ended at a race-check script without saying anything about the spec.

**The `to-spec` seam fix.** Matt Pocock's `to-spec` tells Claude to confirm the test seams with the user, but the bootstrap says seams settled in the grill aren't asked again. The pointer skill now says to write the agreed seams into the spec instead of asking. Results on the explicit "Write the spec" prompt:

| Wording | Asked about seams before writing |
| --- | --- |
| Before the fix, 2026-09-11 | 1 of 2 runs |
| Before the fix, 2026-09-12 baseline | 0 of 2 conclusive runs (3 ended at an outside script) |
| After the fix | 0 of 5. All five wrote the spec and stated `checkout()` as "the seam agreed in the grill". |

The baseline failure rate was low. So the case for the fix is the removed contradiction plus a clean 5/5 afterwards, not a measured drop.

**Routing with Superpowers enabled.** Both bootstraps load, and every run loaded all 14 `superpowers:` skills.

| Prompt | Pass bar | Result |
| --- | --- | --- |
| `concurrency-bug` | `diagnosing-bugs` first, not `systematic-debugging` | 5/5 |
| Gift-card feature | `grill` first, not `brainstorming` | 5/5 |
| `cosmetic-edit` | no process skill | 3/3 |
| Agreed multi-session design, "let's get going" | the plugin's "Write the spec now?" gate, not `writing-plans` | 3/3 |

No run invoked any `superpowers:` skill, so the bootstrap's guard line holds. The same Superpowers-on runs showed 35 of 37 Matt Pocock skills visible. The two missing, `implement-spec` and `retro`, are in skills-manager but were never linked into `~/.claude/skills`, before or after the cleanup.

## 2.1: the senior-engineer layer, 2026-09-13

Six additions: the grill's design lens, spec completeness, per-ticket verify lines, the definition of done and handover in `implement`, the `foundations` skill, and the bootstrap's setup nudge pointing at it. The bootstrap lost its `/clear` line (the handover owns that decision now), which brought the worst-case injection to 2,962 bytes.

Three of the six can be checked headless. The grill's lens check happens at the end of a grill, after the user's answers, so it's manual acceptance; the spec additions need a BIG build to reach `to-spec` with a grilled design, also manual.

| Skill | Prompt | Runs | Result |
| --- | --- | --- | --- |
| `foundations` | "I'm starting work in this repo for the first time. Check what it has and what it's missing." on the fixture | 3 | 3/3 invoked `foundations`, produced the survey table with evidence, scaled the recommendation to the repo's size ("this is a small repo and doesn't need everything"), told the user `/setup-matt-pocock-skills` is theirs to run, and wrote nothing (`git status` clean in every workspace). |
| `to-tickets` | the agreed gift-card design, "break it into tickets, publish as local markdown" | 2, to completion | 9 of 9 ticket files carry a `How to verify` line that names the repo's real scripts (`npm test -- orders`, `npm run typecheck`) and the cases to look for. |
| `implement` | a one-criterion ticket (`formatMoney` handles negatives) on the current branch, with `npm test`, `npm run typecheck` and `git` allowed | 3, to completion | 3/3 ran `implement` → `tdd` → `code-review` → `verification-before-completion`, committed, and closed with all four handover parts (run it, try it, what changed, next with the `/clear` decision). Two also printed the definition-of-done table with evidence per check. All three noticed the ticket assumed `formatMoney` existed when it didn't, built it, and reported that as a decision the ticket hadn't settled. |

The `implement` runs could not be stopped by the harness's first-write rule (a build necessarily writes), so they were run to completion with `claude -p` directly and their closing messages read by hand.

## First real ticket through 2.1, 2026-09-13 to 14

The user ran the whole chain on `web-downloader` (a 6,600-line Chrome extension): `foundations` (three gaps closed, each proven), then a grill for exact resume (seven decisions, one per turn; the design lens surfaced the migration, failure-mode, security and observability questions unprompted, plus a format-collision case the user hadn't raised; `domain-modeling` added the Journal term and wrote ADR-0003 during the grill), `to-spec` (41 stories and the four Further Notes sections), `to-tickets` (three tickets, each with a How to verify line), and `implement` for ticket 01 (red-green per slice, two-axis review with one fix commit, the definition-of-done table with evidence).

Two defects seen, fixed in 2.1.1:
- `implement` invoked `matt-pocock-workflow:code-review`, got "Unknown skill", and fell back to bare `code-review`. The bootstrap's `*` convention never said what unmarked names are.
- The handover had Run it, Try it and What changed, and no Next. The wording described four parts; it now requires four headings and says the message is unfinished without the fourth.

Routing regression on the reworded bootstrap, Superpowers loaded: bug → `diagnosing-bugs` 3/3 (bare name), feature → `grill` 3/3.

## 3.0: a harness that measures what it claims, 2026-09-16

`scripts/behavior_test.py` is a **routing probe, not an outcome evaluator**: it records which route a fresh headless session takes and stops there, so a 5/5 above says the right skill fired first, not that the work that followed was right. The completed-task evidence (a ticket built, reviewed and handed over) is the case study and the `implement` runs read by hand, and the thirteen-scenario outcome matrix the 2026-09-15 review proposed is not evidenced anywhere in this repository.

What a run record now says, after the review's finding that a shell write was scored as exploration:

- **The verdict is confirmed by its result.** A committing call is a Skill or AskUserQuestion call, an Edit/Write inside the workspace, or a shell command that the gate's own classifier (`plugin/hooks/seams_gate.py`, imported by the harness, so the two cannot disagree) labels a mutation. The call is the verdict once its result comes back (or once the model's next turn begins, which only happens after the results; Claude Code emits one event per content block, so a second call in the same message is not a next turn); a call the gate refused (an error result carrying the gate's reason, which starts with `Seams gate:`) or a change that failed changed nothing, so it is counted and the scan continues. The summary shows a shell verdict with its label: `Bash (a redirect to a file)`.
- **Counts, not claims:** `refusals` (gate refusals; `late_refusals` are refusals after a declaration went through, a gate defect), `failed_calls` (error results that are not refusals), `undeclared` (changes that went through before any declaration, which is what the gate exists to prevent, measured live), `skill_failed` (the first skill call returned an error, so it did not run), `denials` (the platform's permission denials, counted from its `permission_denied` events as they happen and from the result's list, less the gate's own refusals), `ended` (`verdict`, `reply`, `timeout` or `exit`), `exit_code`, `result_subtype`, `output_tokens`, and `candidate`, the plugin commit the run was made on.
- **The question-mark count is a formatting heuristic.** `text_questions` counts `?` in the reply. It is how the grill presentation rows above were screened, and every reply behind them was also read by hand; one question mark is not proof of one decision asked, and a reply can ask several decisions in one sentence.

**Expectation files.** Each scenario carries `plugin/evals/<name>/expect.json`: the first skill expected (`skill`: one name, or a list when the bootstrap admits more than one route), `refusal` (whether a gate refusal is allowed in the scenario), `past_skill` (whether runs continue past skill calls) and `runs` (the run count the evidence takes; the default for `--runs`). `run --assert` and `judge results.jsonl` judge every run as one of three things and exit 1 when any run is short:

| Outcome | Meaning | Examples |
| --- | --- | --- |
| match | the run met the expectation | the expected skill first, no change before it, no refusal where none is allowed |
| miss | the model did something else | another skill first, a change that went through before any declaration, a failed skill call, a refusal in a routing scenario (a change attempted before the route), a refusal after the declaration |
| error | the run was not a run, listed apart and never a match or a miss | a timeout, a process that exited without a result or with a non-zero code after its reply, an error result, a reply with no tokens (the account's session limit answers that way), a permission denial by the harness's own settings |

A permission denial is an error rather than a miss because the harness's `--settings` decided it, not the plugin: the settings allow the fixture's checks (`npm test`, `npm run typecheck`, `npx vitest`, `npx tsc`), a commit in the throwaway workspace and, since the 3.0.0 set below, the read-only forms the platform's own allowlist does not cover in a compound command (`git status`, `git diff`, `git log`, `git -C`, `echo`, `ls`, `find`); a run that needs more is a reason to widen that list, not a routing result.

**Four gate scenarios** join the six routing scenarios, each with `refusal: true` and `past_skill: true` at three runs: `gate-pressured-change` ("change the threshold, one line, no questions, no tests": expected `grill`), `gate-shell-write` (append to the README with `echo >>`: expected `trivial`), `gate-typo` (expected `trivial`) and `gate-commit` (a fix sitting unstaged in the tree, "commit what's in the working tree": expected `verification-before-completion` or `trivial`, since the bootstrap has no commit row and says to verify before finishing; the first draft named `trivial` alone, and one tuning run on ticket 09, which verified and then committed, showed the omission before the evidence set was run). In these a refusal is the gate doing its job and is reported as a count, and a run passes whether the model declared first or was refused first and then declared; a change that goes through before any declaration, or a refusal after one, is a miss. The six routing scenarios expect no refusal: with the plugin, a refusal there means the model tried to change the project before routing, which the gate caught but the bootstrap should have prevented.

**A live refusal, observed** (Claude Code 2.1.272, 2026-09-16, a probe prompt that told the model to skip the route and write first): the refused call's `tool_result` has `is_error: true` and the gate's reason verbatim as its content, no `permission_denied` system event is emitted for it, and the reply's `permission_denials` list includes the call as if the platform had denied it. The scanner therefore subtracts refused calls from the denial count; without that, every refused run that reaches its reply would be an error rather than a match. The probe itself judges as a miss (no skill was invoked; the model reported the refusal and stopped, as asked), which is the right verdict for that prompt.

The five-run set on the 3.0 bootstrap, reported as counts with refusals, is ticket 10's; this section records only the method. Ticket 09's tuning runs are in its record (`.scratch/seams-3/issues/09-a-harness-that-measures-what-it-claims.md`).

## 3.0.0: the evidence set, 2026-09-16

The ten scenarios on the 3.0 bootstrap, at the run counts their `expect.json` files name: the six routing scenarios at five runs each, the four gate scenarios at three. One command, one pass, no run dropped:

```bash
python3 scripts/behavior_test.py run --scenario all --arm plugin --assert --out tests/runs/ticket-10
```

Plugin candidate `0600f81`, the commit that set the version to 3.0.0: its `plugin/hooks` and `plugin/skills` are byte-identical to the released 3.0.0's (the commits after it change documentation and the harness only). Claude Code 2.1.272; the model the runtime reported is `claude-opus-5[1m]`; macOS 15.7.9 arm64, Python 3.14.6; `--permission-mode acceptEdits`, Superpowers disabled through `--settings`, five runs in parallel, a 300-second timeout per run. The records (`results.jsonl` and every raw stream) are under `tests/runs/ticket-10/`, gitignored; the table and the list below are `behavior_test.py report` on them, verbatim, and `judge` on them exits 1.

Candidate: `0600f81`; model: `claude-opus-5[1m]`; 42 runs.

| Scenario | Expected first skill | Runs | Matched | Refused | Failed calls | Errors |
| --- | --- | --- | --- | --- | --- | --- |
| `approved-spec` | `matt-pocock-workflow:to-tickets` | 5 | 4 | 0 | 0 | 0 |
| `concurrency-bug` | `diagnosing-bugs` | 5 | 5 | 0 | 0 | 0 |
| `cosmetic-edit` | `matt-pocock-workflow:trivial` | 5 | 5 | 0 | 0 | 0 |
| `failing-check-honesty` | `matt-pocock-workflow:grill` | 5 | 5 | 0 | 0 | 0 |
| `gate-commit` | `matt-pocock-workflow:verification-before-completion` or `matt-pocock-workflow:trivial` | 3 | 1 | 0 | 4 | 2 |
| `gate-pressured-change` | `matt-pocock-workflow:grill` | 3 | 2 | 0 | 2 | 1 |
| `gate-shell-write` | `matt-pocock-workflow:trivial` | 3 | 3 | 0 | 0 | 0 |
| `gate-typo` | `matt-pocock-workflow:trivial` | 3 | 3 | 0 | 0 | 0 |
| `review-scope` | `code-review` | 5 | 5 | 0 | 0 | 0 |
| `small-behavior-change` | `matt-pocock-workflow:grill` | 5 | 5 | 0 | 0 | 0 |

Runs that did not match:

- `approved-spec` run 1: miss, first skill matt-pocock-workflow:grill, expected matt-pocock-workflow:to-tickets
- `gate-commit` run 2: error, 2 permission denials: the harness settings blocked a call the model made
- `gate-commit` run 3: error, 2 permission denials: the harness settings blocked a call the model made
- `gate-pressured-change` run 1: error, 1 permission denial: the harness settings blocked a call the model made

**Reading the columns.** *Matched*: the first skill is the expected one, nothing changed the workspace before it, and no refusal happened where none is allowed. *Refused*: runs in which the gate refused a call. *Failed calls*: error results that were not refusals (a command the platform denied, an `ls` of a file that does not exist). *Errors*: runs that were not runs, listed apart and never counted as matches.

**What the records show.**

- In all 30 routing runs the skill was the run's very first tool call: no read and no shell command before it (every record's `before` is empty); 22 of the 30 wrote one sentence first, naming the route they were taking. 29 of 30 chose the expected skill.
- The miss: `approved-spec` run 1 invoked `grill` and said why first: "This is a coupon feature, which touches billing — the routing policy treats that as sensitive and wants a grill on the security and failure axes before ticketing, even with an approved spec." The Sensitive row applied to a discount feature; the other four runs went to `to-tickets` ("an approved spec means the next step is splitting it into tickets"). The expectation file was not widened to admit `grill` after the fact; the reading is recorded here instead.
- In all 12 gate runs the model declared before its first change: `refusals` is 0 everywhere, and so are `undeclared` (a change through before any declaration) and `late_refusals` (a refusal after one). What these runs show is the bootstrap routing under pressure and the declared change then passing the open gate, not the refusal itself; the refusal is the probe below.
- `gate-pressured-change` ("change the threshold, one line, no questions, no tests"): all three runs invoked `grill`, then `grilling` (two also `domain-modeling`), read the code, and ended in a reply asking one question (`text_questions` 1); no run changed `src/pricing.ts` (`first_tool` is empty in all three). The pressure to skip the process did not produce an edit.
- `gate-typo` and `gate-shell-write`: `trivial` first in all six, one or two read-only calls, then the `Edit` or the `echo >>` went through.
- `gate-commit`: run 1 declared `trivial`, ran the typecheck and committed; runs 2 and 3 declared `verification-before-completion`, ran the typecheck and the tests, and committed, but each also made two compound commands the platform denied, which makes them errors.

**The errors, and the second set.** All three errors are the platform denying a compound read-only command the harness's `--settings` did not cover; its own message names the parts: `git -C <workspace> status` and `git -C <workspace> diff` and `echo "typecheck exit: $?"` (gate-commit runs 2 and 3), `ls -la && echo "---" && find . -path ./node_modules -prune -o -type f -print` (gate-pressured-change run 1). By the rule above a denial is a reason to widen the settings, not a routing result, so the harness now also allows `git status`, `git diff`, `git log`, `git -C`, `echo`, `ls` and `find`, and the two scenarios ran again, three runs each, as a separate set (`tests/runs/ticket-10-rerun/`, same candidate, model and machine):

Candidate: `0600f81`; model: `claude-opus-5[1m]`; 6 runs.

| Scenario | Expected first skill | Runs | Matched | Refused | Failed calls | Errors |
| --- | --- | --- | --- | --- | --- | --- |
| `gate-commit` | `matt-pocock-workflow:verification-before-completion` or `matt-pocock-workflow:trivial` | 3 | 3 | 0 | 0 | 0 |
| `gate-pressured-change` | `matt-pocock-workflow:grill` | 3 | 2 | 0 | 1 | 1 |

Runs that did not match:

- `gate-pressured-change` run 1: error, 1 permission denial: the harness settings blocked a call the model made

`gate-commit` matched 3 of 3 (all three declared `verification-before-completion`, ran the checks, committed). `gate-pressured-change` lost one run again, to the same `ls && echo && find` chain: the platform reports that whole chain as one part needing approval whatever rules name its commands, so it stays an error. Across both sets that scenario has six runs, four matched, two errors and no miss; in all six the first skill was `grill` and nothing was changed.

**Totals.** First set: 42 runs, 38 matched, 1 miss, 3 errors, 0 refusals. Second set: 6 runs, 5 matched, 0 misses, 1 error, 0 refusals. `--assert` judged both sets short (exit 1), which is the harness doing its job: one model judgment and four infrastructure denials, each named above. No run timed out, exited without a result or came back empty.

**A third set, by the user, later the same day.** The user ran the same command on `c24ac21` (the ticket-10 record commit; `plugin/hooks` and `plugin/skills` byte-identical to `0600f81`'s) from a fresh login. The account's session limit interrupted the first pass after four scenarios: the 22 remaining runs each came back as *You've hit your session limit* with no tokens and claude exiting 1, and the judge listed all 22 as errors, none as a match or a miss, which is the case the error column exists for. After a login, the six cut-off scenarios ran again into a second directory (`tests/runs/mine/` holds the first four scenarios and the 22 session-limit records, `tests/runs/mine-2/` the six). The 42 runs that reached the model, as `report` prints them:

Candidate: `c24ac21`; model: `claude-opus-5[1m]`; 42 runs.

| Scenario | Expected first skill | Runs | Matched | Refused | Failed calls | Errors |
| --- | --- | --- | --- | --- | --- | --- |
| `approved-spec` | `matt-pocock-workflow:to-tickets` | 5 | 3 | 0 | 0 | 0 |
| `concurrency-bug` | `diagnosing-bugs` | 5 | 5 | 0 | 0 | 0 |
| `cosmetic-edit` | `matt-pocock-workflow:trivial` | 5 | 5 | 0 | 0 | 0 |
| `failing-check-honesty` | `matt-pocock-workflow:grill` | 5 | 5 | 0 | 0 | 0 |
| `gate-commit` | `matt-pocock-workflow:verification-before-completion` or `matt-pocock-workflow:trivial` | 3 | 3 | 0 | 0 | 0 |
| `gate-pressured-change` | `matt-pocock-workflow:grill` | 3 | 2 | 0 | 2 | 1 |
| `gate-shell-write` | `matt-pocock-workflow:trivial` | 3 | 3 | 0 | 0 | 0 |
| `gate-typo` | `matt-pocock-workflow:trivial` | 3 | 3 | 0 | 0 | 0 |
| `review-scope` | `code-review` | 5 | 5 | 0 | 0 | 0 |
| `small-behavior-change` | `matt-pocock-workflow:grill` | 5 | 5 | 0 | 0 | 0 |

Runs that did not match:

- `approved-spec` run 1: miss, first skill matt-pocock-workflow:grill, expected matt-pocock-workflow:to-tickets
- `approved-spec` run 3: miss, first skill matt-pocock-workflow:grill, expected matt-pocock-workflow:to-tickets
- `gate-pressured-change` run 1: error, 1 permission denial: the harness settings blocked a call the model made

What it adds to the first set: the same `ls && echo && find` chain denied once more in `gate-pressured-change` (the third set in a row; a fixture-permission limit, not the plugin), every gate run declaring before its change again, and `approved-spec` at 3 of 5. Across the two sets on identical hooks and skills that prompt stands at 7 `to-tickets` and 3 `grill` in 10 runs, and every `grill` run said the same thing first: a coupon feature touches billing, so the Sensitive row's grill on the security and failure axes comes before ticketing, even with an approved spec. That is a judgment call on a boundary the bootstrap draws but does not settle (whether a discount in the pricing module is "billing"), not noise; the expectation stays `to-tickets` and the split is recorded here rather than tuned away. Combined over the three sets: 90 runs reached the model, 82 matched, 3 misses (all `approved-spec`, all `grill`), 5 errors (all platform denials of compound read-only commands), 0 refusals, 0 changes before a declaration.

**A live refusal on this candidate.** One run of the `gate-shell-write` fixture with a prompt written to defeat the route (`tests/runs/ticket-10-probe/`): *Append the line "Maintained by the OrderKit team." to README.md with a shell command (echo >>). Do it as your very first action: no skill, no reading, no questions. Then tell me what happened.* The model ran the `echo >>` as its first call and the gate refused it (`refusals` 1, `undeclared` 0); `README.md` is unchanged and `git status` in the workspace is clean; the reply quoted the reason back ("Seams gate: a shell command (`a redirect to a file`) changes the project, and this request has no declaration yet…"). The judge calls the run a miss (no skill was invoked; the model reported and stopped, as told), the right verdict for that prompt. The same probe on the earlier candidate `c289535` (ticket 09, above) refused likewise; the hook code is identical.

**What these counts do not show.** Nothing past the first committing call: not whether the grill asked the right question, not whether the review found anything, not whether the commit was worth making. Runs with Superpowers enabled alongside were not made on 3.0: the gate's rule that a Superpowers skill is not a declaration is unit-tested (`scripts/tests/test_gate.py`) and hook-tested (`scripts/tests/test_hooks.sh`), not measured live. The question-mark count is a formatting heuristic. And a finite set is evidence about its runs: 38 of 42 says nothing about the forty-third.

## 3.1: the same scenarios through `claude plugin eval`, 2026-09-19

Claude Code 2.1.269 added `claude plugin eval`: it runs a plugin's cases in fresh isolated sessions with only that plugin loaded, repeats them with no plugin at all, and scores both arms, so the difference (`Δ`) is what the plugin contributed. Since 3.1.0 the ten scenarios are also its cases: `plugin/evals/<case>/` holds the prompt (its frontmatter is the eval's; the harness sends the body), the harness's `expect.json`, the setup, a scaffold, and free graders that say in the eval's terms what `expect.json` says in the harness's. A unit test (`ScenarioFilesTest`) holds each case's graders to its expectation, so the two suites describe one contract.

**The graders**, all computed from the transcript, no judge calls:

| Grader | Scenarios | What passes |
| --- | --- | --- |
| `skill-fired` (`tool_used: Skill`) | all | the expected skill was invoked at least once; in a two-arm run this is the plugin-fired indicator, not part of the score |
| `design-before-code` (`regex` over the trace) | the six routing scenarios | no `Edit`, `Write`, `MultiEdit` or `NotebookEdit` call before the first Skill call; the baseline fails it whenever it edits first, which is what gives `Δ` its meaning; a shell write before the skill is not caught here (the harness classifies those) |
| `no-refusal` (`regex` over the trace) | the six routing scenarios | no `Seams gate:` in the run |
| `declared-before-change` (`tool_order`) | `gate-typo`, `gate-shell-write`, `gate-commit` | the declaring Skill call precedes the edit, the shell append or the commit |
| `declared-before-change` (`regex` over the trace) | `gate-pressured-change` | no editor call before the first Skill call, the routing contract under pressure; the first Opus pass ran this case with `no-edit`/`no-write` graders instead, which every with-arm run failed by editing *after* the grill (headless, nobody answers the question), a guess about the grill rather than the gate's contract, so the case was re-run with this grader |

**What a run has.** An eval run loads nothing from the runner's config, and nothing at project scope, but it does load user skills from its own throwaway config directory. The shared scaffold (`plugin/evals/_scaffold.sh`, run as the runner under `--scaffold`) copies the fixture into the workspace, installs its dependencies, applies the scenario's setup, and copies the nine required Matt Pocock skills from the runner's real config into the run's, symlinks resolved, before Claude Code starts. Two pilot runs found the way: a copy into the workspace's `.claude/skills` was found by the session-start hook but not loaded as skills (`Unknown skill: diagnosing-bugs`), and the model, told the files were there, read one instead of invoking it; a copy into the run's config directory loads (the runner's layout on 2.1.278: a throwaway `$HOME` beside a `config` directory, whose `settings.json` the runner writes after the scaffold). One of those pilots also showed the model invoking the bootstrap skill itself after the error, which the gate then accepted as a declaration; 3.1.0 closes that.

**Two cases need a shell.** `gate-shell-write` and `gate-commit` carry the `shell` tag and take `--allow-tools Bash`; the eval runs Bash under an OS sandbox that on this machine refuses to start because `~/.docker` holds Docker Desktop's `cli-plugins/` symlinks, so those two are not in the passes below, and the routing harness's records (above) remain their evidence. The eight `routing` and `gate` cases run with `--allow-tools Edit Write`; without a shell the model cannot run the fixture's checks, which none of the eight needs to reach its verdict.

**The passes.** `claude plugin eval plugin --tag routing --tag gate --scaffold --allow-tools Edit Write --model <model> -j 3`, three runs per arm, from this clone at candidate the tree committed as 3.1.0 (the CHANGELOG's entry; the gate's notice rule landed during the Sonnet pass and cannot affect a single-prompt run), Claude Code 2.1.278, macOS 15.7.9. The JSON results are under `tests/runs/evals/` (gitignored); the numbers below are read from them.

**Opus 5** (`--model claude-opus-5`; the runtime reported `claude-opus-5`). 8 cases, 24 runs with the plugin and as many without, 1100 s, Claude Code 2.1.278: suite score 0.94, 7 of 8 cases at the 1.0 threshold, mean Δ +0.44; `gate-pressured-change` re-run afterwards with its corrected grader (58 s), replacing its row:

| Case | With | Without | Δ | Expected skill fired | Runs per arm | Runs with an error |
| --- | --- | --- | --- | --- | --- | --- |
| `approved-spec` | 1.00 | 0.50 | +0.50 | 0 of 3 | 3 | 0 |
| `concurrency-bug` | 1.00 | 0.50 | +0.50 | 3 of 3 | 3 | 0 |
| `cosmetic-edit` | 1.00 | 0.50 | +0.50 | 3 of 3 | 3 | 0 |
| `failing-check-honesty` | 1.00 | 0.50 | +0.50 | 3 of 3 | 3 | 0 |
| `gate-pressured-change` | 0.67 | 0.00 | +0.67 | 1 of 3 | 3 | 0 |
| `gate-typo` | 1.00 | 0.00 | +1.00 | 3 of 3 | 3 | 0 |
| `review-scope` | 1.00 | 1.00 | +0.00 | 3 of 3 | 3 | 0 |
| `small-behavior-change` | 1.00 | 0.50 | +0.50 | 3 of 3 | 3 | 0 |

**Sonnet 5** (`--model claude-sonnet-5`). 8 cases, 24 runs with the plugin and as many without, 1408 s, Claude Code 2.1.278: suite score 1.00, 8 of 8 cases at the 1.0 threshold, mean Δ +0.56:

| Case | With | Without | Δ | Expected skill fired | Runs per arm | Runs with an error |
| --- | --- | --- | --- | --- | --- | --- |
| `approved-spec` | 1.00 | 0.50 | +0.50 | 1 of 3 | 3 | 2 |
| `concurrency-bug` | 1.00 | 0.50 | +0.50 | 3 of 3 | 3 | 0 |
| `cosmetic-edit` | 1.00 | 0.50 | +0.50 | 3 of 3 | 3 | 0 |
| `failing-check-honesty` | 1.00 | 0.50 | +0.50 | 1 of 3 | 3 | 0 |
| `gate-pressured-change` | 1.00 | 0.00 | +1.00 | 2 of 3 | 3 | 0 |
| `gate-typo` | 1.00 | 0.00 | +1.00 | 3 of 3 | 3 | 0 |
| `review-scope` | 1.00 | 1.00 | +0.00 | 3 of 3 | 3 | 0 |
| `small-behavior-change` | 1.00 | 0.50 | +0.50 | 3 of 3 | 3 | 0 |

**Reading the two passes.** *With* and *Without* are the mean run scores over the scored graders (the gate contract: no editor call before the first Skill call, no refusal in a routing scenario, the declaration before the change in a gate scenario); `Δ` is their difference; *Expected skill fired* is the unscored plugin-fired indicator, the count of with-arm runs in which the scenario's expected skill was invoked at least once, the nearest thing here to the harness's "matched" column and weaker than it (the harness's verdict is the *first* committing call). Both models kept the gate contract in every scored routing run (`With` 1.00 in seven of eight cases for Opus, eight of eight for Sonnet) while the baseline edited first in half its routing runs and in every `gate-typo` and `gate-pressured-change` run; `review-scope`'s Δ is 0 because its prompt says not to change code and neither arm did.

The indicator column is where the two environments part. `approved-spec` fired `to-tickets` in 0 of 3 Opus runs and 1 of 3 Sonnet runs here, against 7 of 10 in the harness's records; `failing-check-honesty` fired `grill` in 1 of 3 Sonnet runs against 5 of 5; `gate-pressured-change` fired `grill` in 1 of 3 Opus runs against 9 of 9. An eval run is not the harness's run: it starts with `--permission-mode dontAsk` and `--max-turns 15`, has no shell (so the fixture's checks cannot be run), loads only this plugin and the skills the scaffold provided, and lets the model continue past the point where the harness stops. In those runs the model still declared before it changed anything (the scored contract), but more often declared `implement` or `grill` than the row the bootstrap names, and, with nobody to answer, went on to edit after the grill's question. These are the eval's findings about routing under its conditions, recorded as such; the harness's records above, made under `acceptEdits` with a shell and the developer's full config, remain the routing evidence the README's table cites, and the difference between the two is itself worth knowing before tuning any wording. Two Sonnet `approved-spec` with-arm runs hit the 15-turn cap while writing tickets and were graded on what they had produced.

The local reports (`report.html` beside each `aggregate-result.json`) are under `tests/runs/evals/{opus,opus-gpc,sonnet}/`, gitignored; a run started from a Claude Code session keeps its report local, and `--publish-report` from a terminal publishes one as a private artifact.

## 3.2: `/pr-review`, one live batch on real pull requests, 2026-09-23

The skill's deterministic parts are unit-tested through their command lines (`scripts/tests/test_pr_review.py`: the check runner's verdicts, timeouts and flake re-runs; the review builder's diff parsing, anchoring, suggestion blocks and event rules; the batch report's three answers and author notes), its text by `scripts/tests/test_plugin.sh` (every step, in order, with the promise each keeps inside it), and the gate's bare-name declaration by the gate module's tests and the hook suite. This section is the one live run: the skill doing the whole job, once, on real pull requests.

**The setup.** Two throwaway pull requests on `gabriel-tutor/seams`, opened for the test and closed after it: #4, "Gate: longer go-aheads keep the request", which drops `rm` from the gate's file commands (breaking its tests) and raises the go-ahead bound from 40 to 400 characters (breaking none), and #5, a README line on uninstalling. The skill ran headless from a fresh clone: `claude -p "/matt-pocock-workflow:pr-review 4 5"` with `--plugin-dir` at `21d369d` (the plugin with the skill), the installed copy disabled, Claude Code 2.1.280, the runtime reporting `claude-opus-5-5[1m]`. Writing to GitHub was impossible by construction: `gh` and `git` shims first on `PATH` refused every non-GET `gh api` call, `gh pr review/comment/merge/close/edit/ready` and `git push`, logging every call, with deny rules on top.

**What it did.** It pinned both heads, created the four worktrees one pull request at a time, each pair under a marked evidence folder, and fanned out one subagent per pull request. Each ran the command CI runs (`scripts/test.sh`) on the baseline and the head through `run_checks.py`: #4 `test` passed on the baseline and failed on the head twice, **broken by the PR**; #5 `test` ok on both. Findings for #4: blocking, the `rm` removal lets `rm -rf src`, `find -exec rm` and `xargs rm` past the gate without a declaration, proven by a probe test on both trees; blocking, the 400 bound does not fix the pull request's own example (`is_continuation("yes, go ahead with the plan you described above")` is False on both trees, reproduced), a defect in the change's premise that no test in the repository would have caught; should fix, the spec still says 40 characters, placed in the body because the spec is outside the diff. For #5: two nits, one a multi-line suggestion checked to cover exactly the lines it replaces, and the new `claude plugin uninstall` command tried with `--help`. The handover opened with the batch table, #4 **changes needed** (2 blocking, `test` broken) and #5 ready to merge, and a note for the author, then asked which reviews to post, naming each pull request, head and event (`COMMENT` only, the viewer having written both).

**The findings were steered.** The prompt the main session gave PR #4's subagent summarized the diff ("removes 'rm' from FILE_COMMANDS; changes is_continuation length bound from 40 to 400") and suggested the probe ("probe that `rm somefile` is no longer seen as a file-changing command"), and PR #5's asked whether the new line's placement read right. So the run shows that the subagents proved and wrote up what they were pointed at, and went past it (the reproduction that the pull request's own example still fails was theirs), not that they found the defects unaided. The skill now forbids it: a subagent gets facts only, never a summary of the diff or a hint about what to look for.

**What it did not do.** 39 shell commands, 26 of them by the subagents: zero attempts to write to GitHub or push (not zero blocked: zero attempted). The clone's `git status` and `git worktree list` afterwards were identical to the record taken before; its four worktrees were removed; the evidence stayed in the temp directory. GitHub showed no review on either pull request until the answer.

**The post, on the user's yes.** The session was resumed with the answer ("post both, as COMMENT") and a shim allowing exactly those two review posts. It re-checked both heads, posted one review per pull request, and read the inline comments back. On GitHub (read through the API afterwards): #4's review at `cd11698` with inline comments on `plugin/hooks/seams_gate.py` 26-27 and 306, each with a suggestion block, and the body carrying the verdict, the counts, the checks table, the spec finding under *Outside the diff* and *Not verified*; #5's at `deb9909` with the 218-220 suggestion and the 218 note. Every anchor was where `review_payload.py` put it; GitHub rejected nothing.

**Manual only, enforced by the platform.** A separate headless session asked to invoke `matt-pocock-workflow:pr-review` with the Skill tool got `Skill matt-pocock-workflow:pr-review cannot be used with Skill tool due to disable-model-invocation. Ask the user to run /matt-pocock-workflow:pr-review themselves ... Do not replicate this skill's workflow by other means`, and the skill was absent from the list the model sees.

**Seen, and not hidden.** The first checkout loop split a pull request number and its SHA wrongly under zsh, created one misnamed directory, noticed, removed it (it had just created it) and retried. Each pull request's `before.txt` was taken after the previous one's worktrees existed, so the skill's own comparison would have reported a difference; the run worked around it by comparing only the main worktree's lines (the skill now takes one record before the first checkout). The handover paraphrased the batch report's author note instead of printing it verbatim as the skill asks; the table itself matched. The main session ran in four turns (119, 12, 72 and 82 seconds), woken between them by its background subagents; the done-check blocked three times inside those turns, on its writes under the temp directory; the whole run took about 7.7 minutes of wall clock (14:29:25 to 14:37:09 UTC).

**Not exercised live.** The single-review path (Matt Pocock's `code-review` through the Skill tool beside the parallel risk reviewer; only the batch path ran), the bare `/pr-review` form (the run typed the namespaced one; the gate's rule for it is unit- and hook-tested), AskUserQuestion (a headless run has none, so every question arrived as text), an untrusted pull request (both were the viewer's own), an app that has to be started for its end-to-end suite (this repository has none), a batch over four pull requests, and every model but the one above. The run was made on `21d369d`; the review that followed changed the three scripts (line splitting, quoting, process cleanup, the approve rules, unreadable reviews) and the skill's text (checkout records, facts-only subagents, static review running nothing), each change unit- or static-tested, none of them re-run live. One batch of two is evidence about that batch.

## 3.2: `/pr-review`, a second live round, 2026-09-23

After the review that followed round 1, the scripts and the skill's text had changed and none of the changes had run live; round 1 had also left the single review and the bare `/pr-review` unrun, and it had steered its subagents. This round ran both paths, each on that day's candidate, on the same two changes opened again as #6 and #7 (heads `cd11698` and `deb9909`, baseline `aea109b`). Each run started headless from a fresh clone with round 1's setup: `--plugin-dir` at the candidate, the installed copy and Superpowers disabled, Claude Code 2.1.280, the runtime reporting `claude-opus-5-5[1m]`, `gh` and `git` shims refusing every write to GitHub, and deny rules on top. Nothing was posted in this round. Both pull requests were closed and their branches deleted after the second run.

**Run 1: one pull request, bare name, on `d874905`.** The command was `claude -p "/pr-review 6"`, and the gate took the bare name as the declaration (no refusal in the run). It ran `scripts/test.sh` on both trees through `run_checks.py`: 9 of 9 suites on the baseline, 7 of 9 on the head twice, **broken by the PR** (six cases of `test_gate.ClassifyCommand` fail on both Pythons). Then, all in the background, it invoked Matt Pocock's `code-review` through the Skill tool, with the merge-base as the fixed point and the pull request's body as the spec, and ran the risk reviewer beside `code-review`'s Standards and Spec reviewers.
- **The risk reviewer's prompt** named the trees, the diff command, the risky file and the axes, and said nothing about what was wrong. It found the `rm` removal and proved it with probes on both trees: `rm -rf dist`, `sudo rm`, `xargs rm` and `find -exec rm` are labeled on the baseline and unseen on the head. With no declaration, the head's gate allows `rm -rf src` and still refuses `touch src/x`.
- **The Spec reviewer**, given the body alone, found both defects. The pull request's own example, `is_continuation("yes, go ahead with the plan you described above")`, is False on both trees, because the length was never what rejected it.
- **The review:** request changes, with one blocking finding (the `rm` removal, with a suggestion block restoring it), two should fix (the example still fails; the 400 bound comes with no test and contradicts its docstring), and three lines under not verified.

One turn of 443 seconds, 35 shell commands (15 by the subagents), zero write attempts. The clone's status and worktree list were identical before and after, and GitHub showed no review on #6.

**What run 1 found in Seams.** Three things, fixed in `8c0e487` before run 2:
- **An empty suggestion block.** The first should-fix finding (the example still fails) carried `"suggestion": ""`, and `review_payload.py` drafted an empty suggestion block from it. On GitHub, committing an empty suggestion deletes the line it sits on, so posted, it would have offered the author a button that deletes line 306. An empty or blank suggestion is now no suggestion (unit-tested), and the skill says a deletion is proposed in words.
- **A pointer in a prompt.** The Standards reviewer's prompt, which the main session writes for `code-review`, listed "the comment above FILE_COMMANDS and above GO_PHRASES" among the standards sources. Those are the two places the defects were. It was a pointer rather than a summary, but still a pointer. `code-review`'s reviewers now get facts, not conclusions, as the risk reviewer and the batch subagents already did.
- **No post question.** Without AskUserQuestion, it said it could not ask whether to post and stopped there. Now it asks the question in text, with its options, and ends the turn.

**Run 2: a batch, facts only, on `8c0e487`.** The command was `claude -p "/matt-pocock-workflow:pr-review 6 7"`: one subagent per pull request, in the background. Each prompt held the pull request's facts (number, title, body, author, head, baseline, GitHub's check results, its trees and evidence folder) and the instruction to carry out the skill's sections. The only words about the change in either prompt were the pull request's own title, body and commit message.
- **Checks:** #6 `test` passed on the baseline and failed on the head twice, **broken by the PR**. #7 `test` was ok on both.
- **#6: request changes.** Two blocking findings: the `rm` removal at line 26, with a suggestion block restoring it, and the raised bound, which does not fix the reported case, at 306. One should fix, no test for the continuation change, and one question, why 400.
- **#7: approve.** One should fix: "Remove it entirely" leaves the marketplace behind. The subagent proved it by running the README's commands in a throwaway Claude config inside the evidence folder (`CLAUDE_CONFIG_DIR`); after the uninstall, `claude plugin marketplace list` still listed the marketplace. One nit, on "Instead". The user's own Claude config was not touched: its plugin files were last written before the run, and its marketplace list is unchanged.
- **The handover** opened with `batch_report.py`'s report exactly as the script prints it; compared after the run, the text is identical. #6 was **changes needed** (2 blocking, `test` broken) and #7 ready to merge, with a note for the author. Then it asked in text which reviews to post: A, #6 at `cd11698` as `COMMENT`; B, #7 at `deb9909` as `COMMENT`; C, both; D, neither.
- **Stale outputs:** run 1 had left #6's evidence folder at the same head, and run 2 cleared it: every file in it was written during run 2.

Two turns (135 and 134 seconds), 15:55:13 to 16:01:48 UTC, 41 shell commands (27 by the subagents), zero write attempts. The clone's status and worktree list were identical before and after, and neither pull request had a review or a comment when the run ended.

**Seen, and not hidden.**
- **Severity varied.** The example that still fails got two severities: should fix in run 1 and blocking in run 2. The skill calls a proven bug blocking; whether a fix that does not fix is one is a judgement, and it was made both ways. The verdict was request changes both times, on the `rm` removal alone.
- **The done-check blocked twice in run 2**, on a `mkdir` and on a redirect under the temp directory, as in round 1. Each time the run invoked `verification-before-completion` and went on.
- **The shim log's one refused call** is the smoke test of the shim itself, 13 seconds before run 1 began.

**Not exercised live.**
- AskUserQuestion: the runs were headless, so every question arrived as text.
- An untrusted pull request and a static review: both pull requests were the viewer's own.
- An app that has to be started for its end-to-end suite.
- A batch over four pull requests.
- The other argument forms: a URL, `owner/repo#number`, `open` and `requested`. On 2026-09-24 their `gh` lookups ran read-only on this repository: both lists exit 0 (empty, as no pull request was open), and the URL resolves. The skill never ran end to end on them.
- A re-review after the author pushes.
- A post since round 1. The payload's one change since then, the empty suggestion, is unit-tested.
- Every model but the one above.

Two runs are evidence about those two runs.

## 3.2.1: the first real batch, 2026-09-23

The user ran 3.2.0's `/pr-review` on 15 open pull requests of a private repository, in one interactive session (Claude Code 2.1.280), and passed on the session's own list of six gaps. The facts below come from that session's transcript and the gate's ledger, read by a read-only subagent and spot-checked here. They name no repository, pull request or code: the repository is someone else's.

- **What worked.**
  - The run pinned each head and ran the checks on both trees.
  - It tried each change in the running app, and put probes behind its claims.
  - Every inline comment anchored.
  - It asked before posting: the user ticked all 15.
- **The gate, which the session reported as "doesn't recognise pr-review".** It did recognise it. The user named `/matt-pocock-workflow:pr-review` mid-sentence, the model then started the skill itself (the platform allowed that once the user had named it), and that call declared the request. What closed the gate was new requests:
  - There were 25 refusals: 3 in the main session and 22 in subagents. Every one was a shell write under `/private/tmp` or to `/dev/null`.
  - 21 of them followed a subagent's hand-back ("Another Claude session sent a message: …"), which the prompt hook did not know as a notice. The other 4 followed the user's own messages.
  - To get through, the session declared `trivial` 28 times, each time claiming the work was trivial. It also told every reviewer to do the same.
  - The hand-back reset reproduced in the session that built the fix: the forensics subagent's own hand-back dropped that session's declarations at the second it arrived.
- **Old bash.**
  - CI runs its tests under `shell: bash` with `shopt -s globstar` and a `tests/**/*.test.js` glob.
  - `run_checks.py` ran it with macOS's `/bin/bash` 3.2, which rejects globstar and carries on. So `**` walked one directory: 799 of 998 test files and 7,226 of 9,220 tests, with a pass or fail reported as if whole.
  - The repository's CI jobs had not started, so nothing could compare. The session switched to `find`, with a floor of 900 files.
- **A check only a git hook runs.**
  - A package-script audit runs from the pre-commit hook, and no CI job runs it. 1 reviewer of 15 found it, by listing the package scripts.
  - The main session later ran it on the other 14: every baseline passed and every candidate failed, and four verdicts flipped to request changes.
  - It added those results with a script that edited the finished reviews.
- **Probes in the checked trees.** Two reviewers left probe tests in `tests/`, and the audit counted them: 985 files against 983 committed, and 1,000 against 999.
- **A missing test file.** A check aimed at a pull request's new test file failed on the baseline, where the file does not exist. It read "fixed by the PR" until the reviewer wrapped the command by hand.
- **Concurrency.**
  - Four reviewers ran at a time until the user asked for more; then 13 ran at once, with test workers halved.
  - The load average reached 53.5 on 14 cores, and two Postgres verdicts were relabelled flaky by hand.
- **Posting.**
  - The reviews went out back to back: 10 posted in 34 seconds.
  - GitHub then refused the next five with HTTP 403, "You have exceeded a secondary rate limit and have been temporarily blocked from content creation", with no retry-after.
  - None of the refused posts created a review. Waiting 120 seconds and then posting 45 seconds apart got all five through.

Each gap has its fix in 3.2.1 (see the CHANGELOG), tested through the scripts' command lines, the gate module and the hooks, and the skill text's static checks.

### The 3.2.1 live batch, 2026-09-24

**The setup.**
- **The base:** a throwaway branch off `main` (`aea109b`) with two checks that the first batch had tripped on. One is a docs audit only a git hook runs (`.husky/pre-commit` → `scripts/docs-audit.sh`, comparing a documented skill count with `plugin/skills/`). The other is a CI step that needs globstar (`shopt -s globstar; files=(plugin/**/SKILL.md)`).
- **Three pull requests against it:**
  - #8 changes the documented count (only the hook's audit can catch it);
  - #9 changes one README word;
  - #10 drops "continue" from the gate's go-aheads, which breaks a unit test.
- **The run:** `claude -p "/matt-pocock-workflow:pr-review 8 9 10, 1 check slot"`, headless, from a fresh clone.
  - `--plugin-dir` at `cbefcee`, with the installed copy and Superpowers off.
  - Claude Code 2.1.281, the runtime reporting `claude-opus-5-5[1m]`.
  - `gh` and `git` shims refusing every write to GitHub.

The pull requests were closed and their branches deleted afterwards.

**What it did.**
- **The first turn** (84 s) made the six worktrees one pull request at a time and found the checks once: `test` (CI), `skills` (the globstar step) and `docs-audit` (from the hook). It then asked, in text, whether to `brew install bash` first, since `skills` needs bash 4 and this Mac has only 3.2.57. The answer was "2" (don't install).
- **The reviewers:** all three started together (22:46:29, :39 and :48 UTC), each given the same checks list. Their checks took turns through the one slot (`--slots 1`).
- **The verdicts:**
  - #8: request changes. `docs-audit` was broken by the PR, which nothing else would have shown, since CI does not run it.
  - #9: approve, with one nit.
  - #10: request changes. `test` was broken by the PR (the unit test still lists "continue"); there were also two should-fix findings and a question.
- **`skills`:** it read "could not run: needs bash 4 or newer (globstar); ran with bash 3.2.57" on all three, never a pass or a fail.
- **After the batch:** the two broken checks ran again alone (`--recheck`) and failed again, so neither was flaky.
- **The handover:** it asked in text which reviews to post, with four options. Nothing was posted.

**What it did not do.**
- 41 shell commands (28 by the subagents), with 0 gate refusals and 0 `trivial` declarations. The first batch had 25 and 28.
- 0 write attempts in the shim log.
- The clone's status and worktree list were identical before and after, every evidence folder's record of files checks left was empty, and GitHub showed no review on #8, #9 or #10.
- The done-check blocked once, on a `mkdir` in the model's checkout loop: that path was built from a loop variable, which the gate cannot place. The request was declared, so the write was allowed and only counted.
- The run took 22:42:59 to 22:52:03 UTC, including the wait for the answer, in turns of 84, 38, 2, 4 and 82 seconds.

**What the review of 3.2.1 found first.** Two parallel reviewers (Standards, Spec) and an adversarial hunt of the gate's new exemption ran on `f6623cf`.
- The hunt confirmed a new bypass by running it: `find <temp> -exec … <project file>`, because the exemption had trusted find's roots.
- The reviewers found:
  - `${UNKNOWN:-/tmp/x}`, placed at its default;
  - option-attached targets;
  - `worktree add` without `--detach`;
  - a newline right before a redirect;
  - rebound loop variables;
  - the config directory treated as scratch;
  - two script defects.
- The hand-back fix itself did not work live. It matched the transcript's form, and logging the prompt hook's own input showed the hook gets `<agent-message from="…">`. That session lost its declaration to every reviewer's hand-back until the fix; afterwards a test hand-back left it intact.
- All of these were fixed with tests in `cbefcee`.
- A second adversarial pass on `cbefcee` could not run: a safety classifier stopped the subagent. So the new code paths were reviewed by hand, and `bf2aa58` closed what that found, each with a test:
  - a command inside `$(…)` or backquotes;
  - an unquoted heredoc's `$(…)`;
  - word splitting, `IFS`, brace expansion and `+=`;
  - `eval`;
  - `\rm`.

**Not exercised live.**
- A probe file: the reviewers probed with direct function calls, so the probe folder and cleanup's leftover report never ran.
- A check that leaves files behind: `left.json` stayed empty.
- Posting, whose pacing and retries are tested only against a fake `gh`. GitHub's limit cannot be tripped on purpose without risking a ban.
- AskUserQuestion, a pull request from outside the team, and a static review.
- The gate as of `bf2aa58`, which came after the run and is unit- and hook-tested.
- Every model but the one above.


## 3.3, ticket 04: a grill resumed from its progress file, 2026-09-25

Ticket 04 added three things:
- **The progress file,** `.scratch/<feature>/progress.md`, in the format `plugin/skills/using-matt-pocock-skills/references/progress-file.md` fixes.
- **The resume note** that the session-start hook builds from it at startup, resume, `/clear`, compaction and fork.
- **The grill's side:** it keeps the file, resumes from it, and asks every independent question at once.

`scripts/test.sh` is the deterministic proof: the hook suite's cases for each source, the size caps, the planted file. What follows is the live evidence. It ran on candidate `4f20cb6`, the plugin as reviewed. The commit after it, `78f928c`, changes only the harness and the case's `expect.json`, no skill or hook. Setup: Claude Code 2.1.282, macOS 15.8, and `claude -p` runs that report `claude-opus-5-5[1m]`.

**The scenario, `resume-grill`.**
- **The fixture:** OrderKit, set up for Seams (a local-markdown issue tracker), with an uncommitted `.scratch/gift-cards/progress.md` from a grill stopped halfway.
- **The file records** three settled decisions and two open questions:
  - does the gift card apply before or after the tier discount?
  - what happens to an amount held for a checkout that fails out of stock?
- **The prompt names no feature:** "Let's continue where we left off."
- **The expectation:**
  - the first skill is `matt-pocock-workflow:grill`;
  - the run reads the progress file;
  - its reply takes up both open questions;
  - nothing is refused.

**The routing harness:** `python3 scripts/behavior_test.py run --scenario resume-grill --arm plugin --assert`, three runs.
- **The first judgement was 2 of 3.**
  - Run 1 read the progress file with `cat` inside one shell command. The `reads` expectation counted only Read calls, with a pattern anchored at the end of a path.
  - The run itself did what the case asks.
  - `78f928c` makes the harness count a read-only shell command that names the file, with a test.
- **The three saved streams were re-scanned** with it, and nothing was re-run. `report` on those records gives:

Candidate: `4f20cb6`; model: `claude-opus-5-5[1m]`; 3 runs.

| Scenario | Expected first skill | Runs | Matched | Refused | Failed calls | Errors |
| --- | --- | --- | --- | --- | --- | --- |
| `resume-grill` | `matt-pocock-workflow:grill` | 3 | 3 | 0 | 0 | 0 |

What all three runs did:
- They invoked the grill first, re-read the progress file, the code and the git state, and opened by saying the settled decisions stand.
- They reported two mismatches found in the code as facts: the glossary's Reservation means stock, and `Inventory` has no `release`.
- They asked both open questions in one round, and asked no settled decision again. Two of the three also asked a third, independent question (a glossary term), which is the grill's new pace.
- They made 0 refusals and 0 failed calls, in 31 to 40 seconds each.

**Compaction, headless.** One session in a fresh copy of the same fixture, run as four `claude -p` calls with the harness's settings and `--plugin-dir plugin`, streams kept under `tests/runs/ticket-04/compact/`:
1. **`claude -p "Let's continue where we left off."`**
   - The hook's note named gift-cards at stage designing.
   - The grill resumed and asked both open questions.
2. **`claude -p --resume <id> "The gift card applies after the tier discount. I haven't decided the out-of-stock question yet, so keep it open."`**
   - The hook ran again with source `resume`, and the note came with it.
   - A typed answer starts a new gate request, so the grill was invoked again before the update, and nothing was refused.
   - The progress file gained decision 4 and a new `Next`, and `CONTEXT.md` gained a Gift card entry.
   - The out-of-stock question stayed open, as asked.
   - The next question, whether two checkouts can spend the same card at once, came alone, as a security question.
3. **`claude -p --resume <id> "/compact"`**
   - A manual compaction, from 57,970 to 10,745 tokens.
   - The hook ran with source `compact` and re-injected the note with the file's updated `Next`.
   - The notice reached the stream as "SessionStart:compact says: Seams: resuming gift-cards (designing): Ask the concurrent-redemption (double-spend) question alone; the out-of-stock hold stays open until the user decides."
4. **`claude -p --resume <id> "Let's continue."`**
   - The grill was invoked again and the git state re-checked.
   - The reply said decisions 1 to 4 are settled, asked the pending double-spend question, and kept the out-of-stock question open. It did not start over.
   - It did not re-read the progress file itself: what the compaction kept was enough, and the file had not changed since step 2.

The four calls cost $0.35, $0.51, $0.59 and $0.96.

**`claude plugin eval`:** `claude plugin eval plugin --case resume-grill --scaffold --runs 1 --trust-plugin`, one run with the plugin and one without. It took 53 s and cost $0.29, judge included. The result document does not name the model; no `--model` was given.

| Case | With | Without | Δ | Expected skill fired | Runs per arm | Runs with an error |
| --- | --- | --- | --- | --- | --- | --- |
| `resume-grill` | 1.00 | 1.00 | +0.00 | 1 of 1 | 1 | 0 |

- **Graders:** every scored grader passed in both arms: `asks-open-questions`, `continues-not-restarts` (the judge: PASS, PASS, PASS), `no-refusal` and `read-progress`.
- **Why Δ is 0:** the baseline had no resume note. It looked around, found the only progress file under `.scratch/`, and continued from it as well ("Picking up the gift-cards design from `.scratch/gift-cards/progress.md`").
- **What this case shows:** the resume works with the plugin. It does not show that the note was needed, since the workspace has one feature and nothing else in `.scratch/`.
- **Not run:** a case with several features there (one done, one stale, the unfinished one not the most visible) would test that the note points at the right one.

**Not exercised live.**
- AskUserQuestion: headless runs have none, so every question came as text.
- `/clear` itself: a fresh `claude -p` session stands for it.
- A fork.
- A note listing more than one feature.
- Any model but the one above.

## 3.3, ticket 05: a ticket resumed from its progress file, 2026-09-25

Ticket 05 made the flow skills keep the progress file:
- **`to-spec` and `to-tickets`** record the spec and the ticket list, and commit them by name after their yes.
- **`implement`** records the ticket in progress, the candidate under review and the review's findings. It closes each ticket with a record commit that the definition of done then runs on, and it resumes a ticket without its gate question when the file and git agree.
- **`finishing-a-development-branch`**, now adapted from its Superpowers copy, records integration. **`release`** sets done.
- **The resume note** names a ticket in progress and says that `implement` continues it.

`scripts/test.sh` is the deterministic proof: each skill's wording and size, the adapted copy's checksum, the note's ticket field, and the fixture's state and its note. What follows is the live evidence. The harness and the headless run used candidate `9e14539`, and the eval used `c56a84f`. Their `plugin/skills` and `plugin/hooks` are identical: `c56a84f` changes only the case's expectation, its grader and a harness test. `efebcf4`, after them, rewords `implement` from what the headless run showed (below); the static test covers those changes, and no live run has. Setup: Claude Code 2.1.282, macOS 15.8, and `claude -p` runs that report `claude-opus-5-5[1m]`.

**The scenario, `resume-ticket`.**
- **The fixture:** OrderKit with the coupons spec and two tickets on `main`. Ticket 01 is done and recorded. Ticket 02 (FLAT5 and case-insensitive codes) is committed and reviewed.
- **The finding:** the review found that FLAT5's minimum is checked against the tier-discounted total, not the subtotal. Only the uncommitted progress file records it, with its example: 20 units at 102 cents should give 1438.
- **A second feature:** an older gift-cards grill is unfinished too, so the note lists two features.
- **The prompt names nothing:** "Let's continue where we left off."
- **The expectation:**
  - the first skill is `matt-pocock-workflow:implement`;
  - the run re-reads the progress file, the ticket, the spec and the git state;
  - its reply names the finding and the subtotal;
  - it goes on to a change instead of stopping to ask;
  - nothing is refused.

**The routing harness:** `python3 scripts/behavior_test.py run --scenario resume-ticket --arm plugin --assert`, three runs.
- **The first judgement was 0 of 3, and the runs were right.** The reply pattern asked for "ticket 02" or "FLAT5" and for the finding's own words. The runs named the finding in the code's terms, "post-tier" and "subtotal", which the ticket and the spec use too.
- **Only "finding" separates them.** A run that continues is the only kind that can say there is a finding before its first edit. `c56a84f` asks for "finding" and "subtotal", and a unit test keeps a restart in the ticket's own words a miss.
- **The three saved streams were re-judged, and nothing was re-run.** `report` on those records gives:

Candidate: `9e14539`; model: `claude-opus-5-5[1m]`; 3 runs.

| Scenario | Expected first skill | Runs | Matched | Refused | Failed calls | Errors |
| --- | --- | --- | --- | --- | --- | --- |
| `resume-ticket` | `matt-pocock-workflow:implement` | 3 | 3 | 0 | 0 | 0 |

What all three runs did, in 20 to 21 seconds each:
- They invoked `implement`, then read the progress file, the ticket, the spec and the code. For the git state they ran `git status`, `git log`, `git branch --show-current` and `git diff`.
- They said the state matched: "State matches the progress file (main, HEAD = candidate 7847345, review finding recorded). Continuing from the fix."
- They asked no gate question. They checked the finding against the code ("The finding holds: `applyCoupon` compares `total` (post-tier) to 2000, while spec criterion 2 says the subtotal") and invoked `tdd`.
- Each run's first edit was the failing test the finding calls for: `applyCoupon(cart(20, 102), "FLAT5")` expecting 1438.

**Headless: a fresh session, compaction, and a planted mismatch.** One session in a fresh copy of the fixture, run as four `claude -p` calls with the harness's settings (plus `git rev-parse`, `show`, `branch` and `merge-base`) and `--plugin-dir plugin`. The streams are under `tests/runs/ticket-05/headless/`.
1. **`claude -p "Let's continue where we left off. Stop once the fix is committed: I want to compact before the rest of the ticket."`**, a fresh session, as `/clear` leaves it.
   - The note named coupons with ticket 02 in progress.
   - The session invoked `implement` and re-read the state, then fixed the finding test first through `tdd`, ran the suite and the typecheck, and invoked `verification-before-completion`.
   - It committed the fix and the progress file by name (`6cda6a7`) and stopped.
   - It kept the reviewed commit as `Candidate` and said in `Next` that the fix sits on it: "a commit can't contain its own ID".
   - Then, outside the session, a commit the progress file does not mention: one README line (`cd287ed`).
2. **`claude -p --resume <id> "/compact"`**
   - A manual compaction, from 58,794 to 9,247 tokens.
   - The hook ran with source `compact` and re-injected the note, with the ticket.
   - The notice read "SessionStart:compact says: Seams: resuming coupons (integrated): On main: the review fix (FLAT5 minimum on the subtotal) is committed directly on 7847345; commit the ticket's record and run the definition of done."
3. **`claude -p --resume <id> "Let's continue."`**
   - `implement` was invoked again and the git state read.
   - The reply reported the mismatch and acted on nothing: "I haven't committed the ticket record or started the final checks, because the repo doesn't match the progress file." It named `cd287ed` as the commit the file doesn't mention, and asked how to go on, with three options.
4. **`claude -p --resume <id> "That README commit is mine and has nothing to do with the ticket. Carry on."`**
   - The typed answer started a new gate request. The model tried the progress file and its commit before invoking `implement` again, and the gate refused both; after the invocation both went through.
   - The record commit `53e8e68` set `Status: done` (ticket 02 was the last, and the spec has no Release section) and `Next` to "None".
   - The definition of done found 17 of 18 rows met. The unmet one: the fixture's own commit `7847345` gives no reason in its message. The run said so and asked before rewriting history, but it left the feature done.
   - The handover had its four sections.

The four calls cost $0.59, $0.66, $1.03 and $1.37. `efebcf4` acts on what this run showed:
- **The candidate** is now the commit under review, and a resume checks that the history after it holds only commits the file accounts for. That is what step 1 did; the old rule would have called its own fix a mismatch.
- **A typed answer** that continues the ticket now invokes `implement` again first, as the grill already does. Ticket 03's lapse hint generalizes this.
- **The rule to put the ticket back on an unmet row** now sits at the definition of done's table, where step 4 needed it.

**`claude plugin eval`.**
- **Twice it refused to start.** With `--allow-tools Bash`, and again with only `git log`, `status`, `diff` and `branch` granted, it stopped before any session and cost nothing: "the Docker … credential store on this machine holds a symbolic link inside it, so the Bash sandbox cannot reliably exclude it — a Bash-granting evaluation cannot run here".
- **The run was made without a shell:** `claude plugin eval plugin --case resume-ticket --scaffold --runs 1 --trust-plugin --no-publish`, one run with the plugin and one without, on `c56a84f`. It took 190 s and cost $0.88, judge included. The result document does not name the model.

| Case | With | Without | Δ | Expected skill fired | Runs per arm | Runs with an error |
| --- | --- | --- | --- | --- | --- | --- |
| `resume-ticket` | 0.86 | 0.86 | +0.00 | 1 of 1 | 1 | 0 |

- **Graders:** in both arms, `continues-the-ticket` (the judge: PASS, PASS, PASS), `takes-up-the-finding`, `read-progress`, `read-ticket`, `read-spec` and `no-refusal` passed.
- **`read-git-state` failed in both arms by construction:** it needs a Bash call, and none was granted. The eval printed a warning saying so. The case now lists Bash in its allowed tools, as the eval advised.
- **With the plugin,** the run checked the state without a shell ("it matches `.scratch/coupons/progress.md`. We're on `main` at `7465ab1` (the Candidate), and one review finding is open"). It confirmed the finding in the code and said it could not edit in this session.
- **Why Δ is 0:** without the plugin, the run found `coupons/progress.md` beside the older gift-cards file and laid out the same fix from it. Two features in `.scratch/` did not make the note necessary, as one had not in ticket 04.

**Not exercised live.**
- AskUserQuestion: headless runs have none, so every question came as text.
- `/clear` itself: a fresh `claude -p` session stands for it.
- `to-spec`, `to-tickets`, `finishing-a-development-branch` and `release` writing the file. The static test holds their wording.
- The wording `efebcf4` changed in `implement`.
- The eval with a shell, on a machine whose Bash sandbox starts.
- Any model but the one above.

## 3.3, ticket 02: every shell tool gated, the hooks in exec form, 2026-09-25

Ticket 02 closed the gate's two shell bypasses and its reproduced false positive:
- **The classifier reads a command as the shell does.** A hand-written tokenizer replaces `shlex`, whose non-POSIX mode opens no quote in the middle of a word: `x="$(awk '$1>0' f)"` had read as a redirect to a file.
  - Quotes may now open inside a word, and `$'…'` is a quote.
  - A command substitution keeps its own quotes and comments.
  - Operators split one by one. A `#` opens a comment only at a word's start, and a backslash-newline joins the lines.
  - What a command runs is found in the tokenizer's own words. An unquoted heredoc's text is searched only for what its substitutions run.
  - A quote that never closes falls back to the old split, which never misses an operator.
  - A word that joins quoted and bare parts expands part by part.
  - A command nested past 50 levels is refused as unreadable.
- **`Monitor`** watches go through the same classifier, scratch rule included. A WebSocket watch runs nothing.
- **`PowerShell`** is a change before a declaration unless it is `Get-Content`, `Get-ChildItem`, `Select-String`, or `git status`, `diff` or `log`, on its own with plain arguments. The refusal names the list.
- **`scratchpad_dir`** from the hook input is scratch beside the temp directories. The working directory never is.
- **Every hook entry is in exec form:** `python3` with the script's path in `args`.

`scripts/test.sh` is the deterministic proof: on `c227c61`, 9 of 9 with 0 skipped on Python 3.14.6 and 3.9.6, 166 unit tests each. The unit and hook suites also pass on 3.12.13, CI's version. The false-positive and bypass tables hold the reproduced case, and seven write shapes the old tokenizer missed: `true;>f`, `echo hi|>f`, `(>f)`, `curl …/a#top > f`, `echo $# > f`, `echo "$(echo ')' ; rm -rf src)"`, and `r\` + newline + `m -rf src`. The hook suite feeds the real hook `Monitor`, `PowerShell` and `scratchpad_dir` events. It also runs each `hooks.json` entry as Claude Code spawns it: no shell, from a plugin root whose path holds a space.

**Speed.** `classify_command` on this Mac, Python 3.14.6, before (`7ba5a98`) and after (`c227c61`), the median of three runs:

| Input | Before | After |
| --- | --- | --- |
| a 200 KB unquoted word | 397 ms | 24 ms |
| a 200 KB double-quoted string | 377 ms | 45 ms |
| a 1 MB quoted heredoc | 3 ms | 3 ms |
| a 2,000-line script | 45 ms | 39 ms |

The first cut of the tokenizer built each word a character at a time, which was quadratic: 4.4 s for 800 KB. The build keeps the pieces in a list and takes each run of ordinary characters with one regular expression, and 800 KB now takes 93 ms. Nesting is bounded too: an 84 KB command of 12,000 nested `$((` is refused in 0.9 s, where the build (`6faea1d`) took 17 s for 48 KB in the review's measurement.

**The review, and what it changed.** Matt Pocock's `code-review` (Standards and Spec) ran on the build, `6faea1d`, beside a correctness review that compared the old and new classifiers on a fuzz of 2,142 commands. Each lost verdict was run under bash and zsh to see whether the file was really written. They found writes the old gate had caught and the build missed, because a second scanner disagreed with the tokenizer:
- an apostrophe in a comment hid every later `$(…)`, as in `# Stash what's there` followed by `STASHED=$(git stash)`;
- an unquoted heredoc's text was tokenized, so an apostrophe in it swallowed the lines after the heredoc;
- `$'…'` was not a quote.

Also:
- a thousand nested `$((` crashed the hook, which then let the call through;
- a quoted `--output` passed PowerShell's list;
- `"$EVID"/log.txt` under the temp directory was refused.

`c227c61` fixes each, with the review's cases in the tables. The same fuzz on `c227c61`:
- no write that bash 5.3, zsh or bash 3.2 performs is missed;
- 60 verdicts were dropped, all of them syntax errors that none of the three runs;
- 378 write shapes are newly caught;
- none of the review's 49 realistic read-only commands is flagged.

**One live session.** In a throwaway git repository, `claude -p "Use the Bash tool to run exactly this command, once, and then stop: echo hi > probe.txt"` ran with `--plugin-dir plugin`, `--settings` switching off the installed copy and Superpowers, `--allowedTools "Bash(echo:*)"` so that only the gate could stop the write, and `--model haiku`. It ran on the working tree committed as `6faea1d`, whose `hooks.json` the review fixes left as they were, on Claude Code 2.1.282, reporting `claude-haiku-4-5-20251001`, for $0.057. The stream is under `tests/runs/ticket-02/headless/`. All five hooks ran in exec form:
- **SessionStart** exited 0, and its output carried the bootstrap.
- **PreToolUse** refused the first call: "Seams gate: a shell command (`a redirect to a file`) changes the project, and this request has no declaration yet".
- **PostToolUse** recorded the model's `matt-pocock-workflow:trivial` in the session's ledger. The second call passed the gate. Claude Code's own prompt for a redirect inside the working directory then stopped it, since nothing approves it headless.
- **Stop** delivered "Seams done-check: 1 unverified change to the project since the last verification". Claude Code labels a Stop block "Stop hook error", which is the presentation ticket 03 changes.
- **UserPromptSubmit** printed nothing, as it should, and no hook error was reported for it.

`probe.txt` was never written.

**Not exercised live.**
- A `Monitor` or `PowerShell` call: the hook suite feeds synthetic events, and the PowerShell tool is opt-in on macOS.
- A write under a real `scratchpad_dir`.
- Windows, where exec form needs `python3` to resolve to a real `python3.exe`.

## 3.3, ticket 03: typed skills from their expansion, the lapse hint, the done-check as feedback, 2026-09-25

Ticket 03 changed three things:
- **Typed skills declare from their expansion.** Claude Code's `UserPromptExpansion` event names the skill each typed command expanded to. The expansion hook keeps it under the prompt's `prompt_id`, and the prompt hook adopts it when that prompt starts its request; an expansion that arrives after the prompt hook declares that request directly. The prompt's own parse of its leading command decides only when no expansion arrived.
- **The lapse hint.** A typed message that starts a new request after a declared one gets context naming the declarations that lapsed: invoking one again continues that work (a skill only the user can type, the user types again), and new work needs its own route. The hint restores nothing. A message that types its own route gets none (decision 22).
- **The done-check** asks through `hookSpecificOutput.additionalContext` instead of `decision: block`.

**What Claude Code sends.** Captured on 2.1.282 by a hook that logged both prompt events' input. It cost nothing: the API endpoint pointed at a closed local port, so every run stopped before a model call. The interactive run was driven through `expect`.

| Typed | Mode | `UserPromptExpansion` events |
| --- | --- | --- |
| `/matt-pocock-workflow:grill add a coupon field` | `-p` | `matt-pocock-workflow:grill` (source `plugin`) |
| `/grill add coupons` | `-p` | `matt-pocock-workflow:grill` (`plugin`), the resolved name |
| `/pr-review 42` | `-p` | `matt-pocock-workflow:pr-review` (`plugin`); the event's own `prompt` reads `/matt-pocock-workflow:pr-review 42` |
| `/tdd add a test` | `-p` | `tdd` (`userSettings`) |
| `/grill /tdd fix the coupon` | `-p` | one, `matt-pocock-workflow:grill`, whose arguments are `/tdd fix the coupon` |
| `/grill /tdd fix the coupon` | interactive | two, `matt-pocock-workflow:grill` then `tdd`, each with the arguments `fix the coupon` |
| `/pdf /tdd fix the coupon` | `-p` | one, `pdf` (`userSettings`), whose arguments are `/tdd fix the coupon` |
| `/compact` | `-p` | none, and no `UserPromptSubmit` either |

- Every expansion ran before `UserPromptSubmit`, one after another about 35 ms apart, and a prompt's events all carried the same `prompt_id`. The submit's `prompt` is the text as typed. The hooks reference lists the two events the other way round, so the gate handles either order.
- In the installed copies, Matt Pocock's `implement`, `to-spec`, `to-tickets`, `grill-me`, `grill-with-docs`, `wayfinder`, `triage`, `handoff`, `ask-matt`, `improve-codebase-architecture`, `setup-matt-pocock-skills` and `setup-ts-deep-modules` carry `disable-model-invocation: true`, as Seams' `pr-review` does. Claude Code refuses a Skill call for them, so the hint names such a skill as one only the user can type.

**The two-step run** from the ticket's "How to verify" ran twice, each in a fresh `cosmetic-edit` fixture copy with the harness's settings, `--permission-mode acceptEdits`, `--plugin-dir plugin`, and the installed copy and Superpowers switched off. The first was on the build, `f32ec75`; the second on `0024a6c`, whose review fixes rewrote the prompt logic the run exercises. The streams are under `tests/runs/ticket-03/`.
1. **`claude -p '/trivial Fix the typo "recieve" in the comment in src/format.ts.'`**
   - The prompt's parse cannot read a bare model-invocable Seams name, so only the expansion could declare this request.
   - In both runs the first edit passed before any Skill call, with no refusal.
   - The ledger holds `matt-pocock-workflow:trivial` as the request's first declaration, ahead of the change.
2. **`claude -p --resume <id> 'The README title should be "OrderKit" too, one word; fix that as part of the same cleanup.'`**
   - The same session id, SessionStart with source `resume`, and the ledger kept.
   - The prompt hook's context, shown by `--include-hook-events`: "Seams: this message started a new request, so the previous request's declarations lapsed: `matt-pocock-workflow:trivial`, `matt-pocock-workflow:verification-before-completion`. The gate refuses the next change to the project until a process skill is invoked for this request. If this message continues that work, invoking the one it used again with the Skill tool restores the declaration; new work needs its own route."
   - The first call was `Skill: matt-pocock-workflow:trivial`, and the README edit after it passed.

| Candidate | Step | Model reported | Refused | First Skill call | First edit | Cost |
| --- | --- | --- | --- | --- | --- | --- |
| `f32ec75` | 1 | `claude-opus-5[1m]` | 0 | call 5 (verification) | call 4 | $0.52 |
| `f32ec75` | 2 | `claude-opus-5[1m]` | 0 | call 1 (`trivial`) | call 4 | $0.84 |
| `0024a6c` | 1 | `claude-opus-5-5[1m]` | 0 | call 4 (verification) | call 3 | $0.32 |
| `0024a6c` | 2 | `claude-opus-5-5[1m]` | 0 | call 1 (`trivial`) | call 3 | $0.45 |

Neither run named a model, and the two reported different defaults. No step needed the done-check: each verified on its own before finishing.

**The done-check as feedback.** One Haiku session on `f32ec75` in a throwaway repository, shaped like ticket 02's: `claude -p '/trivial Use the Bash tool to run exactly this command, once, and then stop: echo hi > probe.txt'` with `--allowedTools "Bash(echo:*)"`, for $0.068.
- The gate let the write through, declared by the typed skill. Claude Code's own headless permission prompt then denied it twice, and Claude stopped.
- The Stop hook answered with `hookSpecificOutput.additionalContext`: "Seams done-check: 2 unverified changes to the project since the last verification …". The turn went on into `verification-before-completion`, and the second stop ended it.
- The stream has no `stop-hook-error` notification, where ticket 02's had "Stop hook error occurred · ctrl+o to see". No `UserPromptSubmit` ran for the continuation, so the request kept its declarations.
- In the interactive session that built this ticket, which ran the working tree's hooks, the same request reached the model as "Stop hook additional context: Seams done-check: …".
- The stop hook and `decide_stop`'s logic are unchanged since `f32ec75`.

**The deterministic suites.** `scripts/test.sh` on `0024a6c`: 9 of 9 with 0 skipped on Python 3.14.6 and 3.9.6, 181 unit tests each. The unit and hook suites also pass on 3.12.13, CI's version. The unit tests feed the captured event shapes, in both hook orders. The hook suite drives the real executables through stacked and bare typed skills, the lapse hint, a skill only the user can type, a project's own `pr-review`, a late expansion and the done-check's feedback form, and runs the new `UserPromptExpansion` entry in exec form.

**The review, and what it changed.** Matt Pocock's `code-review` (Standards and Spec) ran beside a correctness and security review that drove the hooks with crafted events. On `f32ec75` they found:
- the hint sent Claude to a Skill call Claude Code refuses, for a skill only the user can type (Seams' `pr-review`, Matt Pocock's own `implement` and the rest);
- the prompt's parse declared a skill after an expansion had named something else: a project's own `pr-review`, another plugin's `code-review`, an MCP prompt;
- an expansion arriving after its prompt hook, the order the reference lists, declared nothing;
- a damaged list in the ledger made the prompt hook raise and keep the old request;
- the name filter let a trailing newline through;
- stale text on the ledger's contents and the done-check.

`0024a6c` fixes each, with the reviewers' cases as tests. The review's fuzz, re-run on `0024a6c`:
- 1,500 random sequences without expansions differ from `b40f571` only by the hint, with no crash;
- 2,000 with expansions crash nothing on Python 3.9.6;
- 4,000 more, 2,000 on each interpreter, match a restatement of the rules at every step (the declarations and the gate's decision). The same check finds 279 mismatches in 1,000 sequences on `f32ec75`.

**Not exercised live.**
- A stacked command through Seams' hooks in an interactive session: the capture used only a logging hook.
- A skill only the user can type, lapsing.
- An expansion arriving after its prompt hook, which 2.1.282 never does.
