# 13: Docs: resuming, surfaces, off switches, measuring, versions

**What to build:** From the README and the changelog, a user can find out:
- how resuming works;
- where Seams loads fully and where it doesn't;
- which settings silently switch it off;
- how to measure what it costs;
- which Claude Code versions it supports.

`foundations` offers `/fewer-permission-prompts`.

**Blocked by:** 02 (The gate sees every shell and stops tripping on quotes); 03 (Typed skills, the lapse hint, a calmer done-check); 07 (A pr-review batch resumes); 10 (Pre-loaded facts); 12 (Unblocked tickets built in parallel)

**Status:** done

- [x] The README covers:
  - **Resuming:** progress files, the resume note, and the notice.
  - **A surfaces table:**
    - Seams loads fully in the CLI and in Desktop local sessions.
    - In VS Code it loads a subset of skills.
    - In cloud sessions it loads only when enabled on the claude.ai account.
    - It doesn't load in Desktop WSL.
    - In `-p`, questions come as text.
  - **Off switches:** `disableAllHooks`, `allowManagedHooksOnly`, `strictPluginOnlyCustomization` for skills, `--bare`, `--safe-mode`.
  - **Measuring:** `claude plugin details`, `/skill-doctor`, and OpenTelemetry with `OTEL_LOG_TOOL_DETAILS=1`.
  - **Supported versions:** 2.1.269 or later, tested on 2.1.281, with the optional fields named.
- [x] `foundations` offers `/fewer-permission-prompts`, which the user runs, and stays within the size bound.
- [x] The CHANGELOG has a 3.3.0 entry saying what changed and why. The evidence doc has a 3.3 section ready for the release's figures.
- [x] Must not happen: the README makes a claim without evidence in this repository or the docs mirror, or a surface claim the docs don't support.

**How to verify:** Read the README and the CHANGELOG against the spec's decisions and the docs pages they cite. Then run `scripts/test.sh`, which includes the static test's README and attribution checks.

## Comments

Built 2026-09-27 on local `main`, not pushed. The commits:
- `891c244`, the build.
- `cb6f325`, the review fixes.
- The commit carrying this record.

**What shipped.**
- **The README.** Each claim about Claude Code links its docs page.
  - **Resuming work**, under How to use it, covers:
    - the progress file: where it lives, who writes it, that it's committed, and that it holds no secrets;
    - the resume note: when it's added, what it holds, its caps, and that it's framed as data;
    - the notice, worded as the hook prints it;
    - what continues each kind of work.
  - **What it costs** is a new section:
    - What every session carries: the listing, the bootstrap at up to 2,900 bytes, and the resume note under 1,500 characters. Why each `SKILL.md` stays within 11,000 bytes.
    - The always-on cost by `claude plugin details`: about 1,165 tokens in 3.2.1 and about 857 in 3.3. That figure leaves out what the hooks inject.
    - How to measure it: `claude plugin details matt-pocock-workflow` (with `--plugin-dir plugin` from a clone); `/skill-doctor`, and where it's unavailable; OpenTelemetry with `CLAUDE_CODE_ENABLE_TELEMETRY=1`. Without `OTEL_LOG_TOOL_DETAILS=1`, a third-party plugin's skill names arrive redacted, and the flag comes with a privacy caution.
  - **Compatibility** gains three subsections:
    - **Claude Code versions:** 2.1.269 or later, and why; the three optional fields with their versions; phase 1's runs on 2.1.282 and 2.1.283.
    - **Where Seams loads:** the CLI and JetBrains; Desktop local and SSH sessions; VS Code's subset; cloud sessions through the claude.ai account, with Matt Pocock's skills in the repository or on claude.ai; Desktop WSL; `claude -p`.
    - **What switches it off:** `disableAllHooks`; `allowManagedHooksOnly`; `strictPluginOnlyCustomization`, which stops Matt Pocock's skills rather than Seams; `--bare` or `CLAUDE_CODE_SIMPLE=1`; `--safe-mode` or `CLAUDE_CODE_SAFE_MODE=1`; and a repository's own `enabledPlugins`.
  - "Once per repo" names `/fewer-permission-prompts`.
  - Decision 45's corrections: the one-question grill on line 7, "no environment variable turns the gate off", the Durable state bullet, and the Compatibility paragraph's 3.0.0 versions.
- **`foundations`** offers `/fewer-permission-prompts` in its offer question. The user runs it, since it writes permission rules. The skill is 5,117 bytes.
- **`plugin.json`**'s description no longer describes a one-question grill.
- **The CHANGELOG** has the 3.3.0 entry, headed `Unreleased (3.3.0)` (decision 44). It says what changed and why, grouped as the spec's Solution is.
- **The evidence doc:**
  - its intro is current;
  - ticket 13's section says where each claim comes from;
  - "3.3.0: the release evidence" holds the tables ticket 14 fills: the suites, the token budgets, the evals against their recorded scores, and the resume cases.
- **The static test** pins each README section (Resuming work, What it costs, and the three Compatibility subsections, with the names the spec lists) and the `foundations` offer. Each check failed before its section existed.

**Evidence** (`docs/plugin-behavior-tests.md`, "3.3, ticket 13"):
- **The suites.** `scripts/test.sh` passes 9 of 9 with 0 skipped on the build's content and on `cb6f325`, on Python 3.14.6 and 3.9.6, with 235 unit tests each. `test_plugin.sh` also passes on Python 3.12.13, CI's version.
- **The docs research.** Four read-only agents read the docs mirror: surfaces, off switches, measuring and versions. Two more read the repository's records. I checked the lines the README cites against the mirror, and the correctness review checked every claim against its source.
- **The measurement.** `claude --plugin-dir plugin plugin details matt-pocock-workflow` on Claude Code 2.1.283: always-on is about 857 tokens, and `implement` is the largest on invoke, at about 3.8k.
- **The versions.** The run records' init events show 2.1.282 for tickets 02 to 10 and 2.1.283 for tickets 11 and 12.

**Review of `891c244`.** Matt Pocock's `code-review` (Standards, Spec) and a correctness reviewer ran as read-only `feature-dev:code-reviewer` agents, with the diff as a file, since this session's agent list predates the Seams agents. The change isn't sensitive and is 238 changed lines, so there was no security review and no `/simplify` offer.
- **Standards:** no findings.
- **Acted on in `cb6f325`:**
  - The README's 2.1.139 and 2.1.163 came from Claude Code's cached changelog, which the must-not doesn't allow. It now cites the mirror's dates (Spec).
  - Decision 45 now names the patch versions the Compatibility paragraph dropped (Spec, below its bar).
  - The sentence on the `/hooks` notices links the changelog (Correctness). The review's premise, that only `disableAllHooks` is documented, was wrong: `changelog/index.md:148` documents all three.
- **Recorded as mine:** decisions 43 (the versions phase 1 ran on, instead of the spec's 2.1.281), 44 (the `Unreleased` heading) and 45 (the stale claims corrected).

**Open**, all in the progress file:
- For ticket 14:
  - no `pr-review` batch resume case, and no batch resumed through `/compact`;
  - `docs/compatibility.md` records only 3.0.0 and 3.1.0;
  - the always-on figures to re-measure;
  - the CHANGELOG's date convention.
- `review_payload.py`'s fixed fence, a 3.2.1 bug that was never routed.
- Not verified live: the surfaces and off switches themselves (the spec documents them and never tests them), and `/fewer-permission-prompts` run from `foundations`.
