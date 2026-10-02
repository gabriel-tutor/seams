"""scripts/test.sh, the suite runner (.scratch/seams-revamp, ticket 01): every suite starts at once, each one's result
and time is reported, a failing suite fails the run and shows its output, and a run over its time budget fails.
Tested through its command line, with stand-in suites passed as --suite NAME=COMMAND."""
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
RUNNER = REPO / "scripts" / "test.sh"


def run(*args: str, env: "dict | None" = None, timeout: float = 60) -> "tuple[int, str]":
    done = subprocess.run(["bash", str(RUNNER), *args], capture_output=True, text=True, timeout=timeout,
                          env=dict(os.environ, **(env or {})))
    return done.returncode, done.stdout + done.stderr


class SuiteRunnerTest(unittest.TestCase):

    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.tmp = Path(self.tmp_dir.name)

    def tearDown(self):
        self.tmp_dir.cleanup()

    def meet(self, me: str, other: str, seconds: int = 10) -> str:
        """A suite that passes only when the other one is running at the same time: each marks itself and waits,
        bounded, for the other's mark."""
        return (f'touch "{self.tmp}/{me}"; for i in $(seq {seconds * 10}); do '
                f'[ -e "{self.tmp}/{other}" ] && exit 0; sleep 0.1; done; exit 1')

    def test_every_suite_starts_at_once(self):
        code, out = run("--suite", f"a={self.meet('a', 'b')}", "--suite", f"b={self.meet('b', 'a')}")
        self.assertEqual(code, 0, out)
        self.assertRegex(out, r"ok\s+a\b")
        self.assertRegex(out, r"ok\s+b\b")

    def test_a_failing_suite_fails_the_run_and_shows_what_it_said(self):
        code, out = run("--suite", "good=true", "--suite", "bad=echo 'expected 3, got 4'; exit 1")
        self.assertEqual(code, 1, out)
        self.assertRegex(out, r"FAILED\s+bad\b")
        self.assertRegex(out, r"ok\s+good\b")
        self.assertIn("expected 3, got 4", out)             # the failure is readable without opening a log

    def test_a_suite_that_cannot_start_is_a_failure_not_a_skip(self):
        code, out = run("--suite", "missing=/no/such/command")
        self.assertEqual(code, 1, out)
        self.assertRegex(out, r"FAILED\s+missing\b")


    def test_a_run_over_its_budget_fails_and_says_by_how_much(self):
        code, out = run("--budget", "0.3", "--suite", "slow=sleep 0.6")
        self.assertEqual(code, 1, out)
        self.assertRegex(out, r"ok\s+slow\b")                # every suite passed: the time alone fails the run
        self.assertRegex(out, r"over budget: \d+\.\d s > 0\.3 s")

    def test_the_budget_comes_from_the_environment_when_not_given(self):
        # CI sets its own (its machines are slower than the user's Mac); the default is one minute.
        code, out = run("--suite", "slow=sleep 0.6", env={"SEAMS_TEST_BUDGET": "0.3"})
        self.assertEqual(code, 1, out)
        self.assertIn("over budget", out)
        code, out = run("--suite", "quick=true")
        self.assertEqual(code, 0, out)
        self.assertIn("budget 60 s", out)


    def test_the_repositorys_own_suites_are_the_default_and_the_eval_harness_is_not_one(self):
        code, out = run("--list")
        self.assertEqual(code, 0, out)
        names = [line.split()[0] for line in out.splitlines() if line.strip()]
        for name in ("gate", "runner", "hooks", "plugin_hook", "install", "plugin"):
            self.assertIn(name, names)
        self.assertTrue(any(n.startswith("pr_review:") for n in names), names)   # the slowest file, split by class
        for gone in ("behavior_test", "prepare_run"):
            self.assertFalse(any(gone in line for line in out.splitlines()), out)

    def test_only_runs_the_named_suites(self):
        code, out = run("--only", "gate,hooks", "--list")
        self.assertEqual(code, 0, out)
        self.assertEqual(sorted(line.split()[0] for line in out.splitlines() if line.strip()), ["gate", "hooks"])
        code, out = run("--only", "pr_review", "--list")                    # a file's name covers its parts
        self.assertTrue(out.strip() and all(line.startswith("pr_review:") for line in out.splitlines() if line.strip()), out)
        code, out = run("--only", "nosuch", "--list")
        self.assertEqual(code, 2, out)

    def test_python_sets_the_interpreter_every_python_suite_and_hook_runs_under(self):
        # The hooks run under whichever python3 Claude Code finds; CI proves the macOS system one this way.
        code, out = run("--python", "/opt/py39/bin/python3", "--only", "gate,hooks,plugin_hook", "--list")
        self.assertEqual(code, 0, out)
        for line in out.splitlines():
            self.assertIn("/opt/py39/bin", line)

    def test_jobs_caps_how_many_run_at_once(self):
        code, out = run("--jobs", "1", "--suite", f"a={self.meet('a', 'b', seconds=1)}",
                        "--suite", f"b={self.meet('b', 'a', seconds=1)}")
        self.assertEqual(code, 1, out)                                       # one at a time, so they never meet


if __name__ == "__main__":
    unittest.main()
