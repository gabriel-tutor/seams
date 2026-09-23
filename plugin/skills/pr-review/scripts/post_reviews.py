#!/usr/bin/env python3
"""Post the reviews a person chose, one at a time, paced under GitHub's limits, and say where each landed.

  post_reviews.py [--per-minute N] [--per-hour N] [--backoff SECONDS] [--slow SECONDS] [--tries N] EVID [EVID ...]

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
Any other refusal, or a block that does not lift, ends the run: the reviews after it are not tried,
so the person can decide, and running it again finds what is already posted.

Each review posted is recorded in EVID/posted.json and its link printed. Exits 0 when every review
is on GitHub, 1 when any is not (each says why), and 2 on a usage error, before anything is posted.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path


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
    return {"folder": folder, "repo": repo, "number": number, "head": head, "payload": payload,
            "name": f"{repo}#{number} at {head[:7]} as {payload.get('event')}"}


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


def delay(headers: dict, backoff: float, blocks: int) -> float:
    """What GitHub asks: retry-after's seconds, or until the primary limit resets; otherwise a
    backoff that doubles with each block of this review."""
    try:
        return max(0.0, float(headers["retry-after"]))
    except (KeyError, ValueError):
        pass
    if headers.get("x-ratelimit-remaining") == "0":
        try:
            return max(0.0, float(headers["x-ratelimit-reset"]) - time.time()) + 1
        except (KeyError, ValueError):
            pass
    return backoff * 2 ** (blocks - 1)


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
        told = False
        while True:
            now = time.monotonic()
            gap = self.slow if self.blocked else self.minute / 60
            in_minute = sum(u for t, u in self.sent if now - t < self.minute)
            in_hour = sum(u for t, u in self.sent if now - t < self.minute * 60)
            fits = ((in_minute == 0 or in_minute + units <= self.per_minute)
                    and (in_hour == 0 or in_hour + units <= self.per_hour))
            if fits and (not self.sent or now - self.sent[-1][0] >= gap):
                return
            if not told and self.minute >= 60:
                print(f"waiting before {name}, to stay under GitHub's limits for creating content", flush=True)
                told = True
            time.sleep(max(0.01, min(self.minute / 120, 1.0)))

    def sent_now(self, units: int) -> None:
        self.sent.append((time.monotonic(), units))


def record(review: dict, posted: dict) -> str:
    (review["folder"] / "posted.json").write_text(json.dumps(
        {"html_url": posted.get("html_url"), "id": posted.get("id"), "event": review["payload"].get("event"),
         "commit_id": review["head"]}, indent=2) + "\n")
    return posted.get("html_url") or ""


def main(argv: "list | None" = None) -> int:
    parser = argparse.ArgumentParser(description="Post the chosen reviews, one at a time.")
    parser.add_argument("evidence", nargs="+", type=Path, help="evidence directories, in the order to post")
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
    except (GhError, KeyError, ValueError) as err:
        print(f"post_reviews.py: cannot tell who is posting: {err}", file=sys.stderr)
        return 2
    pace = Pace(args.per_minute, args.per_hour, args.minute, args.slow)
    missing, stopped = 0, None
    for review in reviews:
        if stopped:
            print(f"not posted: {review['name']}: not tried, {stopped}")
            missing += 1
            continue
        posted = already_posted(review, viewer)
        if posted:
            print(f"already posted: {review['name']}: {posted.get('html_url')}")
            continue
        now = gh_json(f"repos/{review['repo']}/pulls/{review['number']}")["head"]["sha"]
        if now != review["head"]:
            print(f"not posted: {review['name']}: the pull request moved to {now[:7]} since the review; "
                  f"review the new head")
            missing += 1
            continue
        units = 1 + len(review["payload"].get("comments") or [])
        blocks = 0
        while True:
            pace.wait(units, review["name"])
            status, headers, body = submit(review)
            pace.sent_now(units)              # counted from when GitHub answered
            if 200 <= status < 300 and isinstance(body, dict):
                print(f"posted: {review['name']}: {record(review, body)}")
                break
            if not rate_limited(status, headers, body):
                print(f"not posted: {review['name']}: HTTP {status}: {message(body)}")
                missing += 1
                stopped = "since GitHub refused the review above: decide what to do about it, then run this again"
                break
            blocks += 1
            if blocks >= args.tries:
                print(f"not posted: {review['name']}: GitHub still blocks it after {blocks} tries "
                      f"(HTTP {status}: {message(body)})")
                missing += 1
                stopped = "since GitHub is still blocking posts: run this again later"
                break
            pace.blocked = True
            wait = delay(headers, args.backoff, blocks)
            print(f"GitHub blocked {review['name']} (HTTP {status}: {message(body)}); waiting {wait:g} s, "
                  f"then posting more slowly", flush=True)
            time.sleep(wait)
            posted = already_posted(review, viewer)
            if posted:                    # refused, yet kept
                print(f"posted: {review['name']}: {record(review, posted)}")
                break
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())
