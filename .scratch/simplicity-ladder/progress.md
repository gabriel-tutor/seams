# Progress: the simplicity ladder (ponytail's discipline in Seams)

Status: active
Stage: designing
Next: The grill's next round: which of ponytail's parts come over (the ladder and rules, the shortcut comment, the review lens, the debt ledger), where each lives in Seams, the name, and the test seams.
Updated: 2026-10-04

## Decisions

1. Release 4.0.0 first (seams-revamp ticket 09), then this ships as 4.1.0 with its own eval check, so 4.0.0's proof stays valid (the user's choice, 2026-10-04).
2. The discipline applies at the build and review steps, not every session: the ladder lives in the shared rules, `implement` and `tdd` work follow it while writing code, and the reviews check against it; no session-start injection, no new hook (the user's choice).
3. One level, ponytail's default `full` (the ladder enforced); no lite/full/ultra dial, since Seams already scales process by size and risk (the user's choice).

## Open questions

- Which parts come over, where each lives, the term, the test seams; the coverage lens.

## Facts

- ponytail (github.com/dietrichgebert/ponytail, MIT, "Copyright (c) 2026 DietrichGebert", v4.10.3 at c982cd4): skills/ponytail/SKILL.md (6,637 bytes) is the ladder (need it at all, already in the codebase, stdlib, native platform, installed dependency, one line, minimum code), its rules (no unrequested abstractions, shortest working diff once the problem is understood, a `ponytail:` comment naming a shortcut's ceiling and upgrade path), root-cause bug fixes (grep every caller), output "[code] → skipped: [X], add when [Y]", never lazy on trust-boundary validation, data-loss handling, security, accessibility or understanding the problem, and one runnable check for non-trivial logic. Node hooks inject it at SessionStart and SubagentStart and track a level per project; its other skills: review (over-engineering findings on a diff, `L<n>: <tag> <what>. <replacement>.`, ends `net: -<N> lines possible.`), audit (the same over the repo), debt (a ledger of `ponytail:` comments), gain (a static benchmark scoreboard), help (a reference card).
- Its evidence: single-shot benchmarks claim 80-94% less code and 42-75% cheaper, which its README says overstates the win; headless Claude Code sessions on a FastAPI template (Haiku 4.5, 12 feature tasks, n=4): -54% lines, -20% cost, -27% time, 100% on 6 safety tasks; a bare "yagni one-liner" prompt escaped a path-traversal check, ponytail did not. Its "reuse" rung and "grep every caller" rule were added after the agent patched only the function a ticket named (results/2026-06-22).
