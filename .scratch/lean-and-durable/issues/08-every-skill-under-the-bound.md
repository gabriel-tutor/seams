# 08: Every skill under the bound, lighter always-on cost

**What to build:** Every Seams skill fits whole in what compaction keeps, and every session starts lighter:
- **The guard:** a static guard enforces the size bound and forbids model and effort pins.
- **Descriptions:** each leads with its trigger, and together they shrink by about a quarter.
- **The bootstrap:** it states the routing as the project's facts with no out-of-band framing, and states the quality bar, within its 2,900-byte cap.
- **The version:** it lives only in `plugin.json`.

**Blocked by:** 06 (pr-review under the cap, scripts without prompts)

**Status:** done

- [x] The static test fails the build when:
  - any SKILL.md exceeds 11,000 bytes;
  - any SKILL.md or agent sets `model` or `effort`;
  - the marketplace entry carries a version.
- [x] Every SKILL.md is within the bound, with its gates, must-nots and steps first. `release`, `to-tickets` and `finishing-a-development-branch` are checked, and trimmed if needed.
- [x] `claude plugin details` shows always-on cost at or under 875 tokens (from about 1,165).
- [x] The injected bootstrap:
  - has no `<EXTREMELY_IMPORTANT>` wrapper and no imperative out-of-band framing;
  - states every routing row and rule, plus the quality bar, as the project's facts;
  - stays at or under 2,900 bytes.
- [x] Each skill says which extras it skips at low effort, read from `${CLAUDE_EFFORT}`. It never skips a gate or a check.
- [x] Must not happen: routing gets worse. Every routing and gate eval case keeps its score. The eval run is paid, so ask first.

**How to verify:**
- `scripts/test.sh`.
- `claude plugin details matt-pocock-workflow@my-workflow-agent-skills`.
- `claude plugin eval plugin --tag routing --tag gate --scaffold --allow-tools Edit Write --model <model> -j 3`, compared with the recorded 3.1 scores. The run is paid, so ask first.

## Comments

Built 2026-09-25 on local `main`, not pushed. The commits:
- `65988ac`, the build.
- `72de2a7`, the review fixes. The paid eval ran on this candidate.
- The commit carrying this record.

**What shipped.**
- **The guard** (`scripts/tests/test_plugin.sh`). It now runs on CI too: CI has no `claude` CLI, and `scripts/test.sh` used to skip the whole file for it. Only manifest validation needs the CLI now. The guard checks:
  - every SKILL.md is at most 11,000 bytes;
  - no SKILL.md or agent sets `model` or `effort` in its frontmatter. A fixture that breaks each rule shows the guard catching it, and a skill of exactly 11,000 bytes shows it passing;
  - the version is in `plugin.json` only. The marketplace entry lost its copy: when both set one, Claude Code uses `plugin.json`'s without a warning (`plugin-marketplaces`, "Version resolution and release channels");
  - the listing (each skill's and agent's name and description) is at most 2,650 characters. That is 875 tokens at the ratio `claude plugin details` measured on `65988ac`: 2,426 characters for about 801 tokens. The tool counts through the `count_tokens` API for the active model, or estimates offline (`plugins-reference`, "plugin details"), so its figure moves with the machine. It is the evidence, not the test;
  - each Seams skill's effort line, below. Three fixture lines show the check refusing a line that skips a gate, a line that doesn't open with the rule, and a line that names nothing.
- **Descriptions:** each leads with its trigger. The workflow summaries are gone (`incident`, `release`, `pr-review`), and so is the repetition (the bootstrap skill's). The triggers stay, `trivial`'s "this declaration opens the gate" included.
  - Always-on cost by `claude plugin details`: about 1,073 tokens on `e5f1875`, now about 825. 3.2.1 paid about 1,165, so that is 29% less.
  - The listing went from 3,277 to 2,496 characters.
  - `foundations` dropped one trigger, "the bootstrap says the repo is not set up". The session's own line names `matt-pocock-workflow:foundations` in that case.
- **The bootstrap** states the routing as the project's facts. The session-start hook no longer adds the `<EXTREMELY_IMPORTANT>` wrapper or the preamble addressed to Claude. `<SUBAGENT-STOP>` is now "Subagents skip this routing.", and no line tells Claude to ask or offer (the hooks docs, line 902, say command-framed text can trip Claude's prompt-injection defenses).
  - Every row is kept word for word (the static test holds each one), with every rule and the quality bar.
  - At its longest the bootstrap is 2,887 bytes, under the 2,900 cap (`e5f1875`: 2,898).
  - The session's two dynamic lines are facts too: "`matt-pocock-workflow:foundations` is offered first", and "the user installs them with `npx skills add …` and a restart".
- **Effort.** The ten Seams skills read `${CLAUDE_EFFORT}` in one standing line before their first step. Every step, gate and check runs at every level. At `low` a skill skips only the extras it names:
  - `pr-review`: nits and praise;
  - the grill: the count of decisions left;
  - `implement`: the offer to add a run command to the README;
  - `finishing-a-development-branch`: the start announcement;
  - `foundations`: the report's line on why each gap matters;
  - the other five say "nothing here is optional".

  Two kinds of skill don't carry the line. The bootstrap is injected by the session-start hook, where Claude Code fills in no variables, and it runs no steps. The three Superpowers copies stay byte-identical (decision 19). So the ticket's "each skill" means these ten.

  Live check: two headless Sonnet 5 sessions, with `--effort low` and `--effort max`, loaded `trivial`. Each transcript's skill text read `**Effort** \`low\`` and `**Effort** \`max\`` respectively. The two runs cost $0.22 together.
- **Sizes now** (bytes): `pr-review` 10,732 (268 under the bound, which is ticket 07's room), `implement` 9,966, `release` 9,419, `to-tickets` 8,883, `finishing-a-development-branch` 8,600. `release`, `to-tickets` and `finishing-a-development-branch` needed no trim.

**Evidence** (`docs/plugin-behavior-tests.md`, "3.3, ticket 08"):
- **The deterministic suites:** `scripts/test.sh` passes 9 of 9 with 0 skipped on `72de2a7`, on Python 3.14.6 and 3.9.6. Each new check failed first:
  - the marketplace's version, on its 3.2.1 copy;
  - the always-on cost, at about 1,073 tokens;
  - the bootstrap's wrapper and preamble;
  - the effort lines, before they existed;
  - the size and pin guard, before it existed;
  - after the review, the strict effort check, on its three fixture lines.

  With no `claude` CLI on PATH, under bash 3.2, `test_plugin.sh` runs every check but manifest validation and passes.
- **The eval**, paid and on the user's yes: the eight routing and gate cases, three runs per arm with and without the plugin, on `72de2a7`, Claude Code 2.1.282. No case's score dropped on either model, and no expected-skill count fell:
  - **Opus 5** ($20.22): 8 of 8 cases at 1.00 (3.1: 7 of 8). `gate-pressured-change` went from 0.67 to 1.00. Mean Δ +0.54 (3.1: +0.44). Expected skill fired: `approved-spec` 0 → 1 of 3 and `gate-pressured-change` 1 → 2 of 3; the rest stayed at 3 of 3.
  - **Sonnet 5** ($12.49): 8 of 8 at 1.00, as in 3.1. Mean Δ +0.56, as in 3.1. Expected skill fired: `failing-check-honesty` 1 → 3 of 3 and `gate-pressured-change` 2 → 3 of 3; the rest as before.
  - Five runs ended early and were graded on what they did; each kept the gate contract. Opus: one `approved-spec` run at the 15-turn cap, and two `concurrency-bug` runs at the 300-second timeout. Sonnet: two `concurrency-bug` runs at the turn cap.
- **Effort, live:** the two headless sessions above, $0.22.
- **Always-on cost:** `claude --plugin-dir plugin plugin details matt-pocock-workflow` gives about 1,073 tokens on `e5f1875` and about 825 on `72de2a7`.

**Review of `65988ac`.** Matt Pocock's `code-review`, Standards and Spec, as two subagents. Standards raised 10 findings. Spec checked every criterion and raised 5 findings. Each was checked against the code and the docs.
- **Acted on in `72de2a7`:**
  - CI skipped every static guard. It has no `claude` CLI, and `scripts/test.sh` skipped the whole file, so an 11,001-byte skill or a `model` pin passed there. Only manifest validation needs the CLI now. Both axes raised this.
  - The always-on check moved with the machine. The docs say the tool counts through `count_tokens` for the active model, or estimates offline. The listing's length is now the guard, calibrated from the tool.
  - The effort check passed a line that skips a gate, and a line that names nothing. It is strict now, with fixture lines.
  - Two session-start lines had changed meaning. `foundations`' offer had become an order ("comes first"), and the install line read as something already done ("the user runs … and restarts").
  - Triggers were dropped: `foundations`' typecheck, boundary rules and scanning, and `trivial`'s opening of the gate.
  - Smaller fixes:
    - the notices' note on the adaptation;
    - the ticket named in a comment;
    - a one-line helper comment;
    - `KEPT` defined once;
    - the name `HOW_TO_INSTALL`.
- **Not acted on,** per decision 12, because none is a correctness or requirement gap:
  - a helper for the two frontmatter-body `awk` calls;
  - trimming the older bootstrap fragments, which the exact rows now cover;
  - "Red flags that a skill is due now", which says what "meaning invoke now" said.

**Open.**
- **The saving Claude sees is smaller than the tool's figure.** `claude plugin details` counts `pr-review`'s description, but Claude Code keeps a `disable-model-invocation` skill's description out of context (`skills`, the table of invocation fields). Without it, the listing is 19% shorter since `e5f1875` (2,852 → 2,307 characters). The three byte-identical Superpowers copies make up about a third of what remains. The 3.3.0 release should quote both figures.
- **Headroom for later tickets:**
  - ticket 09's two agents have about 50 tokens under 875, since the listing guard counts agents; otherwise 09 trims elsewhere;
  - `pr-review`'s core has 268 bytes left for ticket 07;
  - `implement` has 1,034 bytes left for what tickets 09 to 12 add to it, so some of that goes to references.
- **Noticed, not changed:**
  - The bootstrap says mid-task complexity "moves down, never up", in the table's order, while `trivial` says it "moves you up a row, never down".
  - README line 7 and `plugin.json`'s description still describe a grill that asks one question at a time. That is ticket 13's README pass.
