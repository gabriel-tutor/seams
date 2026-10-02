"""scripts/test.sh, the suite runner (.scratch/seams-revamp, ticket 01): every suite starts at once, each one's result
and time is reported, a failing suite fails the run and shows its output, and a run over its time budget fails, its
hanging suites stopped. Tested through its command line, with stand-in suites passed as --suite NAME=COMMAND."""
import ast
import os
import signal
import subprocess
import tempfile
import time
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
RUNNER = REPO / "scripts" / "test.sh"
TESTS = REPO / "scripts" / "tests"


def run(*args: str, env: "dict | None" = None, timeout: float = 60) -> "tuple[int, str]":
    """The runner as a person runs it: the caller's environment without a budget of its own (CI sets one), plus `env`."""
    base = {k: v for k, v in os.environ.items() if k != "SEAMS_TEST_BUDGET"}
    done = subprocess.run(["bash", str(RUNNER), *args], capture_output=True, text=True, timeout=timeout,
                          env=dict(base, **(env or {})))
    return done.returncode, done.stdout + done.stderr


def listed(*args: str) -> list:
    code, out = run("--list", *args)
    assert code == 0, out
    return [line.split()[0] for line in out.splitlines() if line.strip()]


def gone(pid: int, within: float = 5.0) -> bool:
    """Whether the process has ended (polled, bounded)."""
    deadline = time.monotonic() + within
    while time.monotonic() < deadline:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return True
        time.sleep(0.05)
    return False


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

    def pid_written(self, path: Path) -> int:
        for _ in range(200):
            if path.exists() and path.read_text().strip():
                return int(path.read_text())
            time.sleep(0.05)
        self.fail(f"no pid in {path}")

    # -- running and reporting

    def test_every_suite_starts_at_once(self):
        code, out = run("--suite", f"a={self.meet('a', 'b')}", "--suite", f"b={self.meet('b', 'a')}")
        self.assertEqual(code, 0, out)
        self.assertRegex(out, r"ok\s+a\b")
        self.assertRegex(out, r"ok\s+b\b")

    def test_jobs_caps_how_many_run_at_once(self):
        code, out = run("--jobs", "1", "--suite", f"a={self.meet('a', 'b', seconds=1)}",
                        "--suite", f"b={self.meet('b', 'a', seconds=1)}")
        self.assertEqual(code, 1, out)                                       # one at a time, so they never meet
        self.assertRegex(out, r"FAILED\s+a\b")
        self.assertRegex(out, r"ok\s+b\b")                    # b started after a ended, and found a's mark

    def test_a_failing_suite_fails_the_run_and_shows_what_it_said(self):
        code, out = run("--suite", "good=true", "--suite", "bad=echo 'expected 3, got 4'; exit 1")
        self.assertEqual(code, 1, out)
        self.assertRegex(out, r"FAILED\s+bad\b")
        self.assertRegex(out, r"ok\s+good\b")
        self.assertIn("expected 3, got 4", out)             # the failure is readable without opening a log

    def test_a_command_that_is_not_found_fails_the_run(self):
        code, out = run("--suite", "missing=/no/such/command")
        self.assertEqual(code, 1, out)
        self.assertRegex(out, r"FAILED\s+missing\b")

    def test_a_passing_suite_that_skipped_something_says_so(self):
        # A suite that could not check something on this machine (no claude CLI for the manifests) passes, and the
        # report still shows what was skipped, so nothing is skipped silently.
        code, out = run("--suite", "plugin=echo 'skipped: manifest validation (no claude CLI)'")
        self.assertEqual(code, 0, out)
        self.assertIn("skipped: manifest validation (no claude CLI)", out)

    def test_a_green_run_leaves_no_logs_and_a_failed_one_keeps_them(self):
        tmpdir = {"TMPDIR": str(self.tmp)}
        self.assertEqual(run("--suite", "quick=true", env=tmpdir)[0], 0)
        self.assertEqual(list(self.tmp.glob("seams-tests-*")), [])
        self.assertEqual(run("--suite", "bad=false", env=tmpdir)[0], 1)
        self.assertEqual(len(list(self.tmp.glob("seams-tests-*"))), 1)

    # -- the budget

    def test_a_run_over_its_budget_fails_and_says_by_how_much(self):
        code, out = run("--budget", "0", "--suite", "quick=true")
        self.assertEqual(code, 1, out)                       # the time alone fails the run
        self.assertRegex(out, r"over budget: \d+\.\d s > 0 s")

    def test_the_budget_comes_from_the_environment_when_not_given(self):
        # CI sets its own (its machines are slower than the user's Mac); the default is one minute.
        code, out = run("--suite", "quick=true", env={"SEAMS_TEST_BUDGET": "0"})
        self.assertEqual(code, 1, out)
        self.assertIn("over budget", out)
        code, out = run("--suite", "quick=true")
        self.assertEqual(code, 0, out)
        self.assertIn("budget 60 s", out)

    def test_a_suite_that_hangs_is_stopped_at_the_budget_and_fails_the_run(self):
        # A hang must not hang the run: on the Mac it would never end, and in CI it would run until the job's timeout.
        started = time.monotonic()
        code, out = run("--budget", "1", "--suite", f"hang=echo $$ > {self.tmp}/pid; exec sleep 30",
                        "--suite", "quick=true", timeout=30)
        self.assertEqual(code, 1, out)
        self.assertLess(time.monotonic() - started, 10, out)
        self.assertRegex(out, r"STOPPED\s+hang\b")
        self.assertIn("over budget", out)
        self.assertTrue(gone(int((self.tmp / "pid").read_text())), "the hanging suite is still running")

    def test_a_stopped_run_stops_its_suites(self):
        proc = subprocess.Popen(["bash", str(RUNNER), "--suite", f"long=echo $$ > {self.tmp}/pid; exec sleep 30"],
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        pid = self.pid_written(self.tmp / "pid")
        proc.send_signal(signal.SIGTERM)
        proc.wait(timeout=10)
        self.assertNotEqual(proc.returncode, 0)
        self.assertTrue(gone(pid), "a suite outlived the run that started it")

    # -- which suites, under which Python

    def test_every_test_file_is_a_suite_and_the_slowest_is_split_by_class(self):
        # Nothing added under scripts/tests can go unrun: every test_*.py and test_*.sh is a suite by its own name,
        # and test_pr_review.py is one suite per test class, read here from the file itself.
        names = listed()
        for path in sorted(TESTS.glob("test_*.py")) + sorted(TESTS.glob("test_*.sh")):
            if path.name != "test_pr_review.py":
                self.assertIn(path.stem[len("test_"):], names)
        tree = ast.parse((TESTS / "test_pr_review.py").read_text())
        cases = sorted(n.name for n in tree.body if isinstance(n, ast.ClassDef)
                       and any(isinstance(f, ast.FunctionDef) and f.name.startswith("test") for f in n.body))
        self.assertEqual(sorted(n.split(":", 1)[1] for n in names if n.startswith("pr_review:")), cases)

    def test_only_runs_the_named_suites(self):
        self.assertEqual(sorted(listed("--only", "gate,hooks")), ["gate", "hooks"])
        parts = listed("--only", "pr_review")                               # a file's name covers its parts
        self.assertTrue(parts and all(n.startswith("pr_review:") for n in parts), parts)
        code, out = run("--only", "nosuch", "--list")
        self.assertEqual(code, 2, out)

    @unittest.skipUnless(Path("/usr/bin/python3").exists(), "no system python3 to compare with")
    def test_python_sets_the_interpreter_every_suite_runs_under(self):
        # The hooks run under whichever python3 Claude Code finds; CI proves the macOS system one this way. A suite
        # that calls `python3` or "$PYTHON" gets the interpreter given, whatever else its folder holds.
        version = subprocess.run(["/usr/bin/python3", "-c", "import sys; print(tuple(sys.version_info[:2]))"],
                                 capture_output=True, text=True).stdout.strip()
        check = f'import sys; sys.exit(0 if str(tuple(sys.version_info[:2])) == \\"{version}\\" else 1)'
        code, out = run("--python", "/usr/bin/python3", "--suite", f'path=python3 -c "{check}"',
                        "--suite", f'var="$PYTHON" -c "{check}"')
        self.assertEqual(code, 0, out)

    def test_usage_errors_are_refused_before_anything_runs(self):
        for args, env in ((("--only", ","), {}), (("--suite", "../x=true"), {}),
                          (("--suite", "x=true"), {"SEAMS_TEST_BUDGET": "soon"}), (("--python", "/no/such/python3"), {})):
            with self.subTest(args=args, env=env):
                code, out = run(*args, env=env)
                self.assertEqual(code, 2, out)


if __name__ == "__main__":
    unittest.main()
