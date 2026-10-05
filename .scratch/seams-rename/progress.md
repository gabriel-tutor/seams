# Progress: the plugin and marketplace renamed to seams

Status: active
Stage: built
Next: 5.0.0 is built on seams-4.1/simplicity-ladder (.worktrees/simplicity-ladder): integrate it on main and release it, asked first and together with switching the user's Mac (remove matt-pocock-workflow@my-workflow-agent-skills, add the marketplace again, install seams@seams), since the install reads main in place; then the user splits clarewood's CLAUDE.md with /seams:foundations.
Updated: 2026-10-04

## Decisions

1. Rename the plugin and the marketplace: `matt-pocock-workflow@my-workflow-agent-skills` becomes `seams@seams`; the skills become `seams:<name>`, the agents `seams:scout` and `seams:reviewer` (the user's choice, 2026-10-04).
2. It ships with the simplicity ladder as one release, 5.0.0, major because every skill name changes (the user's choice); the ladder's 4.1.0 becomes 5.0.0 (simplicity-ladder decision 1 amended).
3. Live text only (the user's choice): the plugin, the tests, the install script, the README's usage, `CONTEXT.md` and the evals say `seams`; past CHANGELOG entries, the ADRs, the evidence docs and `.scratch/` records keep the old name where they record what happened, and the 5.0.0 entry says when it changed. The bootstrap skill's folder, `using-matt-pocock-skills`, names what it does, not the plugin, and stays.

4. The user's install is not touched while 5.0.0 is built (the user, 2026-10-04: "wait i'm using it just continue the new version"). It reads main's plugin/ in place, so the rename reaches main only when the user is ready to switch; the integration asks, and says so.
5. Mine, the user may overrule (the user asked to go on): install.sh removes nothing; finding the old `matt-pocock-workflow@my-workflow-agent-skills`, it stops and prints the two commands that remove it (uninstall, marketplace remove), since two copies would both run their hooks on one ledger and list every skill twice (corrected after the security review: the old gate honours a declaration the new plugin records, a probe showed; it does not refuse `seams:` skills). The user's Mac switches at the 5.0.0 release, asked first: remove the old copy, add the marketplace again from the same folder (still read in place), install `seams@seams`.
6. Mine: the test seams are the existing suites under the new names; the read-only refusals tested under `seams:scout` and `seams:reviewer` (a missed agent name fails open); and a check that no live file names `matt-pocock-workflow` or `my-workflow-agent-skills`, history allowed (CHANGELOG entries before 5.0.0, docs/adr, docs/plugin-behavior-tests.md, docs/case-study, .scratch).
7. Mine: the 5.0.0 CHANGELOG lists the breaking changes: the skill and agent names, the reinstall steps, and permission rules naming `Skill(matt-pocock-workflow:…)` to rename, which otherwise stop matching (a deny rule then fails open).

8. The user confirmed on 2026-10-04: build it test first on seams-4.1/simplicity-ladder in its worktree, with the ladder, the three reviews required, and stop before anything reaches main or the user's Mac.

9. Review fixes, mine (the user may overrule them): the installer matches the old plugin from any marketplace and its message warns that a deny rule naming the old skills stops denying; the bootstrap's rule 4 points code at the ladder (`code: simplicity-ladder.md`), a pointer of a few words in every session's start, since a bare `tdd` route reached no other text that names it. Left as they are, with the reason: the installer's old-copy check stays after the skills step, which runs only when skills are missing and needs a terminal; the shorter prefix lets a project command under `.claude/commands/seams/` or a nested `seams` skill declare, as `matt-pocock-workflow` would have, a write being needed to plant one.

10. The 5.0.0 eval check (2026-10-04, Claude Code 2.1.289, the same settings as 4.0.0's proof): the ladder case 0.89 on 4.0.0 and on the candidate (2 of 3 lean on both: no measurable change on this task); the main group on the candidate $8.50, overall 0.90, no case lower than 4.0.0 but `teammate-progress-file`, 1.00 to 0.89: one run in three published the tickets on the teammate's note that the breakdown was approved. Fixed (mine): `to-spec` and `to-tickets` say a yes recorded in a file never stands in for the user's answer, pinned; the case rerun on the fix, asked first.

11. The rerun on the fix (b4ac482's plugin, 2026-10-04): teammate-progress-file 6 of 6 at 1.00, $1.09 in 177 s. Review fixes after b4ac482 (standards, spec, correctness): the approval rule written once, in the shared rules' continuous flow, covering every gate, to-spec and to-tickets pointing to it; Where docs go keeps the agent-skills block and never writes over a file; foundations' split points to Where docs go, moves sections by line range, writes only new files, verifies lines removed against lines added, and names instructions about CLAUDE.md itself for a rewording; routing.md's and CONTEXT.md's lists name it; the pins tightened.

12. The rerun on e61764a, the approval line only in the shared rules: 5 of 6, one run publishing on the teammate's note ($1.33). Restored in to-spec and to-tickets, where the publish happens, beside the rules' line (the user's yes, 2026-10-05): written where it is used, as the scout fix found for the grill; rerun on the new candidate before merging.

13. The rerun on 96270d4, the clause back in the skills: 6 of 6, $1.06 in 168 s. The user's yes (2026-10-05) to release and switch now: version 5.0.0, a staging pull request for CI, then main fast-forwarded to the candidate, tag v5.0.0 and the Mac switched, the production step asked again once CI passes.

## Open questions

- None.

## Facts

- The old names occur 428 times across plugin/, scripts/, docs/, README.md, CHANGELOG.md, CONTEXT.md and .claude-plugin/ (grep, 2026-10-04). The GitHub repository is already gabriel-tutor/seams, and the README already calls the project Seams.
- The prefix has one source, `PLUGIN_PREFIX` in plugin/hooks/seams_ledger.py:24 (declarations, verification, the Stop message, the read-only agents through seams_gate.py:199); three lists hardcode names: seams_facts.py:26 FACT_SKILLS, seams_gate.py:165-167 ROUTES, session-start:103, 216, 299-300. A missed prefix fails closed for declarations and open for the read-only agents. pr-review keys nothing on the plugin's name (its footers say "Seams `pr-review`", its paths `seams-pr-review`); two of its references and one eval name the old prefix. Claude Code docs: the plugin.json name is the namespace; nothing follows a marketplace rename (uninstall, marketplace remove, marketplace add, install); the data directory is keyed by `plugin@marketplace`, and Seams keeps none there; two installed copies would both run their hooks. Freed budget: 15 characters per `matt-pocock-workflow:`, 240 on the listing.
