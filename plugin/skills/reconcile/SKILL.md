---
name: reconcile
description: Use when the records work relies on may have drifted (active progress files, the memories read, the card, the knowledge), and first each unattended night
---

# Reconcile

Re-check the records a piece of work relies on against git and the code, before anything builds on them: fix what the evidence corrects, mark what it can't settle, and record what you did. A record is a pointer, never the truth: git, the code and a command's output are, and every claim below comes from a command run now (shared rules: Evidence).

**Shared rules:** `${CLAUDE_PLUGIN_ROOT}/skills/using-matt-pocock-skills/references/rules.md`, read when a step names one of its sections; the progress file's format: `${CLAUDE_PLUGIN_ROOT}/skills/using-matt-pocock-skills/references/progress-file.md`. **Effort** `${CLAUDE_EFFORT}`: nothing to skip at `low` (shared rules: Effort).

## Check

1. **Every active progress file** (`.scratch/*/progress.md` with `Status: active`), each against its branch and the code:
   - each branch, worktree and SHA its `Next`, `Candidate` and `## Parallel` name exists where it says: `git branch --list <branch>`, `git worktree list`, `git cat-file -e <sha>`, and `git merge-base --is-ancestor <sha> <base-branch>` for a SHA it calls integrated. A failed ancestry check proves nothing alone (a squash or rebase merge, or a base not fetched, fails it too): it is Unsettled unless `gh pr view <n> --json state,mergeCommit` or the fetched `origin/<base-branch>` settles it, and on it you never un-tick a ticket or lower a stage;
   - its `Stage` and its ticket list against the history: a ticket marked done has its commit or its merge where the file says, and a ticket left open has no integration the file missed;
   - commits it doesn't account for, by ancestry, never by date: the file's last commit on its branch, `git log -1 --format=%h <branch> -- <file>` (`<last>`), then `git rev-list --count <last>..<branch>`, where above 0 is commits after it. Where the file isn't on that branch (a parallel run keeps it on the base), `git log --oneline <base-branch>..<branch>` against what its `Next` and `## Parallel` say the branch holds;
   - each `## Facts` line that names a file and line still finds what it says there.
2. **The memories the work reads**: the memory index the session start loaded and each memory file this work reads. One that names a file, a function, a flag, a commit, a version or a release is checked against the repository (`ls`, `grep`, `git tag`, `git log`). One about the user (a preference, a correction) is checked against the records and the code it bears on (a progress file's decisions, CLAUDE.md) and what the user said in this conversation, never against a guess; one with nothing to check it against is left as it is, unmarked.
3. **The card**: each line the session start showed (its feature, stage, next step and stale flag) against the files and git now. The card is built from the files, so a wrong line is fixed in its file, never in the card.
4. **The knowledge**, when the repository has a knowledge config (`docs/agents/knowledge.md`): run `python3 -B ${CLAUDE_PLUGIN_ROOT}/skills/reconcile/scripts/knowledge.py status` (the full report, which hashes a source only when its size or time moved), then `knowledge.py index`: each row the script corrects (a moved or changed file, a rescan, a cited-by row) is Corrected, with the two reports as the command that settled it. What no command settles is Unsettled, marked for the owner under the config's escalation tag in the report, never in an entry: an entry citing a missing source, and a raw source newer than an approved entry that contradicts it. Sources changed since they were distilled are left for `seams:distill`. Reconcile never approves, deletes or rewrites an entry.

## Each finding

Exactly one of three:

- **Confirmed**: the evidence matches the record. Leave it as it is.
- **Corrected**: a command run now settles what the record should say (a SHA that moved, a stage git shows reached, an integrated ticket not ticked, a memory's renamed file). Fix that line at its one home (shared rules: Where docs go) and keep the command and its output for the record. A memory the evidence shows false is corrected in place, citing what showed it. Removing a memory file is destructive (shared rules: The continuous flow): only on the user's yes, never unattended; until then the report proposes it.
- **Unsettled**: no command settles it (a branch that exists nowhere here, a merge git can't trace, a ruling only the user made, a fact outside the repository): mark it in place, `(unverified <date>: <why>)` after the line, replacing an earlier mark, and leave the line itself as it is.

Never delete a record you couldn't check, and change nothing you can't verify: a guess is unsettled, never a correction. Never move a branch, a worktree or a commit to match a record: the record follows git.

## Record

1. In each progress file you changed, a `## Reconcile` section replacing the last run's: the date from `date +%F`, then one line per correction or mark with the command that settled it; set `Updated` to that date.
2. Commit the progress files you changed, by name, with a message that says what was corrected. A file already dirty before you started is edited but left uncommitted, and the report says so. Memory files live outside the repository and are not committed.
3. Report a table: each record checked, its outcome, and its evidence (the command and the line of output that shows it), the unsettled ones first. In unattended mode the report goes to the morning summary (shared rules: Unattended mode).
4. Run `seams:verification-before-completion` before saying the records are reconciled.
