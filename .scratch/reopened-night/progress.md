# A night reopened outside its launcher stops; an overnight commit needs implement

Status: active
Stage: designed
Updated: 2026-10-21
Next: code-review and a security review of the branch against 73a2015 (sensitive: the gate), fix what they find, then ask before merging into main and set Status: done in that commit. The sleep-mode skill's handoff and restart text changed in ~/.claude/skills/sleep-mode/SKILL.md (backup .bak-2026-10-21).

## Why
A sleep-mode night was reopened after the Mac restarted (about 06:00 UTC, 20 Oct) as an ordinary
session: auto mode, no sleep settings, no SEAMS_UNATTENDED. It went on as a night from its conversation: before the
restart 25 of 28 code-changing builders ran the full flow; after it 38 of 38 skipped steps, the sleep guard refused
nothing (42 refusals before), and 37 pull requests merged into develop unchecked. Replayed through today's gate, one of
those commits is refused with SEAMS_UNATTENDED=1 and allowed without it. Separately, no overnight builder ran
`seams:implement`; the commit rule asks only for a design step and tdd.

## Decisions
1. A session that ran unattended and is reopened without SEAMS_UNATTENDED=1 refuses merges, pushes and new builders,
   and says to relaunch with the launcher's resume (`sleepclaude --resume`). (user, 21 Oct: "Seams blocks it, says
   relaunch")
2. Overnight, a builder's code commit also needs `seams:implement`, besides its design step and tdd. (user, 21 Oct:
   "Require implement too")
3. Detection: the gate's own per-session record notes the first time its hooks run with SEAMS_UNATTENDED=1; the same
   session later without it is a night reopened outside its launcher. Generic, no sleep-mode words in Seams. (user)
4. A reopened night refuses `gh pr merge`, `git push`, `git commit` and starting a subagent; reading, notes in
   `.scratch` and answering still work. (user)
5. Overnight, a builder's code commit needs its design step (grill, or diagnosing-bugs for a bug), then
   `seams:implement`, then tdd; a docs-only commit still needs just a route. (user)
6. The user controls the mode by how a session is opened: `sleepclaude --resume` continues a night at any hour (bypass,
   guard, unattended, as long as the user wants); a plain `claude --resume` of a night's session can read and write
   notes but not ship. (user asked for control; Claude's design, 21 Oct)
7. Handoff to a normal session: the refusal names both paths; `sleep mode -off` writes a `## Handoff` in each active
   progress file (what is left, the merge queue, what is BLOCKED and on whom) and sets its `Next`, so a fresh
   `claude` session's start card shows the remaining work. (Claude's design, user asked for an easy handoff)
8. Tests at the gate's hook tests (test_gate.py, test_hooks.sh for the Agent matcher), plus a replay of the night's
   real commit. (user)
9. Confirmed by the user 21 Oct; build in a worktree, branch seams-5.6/reopened-night; stop before merging into main.
10. Review fixes: a reopened night keeps its note (its ledger writes are refused, as overnight); pushes and merges are
    read word by word (`git stash push` and `git log --grep push` pass; `gh -R x pr merge`, the merges endpoint, a
    GraphQL merge and `bash -c` pass through the check); the builder brief names implement; the rules trim restored.
11. Security review of f31a006: `eval`, a git alias (`-c alias.*`, fail closed), a shell's flag cluster (`-lc`) and a
    shell fed a pipe or heredoc (any push or merge word in the command, fail closed) are read as shipping too.

## Facts
- `claude --resume` keeps the session id: the night's transcript and its gate ledger continued in the same files.
- The ledger has no record of whether a session ran unattended; overnight the session cannot write the ledger.
- The PreToolUse matcher does not include the Agent tool; hooks.json loads at launch.
- rules.md sits at its 16,000-byte bound.

## Open questions
- None.

## Facts from the build
- Replayed through the new gate, the night's real code commit is refused both ways: unattended, for want of grill,
  implement and tdd; reopened without it, with the relaunch message.

## Limits
- `/clear` starts a new ledger, and ledgers unused for 7 days are cleaned up: either forgets the note, so the check passes.
- A lost or deleted gate record forgets that a session was a night, so the check passes, as the gate fails open today.
