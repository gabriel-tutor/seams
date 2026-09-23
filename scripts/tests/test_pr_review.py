"""The pr-review skill's three scripts, through their command lines: run_checks.py (the same checks on
a pull request's baseline and candidate, each result attributed), review_payload.py (the review GitHub
receives: findings anchored inside the diff, the rest in the review's body, only an event GitHub and
the verdict allow) and batch_report.py (ready to merge, per pull request, and a note per author)."""
from __future__ import annotations

import json
import os
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


def run_checks(base: Path, head: Path, out: Path, *checks: str, timeout: float = 30) -> "tuple[int, dict, str]":
    """run_checks.py on two trees; the exit status, checks.json by check name, and checks.md."""
    args = [sys.executable, str(RUN_CHECKS), "--base", str(base), "--head", str(head), "--out", str(out),
            "--timeout", str(timeout)]
    for check in checks:
        args += ["--check", check]
    done = subprocess.run(args, capture_output=True, text=True)
    data = json.loads((out / "checks.json").read_text()) if (out / "checks.json").is_file() else []
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
        code, checks, table = run_checks(self.base, self.head, self.out,
                                         'env=pwd; echo "CI=$CI"; test -t 0 && exit 1; exit 0')
        self.assertEqual(checks["env"]["verdict"], "ok", table)
        base_log = (self.out / "env.base.log").read_text()
        self.assertIn(str(self.base.resolve()), base_log)
        self.assertIn("CI=1", base_log)
        self.assertIn(str(self.head.resolve()), (self.out / "env.head.log").read_text())

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


if __name__ == "__main__":
    unittest.main()
