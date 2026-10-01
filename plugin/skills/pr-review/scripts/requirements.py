#!/usr/bin/env python3
"""Turn a reference (what a pull request is meant to do) into numbered requirement lines, by script.

  requirements.py extract --out EVID/reference.json --source LABEL FILE [--source LABEL FILE ...] [--by LABEL LOGIN ...]

Each FILE is the text of one reference: a Seams ticket or spec, a GitHub issue's body, a document the user named.
The review reads it from where it must (a ticket in the pull request's own branch from the baseline, never the
head, so a pull request cannot edit its own acceptance) and puts the text in FILE; LABEL says what it is ("ticket
07 at the baseline", "issue #13"). A requirement line is:

  - a checkbox item (`- [ ]`, `- [x]`) of the reference: kind "criterion". A bullet nested under it belongs to
    that one line;
  - an item under a checkbox that begins "Must not happen", or the text after it on the same line: kind "must-not",
    one line each.

"How to verify" (its text on the same line, or the bullets right after it) is kept apart, in "verify", for the
review to run as checks when trust allows. Nothing after a `## Comments` heading is read: that is a ticket's
build history. A reference that has no checkbox (a prose spec) has no requirement lines; it cannot support an
approval, because nothing in it can be checked line by line.

Writes reference.json: {"sources": [{"label", "sha256"}], "requirements": [{"id", "kind", "text", "source"}],
"verify": [...]}. A source is named by its label and the hash of its text, never by a path: a posted review
must not leak a private file's location. `--by LABEL LOGIN` records who wrote a source (an issue's author) as "by":
the poster refuses an approval resting on a source its pull request's own author wrote. Ids are R1, R2, ... across all sources, in order. Prints the lines.
Exits 0 when written, 2 on a usage error or a source it cannot read, before anything is written.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True                 # the plugin folder is loaded in place: no __pycache__ in it

CHECKBOX = re.compile(r"^(\s*)[-*+]\s+\[[ xX]\]\s+(\S.*?)\s*$")
BULLET = re.compile(r"^(\s*)[-*+]\s+(\S.*?)\s*$")
VERIFY = re.compile(r"^\s*(?:\*\*|__)?how to verify:?(?:\*\*|__)?:?\s*(.*?)\s*$", re.I)
MUST_NOT = re.compile(r"^must not happen\b[:.]?\s*(.*)$", re.I)
HEADING = re.compile(r"^\s*#{1,6}\s+(.*?)\s*#*\s*$")


def indent(line: str) -> int:
    return len(line) - len(line.lstrip())


def parse(text: str, source: str) -> "tuple[list, list]":
    """The requirement lines of one reference (without ids) and its how-to-verify items."""
    lines, found, verify, i = text.splitlines(), [], [], 0
    while i < len(lines):
        line = lines[i]
        heading = HEADING.match(line)
        if heading and heading.group(1).strip().lower() == "comments":
            break
        how = VERIFY.match(line)
        box = CHECKBOX.match(line)
        if how:
            if how.group(1):
                verify.append(how.group(1))
            j = i + 1
            while j < len(lines) and not lines[j].strip():
                j += 1
            while j < len(lines) and BULLET.match(lines[j]):
                verify.append(BULLET.match(lines[j]).group(2))
                j += 1
            i = max(j, i + 1)
        elif box:
            head, nested, j = box.group(2), [], i + 1
            while j < len(lines):
                k = j
                while k < len(lines) and not lines[k].strip():
                    k += 1
                if k >= len(lines) or indent(lines[k]) <= indent(line):
                    break
                if BULLET.match(lines[k]):
                    nested.append(BULLET.match(lines[k]).group(2))
                j = k + 1
            must_not = MUST_NOT.match(head)
            if must_not:
                items = ([must_not.group(1)] if must_not.group(1) else []) + nested
                found += [{"kind": "must-not", "text": item.rstrip(".;").strip(), "source": source} for item in items]
            else:
                joiner = " " if head.endswith(":") else " — "
                found.append({"kind": "criterion", "source": source,
                              "text": head + (joiner + "; ".join(n.rstrip(".;") for n in nested) if nested else "")})
            i = j
        else:
            i += 1
    return found, verify


def main(argv: "list | None" = None) -> int:
    parser = argparse.ArgumentParser(description="Number a reference's requirement lines.")
    sub = parser.add_subparsers(dest="command", required=True)
    extract = sub.add_parser("extract", help="write reference.json from one or more references")
    extract.add_argument("--out", type=Path, required=True, help="where reference.json goes (the evidence directory)")
    extract.add_argument("--source", nargs=2, action="append", metavar=("LABEL", "FILE"), required=True,
                         help="a reference: what it is, and a file holding its text (repeatable)")
    extract.add_argument("--by", nargs=2, action="append", metavar=("LABEL", "LOGIN"), default=[],
                         help="who wrote a source, by its label (repeatable)")
    args = parser.parse_args(argv)
    given = {label for label, _ in args.source}
    for label, _ in args.by:
        if label not in given:
            print(f"requirements.py: --by names {label!r}, which is not a --source", file=sys.stderr)
            return 2
    writers = dict(args.by)
    sources, requirements, verify = [], [], []
    for label, name in args.source:
        try:
            text = Path(name).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as err:
            print(f"requirements.py: cannot read the reference {label!r}: {err}", file=sys.stderr)
            return 2
        lines, how = parse(text, label)
        sources.append({"label": label, "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
                        **({"by": writers[label]} if label in writers else {})})
        requirements += lines
        verify += how
    for number, line in enumerate(requirements, 1):
        line["id"] = f"R{number}"
    requirements = [{key: line[key] for key in ("id", "kind", "text", "source")} for line in requirements]
    args.out.write_text(json.dumps({"sources": sources, "requirements": requirements, "verify": verify}, indent=2) + "\n")
    for line in requirements:
        print(f"{line['id']} {'must not: ' if line['kind'] == 'must-not' else ''}{line['text']}")
    for item in verify:
        print(f"verify: {item}")
    if not requirements:
        print("no requirement lines: nothing in the reference can be checked line by line, so it cannot support an approval")
    return 0


if __name__ == "__main__":
    sys.exit(main())
