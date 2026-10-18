# Progress: senior-quality overnight work, and a memory that stays current

Status: active
Stage: designing
Next: The grill's first round: the memory layer's shape, learning about the user, the overnight tool policy (asked alone), and evidence-gated merges (asked alone).
Updated: 2026-10-18

## Decisions

(none yet)

## Open questions

- The memory layer's shape (a thin pointer layer on Seams' homes, a vault and graph, or Graphify for code only).
- How it learns about the user.
- Overnight tool policy: which MCP and CLI actions may run unattended.
- Whether merges are gated by evidence in code, not only by the heartbeat's text.

## Facts

- 2026-10-18 scouts (kept generic: this repository is public): after 5.3.0, unattended nights did grill, test first and review, but three failures recurred: stale records (headers and queue rows left behind, a start prompt naming an old commit and time window), claims without evidence (estimated timestamps up to two hours off, a commit id typed from memory, a builder reporting passing tests that the lead's checks found wrong), and unreconciled merges (a "merge" message taken as acceptance with the owner's questions open; merges on the lead's own checks; a merge that turned the base branch's CI red). Context was lost because the resume note lists only the newest three active progress files while many older ones still say active, and knowledge given in chat was never written to its home.
- Blocks seen overnight: a pull-request edit and an admin merge refused by the guard, a variables read and reviewers' test runs refused, a stop-hook prompt over background tasks, a 30-minute gate timeout.
- Tools: the project has a deployment platform, WhatsApp, email and CRM services, a workflow instance, data APIs, the tracker, Playwright, Chrome DevTools and Claude in Chrome. The sleep guard allows reads and refuses sends; n8n update/execute/unpublish and CRM creates pass the guard but sit in the project's ask list, so they would prompt and stall. Claude in Chrome needs `--chrome` and can idle overnight; Playwright runs headless. The project's .mcp.json holds tokens but is gitignored.
- Research: ICM (arXiv 2603.16021, github.com/RinDig/Interpretable-Context-Methodology, MIT) has "one home per fact" and one-way references; it is a staging method for sequential work, not a memory store. Graphify (github.com/safishamsi/graphify) parses code locally with no AI, uses a model for notes and tags edges EXTRACTED or INFERRED; open issue: hooks don't rebuild after a rebase. Obsidian is a viewer over a markdown folder. Claude Code: SessionStart hooks re-run on resume (good for a status card); UserPromptSubmit context is replayed stale on resume and capped at 10,000 characters; SessionEnd has 1.5 s (unsuitable for writing notes); auto-memory files carry a modified timestamp.
