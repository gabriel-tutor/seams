---
name: implement
description: Use when an agreed design, spec or ticket is ready to build
---

# Implement

Build what a spec, a ticket or an agreed design describes: tests first at the agreed seams, a commit, a review of that commit, the definition of done with evidence, and a handover, in this order, since the review sees only what is committed.

**Shared rules:** `${CLAUDE_PLUGIN_ROOT}/skills/using-matt-pocock-skills/references/rules.md`, read when a step names one of its sections. **Effort** `${CLAUDE_EFFORT}`: at `low`, skip only the offer to add a run command to the README (shared rules: Effort).

**Repository facts.** The Seams hook adds them as this skill starts (shared rules: Repository facts).

**Delegation.** Scouts and reviewers as a feature's row sets them (shared rules: Process by size and risk); this context keeps the decisions and the edits.

**Reviews.** `${CLAUDE_SKILL_DIR}/references/reviews.md`: read this when the review starts, and again after a compaction or `/clear`.

**Parallel tickets.** `${CLAUDE_SKILL_DIR}/references/parallel.md`: read this when two or more tickets are unblocked, before the gate's question, and to resume a parallel run.

## Gate

Before reading the work, settle which spec, ticket or design you build, and where, asking only what nothing settled. The flow (shared rules: The continuous flow) brings the next unblocked ticket, or the parallel offer when two or more are; where is what the user said, else the branch the last record names, else what the confirmation recorded. Otherwise offer a worktree through `matt-pocock-workflow:using-git-worktrees` (shared rules: Worktrees), which asks for consent, or the current branch, and wait for the answer. A ticket resumed as its progress file records skips this (Resuming, below).

Then note the starting point for the review's fixed point: the branch and HEAD from the repository facts (in a new worktree, its own), and the base branch.

## Progress file

The feature's progress file, `.scratch/<feature>/progress.md` beside its spec, in the format `${CLAUDE_PLUGIN_ROOT}/skills/using-matt-pocock-skills/references/progress-file.md` describes, lets a fresh context continue this ticket. Create it if the feature has none, keep it current at each step below, with `Updated` set to today, and stage it by name with each of the ticket's commits.

- **After the gate:** `Ticket` is this ticket's number, and `Next` names the branch and the starting commit.
- **With each commit:** `Next` says what the commit does and the step that follows, naming the branch and the SHAs it needs: the review against the fixed point, the fixes, or the definition of done. A commit can't name itself, so `Candidate` is the commit under review, set when the review starts. After the review, list the findings you act on under `## Review`, one line each with its file and line, until they are fixed.
- **The record:** just before the definition of done, commit the file with `Stage` set to the stage reached (built on a branch, integrated on the base branch), this ticket marked done in its ticket list, `Ticket`, `Candidate` and `## Review` removed, and `Next` naming the next unblocked ticket, its branch, and whether to `/clear` before it. When nothing is left to build (the last ticket, or a design built in one go), set `Status: done` instead, unless the spec has a Release section; then `Next` is the release, through `matt-pocock-workflow:release`. An unmet row puts the ticket back (Definition of done, below).

## Resuming

When the resume note or the user points at a ticket its progress file records in progress (`Ticket` set), continue it instead of starting over:

1. Read the progress file, then the ticket and the spec, and the git state: the repository facts and `git log --oneline -5`.
2. Where they disagree with the file (the branch is not the one `Next` names; the history after `Candidate`, or after the starting commit before a review, holds commits the file doesn't account for; the ticket is already done), report the mismatch and ask how to go on. Never act on the file instead.
3. Where they agree, what started the ticket still covers it: don't ask the gate question again. Take the starting point and the fixed point from `Next` and the history, and continue from the step `Next` names.

## Build

1. **Read the work.** Fetch the ticket and its spec through the issue tracker (`docs/agents/issue-tracker.md`), then `CONTEXT.md` and any ADR in the area you're touching. Work in the glossary's vocabulary, and check third-party code against its docs (shared rules: Official docs).
2. **Test first.** Invoke `tdd` (Matt Pocock's, bare name) with the Skill tool and follow it one slice at a time at the agreed seams: the spec's Testing Decisions, the ticket, or what the grill settled. Seams settled there are not asked again; only when none was ever agreed, ask once with AskUserQuestion before the first test. If `tdd` isn't available, tell the user Matt Pocock's skills aren't installed, and stop.
3. **Check as you go.** Run the typecheck and the single test file you're working in regularly, and the full suite once at the end. Use the repo's real scripts.

## Commit

1. Stage the ticket's files **by name**: `git add <path> [<path>...]`. Never `git add -A`, `git add .` or `git commit -a`.
2. Anything else that `git status --short` shows dirty or untracked is **excluded**: list those paths in your reply as excluded, and never stage, stash or commit them here.
3. Commit to the branch settled above, with a message that says what changed and why, and names the ticket. If a pre-commit hook rewrites a staged file, re-stage that file by name and commit again; never `--no-verify`.
4. HEAD is now the **candidate**: note `git rev-parse --short HEAD`.

## Review

1. **Fixed point.** On a branch, `git merge-base <base> HEAD`; on the base branch itself, the starting commit noted at the beginning. The candidate is HEAD; do not change it while the review runs.
2. **Empty diff.** If `git diff --stat <fixed-point>...HEAD` prints nothing, there is nothing to review: say why (nothing committed yet, or the fixed point is HEAD) and fix that first.
3. Invoke `code-review` (Matt Pocock's, bare name) with the Skill tool, passing the fixed point. It diffs `<fixed-point>...HEAD` and reviews along its two axes, Standards and Spec.
4. **By size and risk**, the other reviews the change's row names (shared rules: Process by size and risk), run as the reference says.

## Review fixes

1. Judge each finding through `matt-pocock-workflow:receiving-code-review`: verify it against the code before acting, and say which findings you are not acting on and why. Act only on correctness bugs and gaps against the ticket or spec; nothing else changes because a reviewer suggested it.
2. For the findings you act on: fix, commit by the same rules (by name, exclusions listed), and re-run the checks the fix affects: the test file at that seam for a change in one place, the full suite and the typecheck when more files changed.
3. The new HEAD is the candidate; note its SHA.

## Definition of done

Before claiming the work is done, commit the ticket's record (Progress file, above), so that HEAD is the candidate everything below refers to. Then run `matt-pocock-workflow:verification-before-completion` and confirm each item below. Present the evidence as a table: the first row names the candidate SHA the evidence was gathered on, then one row per item with the command run or the check made, and the line that proves it. A Quality bar row (Failure paths to Rollback) that doesn't apply says `n/a` and why, in one line.

| Item | What counts |
| --- | --- |
| Candidate | `git rev-parse --short HEAD` after the record commit, and `git status --short` |
| Tests | the tests at the agreed seams pass, and the full suite passes |
| Typecheck and lint | typecheck passes; lint passes if the repo has one |
| Acceptance criteria | every criterion on the ticket or spec is met, checked one by one |
| Failure paths | each new way the change can fail has a test |
| Security | no secret in the diff; on a sensitive change, each security finding fixed or left with a reason |
| Performance | a hot path or a growing collection, measured before and after |
| Observability | a new failure is logged at its boundary or shown to the user |
| Docs | updated where behavior changed: the README's run or usage lines, the glossary if a term moved |
| Rollback | how this candidate is undone: a revert, a flag or a down-migration |
| No debug leftovers | no tagged logs, commented-out code, throwaway scripts, or `.only` on a test |
| Commit message | says what changed and why, and names the ticket |

Anything unmet is not done: fix it, or say plainly that it's unmet and why. Either way, first put `Ticket` back in the progress file and set `Next` to what is unmet, committed with the fix or on its own, so that a fresh context resumes this ticket instead of the next.

## Handover

The ticket ends with the handover: exactly these four sections, in this order, and not finished until the fourth is written:

1. **Run it.** The exact commands to start and check the work, from the repo's real scripts or README; if it has none, the one-line command that works, and an offer to add it to the README.
2. **Try it.** One short walkthrough per acceptance criterion, in the user's words: what to do, and what they should see. Refer to things by their glossary names. For a user-facing change to a runnable app, offer `/verify`, which only the user can start.
3. **What changed.** The candidate SHA, the files and public interfaces touched, in a few lines, and any decision you made that the ticket didn't settle.
4. **Next.** First the stage reached (shared rules: Stages): a ticket that ends here is *built* or *integrated*. Then name the next unblocked ticket, or say there is none. Then say whether to `/clear` before it (it is unrelated to this one, or this session is heavy) or to continue here (it builds on this one). Continuing here with every row met, go on unoffered to the record's `Next`: that ticket, or with none left `matt-pocock-workflow:finishing-a-development-branch` for a branch's candidate, else any release.

Adapted from Matt Pocock's `implement` skill (github.com/mattpocock/skills, `skills/engineering/implement` at commit `3cca18b368ae95cdbdebbff572ccafa662551015`), MIT License, Copyright (c) 2026 Matt Pocock; the full notice is in this plugin's `THIRD_PARTY_NOTICES.md`.
