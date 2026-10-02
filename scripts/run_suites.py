#!/usr/bin/env python3
"""Run the repository's test suites at once and report each one (scripts/test.sh calls this).

  scripts/test.sh [--only NAME[,NAME...]] [--python PATH] [--jobs N] [--budget SECONDS] [--list]
  scripts/test.sh --suite NAME=COMMAND [--suite ...]       (stand-in suites, for this runner's own tests)

Every file scripts/tests/test_*.py and test_*.sh is a suite, named for its file without `test_`; test_pr_review.py,
the slowest, is one suite per test class (`pr_review:EvidenceTest`). They start at once, up to --jobs at a time (half
the cores by default, so the machine stays usable), each in its own process group with its output kept in a log. As
each ends its result and time are printed, with any `skipped: ...` line it wrote, so nothing is skipped silently;
a failed suite's last lines follow the summary. The run fails when any suite fails, and when it takes longer than
its budget (--budget, else $SEAMS_TEST_BUDGET, else 60 seconds): at the budget the suites still running are stopped
and reported, so a hang cannot hang the run. A run that is stopped stops its suites. A green run leaves no logs;
a failed one keeps them and says where.

--only takes suite names, a file's name covering its parts (`pr_review`). --python is the interpreter every suite
runs under: the Python suites run it, and the shell suites find it first on PATH as `python3` and in $PYTHON (CI
proves the macOS system Python with it). Exits 0 when every suite passed within the budget, 1 otherwise, 2 on a
usage error, before anything runs.
"""
from __future__ import annotations

import argparse
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

sys.dont_write_bytecode = True

REPO = Path(__file__).resolve().parent.parent
TESTS = REPO / "scripts" / "tests"
SPLIT = "test_pr_review.py"                     # the slowest file, run one test class per suite
TAIL = 60                                       # lines of a failed suite's output shown in the report
NAME = re.compile(r"^[A-Za-z0-9][\w.:-]*$")


def test_classes(path: Path) -> list:
    """The test classes of a test file, as unittest finds them: every TestCase subclass it defines with a test."""
    sys.path.insert(0, str(path.parent))
    try:
        module = __import__(path.stem)
    finally:
        sys.path.pop(0)
    loader = unittest.TestLoader()
    return [name for name, value in vars(module).items()
            if isinstance(value, type) and issubclass(value, unittest.TestCase) and value.__module__ == path.stem
            and loader.getTestCaseNames(value)]


def repo_suites(python: str) -> list:
    """(name, argv) for every suite of the repository, the Python ones run under `python`."""
    suites = []
    for path in sorted(TESTS.glob("test_*.py")):
        name = path.stem[len("test_"):]
        if path.name == SPLIT:
            suites += [(f"{name}:{case}", [python, "-m", "unittest", f"{path.stem}.{case}"]) for case in test_classes(path)]
        else:
            suites.append((name, [python, "-m", "unittest", path.stem]))
    suites += [(path.stem[len("test_"):], ["bash", str(path)]) for path in sorted(TESTS.glob("test_*.sh"))]
    return suites


def chosen(suites: list, only: "str | None") -> list:
    if only is None:
        return suites
    wanted = [w.strip() for w in only.split(",") if w.strip()]
    if not wanted:
        raise ValueError("--only names no suite")
    covers = lambda name, w: name == w or name.split(":")[0] == w
    unknown = [w for w in wanted if not any(covers(name, w) for name, _ in suites)]
    if unknown:
        raise ValueError(f"no suite named {', '.join(unknown)}; --list shows them")
    return [s for s in suites if any(covers(s[0], w) for w in wanted)]


def interpreter(given: str) -> str:
    found = shutil.which(given)
    if not found:
        raise ValueError(f"--python {given}: no such interpreter")
    return os.path.abspath(found)


def environment(python: str, bin_dir: Path) -> dict:
    """What every suite runs with: `python` as $PYTHON and first on PATH as `python3`, and no bytecode written."""
    (bin_dir / "python3").symlink_to(python)
    return dict(os.environ, PYTHON=python, PATH=f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}",
                PYTHONPATH=str(TESTS), PYTHONDONTWRITEBYTECODE="1")


def log_of(logs: Path, name: str) -> Path:
    return logs / f"{name.replace(':', '.')}.log"


def stop(proc) -> None:
    """End a suite and whatever it started: its process group, politely and then for good."""
    for sig in (signal.SIGTERM, signal.SIGKILL):
        try:
            os.killpg(proc.pid, sig)
        except (ProcessLookupError, PermissionError):
            return
        try:
            proc.wait(timeout=2)
            return
        except subprocess.TimeoutExpired:
            continue


def parse(argv: "list | None"):
    parser = argparse.ArgumentParser(description="Run the test suites at once.")
    parser.add_argument("--only", help="the suites to run, by name, comma-separated (a file's name covers its parts)")
    parser.add_argument("--python", default="python3", help="the interpreter every suite runs under")
    parser.add_argument("--jobs", type=int, default=max(2, (os.cpu_count() or 4) // 2),
                        help="suites running at once (default: half the cores)")
    parser.add_argument("--budget", type=float, help="seconds the whole run may take (default: $SEAMS_TEST_BUDGET, else 60)")
    parser.add_argument("--list", action="store_true", help="print the suites and their commands, run nothing")
    parser.add_argument("--suite", action="append", default=[], metavar="NAME=COMMAND",
                        help="run this suite instead of the repository's own (repeatable)")
    args = parser.parse_args(argv)
    if args.jobs < 1:
        raise ValueError("--jobs must be 1 or more")
    if args.budget is None:
        try:
            args.budget = float(os.environ.get("SEAMS_TEST_BUDGET") or 60)
        except ValueError:
            raise ValueError(f"SEAMS_TEST_BUDGET is not a number of seconds: {os.environ['SEAMS_TEST_BUDGET']!r}")
    args.python = interpreter(args.python)
    if args.suite:
        suites = []
        for text in args.suite:
            name, sep, command = text.partition("=")
            if not sep or not NAME.match(name) or not command.strip():
                raise ValueError(f"a suite is NAME=COMMAND, its name of letters, digits, _ . : -, got {text!r}")
            suites.append((name, ["bash", "-c", command]))
        args.suites = suites
    else:
        args.suites = chosen(repo_suites(args.python), args.only)
    return args


def main(argv: "list | None" = None) -> int:
    try:
        args = parse(argv)
    except (ValueError, OSError, ImportError) as err:
        print(f"test.sh: {err}", file=sys.stderr)
        return 2
    if args.list:
        for name, command in args.suites:
            print(name, " ".join(command))
        return 0

    logs = Path(tempfile.mkdtemp(prefix="seams-tests-"))
    env = environment(args.python, logs)
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(143))   # a stopped run stops its suites (the finally below)
    started, waiting, running, failed, stopped = time.monotonic(), list(args.suites), [], [], []
    try:
        while waiting or running:
            while waiting and len(running) < args.jobs:
                name, command = waiting.pop(0)
                log = open(log_of(logs, name), "w")
                proc = subprocess.Popen(command, cwd=REPO, stdout=log, stderr=subprocess.STDOUT,
                                        stdin=subprocess.DEVNULL, env=env, start_new_session=True)
                running.append((name, proc, log, time.monotonic()))
            for item in list(running):
                name, proc, log, began = item
                if proc.poll() is None:
                    continue
                running.remove(item)
                log.close()
                ok = proc.returncode == 0
                print(f"{'ok' if ok else 'FAILED':<7} {name} ({time.monotonic() - began:.1f} s)", flush=True)
                for line in log_of(logs, name).read_text(errors="replace").splitlines():
                    if line.startswith("skipped: "):
                        print(f"        {line}")
                if not ok:
                    failed.append(name)
            if time.monotonic() - started > args.budget and (running or waiting):
                for name, proc, log, began in running:
                    stop(proc)
                    log.close()
                    print(f"{'STOPPED':<7} {name} (over budget after {time.monotonic() - began:.1f} s)", flush=True)
                    stopped.append(name)
                stopped += [name for name, _ in waiting]
                for name, _ in waiting:
                    print(f"{'STOPPED':<7} {name} (not started: over budget)", flush=True)
                running, waiting = [], []
                break
            time.sleep(0.05)
    finally:
        for name, proc, log, began in running:
            stop(proc)
            log.close()
    for name in failed:
        log = log_of(logs, name)
        lines = log.read_text(errors="replace").splitlines()
        print(f"\n== {name} failed; its last {min(len(lines), TAIL)} lines (the whole log: {log})")
        print("\n".join(lines[-TAIL:]))
    took = time.monotonic() - started
    passed = len(args.suites) - len(failed) - len(stopped)
    print(f"\n{passed} passed, {len(failed)} failed, {len(stopped)} stopped in {took:.1f} s (budget {args.budget:g} s)")
    if took > args.budget:
        print(f"over budget: {took:.1f} s > {args.budget:g} s")
    if failed or stopped or took > args.budget:
        return 1
    shutil.rmtree(logs, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
