#!/usr/bin/env python3
"""Pin each pull request's evidence directory at checkout, say where its review starts, and keep a batch's
progress file.

  evidence.py pin --pr URL HEAD BASELINE [--pr URL HEAD BASELINE ...]

URL is the pull request's (`gh pr view --json url`), HEAD its candidate (`headRefOid`) and BASELINE the
merge-base checkout found. Each pull request's evidence directory is
${TMPDIR:-/tmp}/seams-pr-review/<owner>-<repo>-<number>-<first 7 of HEAD>, named here so that every run
names it alike, with a .seams-pr-review marker recording what it was pinned at. What an earlier run left
there decides where the review starts:

  new, afresh           every step runs; afresh, the earlier run was pinned at another head or baseline (or
                        wrote an older marker), and everything it left is removed
  continue at Review    checks/ ran at this head and baseline and is kept
  continue at Draft     review.json for this head is kept
  reuse                 the draft (payload.json and review.md for this head) is kept, and posted.json when it
                        was posted

Anything a step after the one reached left (a half-written file, error.txt) is removed, so that nothing but
finished work at this head and baseline stands in for the review. The worktrees are git's: the output says
which to keep, remove or make, and leaves them as they are. A head that moved names another directory.

With more than one pull request it also writes the batch's progress file at the evidence root,
progress-<repository>-<hash>.md, in the progress-file shape: the session's repository (the git root at or
above the working directory), the evidence directories, each pull request's step read from its evidence,
and the command that continues the batch. run_checks.py, review_payload.py and post_reviews.py bring it up
to date as their step ends (refresh), and batch_report.py closes it when the handover covers every pull
request it lists (finish); the session-start hook lists an open one of the session's repository.

Exits 0 when every pull request is pinned; 1 when a directory is not the review's own (without the marker,
a link, another user's, another pull request's), with nothing pinned, or when pinning fails; 2 on a usage
error, before anything is written.
"""
from __future__ import annotations

import argparse
import contextlib
import fcntl
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

MARKER = ".seams-pr-review"
PR_URL = re.compile(r"^https://[^/\s]+/([A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?)/([A-Za-z0-9._-]+)/pull/([0-9]+)/?$")
SHA = re.compile(r"^[0-9a-f]{40}(?:[0-9a-f]{24})?$")


def evidence_root() -> Path:
    """Where every review's evidence lives: ${TMPDIR:-/tmp}/seams-pr-review, as the skill's commands say."""
    return Path(os.environ.get("TMPDIR") or "/tmp") / "seams-pr-review"


def parse_pr(url: str, head: str, baseline: str) -> dict:
    match = PR_URL.match(url)
    if not match or match.group(2) in (".", ".."):
        raise ValueError(f"not a pull request's URL: {url!r}")
    for name, sha in (("HEAD", head), ("BASELINE", baseline)):
        if not SHA.match(sha):
            raise ValueError(f"{name} is not a full commit SHA: {sha!r}")
    owner, repo, number = match.group(1), match.group(2), int(match.group(3))
    return {"url": url, "repo": f"{owner}/{repo}", "number": number, "head": head, "baseline": baseline,
            "name": f"{owner}-{repo}-{number}-{head[:7]}"}


def load_json(path: Path):
    """A JSON file's content, or None when it is missing or unreadable (a half-written file is no evidence)."""
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return None


def reached(evid: Path, head: str) -> str:
    """How far a review of `head` got in `evid`, from what each step leaves: checks/checks.json (checked),
    review.json for this head (reviewed), then payload.json and review.md for it (drafted), then posted.json
    (posted). A static review runs no checks, so a review stands without them."""
    review = load_json(evid / "review.json")
    reviewed = isinstance(review, dict) and isinstance(review.get("pr"), dict) and review["pr"].get("head") == head
    payload = load_json(evid / "payload.json")
    drafted = (reviewed and isinstance(payload, dict) and payload.get("commit_id") == head
               and (evid / "review.md").is_file())
    posted = load_json(evid / "posted.json")
    if drafted and isinstance(posted, dict) and posted.get("commit_id") == head:
        return "posted"
    if drafted:
        return "drafted"
    if reviewed:
        return "reviewed"
    checks = load_json(evid / "checks" / "checks.json")
    if isinstance(checks, list) and all(isinstance(c, dict) and "name" in c for c in checks):
        return "checked"
    return "pinned"


NEXT = {"pinned": "every step runs", "checked": "continue at Review", "reviewed": "continue at Draft",
        "drafted": "reuse: drafted at this head and baseline; it goes to Post",
        "posted": "reuse: posted at this head; nothing to post"}
# What each step leaves, in the order a review writes it; a pin keeps what the step reached needs and removes
# the rest, so that nothing an unfinished or another pin's review left can stand in for this one.
OUTPUTS = ("pr.diff", "probes", "checks", "review.json", "payload.json", "review.md", "posted.json", "error.txt")
KEPT = {"afresh": (), "pinned": ("pr.diff", "probes"), "checked": ("pr.diff", "probes", "checks"),
        "reviewed": ("pr.diff", "probes", "checks", "review.json"),
        "drafted": ("pr.diff", "probes", "checks", "review.json", "payload.json", "review.md"),
        "posted": ("pr.diff", "probes", "checks", "review.json", "payload.json", "review.md", "posted.json")}


def prune(evid: Path, step: str) -> None:
    """Remove every output the step reached does not keep: a directory with what is in it, a file or a link
    by its own name (a link is never followed)."""
    for name in OUTPUTS:
        path = evid / name
        if name in KEPT[step] or not os.path.lexists(path):
            continue
        if path.is_dir() and not path.is_symlink():
            shutil.rmtree(path)
        else:
            path.unlink()


class Refused(Exception):
    """A directory this review cannot call its own: exit 1, with nothing pinned or removed."""


def owned(path: Path) -> bool:
    """Whether the path itself (never what a link points at) belongs to this user."""
    try:
        return os.lstat(path).st_uid == os.getuid()
    except OSError:
        return False


def examine(pr: dict, root: Path) -> "tuple[str, str]":
    """Where this pull request's review starts, from what an earlier run left: the step (new, afresh, or the
    step reached) and the line that says so. Refused when the directory is not this review's own: a link, not a
    directory, without the marker, another user's, or holding another pull request's evidence."""
    evid, marker = root / pr["name"], root / pr["name"] / MARKER
    if os.path.islink(evid):
        raise Refused(f"{evid} is a link, not a directory a review made: stop and ask")
    if not os.path.lexists(evid):
        return "new", "new: every step runs"
    if not evid.is_dir():
        raise Refused(f"{evid} is not a directory: stop and ask")
    if not os.path.lexists(marker):
        raise Refused(f"{evid} exists without the marker ({MARKER}), so it is not a review's: stop and ask")
    if os.path.islink(marker) or not marker.is_file():
        raise Refused(f"{marker} is a link or not a file: stop and ask")
    if not (owned(evid) and owned(marker)):
        raise Refused(f"{evid} belongs to another user: stop and ask")
    earlier = load_json(marker)
    if not isinstance(earlier, dict):
        return "afresh", "afresh: its earlier marker is not one this script wrote; every step runs"
    if earlier.get("url") != pr["url"]:
        raise Refused(f"{evid} holds the evidence of {earlier.get('url')}, not of {pr['url']}: stop and ask")
    if earlier.get("candidate") != pr["head"] or earlier.get("baseline") != pr["baseline"]:
        was = f"head {str(earlier.get('candidate'))[:7]}, baseline {str(earlier.get('baseline'))[:7]}"
        return "afresh", f"afresh: the earlier review was pinned at {was}; every step runs"
    step = reached(evid, pr["head"])
    return step, NEXT[step]


def git(tree: Path, *args: str) -> "str | None":
    done = subprocess.run(["git", "-C", str(tree), *args], capture_output=True, text=True, stdin=subprocess.DEVNULL)
    return done.stdout.strip() if done.returncode == 0 else None


def left_behind(evid: Path) -> dict:
    """What the checks left in each tree, as run_checks.py records it in checks/left.json."""
    data = load_json(evid / "checks" / "left.json")
    data = data if isinstance(data, dict) else {}
    return {side: set(data.get(side) or []) if isinstance(data.get(side), list) else set() for side in ("head", "base")}


def tree_state(tree: Path, sha: str, left: set) -> str:
    """"at" for a git worktree at `sha` holding nothing its commit lacks but what a check left there, "absent" when
    there is no tree, "off" for anything else: another commit, a probe left behind, not a worktree."""
    if not os.path.lexists(tree):
        return "absent"
    if os.path.islink(tree) or not tree.is_dir():
        return "off"
    top, at = git(tree, "rev-parse", "--show-toplevel"), git(tree, "rev-parse", "HEAD")
    if top is None or os.path.realpath(top) != os.path.realpath(tree) or at != sha:
        return "off"
    status = git(tree, "status", "--porcelain", "--untracked-files=all")
    if status is None:
        return "off"
    return "off" if [line[3:] for line in status.splitlines() if line.strip() and line[3:] not in left] else "at"


NEEDS_TREES = ("new", "afresh", "pinned", "checked")      # the steps from Understand to Review read and run the trees


def worktrees(evid: Path, step: str, pr: dict) -> str:
    """What to do with the two worktrees and the diff before the review goes on. A review that continues at Review
    keeps trees its checks left as they were (installs included); one that runs every step gets fresh trees; one
    past Review needs none and keeps those it has until Cleanup. The worktrees are git's: this says what to do and
    leaves each one as it is."""
    left = left_behind(evid) if "checks" in KEPT.get(step, ()) else {"head": set(), "base": set()}
    keep, remade, dropped, fresh = [], [], [], []
    for side, sha in (("head", pr["head"]), ("base", pr["baseline"])):
        state = tree_state(evid / side, sha, left[side])
        if step in NEEDS_TREES:
            if state == "at" and step == "checked":
                keep.append(side)
            else:
                (fresh if state == "absent" else remade).append(side)
        elif state == "at":
            keep.append(side)
        elif state == "off":
            dropped.append(side)
    both = " and ".join
    parts = ([f"keep {both(keep)}" + ("" if step in NEEDS_TREES else " until Cleanup")] if keep else []) + \
            ([f"remove {both(remade)} as cleanup.md says, then make {'them' if len(remade) > 1 else 'it'} again"]
             if remade else []) + \
            ([f"remove {both(dropped)} as cleanup.md says"] if dropped else []) + \
            ([f"make {both(fresh)}"] if fresh else [])
    text = "; ".join(parts) or "none needed"
    if step in NEEDS_TREES + ("reviewed",):
        if (evid / "pr.diff").is_file():
            text += "; pr.diff kept"
        else:
            text += ", then pr.diff" if remade or fresh else "; make pr.diff"
    return text


def pin(pr: dict, root: Path, step: str, what: str) -> str:
    """Pin one pull request's evidence directory as `examine` decided; its lines of the output."""
    evid = root / pr["name"]
    evid.mkdir(exist_ok=True)
    if step != "new":
        prune(evid, step)
    (evid / MARKER).write_text(json.dumps({"url": pr["url"], "candidate": pr["head"], "baseline": pr["baseline"],
                                           "time": datetime.now().isoformat(timespec="seconds")}, indent=2) + "\n")
    return (f"- {pr['repo']}#{pr['number']} at {pr['head'][:7]}: {what}.\n  $EVID: {evid}\n"
            f"  worktrees: {worktrees(evid, step, pr)}")


# --- The batch's progress file ---------------------------------------------------------------------------------
# A batch keeps one progress file at the evidence root, per session repository: the progress-file shape (Status,
# Stage, Next, Updated, then sections), the repository whose sessions list it in their resume note, the evidence
# directories it pinned, and each pull request's step. Each step is read from the evidence itself, so the file
# can only lag behind the evidence, never contradict it.

STEPS = ("posted", "drafted", "reviewed", "checked", "pinned", "missing")      # furthest first
FINISHED = ("drafted", "posted")


def session_repo(start: Path) -> Path:
    """The repository the session runs in: the nearest directory at or above `start` with a .git entry, as the
    session-start hook finds it; `start` itself outside any repository."""
    start = start.resolve()
    for directory in (start, *start.parents):
        if (directory / ".git").exists():
            return directory
    return start


def batch_path(root: Path, repo: Path) -> Path:
    slug = re.sub(r"[^A-Za-z0-9._-]+", "-", repo.name).strip("-.")[:40] or "repository"
    return root / f"progress-{slug}-{hashlib.sha256(str(repo).encode()).hexdigest()[:8]}.md"


@contextlib.contextmanager
def locked(root: Path):
    """One writer of the root's progress files at a time: the reviewers of a batch update theirs at once."""
    try:
        handle = open(root / ".progress.lock", "a")
    except OSError:                           # no lock is no reason to lose the update
        yield
        return
    try:
        fcntl.flock(handle, fcntl.LOCK_EX)
        yield
    finally:
        handle.close()


def pr_state(evid: Path) -> dict:
    """One pull request of a batch, from its evidence directory: which one, pinned where, and its step."""
    marker = load_json(evid / MARKER) if not os.path.islink(evid) else None
    if not isinstance(marker, dict) or not PR_URL.match(str(marker.get("url"))):
        return {"url": "", "line": f"{evid.name}: missing", "step": "missing"}
    match = PR_URL.match(marker["url"])
    ref = f"{match.group(1)}/{match.group(2)}#{int(match.group(3))}"
    head, baseline = str(marker.get("candidate") or ""), str(marker.get("baseline") or "")
    step = reached(evid, head)
    line = f"{ref} at {head[:7]}, baseline {baseline[:7]}: {step}"
    error = evid / "error.txt"
    if step not in FINISHED and error.is_file() and not error.is_symlink():
        try:
            with open(error, "rb") as f:
                reason = " ".join(f.read(4096).decode("utf-8", "replace").split())[:120]
        except OSError:
            reason = ""
        line += f" (its reviewer stopped: {reason})" if reason else " (its reviewer stopped)"
    return {"url": marker["url"], "line": line, "step": step}


def render(repo: Path, names: list, status: str, root: Path) -> str:
    states = [pr_state(root / name) for name in names]
    n = len(states)
    counts = [f"{sum(1 for s in states if s['step'] == step)} {step}" for step in STEPS
              if any(s["step"] == step for s in states)]
    unfinished = sum(1 for s in states if s["step"] not in FINISHED)
    # The command that continues the batch names each pull request by its URL, which /pr-review takes and which the
    # resume note shows as it is (it drops `#` as markup, so owner/repo#number would not survive it).
    command = "/pr-review " + " ".join(s["url"] for s in states if s["url"])
    if status == "done":
        next_step = "Nothing left: the review handover was given."
    else:
        tail = (f"{unfinished} of {n} unfinished." if unfinished
                else "every review is drafted; Post and the handover remain.")
        next_step = f"The user types {command} again to continue it: {tail}"
        if len(next_step) > 200:              # the resume note shows 200 characters of a field
            next_step = f"The user types the /pr-review command under Continue in this file again to continue it: {tail}"
    lines = ["# Progress: pr-review batch", "",
             f"Status: {status}",
             f"Stage: {n} pull request{'s' if n != 1 else ''} ({', '.join(counts)})",
             f"Next: {next_step}",
             f"Updated: {datetime.now().strftime('%Y-%m-%dT%H:%M')}",
             f"Repository: {repo}",
             f"Evidence: {' '.join(names)}", "",
             "## Pull requests", ""] + [f"- {s['line']}" for s in states] + \
            ["", "## Continue", "", "Typed again by the user, this command continues the batch: a review finished at the "
             "same head and baseline is reused, an unfinished one goes on from its last completed step, and a pull "
             "request whose head moved is reviewed afresh.", "", f"    {command}", "",
             "Kept by pr-review's scripts. Each pull request's evidence is the directory under Evidence, beside this "
             "file; its step is read from what that directory holds."]
    return "\n".join(lines) + "\n"


def write_batch(path: Path, repo: Path, names: list, status: str) -> None:
    """Write the batch's progress file whole, then put it in place, so that a reader never sees half of one."""
    part = path.with_name(f".{path.name}.{os.getpid()}.part")
    try:
        part.write_text(render(repo, names, status, path.parent))
        os.replace(part, path)
    finally:
        if os.path.lexists(part):
            part.unlink()


def batches(root: Path) -> list:
    """This user's batch progress files at the root: (path, status, repository, evidence directory names)."""
    found = []
    for path in sorted(root.glob("progress-*.md")):
        if path.is_symlink() or not path.is_file() or not owned(path):
            continue
        fields = {}
        for line in path.read_text(errors="replace").split("\n## ")[0].splitlines():
            key, sep, value = line.partition(":")
            if sep and key.isalpha() and key.lower() not in fields:
                fields[key.lower()] = value.strip()
        names = [n for n in fields.get("evidence", "").split() if re.match(r"^[A-Za-z0-9._-]+$", n)]
        if fields.get("status") in ("active", "done") and fields.get("repository") and names:
            found.append((path, fields["status"], Path(fields["repository"]), names))
    return found


def refresh(evid) -> None:
    """Bring every batch progress file that lists this evidence directory up to date, after a script wrote one of
    its outputs. Never raises: the file is a pointer, and a script's own work never waits on it."""
    try:
        evid = Path(os.path.abspath(evid))
        if not isinstance(load_json(evid / MARKER), dict):
            return                            # not a review's evidence directory: nothing lists it
        with locked(evid.parent):
            for path, status, repo, names in batches(evid.parent):
                if evid.name in names:
                    write_batch(path, repo, names, status)
    except Exception as err:                  # noqa: BLE001
        print(f"note: the batch's progress file was not brought up to date ({err})", file=sys.stderr)


def finish(folders) -> None:
    """Close every open batch whose pull requests the review handover covered, all of them. Never raises."""
    try:
        by_root: dict = {}
        for folder in (Path(os.path.abspath(f)) for f in folders):
            by_root.setdefault(folder.parent, set()).add(folder.name)
        for root, covered in by_root.items():
            with locked(root):
                for path, status, repo, names in batches(root):
                    if status == "active" and set(names) <= covered:
                        write_batch(path, repo, names, "done")
    except Exception as err:                  # noqa: BLE001
        print(f"note: the batch's progress file was not closed ({err})", file=sys.stderr)


def main(argv: "list | None" = None) -> int:
    parser = argparse.ArgumentParser(description="Pin each pull request's evidence directory at checkout.")
    commands = parser.add_subparsers(dest="command", required=True)
    pin_parser = commands.add_parser("pin", help="pin the pull requests of this review")
    pin_parser.add_argument("--pr", action="append", nargs=3, required=True, metavar=("URL", "HEAD", "BASELINE"),
                            help="a pull request's URL, its head and its baseline (repeatable)")
    args = parser.parse_args(argv)
    try:
        prs = [parse_pr(*triple) for triple in args.pr]
        if len({pr["name"] for pr in prs}) != len(prs):
            raise ValueError("a pull request is named twice")
    except ValueError as err:
        print(f"evidence.py: {err}", file=sys.stderr)
        return 2
    root = evidence_root()
    try:
        if os.path.islink(root) or (os.path.lexists(root) and not (root.is_dir() and owned(root))):
            raise Refused(f"{root} is not a directory of this user's: stop and ask")
        if os.path.lexists(root) and os.lstat(root).st_mode & 0o002:
            raise Refused(f"{root} lets other users write in it: stop and ask")
        decisions = [examine(pr, root) for pr in prs]      # every directory is judged before any is touched
    except Refused as err:
        print(f"evidence.py: refused: {err}", file=sys.stderr)
        return 1
    try:
        root.mkdir(mode=0o700, parents=True, exist_ok=True)
        for pr, (step, what) in zip(prs, decisions):
            print(pin(pr, root, step, what), flush=True)
        if len(prs) > 1:
            repo = session_repo(Path.cwd())
            path = batch_path(root, repo)
            with locked(root):
                write_batch(path, repo, [pr["name"] for pr in prs], "active")
            print(f"The batch's progress file: {path}")
        else:                                 # one pull request of a batch, pinned again on its own
            refresh(root / prs[0]["name"])
    except OSError as err:
        print(f"evidence.py: pinning failed after the lines above: {err}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
