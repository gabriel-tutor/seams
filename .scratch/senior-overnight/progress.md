# Progress: senior-quality overnight work, and a memory that stays current

Status: active
Stage: designed
Next: A parallel run is under way (see ## Parallel): 01 by its builder in its worktree; 02 integrated; 03 and 04 built in ~/.claude/skills/sleep-mode (not a repository; backups beside each file). Then 05, through seams:implement.
Ticket: 01
Updated: 2026-10-18

## Spec

.scratch/senior-overnight/spec.md (ready-for-agent)

## Parallel

Base: main at 23e302e, 2 at once
- 01: building, branch senior-overnight/01-live-card, worktree .claude/worktrees/senior-overnight-01
- 02: integrated at ca03bed (suite 19/19 on the merge)
- 03: built in place in ~/.claude/skills/sleep-mode (61 guard tests pass on 3.14 and 3.9; review findings fixed; backups .bak-2026-10-18)

## Parallel note

- 04: built in place in ~/.claude/skills/sleep-mode (guard and mode-hook.py); its security review acted on (decision 20); 80 sleep-mode tests pass on 3.14 and 3.9.
- 05: built in place (SKILL.md, sleepclaude --chrome, tests/test_skill.py); the second security review acted on (decision 21); 89 sleep-mode tests pass on 3.14 and 3.9.

## Tickets

- [ ] 01 The live card at every start (blocked by: none)
- [x] 02 Claims from commands, learning to its home, and /seams:reconcile (blocked by: none)
- [x] 03 The overnight guard's tool boundaries (blocked by: none)
- [x] 04 The guard asks GitHub before a merge, and the two takeover modes (blocked by: 03)
- [x] 05 Sleep mode's takeover commands, nightly reconcile and independent checks (blocked by: 02, 04)
- [ ] 06 One paid eval of an unattended night (blocked by: 01, 02, 05)
- [ ] 07 Release Seams 5.4.0 (blocked by: all)

## Decisions

1. Memory (Gabriel's choice, 2026-10-18): a live project card and re-checking, no second store. Each project gets one short card (status, next step, links to where each fact lives, the commit it was checked against), shown at every session start and resume; a check flags any fact older than the code it describes; every record lists all active work, not only the newest three. ICM's one home per fact, on Seams' existing homes.
2. Learning (Gabriel's choice): whatever a session learns (a ruling given in chat, a preference, a correction) is written at once to its one home (the ticket's progress file, the glossary, an ADR, or Claude's memory of the user), with its source; a weekly reconcile pass re-checks old memories against the code and removes what is no longer true.

3. Overnight tools (Gabriel's choice, 2026-10-18): everything but production may run unattended: every read; the CLIs; browsers; Railway deploys and variable changes on non-production environments; n8n on non-production; CRM test records. Production is refused: the production Railway environment, main or master, live n8n workflows.
4. Messages (Gabriel's choice): real contacts are production. Overnight WhatsApp, email and CRM sends go only to an allowlist Gabriel sets (his own number and email, the team's test numbers, a test inbox); a send to anyone else is refused and drafted for the morning. A tool that would stall on an ask prompt is refused cleanly instead.

5. Merge check (Gabriel's choice): before any overnight merge the guard asks GitHub directly: every CI check green on the exact head, the branch up to date with develop and conflict-free, no review requesting changes (a fresh review on the fixed head clears an old one), and no awaiting-acceptance marker unless the night was started with takeover -hard. The quality parts (the independent review, the principal-engineer checklist) stay the heartbeat's.
6. Takeover commands (Gabriel's words, 2026-10-18: "when i say the word takeover ... it should takeover fix all, recreate the logic, merge etc."; "takeover -soft ... 1, takeover -hard ... 2"): `takeover -soft` takes over every open PR in scope, fixes or rebuilds it to the full bar and merges it, except a PR whose card needs its owner's acceptance, which waits merge-ready; `takeover -hard` merges those too once they pass. Both still pass the guard's merge check.

7. Card (Gabriel's choice): built live at every start and resume from the sources (each active progress file and its Next line, flagged stale when its branch has moved past it or it hasn't changed in days; the current commit); only pointers, no copied facts.
8. Claims (Gabriel's choice): a Seams rule: every time, commit id, count or "passes/unchanged" claim comes from a command run in the session, never from memory; anything said to a person cites its evidence; the morning summary lists each outward claim with its source.
9. Reconcile (Gabriel's choice): each sleep night starts by re-checking the records it will rely on (active progress files, the memories it reads, the card), fixing or flagging stale ones before any builder starts; /seams:reconcile on demand by day.
10. Reviewer (Gabriel's choice): the heartbeat runs the gate and the tests itself on the exact head and hands the output to a read-only reviewer that judges the diff and the evidence.
11. Mine, from the facts: Railway calls naming production, a -prod service, or no environment are refused; n8n has one live instance, so its writes and runs are refused (reads, validation and inactive drafts allowed); a -soft night looks up each PR's card and a PR whose card it can't read waits; overnight sends go to the recipients in a list file Gabriel fills (none until he does); sleepclaude also passes --chrome, with Playwright the overnight browser.

12. Card source (Gabriel's choice): local only at start (progress files, git); a session fetches PR and CI state from GitHub when a task needs it.
13. Tests (Gabriel's choice): unit tests for each new guard rule (recipient list, Railway production, n8n, the GitHub merge check, takeover -soft and -hard), the card and resume hook tests (every active file listed, stale ones flagged), text pins for the claims and reconcile rules, and one paid `claude plugin eval` of an unattended night on a sample repository, asked before it runs.
14. Mine: a progress file is flagged stale when its branch has commits newer than its last update, or it hasn't changed in three days; the guard refuses whenever it can't check (a GitHub lookup that fails refuses the merge).

15. Gabriel confirmed on 2026-10-18: spec it (seams:to-spec), then the tickets (he approves the breakdown), then each ticket built in .worktrees/senior-overnight from main.

16. The breakdown (Gabriel approved it, 2026-10-18): seven tickets under .scratch/senior-overnight/issues/, as listed above.

17. Sends overnight (Gabriel's choice, 2026-10-18, amending 4): the project's ask rules on message sends stay, and an ask rule prompts even under a hook's allow, so overnight every WhatsApp, email and CRM send or record write is refused cleanly and drafted for the morning; no recipient list.

18. Ticket 03's review (mine): a write word in a tool's name wins over any read word; more messaging servers recognized; every environment field must say staging and a Railway change by id is refused (so MCP deploys by id go through the CLI with -e staging); Railway's CLI is closed by default (plain reads pass, everything else names staging; down and delete refused); --set=, attached flags and npx @railway/cli read; the ask check matches server-wide rules and reads the main checkout's and the user's settings. Left as is: `railway variables -e production` is a read, so production values can appear in a transcript (decision 3, every read).

19. Ticket 04 (mine, within decisions 5 and 6): a merge must name its head (--match-head-commit, or sha= on the API) and match GitHub's headRefOid; at least one check, all passed; merge state CLEAN or HAS_HOOKS; no CHANGES_REQUESTED; label acceptance-checked unless the mode is hard. The mode lives in a fenced state file written only by mode-hook.py, a UserPromptSubmit hook in the sleep-mode settings, from the user's `takeover -soft` or `takeover -hard`, and cleared by `sleep mode -off`; without either, the soft rule holds.

20. Ticket 04's security review (Gabriel chose the lead, with evidence): on a soft night the lead reads the card, quotes the clearing line in the progress file, then adds `acceptance-checked`; the morning summary lists each. The guard, from the review: a mode holds only in the session it was typed in (mode-hook writes the session id); CronCreate and ScheduleWakeup can't schedule a takeover; a merge names its head once, in full (40 characters), never --auto, --admin or --input, one merge per command; changes requested read from latestReviews too; up to date asked of the compare API (behind_by 0) and every check develop's tip ran must pass on the head (no branch protection, so GitHub reports neither); review dismissals refused; a write onto a folder holding the fence, or run inside it, refused; the hook's timeout 40 s (a timed-out PreToolUse hook stops the call: the docs, agent-sdk/hooks, Hook timeout).

21. The second security review (mine): a merge names its pull request and never runs under xargs; develop takes merges, never a push; a fence path in a flag's value, or in git or gh (clone, worktree, --work-tree), is refused; gh, git or claude inside another program (arch, script, watch, tmux) refused, and inline code under one; git config writes refused but user, color and display settings (a setting can run a program), and -c likewise; a pull request that changes .github/ waits for Gabriel, and one whose files it can't all see is refused; the base's statuses count as expected checks, and an empty or paged set is refused; gh api paths read as GitHub reads them; sleepclaude clears the takeover state at launch; each lookup 6 s, the hook 60 s; a rebuilt pull request carries the old one's reviews (the skill; the guard can't tie them). Left: Python or a script written to a file can still write the state file (the guard reads commands, not programs: the same limit it states).

## Open questions

- None.

## Facts

- 2026-10-18 scouts (kept generic: this repository is public): after 5.3.0, unattended nights did grill, test first and review, but three failures recurred: stale records (headers and queue rows left behind, a start prompt naming an old commit and time window), claims without evidence (estimated timestamps up to two hours off, a commit id typed from memory, a builder reporting passing tests that the lead's checks found wrong), and unreconciled merges (a "merge" message taken as acceptance with the owner's questions open; merges on the lead's own checks; a merge that turned the base branch's CI red). Context was lost because the resume note lists only the newest three active progress files while many older ones still say active, and knowledge given in chat was never written to its home.
- Blocks seen overnight: a pull-request edit and an admin merge refused by the guard, a variables read and reviewers' test runs refused, a stop-hook prompt over background tasks, a 30-minute gate timeout.
- Tools: the project has a deployment platform, WhatsApp, email and CRM services, a workflow instance, data APIs, the tracker, Playwright, Chrome DevTools and Claude in Chrome. The sleep guard allows reads and refuses sends; n8n update/execute/unpublish and CRM creates pass the guard but sit in the project's ask list, so they would prompt and stall. Claude in Chrome needs `--chrome` and can idle overnight; Playwright runs headless. The project's .mcp.json holds tokens but is gitignored.
- Research: ICM (arXiv 2603.16021, github.com/RinDig/Interpretable-Context-Methodology, MIT) has "one home per fact" and one-way references; it is a staging method for sequential work, not a memory store. Graphify (github.com/safishamsi/graphify) parses code locally with no AI, uses a model for notes and tags edges EXTRACTED or INFERRED; open issue: hooks don't rebuild after a rebase. Obsidian is a viewer over a markdown folder. Claude Code: SessionStart hooks re-run on resume (good for a status card); UserPromptSubmit context is replayed stale on resume and capped at 10,000 characters; SessionEnd has 1.5 s (unsuitable for writing notes); auto-memory files carry a modified timestamp.
