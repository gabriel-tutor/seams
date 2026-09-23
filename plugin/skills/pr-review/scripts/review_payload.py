#!/usr/bin/env python3
"""Turn a pull request's review.json into the one review GitHub receives, and a preview to show first.

  review_payload.py --diff PR.diff --review review.json --event COMMENT|REQUEST_CHANGES|APPROVE
                    --viewer LOGIN --out payload.json [--checks checks.md] [--preview review.md]

PR.diff is `git diff <baseline> <candidate>`, the diff GitHub shows for the pull request. review.json:

  {"pr": {"repo", "number", "url", "title", "author", "head", "mergeable"},
   "verdict": "approve" | "request changes" | "comment",
   "summary": "...",
   "findings": [{"severity": "blocking" | "should fix" | "nit" | "question" | "praise",
                 "title", "body", "path", "line", "end_line", "side": "RIGHT" | "LEFT",
                 "suggestion", "evidence"}],
   "not_verified": ["what could not be checked, and why", ...]}

GitHub accepts an inline comment only on a line inside one of the diff's hunks, and rejects the whole
review (422) when one comment misses; so a finding becomes an inline comment only when its line (or its
whole range, within one hunk) is in the diff on its side, RIGHT for the candidate's lines, LEFT for
removed ones. Every other finding goes into the review's body under "Outside the diff". A suggestion
becomes a GitHub suggestion block on the RIGHT side, plain code on the LEFT (removed lines cannot take
one); an empty or blank suggestion is none, since an empty block would delete the lines it sits on. The author of a pull request can only COMMENT on it (GitHub refuses the other two events), and
APPROVE needs the verdict "approve", no blocking finding, no check broken or removed by the PR (read
from the checks.json beside --checks) and no merge conflict (pr.mergeable).

Writes payload.json ({commit_id, event, body, comments}), ready for
`gh api --method POST repos/<owner>/<repo>/pulls/<number>/reviews --input payload.json`.
Exits 0 when written, 1 when a rule refuses the event (nothing written), 2 on a usage error.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

SEVERITIES = ("blocking", "should fix", "nit", "question", "praise")
VERDICTS = {"approve": "Approve", "request changes": "Request changes", "comment": "Comment"}
EVENTS = ("COMMENT", "REQUEST_CHANGES", "APPROVE")
HUNK = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")
LIMIT = 60000          # GitHub caps a review or comment body at 65,536 characters


class Refused(Exception):
    """A rule of GitHub's or of the verdict's forbids this review; exit 1."""


class Usage(Exception):
    """The inputs are malformed; exit 2."""


ESCAPES = {"a": 7, "b": 8, "t": 9, "n": 10, "v": 11, "f": 12, "r": 13, '"': 34, "\\": 92}


def _unquote(path: str) -> str:
    """A path as git quotes it: C-style, with octal escapes for bytes (core.quotePath on) or raw
    UTF-8 characters (quotePath off), either way inside double quotes."""
    if not (len(path) >= 2 and path.startswith('"') and path.endswith('"')):
        return path
    out, i, text = bytearray(), 0, path[1:-1]
    while i < len(text):
        ch = text[i]
        if ch == "\\" and i + 1 < len(text):
            nxt = text[i + 1]
            if nxt in "01234567" and i + 3 < len(text) + 1 and all(c in "01234567" for c in text[i + 1:i + 4]):
                out.append(int(text[i + 1:i + 4], 8))
                i += 4
                continue
            if nxt in ESCAPES:
                out.append(ESCAPES[nxt])
                i += 2
                continue
        out += ch.encode("utf-8")
        i += 1
    return out.decode("utf-8", "replace")


def _strip_prefix(path: str) -> "str | None":
    path = _unquote(path.split("\t")[0].strip())
    if path == "/dev/null":
        return None
    return path[2:] if path[:2] in ("a/", "b/") else path


def parse_diff(text: str) -> dict:
    """Each file's hunks, as the sets of lines a comment may take on each side:
    {path: [{"RIGHT": {lines}, "LEFT": {lines}}, ...]}. Hunk lines are counted from the @@ header, so
    a removed line that happens to begin with "--" or "++" is read as a line, never as a header."""
    files: dict = {}
    old_path = new_path = None
    current = None                      # the hunk list of the file being read
    hunk = None
    old_left = new_left = 0
    old_no = new_no = 0
    for raw in text.split("\n"):          # not splitlines(): a form feed or U+2028 is part of its line
        raw = raw[:-1] if raw.endswith("\r") else raw
        if hunk is not None and (old_left > 0 or new_left > 0):
            if raw.startswith("\\"):    # "\ No newline at end of file"
                continue
            tag, _ = (raw[:1], raw[1:])
            if tag == "+":
                hunk["RIGHT"].add(new_no)
                new_no += 1
                new_left -= 1
            elif tag == "-":
                hunk["LEFT"].add(old_no)
                old_no += 1
                old_left -= 1
            else:                       # context, including a blank line whose space was stripped
                hunk["RIGHT"].add(new_no)
                hunk["LEFT"].add(old_no)
                new_no += 1
                old_no += 1
                new_left -= 1
                old_left -= 1
            continue
        hunk = None
        if raw.startswith("diff --git "):
            old_path = new_path = None
            current = None
        elif raw.startswith("--- "):
            old_path = _strip_prefix(raw[4:])
        elif raw.startswith("+++ "):
            new_path = _strip_prefix(raw[4:])
            path = new_path or old_path
            if path:
                current = files.setdefault(path, [])
        elif raw.startswith("@@ ") and current is not None:
            m = HUNK.match(raw)
            if not m:
                raise Usage(f"unreadable hunk header: {raw!r}")
            old_no, old_left = int(m.group(1)), int(m.group(2) if m.group(2) is not None else 1)
            new_no, new_left = int(m.group(3)), int(m.group(4) if m.group(4) is not None else 1)
            hunk = {"RIGHT": set(), "LEFT": set()}
            current.append(hunk)
    return files


def place(finding: dict, files: dict) -> "dict | None":
    """Where GitHub will take this finding inline, or None when it must go in the body."""
    path = finding.get("path") or None
    if path and path.startswith("./"):
        path = path[2:]
    line = finding.get("line")
    if not path or not isinstance(line, int) or path not in files:
        return None
    side = finding.get("side") or "RIGHT"
    end = finding.get("end_line") or line
    if end < line:
        line, end = end, line
    for hunk in files[path]:
        if all(n in hunk[side] for n in range(line, end + 1)):
            spot = {"path": path, "line": end, "side": side}
            if end != line:
                spot.update(start_line=line, start_side=side)
            return spot
    return None


def where(finding: dict) -> str:
    path, line, end = finding.get("path"), finding.get("line"), finding.get("end_line")
    if not path:
        return ""
    if not line:
        return f"`{path}`"
    return f"`{path}:{line}-{end}`" if end and end != line else f"`{path}:{line}`"


def suggestion(finding: dict) -> "str | None":
    """The finding's suggested replacement, or None. An empty or blank suggestion is none: on GitHub an
    empty suggestion block deletes the lines it is attached to when the author commits it, so a
    deletion is proposed in words, never by an empty block."""
    text = finding.get("suggestion")
    return text if isinstance(text, str) and text.strip() else None


def comment_body(finding: dict, side: str) -> str:
    parts = [f"**{finding['severity']}** · {finding.get('title') or ''}".rstrip(" ·")]
    if finding.get("body"):
        parts.append(finding["body"].strip())
    if finding.get("evidence"):
        parts.append("Evidence:\n\n" + "\n".join("> " + l for l in str(finding["evidence"]).strip().splitlines()))
    if suggestion(finding) is not None:
        fence = "```suggestion" if side == "RIGHT" else "```"
        parts.append(f"{fence}\n{suggestion(finding)}\n```")
    return _cap("\n\n".join(parts))


def _cap(text: str) -> str:
    return text if len(text) <= LIMIT else text[:LIMIT] + "\n\n…(cut to fit GitHub's limit; the full text is in the local draft)"


def body(review: dict, checks: str, outside: list) -> str:
    counts = {s: sum(1 for f in review["findings"] if f["severity"] == s) for s in SEVERITIES}
    head = str(review["pr"].get("head") or "")[:7]
    lines = [f"**Verdict: {VERDICTS[review['verdict']]}** · reviewed at `{head}`", ""]
    if review.get("summary"):
        lines += [review["summary"].strip(), ""]
    plural = {"nit": "nits", "question": "questions"}
    shown = [f"{counts[s]} {plural.get(s, s) if counts[s] != 1 else s}" for s in SEVERITIES if s != "praise"]
    lines += ["**Findings:** " + " · ".join(shown) + ". Inline on the diff unless listed under *Outside the diff*.", ""]
    if checks.strip():
        lines += ["### Checks: baseline against candidate", "", checks.strip(), ""]
    if outside:
        lines += ["### Outside the diff", ""]
        for f in outside:
            spot = where(f)
            lines.append(f"- **{f['severity']}** {spot + ' ' if spot else ''}{f.get('title') or ''}".rstrip())
            detail = []
            if f.get("body"):
                detail.append(f["body"].strip())
            if f.get("evidence"):
                detail.append("Evidence:\n\n" + "\n".join("> " + l for l in str(f["evidence"]).strip().split("\n")))
            if suggestion(f) is not None:              # no diff line to suggest on: plain code
                detail.append(f"```\n{suggestion(f)}\n```")
            for block in detail:
                lines += [""] + ["  " + l if l else "" for l in block.split("\n")]
            lines.append("")
    if review.get("not_verified"):
        lines += ["### Not verified", ""] + [f"- {item}" for item in review["not_verified"]] + [""]
    ran = ("Checks ran locally on the merge-base and on the head." if checks.strip()
           else "No checks were run on this machine: a static review reads the code only.")
    lines.append(f"<sub>{ran} Drafted with Claude Code (Seams `pr-review`) and posted by a person who "
                 "read it first.</sub>")
    return _cap("\n".join(lines))


def _line(value) -> bool:
    return value is None or (isinstance(value, int) and not isinstance(value, bool) and value > 0)


def validate(review: dict, event: str, viewer: str, broken: list) -> None:
    """Refuse malformed input (Usage) and an event GitHub or the review's own evidence forbids
    (Refused). `broken` names the checks the PR broke or removed."""
    if event not in EVENTS:
        raise Usage(f"--event is one of {', '.join(EVENTS)}, got {event!r}")
    if not isinstance(review, dict) or review.get("verdict") not in VERDICTS:
        raise Usage(f"verdict is one of {', '.join(VERDICTS)}, got {review.get('verdict') if isinstance(review, dict) else review!r}")
    pr = review.get("pr")
    if not isinstance(pr, dict) or not all(pr.get(k) for k in ("head", "author")):
        raise Usage("review.json lacks pr.head or pr.author")
    findings = review.get("findings")
    if not isinstance(findings, list) or not all(isinstance(f, dict) for f in findings):
        raise Usage("review.json's findings is a list of objects")
    for f in findings:
        if f.get("severity") not in SEVERITIES:
            raise Usage(f"a finding's severity is one of {', '.join(SEVERITIES)}, got {f.get('severity')!r}")
        if (f.get("side") or "RIGHT") not in ("RIGHT", "LEFT"):
            raise Usage(f"a finding's side is RIGHT or LEFT, got {f.get('side')!r}")
        if not (_line(f.get("line")) and _line(f.get("end_line"))):
            raise Usage(f"a finding's line and end_line are positive whole numbers, got {f.get('line')!r}, {f.get('end_line')!r}")
        for key in ("path", "title", "body", "suggestion"):
            if f.get(key) is not None and not isinstance(f[key], str):
                raise Usage(f"a finding's {key} is text, got {f[key]!r}")
    if event != "COMMENT" and viewer.casefold() == str(pr["author"]).casefold():
        raise Refused("GitHub does not let the author approve or request changes on their own pull request; "
                      "post it as COMMENT")
    if event == "APPROVE":
        blocking = [f for f in findings if f["severity"] == "blocking"]
        if blocking:
            raise Refused(f"APPROVE with {len(blocking)} blocking finding(s); the verdict is not approve")
        if broken:
            raise Refused(f"APPROVE with {', '.join(broken)} broken or removed by the PR")
        if str(pr.get("mergeable") or "").upper() == "CONFLICTING":
            raise Refused("APPROVE on a branch that conflicts with its base; the conflict comes first")
        if review["verdict"] != "approve":
            raise Refused(f"APPROVE needs the verdict approve, and this review's is {review['verdict']!r}")


def build(review: dict, diff: str, checks: str, event: str, viewer: str, broken: "list | None" = None) -> "tuple[dict, str]":
    validate(review, event, viewer, broken or [])
    files = parse_diff(diff)
    comments, outside = [], []
    for f in review["findings"]:
        spot = place(f, files)
        if spot is None:
            outside.append(f)
        else:
            comments.append({**spot, "body": comment_body(f, spot["side"])})
    payload = {"commit_id": review["pr"]["head"], "event": event, "body": body(review, checks, outside),
               "comments": comments}
    pr = review["pr"]
    preview = [f"# Draft review: {pr.get('repo', '')}#{pr.get('number', '')} at `{str(pr['head'])[:7]}`, as {event}", "",
               payload["body"], "", f"## Inline comments ({len(comments)})", ""]
    for c in comments:
        span = f"{c['start_line']}-{c['line']}" if "start_line" in c else str(c["line"])
        preview += [f"### `{c['path']}:{span}` ({c['side']})", "", c["body"], ""]
    return payload, "\n".join(preview)


def main(argv: "list | None" = None) -> int:
    parser = argparse.ArgumentParser(description="Build the GitHub review for a pull request from its review.json.")
    parser.add_argument("--diff", type=Path, required=True, help="git diff <baseline> <candidate>")
    parser.add_argument("--review", type=Path, required=True, help="the PR's review.json")
    parser.add_argument("--event", required=True, help="COMMENT, REQUEST_CHANGES or APPROVE")
    parser.add_argument("--viewer", required=True, help="the login that will post (gh api user --jq .login)")
    parser.add_argument("--out", type=Path, required=True, help="where payload.json goes")
    parser.add_argument("--checks", type=Path, help="run_checks.py's checks.md, carried in the review's body")
    parser.add_argument("--preview", type=Path, help="where the Markdown preview goes")
    args = parser.parse_args(argv)
    try:
        review = json.loads(args.review.read_text())
        checks, broken = "", []
        if args.checks and args.checks.is_file():
            checks = args.checks.read_text()
            rows_file = args.checks.parent / "checks.json"      # run_checks.py writes both side by side
            if rows_file.is_file():
                broken = [r["name"] for r in json.loads(rows_file.read_text())
                          if r.get("verdict") in ("broken by the PR", "removed by the PR")]
        diff = args.diff.read_bytes().decode("utf-8", "replace")
        payload, preview = build(review, diff, checks, args.event, args.viewer, broken)
    except Refused as err:
        print(f"review_payload.py: refused: {err}", file=sys.stderr)
        return 1
    except (Usage, ValueError, OSError, KeyError, TypeError, AttributeError) as err:
        print(f"review_payload.py: {err}", file=sys.stderr)
        return 2
    args.out.write_text(json.dumps(payload, indent=2) + "\n")
    if args.preview:
        args.preview.write_text(preview + "\n")
    print(f"{len(payload['comments'])} inline comment(s); body {len(payload['body'])} characters; event {args.event}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
