# 12: Unblocked tickets built in parallel

**What to build:** When two or more tickets have no open blockers, `implement` offers to build them at once.
- **Setup:**
  - The user picks the tickets.
  - Each ticket gets its own worktree from local HEAD, on its own branch, and a background subagent that runs `implement`'s steps without questions.
- **Limits:** at most half the machine's cores, and at most 20, run at once.
- **Integration:** the main session integrates finished tickets one at a time, runs the full suite after each, and records each ticket's state in the progress file.

**Blocked by:** 05 (Specs, tickets and builds keep the progress file); 11 (The quality bar in the definition of done; reviews scaled to risk)

**Status:** ready-for-agent

- [ ] The offer appears only when two or more tickets are unblocked. The user picks them in one multi-select question.
- [ ] Each worktree is created under `.claude/worktrees/` from local HEAD, so unpushed commits such as the spec are present. Each is on a branch named for its ticket.
- [ ] Concurrency never exceeds half the cores, 20, or the number of tickets picked.
- [ ] Integration is one ticket at a time onto the base branch, with the full suite after each, then the definition of done on the integrated candidate.
- [ ] Must not happen:
  - a ticket with an open blocker is offered;
  - a worktree is missing an unpushed commit;
  - a failed ticket blocks the others or lands on the base branch. It stays on its branch with its handover and is reported.
- [ ] The progress file shows each parallel ticket's state. A `/clear` mid-run resumes with the right tickets pending.

**How to verify:**
- `scripts/test.sh`.
- A headless run over a fixture repository with three unblocked tickets and an unpushed spec commit. It should produce three worktrees from HEAD and three branches, integrated one at a time with the suite green after each.
- The same run with one ticket made to fail. The other two still integrate, and the failed one stays on its branch.
