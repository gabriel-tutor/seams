#!/usr/bin/env python3
"""The worktree sweep: the repository's worktrees whose work is merged, so they stop filling the disk.

    sweep_worktrees.py list [--repo DIR] [--base BRANCH]          JSON: {"base", "candidates": [{path, branch, reason, size_kb}]}
    sweep_worktrees.py remove PATH... [--repo DIR] [--base BRANCH]  JSON: {"removed": [...], "refused": {path: why}}

A candidate is clean and merged. Clean: `git status` succeeds and shows nothing uncommitted or untracked, and any
ignored file is one a build regenerates (node_modules/, caches, build output), since `git worktree remove` deletes
ignored files. Merged: its HEAD is a commit of the base branch, local or on origin, and work was committed in it
(a worktree just made sits at the base's tip too), or its branch's pull request was merged on GitHub at this very HEAD
(a squash merge). The main worktree, the current one, a locked one and one missing on disk never are. `remove`
checks each path again, runs `git worktree remove` without force and deletes the branch with -d (which refuses one
not fully merged); it prunes nothing else. Exit 0 with the JSON; exit 1 when the repository can't be read.
Standard library only; it writes no bytecode.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys

sys.dont_write_bytecode = True

REGENERABLE = {"node_modules", ".venv", "venv", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", ".tox",
               "dist", "build", ".next", ".nuxt", ".turbo", ".parcel-cache", ".cache", "coverage", "target", ".gradle",
               ".expo", ".DS_Store"}


def git(repo, *args, check=True):
    out = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True)
    if check and out.returncode != 0:
        print(f"git {' '.join(args)}: {out.stderr.strip()}", file=sys.stderr)
        raise SystemExit(1)
    return out


def worktrees(repo):
    """Every worktree from `git worktree list --porcelain -z`, the main one first."""
    entries, cur = [], {}
    for field in git(repo, "worktree", "list", "--porcelain", "-z").stdout.split("\0"):
        if not field:
            if cur:
                entries.append(cur)
            cur = {}
            continue
        key, _, value = field.partition(" ")
        cur[key] = value or True
    return entries


def branch_of(entry):
    return str(entry.get("branch", "")).removeprefix("refs/heads/")


def default_base(repo):
    head = git(repo, "symbolic-ref", "--quiet", "--short", "refs/remotes/origin/HEAD", check=False).stdout.strip()
    if head:
        return head.split("/", 1)[1]
    for name in ("main", "master", "develop"):
        if git(repo, "rev-parse", "--verify", "--quiet", name, check=False).returncode == 0:
            return name
    return "main"


def pr_merged_at(repo, branch, head):
    """Whether a pull request from this branch was merged with this exact HEAD (a reused name or later work is not)."""
    try:
        out = subprocess.run(["gh", "pr", "list", "--head", branch, "--state", "merged", "--json", "headRefOid",
                              "--limit", "20"], cwd=str(repo), capture_output=True, text=True, timeout=30)
        return out.returncode == 0 and any(p.get("headRefOid") == head for p in json.loads(out.stdout or "[]"))
    except (OSError, subprocess.TimeoutExpired, ValueError, AttributeError):
        return False


def unclean(path):
    """Why the worktree is not clean, or None."""
    out = git(path, "status", "--porcelain", "--ignored", "--untracked-files=normal", check=False)
    if out.returncode != 0:
        return "git status failed: " + out.stderr.strip()
    kept = []
    for line in out.stdout.splitlines():
        if not line.startswith("!! "):
            return "not clean: uncommitted or untracked files"
        name = line[3:].rstrip("/").split("/")[-1]
        if name not in REGENERABLE and not name.endswith((".pyc", ".log")):
            kept.append(line[3:])
    return f"not clean: ignored files would be deleted ({', '.join(kept[:5])})" if kept else None


def committed_in(path):
    """Whether work was committed in this worktree: at the base's tip, a fast-forward merge reads like a worktree
    just made, and only its own HEAD reflog tells them apart."""
    out = git(path, "reflog", "--format=%gs", "-n", "50", "HEAD", check=False)
    return out.returncode == 0 and any(line.startswith("commit") for line in out.stdout.splitlines())


def judge(repo, entry, base, protected):
    """(reason, None) when the worktree may be removed, else (None, why not)."""
    path = entry["worktree"]
    if os.path.realpath(path) in protected:
        return None, "the main or current worktree"
    if entry.get("locked"):
        return None, "locked"
    if entry.get("prunable") or not os.path.isdir(path):
        return None, "missing on disk (`git worktree prune` clears it)"
    why = unclean(path)
    if why:
        return None, why
    head = str(entry.get("HEAD", ""))
    for ref in (base, f"origin/{base}"):
        tip = git(repo, "rev-parse", "--verify", "--quiet", ref, check=False).stdout.strip()
        if tip and git(repo, "merge-base", "--is-ancestor", head, ref, check=False).returncode == 0 \
                and (head != tip or committed_in(path)):
            return "merged", None
    branch = branch_of(entry)
    if branch and pr_merged_at(repo, branch, head):
        return "pull request merged", None
    return None, "not merged (or nothing committed in it yet)"


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
    entries = worktrees(repo)
    here = git(os.getcwd(), "rev-parse", "--show-toplevel", check=False).stdout.strip()
    protected = {os.path.realpath(entries[0]["worktree"])} | ({os.path.realpath(here)} if here else set())
    if args.action == "list":
        candidates = []
        for entry in entries[1:]:
            reason, _ = judge(repo, entry, base, protected)
            if reason:
                candidates.append({"path": entry["worktree"], "branch": branch_of(entry), "reason": reason,
                                   "size_kb": size_kb(entry["worktree"])})
        print(json.dumps({"base": base, "candidates": candidates}, indent=1))
        return
    by_path = {os.path.realpath(e["worktree"]): e for e in entries}
    removed, refused = [], {}
    for path in args.paths:
        entry = by_path.get(os.path.realpath(path))
        if entry is None:
            refused[path] = "not a worktree of this repository"
            continue
        reason, why = judge(repo, entry, base, protected)
        if not reason:
            refused[path] = why
            continue
        out = git(repo, "worktree", "remove", entry["worktree"], check=False)
        if out.returncode != 0:
            refused[path] = out.stderr.strip()
            continue
        if reason == "merged" and branch_of(entry):
            git(repo, "branch", "-d", branch_of(entry), check=False)
        removed.append(path)
    print(json.dumps({"removed": removed, "refused": refused}, indent=1))


if __name__ == "__main__":
    main()
