# Progress: the simplicity ladder (ponytail's discipline in Seams)

Status: done
Stage: deployed
Next: None; Released 5.0.0 on 2026-10-05: staging pull request #16 at f72d7d2 green on all three jobs, main fast-forwarded 987c187 to f72d7d2 on the user's yes and its run 37309099015 green, tag v5.0.0; the user's Mac switched from matt-pocock-workflow@my-workflow-agent-skills to seams@seams 5.0.0, read in place, no old key or permission rule left; a session-start probe injects the seams: names and the ladder pointer (2,577 bytes). Rollback: reinstall 4.0.0 from tag v4.0.0 under its old name.
Updated: 2026-10-05

## Decisions

1. Release 4.0.0 first (seams-revamp ticket 09), then this ships as 4.1.0 with its own eval check, so 4.0.0's proof stays valid (the user's choice, 2026-10-04).
2. The discipline applies at the build and review steps, not every session: the ladder lives in the shared rules, `implement` and `tdd` work follow it while writing code, and the reviews check against it; no session-start injection, no new hook (the user's choice).
3. One level, ponytail's default `full` (the ladder enforced); no lite/full/ultra dial, since Seams already scales process by size and risk (the user's choice).

4. What comes over (the user's choice): the ladder and its rules (root-cause fixes that grep every caller; never lazy on trust-boundary validation, data-loss handling, security, accessibility or understanding the problem; the handover says what was skipped and when to add it), the shortcut comment naming a deliberate corner's ceiling and upgrade path, and a review lens for over-building. Not the debt ledger, nor ponytail's other skills (the listing has 1 character left).
5. The term is *Simplicity ladder* (the user's choice), in CONTEXT.md; ponytail credited in THIRD_PARTY_NOTICES.md and where the ladder is written.
6. The test seams (the user's choice): a new eval scenario, an over-build trap on the OrderKit fixture judged on the diff, run on 4.0.0 and the 4.1.0 candidate; and test_plugin.sh contract pins that the build and review steps name the ladder.

7. The ladder's text lives in its own reference, `plugin/skills/using-matt-pocock-skills/references/simplicity-ladder.md`, read only when code is written (implement, tdd) and when the reviews run, so spec, tickets and the grill never load it (ticket 13's cost) (the user's choice).
8. The correctness reviewer also checks the diff against the ladder, and an over-building finding (code the ticket didn't need, or a re-implementation of what the codebase, the standard library, a native feature or an installed dependency already does) counts as a gap and is fixed; no third reviewer (the user's choice).
9. A deliberate shortcut's comment uses the marker `ceiling:`, naming the ceiling and the upgrade path (the user's choice).
10. Design-lens points, mine (the user may overrule them): a bounded change routed to `tdd` reaches the ladder through one pointer line in the shared rules' process section; Seams' own checks (tdd at agreed seams, the process table) stand over ponytail's "one runnable check, no frameworks"; the handover keeps its four sections, "skipped: X, add when Y" going under What changed; the ladder never overrides a sensitive change's reviews, and the reviewer's over-building findings never delete trust-boundary validation, data-loss handling, security or accessibility code; no new dependency, no hook; rollback is reinstalling 4.0.0 or a revert; no ADR, nothing here being hard to reverse.

11. The user confirmed the shared understanding on 2026-10-04: the flow releases 4.0.0 first (seams-revamp ticket 09), then builds this through matt-pocock-workflow:implement in a new worktree (matt-pocock-workflow:using-git-worktrees) as 4.1.0.

12. Ships as 5.0.0 with the rename to `seams`, not as 4.1.0 (the user's choice, 2026-10-04; seams-rename decision 2).

## Open questions

- None.

## Facts

- ponytail (github.com/dietrichgebert/ponytail, MIT, "Copyright (c) 2026 DietrichGebert", v4.10.3 at c982cd4): skills/ponytail/SKILL.md (6,637 bytes) is the ladder (need it at all, already in the codebase, stdlib, native platform, installed dependency, one line, minimum code), its rules (no unrequested abstractions, shortest working diff once the problem is understood, a `ponytail:` comment naming a shortcut's ceiling and upgrade path), root-cause bug fixes (grep every caller), output "[code] → skipped: [X], add when [Y]", never lazy on trust-boundary validation, data-loss handling, security, accessibility or understanding the problem, and one runnable check for non-trivial logic. Node hooks inject it at SessionStart and SubagentStart and track a level per project; its other skills: review (over-engineering findings on a diff, `L<n>: <tag> <what>. <replacement>.`, ends `net: -<N> lines possible.`), audit (the same over the repo), debt (a ledger of `ponytail:` comments), gain (a static benchmark scoreboard), help (a reference card).
- Its evidence: single-shot benchmarks claim 80-94% less code and 42-75% cheaper, which its README says overstates the win; headless Claude Code sessions on a FastAPI template (Haiku 4.5, 12 feature tasks, n=4): -54% lines, -20% cost, -27% time, 100% on 6 safety tasks; a bare "yagni one-liner" prompt escaped a path-traversal check, ponytail did not. Its "reuse" rung and "grep every caller" rule were added after the agent patched only the function a ticket named (results/2026-06-22).
