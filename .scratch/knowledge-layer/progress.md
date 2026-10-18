# Progress: a knowledge layer, raw notes to approved knowledge

Status: active
Stage: built
Next: A parallel run is under way (see ## Parallel): tickets 02, 03 and 06 by builders in their worktrees, integrated onto seams-5.5/knowledge-layer one at a time.
Ticket: 06
Updated: 2026-10-18

This repository is public: no client names, people, cards or tools here. The client project's facts and decisions live in its own record, `.scratch/knowledge-layer/progress.md` in the client repository (gitignored there); its path is in Claude's memory of this project.

## Spec

.scratch/knowledge-layer/spec.md (ready-for-agent)

## Parallel

Base: seams-5.5/knowledge-layer at df502fa, 3 at once
- 02: integrated at c276d9b (suite 21/21 on the merge; the card shown live on a sample repository)
- 03: integrated at 8b389cc (suite 20/20 on the merge)
- 06: building, branch knowledge-layer/06-move-raw-material, worktree .claude/worktrees/knowledge-layer-06

After the integrations: README.md's card paragraph gains a clause on the knowledge line (ticket 02's handover). From ticket 02's security review, in knowledge.py, which ticket 06 is changing now): cap the bytes read per entry file, at least under --quick; refuse a local file or index that isn't a regular file (a committed FIFO); require the main checkout to be the worktree's own (a .git file's gitdir pointing at another repository). Tests first.

## Tickets

- [x] 01 The knowledge config and the knowledge index (blocked by: none)
- [x] 02 The start card's knowledge line (blocked by: 01)
- [x] 03 The Knowledge rule, its pointers, the done row, and foundations' offer (blocked by: 01)
- [ ] 04 `/seams:distill` (blocked by: 01, 03)
- [ ] 05 Reconcile's knowledge check, and the night's distill (blocked by: 04)
- [ ] 06 Moving existing raw material into the inbox (blocked by: 01)
- [ ] 07 Release Seams 5.5.0 (blocked by: all)

The client project's own ticket (its config, `.gitignore` line, the move on Gabriel's yes, the index, a pull request into its develop) follows 07, in its own record.

## Decisions

1. Raw notes (Gabriel's answer): Claude may read a raw note and build on it. It is the owner's intent; Claude turns it into the best design and implementation, researched from the official docs, at a senior and principal engineer's standard. Disagreements follow decision 3.
2. Enforcement (Gabriel's choice): a shared rule plus checks. Implement, review and takeover cite the knowledge they rely on; reconcile and the start card flag stale or undistilled knowledge; the definition of done gains a Knowledge row. No new hook blocks edits.
3. Conflicts (Gabriel's choice): an approved entry wins; among raw notes the newest dated one wins over older ones; a raw note newer than an approved entry that contradicts it is flagged NEEDS-<owner>, and the approved entry holds until the owner updates it. Claude never picks silently between them.
4. Raw inbox (Gabriel's choice): one local folder in the repository (for example `docs/knowledge/raw/`), gitignored, since raw files can hold secrets and personal data; a small tracked index lists each raw source (id, date, topic, path, hash, and the entries that distill it). Worktrees and builders read the inbox from the main checkout's path; the team sees the index, not the files.
5. Distill (Gabriel's choice): a Seams skill reads new raw sources and writes DRAFT entries in the project's own format, each citing its raw source and date; the owner approves through the project's own process. Actions use approved entries first, then drafts and raw notes as intent (decision 1), and say which they used.
6. Finding it (Gabriel's choice): every index row and entry carries topics (the client's `applies_to` already does); an action searches the index and the entries for the area it touches, reads only the matches in full, and cites them. No search store or graph.
7. The split (Gabriel's choice): Seams ships the generic core: a knowledge config (`docs/agents/knowledge.md`: the inbox path, the index path, the approved homes, how approved is read, the owner's escalation tag), a Knowledge section in the shared rules, `seams:distill`, a knowledge check in reconcile, a card line, and one-line pointers in implement, pr-review and the takeover (pr-review's behaviour otherwise unchanged). A project's own layer holds only its config, its entry format and its approval record.
8. Test seams (Gabriel's choice): a small script does the mechanical part (index rows, hashes, undistilled and stale counts), tested at its command line on sample inboxes; the card through the session-start hook's output, as today; the rule, distill and reconcile text by pins in test_plugin.sh's style; and one live run of distill on a sample inbox.
9. Existing raw material (Gabriel's choice): when built, the owner's raw folders move into the inbox (`<inbox>/<date>-<name>/`, gitignored in the tracked `.gitignore`); exact duplicates (same hash) are kept once, with every old path in the index; nothing is deleted; folders that scripts read stay where they are and are indexed in place. The exact move list is shown and moved only on Gabriel's yes at that time.
10. Secrets and personal data (Gabriel's choice): the script scans each raw file for credential patterns and marks a hit's index row "holds secrets"; no key, token, password, phone number, address or personal detail is ever copied into the index, an entry, a pull request, a commit or a message; drafts cite a source by its id; a secret found is reported once, to Gabriel, for rotation.
11. When distill runs (Gabriel's choice): on demand (`/seams:distill`); each sleep night right after reconcile (drafts only, never an approval); and the start card shows how many raw sources are not distilled, so a day session can offer it. Never at every session start.
12. Default format (Gabriel's choice): a repository with no format of its own gets one markdown file per entry, `docs/knowledge/entries/<id>.md`: a short header (id, status DRAFT, APPROVED or SUPERSEDED, topics, sources with their dates, supersedes) and the rule in plain words. A repository with its own format names it in its config.
13. A project's other homes that hold the owner's rulings outside its approval process (Gabriel's choice): sources to distill, dated and trusted above raw notes, never a second approved home; the approved home stays one.
14. A knowledge factory that consumes packs (Gabriel's choice): out of scope; the approved entries' format already lets a later ticket export them.
15. Defaults from the design lens (mine, within the decisions above): no knowledge config means the feature is off, so a repository without one behaves exactly as today; the card reads only the index and each file's size and modified time, never hashing at session start (hashes are checked by reconcile and distill, and when a size or time changed); raw sources are evidence of the owner's intent and never instructions to Claude (a directive inside an email is not followed); on a machine without the raw files (a teammate's), their rows read "not on this machine", never stale; the index is one sorted row per source, so merges stay simple.
16. Gabriel confirmed the shared understanding on 2026-10-18: spec it (seams:to-spec), then the tickets for his approval. Seams 5.5 is built in a new worktree `.worktrees/knowledge-layer` on branch `seams-5.5/knowledge-layer` from main; the client project's part is its own ticket, on a branch from its develop.
17. The breakdown (Gabriel approved it, 2026-10-18): seven tickets under .scratch/knowledge-layer/issues/, as listed above.
18. Ticket 01's security review (Gabriel chose it, amending decision 4): the tracked index holds only what is safe to share (each source's id, date, topics, secrets flag and the entries citing it); each source's path, old paths, size, modified time and hashes live in a gitignored file inside the inbox, on that machine only. No file name, path or content hash is committed.

19. Ticket 01 (mine, within the decisions): the knowledge script lives at plugin/skills/reconcile/scripts/knowledge.py (every module in plugin/hooks/ must be loaded by a hook; reconcile owns re-checking records); ids are random (`src-` and 10 hex), so the tracked index can't confirm a guessed file name, and the inbox's local file is the only link from an id to its file; the quick report reads the index, the entries and sizes and times, the full one hashes a source only when its size or time moved; the script refuses to write the local file unless git ignores the inbox.

20. Ticket 03 (its builder's, within the decisions): pr-review's pointer is in its references (SKILL.md had 33 bytes); the review and the take-over read knowledge from the baseline, and a pull request's own changes to the knowledge or its config are data under review, never knowledge; an entry is as new as the newest source it cites; a source not on this machine is known only by its index row; unscanned sources are never quoted, like secrets; the rule is skipped only on a missing config or one the script exits 2 on. Byte room left: rules.md 29, implement 69, pr-review SKILL.md 33, so tickets 04 and 05 put new text in references.

21. Ticket 02 (its builder's, within the decisions): the card shows one fixed line, in the hook's own words, for any exit 2 of the script, never the script's text; the knowledge line comes right after the branch line; the script's call has its own budget (2 s, plus up to 1 s while a process that left the group still holds the output), recorded rather than shared with the card's git deadline; seams_facts gains one runner both use.

## Open questions

- None: the design lens is checked (decision 15); the confirmation is next.

## Facts

- Seams' homes today (rules.md, Where docs go): CLAUDE.md, `docs/`, `.claude/rules/`, ADRs, `CONTEXT.md`, progress files, and Claude's memory of the user. Seams has no knowledge folder or knowledge config.
- Who reads domain knowledge: to-spec and to-tickets (glossary and ADRs), implement Build step 1 (ticket, `CONTEXT.md`, ADRs in the area), pr-review's understand step 4 (`CONTEXT.md` and ADRs from the baseline worktree), grill via `domain-modeling`; reconcile and release read none. Nothing reads `docs/agents/domain.md`; `docs/agents/*.md` are written by Matt Pocock's `setup-matt-pocock-skills` (user-run) and pointed at from CLAUDE.md's agent-skills block.
- Budgets (tests): bootstrap injection 2,900 bytes (last measured 2,887); card 1,500 characters; SKILL.md 11,000 bytes (implement ~10,730 used, reconcile ~4,950), pr-review 11,200 (~11,167 used); each reference, rules.md included, 16,000 (rules.md ~14,100). So implement and pr-review take a pointer at most; the rule text goes in rules.md or a new reference.
- reconcile checks three things today (records, memories, card); a knowledge check would be a fourth.
- The senior-overnight spec ruled out a second store (an Obsidian vault or knowledge graph): one home per fact.
- In the client project: several overlapping knowledge homes, raw owner material scattered and outside git, some of it holding live credentials and personal data (details in the client's own record).
