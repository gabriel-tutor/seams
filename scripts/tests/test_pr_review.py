"""The pr-review skill's five scripts, through their command lines: evidence.py (each pull request's
evidence directory pinned, what an earlier run finished at the same head and baseline kept, and a batch's
progress file), run_checks.py (the same checks on a pull request's baseline and candidate, each result
attributed), review_payload.py (the review GitHub receives: findings anchored inside the diff, the rest in
the review's body, only an event GitHub and the verdict allow), batch_report.py (ready to merge, per pull
request, and a note per author) and post_reviews.py (the chosen reviews posted one at a time, paced, never
twice)."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
SCRIPTS = REPO / "plugin" / "skills" / "pr-review" / "scripts"
RUN_CHECKS = SCRIPTS / "run_checks.py"
REVIEW_PAYLOAD = SCRIPTS / "review_payload.py"
BATCH_REPORT = SCRIPTS / "batch_report.py"
POST_REVIEWS = SCRIPTS / "post_reviews.py"
EVIDENCE = SCRIPTS / "evidence.py"


def run_checks(base: Path, head: Path, out: Path, *checks: str, timeout: float = 30, extra: tuple = (),
               env: "dict | None" = None) -> "tuple[int, dict, str]":
    """run_checks.py on two trees; the exit status, checks.json by check name, and checks.md."""
    args = [sys.executable, str(RUN_CHECKS), "--base", str(base), "--head", str(head), "--out", str(out),
            "--timeout", str(timeout), "--slot-dir", str(out.parent / "slots"), *extra]
    for check in checks:
        args += ["--check", check]
    done = subprocess.run(args, capture_output=True, text=True, env=env)
    try:
        data = json.loads((out / "checks.json").read_text()) if (out / "checks.json").is_file() else []
    except ValueError:                        # a test that corrupts it on purpose
        data = []
    table = (out / "checks.md").read_text() if (out / "checks.md").is_file() else ""
    return done.returncode, {c["name"]: c for c in data}, table + done.stderr


def gone(pid_file: Path, within: float = 3.0) -> bool:
    """Whether the process whose pid the file holds has ended (polled for a moment)."""
    pid = int(pid_file.read_text().strip())
    deadline = time.monotonic() + within
    while time.monotonic() < deadline:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return True
        except PermissionError:
            return False
        time.sleep(0.1)
    return False


class RunChecksTest(unittest.TestCase):
    """Every check runs on the baseline and on the candidate; its verdict says whose a failure is."""

    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.tmp = Path(self.tmp_dir.name)
        self.base, self.head, self.out = self.tmp / "base", self.tmp / "head", self.tmp / "out"
        self.base.mkdir()
        self.head.mkdir()

    def tearDown(self):
        self.tmp_dir.cleanup()

    def both(self, name: str, text: str = "") -> None:
        (self.base / name).write_text(text)
        (self.head / name).write_text(text)

    def fake_bash(self, folder: str, version: str) -> Path:
        """A `bash` that reports `version` and runs the system's bash for everything else."""
        path = self.tmp / folder / "bash"
        path.parent.mkdir()
        path.write_text('#!/bin/sh\nif [ "$1" = "--version" ]; then\n'
                        f'  echo "GNU bash, version {version}(1)-release (fake)"; exit 0\nfi\nexec /bin/bash "$@"\n')
        path.chmod(0o755)
        return path

    def test_checks_run_in_the_newest_bash_found_and_the_table_names_its_version(self):
        # macOS ships bash 3.2, where CI's `shopt -s globstar` fails and `**` walks one level: a
        # 1,000-file suite ran 799 files and still reported pass or fail as if it were whole.
        # The script also finds this machine's own bashes (its PATH and the usual install places),
        # so the newest fake reports a version no real bash has: a Homebrew 5.3 once outranked 5.2.37.
        old, new = self.fake_bash("old", "3.2.57"), self.fake_bash("new", "99.0.0")
        env = dict(os.environ, PATH=f"{old.parent}:{new.parent}:{os.environ['PATH']}")
        code, checks, table = run_checks(self.base, self.head, self.out, "shell=bash --version", env=env)
        self.assertEqual(code, 0, table)
        self.assertEqual(checks["shell"]["shell"]["version"], "99.0.0")
        self.assertEqual(checks["shell"]["shell"]["path"], str(new))
        self.assertIn("version 99.0.0", (self.out / "shell.head.log").read_text())   # its directory leads PATH
        self.assertIn("bash 99.0.0", table)
        self.assertNotIn(str(self.tmp), table)                                          # no local paths

    def test_a_run_the_local_bash_could_not_make_as_ci_does_could_not_run(self):
        # What bash 3.2 prints and then carries on from: the run is not CI's, whatever its exit code.
        globstar = "echo 'bash: line 1: shopt: globstar: invalid shell option name' >&2; echo 799 files"
        (self.base / "OLD_SHELL").write_text("")
        one_side = "if test -f OLD_SHELL; then echo 'bash: mapfile: command not found' >&2; fi; true"
        old = self.fake_bash("old", "3.2.57")                 # the same on every machine: macOS's bash
        code, checks, table = run_checks(self.base, self.head, self.out, f"tests={globstar}", f"lint={one_side}",
                                         extra=("--bash", str(old)))
        self.assertEqual(code, 0, table)
        for name in ("tests", "lint"):
            with self.subTest(check=name):
                self.assertEqual(checks[name]["verdict"], "could not run")
                self.assertIsNone(checks[name]["rerun"])
        self.assertIn("bash 4", checks["tests"]["head"]["reason"])
        self.assertIn("globstar", checks["tests"]["head"]["reason"])
        self.assertEqual(checks["lint"]["head"]["status"], "pass")
        self.assertIn("could not run", table)

    def test_an_error_that_only_looks_like_an_old_bash_is_still_the_prs(self):
        # "globstr" is no bash option: a typo the pull request made. And under bash 5, a bad
        # substitution is the command's own error.
        new = self.fake_bash("new", "5.2.37")
        env = dict(os.environ, PATH=f"{new.parent}:{os.environ['PATH']}")
        (self.base / "OK").write_text("")
        typo = "test -f OK || { echo 'bash: line 1: shopt: globstr: invalid shell option name' >&2; exit 1; }"
        subst = "test -f OK || { echo 'bash: ${x!}: bad substitution' >&2; exit 1; }"
        code, checks, table = run_checks(self.base, self.head, self.out, f"typo={typo}", f"subst={subst}", env=env)
        self.assertEqual(code, 0, table)
        self.assertEqual(checks["typo"]["verdict"], "broken by the PR")
        self.assertEqual(checks["subst"]["verdict"], "broken by the PR")

    def test_a_test_file_the_baseline_does_not_have_is_absent_there_so_the_check_is_new(self):
        # A check aimed at the pull request's own test file used to "fail" on the baseline, which
        # read as "fixed by the PR" until a reviewer wrapped it by hand.
        (self.head / "new.test.js").write_text("")
        (self.head / "test_new.py").write_text("")
        node = "test -f new.test.js || { echo \"Could not find '$PWD/new.test.js'\" >&2; exit 1; }"
        pytest = "test -f test_new.py || { echo 'ERROR: file or directory not found: test_new.py' >&2; exit 4; }"
        code, checks, table = run_checks(self.base, self.head, self.out, f"node={node}", f"pytest={pytest}")
        self.assertEqual(code, 0, table)
        for name in ("node", "pytest"):
            with self.subTest(check=name):
                self.assertEqual(checks[name]["base"]["status"], "absent")
                self.assertEqual(checks[name]["verdict"], "new in the PR")

    def commit_trees(self) -> None:
        """Make both trees git work trees at a commit, as a review's worktrees are."""
        for tree in (self.base, self.head):
            (tree / "a.txt").write_text("a\n")
            for step in (["init", "-q"], ["add", "a.txt"],
                         ["-c", "user.email=t@example.com", "-c", "user.name=t", "commit", "-qm", "x"]):
                subprocess.run(["git", "-C", str(tree), *step], check=True, capture_output=True)

    def test_a_tree_with_files_git_does_not_have_is_refused_before_any_check_runs(self):
        # Probe tests left in tests/ were counted by a later check: 985 files against 983 committed.
        self.commit_trees()
        (self.head / "tests").mkdir()
        (self.head / "tests" / "zz-review-probe.test.js").write_text("probe")
        (self.base / "a.txt").write_text("changed\n")
        code, checks, text = run_checks(self.base, self.head, self.out, "ok=true")
        self.assertEqual(code, 2, text)
        self.assertEqual(checks, {})
        self.assertIn("tests/zz-review-probe.test.js", text)
        self.assertIn("a.txt", text)
        (self.head / "tests" / "zz-review-probe.test.js").unlink()
        subprocess.run(["git", "-C", str(self.base), "checkout", "-q", "a.txt"], check=True)
        code, checks, text = run_checks(self.base, self.head, self.out, "ok=true")
        self.assertEqual(code, 0, text)

    def test_what_a_check_itself_leaves_in_a_tree_does_not_block_a_later_run(self):
        # A report or build cache git does not ignore must not stop the recheck or a check added
        # later; a probe left behind still does.
        self.commit_trees()
        code, _, text = run_checks(self.base, self.head, self.out, "tests=echo ok > report.xml")
        self.assertEqual(code, 0, text)
        code, checks, text = run_checks(self.base, self.head, self.out, "audit=true", extra=("--merge",))
        self.assertEqual(code, 0, text)
        self.assertEqual(list(checks), ["tests", "audit"])
        (self.head / "zz-probe.test.js").write_text("probe")
        code, _, text = run_checks(self.base, self.head, self.out, "audit=true", extra=("--merge",))
        self.assertEqual(code, 2, text)
        self.assertIn("zz-probe.test.js", text)
        self.assertNotIn("report.xml", text)

    def test_an_unreadable_checks_json_is_a_usage_error_not_a_crash(self):
        self.out.mkdir()
        (self.out / "checks.json").write_text("{not json")
        for extra, checks in ((("--merge",), ("audit=true",)), (("--recheck", "tests"), ())):
            with self.subTest(extra=extra):
                code, _, text = run_checks(self.base, self.head, self.out, *checks, extra=extra)
                self.assertEqual(code, 2, text)
                self.assertNotIn("Traceback", text)

    def test_a_check_found_later_joins_the_table_and_the_others_stay(self):
        # A check found after the reviews finished was added by a script that edited 14 reviews by
        # hand; it now runs through here, beside the checks already run.
        (self.base / "AUDIT_OK").write_text("")
        run_checks(self.base, self.head, self.out, "tests=true", "lint=true")
        code, checks, table = run_checks(self.base, self.head, self.out, "docs-audit=test -f AUDIT_OK",
                                         extra=("--merge",))
        self.assertEqual(code, 0, table)
        self.assertEqual(list(checks), ["tests", "lint", "docs-audit"])
        self.assertEqual(checks["docs-audit"]["verdict"], "broken by the PR")
        self.assertIn("| `tests` |", table)
        self.assertIn("| `docs-audit` |", table)
        code, checks, table = run_checks(self.base, self.head, self.out, "lint=false", extra=("--merge",))
        self.assertEqual(list(checks), ["tests", "lint", "docs-audit"])       # replaced in place
        self.assertEqual(checks["lint"]["verdict"], "already broken")

    def test_a_check_broken_by_the_pr_under_load_is_flaky_when_it_passes_alone(self):
        # Thirteen reviews at once ran a 14-core machine at a load of 53, and two verdicts were
        # relabelled by hand. After a batch, a broken check runs again alone before it can block.
        load = self.tmp / "LOAD"
        load.write_text("")
        (self.base / "BASE").write_text("")
        suite = f"test -f BASE || ! test -f {load}"     # the candidate fails only while LOAD exists
        run_checks(self.base, self.head, self.out, f"suite={suite}", "stays=test -f BASE")
        load.unlink()
        code, checks, table = run_checks(self.base, self.head, self.out,
                                         extra=("--recheck", "suite", "--recheck", "stays"))
        self.assertEqual(code, 0, table)
        self.assertEqual(checks["suite"]["verdict"], "flaky")
        self.assertEqual(checks["suite"]["alone"]["status"], "pass")
        self.assertEqual(checks["stays"]["verdict"], "broken by the PR")
        self.assertIn("alone: pass", table)
        self.assertTrue((self.out / "suite.head.alone.log").is_file())
        code, _, text = run_checks(self.base, self.head, self.out, extra=("--recheck", "suite"))
        self.assertEqual(code, 2, text)                  # only a check broken by the PR runs again alone

    def two_reviews_at_once(self, slots: int) -> "tuple[float, float]":
        """Two run_checks.py started together, sharing a slot directory: when the second review's
        first check started, and when the first review's last check ended."""
        stamp = "python3 -c 'import time; print(\"at\", time.time())'"
        check = f"slow={stamp}; sleep 1; {stamp}"
        runs = []
        for n in (1, 2):
            args = [sys.executable, str(RUN_CHECKS), "--base", str(self.base), "--head", str(self.head),
                    "--out", str(self.tmp / f"out{slots}-{n}"), "--slots", str(slots),
                    "--slot-dir", str(self.tmp / f"slots{slots}"), "--check", check]
            runs.append(subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT))
            time.sleep(0.4)
        for run in runs:
            output = run.communicate(timeout=30)[0]
            self.assertEqual(run.returncode, 0, output)

        def times(n: int, side: str) -> list:
            text = (self.tmp / f"out{slots}-{n}" / f"slow.{side}.log").read_text()
            return [float(line.split()[1]) for line in text.splitlines() if line.startswith("at ")]
        return times(2, "base")[0], times(1, "head")[-1]

    def test_the_machine_runs_only_as_many_checks_at_once_as_it_has_slots(self):
        # Fifteen reviewers can read and review at once; their installs and suites take turns.
        second_starts, first_ends = self.two_reviews_at_once(slots=1)
        self.assertGreaterEqual(second_starts, first_ends)
        second_starts, first_ends = self.two_reviews_at_once(slots=2)
        self.assertLess(second_starts, first_ends)

    def test_each_combination_of_pass_and_fail_gets_its_verdict(self):
        self.both("PASS_OK")
        (self.base / "PASS_BROKEN").write_text("")          # passes on the baseline only: the PR broke it
        (self.head / "PASS_FIXED").write_text("")           # passes on the candidate only: the PR fixed it
        code, checks, table = run_checks(self.base, self.head, self.out,
                                         "ok=test -f PASS_OK", "broken=test -f PASS_BROKEN",
                                         "fixed=test -f PASS_FIXED", "already=test -f PASS_NEITHER")
        self.assertEqual(code, 0, table)
        self.assertEqual(checks["ok"]["verdict"], "ok")
        self.assertEqual(checks["broken"]["verdict"], "broken by the PR")
        self.assertEqual(checks["fixed"]["verdict"], "fixed by the PR")
        self.assertEqual(checks["already"]["verdict"], "already broken")
        self.assertIn("| `broken` |", table)
        self.assertIn("**broken by the PR**", table)

    def test_a_result_that_flips_is_run_again_before_it_is_blamed_on_the_pr(self):
        (self.head / "FLAKY").write_text("")
        # Passes on the baseline; fails on its first run in the candidate and passes on its second:
        # flaky, not the PR's failure.
        flaky = 'test -f FLAKY || exit 0; test -f .ran || { touch .ran; exit 1; }'
        code, checks, table = run_checks(self.base, self.head, self.out, f"flaky={flaky}")
        self.assertEqual(checks["flaky"]["verdict"], "flaky", table)
        self.assertEqual(checks["flaky"]["rerun"]["side"], "head")
        self.assertTrue((self.out / "flaky.head.rerun.log").is_file())

    def test_a_new_check_that_fails_is_run_again_before_it_is_blamed_on_the_pr(self):
        (self.head / "new.sh").write_text('test -f .ran || { touch .ran; exit 1; }\n')
        code, checks, table = run_checks(self.base, self.head, self.out, "new=bash new.sh")
        self.assertEqual(checks["new"]["verdict"], "flaky", table)
        self.assertEqual(checks["new"]["rerun"]["side"], "head")

    def test_a_check_only_one_tree_has_is_new_or_removed_and_one_neither_has_could_not_run(self):
        (self.head / "only-head.sh").write_text("exit 0\n")
        (self.base / "only-base.sh").write_text("exit 0\n")
        code, checks, table = run_checks(self.base, self.head, self.out,
                                         "new=bash only-head.sh", "removed=bash only-base.sh",
                                         "missing=no-such-command-seams-test")
        self.assertEqual(checks["new"]["verdict"], "new in the PR", table)
        self.assertEqual(checks["removed"]["verdict"], "removed by the PR", table)
        self.assertEqual(checks["missing"]["verdict"], "could not run", table)
        self.assertIn("not found", checks["missing"]["base"]["reason"])

    def test_a_package_script_missing_from_one_tree_is_absent_there_not_failing(self):
        # npm, pnpm and yarn exit 1 for a missing script; that is a check the tree does not have.
        (self.head / "e2e.sh").write_text("exit 0\n")
        missing = 'test -f e2e.sh && bash e2e.sh || { echo "npm error Missing script: \\"test:e2e\\"" >&2; exit 1; }'
        code, checks, table = run_checks(self.base, self.head, self.out, f"e2e={missing}")
        self.assertEqual(checks["e2e"]["verdict"], "new in the PR", table)

    def test_make_missing_a_target_is_absent_but_missing_a_prerequisite_is_a_failure(self):
        (self.head / "HAS_TARGET").write_text("")
        target = ('test -f HAS_TARGET && exit 0; echo "make: *** No rule to make target \'e2e\'.  Stop." >&2; exit 2')
        (self.base / "PREREQ_OK").write_text("")
        prereq = ('test -f PREREQ_OK && exit 0; '
                  'echo "make: *** No rule to make target \'foo.c\', needed by \'foo.o\'.  Stop." >&2; exit 2')
        code, checks, table = run_checks(self.base, self.head, self.out, f"target={target}", f"prereq={prereq}")
        self.assertEqual(checks["target"]["verdict"], "new in the PR", table)
        self.assertEqual(checks["prereq"]["verdict"], "broken by the PR", table)

    def test_timeouts_are_attributed_and_never_counted_as_passing(self):
        self.both("QUICK")
        (self.head / "SLOW").write_text("")
        code, checks, table = run_checks(self.base, self.head, self.out,
                                         "hangs-on-head=test -f SLOW && sleep 20 || true",
                                         "hangs-on-both=sleep 20", timeout=1)
        self.assertEqual(checks["hangs-on-head"]["verdict"], "broken by the PR", table)
        self.assertIn("timed out", checks["hangs-on-head"]["head"]["reason"])
        self.assertEqual(checks["hangs-on-both"]["verdict"], "could not run", table)
        self.assertIn("timed out", checks["hangs-on-both"]["base"]["reason"])

    def test_nothing_a_check_started_outlives_it(self):
        # A background process left by a passing check, and one that ignores SIGTERM, both end when
        # the check does; a later check or the next review would otherwise share the machine with them.
        code, checks, table = run_checks(self.base, self.head, self.out,
                                         'left=sleep 60 & echo $! > left.pid; exit 0',
                                         'stubborn=(trap "" TERM; sleep 60) & echo $! > stubborn.pid; exit 0')
        self.assertEqual(checks["left"]["verdict"], "ok", table)
        for tree in (self.base, self.head):
            self.assertTrue(gone(tree / "left.pid"), f"a background process outlived its check in {tree.name}")
            self.assertTrue(gone(tree / "stubborn.pid"), f"a TERM-ignoring process outlived its check in {tree.name}")

    def test_each_side_runs_in_its_own_tree_non_interactively_with_its_output_kept(self):
        self.both("marker")
        no_ci = {name: value for name, value in os.environ.items() if name != "CI"}  # GitHub Actions sets CI=true
        code, checks, table = run_checks(self.base, self.head, self.out,
                                         'env=pwd; echo "CI=$CI"; test -t 0 && exit 1; exit 0', env=no_ci)
        self.assertEqual(checks["env"]["verdict"], "ok", table)
        base_log = (self.out / "env.base.log").read_text()
        self.assertIn(str(self.base.resolve()), base_log)
        self.assertIn("CI=1", base_log)
        self.assertIn(str(self.head.resolve()), (self.out / "env.head.log").read_text())

    def test_a_ci_value_already_set_is_kept(self):
        # Run inside CI, the checks see CI's own value, as they would there.
        self.both("marker")
        code, checks, table = run_checks(self.base, self.head, self.out, 'env=echo "CI=$CI"',
                                         env=dict(os.environ, CI="true"))
        self.assertEqual(checks["env"]["verdict"], "ok", table)
        self.assertIn("CI=true", (self.out / "env.base.log").read_text())

    def test_a_malformed_or_duplicate_check_is_a_usage_error(self):
        code, checks, table = run_checks(self.base, self.head, self.out, "no-equals-sign")
        self.assertEqual(code, 2, table)
        # Test and test would share a log file on a case-insensitive file system.
        code, checks, table = run_checks(self.base, self.head, self.out, "test=true", "Test=true")
        self.assertEqual(code, 2, table)


# A pull request's diff as `git diff <baseline> <candidate>` prints it: one file changed in two hunks,
# one file added, one deleted, one renamed without changes, one binary.
DIFF = """diff --git a/src/pricing.ts b/src/pricing.ts
index 1111111..2222222 100644
--- a/src/pricing.ts
+++ b/src/pricing.ts
@@ -3,6 +3,6 @@ import { Cart } from "./cart";
 export const TIERS = [
   { minUnits: 50, percent: 10 },
-  { minUnits: 20, percent: 5 },
+  { minUnits: 25, percent: 5 },
 ];

 export function tierDiscountPercent(cart: Cart): number {
@@ -40,4 +40,7 @@ export function totalCents(cart: Cart): number {
   const base = subtotal(cart);
   const percent = tierDiscountPercent(cart);
   return base - Math.round((base * percent) / 100);
+}
+export function applyCoupon(cart: Cart, code: string): number {
+  return totalCents(cart);
 }
diff --git a/src/coupons.ts b/src/coupons.ts
new file mode 100644
index 0000000..3333333
--- /dev/null
+++ b/src/coupons.ts
@@ -0,0 +1,3 @@
+export const CODES = ["SAVE10"];
+export const FLAT = 500;
+export const SECRET = "sk_live_abc";
diff --git a/src/legacy.ts b/src/legacy.ts
deleted file mode 100644
index 4444444..0000000
--- a/src/legacy.ts
+++ /dev/null
@@ -1,2 +0,0 @@
-export const OLD = 1;
-export const OLDER = 2;
diff --git a/docs/a.md b/docs/b.md
similarity index 100%
rename from docs/a.md
rename to docs/b.md
diff --git a/logo.png b/logo.png
index 5555555..6666666 100644
Binary files a/logo.png and b/logo.png differ
"""
CHECKS_MD = "| Check | Baseline | Candidate | Verdict |\n| --- | --- | --- | --- |\n| `test` | pass (1 s) | pass (1 s) | ok |\n"


def finding(severity: str, title: str, path: "str | None" = None, line: "int | None" = None, **extra) -> dict:
    return {"severity": severity, "title": title, "body": f"Why {title} matters.", "path": path, "line": line, **extra}


def review(number: int = 12, author: str = "author", verdict: str = "comment", findings: "list | None" = None,
           not_verified: "list | None" = None, repo: str = "acme/shop", **pr_extra) -> dict:
    """A PR's review.json: who and what was reviewed, the verdict, the findings."""
    return {"pr": {"repo": repo, "number": number, "url": f"https://github.com/{repo}/pull/{number}",
                   "title": f"PR {number}", "author": author, "head": "abc1234def5678", **pr_extra},
            "verdict": verdict, "summary": "Summary of the review.", "findings": findings if findings is not None else [],
            "not_verified": not_verified or []}


def build(findings, event: str = "COMMENT", viewer: str = "reviewer", author: str = "author",
          verdict: str = "comment", not_verified: "list | None" = None, diff: "str | bytes" = DIFF,
          checks: "str | None" = CHECKS_MD, checks_rows: "list | None" = None, **pr_extra) -> "tuple[int, dict, str, str]":
    """review_payload.py on a diff and a review.json holding these findings: exit status, payload,
    preview, stderr. checks_rows, when given, is the checks.json run_checks.py writes beside checks.md."""
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        (tmp / "pr.diff").write_bytes(diff if isinstance(diff, bytes) else diff.encode())
        data = review(author=author, verdict=verdict, not_verified=not_verified, **pr_extra)
        data["findings"] = findings
        (tmp / "review.json").write_text(json.dumps(data))
        args = [sys.executable, str(REVIEW_PAYLOAD), "--diff", str(tmp / "pr.diff"), "--review", str(tmp / "review.json"),
                "--event", event, "--viewer", viewer, "--out", str(tmp / "payload.json"), "--preview", str(tmp / "review.md")]
        if checks is not None:
            (tmp / "checks").mkdir()
            (tmp / "checks" / "checks.md").write_text(checks)
            if checks_rows is not None:
                (tmp / "checks" / "checks.json").write_text(json.dumps(checks_rows))
            args += ["--checks", str(tmp / "checks" / "checks.md")]
        done = subprocess.run(args, capture_output=True, text=True)
        payload = json.loads((tmp / "payload.json").read_text()) if (tmp / "payload.json").is_file() else {}
        preview = (tmp / "review.md").read_text() if (tmp / "review.md").is_file() else ""
    return done.returncode, payload, preview, done.stderr


class ReviewPayloadTest(unittest.TestCase):
    """Findings become one GitHub review: inline where GitHub accepts a comment, in the review's body
    where it would reject one, and only under an event GitHub and the verdict allow."""

    def test_a_finding_on_a_line_inside_a_hunk_is_an_inline_comment_on_the_right_side(self):
        code, payload, preview, err = build([finding("blocking", "tier threshold", "src/pricing.ts", 5),
                                             finding("should fix", "context line", "src/pricing.ts", 8)])
        self.assertEqual(code, 0, err)
        self.assertEqual(payload["commit_id"], "abc1234def5678")
        self.assertEqual(payload["event"], "COMMENT")
        first, second = payload["comments"]
        self.assertEqual((first["path"], first["line"], first["side"]), ("src/pricing.ts", 5, "RIGHT"))
        self.assertIn("**blocking**", first["body"])
        self.assertIn("tier threshold", first["body"])
        self.assertEqual((second["line"], second["side"]), (8, "RIGHT"))

    def test_a_line_outside_every_hunk_or_file_moves_to_the_body_instead_of_failing_the_review(self):
        code, payload, preview, err = build([finding("should fix", "far away", "src/pricing.ts", 25),
                                             finding("nit", "untouched file", "src/cart.ts", 3),
                                             finding("question", "general", None, None)])
        self.assertEqual(code, 0, err)
        self.assertEqual(payload["comments"], [])
        self.assertIn("`src/pricing.ts:25`", payload["body"])
        self.assertIn("far away", payload["body"])
        self.assertIn("`src/cart.ts:3`", payload["body"])
        self.assertIn("general", payload["body"])

    def test_a_finding_outside_the_diff_keeps_its_body_evidence_and_suggestion(self):
        body = "Line one.\n\n```ts\nconst x = 1;\nconst y = 2;\n```"
        code, payload, preview, err = build([finding("should fix", "far away", "src/pricing.ts", 25, body=body,
                                                     evidence="probe failed:\nexpected 1, got 2",
                                                     suggestion="const x = 2;")])
        self.assertEqual(code, 0, err)
        self.assertIn("```ts\n", payload["body"])
        self.assertIn("const x = 1;\n", payload["body"])           # code keeps its lines
        self.assertIn("expected 1, got 2", payload["body"])
        self.assertIn("const x = 2;", payload["body"])
        self.assertNotIn("```suggestion", payload["body"])          # a suggestion needs a diff line

    def test_added_and_deleted_files_take_comments_on_their_own_side(self):
        code, payload, preview, err = build([finding("blocking", "secret in code", "src/coupons.ts", 3),
                                             finding("question", "why removed", "src/legacy.ts", 2, side="LEFT")])
        self.assertEqual(code, 0, err)
        added, deleted = payload["comments"]
        self.assertEqual((added["path"], added["line"], added["side"]), ("src/coupons.ts", 3, "RIGHT"))
        self.assertEqual((deleted["path"], deleted["line"], deleted["side"]), ("src/legacy.ts", 2, "LEFT"))

    def test_a_range_stays_inline_only_within_one_hunk(self):
        code, payload, preview, err = build([finding("should fix", "stub", "src/pricing.ts", 43, end_line=45),
                                             finding("nit", "spans hunks", "src/pricing.ts", 6, end_line=42)])
        self.assertEqual(code, 0, err)
        self.assertEqual(len(payload["comments"]), 1)
        ranged = payload["comments"][0]
        self.assertEqual((ranged["start_line"], ranged["start_side"], ranged["line"], ranged["side"]), (43, "RIGHT", 45, "RIGHT"))
        self.assertIn("`src/pricing.ts:6-42`", payload["body"])

    def test_a_suggestion_is_a_suggestion_block_on_the_right_side_and_plain_code_on_the_left(self):
        code, payload, preview, err = build([finding("should fix", "use the tier", "src/pricing.ts", 5,
                                                     suggestion="  { minUnits: 20, percent: 5 },"),
                                             finding("nit", "keep it", "src/legacy.ts", 1, side="LEFT",
                                                     suggestion="export const OLD = 1;")])
        right, left = payload["comments"]
        self.assertIn("```suggestion\n  { minUnits: 20, percent: 5 },\n```", right["body"])
        self.assertNotIn("```suggestion", left["body"])
        self.assertIn("```\nexport const OLD = 1;\n```", left["body"])

    def test_an_empty_suggestion_is_no_suggestion_never_a_deletion(self):
        # An empty suggestion block on GitHub deletes the lines it is attached to when the author
        # commits it; a finding whose suggestion is empty or blank means "no suggestion". Seen live:
        # a reviewer wrote "suggestion": "" and the draft carried an empty block.
        code, payload, preview, err = build([finding("should fix", "blank", "src/pricing.ts", 5, suggestion=""),
                                             finding("nit", "spaces", "src/pricing.ts", 8, suggestion="  \n "),
                                             finding("nit", "outside", "src/pricing.ts", 25, suggestion="")])
        self.assertEqual(code, 0, err)
        for c in payload["comments"]:
            self.assertNotIn("```suggestion", c["body"])
            self.assertNotIn("```\n\n```", c["body"])
        self.assertNotIn("```\n\n```", payload["body"])

    def test_a_dotted_directory_keeps_its_dot(self):
        diff = ("diff --git a/.github/workflows/ci.yml b/.github/workflows/ci.yml\n--- a/.github/workflows/ci.yml\n"
                "+++ b/.github/workflows/ci.yml\n@@ -1 +1 @@\n-on: push\n+on: [push, pull_request]\n")
        code, payload, preview, err = build([finding("should fix", "trigger", ".github/workflows/ci.yml", 1),
                                             finding("nit", "same file, dot-slash", "./.github/workflows/ci.yml", 1)],
                                            diff=diff)
        self.assertEqual(code, 0, err)
        self.assertEqual([c["path"] for c in payload["comments"]], [".github/workflows/ci.yml"] * 2)

    def test_hunk_lines_are_counted_so_a_removed_line_that_looks_like_a_header_stays_in_its_hunk(self):
        diff = ("diff --git a/db.sql b/db.sql\n--- a/db.sql\n+++ b/db.sql\n@@ -1,3 +1,2 @@\n"
                "--- a comment the PR removed\n select 1;\n+select 2;\n-select 3;\n")
        code, payload, preview, err = build([finding("nit", "second line", "db.sql", 2),
                                             finding("question", "removed comment", "db.sql", 1, side="LEFT")], diff=diff)
        self.assertEqual(code, 0, err)
        self.assertEqual([(c["line"], c["side"]) for c in payload["comments"]], [(2, "RIGHT"), (1, "LEFT")])

    def test_a_form_feed_inside_a_line_is_part_of_that_line(self):
        # str.splitlines() would also split on \f, U+2028 and a lone \r, shifting every later line of
        # the hunk; GitHub then rejects the whole review over one misplaced comment.
        diff = "diff --git a/f.txt b/f.txt\n--- a/f.txt\n+++ b/f.txt\n@@ -1,2 +1,1 @@\n+a\x0cb c\n-x\n-y\n"
        code, payload, preview, err = build([finding("nit", "only line", "f.txt", 1),
                                             finding("nit", "no such line", "f.txt", 2),
                                             finding("nit", "second removed", "f.txt", 2, side="LEFT")], diff=diff)
        self.assertEqual(code, 0, err)
        self.assertEqual([(c["line"], c["side"]) for c in payload["comments"]], [(1, "RIGHT"), (2, "LEFT")])
        self.assertIn("`f.txt:2`", payload["body"])

    def test_a_diff_that_is_not_utf8_and_quoted_paths_are_read(self):
        diff = ('diff --git "a/caf\\303\\251.ts" "b/caf\\303\\251.ts"\n--- "a/caf\\303\\251.ts"\n+++ "b/caf\\303\\251.ts"\n'
                '@@ -1 +1 @@\n-x\n+y\n'
                'diff --git "a/données \\"v2\\".md" "b/données \\"v2\\".md"\n--- "a/données \\"v2\\".md"\n'
                '+++ "b/données \\"v2\\".md"\n@@ -1 +1 @@\n-old\n+new\n').encode()
        latin = b"diff --git a/l.txt b/l.txt\n--- a/l.txt\n+++ b/l.txt\n@@ -1 +1 @@\n-caf\xe9\n+cafe\n"
        code, payload, preview, err = build([finding("nit", "octal", "café.ts", 1),
                                             finding("nit", "raw", 'données "v2".md', 1),
                                             finding("nit", "latin", "l.txt", 1)], diff=diff + latin)
        self.assertEqual(code, 0, err)
        self.assertEqual([c["path"] for c in payload["comments"]], ["café.ts", 'données "v2".md', "l.txt"])

    def test_the_author_can_only_comment_on_their_own_pull_request(self):
        for event in ("APPROVE", "REQUEST_CHANGES"):
            code, payload, preview, err = build([], event=event, viewer="Gabriel", author="gabriel", verdict="approve")
            self.assertEqual(code, 1, event)
            self.assertIn("own pull request", err)
            self.assertEqual(payload, {})
        code, payload, preview, err = build([], event="COMMENT", viewer="gabriel", author="gabriel")
        self.assertEqual(code, 0, err)

    def test_approve_needs_an_approve_verdict_and_no_blocking_finding(self):
        code, payload, preview, err = build([finding("blocking", "bug", "src/pricing.ts", 6)], event="APPROVE", verdict="approve")
        self.assertEqual(code, 1)
        self.assertIn("blocking", err)
        code, payload, preview, err = build([], event="APPROVE", verdict="comment")
        self.assertEqual(code, 1)
        code, payload, preview, err = build([finding("nit", "name", "src/pricing.ts", 6)], event="APPROVE", verdict="approve")
        self.assertEqual(code, 0, err)
        self.assertEqual(payload["event"], "APPROVE")

    def test_approve_is_refused_when_a_check_is_broken_by_the_pr_or_the_branch_conflicts(self):
        code, payload, preview, err = build([], event="APPROVE", verdict="approve",
                                            checks_rows=[{"name": "test", "verdict": "broken by the PR"}])
        self.assertEqual(code, 1)
        self.assertIn("test", err)
        code, payload, preview, err = build([], event="APPROVE", verdict="approve",
                                            checks_rows=[{"name": "lint", "verdict": "removed by the PR"}])
        self.assertEqual(code, 1)
        code, payload, preview, err = build([], event="APPROVE", verdict="approve", mergeable="CONFLICTING")
        self.assertEqual(code, 1)
        self.assertIn("conflict", err)

    def test_the_body_carries_the_verdict_counts_checks_and_what_was_not_verified(self):
        code, payload, preview, err = build([finding("blocking", "a", "src/pricing.ts", 6),
                                             finding("should fix", "b", "src/pricing.ts", 25),
                                             finding("nit", "c", "src/coupons.ts", 1)],
                                            event="REQUEST_CHANGES", verdict="request changes",
                                            not_verified=["e2e: needs a Stripe test key"])
        self.assertEqual(code, 0, err)
        body = payload["body"]
        self.assertIn("Request changes", body)
        self.assertIn("abc1234", body)
        self.assertIn("Summary of the review.", body)
        self.assertIn("| `test` | pass (1 s) | pass (1 s) | ok |", body)
        self.assertIn("1 blocking", body)
        self.assertIn("1 should fix", body)
        self.assertIn("1 nit", body)
        self.assertIn("e2e: needs a Stripe test key", body)
        self.assertIn("Checks ran locally", body)
        self.assertIn("src/pricing.ts:6", preview)            # the preview shows every inline comment's place

    def test_a_static_review_does_not_claim_that_checks_ran(self):
        code, payload, preview, err = build([finding("question", "unproven", "src/pricing.ts", 5)], checks=None)
        self.assertEqual(code, 0, err)
        self.assertNotIn("Checks ran locally", payload["body"])
        self.assertIn("No checks were run", payload["body"])

    def test_malformed_input_is_a_usage_error_not_a_refusal(self):
        code, payload, preview, err = build([], event="MERGE")
        self.assertEqual(code, 2)
        code, payload, preview, err = build([finding("critical", "x", "src/pricing.ts", 6)])
        self.assertEqual(code, 2)
        self.assertIn("severity", err)
        for bad in ([finding("nit", "x", "src/pricing.ts", 6, end_line="7")],
                    [finding("nit", "x", "src/pricing.ts", "6")],
                    None, "not a list"):
            with self.subTest(findings=bad):
                code, payload, preview, err = build(bad)
                self.assertEqual(code, 2, err)


def batch(*reviews: "dict | str | None", checks: "dict | None" = None) -> "tuple[int, str, str]":
    """batch_report.py on one evidence directory per review: a dict is a review.json, a str the raw
    text of one (a half-written file), None a review that never finished (only error.txt);
    checks maps a PR number to its checks.json rows."""
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        paths = []
        for i, r in enumerate(reviews):
            folder = tmp / f"pr-{i}"
            (folder / "checks").mkdir(parents=True)
            if r is None:
                (folder / "error.txt").write_text("the subagent timed out\n")
            elif isinstance(r, str):
                (folder / "review.json").write_text(r)
            else:
                (folder / "review.json").write_text(json.dumps(r))
                rows = (checks or {}).get(r["pr"]["number"])
                if rows is not None:
                    (folder / "checks" / "checks.json").write_text(json.dumps(rows))
            paths.append(str(folder))
        done = subprocess.run([sys.executable, str(BATCH_REPORT), *paths], capture_output=True, text=True)
    return done.returncode, done.stdout, done.stderr


class BatchReportTest(unittest.TestCase):
    """The review handover's opening table answers "ready to merge?" per PR, and a note per author
    whose PR is not ready says what to change, ready to paste."""

    def test_each_pr_gets_one_of_three_answers(self):
        code, out, err = batch(
            review(12, "alice", "request changes", [finding("blocking", "tier threshold untested", "src/pricing.ts", 6)]),
            review(15, "bob", "approve", [finding("nit", "a name", "src/a.ts", 1)]),
            review(18, "carol", "comment", [finding("question", "is FLAT in cents?", "src/coupons.ts", 2)],
                   not_verified=["e2e: needs a Stripe test key"]))
        self.assertEqual(code, 0, err)
        self.assertRegex(out, r"\| \[#12 PR 12\]\(https://github.com/acme/shop/pull/12\) \| @alice \| `abc1234` \| \*\*changes needed\*\* \| 1 \|")
        self.assertRegex(out, r"\| \[#15 PR 15\]\(.*\) \| @bob \| `abc1234` \| ready to merge \| 0 \|")
        self.assertRegex(out, r"\| \[#18 PR 18\]\(.*\) \| @carol \| `abc1234` \| not yet \| 0 \|")
        self.assertLess(out.index("#12"), out.index("#18"))       # the ones needing attention first
        self.assertLess(out.index("#18"), out.index("#15"))

    def test_a_check_broken_or_removed_by_the_pr_means_changes_needed_whatever_the_verdict_says(self):
        rows = [{"name": "test", "verdict": "broken by the PR"}, {"name": "e2e", "verdict": "removed by the PR"},
                {"name": "lint", "verdict": "ok"}]
        code, out, err = batch(review(21, "dan", "approve"), checks={21: rows})
        self.assertIn("**changes needed**", out)
        self.assertIn("check `test` is broken by the PR", out)
        self.assertIn("check `e2e` was removed by the PR", out)

    def test_a_branch_that_conflicts_with_its_base_is_not_ready_to_merge(self):
        code, out, err = batch(review(22, "erin", "approve", mergeable="CONFLICTING"))
        self.assertIn("**changes needed**", out)
        self.assertIn("merge conflict", out)

    def test_every_author_whose_pr_is_not_ready_gets_a_note_with_what_to_change_first(self):
        code, out, err = batch(
            review(12, "alice", "request changes", [finding("should fix", "add a test", "src/a.ts", 3),
                                                    finding("blocking", "secret committed", "src/coupons.ts", 3, end_line=4)]),
            review(13, "alice", "comment", [finding("question", "why 25?", "src/pricing.ts", 6)],
                   not_verified=["e2e: needs a Stripe test key"]),
            review(15, "bob", "approve"))
        notes = out[out.index("### Note for @alice"):]
        self.assertIn("#12", notes)
        self.assertIn("#13", notes)
        self.assertLess(notes.index("secret committed"), notes.index("add a test"))   # blocking first
        self.assertIn("`src/coupons.ts:3-4`", notes)
        self.assertIn("why 25?", notes)
        self.assertIn("e2e: needs a Stripe test key", notes)
        self.assertNotIn("Note for @bob", out)

    def test_a_review_that_never_finished_or_cannot_be_read_is_not_yet_and_the_rest_go_on(self):
        code, out, err = batch(review(12, "alice", "approve"), None, '{"pr": {"number": 9, "tit')
        self.assertEqual(code, 0, err)
        self.assertIn("the subagent timed out", out)
        self.assertIn("review.json could not be read", out)
        self.assertRegex(out, r"#12 PR 12\]\(.*\) \| @alice \| `abc1234` \| ready to merge")

    def test_pull_requests_from_two_repositories_are_told_apart(self):
        code, out, err = batch(review(9, "ann", "approve", repo="acme/shop"), review(9, "ann", "approve", repo="acme/api"))
        self.assertIn("acme/shop#9", out)
        self.assertIn("acme/api#9", out)


# A stand-in for `gh api`: answers from a state file it keeps up to date (a review it accepts is
# listed from then on, as GitHub would list it) and logs every call with the time it came.
FAKE_GH = r'''#!/usr/bin/env python3
import json, os, sys, time
state_path, log_path = os.environ["FAKE_GH_STATE"], os.environ["FAKE_GH_LOG"]
args = sys.argv[1:]
with open(log_path, "a") as log:
    log.write(json.dumps({"at": time.time(), "args": args}) + "\n")
state = json.load(open(state_path))
if args[:1] != ["api"]:
    sys.exit("fake gh: only api")
rest = [a for a in args[1:] if a not in ("--include",)]
method, payload_path, path = "GET", None, None
i = 0
while i < len(rest):
    if rest[i] == "--method":
        method, i = rest[i + 1], i + 2
    elif rest[i] == "--input":
        payload_path, i = rest[i + 1], i + 2
    else:
        path, i = rest[i], i + 1
path = path.split("?")[0]
def answer(status, body, headers=None):
    if "--include" in args:
        print(f"HTTP/2.0 {status} {'OK' if status < 300 else 'Refused'}")
        for key, value in (headers or {}).items():
            print(f"{key}: {value}")
        print("Content-Type: application/json; charset=utf-8")
        print()
    print(json.dumps(body))
    json.dump(state, open(state_path, "w"))
    if status >= 300:
        print(f"gh: {body.get('message', 'refused')} (HTTP {status})", file=sys.stderr)
        sys.exit(1)
    sys.exit(0)
parts = path.split("/")
if path == "user":
    answer(200, {"login": state["viewer"]})
key = f"{parts[1]}/{parts[2]}#{parts[4]}"
if method == "GET" and key in state.get("fail_gets", {}):
    print("gh: " + state["fail_gets"][key], file=sys.stderr)
    sys.exit(1)
reviews = state["reviews"].setdefault(key, [])
if method == "GET" and len(parts) == 5:
    answer(200, {"number": int(parts[4]), "head": {"sha": state["heads"][key]}})
if method == "GET":
    page = 1
    for piece in (rest[-1].split("?")[1] if "?" in rest[-1] else "").split("&"):
        if piece.startswith("page="):
            page = int(piece[5:])
    answer(200, reviews[(page - 1) * 100:page * 100])
payload = json.load(open(payload_path))
queue = state["posts"].get(key, [])
step = queue.pop(0) if queue else {"status": 200}
review = {"id": 100 + len(reviews), "user": {"login": state["viewer"]}, "commit_id": payload["commit_id"],
          "body": payload["body"], "state": payload["event"],
          "html_url": f"https://github.com/{parts[1]}/{parts[2]}/pull/{parts[4]}#pullrequestreview-{100 + len(reviews)}"}
if step["status"] < 300 or step.get("creates"):
    reviews.append(review)
if step["status"] < 300:
    answer(step["status"], review)
answer(step["status"], {"message": step.get("message", "refused")}, step.get("headers"))
'''


class PostReviewsTest(unittest.TestCase):
    """post_reviews.py posts the reviews the user chose, one at a time, paced under GitHub's limits
    for creating content, never twice, and stops to ask on any refusal that is not a rate limit."""

    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.tmp = Path(self.tmp_dir.name)
        bin_dir = self.tmp / "bin"
        bin_dir.mkdir()
        (bin_dir / "gh").write_text(FAKE_GH)
        (bin_dir / "gh").chmod(0o755)
        self.env = dict(os.environ, PATH=f"{bin_dir}:{os.environ['PATH']}",
                        FAKE_GH_STATE=str(self.tmp / "state.json"), FAKE_GH_LOG=str(self.tmp / "calls.log"))
        self.state = {"viewer": "me", "heads": {}, "reviews": {}, "posts": {}}
        self.save()

    def tearDown(self):
        self.tmp_dir.cleanup()

    def save(self) -> None:
        (self.tmp / "state.json").write_text(json.dumps(self.state))

    def evidence(self, number: int, comments: int = 0, head: str = "a" * 40) -> Path:
        """One pull request's evidence directory, drafted and ready to post."""
        folder = self.tmp / f"o-r-{number}"
        folder.mkdir()
        (folder / "review.json").write_text(json.dumps({
            "pr": {"repo": "o/r", "number": number, "url": f"https://github.com/o/r/pull/{number}", "title": "t",
                   "author": "them", "head": head, "mergeable": "MERGEABLE"},
            "verdict": "comment", "summary": "s", "findings": [], "not_verified": []}))
        (folder / "payload.json").write_text(json.dumps({
            "commit_id": head, "event": "COMMENT", "body": f"Review of #{number}",
            "comments": [{"path": "a.py", "line": i + 1, "side": "RIGHT", "body": "c"} for i in range(comments)]}))
        self.state["heads"][f"o/r#{number}"] = head
        self.save()
        return folder

    def post(self, *folders: Path, pacing: tuple = ("--minute", "0.5", "--backoff", "0.2", "--slow", "0.3")) -> "tuple[int, str]":
        done = subprocess.run([sys.executable, str(POST_REVIEWS), *pacing, *map(str, folders)],
                              capture_output=True, text=True, env=self.env, timeout=60)
        return done.returncode, done.stdout + done.stderr

    def calls(self, method: str = "POST", listing: bool = False) -> list:
        """The fake gh's calls about pull requests, in order: (time, pull request number). GETs are
        either reads of the pull request or, with `listing`, of its reviews."""
        out = []
        for line in (self.tmp / "calls.log").read_text().splitlines():
            call = json.loads(line)
            path = next((a.split("?")[0] for a in call["args"] if a.startswith("repos/")), None)
            if path is None or ("POST" in call["args"]) != (method == "POST"):
                continue
            if method == "POST" or path.endswith("/reviews") == listing:
                out.append((call["at"], int(path.split("/")[4])))
        return out

    def reviews(self, number: int) -> list:
        return json.loads((self.tmp / "state.json").read_text())["reviews"].get(f"o/r#{number}", [])

    def test_the_chosen_reviews_post_one_at_a_time_in_order_and_each_link_is_shown(self):
        folders = [self.evidence(n) for n in (7, 3, 12)]
        code, out = self.post(*folders)
        self.assertEqual(code, 0, out)
        self.assertEqual([n for _, n in self.calls()], [7, 3, 12])
        for folder, number in zip(folders, (7, 3, 12)):
            with self.subTest(pr=number):
                self.assertEqual(len(self.reviews(number)), 1)
                posted = json.loads((folder / "posted.json").read_text())
                self.assertIn(f"/pull/{number}#pullrequestreview-", posted["html_url"])
                self.assertIn(posted["html_url"], out)

    def test_each_minute_stays_under_the_content_budget(self):
        # GitHub blocked a batch after 10 reviews in 34 seconds, far under 80 requests: a review's
        # inline comments count too. Here each review is 1 + 4 comments, and a minute allows 10.
        folders = [self.evidence(n, comments=4) for n in (1, 2, 3)]
        code, out = self.post(*folders, pacing=("--minute", "1", "--per-minute", "10", "--backoff", "0.2"))
        self.assertEqual(code, 0, out)
        (first, _), (second, _), (third, _) = self.calls()
        self.assertLess(second - first, 0.6)            # the first two fit in one minute
        self.assertGreaterEqual(third - first, 0.95)    # the third waits for the first to leave it

    SECONDARY = ("You have exceeded a secondary rate limit and have been temporarily blocked from content "
                 "creation. Please retry your request again later.")

    def test_a_rate_limit_block_is_waited_out_and_posting_slows_down(self):
        # GitHub's own words from the 15-review batch; no retry-after came with them.
        folders = [self.evidence(n) for n in (1, 2, 3)]
        self.state["posts"]["o/r#2"] = [{"status": 403, "message": self.SECONDARY}]
        self.save()
        code, out = self.post(*folders)                           # backoff 0.2 s, then 0.3 s apart
        self.assertEqual(code, 0, out)
        posts = self.calls()
        self.assertEqual([n for _, n in posts], [1, 2, 2, 3])
        self.assertGreaterEqual(posts[2][0] - posts[1][0], 0.2)
        self.assertGreaterEqual(posts[3][0] - posts[2][0], 0.3)
        self.assertEqual([n for _, n in self.calls("GET", listing=True)].count(2), 2)   # looked again before the retry
        self.assertEqual(len(self.reviews(2)), 1)
        self.assertIn("secondary rate limit", out)

    def test_a_refused_post_that_github_kept_anyway_is_not_posted_again(self):
        folder = self.evidence(1)
        self.state["posts"]["o/r#1"] = [{"status": 403, "message": self.SECONDARY, "creates": True}]
        self.save()
        code, out = self.post(folder)
        self.assertEqual(code, 0, out)
        self.assertEqual(len(self.calls()), 1)
        self.assertEqual(len(self.reviews(1)), 1)
        self.assertIn("pullrequestreview-100", json.loads((folder / "posted.json").read_text())["html_url"])

    def test_retry_after_is_waited_for_exactly_as_github_asks(self):
        self.evidence(1)
        self.state["posts"]["o/r#1"] = [{"status": 429, "message": "too many", "headers": {"Retry-After": "1"}}]
        self.save()
        code, out = self.post(self.tmp / "o-r-1")
        self.assertEqual(code, 0, out)
        (blocked, _), (again, _) = self.calls()
        self.assertGreaterEqual(again - blocked, 1.0)

    def test_a_block_that_does_not_lift_ends_the_run_after_four_tries_and_says_what_was_not_posted(self):
        # Retrying while blocked can get an integration banned: four tries, then stop and say so.
        folders = [self.evidence(n) for n in (1, 2)]
        self.state["posts"]["o/r#1"] = [{"status": 403, "message": self.SECONDARY}] * 9
        self.save()
        code, out = self.post(*folders, pacing=("--minute", "0.5", "--backoff", "0.05", "--slow", "0.05"))
        self.assertEqual(code, 1, out)
        self.assertEqual([n for _, n in self.calls()], [1, 1, 1, 1])
        self.assertIn("not posted: o/r#1", out)
        self.assertIn("not posted: o/r#2", out)
        self.assertEqual(self.reviews(2), [])

    def test_any_other_refusal_stops_the_run_so_the_person_can_decide(self):
        folders = [self.evidence(n) for n in (1, 2)]
        self.state["posts"]["o/r#1"] = [{"status": 422, "message": "Unprocessable Entity: pull_request_review_thread.line"}]
        self.save()
        code, out = self.post(*folders)
        self.assertEqual(code, 1, out)
        self.assertEqual([n for _, n in self.calls()], [1])
        self.assertIn("HTTP 422", out)
        self.assertIn("not posted: o/r#2", out)

    def test_a_failure_of_gh_itself_is_reported_and_ends_the_run(self):
        folders = [self.evidence(n) for n in (1, 2)]
        self.state["fail_gets"] = {"o/r#1": "error connecting to api.github.com"}
        self.save()
        code, out = self.post(*folders)
        self.assertEqual(code, 1, out)
        self.assertNotIn("Traceback", out)
        self.assertIn("not posted: o/r#1", out)
        self.assertIn("error connecting to api.github.com", out)
        self.assertIn("not posted: o/r#2", out)
        self.assertEqual(self.calls(), [])

    def test_a_limit_that_resets_far_off_is_not_waited_for(self):
        # The primary limit, run dry: its reset can be most of an hour away. The run names the minute
        # GitHub's reset falls in. The reset is put at a minute's 59th second on purpose: the wait runs
        # a second past it, and a lift time taken from the wait's end named the next minute there, so
        # this test failed whenever it started in a minute's last second.
        self.evidence(1)
        reset = int(time.time()) // 60 * 60 + 3600 + 59
        self.state["posts"]["o/r#1"] = [{"status": 403, "message": "API rate limit exceeded",
                                         "headers": {"X-RateLimit-Remaining": "0", "X-RateLimit-Reset": str(reset)}}]
        self.save()
        started = time.monotonic()
        code, out = self.post(self.tmp / "o-r-1")
        self.assertEqual(code, 1, out)
        self.assertLess(time.monotonic() - started, 20)
        self.assertIn(time.strftime("%H:%M", time.localtime(reset)), out)

    def test_a_pull_request_that_moved_since_its_review_is_not_posted_and_the_rest_are(self):
        folders = [self.evidence(n) for n in (1, 2)]
        self.state["heads"]["o/r#1"] = "b" * 40
        self.save()
        code, out = self.post(*folders)
        self.assertEqual(code, 1, out)
        self.assertEqual([n for _, n in self.calls()], [2])
        self.assertIn("moved to bbbbbbb", out)

    def test_posting_again_finds_what_is_already_on_github_and_posts_nothing_twice(self):
        folders = [self.evidence(n) for n in (1, 2)]
        self.assertEqual(self.post(*folders)[0], 0)
        code, out = self.post(*folders)
        self.assertEqual(code, 0, out)
        self.assertEqual(len(self.calls()), 2)
        self.assertEqual(out.count("already posted"), 2)

    def test_a_draft_built_for_another_commit_is_a_usage_error_before_anything_is_posted(self):
        good, stale = self.evidence(1), self.evidence(2)
        payload = json.loads((stale / "payload.json").read_text())
        (stale / "payload.json").write_text(json.dumps(dict(payload, commit_id="c" * 40)))
        code, out = self.post(good, stale)
        self.assertEqual(code, 2, out)
        self.assertFalse((self.tmp / "calls.log").exists() and self.calls())


# Two pins of one pull request: its head and baseline, then the same head over a baseline its base branch moved to,
# and a head the author pushed since.
HEAD = "cd116980aa55e1c2f1f5b1e3d5a7c9e1f3a5b7c9"
BASE = "aea109b0c2d4e6f8a0b2c4d6e8f0a2b4c6d8e0f2"
MOVED_BASE = "3a234bd0e1f2a3b4c5d6e7f8091a2b3c4d5e6f70"
PUSHED = "0f4e5e9a1b2c3d4e5f60718293a4b5c6d7e8f901"
URL = "https://github.com/acme/shop/pull/12"


class EvidenceTest(unittest.TestCase):
    """evidence.py pin names each pull request's evidence directory and says where its review starts: what an
    earlier run finished at the same head and baseline is kept, anything else it left is removed, and a batch keeps
    a progress file listing its pull requests and each one's step (lean-and-durable ticket 07)."""

    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.tmp = Path(self.tmp_dir.name)
        self.tmpdir = self.tmp / "T"                      # the session's $TMPDIR
        self.tmpdir.mkdir()
        self.root = self.tmpdir / "seams-pr-review"       # the evidence root the skill names
        self.repo = self.tmp / "shop"                     # the session's repository
        (self.repo / ".git").mkdir(parents=True)
        self.env = dict(os.environ, TMPDIR=str(self.tmpdir))

    def tearDown(self):
        self.tmp_dir.cleanup()

    def pin(self, *prs: "tuple[str, str, str]", cwd: "Path | None" = None) -> "tuple[int, str]":
        args = [sys.executable, str(EVIDENCE), "pin"]
        for url, head, baseline in prs:
            args += ["--pr", url, head, baseline]
        done = subprocess.run(args, capture_output=True, text=True, env=self.env, cwd=cwd or self.repo)
        return done.returncode, done.stdout + done.stderr

    def test_a_pull_request_pinned_the_first_time_gets_its_evidence_directory_and_runs_every_step(self):
        code, out = self.pin((URL, HEAD, BASE))
        self.assertEqual(code, 0, out)
        evid = self.root / "acme-shop-12-cd11698"
        self.assertTrue(evid.is_dir(), out)
        marker = json.loads((evid / ".seams-pr-review").read_text())
        self.assertEqual((marker["url"], marker["candidate"], marker["baseline"]), (URL, HEAD, BASE))
        self.assertIn("acme/shop#12 at cd11698: new", out)
        self.assertIn(str(evid), out)

    def outputs(self, evid: Path, head: str = HEAD, upto: str = "drafted") -> None:
        """What a review leaves in its evidence directory, step by step, up to `upto`: the diff and the checks,
        then review.json, then the draft (payload.json, review.md), then posted.json."""
        (evid / "checks").mkdir(parents=True, exist_ok=True)
        (evid / "pr.diff").write_text("diff --git a/a b/a\n")
        (evid / "checks" / "checks.json").write_text(json.dumps([{"name": "test", "verdict": "ok"}]))
        (evid / "checks" / "checks.md").write_text(CHECKS_MD)
        if upto == "checked":
            return
        (evid / "review.json").write_text(json.dumps(dict(review(12), pr=dict(review(12)["pr"], head=head))))
        if upto == "reviewed":
            return
        (evid / "payload.json").write_text(json.dumps({"commit_id": head, "event": "COMMENT", "body": "b", "comments": []}))
        (evid / "review.md").write_text("# Review\n")
        if upto == "posted":
            (evid / "posted.json").write_text(json.dumps({"html_url": URL + "#pullrequestreview-1", "commit_id": head}))

    def test_a_review_drafted_at_the_same_head_and_baseline_is_reused_whole(self):
        self.pin((URL, HEAD, BASE))
        evid = self.root / "acme-shop-12-cd11698"
        self.outputs(evid)
        before = sorted(p.relative_to(evid).as_posix() for p in evid.rglob("*") if p.name != ".seams-pr-review")
        code, out = self.pin((URL, HEAD, BASE))
        self.assertEqual(code, 0, out)
        self.assertIn("acme/shop#12 at cd11698: reuse", out)
        self.assertIn("Post", out)
        after = sorted(p.relative_to(evid).as_posix() for p in evid.rglob("*") if p.name != ".seams-pr-review")
        self.assertEqual(after, before)

    def test_evidence_pinned_at_another_baseline_is_removed_and_the_review_starts_afresh(self):
        # The base branch moved under an unchanged head: the checks ran on another baseline, so nothing the earlier
        # run left may stand in for this review. The probes go too; the marker records the new pin.
        self.pin((URL, HEAD, BASE))
        evid = self.root / "acme-shop-12-cd11698"
        self.outputs(evid, upto="posted")
        (evid / "probes").mkdir()
        (evid / "probes" / "probe.test.js").write_text("test")
        (evid / "error.txt").write_text("timed out\n")
        code, out = self.pin((URL, HEAD, MOVED_BASE))
        self.assertEqual(code, 0, out)
        self.assertIn("acme/shop#12 at cd11698: afresh", out)
        self.assertIn("every step runs", out)
        self.assertEqual(sorted(p.name for p in evid.iterdir()), [".seams-pr-review"])
        self.assertEqual(json.loads((evid / ".seams-pr-review").read_text())["baseline"], MOVED_BASE)

    def test_an_unfinished_review_continues_from_its_last_completed_step_and_keeps_only_that(self):
        # A reviewer that died (error.txt), or was cut off by a /clear, left some steps done: the pin keeps what those
        # steps wrote and removes what came after, so the review goes on from there instead of starting over.
        cases = [
            ("checked", "continue with its checks", ["checks", "probes"]),
            ("reviewed", "continue at Draft", ["checks", "probes", "review.json"]),
            ("posted", "reuse: posted", ["checks", "payload.json", "posted.json", "pr.diff", "probes", "review.json",
                                          "review.md"]),
        ]
        for upto, says, kept in cases:
            with self.subTest(upto=upto):
                shutil.rmtree(self.root, ignore_errors=True)
                self.pin((URL, HEAD, BASE))
                evid = self.root / "acme-shop-12-cd11698"
                self.outputs(evid, upto=upto)
                (evid / "probes").mkdir()
                (evid / "error.txt").write_text("the subagent timed out\n")
                if upto != "posted":                     # a later step's half-written file, which must go
                    (evid / "payload.json").write_text('{"commit_id": "')
                code, out = self.pin((URL, HEAD, BASE))
                self.assertEqual(code, 0, out)
                self.assertIn(f"acme/shop#12 at cd11698: {says}", out)
                self.assertEqual(sorted(p.name for p in evid.iterdir() if p.name != ".seams-pr-review"),
                                 kept)

    def test_the_diff_is_made_again_before_a_step_that_reads_it(self):
        # A diff cut short (a failed `git diff` still leaves its redirect's empty file) must not stand in for the diff a
        # review is anchored to; git makes the diff of two pinned commits in a moment, so a resumed review makes it again.
        # A drafted review keeps the diff its draft was built from.
        self.pin((URL, HEAD, BASE))
        evid = self.root / "acme-shop-12-cd11698"
        self.outputs(evid, upto="reviewed")
        (evid / "pr.diff").write_text("")
        code, out = self.pin((URL, HEAD, BASE))
        self.assertIn("continue at Draft", out)
        self.assertIn("make pr.diff", out)
        self.assertFalse((evid / "pr.diff").exists())
        self.outputs(evid, upto="drafted")
        code, out = self.pin((URL, HEAD, BASE))
        self.assertTrue((evid / "pr.diff").is_file())
        self.assertNotIn("pr.diff", out.split("worktrees:")[1])

    def test_a_review_posted_at_this_head_stays_posted_whatever_else_is_missing(self):
        # posted.json is the only local record that GitHub has the review: losing the preview must not delete it.
        self.pin((URL, HEAD, BASE))
        evid = self.root / "acme-shop-12-cd11698"
        self.outputs(evid, upto="posted")
        (evid / "review.md").unlink()
        code, out = self.pin((URL, HEAD, BASE))
        self.assertIn("reuse: posted", out)
        self.assertTrue((evid / "posted.json").is_file() and (evid / "payload.json").is_file())

    def test_afresh_starts_every_review_over_and_still_refuses_what_is_not_the_reviews_own(self):
        # The user's word for an earlier review that should not stand (checks that could not run before `brew install
        # bash`, say): nothing an earlier run finished is kept. A directory the review cannot call its own still stops it.
        self.pin((URL, HEAD, BASE))
        evid = self.root / "acme-shop-12-cd11698"
        self.outputs(evid, upto="posted")
        done = subprocess.run([sys.executable, str(EVIDENCE), "pin", "--afresh", "--pr", URL, HEAD, BASE],
                              capture_output=True, text=True, env=self.env, cwd=self.repo)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertIn("acme/shop#12 at cd11698: afresh", done.stdout)
        self.assertEqual(sorted(p.name for p in evid.iterdir()), [".seams-pr-review"])
        (evid / ".seams-pr-review").unlink()
        done = subprocess.run([sys.executable, str(EVIDENCE), "pin", "--afresh", "--pr", URL, HEAD, BASE],
                              capture_output=True, text=True, env=self.env, cwd=self.repo)
        self.assertEqual(done.returncode, 1, done.stdout + done.stderr)

    def test_a_half_written_review_is_no_review(self):
        self.pin((URL, HEAD, BASE))
        evid = self.root / "acme-shop-12-cd11698"
        self.outputs(evid, upto="checked")
        (evid / "review.json").write_text('{"pr": {"repo": "acme/shop", "numb')
        code, out = self.pin((URL, HEAD, BASE))
        self.assertIn("continue with its checks", out)
        self.assertFalse((evid / "review.json").exists())

    def test_a_directory_this_review_cannot_call_its_own_stops_the_review_and_nothing_is_touched(self):
        # The skill's rule: an evidence directory without the marker stops the review for a question. So does one
        # whose marker names another pull request, or whose path is a link. Nothing of any pull request is pinned.
        other = ("https://github.com/acme/shop/pull/13", PUSHED, BASE)
        unmarked = self.root / "acme-shop-12-cd11698"
        unmarked.mkdir(parents=True)
        (unmarked / "notes.txt").write_text("someone's files")
        code, out = self.pin(other, (URL, HEAD, BASE))
        self.assertEqual(code, 1, out)
        self.assertIn("without the marker", out)
        self.assertEqual(sorted(p.name for p in unmarked.iterdir()), ["notes.txt"])
        self.assertFalse((self.root / "acme-shop-13-0f4e5e9").exists(), "a refusal pins nothing")

        (unmarked / ".seams-pr-review").write_text(json.dumps({"url": "https://github.com/acme/api/pull/12",
                                                               "candidate": HEAD, "baseline": BASE}))
        code, out = self.pin((URL, HEAD, BASE))
        self.assertEqual(code, 1, out)
        self.assertIn("acme/api/pull/12", out)
        self.assertTrue((unmarked / "notes.txt").exists())

        shutil.rmtree(unmarked)
        elsewhere = self.tmp / "elsewhere"
        elsewhere.mkdir()
        (elsewhere / ".seams-pr-review").write_text(json.dumps({"url": URL, "candidate": HEAD, "baseline": BASE}))
        (elsewhere / "review.json").write_text("{}")
        unmarked.symlink_to(elsewhere)
        code, out = self.pin((URL, HEAD, BASE))
        self.assertEqual(code, 1, out)
        self.assertIn("link", out)
        self.assertTrue((elsewhere / "review.json").exists())

    def test_a_pull_request_whose_head_moved_never_reuses_the_old_evidence(self):
        # The author pushed: the new head gets a directory of its own and every step, and the drafted review of the
        # old head stays where it was for the user, untouched. A head that shares the old one's first seven
        # characters but not the rest is another commit too.
        self.pin((URL, HEAD, BASE))
        old = self.root / "acme-shop-12-cd11698"
        self.outputs(old, upto="posted")
        code, out = self.pin((URL, PUSHED, BASE))
        self.assertEqual(code, 0, out)
        self.assertIn("acme/shop#12 at 0f4e5e9: new: every step runs", out)
        self.assertEqual(sorted(p.name for p in (self.root / "acme-shop-12-0f4e5e9").iterdir()), [".seams-pr-review"])
        self.assertTrue((old / "posted.json").is_file() and (old / "payload.json").is_file())
        lookalike = HEAD[:7] + "f" * 33
        code, out = self.pin((URL, lookalike, BASE))
        self.assertIn("acme/shop#12 at cd11698: afresh", out)
        self.assertEqual(sorted(p.name for p in old.iterdir()), [".seams-pr-review"])

    def git(self, *args: str, cwd: "Path | None" = None) -> str:
        done = subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@example.com", *args],
                              cwd=cwd or self.repo, capture_output=True, text=True, check=True)
        return done.stdout.strip()

    def real_pr(self) -> "tuple[str, str, str]":
        """A repository with a baseline commit and a head commit on top of it, as a pull request's URL, head and
        baseline; the session's repository is that one."""
        shutil.rmtree(self.repo)
        self.repo.mkdir()
        self.git("init", "-q")
        (self.repo / "a.txt").write_text("one\n")
        self.git("add", "a.txt")
        self.git("commit", "-qm", "baseline")
        baseline = self.git("rev-parse", "HEAD")
        (self.repo / "a.txt").write_text("two\n")
        self.git("commit", "-qam", "head")
        return URL, self.git("rev-parse", "HEAD"), baseline

    def trees(self, evid: Path, head: str, baseline: str) -> None:
        for side, sha in (("head", head), ("base", baseline)):
            self.git("worktree", "add", "-q", "--detach", str(evid / side), sha)

    def test_worktrees_are_kept_only_where_the_step_it_continues_at_can_use_them(self):
        # A review that continues at Review keeps both trees as its checks left them (their installs, the files a
        # check leaves); a review that runs every step gets fresh ones; a drafted review needs none, and keeps those it
        # has until Cleanup. A tree off its commit, or holding a file neither its commit nor a check left (a probe), is
        # remade. Worktrees are git's, so the pin says what to do and leaves each one as it is.
        url, head, baseline = self.real_pr()
        self.pin((url, head, baseline))
        evid = self.root / f"acme-shop-12-{head[:7]}"
        code, out = self.pin((url, head, baseline))
        self.assertIn("worktrees: make head and base, then pr.diff", out)

        self.trees(evid, head, baseline)
        self.outputs(evid, head=head, upto="checked")
        (evid / "checks" / "left.json").write_text(json.dumps({"base": [], "head": ["coverage.txt"]}))
        (evid / "head" / "coverage.txt").write_text("what a check left\n")
        code, out = self.pin((url, head, baseline))
        self.assertIn("continue with its checks", out)
        self.assertIn("worktrees: keep head and base; make pr.diff", out)

        (evid / "head" / "probe.test.js").write_text("a probe left behind\n")
        code, out = self.pin((url, head, baseline))
        self.assertIn("worktrees: keep base; remove head as cleanup.md says, then make it again", out)

        (evid / "head" / "probe.test.js").unlink()
        self.outputs(evid, head=head, upto="drafted")
        code, out = self.pin((url, head, baseline))
        self.assertIn("reuse", out)
        self.assertIn("worktrees: keep head and base until Cleanup", out)

        code, out = self.pin((url, head, self.git("rev-parse", "HEAD~0")))   # the baseline moved to the head itself
        self.assertIn("afresh", out)
        self.assertIn("worktrees: remove head and base as cleanup.md says, then make them again, then pr.diff", out)
        self.assertTrue((evid / "head" / "a.txt").is_file() and (evid / "base" / "a.txt").is_file(),
                        "the pin never removes a worktree itself")

    def batch_file(self, holding: str = "") -> "tuple[Path, dict, str]":
        """The one progress file at the evidence root (or the one whose evidence list holds `holding`): its path, its
        header (the key-value lines before the first section) and its text."""
        files = [f for f in sorted(self.root.glob("progress-*.md")) if holding in f.read_text()]
        self.assertEqual(len(files), 1, [f.name for f in files])
        text = files[0].read_text()
        header = {}
        for line in text.split("\n## ")[0].splitlines():
            key, sep, value = line.partition(": ")
            if sep and key[:1].isalpha() and " " not in key:
                header[key] = value
        return files[0], header, text

    def test_a_batch_keeps_a_progress_file_at_the_evidence_root_and_a_single_review_keeps_none(self):
        # The progress-file shape (Status, Stage, Next, Updated, then sections), with the session's repository, so
        # that the next session there lists it, and each pull request with its step. The session may sit in a
        # subdirectory: the repository is its root.
        self.pin((URL, HEAD, BASE))
        self.assertEqual(list(self.root.glob("progress-*.md")), [], "one pull request is not a batch")
        self.outputs(self.root / "acme-shop-12-cd11698", upto="drafted")
        (self.repo / "src").mkdir()
        code, out = self.pin((URL, HEAD, BASE), ("https://github.com/acme/shop/pull/13", PUSHED, BASE),
                             cwd=self.repo / "src")
        self.assertEqual(code, 0, out)
        path, header, text = self.batch_file()
        self.assertIn(str(path), out)
        self.assertEqual(header["Status"], "active")
        self.assertEqual(header["Stage"], "2 pull requests: 1 drafted, 1 pinned")
        self.assertEqual(header["Next"], "The user types /pr-review again with pull requests 12 and 13 of acme/shop to "
                                         "continue it: 1 of 2 unfinished.")
        self.assertIn("    /pr-review https://github.com/acme/shop/pull/12 https://github.com/acme/shop/pull/13\n", text)
        self.assertRegex(header["Updated"], r"^\d{4}-\d\d-\d\dT\d\d:\d\d$")
        self.assertEqual(header["Repository"], str(self.repo.resolve()))
        self.assertIn("\n## Pull requests\n", text)
        self.assertIn("- acme/shop#12 at cd11698, baseline aea109b: drafted", text)
        self.assertIn("- acme/shop#13 at 0f4e5e9, baseline aea109b: pinned", text)

    def test_the_scripts_bring_the_batch_file_up_to_date_as_each_step_ends_and_the_handover_closes_it(self):
        # Checked when run_checks.py writes checks.json; reviewed when review_payload.py reads a review.json it may
        # still refuse; drafted when it writes the draft; posted when post_reviews.py posts; and done when
        # batch_report.py gives the handover for every pull request the batch pinned. No extra call is needed.
        second = ("https://github.com/acme/shop/pull/13", PUSHED, BASE)
        self.pin((URL, HEAD, BASE), second)
        evid = self.root / "acme-shop-12-cd11698"
        other = self.root / "acme-shop-13-0f4e5e9"
        self.assertEqual(self.batch_file()[1]["Stage"], "2 pull requests: 2 pinned")
        for side in ("base", "head"):
            (evid / side).mkdir()
        done = subprocess.run([sys.executable, str(RUN_CHECKS), "--base", str(evid / "base"), "--head", str(evid / "head"),
                               "--out", str(evid / "checks"), "--slot-dir", str(self.tmp / "slots"),
                               "--check", "test=true"], capture_output=True, text=True, env=self.env)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(self.batch_file()[1]["Stage"], "2 pull requests: 1 checked, 1 pinned")

        (evid / "pr.diff").write_text(DIFF)
        data = dict(review(12, verdict="request changes", findings=[finding("blocking", "a bug", "src/pricing.ts", 6)]))
        data["pr"] = dict(data["pr"], repo="acme/shop", head=HEAD)
        (evid / "review.json").write_text(json.dumps(data))
        payload_args = [sys.executable, str(REVIEW_PAYLOAD), "--diff", str(evid / "pr.diff"), "--review",
                        str(evid / "review.json"), "--viewer", "me", "--out", str(evid / "payload.json"),
                        "--preview", str(evid / "review.md"), "--checks", str(evid / "checks" / "checks.md")]
        refused = subprocess.run(payload_args + ["--event", "APPROVE"], capture_output=True, text=True, env=self.env)
        self.assertEqual(refused.returncode, 1, refused.stderr)
        self.assertEqual(self.batch_file()[1]["Stage"], "2 pull requests: 1 reviewed, 1 pinned")
        built = subprocess.run(payload_args + ["--event", "REQUEST_CHANGES"], capture_output=True, text=True, env=self.env)
        self.assertEqual(built.returncode, 0, built.stderr)
        self.assertEqual(self.batch_file()[1]["Stage"], "2 pull requests: 1 drafted, 1 pinned")

        bin_dir = self.tmp / "bin"
        bin_dir.mkdir()
        (bin_dir / "gh").write_text(FAKE_GH)
        (bin_dir / "gh").chmod(0o755)
        (self.tmp / "state.json").write_text(json.dumps({"viewer": "me", "heads": {"acme/shop#12": HEAD},
                                                         "reviews": {}, "posts": {}}))
        env = dict(self.env, PATH=f"{bin_dir}:{os.environ['PATH']}", FAKE_GH_STATE=str(self.tmp / "state.json"),
                   FAKE_GH_LOG=str(self.tmp / "calls.log"))
        posted = subprocess.run([sys.executable, str(POST_REVIEWS), "--minute", "0.5", str(evid)],
                                capture_output=True, text=True, env=env, timeout=60)
        self.assertEqual(posted.returncode, 0, posted.stdout + posted.stderr)
        self.assertEqual(self.batch_file()[1]["Stage"], "2 pull requests: 1 posted, 1 pinned")

        # Only the final handover closes the batch (--close), and only once every review in it is drafted or posted: a
        # headless run prints the table before its post question, and a review that could not finish stays to be done.
        report = lambda *args: subprocess.run([sys.executable, str(BATCH_REPORT), *args], capture_output=True, text=True,
                                              env=self.env)
        for args, why in (((str(evid), str(other)), "the table before the post question"),
                          (("--close", str(evid)), "a handover for part of the batch"),
                          (("--close", str(evid), str(other)), "a review not yet drafted")):
            done = report(*args)
            self.assertEqual(done.returncode, 0, done.stderr)
            self.assertEqual(self.batch_file()[1]["Status"], "active", f"{why} closes nothing")
        self.outputs(other, head=PUSHED, upto="drafted")
        done = report("--close", str(evid), str(other))
        self.assertEqual(done.returncode, 0, done.stderr)
        header = self.batch_file()[1]
        self.assertEqual((header["Status"], header["Next"]), ("done", "Nothing left: the review handover was given."))

    def test_the_next_step_names_the_batchs_pull_requests_in_a_line_the_resume_note_shows_whole(self):
        # The note shows 200 characters of a field and turns `#` into a space. Three URLs of this very repository run past
        # that (the live run on 7186f58 fell back to pointing at the file), so the next step names the pull requests by
        # number and repository; the exact command stays under Continue in the file.
        repo = lambda n, name="gabriel-tutor/seams": f"https://github.com/{name}/pull/{n}"
        self.pin((repo(5), HEAD, BASE), (repo(6), PUSHED, BASE), (repo(7), MOVED_BASE, BASE),
                 (repo(9, "acme/a-much-longer-repository-name"), HEAD, BASE))
        header = self.batch_file()[1]
        self.assertEqual(header["Next"], "The user types /pr-review again with pull requests 5, 6 and 7 of gabriel-tutor/"
                                         "seams and 9 of acme/a-much-longer-repository-name to continue it: 4 of 4 "
                                         "unfinished.")
        self.assertLessEqual(len(header["Next"]), 200)
        many = [(repo(n), HEAD, BASE) for n in range(100, 140)]
        shutil.rmtree(self.root)
        self.pin(*many)
        self.assertEqual(self.batch_file()[1]["Next"], "The user types the /pr-review command under Continue in this file "
                                                       "again to continue it: 40 of 40 unfinished.")

    def test_each_batch_keeps_its_own_file_and_the_same_pull_requests_typed_again_continue_theirs(self):
        # A second batch in the same repository must not erase the first: each is its own set of pull requests. The
        # same set typed again, in another order or after a push, is the same batch.
        self.pin((URL, HEAD, BASE), ("https://github.com/acme/shop/pull/13", PUSHED, BASE))
        self.pin(("https://github.com/acme/shop/pull/14", HEAD, BASE), ("https://github.com/acme/shop/pull/15", PUSHED, BASE))
        self.assertEqual(len(list(self.root.glob("progress-*.md"))), 2)
        self.assertEqual(self.batch_file("acme-shop-12-")[1]["Status"], "active")
        code, out = self.pin(("https://github.com/acme/shop/pull/13", PUSHED, BASE), (URL + "/", PUSHED, BASE))
        self.assertEqual(code, 0, out)
        self.assertEqual(len(list(self.root.glob("progress-*.md"))), 2)
        self.assertIn("acme-shop-12-0f4e5e9", self.batch_file("acme-shop-13-")[1]["Evidence"])

    def test_one_pull_request_of_a_batch_pinned_again_alone_brings_the_batch_file_up_to_date(self):
        # The base branch moved and the user re-runs one pull request: its drafted review goes, and the batch's file
        # says so rather than still calling it drafted.
        self.pin((URL, HEAD, BASE), ("https://github.com/acme/shop/pull/13", PUSHED, BASE))
        self.outputs(self.root / "acme-shop-12-cd11698", upto="drafted")
        code, out = self.pin((URL, HEAD, BASE))
        self.assertEqual(self.batch_file()[1]["Stage"], "2 pull requests: 1 drafted, 1 pinned", out)
        self.pin((URL, HEAD, MOVED_BASE))
        self.assertEqual(self.batch_file()[1]["Stage"], "2 pull requests: 2 pinned")

    def test_a_pull_request_named_twice_is_a_usage_error_before_anything_is_written(self):
        code, out = self.pin((URL, HEAD, BASE), (URL + "/", HEAD, BASE))
        self.assertEqual(code, 2, out)
        self.assertFalse(self.root.exists())

    def test_the_handover_closes_the_batch_whatever_form_its_evidence_paths_take(self):
        self.pin((URL, HEAD, BASE), ("https://github.com/acme/shop/pull/13", PUSHED, BASE))
        self.outputs(self.root / "acme-shop-12-cd11698", upto="drafted")
        self.outputs(self.root / "acme-shop-13-0f4e5e9", head=PUSHED, upto="posted")
        report = subprocess.run([sys.executable, str(BATCH_REPORT), "--close", "acme-shop-12-cd11698",
                                 "./acme-shop-13-0f4e5e9/"], capture_output=True, text=True, env=self.env,
                                cwd=self.root)
        self.assertEqual(report.returncode, 0, report.stderr)
        self.assertEqual(self.batch_file()[1]["Status"], "done")

    def test_the_scripts_find_each_other_when_python_leaves_their_folder_off_its_path(self):
        # PYTHONSAFEPATH (Python 3.11 and later) keeps a script's own folder off sys.path; the scripts still find
        # evidence.py, and evidence.py still finds run_checks.py, beside them.
        self.pin((URL, HEAD, BASE), ("https://github.com/acme/shop/pull/13", PUSHED, BASE))
        evid = self.root / "acme-shop-12-cd11698"
        for side in ("base", "head"):
            (evid / side).mkdir()
        env = dict(self.env, PYTHONSAFEPATH="1")
        done = subprocess.run([sys.executable, str(RUN_CHECKS), "--base", str(evid / "base"), "--head", str(evid / "head"),
                               "--out", str(evid / "checks"), "--slot-dir", str(self.tmp / "slots"),
                               "--check", "test=true"], capture_output=True, text=True, env=env, cwd=self.tmp)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertTrue(self.batch_file()[1]["Stage"].startswith("2 pull requests: "))
        self.assertIn("1 checked", self.batch_file()[1]["Stage"])
        done = subprocess.run([sys.executable, str(EVIDENCE), "pin", "--pr", URL, HEAD, BASE], capture_output=True,
                              text=True, env=env, cwd=self.repo)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertIn("continue", done.stdout)

    def test_a_progress_file_that_cannot_be_written_never_stops_a_script(self):
        # The file is a pointer: the scripts do their own work first and say nothing of it when it fails.
        self.pin((URL, HEAD, BASE), ("https://github.com/acme/shop/pull/13", PUSHED, BASE))
        path = self.batch_file()[0]
        path.unlink()
        path.mkdir()                                       # in the way of the rewrite
        evid = self.root / "acme-shop-12-cd11698"
        for side in ("base", "head"):
            (evid / side).mkdir()
        done = subprocess.run([sys.executable, str(RUN_CHECKS), "--base", str(evid / "base"), "--head", str(evid / "head"),
                               "--out", str(evid / "checks"), "--slot-dir", str(self.tmp / "slots"),
                               "--check", "test=true"], capture_output=True, text=True, env=self.env)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertTrue((evid / "checks" / "checks.json").is_file())
        report = subprocess.run([sys.executable, str(BATCH_REPORT), str(evid)], capture_output=True, text=True, env=self.env)
        self.assertEqual(report.returncode, 0, report.stderr)
        self.assertIn("| PR |", report.stdout)

    def test_an_evidence_root_other_users_may_write_in_is_refused_and_a_group_one_is_not(self):
        # On a shared machine without $TMPDIR the root sits in /tmp. Other users writing in it could plant a finished
        # review to be reused; a private group's write bit (mkdir under umask 002) lets in nobody else.
        self.root.mkdir()
        self.root.chmod(0o777)
        code, out = self.pin((URL, HEAD, BASE))
        self.assertEqual(code, 1, out)
        self.assertIn("other users", out)
        self.root.chmod(0o775)
        code, out = self.pin((URL, HEAD, BASE))
        self.assertEqual(code, 0, out)

    def test_a_tracked_file_a_check_changed_keeps_its_tree_as_run_checks_would_accept_it(self):
        # An install that rewrites a lockfile, a build that rewrites a generated file: run_checks.py records the change in
        # left.json and runs in that tree again, so the pin keeps it. The first line of git's porcelain starts with a space.
        url, head, baseline = self.real_pr()
        self.pin((url, head, baseline))
        evid = self.root / f"acme-shop-12-{head[:7]}"
        self.trees(evid, head, baseline)
        done = subprocess.run([sys.executable, str(RUN_CHECKS), "--base", str(evid / "base"), "--head", str(evid / "head"),
                               "--out", str(evid / "checks"), "--slot-dir", str(self.tmp / "slots"),
                               "--check", "test=echo more >> a.txt"], capture_output=True, text=True, env=self.env)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(json.loads((evid / "checks" / "left.json").read_text())["head"], ["a.txt"])
        code, out = self.pin((url, head, baseline))
        self.assertIn("worktrees: keep head and base", out)

    def test_what_the_pin_makes_only_its_user_can_write_whatever_the_umask(self):
        # Under umask 002 a directory is group-writable by default. On a machine whose users share a group, a finished
        # review planted in one would be offered at Post, so the evidence and the batch's file are the user's alone.
        done = subprocess.run([sys.executable, str(EVIDENCE), "pin", "--pr", URL, HEAD, BASE,
                               "--pr", "https://github.com/acme/shop/pull/13", PUSHED, BASE],
                              capture_output=True, text=True, env=self.env, cwd=self.repo, preexec_fn=lambda: os.umask(0o002))
        self.assertEqual(done.returncode, 0, done.stderr)
        mode = lambda p: p.stat().st_mode & 0o777
        self.assertEqual(mode(self.root), 0o700)
        self.assertEqual(mode(self.root / "acme-shop-12-cd11698"), 0o700)
        self.assertEqual(mode(self.batch_file()[0]), 0o600)

    def test_a_link_in_place_of_the_root_or_the_marker_or_a_file_in_place_of_the_directory_stops_the_review(self):
        elsewhere = self.tmp / "elsewhere"
        elsewhere.mkdir()
        self.root.symlink_to(elsewhere)
        code, out = self.pin((URL, HEAD, BASE))
        self.assertEqual(code, 1, out)
        self.assertEqual(list(elsewhere.iterdir()), [], "nothing is made through a linked root")
        self.root.unlink()
        self.root.mkdir(mode=0o700)
        evid = self.root / "acme-shop-12-cd11698"
        evid.write_text("a file")
        code, out = self.pin((URL, HEAD, BASE))
        self.assertEqual(code, 1, out)
        self.assertEqual(evid.read_text(), "a file")
        evid.unlink()
        evid.mkdir()
        (elsewhere / "marker").write_text(json.dumps({"url": URL, "candidate": HEAD, "baseline": BASE}))
        (evid / ".seams-pr-review").symlink_to(elsewhere / "marker")
        (evid / "review.json").write_text("{}")
        code, out = self.pin((URL, HEAD, BASE))
        self.assertEqual(code, 1, out)
        self.assertTrue((evid / "review.json").exists())

    def test_a_marker_an_older_version_wrote_starts_the_review_afresh(self):
        # 3.2's marker was free text; nothing says what its review was pinned at, so nothing in it is kept.
        evid = self.root / "acme-shop-12-cd11698"
        evid.mkdir(parents=True)
        (evid / ".seams-pr-review").write_text(f"{URL}\ncandidate {HEAD}\nbaseline {BASE}\n2026-09-24T10:00\n")
        self.outputs(evid)
        code, out = self.pin((URL, HEAD, BASE))
        self.assertEqual(code, 0, out)
        self.assertIn("afresh", out)
        self.assertEqual(sorted(p.name for p in evid.iterdir()), [".seams-pr-review"])


if __name__ == "__main__":
    unittest.main()
