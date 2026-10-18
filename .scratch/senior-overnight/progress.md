# Progress: senior-quality overnight work, and a memory that stays current

Status: active
Stage: designing
Next: The grill's first round: the memory layer's shape, learning about the user, the overnight tool policy (asked alone), and evidence-gated merges (asked alone).
Updated: 2026-10-18

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

## Open questions

- Whether the card reads GitHub at session start; test seams.

## Facts

- 2026-10-18 scouts (kept generic: this repository is public): after 5.3.0, unattended nights did grill, test first and review, but three failures recurred: stale records (headers and queue rows left behind, a start prompt naming an old commit and time window), claims without evidence (estimated timestamps up to two hours off, a commit id typed from memory, a builder reporting passing tests that the lead's checks found wrong), and unreconciled merges (a "merge" message taken as acceptance with the owner's questions open; merges on the lead's own checks; a merge that turned the base branch's CI red). Context was lost because the resume note lists only the newest three active progress files while many older ones still say active, and knowledge given in chat was never written to its home.
- Blocks seen overnight: a pull-request edit and an admin merge refused by the guard, a variables read and reviewers' test runs refused, a stop-hook prompt over background tasks, a 30-minute gate timeout.
- Tools: the project has a deployment platform, WhatsApp, email and CRM services, a workflow instance, data APIs, the tracker, Playwright, Chrome DevTools and Claude in Chrome. The sleep guard allows reads and refuses sends; n8n update/execute/unpublish and CRM creates pass the guard but sit in the project's ask list, so they would prompt and stall. Claude in Chrome needs `--chrome` and can idle overnight; Playwright runs headless. The project's .mcp.json holds tokens but is gitignored.
- Research: ICM (arXiv 2603.16021, github.com/RinDig/Interpretable-Context-Methodology, MIT) has "one home per fact" and one-way references; it is a staging method for sequential work, not a memory store. Graphify (github.com/safishamsi/graphify) parses code locally with no AI, uses a model for notes and tags edges EXTRACTED or INFERRED; open issue: hooks don't rebuild after a rebase. Obsidian is a viewer over a markdown folder. Claude Code: SessionStart hooks re-run on resume (good for a status card); UserPromptSubmit context is replayed stale on resume and capped at 10,000 characters; SessionEnd has 1.5 s (unsuitable for writing notes); auto-memory files carry a modified timestamp.
