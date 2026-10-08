# Progress: worktrees whose work is merged are swept

Status: active
Stage: designing
Next: The user's confirmation and where to build; then the build, released as 5.1.0.
Updated: 2026-10-08

## Decisions

1. When (the user's choice, 2026-10-08): `finishing-a-development-branch` sweeps every merged, clean worktree of the repository at each integration, one yes for the list; the session start adds one line when worktrees pile up, pointing to the sweep.
2. Scope (the user's choice): any worktree of the repository, wherever it lives (clarewood's `~/clarewoodcapital/wt-*` included), always only merged and clean ones, after the user's yes.
3. Clarewood's merged worktrees are cleaned by the new sweep after the release (the user's choice).
4. Mine, the user may overrule them: merged means the worktree's HEAD is an ancestor of the base branch, local or on origin, or its branch's pull request is merged on GitHub (squash merges); a worktree with uncommitted changes or commits outside the base is never a candidate; removal is `git worktree remove` without force, then `git worktree prune`, and the branch deleted with `-d` only; the session-start hint is one `git worktree list` call, shown over 10 worktrees, no merge check at start; the sweep is a script beside `finishing-a-development-branch`, listing candidates with sizes and removing only the approved paths; tests on the script against temporary repositories (merged, squash-merged, dirty, unmerged), the hint in the hook suite, pins for the finishing step; released as 5.1.0.

## Open questions

- None; the user's confirmation.

## Facts

- 2026-10-08: clarewood's underwriting-engine has 126 worktrees, all but one at `~/clarewoodcapital/wt-*` (siblings, not `.worktrees/`), 45 GB in all (about 950 MB each); of 66 checked, 53 have HEAD already in origin/develop.
- Seams creates worktrees in `using-git-worktrees` (`.worktrees/` by default) and in a parallel run (`.claude/worktrees/<feature>-<NN>`); `finishing-a-development-branch` removes one only on a local merge or a discard and only under `.worktrees/` or `worktrees/`; the pull-request and keep options keep it with nothing removing it later; a parallel run removes its integrated tickets' worktrees but not failed or earlier ones; no hook creates or removes worktrees.
