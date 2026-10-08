#!/usr/bin/env python3
"""The worktree sweep: the repository's worktrees whose work is merged, so they stop filling the disk.

    sweep_worktrees.py list [--repo DIR] [--base BRANCH]          JSON: {"base", "candidates": [{path, branch, reason, size_kb}]}
    sweep_worktrees.py remove PATH... [--repo DIR] [--base BRANCH]  JSON: {"removed": [...], "refused": {path: why}}

A candidate is clean (nothing uncommitted or untracked) and merged: its HEAD is in the base branch, local or on
origin, or its branch's pull request is merged on GitHub (a squash merge). The main worktree, the current one and a
locked one never are. `remove` checks each path again, runs `git worktree remove` without force, deletes the branch
with -d (which refuses one not fully merged), and prunes. Standard library only; it writes no bytecode.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys

sys.dont_write_bytecode = True


def git(repo, *args, check=True):
    out = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True)
    if check and out.returncode != 0:
        raise SystemExit(f"git {' '.join(args)}: {out.stderr.strip()}")
    return out


def worktrees(repo):
    """Every worktree from `git worktree list --porcelain`, the main one first."""
    entries, cur = [], {}
    for line in git(repo, "worktree", "list", "--porcelain").stdout.splitlines() + [""]:
        if not line:
            if cur:
                entries.append(cur)
            cur = {}
            continue
        key, _, value = line.partition(" ")
        cur[key] = value or True
    return entries


def default_base(repo):
    head = git(repo, "symbolic-ref", "--quiet", "--short", "refs/remotes/origin/HEAD", check=False).stdout.strip()
    if head:
        return head.split("/", 1)[1]
    for name in ("main", "master", "develop"):
        if git(repo, "rev-parse", "--verify", "--quiet", name, check=False).returncode == 0:
            return name
    return "main"


def pr_merged(repo, branch):
    try:
        out = subprocess.run(["gh", "pr", "list", "--head", branch, "--state", "merged", "--json", "number",
                              "--limit", "1"], cwd=str(repo), capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired):
        return False
    try:
        return out.returncode == 0 and bool(json.loads(out.stdout or "[]"))
    except ValueError:
        return False


def judge(repo, entry, base, here):
    """Why this worktree may be removed, or None with the reason it may not."""
    path = entry["worktree"]
    if os.path.realpath(path) in (os.path.realpath(repo_main(repo)), here):
        return None, "the main or current worktree"
    if entry.get("locked"):
        return None, "locked"
    if entry.get("prunable"):
        return "missing on disk", None
    if git(path, "status", "--porcelain", check=False).stdout.strip():
        return None, "not clean"
    head = entry.get("HEAD", "")
    for ref in (base, f"origin/{base}"):
        if git(repo, "merge-base", "--is-ancestor", head, ref, check=False).returncode == 0:
            return "merged", None
    branch = entry.get("branch", "").removeprefix("refs/heads/")
    if branch and pr_merged(repo, branch):
        return "pull request merged", None
    return None, "not merged"


def repo_main(repo):
    return worktrees(repo)[0]["worktree"]


def size_kb(path):
    out = subprocess.run(["du", "-sk", path], capture_output=True, text=True)
    return int(out.stdout.split()[0]) if out.returncode == 0 and out.stdout else 0


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("action", choices=("list", "remove"))
    parser.add_argument("paths", nargs="*")
    parser.add_argument("--repo", default=".")
    parser.add_argument("--base")
    args = parser.parse_args()
    repo = git(args.repo, "rev-parse", "--show-toplevel").stdout.strip()
    base = args.base or default_base(repo)
    here = os.path.realpath(os.getcwd())
    entries = worktrees(repo)
    if args.action == "list":
        candidates = []
        for entry in entries[1:]:
            reason, _ = judge(repo, entry, base, here)
            if reason:
                candidates.append({"path": entry["worktree"], "branch": entry.get("branch", "").removeprefix("refs/heads/"),
                                   "reason": reason, "size_kb": size_kb(entry["worktree"])})
        print(json.dumps({"base": base, "candidates": candidates}, indent=1))
        return
    by_path = {os.path.realpath(e["worktree"]): e for e in entries}
    removed, refused = [], {}
    for path in args.paths:
        entry = by_path.get(os.path.realpath(path))
        if entry is None:
            refused[path] = "not a worktree of this repository"
            continue
        reason, why = judge(repo, entry, base, here)
        if not reason:
            refused[path] = why
            continue
        if reason != "missing on disk":
            out = git(repo, "worktree", "remove", entry["worktree"], check=False)
            if out.returncode != 0:
                refused[path] = out.stderr.strip()
                continue
        branch = entry.get("branch", "").removeprefix("refs/heads/")
        if branch and reason == "merged":
            git(repo, "branch", "-d", branch, check=False)
        removed.append(path)
    git(repo, "worktree", "prune")
    print(json.dumps({"removed": removed, "refused": refused}, indent=1))


if __name__ == "__main__":
    main()
