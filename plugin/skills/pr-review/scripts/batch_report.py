#!/usr/bin/env python3
"""The opening of a pr-review handover: is each pull request ready to merge, and what does each author
whose pull request is not ready have to change first.

  batch_report.py DIR [DIR ...]

Each DIR is one pull request's evidence directory: review.json (see review_payload.py) and, when the
checks ran, checks/checks.json (see run_checks.py). A directory without review.json is a review that
never finished; its error.txt, when there is one, says why. Each pull request gets one answer:

  changes needed   a blocking finding, a check broken or removed by the PR, or the verdict "request changes"
  not yet          open questions, checks that could not run, or a review that never finished
  ready to merge   the verdict "approve", nothing blocking, no check broken by the PR

Prints a Markdown table, the ones needing attention first, then one note per author whose pull request
is not ready, each ready to paste to them: the link, the blocking items first, then the rest. Exits 0,
or 2 when no directory is given.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ORDER = {"changes needed": 0, "not yet": 1, "ready to merge": 2}
RANK = {"blocking": 0, "should fix": 1, "question": 2, "nit": 3, "praise": 4}
BROKEN = {"broken by the PR", "removed by the PR"}


def load(folder: Path) -> dict:
    """One pull request's state, from its evidence directory."""
    review_file = folder / "review.json"
    if not review_file.is_file():
        error = folder / "error.txt"
        reason = error.read_text().strip() if error.is_file() else "no review.json was written"
        return {"folder": folder.name, "status": "not yet", "reason": f"could not review: {reason}",
                "pr": None, "findings": [], "not_verified": [], "broken": []}
    review = json.loads(review_file.read_text())
    checks_file = folder / "checks" / "checks.json"
    rows = json.loads(checks_file.read_text()) if checks_file.is_file() else []
    broken = [r["name"] for r in rows if r.get("verdict") in BROKEN]
    findings = sorted(review.get("findings") or [], key=lambda f: RANK.get(f.get("severity"), 9))
    blocking = [f for f in findings if f.get("severity") == "blocking"]
    if review.get("verdict") == "request changes" or blocking or broken:
        status, reason = "changes needed", ""
    elif review.get("verdict") == "approve":
        status, reason = "ready to merge", ""
    else:
        open_ = sum(1 for f in findings if f.get("severity") == "question")
        unverified = len(review.get("not_verified") or [])
        parts = ([f"{open_} open question{'s' if open_ != 1 else ''}"] if open_ else []) + \
                ([f"{unverified} thing{'s' if unverified != 1 else ''} not verified"] if unverified else [])
        status, reason = "not yet", ", ".join(parts) or "the review did not approve"
    return {"folder": folder.name, "status": status, "reason": reason, "pr": review.get("pr") or {},
            "findings": findings, "not_verified": review.get("not_verified") or [], "broken": broken}


def link(state: dict) -> str:
    pr = state["pr"]
    if not pr:
        return f"`{state['folder']}`"
    return f"[#{pr.get('number')} {pr.get('title', '')}]({pr.get('url', '')})".replace(" ]", "]")


def spot(finding: dict) -> str:
    path, line = finding.get("path"), finding.get("line")
    if not path:
        return ""
    return f" (`{path}:{line}`)" if line else f" (`{path}`)"


def report(states: list) -> str:
    states = sorted(states, key=lambda s: (ORDER[s["status"]], (s["pr"] or {}).get("number") or 0))
    counts = {k: sum(1 for s in states if s["status"] == k) for k in ORDER}
    lines = [f"{len(states)} pull request{'s' if len(states) != 1 else ''}: {counts['ready to merge']} ready to merge, "
             f"{counts['changes needed']} with changes needed, {counts['not yet']} not yet.", "",
             "| PR | Author | Head | Ready to merge? | Blocking | Checks broken by the PR |",
             "| --- | --- | --- | --- | --- | --- |"]
    for s in states:
        pr = s["pr"] or {}
        author = f"@{pr['author']}" if pr.get("author") else "—"
        head = f"`{str(pr['head'])[:7]}`" if pr.get("head") else "—"
        shown = f"**{s['status']}**" if s["status"] == "changes needed" else s["status"]
        blocking = sum(1 for f in s["findings"] if f.get("severity") == "blocking") if pr else "—"
        broken = ", ".join(f"`{b}`" for b in s["broken"]) or "—"
        lines.append(f"| {link(s)} | {author} | {head} | {shown} | {blocking} | {broken} |")
    not_ready = [s for s in states if s["status"] != "ready to merge"]
    authors: dict = {}
    for s in not_ready:
        authors.setdefault((s["pr"] or {}).get("author") or "", []).append(s)
    for author, mine in authors.items():
        lines += ["", f"### Note for @{author}" if author else "### Not reviewed"]
        for s in mine:
            lines.append("")
            if s["status"] == "changes needed":
                lines.append(f"{link(s)} needs changes before it can merge:")
                items = [f"check `{b}` is broken by the PR" for b in s["broken"]]
                items += [f"**{f['severity']}**: {f.get('title', '')}{spot(f)}" for f in s["findings"]
                          if f.get("severity") in ("blocking", "should fix", "question")]
                lines += [f"{i}. {item}" for i, item in enumerate(items, 1)]
            else:
                lines.append(f"{link(s)} is not ready yet ({s['reason']}):")
                lines += [f"- **{f['severity']}**: {f.get('title', '')}{spot(f)}" for f in s["findings"]
                          if f.get("severity") in ("blocking", "should fix", "question")]
                lines += [f"- not verified: {item}" for item in s["not_verified"]]
    return "\n".join(lines).rstrip() + "\n"


def main(argv: "list | None" = None) -> int:
    folders = [Path(a) for a in (argv if argv is not None else sys.argv[1:])]
    if not folders:
        print(__doc__, file=sys.stderr)
        return 2
    print(report([load(f) for f in folders]), end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
