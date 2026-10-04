# Progress: CLAUDE.md kept small, an oversized one split into lazy modules

Status: active
Stage: designing
Next: The user's confirmation; then the build on seams-4.1/simplicity-ladder with the ladder and the rename, as part of 5.0.0.
Updated: 2026-10-04

## Decisions

1. Prevent and cure (the user's choice, 2026-10-04): Seams' docs rule keeps CLAUDE.md a short index, and `foundations` splits an oversized one; no new skill, no @-imports (they load at launch, so they save nothing).
2. Ships in 5.0.0 with the simplicity ladder and the rename (the user's choice).
3. The user splits clarewood's CLAUDE.md in clarewood after 5.0.0, through `/seams:foundations` (the user's choice).
4. Mine, the user may overrule them (the user left the approach to me): the budget is the docs' guidance, under 200 lines, which `foundations` reports as a gap; the split moves sections verbatim, never rewritten, after the user approves a plan of each section and its destination; a section about one part of the code goes to `.claude/rules/<topic>.md` with `paths:` globs for that code, anything else to `docs/agents/<topic>.md`; CLAUDE.md keeps the commands, the conventions, the gotchas and the agent-skills block, and a one-line plain-text pointer to each moved file; the shared rules gain a Docs section saying where docs go (a feature's design notes to `docs/`, decisions to ADRs, area rules to path-scoped rules, CLAUDE.md never), and implement's Docs row points to it; test_plugin.sh pins the rule and the foundations row; no paid eval.

## Open questions

- None; the user's confirmation.

## Facts

- clarewoodcapital/underwriting-engine/CLAUDE.md: 241,344 bytes, 2,487 lines, 44 sections, 252 commits touching it; the largest sections are dated feature notes (Document attachments, G2.72, 51 KB; Comparable acquisition, 34 KB; Database, 30 KB). Its own "How to trust this file" asks for a divergence to be fixed in the file in the same change. No Seams skill mentions CLAUDE.md (grep, 2026-10-04); Matt Pocock's setup-matt-pocock-skills writes the small Agent skills block.
- Claude Code (the user's, 2026-10-04) warns "CLAUDE.md is over the 150.0k-char limit (240.0k chars)". The docs mirror (memory): target under 200 lines; a file up to 4 MiB loads in full; @-imports load at launch ("helps organization but doesn't reduce context"); `.claude/rules/*.md` with `paths:` and CLAUDE.md files in subdirectories load only when Claude reads matching files; a docs file named in plain text costs only its mention; `/doctor` proposes trims (2.1.206+).
