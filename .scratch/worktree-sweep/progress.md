# Progress: worktrees whose work is merged are swept

Status: done
Stage: deployed
Next: None; released 5.1.0 on 2026-10-08: staging pull request #17 at 4fa3fcf green (run 37793619120), main fast-forwarded f72d7d2 to 4fa3fcf on the user's yes and green (37794811393), tag v5.1.0, the user's install at seams 5.1.0; the build's own worktree removed by the sweep itself (the one candidate it listed). Rollback: reinstall from tag v5.0.0, or revert.
Updated: 2026-10-08

## Decisions

1. When (the user's choice, 2026-10-08): `finishing-a-development-branch` sweeps every merged, clean worktree of the repository at each integration, one yes for the list; the session start adds one line when worktrees pile up, pointing to the sweep.
2. Scope (the user's choice): any worktree of the repository, wherever it lives (clarewood's `~/clarewoodcapital/wt-*` included), always only merged and clean ones, after the user's yes.
3. Clarewood's worktrees: the user is deleting them by hand (2026-10-08, replacing the earlier choice to sweep them after the release); this work is the plugin only.
4. Mine, the user may overrule them: merged means the worktree's HEAD is an ancestor of the base branch, local or on origin, or its branch's pull request is merged on GitHub (squash merges); a worktree with uncommitted changes or commits outside the base is never a candidate; removal is `git worktree remove` without force, then `git worktree prune`, and the branch deleted with `-d` only; the session-start hint is one `git worktree list` call, shown over 10 worktrees, no merge check at start; the sweep is a script beside `finishing-a-development-branch`, listing candidates with sizes and removing only the approved paths; tests on the script against temporary repositories (merged, squash-merged, dirty, unmerged), the hint in the hook suite, pins for the finishing step; released as 5.1.0.

5. The user confirmed on 2026-10-08: build it through seams:implement in a new worktree under .worktrees/, released as 5.1.0.

6. Mine (build): the session-start hint is the user's notice (systemMessage), not Claude's context, since the bootstrap's injection has about 6 bytes left under its cap; the sweep asks once for the list (all, choose, none) since AskUserQuestion holds four options; the finishing skill's step 7 runs it after Option 1 and on request, its description naming the sweep.

7. Review fixes (standards, spec, correctness, security; mine): a worktree is clean only when `git status --ignored` succeeds and shows nothing but ignored files a build regenerates (node_modules/, caches, build output), since `git worktree remove` deletes ignored files; a pull request counts only when merged at this very HEAD; a worktree at the base's tip counts only when its own HEAD reflog records a commit (a fresh one does not, a fast-forward merge does); the current worktree is protected from any subfolder; no global prune, and one missing on disk is not offered; the porcelain read with -z; the sweep runs after a parallel run's integrations too; CI's Python 3.9 job runs the sweep suite. Left: the gate holds no consent of its own (the skill's question and Claude Code's permission prompt do), and a new branch fast-forwarded with no commit of its own is not offered.

## Open questions

- None.

## Facts

- 2026-10-08: clarewood's underwriting-engine has 126 worktrees, all but one at `~/clarewoodcapital/wt-*` (siblings, not `.worktrees/`), 45 GB in all (about 950 MB each); of 66 checked, 53 have HEAD already in origin/develop.
- Seams creates worktrees in `using-git-worktrees` (`.worktrees/` by default) and in a parallel run (`.claude/worktrees/<feature>-<NN>`); `finishing-a-development-branch` removes one only on a local merge or a discard and only under `.worktrees/` or `worktrees/`; the pull-request and keep options keep it with nothing removing it later; a parallel run removes its integrated tickets' worktrees but not failed or earlier ones; no hook creates or removes worktrees.
