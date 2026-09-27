# 12: Unblocked tickets built in parallel

**What to build:** When two or more tickets have no open blockers, `implement` offers to build them at once.
- **Setup:**
  - The user picks the tickets.
  - Each ticket gets its own worktree from local HEAD, on its own branch, and a background subagent that runs `implement`'s steps without questions.
- **Limits:** at most half the machine's cores, and at most 20, run at once.
- **Integration:** the main session integrates finished tickets one at a time, runs the full suite after each, and records each ticket's state in the progress file.

**Blocked by:** 05 (Specs, tickets and builds keep the progress file); 11 (The quality bar in the definition of done; reviews scaled to risk)

**Status:** done

- [x] The offer appears only when two or more tickets are unblocked. The user picks them in one multi-select question.
- [x] Each worktree is created under `.claude/worktrees/` from local HEAD, so unpushed commits such as the spec are present. Each is on a branch named for its ticket.
- [x] Concurrency never exceeds half the cores, 20, or the number of tickets picked.
- [x] Integration is one ticket at a time onto the base branch, with the full suite after each, then the definition of done on the integrated candidate.
- [x] Must not happen:
  - a ticket with an open blocker is offered;
  - a worktree is missing an unpushed commit;
  - a failed ticket blocks the others or lands on the base branch. It stays on its branch with its handover and is reported.
- [x] The progress file shows each parallel ticket's state. A `/clear` mid-run resumes with the right tickets pending.

**How to verify:**
- `scripts/test.sh`.
- A headless run over a fixture repository with three unblocked tickets and an unpushed spec commit. It should produce three worktrees from HEAD and three branches, integrated one at a time with the suite green after each.
- The same run with one ticket made to fail. The other two still integrate, and the failed one stays on its branch.

## Comments

Built 2026-09-27 on local `main`, not pushed. The commits:
- `a71e934`, the build.
- `fcf1729`, the review fixes, per-agent declarations among them.
- `f3f246c`, `008d07f` and `d786b63`, fixes from the live runs: the harness's core count, when a ticket is `building`, and the shell forms Claude Code asks about.
- The commit carrying this record.

**What shipped.**
- **The offer.** `implement`'s opening names `references/parallel.md` ("read this when two or more tickets are unblocked, before the gate's question, and to resume a parallel run"). Three trims paid for the line, since `implement` had 27 bytes left; it is now 10,954 bytes.
  - A ticket is offered when every ticket it is blocked by is done, never with an open blocker.
  - The offer is one AskUserQuestion with `multiSelect: true`, and only when two or more are unblocked and the request names no one ticket.
  - Picking two or more is the yes for the whole run. Picking one goes on as any ticket.
- **The run** (the reference):
  - **Setup.** The slots are half the cores, at most four, at most the tickets picked. `.claude/worktrees/` is ignored in a commit of its own. The base is HEAD. One worktree per ticket (`git worktree add -b <feature>/<NN>-<slug> .claude/worktrees/<feature>-<NN> <base>`), each checked to print the base. Never Claude Code's own worktree tools, which branch from the remote's default branch.
  - **Builders.** Each gets the facts, never a plan. It invokes `implement` and follows the section For a builder:
    - no questions, no progress file, no record commit;
    - only its own worktree and branch, with `git -C` for git, no `cd` beside git, and no `$` in a command;
    - never skip a review;
    - commit everything, then a first line of `Ticket <NN>: built at <sha>` or `Ticket <NN>: failed: <reason>`.
  - **Integration.** One ticket at a time. The merge (`git -C <worktree> checkout --detach <base-branch>`, then `merge --no-ff`) and the full suite run in the ticket's worktree, then `git merge --ff-only` on the base branch. The worktree and the merged branch are removed after, never forced. A failed ticket goes back on its branch, keeps its worktree and handover, and is reported.
  - **The progress file.** Only the main conversation writes it: `Ticket` lists the run's tickets, and `## Parallel` holds each one's state. It is committed with the run's record.
  - **Resuming.** Each state is checked against git. The pending tickets start first, then the built ones are integrated. A building ticket's builder is waited for, since a `/clear` doesn't stop it; when nothing shows it running, the user is asked.
  - **The end.** The record commit, the definition of done where no worktree sits inside the tree it searches, and one handover.
- **The gate** (decision 42, the user's choice): a subagent's own declaration covers that subagent alone and outlives the main conversation's requests (`seams_gate.declared_for`).
- **The glossary** gains *Parallel run* and *Builder*. *Declaration* notes the subagent's own. The README, `routing.md` and `progress-file.md` describe the run.
- **The scenario `resume-parallel`** plants a run stopped halfway on the shared shop-basics feature. The harness now allows a resumed run's reads, git steps and core count.

**Evidence** (`docs/plugin-behavior-tests.md`, "3.3, ticket 12"):
- **The suites.** `scripts/test.sh` passes 9 of 9 on every commit, on Python 3.14.6 and 3.9.6. The Python suites also pass on 3.12.13. Each new check failed first.
- **The probes.**
  - vitest in the main checkout collects every worktree's tests, ignored or not.
  - A background agent survives `/clear`, and its report reaches the cleared conversation (2.1.283, Haiku 4.5).
- **The resume scenario,** paid, on the user's yes, Opus 5.5, three runs each:
  - `fcf1729`: 0 of 3, 3 errors, each the core count denied by the harness's settings.
  - `f3f246c`: 2 of 3, 1 error, Claude Code's `sed` check. Every run started ticket 03's builder, told its worktree, before its first change.
- **Two headless runs from scratch,** paid, Opus 5.5:
  - On `f3f246c`: all three tickets built, reviewed, and integrated one at a time with the suite green in each worktree; the definition of done passed 26 of 26 tests on the record commit. $4.19, 239 s.
  - On `008d07f`, with ticket 02 refused at a pre-commit hook: 01 and 03 were integrated, and 02 stayed on its branch with its staged work and was reported. The definition of done ran in a worktree made at the candidate. $4.02, 253 s.

**Review of `a71e934`.** Matt Pocock's `code-review` (Standards, Spec), a correctness reviewer and a security reviewer, as read-only `feature-dev:code-reviewer` agents. The session's agent list predates the Seams agents. The run removes worktrees and deletes branches, so it got the security review. `/simplify` was offered on the 519-line diff, and the user declined.
- **Acted on in `fcf1729`:**
  - a builder's declaration opened the gate for the user's unrouted message (security and spec; user story 48);
  - the harness would deny a resumed run's git steps;
  - the tasks-graders check was vacuous for the new scenario;
  - a sentence that read backwards on `worktree.baseRef`.
- **The user's call:** decision 42, per-agent declarations.
- **Recorded as mine:** decisions 37 to 41: the reference and the trims, four builders at most, integration in the ticket's worktree, the main conversation alone writing the progress file, and the resume order.
- **Not acted on:**
  - The spec review's wish for the full runs as a committed eval. The harness stops at a run's first change by design, and a full run costs dollars; the runs are recorded instead.
  - The fix's security review: no check on which kind of subagent may keep a declaration, and a forged ledger entry now persisting. The first is the design the user chose, covering only that agent's own calls. The second adds nothing to a forgery that was already possible, since writes under the temp directory are scratch.

**Open.**
- Tool writes into the gate's ledger directory are scratch, so any agent can plant a declaration. Refusing writes there would close it; it is a gate change.
- A builder's `verification-before-completion` still marks the whole session verified, as any subagent's did before.
- Whether Claude Code ever reuses an `agent_id` for a different subagent is unconfirmed; decision 42 assumes it doesn't.
- Not exercised live:
  - the offer as a multi-select question;
  - a resume after a restart;
  - a merge conflict at integration;
  - builders' permission prompts in an interactive session;
  - the eval path of `resume-parallel`.
- The harness still loads the synced Superpowers copy (`sp=15`), as ticket 10 found.
