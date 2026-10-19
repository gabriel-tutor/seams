# Progress: the full Seams flow, enforced overnight

Status: active
Stage: designed
Next: The Seams part is built on seams-5.5/overnight-full-flow (the commit and handover rules; 21 suites pass); next the sleep-mode guard's merge rule on a scratchpad copy; then a code review and a security review (sensitive: the gate); set Status: done in the commit that ships it, after integration on the user's yes.
Updated: 2026-10-19

## Decisions

1. What the hooks enforce in unattended mode (the user's ask, 2026-10-19: "why sleep mode didn't always use the seams workflow just like the normal ... why there is no hook for every action"; "Full flow, gh -hard too", the user's choice): a builder can't commit until its own session ran the grill, tdd, code-review and verification (seams:trivial alone only for a commit that touches no code); the lead can't merge a pull request until `/seams:pr-review` ran on it, under `gh -hard` too (reviewed, then merged whatever its checks say).
2. When a review counts (the user's choice, 2026-10-19, "Only after its latest commit"): a `/seams:pr-review` covers a merge only when it started after the pull request's newest commit, so fixes pushed after a review are reviewed again before the merge.
3. Mine, the user may overrule them: the builder rule lives in Seams' gate, unattended mode only, checked at `git commit` (pushes stay free, so the lead pushes builders' commits after verifying them), against the committing agent's own declarations (a docs-only commit, every staged file Markdown or under `docs/`, needs any route); the merge rule lives in the sleep-mode guard, which reads the lead's own transcript (fenced) for a completed `seams:pr-review` naming the pull request or `open`, timed after the head commit's date on GitHub; a refusal names each missing step, the pull request stays in the morning queue, and the morning summary lists it. Tests at each hook's command line. The Seams part is built in a worktree; the guard part on a scratchpad copy, then backed up and swapped in.
4. The user confirmed on 2026-10-19: build it with tdd, the Seams part in a new worktree on seams-5.5/overnight-full-flow, the guard on a scratchpad copy, both reviews; integrating, pushing and releasing each wait for the user's yes.
5. Mine, the user may overrule it (2026-10-19, found while building): `implement` commits before `code-review` reviews the commit, so the builder rule is split where the flow puts each step: a code commit needs the committing agent's own design step (`seams:grill`, or `diagnosing-bugs` for a bug, the routing's bug row) and `tdd`; a builder that changed the project hands back (a new SubagentStop hook, asked once per stop as the done-check asks) only after `code-review` and `verification-before-completion` ran since its last change. Each agent's skills and last change are kept in the ledger beside its route, never reset by a heartbeat. The SubagentStop hook loads only in a session launched after it is installed.

## Open questions

- None.

## Facts

- 2026-10-19, the night of 16-19 Oct (one sleepclaude session's transcript): Seams' hooks ran (73 heartbeats each fired the prompt hooks; verification ran 327 times; builders were refused until they routed), but the gate accepts any routing skill: of 81 general-purpose builders that changed files, 66 routed, mostly through `tdd` alone or `seams:trivial`; `seams:grill` ran in 11, `seams:implement` in 2, `code-review` in 1. The lead ran `/seams:pr-review` once; the sleep-mode heartbeat names a read-only `seams:reviewer` agent, not pr-review.
- The gate (`plugin/hooks/seams_gate.py`, `seams_ledger.declared_for`): unattended, a subagent is covered by its own declaration of any skill in ROUTING_SKILLS (trivial, grill, implement, to-spec, to-tickets, incident, tdd, diagnosing-bugs), or by the main conversation's pr-review; nothing checks the route's fit or a review.
