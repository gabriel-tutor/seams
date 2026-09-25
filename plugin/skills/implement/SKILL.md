---
name: implement
description: Use when an agreed design, spec or ticket is ready to build
---

# Implement

Build the work a spec, a ticket or an agreed design describes: tests first at the agreed seams, a commit, a review of that commit, the definition of done with evidence, and a handover. The steps run in this order; the review sees only what is committed, which is why the commit comes before it.

## Gate

Before reading anything, confirm which spec, ticket or agreed design you're building, and where. Offer a worktree through `matt-pocock-workflow:using-git-worktrees`, which asks for consent, or the current branch. Wait for a yes. Skip this only when the user's last message already names both, when a yes earlier in this request covered this ticket and where it goes ("build all three on main"), or when you resume a ticket in progress whose state matches its progress file (Resuming, below).

Then note the starting point, which the review's fixed point needs: the current branch, its base branch, and `git rev-parse HEAD`.

## Progress file

The feature's progress file, `.scratch/<feature>/progress.md` beside its spec, is how a fresh context continues this ticket after `/clear` or compaction. Read its format in `${CLAUDE_PLUGIN_ROOT}/skills/using-matt-pocock-skills/references/progress-file.md` before the first write, and create the file if the feature has none. Keep it current at each step below, with `Updated` set to today, and stage it by name with each of the ticket's commits. Decisions and pointers only: never a secret, a token or personal data.

- **After the gate's yes:** `Ticket` is this ticket's number, and `Next` names the branch and the starting commit.
- **After each commit:** `Candidate` is its short SHA, and `Next` is the step that follows, with the SHAs it needs: the review against the fixed point, the fixes, or the definition of done. After the review, list the findings you act on under `## Review`, one line each with its file and line, until they are fixed.
- **The record:** just before the definition of done, commit the file with `Stage` set to the stage reached (built on a branch, integrated on the base branch), this ticket marked done in its ticket list, `Ticket`, `Candidate` and `## Review` removed, and `Next` naming the next unblocked ticket and whether to `/clear` before it. When nothing is left to build (the last ticket, or a design built in one go), set `Status: done` instead, unless the spec has a Release section; then `Next` is the release, through `matt-pocock-workflow:release`.

## Resuming

When the resume note or the user points at a ticket that its progress file records in progress (`Ticket` set), continue it instead of starting over:

1. Read the progress file, then the ticket and the spec, and the git state: the branch, `git status --short`, `git log --oneline -5`.
2. Where they disagree with the file (another branch, a `Candidate` not in the history, commits after it that the file doesn't mention, a ticket already done), report the mismatch and ask how to go on. Never act on the file instead.
3. Where they agree, the yes given when the ticket started still covers it: don't ask the gate question again. Take the starting point and the fixed point from `Next` and the history, and continue from the step `Next` names.

## Build

1. **Read the work.** Fetch the ticket and the spec it came from through the issue-tracker workflow (`docs/agents/issue-tracker.md`), then `CONTEXT.md` and any ADR in the area you're touching. Work in the glossary's vocabulary.
2. **Test first.** Invoke `tdd` (Matt Pocock's, bare name) with the Skill tool and follow it one slice at a time at the agreed seams: the spec's Testing Decisions, the ticket, or what the grill settled. Seams settled there are not asked again; only when none was ever agreed, ask once with AskUserQuestion before the first test. If `tdd` isn't available, tell the user Matt Pocock's skills aren't installed, and stop.
3. **Check as you go.** Run the typecheck and the single test file you're working in regularly, and the full suite once at the end. Use the repo's real scripts.

## Commit

1. Stage the ticket's files **by name**: `git add <path> [<path>...]`. Never `git add -A`, `git add .` or `git commit -a`.
2. Anything else that `git status --short` shows dirty or untracked is **excluded**: list those paths in your reply as excluded, and leave them alone. They are never staged, stashed or committed here.
3. Commit to the branch settled above, with a message that says what changed and why, and names the ticket. If a pre-commit hook rewrites a staged file, re-stage that file by name and commit again; never `--no-verify`.
4. HEAD is now the **candidate**: note `git rev-parse --short HEAD`.

## Review

1. **Fixed point.** On a branch, the merge-base with its base branch: `git merge-base <base> HEAD`. On the base branch itself, the starting commit noted at the beginning (`git merge-base` would return HEAD there). The candidate is HEAD; do not change it while the review runs.
2. **Empty diff.** Run `git diff --stat <fixed-point>...HEAD` first. If it prints nothing, there is nothing to review: report that, say why (nothing committed yet, or the fixed point is HEAD), and fix that before going on. Never run the review on an empty diff.
3. `code-review` reads `docs/agents/issue-tracker.md`; if the repo has none, offer `matt-pocock-workflow:foundations` before the review.
4. Invoke `code-review` (Matt Pocock's, bare name) with the Skill tool, passing the fixed point. It diffs `<fixed-point>...HEAD` and reviews along its two axes, Standards and Spec.

## Review fixes

1. Judge each finding through `matt-pocock-workflow:receiving-code-review`: verify it against the code before acting, and say which findings you are not acting on and why.
2. For the findings you act on: fix, then commit the fix by the same rules as above (by name, exclusions listed), and re-run the checks the fix affects: the test file at that seam for a change in one place, the full suite and the typecheck when more than one file changed.
3. The new HEAD is the candidate; note its SHA.

## Definition of done

Before claiming the work is done, commit the ticket's record (Progress file, above), so that HEAD is the candidate everything below refers to. Then run `matt-pocock-workflow:verification-before-completion` and confirm each item below, with the command output as evidence. Present the result as a table: the first row names the candidate SHA the evidence was gathered on, then one row per item with the command run and the line of its output that proves it.

| Item | What counts |
| --- | --- |
| Candidate | `git rev-parse --short HEAD`, after the record commit |
| Tests | the tests at the agreed seams pass, and the full suite passes |
| Typecheck and lint | typecheck passes; lint passes if the repo has one |
| Acceptance criteria | every criterion on the ticket or spec is met, checked one by one |
| No debug leftovers | no tagged logs, commented-out code, throwaway scripts, or `.only` on a test |
| Docs | updated where behavior changed: the README's run or usage lines, the glossary if a term moved |
| Commit message | says what changed and why, and names the ticket |

Anything unmet is not done: fix it, or say plainly that it's unmet and why.

## Handover

Your closing message is the handover. It has exactly four sections under these four headings, in this order, and it is not finished until the fourth is written:

1. **Run it.** The exact commands to start and to check the work, taken from the repo's real scripts or README. If the repo has no run or verify command, give the one-line command that works and offer to add it to the README.
2. **Try it.** One short walkthrough per acceptance criterion, in the user's words: what to do, and what they should see. Refer to things by their glossary names.
3. **What changed.** The candidate SHA, the files and public interfaces touched, in a few lines, and any decision you made that the ticket didn't settle.
4. **Next.** First the stage reached, one of the six: designed, built, integrated, release-ready, deployed, operated. A ticket that ends here is *built* (the candidate is on a branch) or *integrated* (it is on the base branch); it is never "done" without the stage, and it is never *deployed* until `matt-pocock-workflow:release` has verified the running candidate. Then name the next unblocked ticket, or say there is none. Then say one of two things: `/clear` before it, because it is unrelated to this one or this session is already heavy; or continue in this session, because it builds on this one. If the candidate is on a branch, also offer `matt-pocock-workflow:finishing-a-development-branch`. A handover that stops at "What changed" is incomplete.

Adapted from Matt Pocock's `implement` skill (github.com/mattpocock/skills, `skills/engineering/implement` at commit `3cca18b368ae95cdbdebbff572ccafa662551015`), MIT License, Copyright (c) 2026 Matt Pocock; the full notice is in this plugin's `THIRD_PARTY_NOTICES.md`.
