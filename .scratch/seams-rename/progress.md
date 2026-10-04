# Progress: the plugin and marketplace renamed to seams

Status: active
Stage: designing
Next: The grill's next round, on the scouts' facts: the gate's handling of the old names during the transition, the user's install's migration, pr-review's uses; then the test seams, the lens and the confirmation.
Updated: 2026-10-04

## Decisions

1. Rename the plugin and the marketplace: `matt-pocock-workflow@my-workflow-agent-skills` becomes `seams@seams`; the skills become `seams:<name>`, the agents `seams:scout` and `seams:reviewer` (the user's choice, 2026-10-04).
2. It ships with the simplicity ladder as one release, 5.0.0, major because every skill name changes (the user's choice); the ladder's 4.1.0 becomes 5.0.0 (simplicity-ladder decision 1 amended).
3. Live text only (the user's choice): the plugin, the tests, the install script, the README's usage, `CONTEXT.md` and the evals say `seams`; past CHANGELOG entries, the ADRs, the evidence docs and `.scratch/` records keep the old name where they record what happened, and the 5.0.0 entry says when it changed. The bootstrap skill's folder, `using-matt-pocock-skills`, names what it does, not the plugin, and stays.

## Open questions

- The gate and the old names in the transition; the user's install's migration; pr-review's uses of the name; the test seams; the lens.

## Facts

- The old names occur 428 times across plugin/, scripts/, docs/, README.md, CHANGELOG.md, CONTEXT.md and .claude-plugin/ (grep, 2026-10-04). The GitHub repository is already gabriel-tutor/seams, and the README already calls the project Seams.
