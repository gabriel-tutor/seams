#!/usr/bin/env python3
"""Run the repository's test suites at once and report each one (scripts/test.sh calls this).

  scripts/test.sh [--only NAME[,NAME...]] [--python PATH] [--jobs N] [--budget SECONDS] [--list]
  scripts/test.sh --suite NAME=COMMAND [--suite ...]       (stand-in suites, for this runner's own tests)

Every suite starts at once, up to --jobs at a time (half the cores by default, so the machine stays usable), each
in its own process with its output kept in a log. As each ends its result and time are printed; a failed suite's
last lines follow the summary. The run fails when any suite fails, and when the whole run takes longer than its
budget (--budget, else $SEAMS_TEST_BUDGET, else 60 seconds): slowness is caught when it creeps in.

The suites: the gate's unit tests, this runner's, pr-review's (split by test class, the slowest file), the hooks,
the session-start hook, the installer and the static checks. --only takes suite names, a file's name covering its
parts (`pr_review`); --python is the interpreter the Python suites and the hooks run under (CI proves the macOS
system Python with it). Exits 0 when every suite passed within the budget, 1 otherwise, 2 on a usage error.
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.dont_write_bytecode = True

REPO = Path(__file__).resolve().parent.parent
TESTS = REPO / "scripts" / "tests"
TAIL = 60                                       # lines of a failed suite's output shown in the report
TEST_CLASS = re.compile(r"^class (\w+)\([^)]*unittest\.TestCase\)", re.M)


def repo_suites(python: str) -> list:
    """(name, argv, extra environment) for each of the repository's suites, run under `python`."""
    on_path = {"PYTHONPATH": str(TESTS)}         # the test files import by module name from their own folder
    suites = [("gate", [python, "-m", "unittest", "test_gate"], on_path),
              ("runner", [python, "-m", "unittest", "test_runner"], on_path)]
    for name in TEST_CLASS.findall((TESTS / "test_pr_review.py").read_text()):
        suites.append((f"pr_review:{name}", [python, "-m", "unittest", f"test_pr_review.{name}"], on_path))
    folder = str(Path(python).parent) if os.sep in python else ""
    path_first = {"PATH": f"{folder}{os.pathsep}{os.environ.get('PATH', '')}"} if folder else {}
    suites += [("hooks", ["bash", str(TESTS / "test_hooks.sh")], {"PYTHON": python}),
               # session-start runs through its shebang, so the interpreter's folder has to come first on PATH
               ("plugin_hook", ["bash", str(TESTS / "test_plugin_hook.sh")], path_first),
               ("install", ["bash", str(TESTS / "test_install.sh")], {}),
               ("plugin", ["bash", str(TESTS / "test_plugin.sh")], {})]
    return suites


def chosen(suites: list, only: "str | None") -> list:
    if not only:
        return suites
    wanted = [w.strip() for w in only.split(",") if w.strip()]
    unknown = [w for w in wanted if not any(name == w or name.split(":")[0] == w for name, _, _ in suites)]
    if unknown:
        raise ValueError(f"no suite named {', '.join(unknown)}; --list shows them")
    return [s for s in suites if s[0] in wanted or s[0].split(":")[0] in wanted]


def main(argv: "list | None" = None) -> int:
    parser = argparse.ArgumentParser(description="Run the test suites at once.")
    parser.add_argument("--only", help="the suites to run, by name, comma-separated (a file's name covers its parts)")
    parser.add_argument("--python", default="python3", help="the interpreter the Python suites and the hooks run under")
    parser.add_argument("--jobs", type=int, default=max(2, (os.cpu_count() or 4) // 2),
                        help="suites running at once (default: half the cores)")
    parser.add_argument("--budget", type=float, default=float(os.environ.get("SEAMS_TEST_BUDGET") or 60),
                        help="seconds the whole run may take before it fails (default: $SEAMS_TEST_BUDGET, else 60)")
    parser.add_argument("--list", action="store_true", help="print the suites and their commands, run nothing")
    parser.add_argument("--suite", action="append", default=[], metavar="NAME=COMMAND",
                        help="run this suite instead of the repository's own (repeatable)")
    args = parser.parse_args(argv)
    try:
        if args.jobs < 1:
            raise ValueError("--jobs must be 1 or more")
        suites = [(name, ["bash", "-c", command], {}) for name, _, command in (s.partition("=") for s in args.suite)] \
            or chosen(repo_suites(args.python), args.only)
    except (ValueError, OSError) as err:
        print(f"test.sh: {err}", file=sys.stderr)
        return 2
    if args.list:
        for name, command, extra in suites:
            print(name, " ".join(f"{k}={v}" for k, v in extra.items()), " ".join(command))
        return 0

    logs = Path(tempfile.mkdtemp(prefix="seams-tests-"))
    started, waiting, running, failed, done = time.monotonic(), list(suites), [], [], 0
    while waiting or running:
        while waiting and len(running) < args.jobs:
            name, command, extra = waiting.pop(0)
            log = open(logs / f"{name.replace(':', '.')}.log", "w")
            try:
                proc = subprocess.Popen(command, cwd=REPO, stdout=log, stderr=subprocess.STDOUT,
                                        stdin=subprocess.DEVNULL, env=dict(os.environ, **extra))
            except OSError as err:                     # a suite that cannot start is a failure, never a skip
                log.write(f"could not start: {err}\n")
                log.close()
                print(f"{'FAILED':<7} {name} (could not start)", flush=True)
                failed.append(name)
                continue
            running.append((name, proc, log, time.monotonic()))
        for item in list(running):
            name, proc, log, began = item
            if proc.poll() is None:
                continue
            running.remove(item)
            log.close()
            done += 1
            print(f"{'ok' if proc.returncode == 0 else 'FAILED':<7} {name} ({time.monotonic() - began:.1f} s)", flush=True)
            if proc.returncode != 0:
                failed.append(name)
        time.sleep(0.05)
    for name in failed:
        log = logs / f"{name.replace(':', '.')}.log"
        lines = log.read_text(errors="replace").splitlines()
        print(f"\n== {name} failed; its last {min(len(lines), TAIL)} lines (the whole log: {log})")
        print("\n".join(lines[-TAIL:]))
    took = time.monotonic() - started
    print(f"\n{len(suites) - len(failed)} passed, {len(failed)} failed in {took:.1f} s (budget {args.budget:g} s)")
    if took > args.budget:
        print(f"over budget: {took:.1f} s > {args.budget:g} s")
    return 1 if failed or took > args.budget else 0


if __name__ == "__main__":
    sys.exit(main())
