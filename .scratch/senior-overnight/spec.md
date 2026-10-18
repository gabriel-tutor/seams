# Spec: senior-quality overnight work, and a memory that stays current

Status: ready-for-agent

## Problem Statement

Gabriel runs his tickets overnight with sleep mode in an unattended Seams session (5.3.0). The flow now runs, but the work still isn't the senior-quality output he gets by day:

- Records go stale: a progress file's header and queue rows lag hours behind its own log, and a start prompt sends the session to an old commit and the wrong time window.
- Claims are made without evidence: timestamps estimated hours off, a commit id typed from memory, a builder reporting passing tests that the lead's checks found wrong, an "unchanged" figure reported to the product owner that had moved.
- Work merges unreconciled: a "merge" message taken as the owner's acceptance while his questions stood open, merges on the lead's own checks, a merge that turned the base branch's CI red.
- Overnight work stalls or skips the tools the project uses: a tool listed as "ask" waits for a prompt no one answers; reads and test runs it needs are refused.

By day, sessions forget what the project already knows: the resume note lists only the newest three active progress files while many older ones still say active, knowledge given in chat never reaches its home, and nothing tells a session which recorded fact is out of date.

## Solution

Two layers, both on Seams' existing homes, with no second store.

**A memory that stays current.** Every session starts (and resumes) with a live project card built from the local sources: every active progress file with its next step, each flagged when it is stale, and the current commit. Whatever a session learns is written at once to the fact's one home, with its source. Every claim of a time, a commit, a count or a result comes from a command run in the session, or is not made. Each sleep night begins by re-checking the records it will rely on.

**Overnight with full tools and a hard bar.** Everything but production runs unattended: every read, the CLIs, browsers, staging deploys and variables, messages to a recipient list Gabriel sets. Production (the production environment, main or master, the live workflow instance, real contacts) is refused cleanly instead of stalling, and drafted for the morning. Before any merge the guard asks GitHub for the facts the session can't fake. Two commands take over every open pull request: `takeover -soft` merges all but the ones awaiting their owner's acceptance; `takeover -hard` merges those too. The lead runs the gate and tests itself; a read-only reviewer judges the evidence.

## User Stories

1. As Gabriel, I want every session to start with a card of all active work, so that nothing is forgotten because it isn't among the newest three.
2. As Gabriel, I want a stale progress file flagged on the card, so that a session never trusts a record its branch has moved past.
3. As Gabriel, I want the card rebuilt on resume and after a compaction, so that a long session never works from a picture it formed hours ago.
4. As Gabriel, I want the card to hold only pointers, so that it can never become a second, drifting copy of a fact.
5. As Gabriel, I want the card to read only local files, so that a session starts at once and offline.
6. As Gabriel, I want what I tell a session in chat (a ruling, a number, a correction) written at once to its home with its source, so that the next session knows it.
7. As Gabriel, I want my preferences and corrections kept in Claude's memory of me and re-checked, so that it keeps learning about me without keeping what's no longer true.
8. As Gabriel, I want every time, commit id and count in a record or a message to come from a command run in that session, so that nothing is estimated or typed from memory.
9. As Gabriel, I want any claim made to a person (a PR comment, a ticket reply, a report) to cite its evidence, so that a guess can't pass as a finding.
10. As Gabriel, I want the morning summary to list each outward claim with its source, so that I can spot an unsupported one in seconds.
11. As Gabriel, I want each sleep night to start by re-checking the active progress files, the memories it reads and the card, so that the night doesn't build on stale records.
12. As Gabriel, I want `/seams:reconcile` by day, so that I can run the same re-check whenever I suspect drift.
13. As Gabriel, I want every read tool available overnight (deployment logs and statuses, property data, the tracker, the CLIs), so that builders can find facts instead of guessing.
14. As Gabriel, I want headless browser testing overnight, so that UI work is checked the way a user sees it.
15. As Gabriel, I want staging deploys and staging variables allowed overnight, so that work can be tested end to end before morning.
16. As Gabriel, I want anything in production refused overnight (the production environment or a production service, main or master, the live workflow instance), so that nothing live changes while I sleep.
17. As Gabriel, I want a deployment call that names no environment refused, so that a default can't quietly land in production.
18. As Gabriel, I want messages sent overnight only to recipients on a list I keep, so that tests can message my team's test numbers and inboxes but never a real contact.
19. As Gabriel, I want every send refused while the list is empty, so that the safe state is the default.
20. As Gabriel, I want a refused send written as a draft for the morning, so that the work still moves.
21. As Gabriel, I want a tool that would stall on an "ask" prompt refused cleanly instead, so that a night never hangs on a question.
22. As Gabriel, I want the guard to ask GitHub before any overnight merge (every check green on the exact head, the branch up to date and conflict-free, no review asking for changes), so that a merge can't happen on the session's word.
23. As Gabriel, I want the guard to refuse a merge whenever it can't check, so that a failed lookup is a refusal, not a pass.
24. As Gabriel, I want to say `takeover -soft` and have every open pull request in scope fixed or rebuilt to the full bar and merged, except those awaiting their owner's acceptance, which wait merge-ready.
25. As Gabriel, I want `takeover -hard` to merge those too once they pass the bar, so that I choose when acceptance can follow on the base branch.
26. As Gabriel, I want a take-over that can't read a pull request's card to treat it as awaiting acceptance, so that missing information never becomes a merge.
27. As Gabriel, I want the lead to run the gate and the tests itself on the exact head, so that a builder's own report never stands as evidence.
28. As Gabriel, I want a read-only reviewer to judge the diff and that evidence, so that review stays independent and can't change anything.
29. As Gabriel, I want the overnight session started with Chrome available and Playwright as the default browser, so that browser work doesn't die when the extension idles.
30. As a teammate, I want none of this to change my day sessions unless I opt in, so that my workflow stays as it is.

## Implementation Decisions

- **Seams, the session start.** The bootstrap's resume note becomes the live card: every progress file whose Status is active, newest first, each with its feature, stage, next step and a stale flag; the current branch and commit. A file is stale when its branch has commits newer than its last update, or it hasn't changed in three days. Only local sources (the files, git); no network. It runs at start, resume, clear and compact, as today's resume note does, within the injection budget the plugin's tests set: past the budget, the card lists the rest by name only.
- **Seams, the shared rules.** The Evidence section gains the claims rule (times, commit ids, counts and results come from a command run in the session; claims made to a person cite their evidence) and the learning rule (what a session learns is written at once to its one home with its source, by the "Where docs go" table). Unattended mode's section gains the morning list of outward claims and the nightly reconcile step.
- **Seams, `/seams:reconcile`.** A new skill: re-check the records a piece of work relies on (active progress files against their branches and the code, the memories it reads, the card), fix what the evidence corrects, mark what it can't settle, and write what it did. Sleep mode runs it first each night.
- **Sleep mode's guard** (the user's own, outside this repository; the team's copy follows later):
  - a recipient list file beside the guard; overnight message and CRM-contact sends are allowed only to listed recipients, and every send is refused while the list is empty;
  - deployment tools and CLI calls naming the production environment, a production service or no environment are refused; staging is allowed;
  - the workflow instance is live, so its writes and runs are refused (reads, validation and inactive drafts allowed);
  - a tool that sits in the project's ask list but passes the guard is refused cleanly, so nothing stalls on a prompt;
  - before a merge, the guard queries GitHub for the pull request's checks on its exact head, its merge state and its review decision, and refuses unless all hold and the night's takeover mode allows the acceptance state.
- **Sleep mode's skill:** the `takeover -soft` and `takeover -hard` commands; the night's first step is `/seams:reconcile`; the lead runs the gate and tests and hands the output to a read-only reviewer; a pull request's card is looked up for acceptance, and an unreadable card waits; the morning summary lists the night's auto-answers, refusals and outward claims with their sources. The launcher passes `--chrome`.

## Testing Decisions

- A good test drives a public boundary with real inputs and checks what comes out; it never reaches into internals.
- **The guard:** its command-line seam (a PreToolUse event on stdin, a decision out), as its existing suite does: the recipient list (listed, unlisted, empty), Railway (production by name, by service, by default; staging), the workflow instance, the ask-list tools, the merge check against a stand-in `gh` that answers checks, merge state and review decision (all pass; each one failing; the lookup failing), and the two takeover modes' acceptance rule.
- **The session start:** the hook's output, as `test_plugin_hook.sh` and `test_unattended.py` drive it today: every active file listed, a stale one flagged by both rules, the budget held with many files.
- **The rules and the skill:** text pins in `test_plugin.sh`'s style for the claims, learning and reconcile rules and the reconcile skill's steps.
- **One paid eval** (`claude plugin eval`) of an unattended night on a sample repository, asked before it runs.
- Prior art: `scripts/tests/test_unattended.py`, `test_gate.py`, `test_plugin_hook.sh`, and the guard's `tests/test_guard.py`.

## Out of Scope

- An Obsidian vault, session notes or a knowledge graph of notes (a second home for facts); Graphify for code may come later as a navigation aid, its inferred links never treated as facts.
- The team's own sleep mode: it follows once Gabriel's has run for a few nights.
- GitHub branch protection: the organization's plan doesn't offer it on a private repository.
- Choosing the recipient list's members: Gabriel fills the file.

## Further Notes

- **Alternatives considered:** the video's Obsidian, Graphify and per-prompt graph walk (a second store, AI-inferred links that read as truth); a hand-kept card (drifts between saves); a card that also reads GitHub at start (slow and offline-fragile); weekly reconcile (a night could build on a week-old record); allowing sends to anyone outside production systems (a message to a real contact can't be undone); a reviewer that runs commands itself (it could change state).
- **Risks and failure modes:** a guard rule that misses a spelling (it reads commands, not scripts written to files and run; the GitHub merge check and the recipient list fail closed); a stale flag that's noisy (three days is a starting point); a card past the injection budget (the rest listed by name only); a GitHub outage (merges refused until it answers); an empty recipient list (every send refused, which is the safe default).
- **Rollout and migration:** Seams ships as a minor release; day sessions change only in their start card, which replaces the resume note. The guard and the sleep-mode skill change in place with backups beside each file. Reversing is a revert of the release and restoring the backups.
- **Observability:** the morning summary lists every auto-answer, refusal and outward claim with its source; the guard's refusals name their reason; the card shows stale records at every start.
- **Release:** Seams to its GitHub marketplace through `seams:release` (a staging pull request for CI, then main and the tag); the guard and the sleep-mode skill are installed in place on Gabriel's Mac.
