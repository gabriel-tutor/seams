# Progress: the plugin and marketplace renamed to seams

Status: active
Stage: designed
Next: The rename is committed on seams-4.1/simplicity-ladder (.worktrees/simplicity-ladder) with the ladder; next code-review, a correctness review and the security review over 584de2b...HEAD, then the fixes, the eval runs (paid, asked) and the release of 5.0.0, the user's Mac switched only when the user says so.
Updated: 2026-10-04

## Decisions

1. Rename the plugin and the marketplace: `matt-pocock-workflow@my-workflow-agent-skills` becomes `seams@seams`; the skills become `seams:<name>`, the agents `seams:scout` and `seams:reviewer` (the user's choice, 2026-10-04).
2. It ships with the simplicity ladder as one release, 5.0.0, major because every skill name changes (the user's choice); the ladder's 4.1.0 becomes 5.0.0 (simplicity-ladder decision 1 amended).
3. Live text only (the user's choice): the plugin, the tests, the install script, the README's usage, `CONTEXT.md` and the evals say `seams`; past CHANGELOG entries, the ADRs, the evidence docs and `.scratch/` records keep the old name where they record what happened, and the 5.0.0 entry says when it changed. The bootstrap skill's folder, `using-matt-pocock-skills`, names what it does, not the plugin, and stays.

4. The user's install is not touched while 5.0.0 is built (the user, 2026-10-04: "wait i'm using it just continue the new version"). It reads main's plugin/ in place, so the rename reaches main only when the user is ready to switch; the integration asks, and says so.
5. Mine, the user may overrule (the user asked to go on): install.sh removes nothing; finding the old `matt-pocock-workflow@my-workflow-agent-skills`, it stops and prints the two commands that remove it (uninstall, marketplace remove), since two copies' gates would both run and the old one refuses every `seams:` declaration. The user's Mac switches at the 5.0.0 release, asked first: remove the old copy, add the marketplace again from the same folder (still read in place), install `seams@seams`.
6. Mine: the test seams are the existing suites under the new names; the read-only refusals tested under `seams:scout` and `seams:reviewer` (a missed agent name fails open); and a check that no live file names `matt-pocock-workflow` or `my-workflow-agent-skills`, history allowed (CHANGELOG entries before 5.0.0, docs/adr, docs/plugin-behavior-tests.md, docs/case-study, .scratch).
7. Mine: the 5.0.0 CHANGELOG lists the breaking changes: the skill and agent names, the reinstall steps, and permission rules naming `Skill(matt-pocock-workflow:…)` to rename, which otherwise stop matching (a deny rule then fails open).

8. The user confirmed on 2026-10-04: build it test first on seams-4.1/simplicity-ladder in its worktree, with the ladder, the three reviews required, and stop before anything reaches main or the user's Mac.

## Open questions

- None.

## Facts

- The old names occur 428 times across plugin/, scripts/, docs/, README.md, CHANGELOG.md, CONTEXT.md and .claude-plugin/ (grep, 2026-10-04). The GitHub repository is already gabriel-tutor/seams, and the README already calls the project Seams.
- The prefix has one source, `PLUGIN_PREFIX` in plugin/hooks/seams_ledger.py:24 (declarations, verification, the Stop message, the read-only agents through seams_gate.py:199); three lists hardcode names: seams_facts.py:26 FACT_SKILLS, seams_gate.py:165-167 ROUTES, session-start:103, 216, 299-300. A missed prefix fails closed for declarations and open for the read-only agents. pr-review keys nothing on the plugin's name (its footers say "Seams `pr-review`", its paths `seams-pr-review`); two of its references and one eval name the old prefix. Claude Code docs: the plugin.json name is the namespace; nothing follows a marketplace rename (uninstall, marketplace remove, marketplace add, install); the data directory is keyed by `plugin@marketplace`, and Seams keeps none there; two installed copies would both run their hooks. Freed budget: 15 characters per `matt-pocock-workflow:`, 240 on the listing.
