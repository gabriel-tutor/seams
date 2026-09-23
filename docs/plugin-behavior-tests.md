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

**What it did not do.** 39 shell commands, 26 of them by the subagents: zero attempts to write to GitHub or push (not zero blocked: zero attempted). The clone's `git status` and `git worktree list` afterwards were identical to the record taken before; its four worktrees were removed; the evidence stayed in the temp directory. GitHub showed no review on either pull request until the answer.

**The post, on the user's yes.** The session was resumed with the answer ("post both, as COMMENT") and a shim allowing exactly those two review posts. It re-checked both heads, posted one review per pull request, and read the inline comments back. On GitHub (read through the API afterwards): #4's review at `cd11698` with inline comments on `plugin/hooks/seams_gate.py` 26-27 and 306, each with a suggestion block, and the body carrying the verdict, the counts, the checks table, the spec finding under *Outside the diff* and *Not verified*; #5's at `deb9909` with the 218-220 suggestion and the 218 note. Every anchor was where `review_payload.py` put it; GitHub rejected nothing.

**Manual only, enforced by the platform.** A separate headless session asked to invoke `matt-pocock-workflow:pr-review` with the Skill tool got `Skill matt-pocock-workflow:pr-review cannot be used with Skill tool due to disable-model-invocation. Ask the user to run /matt-pocock-workflow:pr-review themselves ... Do not replicate this skill's workflow by other means`, and the skill was absent from the list the model sees.

**Seen, and not hidden.** The first checkout loop split a pull request number and its SHA wrongly under zsh, created one misnamed directory, noticed, removed it (it had just created it) and retried. The handover paraphrased the batch report's author note instead of printing it verbatim as the skill asks; the table itself matched. The run woke four times (the fan-out, each subagent's finish, and a re-check the done-check asked for), 284 seconds in all.

**Not exercised live.** An untrusted pull request (both were the viewer's own, so the trust question never came up; the rule is in the text and the static guard), an app that has to be started for its end-to-end suite (this repository has none), a batch over four pull requests, and every model but the one above. One batch of two is evidence about that batch.

