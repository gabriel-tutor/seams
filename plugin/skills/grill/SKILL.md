---
name: grill
description: Use before building a feature or changing behavior, when a plan or design needs stress-testing, or when another skill says to call grilling
---

# Grill

This is Matt Pocock's grilling, presented as clickable questions, every independent one at once, with its record kept in the feature's progress file so that `/clear` or compaction loses nothing.

**Effort** `${CLAUDE_EFFORT}`: every step, gate and check runs at every level; at `low`, skip only the count of decisions left.

**Repository facts.** As this skill starts, the Seams hook adds the branch, the short HEAD, the first lines of the status and the progress files. They are a snapshot: once git may have moved (a commit, a checkout, a new worktree, a resumed session), run git again, and look up yourself any fact the hook did not give.

## Method

1. Invoke Matt Pocock's `grilling` skill with the Skill tool, and follow its method exactly:
   - Keep the design tree and its frontier.
   - Find facts yourself, through `matt-pocock-workflow:scout` agents: when a frontier question needs facts from the code or the docs, start one scout per independent question, all in one message, however small the codebase. A fact already in view needs no scout, and neither do the reads under Resuming.
   - Put every decision to the user.
   - Keep going until the frontier is empty and the user confirms you share an understanding. Nothing gets built before that confirmation.

   If `grilling` isn't available, tell the user Matt Pocock's skills aren't installed, and stop.
2. In a git repo, also invoke `domain-modeling`, and update `CONTEXT.md` and the ADRs as decisions land.

## Presentation

This replaces grilling's round format. Each of your turns has exactly two parts, in this order:

1. **Facts:** the facts from the code or docs that this round's questions depend on, in a few lines. If it helps, add how many decisions remain after this round, as a number ("3 more decisions after these").
2. **Questions:** ask every independent question on the frontier at once, up to four in one AskUserQuestion call, each with 2–4 options. Questions are independent when no answer changes another's options; a question that depends on one of them waits for the next round. A gate, security or destructive question is asked alone, in a call of its own. Put your recommended answer first and end its label with "(Recommended)". Free-text answers arrive through "Other". If AskUserQuestion isn't available, write the same questions in text: each question, its options as a short list, and your recommendation. Then end your turn.

The rest of the frontier stays in your design tree until its turn; the count in the facts is all the user sees of it. Take questions from the frontier in dependency order. A decision the code or an earlier answer already settles is not a question; the fact goes in the facts section, and the frontier moves on. For anything that will be built, one frontier question is which seams the tests go at, because Matt Pocock's `tdd` tests only at agreed seams.

## Progress file

The grill's record is the feature's progress file, `.scratch/<feature>/progress.md` at the repository root. Read its format in `${CLAUDE_PLUGIN_ROOT}/skills/using-matt-pocock-skills/references/progress-file.md` before the first write.

- Create it at the first settled decision: `Status: active`, `Stage: designing`, `Next` saying what the grill asks next, `Updated` today.
- After each answered round, before asking the next, update it: the answers into Decisions, the frontier into Open questions, the facts worth keeping into Facts, then `Next` and `Updated`.
- Decisions and pointers only: never a secret, a credential, a token or personal data.

## Resuming

When the resume note or the user points at a feature whose progress file says `Stage: designing`, continue that grill instead of starting a new one:

1. Read the progress file, then the spec, the tickets, `CONTEXT.md` and the ADRs where they exist, and the git state (the repository facts, `git log --oneline -5`).
2. Where they disagree with the file (a decision the code contradicts, a spec or a commit the file doesn't mention), report the mismatch in the facts and settle it with the user before going on.
3. Settled decisions are not asked again. Ask the recorded open questions first, then continue down the frontier.

## Coverage

Before you call the frontier empty, check the design tree against the design lens in `references/design-lens.md` (next to this file). Any axis that applies to this change and is still unsettled is a branch you missed: add it to the frontier. Axes that don't apply are skipped silently. The lens scales with the change, as it says.

## Done

The grill is done when the frontier is empty, the lens has been checked, every branch has been visited, and the user has confirmed the shared understanding. Ask for that confirmation with AskUserQuestion, naming the next step from the bootstrap's routing that a yes starts, such as `tdd`, `matt-pocock-workflow:implement` or `matt-pocock-workflow:to-spec`; when the work will be built through `implement`, ask in the same call where: a worktree through `matt-pocock-workflow:using-git-worktrees` (recommended for a feature) or the current branch. The yes starts the continuous flow (the bootstrap's flow rule): record the confirmation and where to build under Decisions, set the progress file's `Next` to that step, and go on to it at once, without asking again. When that step is `tdd` (a bounded change: no spec, no `implement`, so no later skill keeps the file), `Next` also says to set `Status: done` in the commit that ships the change, and you do so when you make that commit. For a sensitive change, `Next` also names the reviews it needs before it ships: `code-review` and a security review (`/security-review`, or a `matt-pocock-workflow:reviewer` agent where it can't run).
