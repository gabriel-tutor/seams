# Cleanup

1. Stop anything this review started (servers, containers).
2. Remove only worktrees carrying this review's marker. First `git -C "$EVID/head" status --porcelain` and the same for `"$EVID/base"`: a file left in a tree (a probe) moves to `$EVID/probes/` and is reported, never deleted with the tree. Then `git -C <repo> worktree remove --force "$EVID/head"` and `"$EVID/base"`, and `git -C <repo> worktree prune`; remove the clone when this review made it. The evidence (`checks/`, `probes/`, `pr.diff`, `review.json`, `payload.json`, `review.md`) stays in `$EVID` for the user.
3. After the last pull request's worktrees are gone, compare `git -C <repo> status --porcelain` and `git -C <repo> worktree list --porcelain` with the one record from Checkout; report any difference as a problem, never silently.
4. Run `matt-pocock-workflow:verification-before-completion` on the review's own claims: the checks table and every blocking finding's evidence were produced in this session at the candidate, and the user's repository is as it was.
