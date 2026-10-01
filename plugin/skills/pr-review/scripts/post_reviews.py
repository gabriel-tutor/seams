#!/usr/bin/env python3
"""Post the reviews a person chose, one at a time, paced under GitHub's limits, and say where each landed.

  post_reviews.py [--auto] [--per-minute N] [--per-hour N] [--minute SECONDS] [--backoff SECONDS]
                  [--slow SECONDS] [--tries N] EVID [EVID ...]

Each EVID is one pull request's evidence directory: review.json (which pull request, at which
commit) and payload.json (the review GitHub receives, from review_payload.py), posted in the order
given with `gh api`. Before each post it looks for the same review already on GitHub (the viewer's,
at that commit, with that body) and does not post it twice, and it re-reads the pull request's head:
a pull request that moved since its review is stale and is not posted.

GitHub allows 80 content-creating requests a minute and 500 an hour, one at a time; a batch of 15
reviews was blocked after 10 in 34 seconds, so a review counts 1 plus its inline comments, and the
posts stay under half of each limit. A post GitHub blocks for a rate limit (403 or 429) waits as
GitHub asks (retry-after, or the reset time; otherwise --backoff seconds, doubling), is looked for
again (a refused post is sometimes kept), and is tried again, up to --tries times; from the first
block on, posts are --slow seconds apart. Retrying the same approved review needs no new approval.
A wait longer than all the tries' backoff together (a primary limit resetting within the hour) is
not taken: the run says when to post again. Any other refusal, a failure of gh itself, or a block
that does not lift ends the run: the reviews after it are not tried, so the person can decide, and
running it again finds what is already posted. --minute shortens the budget's minute for tests.

With --auto a review posts without a person's yes only when it is fully verified at its head (CONTEXT.md) and the
viewer can push to the repository; the rule is read from the evidence on disk, never from the model's say-so:
checks/checks.json lists at least one check and none "could not run" or "flaky", review.json's not_verified is empty,
every finding but a question or praise is verified at the head, every blocking one has a proof (a check, a probe,
a reproduction or a citation), and an APPROVE needs an independent reference (intent.independent). A review that
falls short is not posted: `needs your yes: <review>: <why>` is printed, it counts as not on GitHub (exit 1), and
the reviews after it are still tried. Without --auto the poster posts what the person chose, as it always did.

Each review posted is recorded in EVID/posted.json, and the progress file of a batch listing EVID brought up to
date (evidence.py), and its link printed. Exits 0 when every review
is on GitHub, 1 when any is not (each says why), and 2 on a usage error, before anything is posted.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

sys.dont_write_bytecode = True                 # the plugin folder is loaded in place: no __pycache__ in it
sys.path.insert(0, str(Path(__file__).resolve().parent))   # beside this script, even under PYTHONSAFEPATH
try:
    import evidence                            # the batch's progress file, kept current as each step ends
except Exception:                              # noqa: BLE001  never a reason for a script to stop
    evidence = None


class GhError(Exception):
    pass


def gh_json(path: str):
    """A GET through `gh api`, its JSON body."""
    done = subprocess.run(["gh", "api", path], capture_output=True, text=True, stdin=subprocess.DEVNULL)
    if done.returncode != 0:
        raise GhError((done.stderr or done.stdout).strip() or f"gh api {path} failed")
    return json.loads(done.stdout)


def load(folder: Path) -> dict:
    """One pull request's review, ready to post."""
    review = json.loads((folder / "review.json").read_text())
    payload = json.loads((folder / "payload.json").read_text())
    pr = review["pr"]
    repo, number, head = pr["repo"], int(pr["number"]), pr["head"]
    if payload.get("commit_id") != head:
        raise ValueError(f"{folder}: payload.json is for {str(payload.get('commit_id'))[:7]}, "
                         f"the review for {head[:7]}; rebuild it with review_payload.py")
    return {"folder": folder, "repo": repo, "number": number, "head": head, "payload": payload, "review": review,
            "name": f"{repo}#{number} at {head[:7]} as {payload.get('event')}"}


PROOFS = ("check", "probe", "reproduction", "citation")      # what a blocking finding may rest on (CONTEXT.md, Finding)
PUSH_RIGHTS = ("push", "maintain", "admin")


def may_push(repo: str, known: dict) -> bool:
    """Whether the viewer can push to the repository: where a review is expected. Anything gh cannot say is no."""
    if repo not in known:
        try:
            rights = gh_json(f"repos/{repo}").get("permissions") or {}
        except (GhError, ValueError, AttributeError):
            rights = {}
        known[repo] = any(rights.get(right) is True for right in PUSH_RIGHTS)
    return known[repo]


def shortfalls(review: dict, can_push: bool) -> list:
    """Why this review may not post without a yes: one line each, [] when it is fully verified at its head.
    Fails closed: evidence that is missing or unreadable is evidence of nothing."""
    data, reasons = review["review"], []
    try:
        rows = json.loads((review["folder"] / "checks" / "checks.json").read_text())
    except (OSError, ValueError):
        rows = None
    if not isinstance(rows, list) or not rows or not all(isinstance(r, dict) for r in rows):
        reasons.append("no check ran (static review, or no readable checks/checks.json)")
    else:
        for row in rows:
            if row.get("verdict") in ("could not run", "flaky"):
                reasons.append(f"{row['verdict']}: {row.get('name')}")
    left = data.get("not_verified")
    if not isinstance(left, list) or left:
        reasons.append("left under not verified: " + ("; ".join(map(str, left))[:200] if isinstance(left, list)
                                                       else "review.json has no not_verified list"))
    findings = data.get("findings")
    if not isinstance(findings, list):
        findings = []
        reasons.append("review.json has no findings list")
    for finding in findings:
        if not isinstance(finding, dict):
            reasons.append("a finding is not readable")
            continue
        title = str(finding.get("title") or "untitled")
        if finding.get("severity") not in ("question", "praise") and finding.get("verified") is not True:
            reasons.append(f"finding not verified at the head: {title}")
        if finding.get("severity") == "blocking" and finding.get("proof") not in PROOFS:
            reasons.append(f"blocking finding has no proof (one of {', '.join(PROOFS)}): {title}")
    if not can_push:
        reasons.append(f"the viewer cannot push to {review['repo']}")
    intent = data.get("intent")
    if review["payload"].get("event") == "APPROVE" and not (isinstance(intent, dict) and intent.get("independent") is True):
        reasons.append("an approval needs an independent reference, and the pull request's own description is not one")
    return reasons


def already_posted(review: dict, viewer: str):
    """This very review when GitHub already has it: the viewer's, at this commit, with this body.
    Checked before every post, so a post GitHub refused but kept is never posted twice."""
    page = 1
    while True:
        batch = gh_json(f"repos/{review['repo']}/pulls/{review['number']}/reviews?per_page=100&page={page}")
        for posted in batch:
            if ((posted.get("user") or {}).get("login") == viewer and posted.get("commit_id") == review["head"]
                    and (posted.get("body") or "").strip() == (review["payload"].get("body") or "").strip()):
                return posted
        if len(batch) < 100:
            return None
        page += 1


def message(body) -> str:
    return str(body.get("message") or body) if isinstance(body, dict) else str(body)


def rate_limited(status: int, headers: dict, body) -> bool:
    """A refusal that waiting cures: GitHub's secondary limit, or the primary one run dry."""
    return status in (403, 429) and ("rate limit" in message(body).lower() or "retry-after" in headers
                                     or headers.get("x-ratelimit-remaining") == "0")


def delay(headers: dict, backoff: float, blocks: int) -> "tuple[float, float]":
    """What GitHub asks, as the seconds to wait and the time its limit lifts: retry-after's seconds,
    or until the primary limit resets (the wait runs a second past the reset, which is the lift
    time); otherwise a backoff that doubles with each block of this review."""
    now = time.time()
    try:
        wait = max(0.0, float(headers["retry-after"]))
        return wait, now + wait
    except (KeyError, ValueError):
        pass
    if headers.get("x-ratelimit-remaining") == "0":
        try:
            reset = float(headers["x-ratelimit-reset"])
            return max(0.0, reset - now) + 1, reset
        except (KeyError, ValueError):
            pass
    wait = backoff * 2 ** (blocks - 1)
    return wait, now + wait


def submit(review: dict) -> "tuple[int, dict, object]":
    """POST the review: the HTTP status, the response headers (lower-cased names) and the body."""
    done = subprocess.run(["gh", "api", "--include", "--method", "POST",
                           f"repos/{review['repo']}/pulls/{review['number']}/reviews",
                           "--input", str(review["folder"] / "payload.json")],
                          capture_output=True, text=True, stdin=subprocess.DEVNULL)
    head, _, text = done.stdout.replace("\r\n", "\n").partition("\n\n")
    lines = head.split("\n")
    try:
        status = int(lines[0].split()[1])
    except (IndexError, ValueError):
        raise GhError((done.stderr or done.stdout).strip() or "gh api gave no response")
    headers = {}
    for line in lines[1:]:
        name, sep, value = line.partition(":")
        if sep:
            headers[name.strip().lower()] = value.strip()
    try:
        body = json.loads(text) if text.strip() else {}
    except ValueError:
        body = text.strip()
    return status, headers, body


class Pace:
    """GitHub's secondary limits for creating content: 80 requests a minute and 500 an hour, one
    at a time, a second apart. A review counts 1 plus its inline comments, and this stays at half
    of each limit. Once GitHub has blocked a post, the posts that follow are `slow` seconds apart."""

    def __init__(self, per_minute: int, per_hour: int, minute: float, slow: float):
        self.per_minute, self.per_hour, self.minute, self.slow = per_minute, per_hour, minute, slow
        self.sent: list = []              # (monotonic time, units)
        self.blocked = False

    def wait(self, units: int, name: str) -> None:
        told, started = False, time.monotonic()
        while True:
            now = time.monotonic()
            gap = self.slow if self.blocked else self.minute / 60
            in_minute = sum(u for t, u in self.sent if now - t < self.minute)
            in_hour = sum(u for t, u in self.sent if now - t < self.minute * 60)
            fits = ((in_minute == 0 or in_minute + units <= self.per_minute)
                    and (in_hour == 0 or in_hour + units <= self.per_hour))
            if fits and (not self.sent or now - self.sent[-1][0] >= gap):
                return
            if not told and now - started > self.minute / 30:
                print(f"waiting before {name}, to stay under GitHub's limits for creating content", flush=True)
                told = True
            time.sleep(max(0.01, min(self.minute / 120, 1.0)))

    def sent_now(self, units: int) -> None:
        self.sent.append((time.monotonic(), units))


def record(review: dict, posted: dict, auto: bool = False) -> str:
    (review["folder"] / "posted.json").write_text(json.dumps(
        {"html_url": posted.get("html_url"), "id": posted.get("id"), "event": review["payload"].get("event"),
         "commit_id": review["head"], **({"auto": True} if auto else {})}, indent=2) + "\n")
    if evidence is not None:
        evidence.update_batches(review["folder"])
    return posted.get("html_url") or ""


def main(argv: "list | None" = None) -> int:
    parser = argparse.ArgumentParser(description="Post the chosen reviews, one at a time.")
    parser.add_argument("evidence", nargs="+", type=Path, help="evidence directories, in the order to post")
    parser.add_argument("--auto", action="store_true",
                        help="post a review without a yes only when it is fully verified at its head")
    parser.add_argument("--per-minute", type=int, default=40,
                        help="content a minute: each review counts 1 plus its inline comments (GitHub allows 80)")
    parser.add_argument("--per-hour", type=int, default=250, help="content an hour (GitHub allows 500)")
    parser.add_argument("--minute", type=float, default=60.0, help="seconds in the budget's minute (tests shorten it)")
    parser.add_argument("--backoff", type=float, default=60.0,
                        help="seconds to wait after a block that names no wait, doubling each time")
    parser.add_argument("--slow", type=float, default=45.0, help="seconds between posts once GitHub has blocked one")
    parser.add_argument("--tries", type=int, default=4, help="attempts per review before giving up")
    args = parser.parse_args(argv)
    try:
        reviews = [load(folder) for folder in args.evidence]
    except (OSError, ValueError, KeyError, TypeError) as err:
        print(f"post_reviews.py: {err}", file=sys.stderr)
        return 2
    try:
        viewer = gh_json("user")["login"]
    except (GhError, KeyError, ValueError, TypeError) as err:
        print(f"post_reviews.py: cannot tell who is posting: {err}", file=sys.stderr)
        return 2
    pace = Pace(args.per_minute, args.per_hour, args.minute, args.slow)
    missing, stopped, rights = 0, None, {}
    for review in reviews:
        if stopped:
            print(f"not posted: {review['name']}: not tried, {stopped}")
            missing += 1
            continue
        if args.auto:
            why = shortfalls(review, may_push(review["repo"], rights))
            if why:
                print(f"needs your yes: {review['name']}: {'; '.join(why)}")
                missing += 1
                continue
        try:
            on_github, stopped = post_one(review, viewer, pace, args)
        except (GhError, ValueError, KeyError, TypeError) as err:
            print(f"not posted: {review['name']}: gh failed: {err}")
            on_github, stopped = False, "since gh itself failed above: fix that, then run this again"
        if not on_github:
            missing += 1
    return 1 if missing else 0


def post_one(review: dict, viewer: str, pace: Pace, args) -> "tuple[bool, str | None]":
    """Post one review, or find it already posted: whether it is on GitHub, and why the run
    stops (None to go on)."""
    posted = already_posted(review, viewer)
    if posted:
        print(f"already posted: {review['name']}: {posted.get('html_url')}")
        return True, None
    now = gh_json(f"repos/{review['repo']}/pulls/{review['number']}")["head"]["sha"]
    if now != review["head"]:
        print(f"not posted: {review['name']}: the pull request moved to {now[:7]} since the review; "
              f"review the new head")
        return False, None
    units = 1 + len(review["payload"].get("comments") or [])
    blocks = 0
    while True:
        pace.wait(units, review["name"])
        status, headers, body = submit(review)
        pace.sent_now(units)                  # counted from when GitHub answered
        if 200 <= status < 300 and isinstance(body, dict):
            print(f"posted: {review['name']}: {record(review, body, args.auto)}")
            return True, None
        if not rate_limited(status, headers, body):
            print(f"not posted: {review['name']}: HTTP {status}: {message(body)}")
            return False, "since GitHub refused the review above: decide what to do about it, then run this again"
        blocks += 1
        if blocks >= args.tries:
            print(f"not posted: {review['name']}: GitHub still blocks it after {blocks} tries "
                  f"(HTTP {status}: {message(body)})")
            return False, "since GitHub is still blocking posts: run this again later"
        wait, lifts = delay(headers, args.backoff, blocks)
        if wait > args.backoff * 2 ** (args.tries - 1):
            at = time.strftime("%H:%M", time.localtime(lifts))
            print(f"not posted: {review['name']}: GitHub's rate limit lifts at {at} "
                  f"(HTTP {status}: {message(body)}); run this again then")
            return False, f"since GitHub's rate limit lifts at {at}"
        pace.blocked = True
        print(f"GitHub blocked {review['name']} (HTTP {status}: {message(body)}); waiting {wait:g} s, "
              f"then posting more slowly", flush=True)
        time.sleep(wait)
        posted = already_posted(review, viewer)
        if posted:                            # refused, yet kept
            print(f"posted: {review['name']}: {record(review, posted, args.auto)}")
            return True, None


if __name__ == "__main__":
    sys.exit(main())
