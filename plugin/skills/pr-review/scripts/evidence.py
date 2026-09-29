#!/usr/bin/env python3
"""Pin each pull request's evidence directory at checkout, say where its review starts, and keep a batch's
progress file.

  evidence.py pin [--afresh] --pr URL HEAD BASELINE [--pr URL HEAD BASELINE ...]

URL is the pull request's (`gh pr view --json url`), HEAD its candidate (`headRefOid`) and BASELINE the
merge-base checkout found. Each pull request's evidence directory is
${TMPDIR:-/tmp}/seams-pr-review/<owner>-<repo>-<number>-<first 7 of HEAD>, named here so that every run
names it alike, with a .seams-pr-review marker recording what it was pinned at. What an earlier run left
there decides where the review starts:

  new, afresh                every step runs; afresh, the request said so (--afresh), or the earlier run was
                             pinned at another head or baseline, or wrote an older marker: nothing it left is kept
  continue with its checks   checks/ ran at this head and baseline and is kept; every other step runs, Understand
                             and the parts of Checks that leave no file (Try it, Security) included
  continue at Draft          review.json for this head is kept; its payload is built
  reuse                      the draft (payload.json and review.md for this head) is kept and goes to Post, or,
                             posted at this head (posted.json), there is nothing left to post

Anything else an earlier run left (a later step's half-written file, error.txt) is removed, and so is the diff
before any step that reads it, so that nothing but finished work at this head and baseline stands in for the
review. Only the user's own files count. The worktrees are git's: the output says which to keep, remove or make,
and leaves them as they are. A head that moved names another directory.

With more than one pull request it also writes the batch's progress file at the evidence root, in the progress-file
shape, named after the session's repository (the git root at or above the working directory) and the batch's pull
requests: the repository, the evidence directories, each pull request's step read from its evidence, and the
command that continues the batch. run_checks.py, review_payload.py and post_reviews.py bring it up to date as their
step ends (update_batches), and batch_report.py --close closes it at the final handover once every review in it is
drafted or posted (close_batches). The session-start hook lists an open one of the session's repository.

Exits 0 when every pull request is pinned; 1 when a directory is not the review's own (without the marker, a link,
another user's, another pull request's), with nothing pinned, or when pinning fails; 2 on a usage error, before
anything is written.
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

sys.dont_write_bytecode = True                 # the plugin folder is loaded in place: no __pycache__ in it
sys.path.insert(0, str(Path(__file__).resolve().parent))   # run_checks.py beside it, even under PYTHONSAFEPATH

MARKER = ".seams-pr-review"
PR_URL = re.compile(r"^https://([^/\s]+)/([A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?)/([A-Za-z0-9._-]+)/pull/([0-9]+)/?$")
SHA = re.compile(r"^[0-9a-f]{40}(?:[0-9a-f]{24})?$")


def evidence_root() -> Path:
    """Where every review's evidence lives: ${TMPDIR:-/tmp}/seams-pr-review, as the skill's commands say."""
    return Path(os.environ.get("TMPDIR") or "/tmp") / "seams-pr-review"


def parse_pr(url: str, head: str, baseline: str) -> dict:
    """A pull request as the command line names it, its URL in the one form GitHub gives (`gh pr view --json url`)."""
    match = PR_URL.match(url)
    if not match or match.group(3) in (".", ".."):
        raise ValueError(f"not a pull request's URL: {url!r}")
    for name, sha in (("HEAD", head), ("BASELINE", baseline)):
        if not SHA.match(sha):
            raise ValueError(f"{name} is not a full commit SHA: {sha!r}")
    host, owner, repo, number = match.group(1), match.group(2), match.group(3), int(match.group(4))
    return {"url": f"https://{host}/{owner}/{repo}/pull/{number}", "repo": f"{owner}/{repo}", "number": number,
            "head": head, "baseline": baseline, "name": f"{owner}-{repo}-{number}-{head[:7]}"}


def load_json(path: Path):
    """A JSON file's content, or None when it is missing or unreadable (a half-written file is no evidence)."""
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return None


def evidence_json(path: Path):
    """A file a review wrote, as JSON: None when it is missing, unreadable, a link, or not the user's own (on a machine
    others share, a file someone else put there is no evidence of this review)."""
    if os.path.islink(path) or not owned(path):
        return None
    return load_json(path)


def reached(evid: Path, head: str) -> str:
    """How far a review of `head` got in `evid`, from what each step leaves: checks/checks.json (checked),
    review.json for this head (reviewed), then payload.json and review.md for it (drafted), and posted.json for it
    (posted, whatever else is missing: it is the only local record that GitHub has the review). A static review runs
    no checks, so a review stands without them."""
    posted = evidence_json(evid / "posted.json")
    if isinstance(posted, dict) and posted.get("commit_id") == head:
        return "posted"
    review = evidence_json(evid / "review.json")
    if isinstance(review, dict) and isinstance(review.get("pr"), dict) and review["pr"].get("head") == head:
        payload = evidence_json(evid / "payload.json")
        preview = evid / "review.md"
        if isinstance(payload, dict) and payload.get("commit_id") == head and owned(preview) \
                and not os.path.islink(preview):
            return "drafted"
        return "reviewed"
    checks = evidence_json(evid / "checks" / "checks.json")
    if isinstance(checks, list) and all(isinstance(c, dict) and "name" in c for c in checks):
        return "checked"
    return "pinned"


NEXT = {"pinned": "every step runs",
        "checked": "continue with its checks: they ran at this head and baseline; every other step runs",
        "reviewed": "continue at Draft: its review.json is kept; build its payload",
        "drafted": "reuse: drafted at this head and baseline; it goes to Post",
        "posted": "reuse: posted at this head; nothing to post"}
# What each step leaves, in the order a review writes it; a pin keeps what the step reached needs and removes
# the rest, so that nothing an unfinished or another pin's review left can stand in for this one. The diff is made
# again before any step that reads it (git makes it from the two pinned commits in a moment), so an empty or cut-short
# one never stands; a draft keeps the diff it was built from.
OUTPUTS = ("pr.diff", "probes", "checks", "review.json", "payload.json", "review.md", "posted.json", "error.txt")
KEPT = {"afresh": (), "pinned": ("probes",), "checked": ("probes", "checks"),
        "reviewed": ("probes", "checks", "review.json"),
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


def examine(pr: dict, root: Path, afresh: bool = False) -> "tuple[str, str]":
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
    if afresh and earlier.get("url") == pr["url"]:
        return "afresh", "afresh, as the request asked: nothing an earlier run left is kept; every step runs"
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


def run_checks():
    """run_checks.py beside this script, the one judge of what a tree holds beyond its commit: a tree it would refuse
    is never kept. Imported when needed, since run_checks.py imports this module as it loads."""
    import run_checks as module
    return module


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
    return "off" if [f for f in run_checks().stray_files(tree) if f not in left] else "at"


NEEDS_TREES = ("new", "afresh", "pinned", "checked")      # the steps from Understand to Review read and run the trees


def worktrees(evid: Path, step: str, pr: dict) -> str:
    """What to do with the two worktrees and the diff before the review goes on. A review that continues at Review
    keeps trees its checks left as they were (installs included); one that runs every step gets fresh trees; one
    past Review needs none and keeps those it has until Cleanup. The worktrees are git's: this says what to do and
    leaves each one as it is."""
    left = run_checks().left_behind(evid / "checks") if "checks" in KEPT.get(step, ()) else {"head": set(), "base": set()}
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
    text = "; ".join(parts)
    if step in NEEDS_TREES + ("reviewed",):
        text += ", then pr.diff" if remade or fresh else ("; " if text else "") + "make pr.diff"
    return text or "none needed"


def pin(pr: dict, root: Path, step: str, what: str) -> str:
    """Pin one pull request's evidence directory as `examine` decided; its lines of the output."""
    evid = root / pr["name"]
    evid.mkdir(mode=0o700, exist_ok=True)
    os.chmod(evid, 0o700)                     # the user's alone, whatever the umask made it (see main)
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


def batch_path(root: Path, repo: Path, urls: list) -> Path:
    """A batch's file: named after the session's repository and the batch's pull requests, so that typing the same
    pull requests again continues it, and another batch in the same repository keeps a file of its own."""
    slug = re.sub(r"[^A-Za-z0-9._-]+", "-", repo.name).strip("-.")[:40] or "repository"
    key = hashlib.sha256("\n".join([str(repo)] + sorted(urls)).encode()).hexdigest()[:10]
    return root / f"progress-{slug}-{key}.md"


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
    ref = f"{match.group(2)}/{match.group(3)}#{int(match.group(4))}"
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


def in_words(items: list) -> str:
    return items[0] if len(items) == 1 else ", ".join(items[:-1]) + " and " + items[-1]


def described(urls: list) -> str:
    """The batch's pull requests in words, by number and repository: "pull requests 5, 6 and 7 of owner/repo"."""
    by_repo: dict = {}
    for url in urls:
        match = PR_URL.match(url)
        by_repo.setdefault(f"{match.group(2)}/{match.group(3)}", []).append(int(match.group(4)))
    groups = [f"{in_words([str(n) for n in sorted(numbers)])} of {name}" for name, numbers in by_repo.items()]
    return f"pull request{'s' if len(urls) != 1 else ''} {in_words(groups)}"


def render(repo: Path, names: list, status: str, root: Path) -> str:
    states = [pr_state(root / name) for name in names]
    n = len(states)
    counts = [f"{sum(1 for s in states if s['step'] == step)} {step}" for step in STEPS
              if any(s["step"] == step for s in states)]
    unfinished = sum(1 for s in states if s["step"] not in FINISHED)
    # The command that continues the batch names each pull request by its URL, which /pr-review takes; the next step
    # names them by number and repository, which fits the 200 characters the resume note shows of a field (it drops
    # `#` as markup, so owner/repo#number would not survive it), and points at the command when even that does not.
    urls = [s["url"] for s in states if s["url"]]
    command = "/pr-review " + " ".join(urls)
    if status == "done":
        next_step = "Nothing left: the review handover was given."
    else:
        tail = (f"{unfinished} of {n} unfinished." if unfinished
                else "every review is drafted; Post and the handover remain.")
        next_step = f"Continue it with pr-review on {described(urls)}: {tail}" if urls else ""
        if not urls or len(next_step) > 200:
            next_step = f"Continue it with the /pr-review command under Continue in this file: {tail}"
    lines = ["# Progress: pr-review batch", "",
             f"Status: {status}",
             f"Stage: {n} pull request{'s' if n != 1 else ''}: {', '.join(counts)}",
             f"Next: {next_step}",
             f"Updated: {datetime.now().strftime('%Y-%m-%dT%H:%M')}",
             f"Repository: {repo}",
             f"Evidence: {' '.join(names)}", "",
             "## Pull requests", ""] + [f"- {s['line']}" for s in states] + \
            ["", "## Continue", "", "Typed again by the user, this command continues the batch: a review finished at the "
             "same head and baseline is reused, an unfinished one goes on from its last completed step, and a pull "
             "request whose head moved is reviewed afresh. With `afresh` added, every one is reviewed anew.", "",
             f"    {command}", "",
             "Kept by pr-review's scripts. Each pull request's evidence is the directory under Evidence, beside this "
             "file; its step is read from what that directory holds."]
    return "\n".join(lines) + "\n"


def write_batch(path: Path, repo: Path, names: list, status: str) -> None:
    """Write the batch's progress file whole, then put it in place, so that a reader never sees half of one."""
    part = path.with_name(f".{path.name}.{os.getpid()}.part")
    if os.path.lexists(part):                 # a crashed writer's; unlinking a link never touches its target
        part.unlink()
    try:
        fd = os.open(part, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w") as f:
            f.write(render(repo, names, status, path.parent))
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


def update_batches(evid) -> None:
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


def close_batches(folders) -> None:
    """Close every open batch the final review handover covered whole, once every review in it is drafted or posted:
    a review that could not finish keeps its batch open, and the resume note listing it. Never raises."""
    try:
        by_root: dict = {}
        for folder in (Path(os.path.abspath(f)) for f in folders):
            by_root.setdefault(folder.parent, set()).add(folder.name)
        for root, covered in by_root.items():
            with locked(root):
                for path, status, repo, names in batches(root):
                    if status == "active" and set(names) <= covered and \
                            all(pr_state(root / name)["step"] in FINISHED for name in names):
                        write_batch(path, repo, names, "done")
    except Exception as err:                  # noqa: BLE001
        print(f"note: the batch's progress file was not closed ({err})", file=sys.stderr)


def main(argv: "list | None" = None) -> int:
    parser = argparse.ArgumentParser(description="Pin each pull request's evidence directory at checkout.")
    commands = parser.add_subparsers(dest="command", required=True)
    pin_parser = commands.add_parser("pin", help="pin the pull requests of this review")
    pin_parser.add_argument("--pr", action="append", nargs=3, required=True, metavar=("URL", "HEAD", "BASELINE"),
                            help="a pull request's URL, its head and its baseline (repeatable)")
    pin_parser.add_argument("--afresh", action="store_true",
                            help="keep nothing an earlier run left: the request said afresh")
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
        decisions = [examine(pr, root, args.afresh) for pr in prs]   # every directory is judged before any is touched
    except Refused as err:
        print(f"evidence.py: refused: {err}", file=sys.stderr)
        return 1
    try:
        # The evidence, and the batch's file beside it, are the user's alone: on a machine whose users share a group,
        # a finished review planted in a group-writable directory would be offered at Post.
        root.mkdir(mode=0o700, parents=True, exist_ok=True)
        os.chmod(root, 0o700)
        for pr, (step, what) in zip(prs, decisions):
            print(pin(pr, root, step, what), flush=True)
        if len(prs) > 1:
            repo = session_repo(Path.cwd())
            path = batch_path(root, repo, [pr["url"] for pr in prs])
            with locked(root):
                write_batch(path, repo, [pr["name"] for pr in prs], "active")
            print(f"The batch's progress file: {path}")
        else:                                 # one pull request of a batch, pinned again on its own
            update_batches(root / prs[0]["name"])
    except OSError as err:
        print(f"evidence.py: pinning failed after the lines above: {err}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
