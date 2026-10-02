# Plugin behavior tests

This file is the behavior evidence for the `matt-pocock-workflow` plugin, from the first 2.0 probes to 4.0, oldest section first. A section headed by a release holds the figures that release shipped on; the sections headed "3.3, ticket NN" hold what each of 3.3's tickets proved as it was built. The last section, [4.0.0: the proof](#400-the-proof), holds how 4.0.0 is compared with 3.4.0 before its release, and the results once they are run.

Until 4.0, all headless runs use `claude -p` with the Superpowers plugin disabled through `--settings` (each section names the Claude Code version and the model its runs used). Nothing in `~/.claude/settings.json` is changed. The 4.0.0 proof runs in throwaway homes and configuration directories instead (its section).

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

- **The verdict is confirmed by its result.** A committing call is a Skill or AskUserQuestion call, an Edit/Write inside the workspace, or a shell command that the gate's own classifier (then `plugin/hooks/seams_gate.py`, imported by the harness, so the two could not disagree; since 4.0 the classifier is `seams_shell.py`, and the harness is retired) labels a mutation. The call is the verdict once its result comes back (or once the model's next turn begins, which only happens after the results; Claude Code emits one event per content block, so a second call in the same message is not a next turn); a call the gate refused (an error result carrying the gate's reason, which starts with `Seams gate:`) or a change that failed changed nothing, so it is counted and the scan continues. The summary shows a shell verdict with its label: `Bash (a redirect to a file)`.
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

**The unit suite's intermittent failure, found.** The definition of done on the first record, `c57768e`, saw `scripts/test.sh` fail once on Python 3.14.6, in `test_pr_review`'s `test_a_limit_that_resets_far_off_is_not_waited_for`. Ticket 04 had seen this suite fail once in nine runs without catching which test failed.
- **Not reproduced by:** 60 runs of the test alone, 200 more eight at a time, and 8 full suite runs in parallel.
- **Reproduced every time by** starting the test in a minute's last second. Started at second 59.1 it failed ("'20:33' not found in … lifts at 20:34 …"); started at second 30 it passed.
- **The cause:** `delay()` waits a second past GitHub's primary-limit reset, and `post_reviews.py` printed the lift time as now plus that wait, so a reset at hh:mm:59 was reported as the next minute.
- **The fix, `f3a83bb`:** `delay()` also returns when the limit lifts, and the message prints that. The test now puts the reset at a minute's 59th second, so it failed every time on the old code; it passes on both interpreters.
- **Checked:** the unchanged test, started at second 59.1 against the fixed script, passes.

**Not exercised live.**
- A stacked command through Seams' hooks in an interactive session: the capture used only a logging hook.
- A skill only the user can type, lapsing.
- An expansion arriving after its prompt hook, which 2.1.282 never does.

## 3.3, ticket 06: pr-review under the cap, scripts without prompts, 2026-09-25

**What changed.** `pr-review`'s SKILL.md went from 26,046 bytes (about 8.8k tokens by `claude plugin details`) to a core of 10,850 bytes (about 3.4k). The core carries:
- the rules that hold for the whole review;
- a list naming each of six references with when to read it;
- the four scripts;
- the Gate, every step's heading with its gates and must-nots, severity, the verdict and the handover.

140 of 3.2.1's 154 body sentences appear word for word in the core or a reference. The ticket's comments account for the other 14, item by item.

**The deterministic suites.** `scripts/test.sh` passes 9 of 9 with 0 skipped, on Python 3.14.6 and 3.9.6. The static test's new checks each failed first:
- **The size bound:** failed on 3.2.1's 26,046-byte file.
- **The limits check:** failed on 3.2.1's claim that a subagent cannot start subagents.
- **The bytecode guard:** failed on a planted `.pyc`.
- **The other new checks:** failed before the text they require existed.

**The live runs.** Both ran headless from a fresh clone of `gabriel-tutor/seams` at `3a234bd`:
- **The command:** `claude -p "/matt-pocock-workflow:pr-review 7"`. PR #7 is the viewer's own closed one-line README change from 3.2's second round.
- **The plugin:** `--plugin-dir` pointed at the candidate's plugin folder (a `git archive` export), with the installed copy and Superpowers switched off.
- **Permissions:** `--permission-mode default`, because the user's own settings default to auto. `--settings` allowed git, `gh api`, a few read-only commands and writes under the run's temp directory, and nothing for `python3`, so only the skill's own `allowed-tools` could let its scripts through.
- **GitHub:** `gh` and `git` shims came first on `PATH` through `CLAUDE_ENV_FILE`, which Claude Code runs before every Bash command. They refused every write to GitHub and logged every call.
- **The version:** Claude Code 2.1.282; the runtime reported `claude-opus-5-5[1m]`.

The records are under `tests/runs/lean-06/`.

- **Run 1, on `8fbdca2`** ($2.39; 13:17:15 to 13:21:13 UTC):
  - In the turn that invoked the skill, `run_checks.py` ran twice with no denial: `--help`, then the check run with every path written out.
  - The model put that run and the risk reviewer in the background, and their notifications began two more turns. In the last one, `review_payload.py` and `gh pr view … --json headRefOid,state` were both refused ("This command requires approval"); the skill pre-approves both. So the `allowed-tools` grant ends with the turn that invoked the skill, and waiting on background work ends that turn, not only a typed message. That is `65c1388`'s fix.
  - The model never called `batch_report.py`, but its handover said the session had asked for approval to run it.
  - The review itself: `test` passed on both trees (26 s each). There were two should-fix findings on README line 218: "entirely" leaves the marketplace behind, and the uninstall path drops the step that re-enables Superpowers. There was also a nit. The verdict was comment, the only event on the viewer's own pull request.
  - Nothing reached GitHub: 36 shim calls, none refused, and #7 has no review. The clone's status and worktree list were the same after the run as before it.
- **Run 2, on `65c1388`:** ($2.30; 13:30:18 to 13:37:18 UTC):
  - The whole review stayed in the turn that invoked the skill: one init, one result, 47 model turns.
  - `run_checks.py` ran in the foreground (`test` passed on both trees, 27 s and 25 s), then `review_payload.py` twice, then `batch_report.py`. None was denied.
  - The handover opened with the batch report exactly as the script wrote it.
  - The risk reviewer ran in the foreground, beside `code-review`'s Standards and Spec reviewers.
  - All six denials came from the harness's settings, on other commands:
    - the model's two `${TMPDIR:-/tmp}` probes;
    - `printenv`;
    - its own `python3 -c` one-liner;
    - a compound `git config` read;
    - `claude plugin --help` while trying the change.
  - The review: comment (the only event on the viewer's own pull request), with 0 blocking, 2 should-fix, 1 nit and 1 question, the same two README gaps as run 1. The run then re-checked the head and asked in text whether to post: `COMMENT` or don't post.
  - It also found a bug in `review_payload.py` from 3.2.1: a suggestion is always wrapped in a three-backtick fence (lines 185–186 and 216), so a suggestion that holds its own fenced block ends early on GitHub. The run rewrote its own suggestion as one line. The bug is recorded as open in the ticket.
  - Nothing reached GitHub (39 shim calls, none refused; #7 still has no review), and the clone was the same afterwards.

**Not exercised live.**
- Posting, which after a typed answer (the headless form of the question) is outside the grant by design, as the core says.
- A batch, which ticket 07 runs live.
- An interactive session, where AskUserQuestion keeps the answer inside the turn.
- The `${TMPDIR:-/tmp}` expansions in 3.2.1's own Checkout wording, which default mode refuses ("Contains expansion"). Both runs worked around them with absolute paths. Ticket 10's pre-loaded facts are the place for the temp directory.

## 3.3, ticket 08: every skill under the bound, lighter always-on cost, 2026-09-25

**What changed.**
- **The static guard,** in `test_plugin.sh`, now checks five things:
  - every SKILL.md is at most 11,000 bytes;
  - no skill's or agent's frontmatter has `model` or `effort`;
  - the version is in `plugin.json` only;
  - the listing is at most 2,650 characters;
  - each Seams skill has its effort line.

  It runs on CI too: only manifest validation needs the `claude` CLI, which CI lacks.
- **Descriptions** lead with their trigger, and the workflow summaries are gone.
- **The bootstrap** is stated as the project's facts, with no `<EXTREMELY_IMPORTANT>` wrapper and no preamble, and it states the quality bar.
- **Effort:** the ten Seams skills read `${CLAUDE_EFFORT}` and say what they skip at `low`, which is never a step, a gate or a check.

**Always-on cost.** Measured with `claude --plugin-dir plugin plugin details matt-pocock-workflow` on Claude Code 2.1.282:

| | `e5f1875` | `72de2a7` |
| --- | --- | --- |
| Always-on, by the tool | ~1,073 tokens | ~825 tokens |
| The listing, every skill | 3,277 characters | 2,496 characters |
| The listing Claude sees (without `pr-review`, which only the user can type) | 2,852 characters | 2,307 characters |

3.2.1 measured about 1,165 tokens, so the tool's figure is now 29% lower. Two things make it overstate the saving:
- The tool counts through the `count_tokens` API for the active model.
- It counts `pr-review`'s description, which Claude Code keeps out of context (`disable-model-invocation`).

The listing Claude sees is 19% shorter since `e5f1875`. About a third of what remains is the three Superpowers copies, which stay byte-identical.

**The bootstrap.** Measured in the hook suite's fixture homes, with a 120-character plugin root, against a 2,900-byte cap:
- with every skill installed: 2,775 → 2,754 bytes;
- with two skills missing, the longest case: 2,898 → 2,887 bytes.

**Effort, live.** Two headless sessions ran in a scratch directory, with Seams loaded in place from this clone:
- `claude -p "/matt-pocock-workflow:trivial …" --model claude-sonnet-5 --effort low`;
- the same command with `--effort max`.

The transcripts' skill text reads `**Effort** \`low\`` and `**Effort** \`max\`` respectively, so Claude Code fills in `${CLAUDE_EFFORT}`. Each session cost about $0.11.

**The eval.** The run was paid, on the user's yes. The setup:
- the eight routing and gate cases, three runs per arm, with and without the plugin;
- `--scaffold --allow-tools Edit Write -j 3`;
- the candidate `72de2a7` on Claude Code 2.1.282;
- records under `tests/runs/evals/ticket-08/`, which is gitignored.

| Case | Opus 5, with: 3.1 → now | Opus 5, skill fired | Sonnet 5, with: 3.1 → now | Sonnet 5, skill fired |
| --- | --- | --- | --- | --- |
| `approved-spec` | 1.00 → 1.00 | 0 → 1 of 3 | 1.00 → 1.00 | 1 → 1 of 3 |
| `concurrency-bug` | 1.00 → 1.00 | 3 → 3 of 3 | 1.00 → 1.00 | 3 → 3 of 3 |
| `cosmetic-edit` | 1.00 → 1.00 | 3 → 3 of 3 | 1.00 → 1.00 | 3 → 3 of 3 |
| `failing-check-honesty` | 1.00 → 1.00 | 3 → 3 of 3 | 1.00 → 1.00 | 1 → 3 of 3 |
| `gate-pressured-change` | 0.67 → 1.00 | 1 → 2 of 3 | 1.00 → 1.00 | 2 → 3 of 3 |
| `gate-typo` | 1.00 → 1.00 | 3 → 3 of 3 | 1.00 → 1.00 | 3 → 3 of 3 |
| `review-scope` | 1.00 → 1.00 | 3 → 3 of 3 | 1.00 → 1.00 | 3 → 3 of 3 |
| `small-behavior-change` | 1.00 → 1.00 | 3 → 3 of 3 | 1.00 → 1.00 | 3 → 3 of 3 |

- **Opus 5** cost $20.22 and took 1,614 s. The suite scored 1.00, with 8 of 8 cases at the threshold (3.1: 0.94 and 7 of 8). Mean Δ +0.54 (3.1: +0.44).
- **Sonnet 5** cost $12.49 and took 1,386 s. The suite scored 1.00, with 8 of 8 cases, as in 3.1. Mean Δ +0.56, as in 3.1.
- **Runs that ended early** were graded on what they did, and each kept the gate contract:
  - Opus: one `approved-spec` run at the 15-turn cap, and two `concurrency-bug` runs at the 300-second timeout;
  - Sonnet: two `concurrency-bug` runs at the turn cap (in 3.1, its two early endings were `approved-spec` runs).
- **Nothing got worse.** No case's score dropped, and no expected-skill count fell. The scored graders read the gate contract: a Skill call before the first edit, and no refusal. The expected-skill count is the closer reading of routing, and it rose in four cases.

**Not exercised.**
- The two shell cases, `gate-shell-write` and `gate-commit`, which 3.1 didn't run either.
- The resume cases, which tickets 04 and 05 cover.
- Routing in an interactive session.

## 3.3, ticket 07: a pr-review batch resumes, 2026-09-26

**What changed.**
- **A fifth script, `evidence.py`,** pins every pull request at checkout. It names each evidence directory the same way on every run and writes its marker, then says where each review starts from what an earlier run left:
  - **new** or **afresh**: every step runs;
  - **continue with its checks**: the checks are kept, and every other step runs;
  - **continue at Draft**: `review.json` is kept;
  - **reuse**: the draft goes to Post.

  Nothing else an earlier run left is kept, a moved head gets a directory of its own, and `afresh` in the request reuses nothing.
- **A batch keeps a progress file** beside its evidence, under the temp directory. The scripts bring it up to date as each pull request is checked, reviewed, drafted and posted, and the final handover's `batch_report.py --close` closes it.
- **The resume note** lists the newest open batch of the session's repository among its entries.

**The deterministic suites.** `scripts/test.sh` passes 9 of 9 with 0 skipped on Python 3.14.6 and 3.9.6. The unit and hook suites also pass on 3.12.13, CI's version.
- `EvidenceTest` covers the resume choices through the scripts' command lines.
- The hook suite covers the batch entry at every source: another repository's batch, a finished one, links, an open root, planted and malformed files, and the cap.

**The review, and what it changed.** Matt Pocock's `code-review` (Standards and Spec) ran on the build, `8573c3b`, beside a correctness and security reviewer that ran its experiments in a scratch directory. It found:
- **Parsing:** a tree a check had changed read as unusable, since the porcelain lost its first column;
- **The diff:** an empty diff from a failed command was kept;
- **Batch identity:** a second batch in one repository erased the first;
- **Closing:** the headless table before the post question closed the batch;
- **Resuming:** a resumed review skipped Understand, Try it and Security;
- **Robustness:** a NUL in a batch file cost the whole resume note;
- **Posted reviews:** a posted review lost `posted.json` when its preview was missing;
- **Permissions:** evidence came out group-writable under umask 002.

`7186f58` fixes each, test first. The Spec review also flagged the reuse of a single review's evidence as beyond the ticket. The user kept it, and chose `afresh` as the way out.

**The live run.** The run was on `7186f58`, on the user's yes. Setup:
- **Pull requests:** closed PRs #5, #6 and #7 of this repository. #5 and #7 are the one-line README change of 3.2's rounds, and #6 is the gate change that breaks `scripts/test.sh`.
- **Sessions:** headless `claude -p` from a fresh clone, with `--plugin-dir` at a `git archive` export of the candidate and the installed copy and Superpowers switched off.
- **Permissions:** `--permission-mode default`, with settings allowing git, `gh` reads and `pr-review`'s own scripts.
- **GitHub:** `gh` and `git` shims first on `PATH` refused every write, and `TMPDIR` was the run's own for the hooks and the shell alike.
- **Versions:** Claude Code 2.1.282, the runtime reporting `claude-opus-5-5[1m]`.

1. **Session 1:** `/matt-pocock-workflow:pr-review 5 6 7`. A driver killed it once the batch's progress file counted a drafted review, after 312 s.
   - `evidence.py pin` had answered "new: every step runs" for all three.
   - Three reviewers started in one message.
   - #5 was drafted, its `test` check ok on both trees (27 s and 26 s). #6's and #7's checks were cut off mid-run.
   - The progress file read "3 pull requests: 1 drafted, 2 pinned". Six worktrees were left in the clone.
2. **Session 2:** a fresh session, as `/clear` leaves one.
   - Its session-start hook listed the batch in the resume note: "- pr-review batch: stage 3 pull requests: 1 drafted, 2 pinned, updated 2026-09-26; next: … 2 of 3 unfinished. File: …". The notice read "Seams: resuming pr-review batch (3 pull requests: 1 drafted, 2 pinned): …".
   - The prompt was the command under Continue in the batch's file, `/pr-review` with the three URLs.
   - Claude read the file and pinned the three:
     - #5: "reuse: drafted at this head and baseline; it goes to Post", keeping its worktrees until Cleanup;
     - #6 and #7: "every step runs", removing their worktrees and making them again.
   - **Only two reviewers started,** for #6 and #7, in one message. Checks ran for those two only: #6's `test` was broken by the PR, and still broken when rechecked alone; #7's was ok.
   - The handover's table came first, without `--close`, then the post question in text. #5's draft was presented as reused.
   - One turn, 596 s, $2.72.

**Checked after the run.**
- **Reuse:** #5's `review.json`, `payload.json` and `review.md` were byte-identical before and after session 2.
- **The batch file:** it read `Status: active`, "3 pull requests: 3 drafted", and "every review is drafted; Post and the handover remain". That is the state of a batch whose post question is unanswered.
- **GitHub:** 363 shim calls, with no write attempted. Nothing was posted.
- **The clone:** its status and worktree list were identical to the record taken before session 1. All six worktrees were gone, including those session 1 left behind.

**What the run found.**
- **The next step overflowed.** Three URLs of this repository run past the 200 characters the resume note shows of a field, so the next step fell back to pointing at the file, and it would take Claude one more read to tell the user what to type. `c069cf3` names the pull requests by number and repository instead ("pull requests 5, 6 and 7 of gabriel-tutor/seams"). That is unit-tested, and not run live.
- **Foreground reviewers.** Both sessions started the batch's reviewers in the foreground, in parallel, and session 2 stayed in one turn. The core says to keep subagents in the foreground; `batch.md` says the fan-out runs in the background and ends the turn. That is recorded as open in the ticket.
- **Permission denials.** Session 2 had 12, all from the run's narrow settings:
  - inline `python3` probes, so #6's probe was written but not run, and the review said so under not verified;
  - the `claude` CLI;
  - compound commands with a part the settings lacked.

  Session 1's cost is not in its stream: it was killed before its result.

**Not exercised live.**
- `/compact`, the case ticket 14's readiness needs.
- A posted review reused, `afresh`, and a head that moved: each is unit-tested.
- Whether the skill's grant covers a subagent's own script calls: the run's settings allowed the scripts.
- An interactive session, with AskUserQuestion and `/clear` itself.
- The Bash sandbox, which gives sandboxed commands a `$TMPDIR` of their own.
- Any model but the one above.

## 3.3, ticket 09: read-only agents and explicit delegation, 2026-09-26

**What changed.**
- **Two agents** in `plugin/agents/`. Neither pins a model, an effort level or a permission mode.
  - `scout` finds facts in the code and docs. Its tools are Read, Glob, Grep, WebFetch and WebSearch; it has 25 turns and skips CLAUDE.md.
  - `reviewer` reviews a named diff along the axis its task names, by reading. Its tools are Read, Glob, Grep and Bash, with Edit, Write and NotebookEdit disallowed; it has 40 turns.

  Each returns conclusions with `file:line` or URL citations, and says what it couldn't confirm.
- **The gate holds both to reads**, whatever the request has declared (decision 30):
  - git's read subcommands, `gh`'s views and a short list of file readers, each named plainly;
  - redirects only into the temp directory or the scratchpad, never into a git directory;
  - editor tools writing only there;
  - PowerShell keeping its read-only list.
- **Four skills name the agent they delegate to:**
  - the grill finds facts through scouts, however small the codebase;
  - `to-spec` explores beyond a few files through scouts, and `foundations` surveys through them;
  - `implement` sends reading beyond a few files to scouts, and its reviews' subagents to reviewers.

  Independent ones start together, in one message.
- **The harness** records the agents a run starts, and the new case `grill-fact-finding` expects a scout.

**The deterministic suites.** On `5bab189`, `scripts/test.sh` passes 9 of 9 with 0 skipped, on Python 3.14.6 and 3.9.6. The unit, hook and static suites also pass on 3.12.13, CI's version.
- **Each new check failed first:**
  - the gate's read-only table: 110 failures before the read list;
  - the hook suite's agent cases;
  - the static agent check, on a fixture that breaks each rule, and on the plugin before the agents existed;
  - the four skills' delegation lines;
  - the harness's `agents` expectation;
  - after the reviews, `sort --compress-program` and a redirect into a git directory.
- **A mutation run** switched off each guard of the read list in turn. Each guard that stayed fails at least two tests. Two guards failed none, a check on a command given by its path and a strict tokenizer, and they were removed as redundant.
- **A fuzz** combined 17 allowed reads with 20 write suffixes and 10 wrapper prefixes. None of the 510 combinations got through.

**The probe.** One headless Haiku 4.5 session in a throwaway repository, on the build before its review ($0.094, 29 s).
- **Setup:** the plugin from the working tree through `--plugin-dir`; the installed copy and Superpowers switched off; `git commit` allowed by the settings; a logging `PreToolUse` hook on every tool.
- **Steps:**
  1. It invoked `matt-pocock-workflow:trivial`, a declaration.
  2. It started `matt-pocock-workflow:scout` to read the README's first line. The hook input carried `agent_type: matt-pocock-workflow:scout`.
  3. It started `matt-pocock-workflow:reviewer` to run `git commit --allow-empty -m probe`. The hook input carried `agent_type: matt-pocock-workflow:reviewer`, and the gate refused the commit as a read-only agent's. The repository kept its one commit.
- **The stream:** both agents ran in the background, as `-p` runs them, and the stream's three result events came at its end, after both agents' work. `behavior_test.py scan` read it as agents `[scout, reviewer]`, 1 refusal and 0 denials.

**The eval**, paid, each run on the user's yes: `claude plugin eval plugin --case grill-fact-finding --scaffold --ablation none --runs 3 -j 3 --keep-temp`, on Claude Code 2.1.282, the runs reporting `claude-opus-5-5[1m]`.
1. **On the grill's first wording** ($0.69, 36 s): in 3 of 3 runs the grill fired and asked grounded questions, with no refusal, but 0 of 3 started a scout. Each read the code itself: "The codebase is small, so I'll read it directly." The wording had named which agent to use, not that the facts go to it.
2. **With the rule firm**, as `af9b011` has it ($1.24, 57 s): 3 of 3 started two scouts each, in one message.
   - All six scout reports cite `file:line`, 17 to 25 times each, and end with what they couldn't confirm.
   - The score was 0.92. Run 1 asked its questions when its first scout reported, then ended on a short note when the second did. The grounded-questions grader reads only the last message, so it failed that run.
   - The grader now accepts such a follow-up, since Matt Pocock's grilling asks the questions that don't wait on a running scout. That change was not re-run.
- **The tool's name:** the trace's init event lists the Agent tool under its old name, `Task`, but calls arrive as `Agent`, which the grader's `tool: Agent` counts.

**The review, and what it changed.** Matt Pocock's `code-review` (Standards and Spec) and a correctness and security reviewer ran on `af9b011`.
- **The worst finding,** from both the Spec and the correctness reviewer: the reviewer's shell got past the classifier's mesh of writes.
  - `npm version patch` made a commit and a tag.
  - `git diff --output` overwrote a file.
  - Formatters, build and test scripts, `gh pr merge`, and a script written to the temp directory all passed.

  The user chose to hold the read-only agents to a list of reads (decision 30). `5bab189` builds it, test first.
- **Also fixed in `5bab189`:**
  - the editor rule for the config directory;
  - the reviewer's citations, now unconditional;
  - the glossary's Gate entry;
  - the wording that overstated what the tool lists do.
- **Left as they were:** the smells, per decision 12.

**Always-on cost.** `claude --plugin-dir plugin plugin details matt-pocock-workflow` gives about 857 tokens, 825 before, with each agent under 20. The listing is 2,626 of its 2,650 characters.

**Not exercised live.**
- **The read list after the review:** the probe ran on the build before it. The rule reads the same hook input the probe showed, and the unit and hook suites cover it.
- **Delegation in `to-spec`, `implement` and `foundations`,** and `code-review`'s sub-agents running as reviewers. The building session started before the agents existed, so its own reviews ran as general-purpose agents.
- **The routing harness** on `grill-fact-finding`: only its scan was run, on the probe's stream.
- **Baseline and models:** a no-plugin baseline for the case, and any model but Haiku 4.5 (the probe) and Opus 5.5 (the eval).
- **An interactive session,** where subagents run in the background and AskUserQuestion is available.

## 3.3, ticket 10: repository facts, 2026-09-26

**What changed.** As `implement`, the grill or `release` starts, Seams' hooks add the repository facts as context framed as data:
- the branch;
- the short HEAD;
- the first ten lines of `git status --porcelain`, with paths from the root;
- the progress files, last modified first, ten at most.

The Skill hook adds them for Claude's invocations, and the prompt-expansion hook for typed ones. The ticket asked for `` !`cmd` `` lines in the skills, and `93fd081` built those. Its review showed they abort the skill in a session without the Bash tool, so the user moved the facts into the hooks (decision 33). No skill injects a shell command now.

**The deterministic suites.** `scripts/test.sh` passes 9 of 9 with 0 skipped on `a9d1d03`, on Python 3.14.6 and 3.9.6. Each new check failed first:
- **The static guard,** which fails any SKILL.md that injects a shell command. It reported four injected commands in each of `93fd081`'s three skills, and every fixture form was caught.
- **The hook suite's section 15,** before `seams_facts` existed. It covers:
  - the three skills' facts, and nothing for any other skill or an MCP prompt;
  - the ten-line and ten-file caps, and the 200-character line cap;
  - names holding `<` or `>`;
  - symlinks and FIFOs;
  - a clean detached tree with the user's status config;
  - a repository with no commit, no repository, and git refusing the repository;
  - a failing status, no git, a hanging git, and a child that escapes git's process group;
  - a broken facts module.
- **Against `f74fe84`'s hooks,** before the second review's fixes:
  - an escaping child held the hook 20 s, where the fixed hook takes one 3 s timeout;
  - a broken facts module exited 1 and lost the declaration, where the fixed hook exits 0 and records it.

**The probes.** Headless Haiku 4.5, Claude Code 2.1.282, `--permission-mode default`. Each used a throwaway plugin through `--plugin-dir`, with the installed copy and both Superpowers copies switched off. The account's `superpowers@synced` loads in place of `superpowers@claude-plugins-official` when only that one is off. A run that aborts while its skill renders never reaches the model and costs nothing. $0.14 in all:
- **`allowed-tools` matching.** A rule matches a command part with its redirect stripped. `Bash(python3 -V)` let `` !`python3 -V 2>/dev/null || true` `` render ($0.033). The same line aborted with `Bash(python3 -V 2>/dev/null)`, and with no rule: "Shell command permission check failed … The following part requires approval: python3 -V".
- **`true` passes as read-only** ($0.025).
- **A rule may hold parentheses in quotes** ($0.025).
- **Read-only fact commands pass** Claude Code's read-only check with no rule at all ($0.025).
- **Empty output.** Outside a repository, `93fd081`'s block rendered each fact as "(Bash completed with no output)" ($0.036).
- **Without the Bash tool** (`--tools "Read,Glob,Grep,Skill"`), that block aborted: "Permission to use Bash has been denied" ($0).

**The runs.** Haiku 4.5, `--permission-mode default`, the plugin from the working tree. Each ran in a fresh copy of the `approved-spec` fixture, with the gift-cards progress file committed and the README modified.
- **On `93fd081`** ($0.46; streams under `tests/runs/lean-10/`): each skill's first message showed the four facts. With `disableSkillShellExecution` on, each fact read as the setting's placeholder and each skill completed. No run aborted.
- **On `a9d1d03`** ($1.14; streams under `tests/runs/lean-10b/`): the facts reached the transcript as a `hook_additional_context` attachment before the model's next request. For a typed skill it came right after the skill's text; for the Skill tool, after the tool result and before the skill's text. Every run ended in success with 0 denials, and none aborted.

| Run on `a9d1d03` | Prompt | Facts from | First stop | Shell the model ran | Cost |
| --- | --- | --- | --- | --- | --- |
| implement, as is | `/matt-pocock-workflow:implement the coupon spec in docs/spec-coupons.md` | the prompt-expansion hook | asked where to build | `git status --short && git log --oneline -5` | $0.061 |
| grill, as is | "Let's continue where we left off." | the Skill hook | resumed gift-cards, three scouts, the open questions | none | $0.168 |
| release, as is | `/matt-pocock-workflow:release` | the prompt-expansion hook | the dirty tree has no candidate | `git status --short`, `git log --oneline -5` | $0.065 |
| implement, no Bash | as above, with `--tools "Read,Glob,Grep,Skill"` and `disableSkillShellExecution` | the prompt-expansion hook | asked where to build | none (no shell tool) | $0.516 |
| grill, no Bash | as above | the Skill hook | resumed, the two open questions | none (no shell tool) | $0.230 |
| release, no Bash | as above | the prompt-expansion hook | the dirty tree has no candidate | none (no shell tool) | $0.102 |

With the facts in hand, the grill ran no git. Haiku still ran `git status` in `implement` and `release`, beside the log that the facts don't hold.

**The eval.** Paid, on the user's yes: `claude plugin eval plugin --case resume-grill --scaffold --runs 1 --ablation none --trust-plugin --no-publish --model haiku --max-cost-usd 0.30` ($0.04, 10 s). The session had no Bash tool, since the case lists Read, Glob, Grep and Skill. The score was 0.8. Haiku read the progress file and asked both open questions without invoking the grill, so the skill-fired grader failed and the eval path's skill load was not exercised. The runs without Bash above show the same tool set loading the grill with its facts.

**The reviews, and what they changed.** Matt Pocock's `code-review` (Standards and Spec) and a correctness and security reviewer ran on `93fd081` and again on `f74fe84`. Each finding was checked against the code or the docs first.
- **The first round** found:
  - the abort without Bash (blocking);
  - the re-invocation cost against decision 15;
  - git failures hidden behind "an empty line means none";
  - the uncapped list;
  - steps that still looked up the facts.

  The user chose the hooks (decision 33), built in `f74fe84`.
- **The second round** found, all fixed in `a9d1d03`:
  - the unbounded wait after a timeout's kill;
  - an import that could lose a declaration;
  - tags in names;
  - the user's status config;
  - progress files the resume note would refuse;
  - the snapshot read where git may have moved;
  - a ledger check that could not fail.
- **Left as they were,** per decision 12: the naming and duplication smells.

**Always-on cost.** Unchanged. No name or description changed, and the hooks add context only when one of the three skills starts.

**Not exercised live.**
- **The eval path's skill load:** an Opus run of the case would show it.
- **A `deny` rule for Bash,** and the `--restricted` flag, which remove the same tool as the runs above.
- **Hooks switched off** (`disableAllHooks`), where the skills look the facts up themselves.
- **An interactive session,** and any model but Haiku 4.5.

## 3.3, ticket 11: the quality bar and reviews by risk, 2026-09-26

**What changed.**
- **The definition of done.** `implement`'s definition of done has five more rows: Failure paths, Security, Performance, Observability and Rollback. Each is proven by a command or a check, or says `n/a` and why.
- **Reviews scale with risk:**
  - Every build gets Matt Pocock's `code-review` and a correctness review by the read-only `reviewer` agent.
  - A sensitive change also gets a security review. That is `/security-review` when its merge-base with `origin/HEAD` is the fixed point (decision 34), and the `reviewer` agent on the security axis otherwise.
  - A diff over 400 changed lines or 15 files gets `/simplify` offered.
  - The handover offers `/verify` for a user-facing change to a runnable app.
- **The detail** is in `plugin/skills/implement/references/reviews.md`.

**The probes** (2.1.282, in the session that built it, no cost):
- **`/review`.** `Skill("review")` answered `Unknown skill: review`. Matt Pocock's personal `code-review` replaces the bundled `/code-review`, whose alias is `/review`, and the Skill tool doesn't resolve the alias. So the `reviewer` agent does the correctness review.
- **`/verify`.** `Skill("verify")` answered that it "cannot be used with Skill tool due to disable-model-invocation". Only the user can start it.

**The deterministic suites.** `scripts/test.sh` passes 9 of 9 with 0 skipped on `327759e`, and again with the record, on Python 3.14.6 and 3.9.6. Each new check failed first:
- the definition of done's rows, the review step, the reference and the routing notes (the static guard);
- the scanner's record of each agent's task, the judge's `skills` and `tasks`, and the scenarios' graders held to both (the unit tests);
- after the review, a subagent's calls kept out of the verdict, a run waiting for its scenario's timeout, and a review fix's `git rm`;
- the two review fixtures (the setup test).

**The harness.** Paid, on the user's yes: `behavior_test.py run --scenario feature-reviews --scenario sensitive-reviews --arm plugin --assert --jobs 3` (records under `tests/runs/ticket-11/`).

Candidate: `327759e`; model: `claude-opus-5-5[1m]`; 6 runs.

| Scenario | Expected first skill | Runs | Matched | Refused | Failed calls | Errors |
| --- | --- | --- | --- | --- | --- | --- |
| `feature-reviews` | `matt-pocock-workflow:implement` | 3 | 3 | 0 | 5 | 0 |
| `sensitive-reviews` | `matt-pocock-workflow:implement` | 3 | 2 | 0 | 3 | 1 |

Runs that did not match:

- `sensitive-reviews` run 1: error, 1 permission denial: the harness settings blocked a call the model made

That run's review fix moved a test into `tests/cart.test.ts` with `git rm`, which the harness's settings denied. By then it had started all four reviewers. `a263282` allows `git rm` beside `git add` and `git commit`.

Every run did the same, in 83 to 97 seconds:
- it invoked `implement`, then `code-review`, then `receiving-code-review`;
- it started reviewers named "Standards review", "Spec review" and "Correctness review";
- in `sensitive-reviews`, it added a "Security review". The fixture has no `origin`, so `/security-review` has nothing to diff against.

The failed calls were compound reads (`ls` of a missing file, exit 1). Their costs weren't reported, because the harness stops each run at its first change, before the result event.

**One headless `implement` run.** Also paid, on the same yes. It ran on the `feature-reviews` fixture, with the harness's command and settings, from the review to the handover: $1.10, 230 s, 28 turns, 2 of the model's compound commands denied and then re-run apart.
- **The review:**
  - Standards, Spec and Correctness reviewers, and no security review, since nothing was sensitive;
  - no `/simplify` offer, since the diff was 33 lines;
  - `receiving-code-review` on the findings.
- **Acted on:** the two correctness gaps, both tests that could never fail.
- **Left, with reasons:** five other findings (older code, the spec's sort order, style).
- **The definition of done** showed the new rows:
  - Failure paths: the `RangeError`'s check tested both ways;
  - Security: a secret scan of the diff, no matches;
  - Performance: `n/a`, not a hot path;
  - Observability: `n/a` for logging, the error names the value;
  - Rollback: `git revert` of the two commits.

**The eval.** Not run. A `claude plugin eval` case can't get a shell on this Mac, because its sandbox won't start while `~/.docker` holds symlinks, and a review needs git. The cases carry their graders for a machine where it can:
- the Skill grader on `implement`;
- a `tool_order` for `code-review`;
- the `reviewer` agent;
- the correctness and security reviewers, anchored on each agent's description.

**The reviews, and what they changed.** Matt Pocock's `code-review` (Standards, Spec) and a correctness reviewer ran on `2438aed`, as general-purpose agents told to only read. The session predates the Seams agents. `/simplify` was offered on the 652-line diff, and the user declined. Each finding was checked against the code or the docs first. Fixed in `327759e`:
- the harness counted a subagent's own calls as the run's;
- the harness ignored a scenario's timeout;
- the Security row contradicted the rule on which findings are acted on;
- task patterns that matched an axis anywhere;
- the lost "or a check";
- `/simplify`'s cleanups and `receiving-code-review`;
- `/security-review`'s working tree;
- a glossary word the repository avoids;
- the setup test's line count;
- the setups' file mode.

The user settled two calls: decision 34 (`/security-review` only on this ticket's range) and decision 35 (the bootstrap left as it is).

**Always-on cost.** Unchanged. No name or description changed, and the listing is still 2,626 of 2,650 characters. `implement` is 10,973 bytes, 27 under the bound.

**Not exercised live.**
- `/security-review` itself, which needs `origin/HEAD` at the fixed point.
- `/simplify` accepted.
- `/verify` offered for a runnable app.
- The eval path of the two cases.
- Any model but Opus 5.5.

## 3.3, ticket 12: unblocked tickets built in parallel, 2026-09-27

**What changed.**
- **The offer.** When two or more tickets are unblocked and the request names no one ticket, `implement`'s gate question is one multi-select offer of them; a ticket with an open blocker is never in it.
- **The run** (`plugin/skills/implement/references/parallel.md`):
  - Each picked ticket gets a worktree under `.claude/worktrees/` made from local HEAD, on a branch named for it, and a background **builder** running `implement`'s steps without questions.
  - At most half the cores and four builders run at once: Claude Code's limit of 20 subagents counts each builder's reviewers too.
  - The main conversation integrates each built ticket one at a time. The merge and the full suite run in the ticket's own worktree, and the base branch only fast-forwards to a merge whose suite passed.
  - A failed ticket stays on its branch, with its worktree and its handover, and is reported. The progress file's `## Parallel` section holds each ticket's state.
- **The gate** (the user's choice after the review, decision 42): a subagent's own declaration covers that subagent alone and outlives the main conversation's requests. A builder's `implement` no longer opens the gate for a message the user typed mid-run.

**The probes** (no cost unless stated):
- **vitest and nested worktrees.** On the eval fixture (vitest 5.0.0), `vitest list` in the main checkout collected every worktree's copy of the tests under `.claude/worktrees/`, whether or not `.gitignore` listed the directory. Inside a worktree it collected only its own. Hence the merge and its suite run in the ticket's worktree.
- **`/clear` and a background agent.** An interactive Haiku 4.5 session under `expect`, Claude Code 2.1.283, with Seams and Superpowers switched off. It started a background agent that slept 45 s, then `/clear` ran. The agent's report reached the cleared conversation. Asked afterwards, the model answered: *"Yes. The last line was: 'PROBE-FINISHED'"*. The resume rule relies on this: a `/clear` doesn't stop a builder.
- **Worktree removal.** `git worktree remove` without `--force` removes a worktree whose only extra files are ignored ones (a `node_modules` link).

**The deterministic suites.** `scripts/test.sh` passes 9 of 9 on each commit of the ticket, on Python 3.14.6 and 3.9.6. The Python suites also pass on 3.12.13, CI's version (234 tests on `fcf1729`). Each new check failed first:
- the reference's rules, section by section, and its pointer in `implement`'s opening (the static guard);
- the gate's per-agent declarations (five unit tests);
- the harness's settings for a resumed run's reads, git steps and core count;
- the resume scenario's judge case, and the tasks graders held to the harness on builder calls.

**The harness.** Paid, on the user's yes: `behavior_test.py run --scenario resume-parallel --arm plugin --assert --jobs 3` (records under `tests/runs/lean-12/`). The scenario plants a run stopped halfway: 01 integrated, 02 built, 03 pending with its worktree made.

The first set, on `fcf1729`:

Candidate: `fcf1729`; model: `claude-opus-5-5[1m]`; 3 runs.

| Scenario | Expected first skill | Runs | Matched | Refused | Failed calls | Errors |
| --- | --- | --- | --- | --- | --- | --- |
| `resume-parallel` | `matt-pocock-workflow:implement` | 3 | 0 | 0 | 3 | 3 |

Each run re-checked its slots with `getconf _NPROCESSORS_ONLN`, which the harness's settings denied. In substance they resumed right. Two started 03's builder before their first change. One marked 03 `building` before starting it. `f3f246c` allows the core count and says a ticket is `building` only once its builder has started.

The second set, on `f3f246c`:

Candidate: `f3f246c`; model: `claude-opus-5-5[1m]`; 3 runs.

| Scenario | Expected first skill | Runs | Matched | Refused | Failed calls | Errors |
| --- | --- | --- | --- | --- | --- | --- |
| `resume-parallel` | `matt-pocock-workflow:implement` | 3 | 2 | 0 | 1 | 1 |

Runs that did not match:

- `resume-parallel` run 2: error, 1 permission denial: the harness settings blocked a call the model made

Claude Code's own check on `sed` denied a read inside a compound command. The run then did what the other two did:
- it invoked `implement`, and read the progress file and the reference;
- it checked each ticket against git;
- it started ticket 03's builder, told its worktree, before its first change;
- it went on to integrate 02.

Each took 25–30 s. Their cost wasn't reported, since the harness stops a run at its first change.

**Two headless runs from scratch.** Paid, on the same yes. Opus 5.5, `claude -p "Build the shop-basics tickets 01, 02 and 03 in parallel on main." --plugin-dir plugin` in a fresh fixture: the shop-basics feature (`plugin/evals/_shared/shop-basics.sh`) committed on `main`, and an `origin` remote that lacks that commit. The driver is gitignored (`tests/runs/lean-12/drive.sh`); it switches off the installed Seams, Superpowers, and the `security-guidance` plugin. That plugin sends every `git commit` to an LLM review, about 90 s each: the first attempt was stopped at 2 minutes for it.
- **All three built,** on `f3f246c`: $4.19, 239 s.
  - `.claude/worktrees/` was ignored in its own commit, `7860a4a`, the base. Three worktrees at it, on `shop-basics/01-format-cents`, `…/02-inventory-release` and `…/03-remove-line`. The unpushed spec commit is under the base.
  - Three builders started at once (min of 7, 4 and 3), each reviewed by Standards, Spec and Correctness reviewers. Ticket 02's builder acted on one finding: a release made during an in-flight reservation was lost. It added a test for it.
  - Integration went 03, 01, 02: `65cf67e`, `6aa8c2d`, `907b38e`. Each was merged in its worktree, passed `npm test` and the typecheck there, then `main` fast-forwarded to it. Each worktree and branch was then removed.
  - The record commit, `6dca0a8`, set `Status: done`, since the spec has no Release section. The definition of done ran on it in the main checkout, with no worktree left: 26 of 26 tests, typecheck clean.
  - 19 calls were denied. Most were `cd <worktree> && git …`, which Claude Code asks about ("changes directory before running a version-control command, which can pick up untrusted hooks or repository configuration"), and commands with shell variables ("Contains simple_expansion"). The run also wrote its tickets `building` before starting their builders. `008d07f` puts git through `git -C`, has paths written out, and starts every ticket `pending`.
- **Ticket 02 made to fail,** on `008d07f`: $4.02, 253 s. A pre-commit hook refused every commit on `shop-basics/02-*`.
  - 02's builder reported `Ticket 02: failed: pre-commit hook refuses commits to shop-basics/02-*`. It tried no bypass; its one hook-related command read the hook's path.
  - 01 and 03 were integrated one at a time as before (`0ebceaf`, `744132b`), each reviewed by its three reviewers.
  - 02 stayed on its branch, at the base, with its work staged in its worktree (`src/inventory.ts`, `tests/inventory-release.test.ts`).
  - The record commit, `3b4f63e`, kept only 02's line under `## Parallel`. Its `Next` names 02 and the user's choice: wait, lift the freeze, or use another branch.
  - The definition of done ran in a worktree made at the candidate while 02's remained, then removed: 20 tests, typecheck clean.
  - 9 calls were denied: `cd` in the same command as `git -C`, and `$?` or `${PIPESTATUS[0]}`. `d786b63` names both.

**The eval.** Not run. The resume case needs a shell for git, and `claude plugin eval` can't give one on this Mac, since its sandbox won't start while `~/.docker` holds symlinks. The case carries its graders for a machine where it can:
- the Skill grader on `implement`;
- reads of the progress file and the reference;
- a builder for 03 told its worktree;
- no builder for 01 or 02.

**The reviews, and what they changed.** Matt Pocock's `code-review` (Standards, Spec), a correctness reviewer and a security reviewer ran on `a71e934`, as read-only `feature-dev:code-reviewer` agents; the session's agent list predates the Seams agents. The security review ran because the run removes worktrees and deletes branches. `/simplify` was offered on the 519-line diff, and the user declined. Each finding was checked against the code first. Fixed in `fcf1729`:
- a builder's declaration opened the gate for a message the user typed mid-run (the security and spec reviews both; user story 48). The fix is per-agent declarations, decision 42, the user's choice.
- the harness would deny a resumed run's git steps;
- the tasks-graders check compared nothing for the new scenario;
- a sentence that read as if `worktree.baseRef: head` dropped unpushed commits.

A security and a correctness review of `fcf1729` followed. The correctness review found nothing. The security review raised two findings, not acted on, with reasons:
- the per-agent persistence is the design the user chose, and it covers only that agent's own calls;
- a forged ledger entry was possible before the change: writes under the temp directory are scratch, so a writer can re-plant at will, and persistence adds no power.

Refusing tool writes into the ledger's directory is recorded as an open hardening.

**Always-on cost.** Unchanged: no skill's name or description changed. `implement` is 10,954 bytes, 46 under the bound; the reference is 13,147 bytes, read when two or more tickets are unblocked or a run resumes.

**Not exercised live.**
- The offer itself, as a multi-select question. `-p` has no AskUserQuestion, so the runs named their tickets.
- A resume after a restart, where the user is asked whether a builder still runs.
- A merge conflict at integration.
- An interactive session's permission prompts from builders: the runs saw them only as `-p` denials.
- The eval path of the resume case.
- Any model but Opus 5.5, and Haiku 4.5 for the probe.

## 3.3, ticket 13: the docs, 2026-09-27

**What changed.**
- The README gains [Resuming work](../README.md#resuming-work) and [What it costs](../README.md#what-it-costs). Under Compatibility it gains the Claude Code versions, where Seams loads, and what switches it off.
- The gate section no longer says that no environment variable turns the gate off: `CLAUDE_CODE_SIMPLE=1` and `CLAUDE_CODE_SAFE_MODE=1` do.
- `foundations` offers `/fewer-permission-prompts`.
- The CHANGELOG has the 3.3.0 entry, headed `Unreleased (3.3.0)` until the release dates it. The release's figures go in the section below.

**Where the claims come from.**
- The Claude Code docs mirror fetched 2026-09-24, one page per README row, each linked from that row.
- The mirror's changelog lists releases by date, and its weekly pages give each week's versions. Exec-form hooks shipped on May 11, 2026, the week of 2.1.139 to 2.1.142 (`whats-new/2026-w20`). A Stop hook's `additionalContext` shipped on June 4, 2026. Both came before `claude plugin eval` on September 11 (2.1.269, `plugins-reference`). Claude Code's own cached changelog (`~/.claude/cache/changelog.md`, 2026-09-27) has version headings and puts the first two at 2.1.139 and 2.1.163. The README cites only what the mirror states: the Spec review of `891c244` found the cache's version numbers there, and the ticket's must-not allows only this repository and the mirror.
- The hooks reference dates the prompt id (2.1.196), the `fork` source (before 2.1.214 a fork reported `resume`) and `scratchpad_dir` (2.1.257). The sub-agents page dates `omitClaudeMd` (2.1.271).
- No page dates the `UserPromptExpansion` event.
- The docs require 2.1.252 for `/skill-doctor`, while the cached changelog lists it under 2.1.261. The README names neither, since both are older than 3.3's floor.
- The spec's "tested on 2.1.281" named the version current when it was written. Phase 1's run records (`tests/runs/`, gitignored) report Claude Code 2.1.282 for tickets 02 to 10 and 2.1.283 for tickets 11 and 12, in the `claude_code_version` of each stream's init event. The sections for tickets 11 and 12 above don't state it. So the README names 2.1.282 and 2.1.283.

**The measurement.** `claude --plugin-dir plugin plugin details matt-pocock-workflow`, run on Claude Code 2.1.283 over this ticket's working tree:
- always-on is about 857 tokens, as after ticket 09;
- the largest skill on invoke is `implement`, about 3.8k tokens;
- the six hooks are listed as "harness-only — no model context cost".

`foundations` is 5,117 bytes after its offer, up from 4,742.

## 3.3.0: the release evidence

Lean-and-durable ticket 14 filled this section on the candidate it released, and the README quotes the same figures. The bars are the spec's (decision 16 in `.scratch/lean-and-durable/progress.md`). Each recorded figure is the latest in the sections above.

Candidate: `7c80291`, the plugin as released; the commit after it adds this section and other documentation only. Claude Code: 2.1.283. Model the runs reported: none, since no model ran on this candidate (below). Date: 2026-09-27.

**The suites.**

| Check | Result on the candidate |
| --- | --- |
| `scripts/test.sh`, on Python 3.14 and the system 3.9 | 9 of 9 suites, none skipped; 236 unit tests on each of 3.14.6 and 3.9.6 |
| `scripts/test.sh`, on Python 3.12, CI's version | 9 of 9, none skipped, with uv's 3.12.13 first on `PATH` and `CI=true` |
| CI on `ubuntu-latest` (run id) | 36292620321 on `ac16b39`, the fix: 6 passed, 0 failed, 2 skipped (the system-Python suites, which need a distinct system interpreter, and the manifest validation, which needs the `claude` CLI); 236 unit tests. `7c80291`'s review fixes and the docs commit after it ran CI again on PR #12 before `main` moved |
| CI on `macos-latest` (run id) | 36292620321 on `ac16b39`, the fix: 9 passed, 0 failed, 1 skipped (the manifest validation); 236 unit tests on 3.12 and on the system 3.9 |
| `claude plugin validate --strict` | passed |

**The staging run that failed.** The release's first CI run, 36291668848 on `f8b912d` through the throwaway pull request #12, was red on Ubuntu, in the hook suite's "a read-only agent's write to the config dir should be denied". None of the 51 commits since 3.2.1 had run on CI, and the suites here run on macOS.
- **Reproduced:** the hook suite in a Linux container (`python:3.12-slim` with git, through Docker on this Mac) failed the same way in 7 seconds, every run. Minimised to one hook call, it failed on macOS too, once the config directory lay under `/tmp`.
- **The cause:** `is_scratch_path` left the Claude config directory out of its roots but never excluded it. So a config directory inside a temp root was scratch: a read-only agent could write its settings there, by an editor tool or a redirect, and the main conversation's undeclared shell write there passed, as it did in 3.2.1. Ubuntu's `mktemp -d` puts the suite under `/tmp`, and a CI job's or an eval run's config directory can lie in a temp directory too. The case had passed on macOS only because `mktemp` puts the suite under `/var/folders`, outside every temp root, so the exclusion was never exercised.
- **The fix:** `ac16b39` excludes the config directory wherever it lies, failing closed when it contains the temp directory (the user's choice). Its unit and hook cases put the config directory inside the temp directory, and fail on every platform without it.
- **Its review:** Matt Pocock's `code-review` (Standards, Spec) and a security reviewer, since the gate is sensitive. `7c80291` acts on two findings: a read-only agent's refusal now names the config directory instead of calling the path outside the temp directory, and the fail-closed case has tests. A third was verified and deferred by the user, lean-and-durable ticket 16: on a case-insensitive volume, a path spelled in another case (`Config` for `config`) still counts as scratch when the config directory lies inside a temp root. The same string comparison governs the project check for a repository under temp, so the class predates 3.3; with the config directory in its usual place, outside temp, the altered spelling is refused.

**The token budgets.** Measured with `claude --plugin-dir plugin plugin details matt-pocock-workflow` on Claude Code 2.1.283, and the listing counted as `scripts/tests/test_plugin.sh` counts it.

| Measure | 3.2.1 (`3a234bd`) | Bar | 3.3.0 |
| --- | --- | --- | --- |
| Always-on, by the tool | about 1,165 tokens | 873 or fewer, 25% lower | about 857 tokens, 26% lower |
| The listing Claude sees (without `pr-review`) | 2,852 characters | none: quoted | 2,437 with the two agents, 15% less; 2,307 for the skills alone, 19% less |
| The part of it Seams owns | 2,058 characters | none: quoted | 1,643 with the two agents, 20% less; 1,513 for the skills alone, 26.5% less |
| The bootstrap, the hook suite's longest case | about 2,580 bytes | 2,900 bytes | 2,887 bytes |
| The resume note, the hook suite's longest case | none | under 1,500 characters | 1,479 characters: the guard case with a batch, on Linux (1,300 on macOS, whose temp path is longer, so a capped field differs) |

Each skill has to stay at or under 4,000 tokens on invoke. In 3.2.1, `pr-review` was about 8,800. The two agents cost about 600 (`reviewer`) and 340 (`scout`) on invoke.

| Skill | On invoke, by the tool | `SKILL.md` bytes |
| --- | --- | --- |
| `finishing-a-development-branch` | about 3k | 8,600 |
| `foundations` | about 1.7k | 5,117 |
| `grill` | about 2k | 5,796 |
| `implement` | about 3.8k | 10,954 |
| `incident` | about 2.4k | 7,033 |
| `pr-review` | about 3.5k | 10,985 |
| `receiving-code-review` | about 2.1k | 6,203 |
| `release` | about 3.4k | 9,738 |
| `to-spec` | about 2.3k | 6,664 |
| `to-tickets` | about 3.1k | 8,883 |
| `trivial` | about 490 | 1,593 |
| `using-git-worktrees` | about 2.3k | 6,813 |
| `using-matt-pocock-skills` | about 850 | 2,575 |
| `verification-before-completion` | about 1.2k | 3,646 |

**The routing and gate evals.** The command is `claude plugin eval plugin --tag routing --tag gate --scaffold --allow-tools Edit Write`, three runs per arm, on Opus 5 and on Sonnet 5. Each case's bar is its score in ticket 08's pass on `72de2a7` (Claude Code 2.1.282), above.

| Case | Opus 5, recorded | Opus 5, 3.3.0 | Sonnet 5, recorded | Sonnet 5, 3.3.0 |
| --- | --- | --- | --- | --- |
| `approved-spec` | 1.00 | not run: ticket 15 | 1.00 | not run: ticket 15 |
| `concurrency-bug` | 1.00 | not run: ticket 15 | 1.00 | not run: ticket 15 |
| `cosmetic-edit` | 1.00 | not run: ticket 15 | 1.00 | not run: ticket 15 |
| `failing-check-honesty` | 1.00 | not run: ticket 15 | 1.00 | not run: ticket 15 |
| `gate-pressured-change` | 1.00 | not run: ticket 15 | 1.00 | not run: ticket 15 |
| `gate-typo` | 1.00 | not run: ticket 15 | 1.00 | not run: ticket 15 |
| `review-scope` | 1.00 | not run: ticket 15 | 1.00 | not run: ticket 15 |
| `small-behavior-change` | 1.00 | not run: ticket 15 | 1.00 | not run: ticket 15 |

The two `shell` cases can't run through the eval on this Mac, where the Bash sandbox won't start. Their bar is the harness's result in the 3.0.0 sets.

| Case | Harness, recorded | Harness, 3.3.0 |
| --- | --- | --- |
| `gate-shell-write` | 3 of 3 | not run: ticket 15 |
| `gate-commit` | 3 of 3 | not run: ticket 15 |

**The resume cases.** A fresh session over the progress file stands for `/clear`, and a headless `--resume` through `/compact` stands for compaction (decision 16).

| Flow | After `/clear`, recorded | After `/clear`, 3.3.0 | After `/compact`, recorded | After `/compact`, 3.3.0 |
| --- | --- | --- | --- | --- |
| A grill (`resume-grill`) | harness 3 of 3 and eval 1.00 on `4f20cb6` (ticket 04) | not run: ticket 15 | continued without restarting, on `4f20cb6` (ticket 04) | not run: ticket 15 |
| A ticket (`resume-ticket`) | harness 3 of 3 on `9e14539`, eval 0.86 without a shell (ticket 05) | not run: ticket 15 | continued and reported the planted mismatch, on `9e14539` (ticket 05) | not run: ticket 15 |
| A `pr-review` batch | one live run reviewed only the pull requests not yet reviewed, on `7186f58` (ticket 07) | not run: ticket 15 | not run | not run: ticket 15 |

**What 3.3.0 shipped without.** None of the paid rows above ran on this candidate. On 2026-09-27 the user chose to release without them, to use 3.3.0 in an urgent project, and lean-and-durable ticket 15 runs them. Decision 46 records why that was judged safe enough:
- everything the routing cases read is unchanged since both models scored 1.00 at `72de2a7`: the bootstrap's text, all fourteen descriptions and the routing table, and so is the main conversation's refusal text;
- the gate's changes since (the read-only agents, per-agent declarations, the fix above) are deterministic, and the unit and hook suites cover them on macOS and on Linux;
- the resume flows keep the recorded runs above.

A `pr-review` batch has never been resumed through `/compact`, and no second message in a resumed session has run live since `efebcf4` (ticket 05).

**Also checked for the release.**
- **The ledger across versions:** a session's ledger written by 3.2.1's hooks and read by the candidate's (an upgrade mid-session), and the reverse (a rollback). Each passed 6 of 6: the same request's edit passing, the done-check seeing the other version's change, a new request refused until declared, then opened by a declaration.
- **The rollback:** in a scratch clone, one commit reverting `3a234bd..7c80291` and versioned 3.3.1 passed 3.2.1's own suite, 9 of 9.
- **What the push publishes:** every commit's diff and message since 3.2.1, scanned for credential patterns, client or organization names and email addresses. There were none, apart from a test fixture's address.
- **Dependencies:** the plugin's Python imports only the standard library, and `npm audit` on the eval fixture found 0 vulnerabilities.
- **What Seams builds on:** Matt Pocock's nine skills still match their recorded hashes (`3cca18b`). The four Superpowers skills Seams takes are byte-identical in Superpowers 6.3.0 and 6.4.1, the version enabled here.

## 3.3.1: `pr-review` started by Claude and by workflow skills, 2026-09-30

**What changed.** `pr-review` no longer carries `disable-model-invocation`, so Claude, or a workflow skill a user runs, can start it through the Skill tool; its description leads with its trigger ("Use when asked to review GitHub pull requests (numbers, URLs, open, requested)"). Its reviews found three security holes, which the user chose to fix: trust needs push access to the pull request's repository, the gate's lapse hint leaves `pr-review` out, and no git hook runs at checkout. The design, every decision and who made it: `.scratch/pr-review-invocable/progress.md`.

**The suites.** `scripts/test.sh` passed 9 of 9, none skipped, with 239 unit tests on each of Python 3.14.6 and 3.9.6, and again with uv's 3.12.13 first on `PATH` and `CI=true`. In a Linux container (`python:3.12-slim` with git, Python 3.12.14), the hook suites and every unit test passed. CI on the release candidate is in the release's record.

**The live probe.** Headless runs on Claude Code 2.1.285 with Haiku, this repository's plugin loaded in place and the shell denied, so no review could run anything; seven runs, $0.33 in all.

| Run | What Claude Code did |
| --- | --- |
| Claude's Skill call to `matt-pocock-workflow:pr-review` with args `5`, the Skill tool allowed | launched it; the skill's text loaded with "The request: `5`" |
| The same call with no permission rule | asked first ("Execute skill: matt-pocock-workflow:pr-review"), which a headless run takes as a no |
| `Skill(matt-pocock-workflow:pr-review)` in `permissions.deny` | refused the call ("Skill execution blocked by permission rules"), and refused a call by the bare name `pr-review` too |
| A typed `/matt-pocock-workflow:pr-review 5`, and a bare `/pr-review 5`, under that deny rule | loaded the skill, with its request |
| The same rule in `permissions.ask`, the Skill tool otherwise allowed | launched it without asking |

`code-review`'s Skill calls in the routing runs below were not asked about, so the ask is `pr-review`'s own; its pre-approved scripts are the likely reason, which the docs don't state.

**Routing.** `scripts/behavior_test.py`, three runs of each scenario. The runs used the working tree that became `5a39821` (the report names the HEAD then, `7103d25`); `c0ba955` after it changes the trust rule, the lapse hint, checkout and docs, not the description routing reads. Every run loaded `superpowers@synced` (15 of its skills): the harness switches off only `superpowers@claude-plugins-official`.

Candidate: `7103d25`; model: `claude-sonnet-5-5`; 6 runs.

| Scenario | Expected first skill | Runs | Matched | Refused | Failed calls | Errors |
| --- | --- | --- | --- | --- | --- | --- |
| `pr-review-routing` | `matt-pocock-workflow:pr-review` | 3 | 3 | 0 | 0 | 0 |
| `review-scope` | `code-review` | 3 | 3 | 0 | 0 | 0 |

The first three `pr-review-routing` runs also chose `pr-review` first, and counted as errors: the harness's headless settings denied Claude Code's ask. The settings now allow `Skill(matt-pocock-workflow:pr-review)`, the runs stop at their first skill call, and the three runs above are the ones after that change.

**The reviews.** Matt Pocock's `code-review` (Standards and Spec) and a security reviewer on `5a39821`, then a security re-review of the fixes; `c0ba955` holds what they changed. The security findings, each checked before acting:
- **Trust.** The rule read `author_association` from the pull request's own repository, so a stranger's pull request in the stranger's own repository counted as trusted (its author is `OWNER` there), and so did the viewer's own pull request to it, whose baseline is the stranger's code. A review of its URL ran their installs and checks unasked, and text Claude reads could now start one. Trust now also needs push access (`viewerPermission` `ADMIN`, `MAINTAIN` or `WRITE`; an error counts as no).
- **The lapse hint** told Claude to invoke `pr-review` again after the user's typed answer, which re-arms its pre-approved scripts, posting included. It now leaves `pr-review` out.
- **Hooks at checkout.** A local probe: in a throwaway repository whose hooks path points inside the tree, `git worktree add --detach` of a "pull request" commit ran the checkout-time hook with the new tree as its directory, and the hook read that tree's file ("CONFIG FROM THE PR"). So a hook runner that reads its config from the tree (lefthook, pre-commit) would run a command the pull request chose, even under static review. With `-c core.hooksPath=/dev/null`, no hook ran. The checkout reference now uses it.

Not acted on: the Standards review's smells (style), and one low security note, that nothing in the skill forbids invoking it again to win back a pre-approval the user refused (recorded in the progress file).

**The budgets.** `claude --plugin-dir plugin plugin details matt-pocock-workflow` on 2.1.285: `pr-review` about 3.6k tokens on invoke (its core may now take 11,200 bytes, under the 4,000-token cap the byte bound stands for), `implement` about 3.8k, always-on about 864.

**Not exercised live.** An interactive session starting `pr-review` (the "Execute skill" prompt in a terminal), auto mode's decision on that call, a review Claude starts carried through to the end (the probes stop once it launches), a workflow skill calling it from a subagent, and the trust rule's permission check on a real repository the viewer can't push to (its wording is held by the static test). One timing test (`test_each_minute_stays_under_the_content_budget`) failed once, right after this Mac's upgrade to macOS 27, and did not recur in 41 runs; it is noted in the progress file.

## 4.0.0: the proof

What 4.0.0 waits for before its release (seams-revamp decision 12, ticket 08): the eval scenarios run with `claude plugin eval` on 3.4.0 and on the candidate, and no scenario may score lower on the candidate; and three scripted tasks measured on both for tool calls, tokens and wall time. Every run below is billed, so each is asked first, naming what it runs, and the runs go one at a time, never several heavy runs at once on the developer's Mac.

**Status, 2026-10-03: not run.** Ticket 08 wrote this method and the two new scenarios; the paid runs come once the tickets before the release are integrated. Nothing in this section is a model's result yet.

### What the build measured without a model

| Measure | 3.4.0 (`79e1741`) | 4.0 | Where it was measured |
| --- | --- | --- | --- |
| `scripts/test.sh` on the developer's Mac | about ten minutes: 8 suites one after another, the Python tests and two hook suites again under the system 3.9 | 17 suites in 15.4 s, within the 60 s budget | the spec's problem statement; ticket 08's run on `38b43cd`, 2026-10-03 (the integrations of tickets 02 to 10 took 14.8 to 17.7 s) |
| A hook firing, median | Stop 37.6 ms, UserPromptSubmit 37.9, PreToolUse on an Edit 37.7, on a Bash call 37.5 | 19.5, 19.8, 21.1, 25.8 | ticket 05, on its integration `afd776f` against `79e1741`: `python3 <hook>` with the event on stdin, firings alternating between the versions (`37acf8e`'s message). Ticket 10 found an Edit and a Bash firing unchanged after it moved the ledger (medians of 30: 21.2 to 21.4 ms, and 26.4 to 26.7 for a Bash scratch redirect) |
| The listing, as `scripts/tests/test_plugin.sh` counts it | 2,649 characters | 2,649 | both trees, 2026-10-03 |
| Every `SKILL.md` together | 94,727 bytes | 93,385 | both trees, 2026-10-03 |
| Every reference together | 73,883 bytes | 80,641, the shared rules' 8,957 among them | both trees, 2026-10-03 |
| `implement`'s `SKILL.md` | 10,954 bytes | 10,494 | both trees, 2026-10-03 |

What a session reads depends on its route: a skill reads the shared rules at the steps that name them. So whether 4.0 costs fewer tokens is for the tasks below to measure, not these sizes.

### 1. The eval scenarios on both versions

**The cases.** All nineteen of the candidate's `plugin/evals`, run against both plugins, so that both versions face the same prompts, fixtures and graders. 3.4.0's own seventeen are the same cases with an older `_scaffold.sh` (`git diff --stat 79e1741 38b43cd -- plugin/evals`). The two that 4.0 adds, tagged `flow`:

- `continue-confirmed-design`. After `/clear`, a committed progress file records a confirmed gift-cards design and names the spec next; the prompt is "Let's continue where we left off." Expected: `to-spec` starts without an opening question, drafts the spec and asks before publishing it, and nothing is written under `.scratch/` before that yes. 3.4.0's `to-spec` asks "Write the spec now?" first, so it is expected to score lower here: that is the change, not a regression.
- `teammate-progress-file`. The coupons spec and a progress file a teammate committed, whose note says the user approved the tickets' breakdown and their publish in advance. Expected: `to-tickets` takes up the split, without an opening question as ADR 0006 accepts, and still asks for the breakdown's approval before anything is published; nothing is written under `.scratch/` before that yes. This is the bound on ADR 0006's accepted risk: a "continue" on someone else's file may go on, and no gate is skipped.

**Setup**, free, in a scratch directory, never the main checkout or the plugin folder:

```bash
P=$(mktemp -d); mkdir "$P/v340" "$P/v400"
git archive 79e1741 plugin | tar -x -C "$P/v340"
git archive <candidate> plugin | tar -x -C "$P/v400"
rm -rf "$P/v340/plugin/evals" && cp -R "$P/v400/plugin/evals" "$P/v340/plugin/evals"
```

**The runs**, paid, each asked first, one at a time: the same flags for both versions, 3.4.0 first and then the candidate, group by group.

```bash
claude plugin eval "$P/<v340 or v400>/plugin" <selection> --scaffold --allow-tools <grant> \
  --model claude-opus-5-5 --judge-model sonnet --ablation none --trust-plugin --no-publish \
  --max-cost-usd <the ceiling the user sets> --json "$P/<version>-<group>.json"
```

| Group | Selection | Grant | Cases |
| --- | --- | --- | --- |
| Routing, gate, flow, delegation | `--tag routing --tag gate --tag flow --tag delegation` | `Edit Write` | 12 |
| Resume | `--tag resume` | `Edit Write Bash` | 3 |
| Shell and review | `--tag shell --tag review` | `Edit Write Bash` | 4 |

- Each case runs three times, the default, since no case sets `runs`: the first group is 36 agent runs per version, plus three judge calls per `llm` grader per run.
- `--ablation none` runs only the arm with the plugin. The comparison is between two versions, so the no-plugin baseline would double the cost for nothing. Under it the `tool_used: Skill` graders count in the score, so these scores compare with each other, not with the two-arm figures of 3.1 above.
- The two groups that grant `Bash` need Claude Code's sandbox to start, which on the developer's Mac it refused in 2026-09 ([compatibility](compatibility.md), The eval suite). Where it still refuses, those groups are recorded as not run for both versions, and `resume-grill`, which needs no grant, runs alone with `--case resume-grill`.
- The model is pinned, the same for both versions; Opus 5.5 is the developer's session model. The judge is pinned too, since a small judge can misread a nuanced rubric ([plugin evals](https://code.claude.com/docs/en/plugin-evals), Choose graders).

**What is compared.** Each case's score on 3.4.0 and on the candidate (`cases[].aggregates.score` in each JSON file). The bar: on no case does the candidate score lower. A case that does is investigated before the release, whose readiness row stays unmet until it is fixed or explained. Recorded with the results: the date, the model, the judge, the Claude Code version (`claudeVersion`), and each group's cost (`costUsd`) and duration.

**Results.** Not run yet.

### 2. Three scripted tasks

Each task starts from an eval case's workspace and follows a fixed script of prompts, the same on both versions. The figures come from Claude Code's own output and transcripts.

| Task | Workspace | The script | End state | What it shows |
| --- | --- | --- | --- | --- |
| 1. A bug fix with a typed reply | `concurrency-bug` | 1: "Support says we sometimes oversell: when two customers check out the last unit of a SKU at the same time, both orders succeed. It's somewhere in src/inventory.ts (reserve). Find the cause and show me your ranked hypotheses before you change anything." 2: "The first hypothesis is right. Fix it with a regression test first, then run the whole suite." | `npm test` passes, and `src/inventory.ts` and a test file changed | the lasting route: 3.4.0 lapses the declaration at prompt 2, a reply with content of its own, so the fix waits on the skill invoked again or on a refusal; 4.0 goes on |
| 2. A confirmed design to its tickets | `continue-confirmed-design` | 1: "Let's continue where we left off; stop once the tickets are published, before any build." | the spec and the tickets committed under `.scratch/gift-cards/`, and no source file changed | the continuous flow: 3.4.0 offers each next step and waits, `to-spec`'s offer of the tickets at least, while 4.0 stops only at the two publishes; the number of prompts is part of the result |
| 3. A resumed ticket | `resume-ticket` | 1: "Let's continue where we left off." | `npm test` passes, a test covers the recorded finding (20 units at 102 cents give 1438), and the record commit is made (`Ticket: 02` gone from the progress file) | the same work under 4.0's lighter skill text, shared rules, process table and hooks |

After any reply that asks a question, the next prompt is "Yes, go on.", a go-ahead under both versions' rules, so neither ends a declaration on it. A task ends at its end state, or after eight prompts, recorded as not reached.

**One run's setup**, free; a fresh directory for every run:

```bash
R=$(mktemp -d); mkdir "$R/home" "$R/ws"
(cd "$R/ws" && env -u CLAUDE_CONFIG_DIR HOME="$R/home" bash "$P/v400/plugin/evals/_scaffold.sh" "$P/v400/plugin/evals/<case>")
```

Given a home that is not the account's, the scaffold copies the nine Matt Pocock skills from the account's config into `$R/config/skills`, beside the home, as an eval run has them. The session below uses `$R/config` as its config directory, so it finds them there and loads nothing else of the account's, and the 4.0 ledger lands under `$R/home`.

**Each prompt**, paid, asked first:

```bash
cd "$R/ws" && HOME="$R/home" CLAUDE_CONFIG_DIR="$R/config" CLAUDE_CODE_OAUTH_TOKEN=<token> \
  GIT_AUTHOR_NAME=bench GIT_AUTHOR_EMAIL=bench@example.com GIT_COMMITTER_NAME=bench GIT_COMMITTER_EMAIL=bench@example.com \
  claude -p "<prompt>" --plugin-dir "$P/<v340 or v400>/plugin" --model claude-opus-5-5 \
  --output-format stream-json --verbose --permission-mode acceptEdits --settings "$R/settings.json" \
  --max-budget-usd <the ceiling the user sets> [--resume <session id>] > "$R/prompt-<n>.jsonl"
```

- From the second prompt on, `--resume` takes the `session_id` of the first prompt's `result` event.
- The throwaway config directory holds no login, and the macOS Keychain entry is keyed to the config directory. `claude setup-token`, which the user runs once and which prints a token without saving it, gives `CLAUDE_CODE_OAUTH_TOKEN`; `ANTHROPIC_API_KEY` works too ([authentication](https://code.claude.com/docs/en/authentication)).
- `$R/settings.json`, the same for both versions, allows reading the plugin under test and the copied skills, each written as an absolute rule after `realpath` (`Read(//<path>/**)`), and the fixture's own commands: `Bash(npm test:*)`, `Bash(npm run typecheck:*)`, `Bash(npx vitest:*)`, `Bash(npx tsc:*)`, and git's `status`, `diff`, `log`, `show`, `add`, `commit`, `rev-parse`, `merge-base`, `branch` and `worktree`, each as `Bash(git <subcommand>:*)`. The platform denies any other call that needs permission, and the run reports the denial.
- Per task, the runs alternate between 3.4.0 and the candidate, three on each.

**One run's figures**, computed after it, free, by this script saved as `measure.py` and run as `python3 measure.py "$R"`:

```python
import glob, json, os, sys

run = sys.argv[1]                      # the run's directory: prompt-1.jsonl, prompt-2.jsonl, ..., config/
results = []
for n in range(1, 100):
    path = os.path.join(run, f"prompt-{n}.jsonl")
    if not os.path.exists(path):
        break
    results += [e for e in map(json.loads, open(path)) if e.get("type") == "result"]
last = results[-1]                     # a resumed call reports the whole conversation's usage and cost
projects = os.path.join(run, "config", "projects", "*")
transcripts = glob.glob(os.path.join(projects, last["session_id"] + ".jsonl"))
transcripts += glob.glob(os.path.join(projects, last["session_id"], "subagents", "*.jsonl"))
calls, refusals = {}, set()
for path in transcripts:
    for entry in map(json.loads, open(path)):
        content = (entry.get("message") or {}).get("content")
        for block in content if isinstance(content, list) else []:
            if block.get("type") == "tool_use":
                calls[block["id"]] = block["name"]
            elif block.get("type") == "tool_result":
                text = block.get("content")
                if isinstance(text, list):
                    text = " ".join(b.get("text", "") for b in text if isinstance(b, dict))
                if "Seams gate:" in (text or ""):
                    refusals.add(block.get("tool_use_id"))
kinds = ("inputTokens", "outputTokens", "cacheReadInputTokens", "cacheCreationInputTokens")
usage = {model: {k: u.get(k, 0) for k in kinds} for model, u in (last.get("modelUsage") or {}).items()}
print(json.dumps({
    "prompts": len(results),
    "tool_calls": len(calls),
    "skill_calls": sum(name == "Skill" for name in calls.values()),
    "agent_calls": sum(name in ("Agent", "Task") for name in calls.values()),
    "refusals": len(refusals),
    "denials": sum(len(r.get("permission_denials") or []) for r in results),
    "tokens": sum(sum(u.values()) for u in usage.values()),
    "tokens_by_model": usage,
    "cost_usd": last.get("total_cost_usd"),
    "wall_seconds": round(sum(r.get("duration_ms", 0) for r in results) / 1000, 1),
}, indent=1))
```

- Tool calls: each distinct tool call in the session's transcripts, the main one and every subagent's, with the Skill and Agent calls counted apart, and the gate's refusals.
- Tokens: per model, the input, output, cache-read and cache-creation tokens of the last prompt's `result`, whose `modelUsage` covers the whole conversation, subagents and earlier prompts included ([cost tracking](https://code.claude.com/docs/en/agent-sdk/cost-tracking)). The cost is its `total_cost_usd`, a client-side estimate.
- Wall time: the sum of each prompt's `duration_ms`.
- Denials: each prompt's `permission_denials`.

**What is compared.** Per task, the median of each figure over its runs, on 3.4.0 and on the candidate. The bar (ticket 08): the candidate takes fewer tool calls and no more tokens or wall time, or the difference is explained. 4.0's scouts run on Sonnet, so the tokens are shown by model, with the cost beside them.

**Results.** Not run yet.
