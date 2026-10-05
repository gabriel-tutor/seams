# Progress: CLAUDE.md kept small, an oversized one split into lazy modules

Status: done
Stage: deployed
Next: None; Released 5.0.0 on 2026-10-05: staging pull request #16 at f72d7d2 green on all three jobs, main fast-forwarded 987c187 to f72d7d2 on the user's yes and its run 37309099015 green, tag v5.0.0; the user's Mac switched from matt-pocock-workflow@my-workflow-agent-skills to seams@seams 5.0.0, read in place, no old key or permission rule left; a session-start probe injects the seams: names and the ladder pointer (2,577 bytes). Rollback: reinstall 4.0.0 from tag v4.0.0 under its old name. Left to the user: splitting clarewood's CLAUDE.md with /seams:foundations in that repository (decision 3).
Updated: 2026-10-05

## Decisions

1. Prevent and cure (the user's choice, 2026-10-04): Seams' docs rule keeps CLAUDE.md a short index, and `foundations` splits an oversized one; no new skill, no @-imports (they load at launch, so they save nothing).
2. Ships in 5.0.0 with the simplicity ladder and the rename (the user's choice).
3. The user splits clarewood's CLAUDE.md in clarewood after 5.0.0, through `/seams:foundations` (the user's choice).
4. Mine, the user may overrule them (the user left the approach to me): the budget is the docs' guidance, under 200 lines, which `foundations` reports as a gap; the split moves sections verbatim, never rewritten, after the user approves a plan of each section and its destination; a section about one part of the code goes to `.claude/rules/<topic>.md` with `paths:` globs for that code, anything else to `docs/agents/<topic>.md`; CLAUDE.md keeps the commands, the conventions, the gotchas and the agent-skills block, and a one-line plain-text pointer to each moved file; the shared rules gain a Docs section saying where docs go (a feature's design notes to `docs/`, decisions to ADRs, area rules to path-scoped rules, CLAUDE.md never), and implement's Docs row points to it; test_plugin.sh pins the rule and the foundations row; no paid eval.

5. The user confirmed on 2026-10-04: build it on seams-4.1/simplicity-ladder, test first, reviewed with the rest of 5.0.0, stopping before main and the user's Mac.

## Open questions

- None.

## Facts

- clarewoodcapital/underwriting-engine/CLAUDE.md: 241,344 bytes, 2,487 lines, 44 sections, 252 commits touching it; the largest sections are dated feature notes (Document attachments, G2.72, 51 KB; Comparable acquisition, 34 KB; Database, 30 KB). Its own "How to trust this file" asks for a divergence to be fixed in the file in the same change. No Seams skill mentions CLAUDE.md (grep, 2026-10-04); Matt Pocock's setup-matt-pocock-skills writes the small Agent skills block.
- Claude Code (the user's, 2026-10-04) warns "CLAUDE.md is over the 150.0k-char limit (240.0k chars)". The docs mirror (memory): target under 200 lines; a file up to 4 MiB loads in full; @-imports load at launch ("helps organization but doesn't reduce context"); `.claude/rules/*.md` with `paths:` and CLAUDE.md files in subdirectories load only when Claude reads matching files; a docs file named in plain text costs only its mention; `/doctor` proposes trims (2.1.206+).
