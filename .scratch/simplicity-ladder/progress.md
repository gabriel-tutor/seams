# Progress: the simplicity ladder (ponytail's discipline in Seams)

Status: active
Stage: designing
Next: The grill's third round: where the ladder's text lives, which review carries the lens and whether its findings are acted on, the shortcut comment's marker; then the coverage lens and the confirmation.
Updated: 2026-10-04

## Decisions

1. Release 4.0.0 first (seams-revamp ticket 09), then this ships as 4.1.0 with its own eval check, so 4.0.0's proof stays valid (the user's choice, 2026-10-04).
2. The discipline applies at the build and review steps, not every session: the ladder lives in the shared rules, `implement` and `tdd` work follow it while writing code, and the reviews check against it; no session-start injection, no new hook (the user's choice).
3. One level, ponytail's default `full` (the ladder enforced); no lite/full/ultra dial, since Seams already scales process by size and risk (the user's choice).

4. What comes over (the user's choice): the ladder and its rules (root-cause fixes that grep every caller; never lazy on trust-boundary validation, data-loss handling, security, accessibility or understanding the problem; the handover says what was skipped and when to add it), the shortcut comment naming a deliberate corner's ceiling and upgrade path, and a review lens for over-building. Not the debt ledger, nor ponytail's other skills (the listing has 1 character left).
5. The term is *Simplicity ladder* (the user's choice), in CONTEXT.md; ponytail credited in THIRD_PARTY_NOTICES.md and where the ladder is written.
6. The test seams (the user's choice): a new eval scenario, an over-build trap on the OrderKit fixture judged on the diff, run on 4.0.0 and the 4.1.0 candidate; and test_plugin.sh contract pins that the build and review steps name the ladder.

## Open questions

- Where the ladder's text lives; the review lens's reviewer and whether its findings are acted on; the shortcut comment's marker; the coverage lens.

## Facts

- ponytail (github.com/dietrichgebert/ponytail, MIT, "Copyright (c) 2026 DietrichGebert", v4.10.3 at c982cd4): skills/ponytail/SKILL.md (6,637 bytes) is the ladder (need it at all, already in the codebase, stdlib, native platform, installed dependency, one line, minimum code), its rules (no unrequested abstractions, shortest working diff once the problem is understood, a `ponytail:` comment naming a shortcut's ceiling and upgrade path), root-cause bug fixes (grep every caller), output "[code] → skipped: [X], add when [Y]", never lazy on trust-boundary validation, data-loss handling, security, accessibility or understanding the problem, and one runnable check for non-trivial logic. Node hooks inject it at SessionStart and SubagentStart and track a level per project; its other skills: review (over-engineering findings on a diff, `L<n>: <tag> <what>. <replacement>.`, ends `net: -<N> lines possible.`), audit (the same over the repo), debt (a ledger of `ponytail:` comments), gain (a static benchmark scoreboard), help (a reference card).
- Its evidence: single-shot benchmarks claim 80-94% less code and 42-75% cheaper, which its README says overstates the win; headless Claude Code sessions on a FastAPI template (Haiku 4.5, 12 feature tasks, n=4): -54% lines, -20% cost, -27% time, 100% on 6 safety tasks; a bare "yagni one-liner" prompt escaped a path-traversal check, ponytail did not. Its "reuse" rung and "grep every caller" rule were added after the agent patched only the function a ticket named (results/2026-06-22).
