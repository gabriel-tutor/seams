# Progress: sleep mode runs the full Seams flow unattended

Status: active
Stage: designing
Next: The grill's next round: where the unattended rule lives, who runs the flow per ticket, whether the gate enforces it for builders, and the overnight merge bar (asked alone).
Updated: 2026-10-14

## Decisions

1. Answers (Gabriel's choice, 2026-10-14): overnight, every question a Seams skill would ask, product and business calls included, takes its recommended option; each one is recorded as auto-answered for his morning review.
2. Scope (Gabriel's choice): his own sleep mode first (~/.claude/skills/sleep-mode), proven over a night or two; the team's /clarewood:sleep-mode follows in a later PR. The user's standing rules hold: build in a worktree, never in place; don't ruin pr-review.

3. Where (Gabriel's choice): Seams gains an unattended mode, on only when the launcher sets it; every stop in every skill takes its recommended option and is written to the feature's progress file as auto-answered; the hard gates (push to main, deploy, publish, paid runs, discards) still never happen. A Seams release, 5.3.0.
4. Builders (Gabriel's choice): one builder per ticket, in its own worktree, running the full route its size needs (grill; spec and tickets for a feature; implement with tdd; the reviews; verification), ending in a pull request; the heartbeat starts builders, checks their evidence and keeps the morning record.
5. Enforcement (Gabriel's choice): in unattended mode the gate requires each builder to invoke a routing skill itself before editing project files (today the main session's route covers every subagent), and a builder's handover is checked for verification-before-completion's evidence, since the done-check doesn't run in a subagent.

6. Merge bar (Gabriel's choice): a pull request merges into develop overnight only when its builder ran the full flow and the evidence is on disk: Seams' definition of done met row by row, an independent code-review and the principal-engineer checklist with every Jira point MET, CI green on the exact head, up to date with develop, and its owner's acceptance where the card names one; anything short stays merge-ready for the morning.

## Open questions

- Test seams.

## Facts

- 2026-10-14 scouts: ~/.claude/skills/sleep-mode/SKILL.md names no Seams skill; builders get "Start new builders as subagents (the Agent tool)" (:13) and the merge bar is "CI green on its head, review findings acted on, up to date with its base" (:20). The clarewood ticket-builder agent leaves the skill to the lead's prompt (effort low).
- Seams has no unattended mode: grill, to-spec, to-tickets, implement, finishing, release, foundations and worktrees each stop for the user; only grill and pr-review have a headless fallback (ask in text, end the turn). A subagent cannot use AskUserQuestion. The gate allows a subagent's edits once the main session has declared a route (hooks/seams_ledger.py:276-285), so builders skip the flow; the done-check (Stop) does not fire in a subagent (no SubagentStop hook).
- Overnight evidence (the project's own records): merges before the work was accepted, cards reopened after Engineering Complete, a regression, CI turned red by merge interactions, and a merge against a product ruling.
