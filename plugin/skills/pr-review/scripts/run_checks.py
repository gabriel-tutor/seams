#!/usr/bin/env python3
"""Run a pull request's checks on its baseline and on its candidate, and say whose each failure is.

  run_checks.py --base DIR --head DIR --out DIR --check NAME=COMMAND [--check ...] [--timeout SECONDS]

Each check runs with `bash -c COMMAND` in the baseline tree, then in the candidate tree, with stdin
closed and CI=1 (unless already set), its output kept in <out>/<name>.<base|head>.log. When the two
disagree, the side that failed runs once more, so a flaky check is called flaky rather than blamed on
the pull request. Whatever a check leaves running when it ends is ended with it. The verdicts:

  ok                 passes on both
  broken by the PR   passes on the baseline, fails on the candidate twice (a timeout is a failure)
  fixed by the PR    fails on the baseline twice, passes on the candidate
  already broken     fails on both: not the pull request's doing
  flaky              the second run disagreed with the first
  new in the PR      absent from the baseline, passing on the candidate (failing there twice is
                     "broken by the PR")
  removed by the PR  present on the baseline, absent from the candidate
  could not run      absent from both, or timed out on both (raise --timeout, or run it by hand)

A check is absent from a tree when its command is not found or not executable (exit 127 or 126), or
when a package manager reports the script missing. Writes <out>/checks.json and <out>/checks.md, the
table a review carries (no local paths in it), and prints the table. Exits 0 when the comparison ran,
whatever the verdicts, and 2 on a usage error.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import signal
import subprocess
import sys
import time
from pathlib import Path

# How package managers and make say a script or target does not exist; the check is then absent
# from that tree rather than failing in it. make's own target missing is absent; a prerequisite
# missing ("..., needed by 'x'") is a failure like any other.
MISSING_SCRIPT = re.compile(r"Missing script:|ERR_PNPM_NO_SCRIPT|error Command \".*\" not found|"
                            r"Couldn't find a script named|error: Script not found|"
                            r"No rule to make target [`'][^'`]*'\.\s+Stop\.|don't know how to make \S+\. Stop")
NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]*$")
BLOCKING = {"broken by the PR", "removed by the PR"}


def run_side(command: str, tree: Path, log: Path, timeout: float) -> dict:
    """One run of one check in one tree: its status (pass, fail, timeout, absent), exit code,
    seconds, a short reason and the log's file name."""
    tree = tree.resolve()
    env = dict(os.environ, PWD=str(tree))
    env.setdefault("CI", "1")
    started = time.monotonic()
    with open(log, "w") as out:
        proc = subprocess.Popen(["bash", "-c", command], cwd=str(tree), stdin=subprocess.DEVNULL,
                                stdout=out, stderr=subprocess.STDOUT, env=env, start_new_session=True)
        try:
            code = proc.wait(timeout=timeout)
            timed_out = False
        except subprocess.TimeoutExpired:
            timed_out = True
        end_group(proc.pid)             # the check on a timeout, and whatever it left running either way
        if timed_out:
            proc.wait()
            return {"status": "timeout", "exit": None, "seconds": round(time.monotonic() - started),
                    "reason": f"timed out after {timeout:g} s", "log": log.name}
    seconds = round(time.monotonic() - started)
    if code == 0:
        return {"status": "pass", "exit": 0, "seconds": seconds, "reason": "", "log": log.name}
    if code in (126, 127):
        return {"status": "absent", "exit": code, "seconds": seconds,
                "reason": f"command not found (exit {code})", "log": log.name}
    if MISSING_SCRIPT.search(log.read_text(errors="replace")):
        return {"status": "absent", "exit": code, "seconds": seconds, "reason": "script not found", "log": log.name}
    return {"status": "fail", "exit": code, "seconds": seconds, "reason": f"exit {code}", "log": log.name}


def end_group(pgid: int) -> None:
    """End every process of a check's group: SIGTERM, a moment to exit cleanly, then SIGKILL for
    whatever ignored it. Runs after every check, so a server or watcher a check left behind never
    shares the machine with the next check; returns at once when nothing is left."""
    try:
        os.killpg(pgid, signal.SIGTERM)
    except (ProcessLookupError, PermissionError):
        return
    time.sleep(0.3)
    try:
        os.killpg(pgid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError):
        pass


def verdict(base: str, head: str) -> "tuple[str, str | None]":
    """The verdict for a pair of statuses, and the side to run again before trusting it (None when
    the pair needs no second run)."""
    passing = {"pass"}
    failing = {"fail", "timeout"}
    if base == "absent" and head == "absent":
        return "could not run", None
    if base == "timeout" and head == "timeout":
        return "could not run", None
    if base == "absent":
        return ("new in the PR", None) if head == "pass" else ("broken by the PR", "head")
    if head == "absent":
        return "removed by the PR", None
    if base in passing and head in passing:
        return "ok", None
    if base in passing and head in failing:
        return "broken by the PR", "head"
    if base in failing and head in passing:
        return "fixed by the PR", "base"
    return "already broken", None


def compare(name: str, command: str, base: Path, head: Path, out: Path, timeout: float) -> dict:
    """Both runs of one check, the second run when the two disagree, and the verdict."""
    result = {"name": name, "command": command,
              "base": run_side(command, base, out / f"{name}.base.log", timeout),
              "head": run_side(command, head, out / f"{name}.head.log", timeout),
              "rerun": None}
    first, again = verdict(result["base"]["status"], result["head"]["status"])
    if again:
        tree = base if again == "base" else head
        second = run_side(command, tree, out / f"{name}.{again}.rerun.log", timeout)
        result["rerun"] = {"side": again, **second}
        if second["status"] == "pass":
            first = "flaky"
    result["verdict"] = first
    return result


def cell(run: dict, rerun: "dict | None") -> str:
    """One side of one check, as the table shows it."""
    if run["status"] == "pass":
        text = f"pass ({run['seconds']} s)"
    elif run["status"] in ("absent", "timeout"):
        text = run["reason"]
    else:
        text = f"fail, {run['reason']} ({run['seconds']} s)"
    if rerun:
        text += "; again: " + ("pass" if rerun["status"] == "pass" else rerun["reason"] or rerun["status"])
    return text


def table(results: list) -> str:
    lines = ["| Check | Baseline | Candidate | Verdict |", "| --- | --- | --- | --- |"]
    for r in results:
        rerun = r["rerun"]
        base = cell(r["base"], rerun if rerun and rerun["side"] == "base" else None)
        head = cell(r["head"], rerun if rerun and rerun["side"] == "head" else None)
        shown = f"**{r['verdict']}**" if r["verdict"] in BLOCKING else r["verdict"]
        lines.append(f"| `{r['name']}` | {base} | {head} | {shown} |")
    return "\n".join(lines) + "\n"


def parse_check(text: str) -> "tuple[str, str]":
    name, sep, command = text.partition("=")
    if not sep or not NAME.match(name.strip()) or not command.strip():
        raise ValueError(f"a check is NAME=COMMAND with a name of letters, digits, . _ : -, got: {text!r}")
    return name.strip(), command.strip()


def main(argv: "list | None" = None) -> int:
    parser = argparse.ArgumentParser(description="Run checks on a baseline and a candidate tree; attribute each result.")
    parser.add_argument("--base", type=Path, required=True, help="the baseline tree (the merge-base checked out)")
    parser.add_argument("--head", type=Path, required=True, help="the candidate tree (the PR head checked out)")
    parser.add_argument("--out", type=Path, required=True, help="where the logs, checks.json and checks.md go")
    parser.add_argument("--check", action="append", default=[], help="NAME=COMMAND, in the order to run (repeatable)")
    parser.add_argument("--timeout", type=float, default=900, help="seconds per run of one check (default 900)")
    args = parser.parse_args(argv)
    try:
        checks = [parse_check(c) for c in args.check]
        if not checks:
            raise ValueError("no --check given")
        names = [name.casefold() for name, _ in checks]
        if len(set(names)) != len(names):
            raise ValueError("two checks share a name (case aside); each writes its own log files")
        for tree in (args.base, args.head):
            if not tree.is_dir():
                raise ValueError(f"not a directory: {tree}")
    except ValueError as err:
        print(f"run_checks.py: {err}", file=sys.stderr)
        return 2
    args.out.mkdir(parents=True, exist_ok=True)
    results = [compare(name, command, args.base, args.head, args.out, args.timeout) for name, command in checks]
    (args.out / "checks.json").write_text(json.dumps(results, indent=2) + "\n")
    shown = table(results)
    (args.out / "checks.md").write_text(shown)
    print(shown, end="")
    print(f"\nLogs: {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
