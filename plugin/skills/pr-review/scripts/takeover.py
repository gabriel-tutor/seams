#!/usr/bin/env python3
"""Take a pull request over: where the fixes may go, and a push that only ever does what the user was asked about.

  takeover.py target --facts FACTS.json
  takeover.py push --target TARGET.json --worktree DIR --commit SHA [--remote-url URL]

`target` decides, from facts the review gathered with gh, where the user's fixes go. FACTS.json:

  {"viewer": "login", "viewerPermission": "WRITE", "headOwnerType": "User" | "Organization", "authorId": 4242,
   "pr": {"number", "title", "url", "author": {"login"}, "isCrossRepository", "maintainerCanModify", "headRefName",
          "headRefOid", "headRepository": {"name"}, "headRepositoryOwner": {"login"}, "baseRefName"}}

(`gh pr view --json ...`, `gh repo view <base> --json viewerPermission`, `gh api users/<head owner>` for its type and
`gh api users/<author>` for the id). The answer is JSON: "mode" is "author-branch" (the author's own branch, where
GitHub lets the user push: their own pull request, a branch of a repository they can push to, or a fork whose
author allowed edits from maintainers and is a person: an organisation's fork cannot be edited that way),
"new-branch" (a branch of the user's in the base repository, and a pull request of theirs that names the author's) or
"fork" (the user cannot push to the base repository, so a fork of their own is the way in); "repo" and "branch" are
where to push; "trailer" is the line that keeps the author's credit (none on the user's own pull request); "reason"
says why. Anything gh could not say is no.

`push` pushes one commit of the take-over worktree to that target, and refuses unless it is exactly what the user was
asked about: the commit is the worktree's HEAD; it continues the pull request's head (history rewritten, or another
line, is refused); there is something to push; every commit it adds carries the trailer; and the push is not a force:
a branch the author moved meanwhile is left alone and the push is refused. There is no option to force. It records
what it pushed in pushed.json beside TARGET.json. Exits 0 when pushed, 1 when refused or failed (it says why), and 2
on a usage error.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True                 # the plugin folder is loaded in place: no __pycache__ in it

PUSH_RIGHTS = ("ADMIN", "MAINTAIN", "WRITE")


def base_repo(url: str) -> str:
    found = re.match(r"https?://[^/]+/([^/]+/[^/]+)/pull/\d+", url or "")
    if not found:
        raise ValueError(f"pr.url is not a pull request's URL: {url!r}")
    return found.group(1)


def safe(name: str) -> str:
    return re.sub(r"-{2,}", "-", re.sub(r"[^A-Za-z0-9_-]+", "-", name)).strip("-") or "branch"


def decide(facts: dict) -> dict:
    """Where the fixes go, and why (see the module's docstring)."""
    pr = facts["pr"]
    number, base = pr["number"], base_repo(pr["url"])
    author = (pr.get("author") or {}).get("login") or ""
    viewer = facts.get("viewer") or ""
    mine = bool(viewer) and viewer.casefold() == author.casefold()
    cross = bool(pr.get("isCrossRepository"))
    head_repo = base
    if cross:
        owner = (pr.get("headRepositoryOwner") or {}).get("login")
        name = (pr.get("headRepository") or {}).get("name")
        head_repo = f"{owner}/{name}" if owner and name else None
    can_push = facts.get("viewerPermission") in PUSH_RIGHTS
    trailer = None
    if not mine and author:
        ident = facts.get("authorId")
        trailer = f"Co-authored-by: {author} <{ident}+{author}@users.noreply.github.com>" if ident \
            else f"Co-authored-by: {author} <{author}@users.noreply.github.com>"
    answer = {"mode": None, "repo": None, "branch": pr.get("headRefName"), "base": pr.get("baseRefName"),
              "head": pr.get("headRefOid"), "number": number, "trailer": trailer, "reason": "",
              "pr_title": None, "pr_body": None}
    if mine and head_repo:
        answer.update(mode="author-branch", repo=head_repo, reason="it is your own pull request")
    elif not cross and can_push:
        answer.update(mode="author-branch", repo=base, reason=f"the branch is in {base}, which you can push to")
    elif cross and can_push and head_repo and pr.get("maintainerCanModify") is True and facts.get("headOwnerType") == "User":
        answer.update(mode="author-branch", repo=head_repo,
                      reason=f"the author allowed edits from maintainers, and you can push to {base}")
    elif can_push:
        why = ("the fork belongs to an organisation, whose branches maintainers cannot edit"
               if pr.get("maintainerCanModify") is True and facts.get("headOwnerType") != "User"
               else "the author did not allow edits from maintainers")
        answer.update(mode="new-branch", repo=base, branch=f"takeover/{number}-{safe(str(pr.get('headRefName')))}",
                      reason=f"{why}, so the fixes go on a branch of yours in {base}",
                      pr_title=f"Take over #{number}: {pr.get('title') or ''}".strip(),
                      pr_body=(f"Continues #{number} by @{author}, whose commits it keeps and whose credit it carries "
                               "(Co-authored-by). Opened to merge it without waiting for the author's reply."))
    else:
        answer.update(mode="fork", reason=f"you cannot push to {base} (your permission: "
                                          f"{facts.get('viewerPermission') or 'unknown'}), so a take-over needs a fork of "
                                          "your own: gh repo fork")
    return answer


def git(worktree: Path, *args: str) -> "tuple[int, str]":
    done = subprocess.run(["git", "-C", str(worktree), *args], capture_output=True, text=True, stdin=subprocess.DEVNULL,
                          env=dict(os.environ, GIT_TERMINAL_PROMPT="0"))
    return done.returncode, (done.stdout + done.stderr).strip()


def refuse(why: str) -> int:
    print(f"takeover.py: refused: {why}", file=sys.stderr)
    return 1


def push(args) -> int:
    try:
        target = json.loads(args.target.read_text())
        mode, branch, pr_head = target["mode"], target["branch"], target["head"]
    except (OSError, ValueError, KeyError, TypeError) as err:
        print(f"takeover.py: cannot read the target: {err}", file=sys.stderr)
        return 2
    if mode not in ("author-branch", "new-branch"):
        return refuse(f"the decision is {mode!r}: there is nowhere to push (a fork of your own comes first)")
    code, here = git(args.worktree, "rev-parse", "HEAD")
    code2, asked = git(args.worktree, "rev-parse", "--verify", f"{args.commit}^{{commit}}")
    if code or code2:
        return refuse(f"cannot read the commit in {args.worktree}: {here if code else asked}")
    if here != asked:
        return refuse(f"the worktree's HEAD is {here[:7]}, not the commit you were asked about ({asked[:7]})")
    if git(args.worktree, "merge-base", "--is-ancestor", pr_head, asked)[0] != 0:
        return refuse(f"{asked[:7]} does not continue the pull request's head {pr_head[:7]}: its history was rewritten, "
                      "or it is another line")
    code, listed = git(args.worktree, "rev-list", f"{pr_head}..{asked}")
    commits = listed.split()
    if code or not commits:
        return refuse(f"nothing to push: {asked[:7]} adds nothing to the pull request's head")
    trailer = target.get("trailer")
    for commit in commits:
        message = git(args.worktree, "log", "-1", "--format=%B", commit)[1]
        if trailer and trailer not in message.splitlines():
            return refuse(f"commit {commit[:7]} lacks the line {trailer!r}: Co-authored-by keeps the author's credit")
    url = args.remote_url or f"https://github.com/{target['repo']}.git"
    code, said = git(args.worktree, "push", url, f"{asked}:refs/heads/{branch}")
    if code != 0:
        return refuse(f"git push did not go through (a branch the author moved meanwhile is never forced): {said}")
    (args.target.parent / "pushed.json").write_text(json.dumps(
        {"commit": asked, "repo": target.get("repo"), "branch": branch, "mode": mode, "number": target.get("number")},
        indent=2) + "\n")
    print(f"pushed: {asked[:7]} to {target.get('repo')} {branch} ({mode}): {len(commits)} commit(s) on top of the "
          f"pull request's head {pr_head[:7]}")
    return 0


def main(argv: "list | None" = None) -> int:
    parser = argparse.ArgumentParser(description="Take a pull request over.")
    sub = parser.add_subparsers(dest="command", required=True)
    where = sub.add_parser("target", help="where the fixes may go")
    where.add_argument("--facts", type=Path, required=True, help="the facts the review gathered, as JSON")
    sending = sub.add_parser("push", help="push the one commit the user was asked about")
    sending.add_argument("--target", type=Path, required=True, help="the output of `target`, saved")
    sending.add_argument("--worktree", type=Path, required=True, help="the take-over worktree")
    sending.add_argument("--commit", required=True, help="the commit the user was asked about")
    sending.add_argument("--remote-url", help="push here instead of https://github.com/<repo>.git (tests)")
    args = parser.parse_args(argv)
    if args.command == "target":
        try:
            print(json.dumps(decide(json.loads(args.facts.read_text())), indent=2))
        except (OSError, ValueError, KeyError, TypeError) as err:
            print(f"takeover.py: {err}", file=sys.stderr)
            return 2
        return 0
    return push(args)


if __name__ == "__main__":
    sys.exit(main())
