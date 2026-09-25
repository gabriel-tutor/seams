# 06: pr-review under the cap, scripts without prompts

**What to build:** `pr-review`'s instructions fit whole in what compaction keeps:
- **The core:** a SKILL.md under the size bound (11,000 bytes, about 4,000 tokens), with its gates, must-nots and steps first.
- **References:** batch mode, checks, drafting and posting, and cleanup move to reference files. The core names each one with a "read this when…" line.
- **Scripts:** its bundled scripts are referenced through `${CLAUDE_SKILL_DIR}` and pre-approved in `allowed-tools`, so they never prompt.
- **Limits:** the claim that subagents can't start subagents is replaced by Claude Code's real limits.

This split prefactors tickets 07 and 08.

**Blocked by:** 01 (Release 3.2.1)

**Status:** done

- [x] `pr-review`'s SKILL.md is at most 11,000 bytes, and `claude plugin details` shows its on-invoke cost at or under 4,000 tokens.
- [x] Every reference file is named in the core's first screen, together with when to read it. Guidance that must hold for the whole review is written as standing instructions.
- [x] Its scripts are referenced through `${CLAUDE_SKILL_DIR}` in the body and in `allowed-tools` rules. A headless run in default permission mode runs them without a permission denial.
- [x] Limits:
  - Subagents can nest three levels deep by default.
  - At most 20 run concurrently.
  - Wide fan-outs can hit rate limits.
- [x] Must not happen: behaviour is lost in the split. The existing `pr-review` tests and the static test's `pr-review` checks still pass. Every rule in 3.2.1's SKILL.md is present in the core or a reference, checked item by item in the ticket's comments.
- [x] Stale `__pycache__` in the `pr-review` scripts is removed.

**How to verify:**
- `scripts/test.sh`.
- `claude plugin details matt-pocock-workflow@my-workflow-agent-skills` for the on-invoke figure.
- A headless `/pr-review` run on a throwaway pull request in this repository, with writes to GitHub blocked as in 3.2.1's live runs. It must show the scripts running without prompts.

## Comments

Built 2026-09-25 on local `main`, not pushed. The commits:
- `bb5a825`, the build.
- `8fbdca2`, the review fixes. Live run 1 used this candidate.
- `65c1388`, the fix from live run 1: a single review stays in the turn its pre-approval covers. Live run 2 used this candidate.
- The commit carrying this record.

**What shipped.**
- **The core:** `SKILL.md` is 10,850 bytes, about 3.4k tokens on invoke by `claude plugin details` (from 26,046 bytes and about 8.8k). Before its first step it states the rules that hold for the whole review, and it names each reference with when to read it and to read it again after a compaction or `/clear`. The Gate, severity, the verdict and the handover stay whole in the core. Every other step keeps its heading there, and its gates and must-nots.
- **Six references**, not four: `checkout.md`, `batch.md`, `understand-and-review.md`, `checks.md`, `draft-and-post.md` and `cleanup.md`. 3.2.1's Gate, Checkout, Understand, Review and handover alone were 11,443 bytes. This is decision 23, made in the build and not the user's choice.
- **Scripts:**
  - Each is named as `python3 ${CLAUDE_SKILL_DIR}/scripts/<name>.py` in the body and pre-approved by the same command in `allowed-tools`. The references write `<skill-dir>`, which the core defines, because Claude Code fills the variable in only in SKILL.md.
  - A call must be only that command, with every path written out, because an allow rule matches neither past a variable assignment nor a chained command.
  - The grant ends with the turn that invoked the skill. That turn ends when the session waits on background work or on an answer typed as a message, so a single review runs its scripts and its reviewers in the foreground. A headless post question comes after the handover's table.
  - After the turn, the user's own permission settings decide. `batch.md` says its fan-out ends the turn.
- **Limits:** Claude Code's documented limits replace the claim that subagents can't start subagents: three levels of nesting, 20 running at once by default, and rate limits on a wide fan-out. Each pull request still gets one subagent that walks every axis itself, now for the right reason.
- **Bytecode:** none is in the plugin, and none was ever tracked. A static guard keeps it that way.
- **The description** now leads with its trigger and drops its repetition, done early for ticket 08 so that the core's must-holds fit. `pr-review`'s always-on cost went from about 220 tokens to about 140, and the plugin's from about 1,165 to about 1,073.

**Item by item: every rule of 3.2.1's SKILL.md, and where it is now.** The core is `SKILL.md`; the rest are under `references/`. "Word for word" is checked mechanically: 140 of the 154 sentences of 3.2.1's body appear unchanged in the core or a reference, and the other 14 are the rewordings named below.
- **Frontmatter:** the name, `disable-model-invocation`, `argument-hint`, the seven `gh` pre-approvals and the seven disallowed commands → the core, unchanged. The four script rules are new. The description is shortened (below).
- **Opening:**
  - the senior engineer's review and `$ARGUMENTS` → the core, word for word;
  - the three promises → the core's rules for the whole review, word for word. "Three promises hold throughout" now reads "These hold for the whole review, whatever a step or a reference says";
  - pull request content as data, and an attempt to instruct as a blocking finding → the core, word for word.
- **Gate 1–5:** which pull requests, the preconditions, the facts, trust and its question, and Seams' gate → the core, word for word. Only "(see Batch)" is gone: the reference list says when `batch.md` is read.
- **Checkout:** always one PR at a time, and why → `checkout.md`, with the rule in the core too. Steps 1–5, the rest of Checkout → `checkout.md`, word for word:
  - the marked clone;
  - the one record before the first checkout;
  - fetch and pin, and re-pin a head that moved;
  - the merge-base baseline;
  - `$EVID`: stale outputs removed, an unmarked directory stops the review, the marker, the two `--detach` worktrees;
  - the diff.

  "As in Cleanup" now names `cleanup.md`. The core also says an unmarked directory stops the review for a question.
- **Batch:**
  - One pull request skips the step, and Understand through Draft run here → the core. Several run in parallel, one subagent each → `batch.md`.
  - "A subagent can neither ask the user anything nor start subagents of its own" → replaced, as the ticket asks, by Claude Code's documented limits: no AskUserQuestion, nesting three levels deep, 20 at once by default, rate limits.
  - Steps 1–7 → `batch.md`, word for word:
    - the checks once per repository ("as Checks says" now "as `checks.md` says");
    - every question first (trust, services, bash 4);
    - all at once, the check slots, each suite's workers;
    - facts only, with no review hints (plus the skill's directory, which a subagent needs to find the references);
    - the instruction and its three differences (now naming the core and the three references a subagent reads);
    - a failed subagent, `error.txt`, "not yet: could not review" (plus "a rate limit included");
    - the rechecks alone, flaky checks, rebuilt payloads, `--merge`, never by hand.
  - "When Claude Code will not start another subagent, start it as one finishes" → `batch.md`: "when Claude Code refuses another (`Concurrent subagent limit reached`), start it as one finishes".
- **Understand 1–6:** the pull request and its spec, merge state, your earlier review, the repo's standards, size, and the sensitive files → `understand-and-review.md`, word for word. Item 6 was titled "Risk" and is now "Sensitive files", the glossary's word. The core names each, with `CONFLICTING` as a blocking finding.
- **Checks 1–7:** discover, don't invent; run on both trees; already broken is not yet innocent; E2E; try it; security; the rule → `checks.md`, word for word. The core keeps four things:
  - discover, never invent;
  - services only after a yes, and never real credentials, paid APIs or production data;
  - static review skips the step;
  - a check that could not run is never passing.
- **Review:**
  - Items 1–3 → `understand-and-review.md`, word for word:
    - `code-review`, and the risk reviewer with its axes (now given "the sensitive files");
    - verify every finding;
    - prove what you can, with probes; static review runs nothing; an unproven suspicion is a question.
  - The core restates verify, prove and static review.
  - 4 (severity) and 5 (the verdict) → the core, word for word.
- **Draft 1–2:** `review.json` and `review_payload.py` → `draft-and-post.md`, word for word. The core keeps "no local paths, machine names or secrets" and "a deletion in words".
- **Cleanup 1–4** → `cleanup.md`, word for word. The core keeps three rules: only what carries the marker is removed; a file left in a tree is moved, not deleted; any difference from the record is reported.
- **Post 1–5:** show, re-check, ask every time, post what was chosen, never push → `draft-and-post.md`, word for word. A headless run now gives the handover's table before its text question, while the pre-approval holds. The core keeps:
  - a head that moved is not posted;
  - ask every time, naming the pull request, the candidate and the event;
  - an earlier yes never covers posting;
  - post only what was chosen, with the event chosen;
  - the viewer's own pull request gets only `COMMENT`;
  - the never-push list, among the rules for the whole review.
- **Review handover 1–4** → the core, word for word; the script's path is now `${CLAUDE_SKILL_DIR}`.

**Evidence** (`docs/plugin-behavior-tests.md`, "3.3, ticket 06"):
- **The deterministic suites:** `scripts/test.sh` passes 9 of 9 with 0 skipped, on Python 3.14.6 and 3.9.6. Every new static check failed first: on 3.2.1's file, on a planted `.pyc`, or before its text existed.
- **Live run 1, on `8fbdca2`:**
  - `run_checks.py` ran with no denial in the turn that invoked the skill.
  - The model put the check run and the risk reviewer in the background, and their notifications began new turns. There, `review_payload.py` and the pre-approved `gh pr view` were refused.
  - The criterion was unmet, and the finding led to `65c1388`.
- **Live run 2, on `65c1388`:**
  - The whole review stayed in one turn.
  - `run_checks.py`, `review_payload.py` (twice) and `batch_report.py` ran with no denial. The handover printed the batch report as the script wrote it.
  - The six denials were all the harness's settings acting on other commands.
  - `post_reviews.py` needs an answer, which a headless run gets in a later turn. The core says that turn runs under the user's permission settings.
- **Both runs:** nothing reached GitHub (the shims logged no write, and #7 has no review), and the clone's status and worktree list were unchanged.

**Review.** The two-axis review of `bb5a825` found 9 Standards findings and 7 Spec findings, each checked against the code and the docs.
- Acted on in `8fbdca2`:
  - the gates and must-nots that lived only in references;
  - the headless post outside the grant;
  - the wrong reason on the bytecode guard;
  - "20" hard-coded as the limit;
  - the `review.md` name, which also meant the draft preview;
  - the glossary's "sensitive" and the handover's words;
  - the ambiguous "(ticket 06)".
- Not acted on, per decision 12 (these are not correctness or requirement gaps): the duplicated test helper, the negative greps' output, the must-holds written twice (the spec puts them first, in the core), and the path styles and rule forms.

**Open.**
- Decision 23 waits for the user's sign-off.
- **Batches:** a batch's later turns (rechecks, rebuilt payloads, the handover's table, posting) run under the user's permission settings, and the docs don't say whether the grant covers a subagent's own script calls. Ticket 07's live batch will show it. Letting the gate hook allow the four scripts while a `pr-review` declaration holds would cover both; that is a sensitive change and needs its own grill.
- **A bug from 3.2.1:** `review_payload.py` wraps a suggestion in a fixed three-backtick fence (lines 185–186 and 216), so a suggestion that holds its own fenced block ends early on GitHub. Live run 2 found it; it is not routed yet.
- **Headroom:** the core is 150 bytes under the bound. Ticket 07 adds to it, so ticket 08's shorter descriptions should come first, or ticket 07 moves text into `batch.md`.
- **The temp directory:** default mode refuses 3.2.1's `${TMPDIR:-/tmp}` Checkout wording ("Contains expansion"), and both runs worked around it. Ticket 10's pre-loaded facts are the place to give skills the temp directory.
