#!/usr/bin/env python3
"""Run a pull request's checks on its baseline and on its candidate, and say whose each failure is.

  run_checks.py --base DIR --head DIR --out DIR --check NAME=COMMAND [--check ...] [--timeout SECONDS]
                [--merge] [--slots N] [--slot-dir DIR]
  run_checks.py --base DIR --head DIR --out DIR --recheck NAME [--recheck ...]

Each check runs with `bash -c COMMAND`, in the newest bash on PATH or in the usual install places
(macOS ships 3.2; CI's is 4 or newer), in the baseline tree, then in the candidate tree, with stdin
closed and CI=1 (unless already set), its output kept in <out>/<name>.<base|head>.log. When the two
disagree, the side that failed runs once more, so a flaky check is called flaky rather than blamed on
the pull request. Whatever a check leaves running when it ends is ended with it.

Both trees must be as their commits have them: a file git does not have (a probe left behind) is a
usage error, before anything runs. The run waits for one of the machine's check slots (--slots, half
its cores by default, shared through --slot-dir), so reviews started together take turns. --merge
keeps the checks already in checks.json and adds or replaces these; --recheck runs a check broken by
the PR once more on the candidate, alone after a batch, and calls it flaky when it passes. The verdicts:

  ok                 passes on both
  broken by the PR   passes on the baseline, fails on the candidate twice (a timeout is a failure)
  fixed by the PR    fails on the baseline twice, passes on the candidate
  already broken     fails on both: not the pull request's doing
  flaky              the second run disagreed with the first
  new in the PR      absent from the baseline, passing on the candidate (failing there twice is
                     "broken by the PR")
  removed by the PR  present on the baseline, absent from the candidate
  could not run      absent from both, or timed out on both (raise --timeout, or run it by hand), or
                     the local bash lacked what the command needs (globstar, mapfile, ...) on either
                     side: that run was not CI's, whatever its exit code

A check is absent from a tree when its command is not found or not executable (exit 127 or 126), or
when a package manager or test runner reports the script or test file missing. Writes
<out>/checks.json and <out>/checks.md, the table a review carries (no local paths in it; it names the
bash version), and prints the table. Exits 0 when the comparison ran, whatever the verdicts, and 2 on
a usage error.
"""
from __future__ import annotations

import argparse
import fcntl
import json
import os
import re
import signal
import subprocess
import sys
import time
from pathlib import Path

# How package managers, make and test runners say a script, target or test file does not exist;
# the check is then absent from that tree rather than failing in it, so a check aimed at a test
# file the pull request adds reads "new in the PR". make's own target missing is absent; a
# prerequisite missing ("..., needed by 'x'") is a failure like any other.
MISSING_SCRIPT = re.compile(r"Missing script:|ERR_PNPM_NO_SCRIPT|error Command \".*\" not found|"
                            r"Couldn't find a script named|error: Script not found|"
                            r"No rule to make target [`'][^'`]*'\.\s+Stop\.|don't know how to make \S+\. Stop|"
                            r"Could not find '[^']+'|ERROR: file or directory not found:|"
                            r"No tests found, exiting with code 1|No test files found, exiting with code 1|"
                            r"Error: No test files found")
NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]*$")
BLOCKING = {"broken by the PR", "removed by the PR"}
BASH_VERSION = re.compile(r"version (\d+)\.(\d+)(?:\.(\d+))?")
# What a bash older than 4 prints when a command needs 4 or newer, and then often carries on from:
# `shopt -s globstar` fails and `**` walks one directory, so a suite silently runs part of itself.
OLD_BASH = re.compile(r"shopt: (\w+): invalid shell option name|(?:declare|local|typeset): (-[nA]): invalid option"
                      r"|\b(mapfile|readarray): command not found|wait: (-n): invalid option|: (bad substitution)")
KNOWN_BASHES = ("/opt/homebrew/bin/bash", "/usr/local/bin/bash", "/bin/bash", "/usr/bin/bash")


def find_bash() -> dict:
    """The newest bash on PATH or in the usual install places, as {"path", "version"}. CI's bash is
    4 or newer; macOS ships 3.2, which has no globstar, associative arrays or mapfile."""
    best, best_key, seen = None, None, set()
    folders = os.environ.get("PATH", "").split(os.pathsep)
    for path in [os.path.join(f, "bash") for f in folders if f] + list(KNOWN_BASHES):
        real = os.path.realpath(path)
        if real in seen or not (os.path.isfile(path) and os.access(path, os.X_OK)):
            continue
        seen.add(real)
        try:
            text = subprocess.run([path, "--version"], capture_output=True, text=True, timeout=5,
                                  stdin=subprocess.DEVNULL).stdout
        except (OSError, subprocess.SubprocessError):
            continue
        found = BASH_VERSION.search(text)
        if not found:
            continue
        key = tuple(int(part or 0) for part in found.groups())
        if best_key is None or key > best_key:
            best, best_key = {"path": path, "version": ".".join(g for g in found.groups() if g)}, key
    return best or {"path": "bash", "version": "unknown"}


def run_side(command: str, tree: Path, log: Path, timeout: float, shell: dict) -> dict:
    """One run of one check in one tree, with the chosen bash (its directory first on PATH, so
    `#!/usr/bin/env bash` finds it too): its status (pass, fail, timeout, absent, or unsupported
    when the log shows the shell lacking what the command needs), exit code, seconds, a short
    reason and the log's file name."""
    tree = tree.resolve()
    env = dict(os.environ, PWD=str(tree))
    if os.path.isabs(shell["path"]):
        env["PATH"] = os.path.dirname(shell["path"]) + os.pathsep + env.get("PATH", "")
    env.setdefault("CI", "1")
    started = time.monotonic()
    with open(log, "w") as out:
        proc = subprocess.Popen([shell["path"], "-c", command], cwd=str(tree), stdin=subprocess.DEVNULL,
                                stdout=out, stderr=subprocess.STDOUT, env=env, start_new_session=True)
        try:
            code = proc.wait(timeout=timeout)
            timed_out = False
        except subprocess.TimeoutExpired:
            timed_out = True
        end_group(proc.pid)             # the check on a timeout, and whatever it left running either way
        if timed_out:
            proc.wait()
    seconds = round(time.monotonic() - started)
    old = OLD_BASH.search(log.read_text(errors="replace"))
    if old:
        feature = next(g for g in old.groups() if g)
        return {"status": "unsupported", "exit": None if timed_out else code, "seconds": seconds,
                "reason": f"needs bash 4 or newer ({feature}); ran with bash {shell['version']}", "log": log.name}
    if timed_out:
        return {"status": "timeout", "exit": None, "seconds": seconds,
                "reason": f"timed out after {timeout:g} s", "log": log.name}
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
    if "unsupported" in (base, head):          # one side did not run as CI runs it: nothing to compare
        return "could not run", None
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


def compare(name: str, command: str, base: Path, head: Path, out: Path, timeout: float, shell: dict) -> dict:
    """Both runs of one check, the second run when the two disagree, and the verdict."""
    result = {"name": name, "command": command, "shell": shell,
              "base": run_side(command, base, out / f"{name}.base.log", timeout, shell),
              "head": run_side(command, head, out / f"{name}.head.log", timeout, shell),
              "rerun": None}
    first, again = verdict(result["base"]["status"], result["head"]["status"])
    if again:
        tree = base if again == "base" else head
        second = run_side(command, tree, out / f"{name}.{again}.rerun.log", timeout, shell)
        result["rerun"] = {"side": again, **second}
        if second["status"] == "pass":
            first = "flaky"
    result["verdict"] = first
    return result


def cell(run: dict, rerun: "dict | None") -> str:
    """One side of one check, as the table shows it."""
    if run["status"] == "pass":
        text = f"pass ({run['seconds']} s)"
    elif run["status"] in ("absent", "timeout", "unsupported"):
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
        if r.get("alone"):
            head += "; alone: " + ("pass" if r["alone"]["status"] == "pass" else r["alone"]["reason"] or r["alone"]["status"])
        shown = f"**{r['verdict']}**" if r["verdict"] in BLOCKING else r["verdict"]
        lines.append(f"| `{r['name']}` | {base} | {head} | {shown} |")
    shells = sorted({r["shell"]["version"] for r in results if r.get("shell")})
    if shells:
        lines += ["", "Ran with bash " + ", ".join(shells) + "."]
    return "\n".join(lines) + "\n"


def stray_files(tree: Path) -> list:
    """What a git work tree has that its commit does not: modified, deleted or untracked files
    (ignored ones aside). A check must see the tree as committed; a probe left in it would be
    counted. A tree outside git has nothing to report."""
    inside = subprocess.run(["git", "-C", str(tree), "rev-parse", "--is-inside-work-tree"],
                            capture_output=True, text=True, stdin=subprocess.DEVNULL)
    if inside.returncode != 0 or inside.stdout.strip() != "true":
        return []
    status = subprocess.run(["git", "-C", str(tree), "status", "--porcelain", "--untracked-files=all"],
                            capture_output=True, text=True, stdin=subprocess.DEVNULL)
    return [line[3:] for line in status.stdout.splitlines() if line.strip()]


def parse_check(text: str) -> "tuple[str, str]":
    name, sep, command = text.partition("=")
    if not sep or not NAME.match(name.strip()) or not command.strip():
        raise ValueError(f"a check is NAME=COMMAND with a name of letters, digits, . _ : -, got: {text!r}")
    return name.strip(), command.strip()


def default_slots() -> int:
    return max(1, (os.cpu_count() or 2) // 2)


def take_slot(folder: Path, slots: int):
    """Hold one of the machine's check slots until this process ends: an exclusive lock on one of
    `slots` files, waited for when all are taken. Every reviewer of a batch starts at once; their
    installs and suites take turns. A review that dies frees its slot, since the lock dies with it.
    A slot folder this user cannot write is no reason to stop: the checks run without one."""
    try:
        folder.mkdir(parents=True, exist_ok=True)
    except OSError as err:
        print(f"run_checks.py: running without a check slot ({err})", file=sys.stderr)
        return None
    said = False
    while True:
        for i in range(slots):
            try:
                handle = open(folder / f"slot-{i}.lock", "a")
            except OSError as err:
                print(f"run_checks.py: running without a check slot ({err})", file=sys.stderr)
                return None
            try:
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
                return handle
            except OSError:
                handle.close()
        if not said:
            print(f"Waiting for one of {slots} check slots ...", flush=True)
            said = True
        time.sleep(1)


def broken_check(earlier: list, name: str) -> dict:
    for result in earlier:
        if result["name"].casefold() == name.casefold():
            if result["verdict"] != "broken by the PR":
                raise ValueError(f"{name} is {result['verdict']}: only a check broken by the PR runs again alone")
            return result
    raise ValueError(f"no check named {name} in checks.json")


def alone(result: dict, head: Path, out: Path, timeout: float, shell: dict) -> dict:
    """A check broken by the PR, run once more on the candidate with nothing else running (after a
    batch): passing now, the failures were the machine's load, and the verdict is flaky."""
    again = dict(result, alone=run_side(result["command"], head, out / f"{result['name']}.head.alone.log",
                                         timeout, shell))
    if again["alone"]["status"] == "pass":
        again["verdict"] = "flaky"
    return again


def earlier_results(out: Path) -> list:
    path = out / "checks.json"
    return json.loads(path.read_text()) if path.is_file() else []


def merged(earlier: list, new: list) -> list:
    """The earlier checks with each new one in its namesake's place, or at the end."""
    by_name = {r["name"].casefold(): r for r in new}
    kept = [by_name.pop(r["name"].casefold(), r) for r in earlier]
    return kept + [r for r in new if r["name"].casefold() in by_name]


def write_results(out: Path, results: list) -> None:
    """checks.json, checks.md (the table a review carries), and the table on stdout."""
    (out / "checks.json").write_text(json.dumps(results, indent=2) + "\n")
    shown = table(results)
    (out / "checks.md").write_text(shown)
    print(shown, end="")
    print(f"\nLogs: {out}")


def main(argv: "list | None" = None) -> int:
    parser = argparse.ArgumentParser(description="Run checks on a baseline and a candidate tree; attribute each result.")
    parser.add_argument("--base", type=Path, required=True, help="the baseline tree (the merge-base checked out)")
    parser.add_argument("--head", type=Path, required=True, help="the candidate tree (the PR head checked out)")
    parser.add_argument("--out", type=Path, required=True, help="where the logs, checks.json and checks.md go")
    parser.add_argument("--check", action="append", default=[], help="NAME=COMMAND, in the order to run (repeatable)")
    parser.add_argument("--timeout", type=float, default=900, help="seconds per run of one check (default 900)")
    parser.add_argument("--merge", action="store_true",
                        help="keep the checks already in OUT/checks.json; these replace a namesake or join the end")
    parser.add_argument("--recheck", action="append", default=[], metavar="NAME",
                        help="run a check broken by the PR again, alone, on the candidate (repeatable)")
    parser.add_argument("--slots", type=int, default=default_slots(),
                        help="checks the machine runs at once, across every review (default: half its cores)")
    parser.add_argument("--slot-dir", type=Path,
                        default=Path(os.environ.get("TMPDIR") or "/tmp") / "seams-pr-review" / "slots",
                        help="where the slots are kept; reviews that share it take turns")
    args = parser.parse_args(argv)
    try:
        if args.slots < 1:
            raise ValueError("--slots must be 1 or more")
        checks = [parse_check(c) for c in args.check]
        if checks and args.recheck:
            raise ValueError("--check and --recheck do not mix: a recheck runs a check already in checks.json")
        if not checks and not args.recheck:
            raise ValueError("no --check given")
        rechecks = [broken_check(earlier_results(args.out), name) for name in args.recheck]
        names = [name.casefold() for name, _ in checks]
        if len(set(names)) != len(names):
            raise ValueError("two checks share a name (case aside); each writes its own log files")
        for tree in (args.base, args.head):
            if not tree.is_dir():
                raise ValueError(f"not a directory: {tree}")
        dirty = []
        for tree in (args.base, args.head):
            stray = stray_files(tree)
            if stray:
                shown = ", ".join(stray[:10]) + (f" and {len(stray) - 10} more" if len(stray) > 10 else "")
                dirty.append(f"{tree} has files its commit does not have: {shown}")
        if dirty:
            raise ValueError("; ".join(dirty) + ". Remove them (a probe belongs in the evidence directory) "
                             "so every check sees the tree as committed")
    except ValueError as err:
        print(f"run_checks.py: {err}", file=sys.stderr)
        return 2
    args.out.mkdir(parents=True, exist_ok=True)
    slot = take_slot(args.slot_dir, args.slots)      # held until this process ends
    shell = find_bash()
    if rechecks:
        results = merged(earlier_results(args.out), [alone(r, args.head, args.out, args.timeout, shell) for r in rechecks])
    else:
        results = [compare(name, command, args.base, args.head, args.out, args.timeout, shell)
                   for name, command in checks]
        if args.merge:
            results = merged(earlier_results(args.out), results)
    write_results(args.out, results)
    if slot is not None:
        slot.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
