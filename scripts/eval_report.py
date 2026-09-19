#!/usr/bin/env python3
"""The docs' table for one or more `claude plugin eval --json` documents, as Markdown, so the
evidence document cannot say more than the records do.

  eval_report.py RESULT.json [...]

One row per case: the with-arm score, the without-arm score, Δ, how many with-arm runs passed the
`skill-fired` grader (the plugin-fired indicator, which a two-arm run leaves out of the score), the
runs per arm, and the runs that ended with an error (a timeout, the turn cap, a usage limit). When a case
appears in several documents the last one given wins, so a re-run of one case can replace it.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path


def rows(documents: "list[dict]") -> "list[dict]":
    """One row per case across the documents, later documents replacing earlier cases."""
    cases: dict = {}
    for doc in documents:
        for case in doc.get("cases") or []:
            arms = case.get("arms") or {}
            with_runs, without_runs = arms.get("with") or [], arms.get("without") or []
            cases[case["name"]] = {
                "case": case["name"],
                "with": case["aggregates"].get("score"),
                "without": (sum(r.get("score") or 0 for r in without_runs) / len(without_runs)) if without_runs else None,
                "delta": case["aggregates"].get("delta"),
                "runs": len(with_runs),
                "errors": sum(1 for r in with_runs + without_runs if r.get("error")),
                "fired": sum(1 for r in with_runs for g in r.get("graders") or [] if g.get("name") == "skill-fired" and g.get("passed")),
                "model": doc.get("model") or (doc.get("suite") or {}).get("model"),
            }
    return [cases[k] for k in sorted(cases)]


def _num(value) -> str:
    return "" if value is None else f"{value:.2f}"


def report(documents: "list[dict]") -> str:
    lines = ["| Case | With | Without | Δ | Expected skill fired | Runs per arm | Runs with an error |",
             "| --- | --- | --- | --- | --- | --- | --- |"]
    for r in rows(documents):
        delta = "" if r["delta"] is None else f"{r['delta']:+.2f}"
        lines.append(f"| `{r['case']}` | {_num(r['with'])} | {_num(r['without'])} | {delta} | {r['fired']} of {r['runs']} | {r['runs']} | {r['errors']} |")
    partial = [d for d in documents if d.get("partial")]
    if partial:
        lines += ["", "Partial documents: " + ", ".join(str(d.get("partialReason")) for d in partial) + "."]
    return "\n".join(lines)


def main(argv: "list[str] | None" = None) -> int:
    paths = (argv if argv is not None else sys.argv[1:])
    if not paths:
        print(__doc__, file=sys.stderr)
        return 2
    print(report([json.loads(Path(p).read_text()) for p in paths]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
