"""The knowledge index (knowledge-layer ticket 01), through knowledge.py's command line, against temporary
repositories: a repository opts in with a knowledge config; the script keeps a tracked index of every raw source in
its inbox and its configured source homes, and reports what is undistilled, changed, missing or not on this machine.
No config means the layer is off."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
SCRIPT = REPO / "plugin" / "skills" / "reconcile" / "scripts" / "knowledge.py"
GIT_ENV = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@e", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@e"}
CONFIG = """# Knowledge

How this repository keeps its product knowledge (Seams' knowledge layer).

```knowledge
inbox: docs/knowledge/raw
index: docs/knowledge/index.jsonl
entries: docs/knowledge/entries
format: markdown
escalation: NEEDS-OWNER
sources: docs/rulings.md
```
"""


def git(cwd, *args):
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=True,
                          env={**os.environ, **GIT_ENV}).stdout.strip()


class KnowledgeTest(unittest.TestCase):

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp()).resolve()
        self.addCleanup(subprocess.run, ["rm", "-rf", str(self.tmp)])
        self.repo = self.tmp / "repo"
        self.repo.mkdir()
        git(self.repo, "init", "-q", "-b", "main")
        (self.repo / "README.md").write_text("r\n")
        git(self.repo, "add", "README.md")
        git(self.repo, "commit", "-qm", "base")

    def run_script(self, *args, cwd=None, code=0):
        done = subprocess.run([sys.executable, "-B", str(SCRIPT), *args], cwd=cwd or self.repo, capture_output=True,
                              text=True, timeout=60, env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
        self.assertEqual(done.returncode, code, done.stdout + done.stderr)
        return done.stdout + done.stderr

    def configure(self, text=CONFIG):
        (self.repo / "docs" / "agents").mkdir(parents=True, exist_ok=True)
        (self.repo / "docs" / "agents" / "knowledge.md").write_text(text)

    def files(self):
        return sorted(str(p.relative_to(self.repo)) for p in self.repo.rglob("*") if p.is_file() and ".git" not in p.parts)

    def test_without_a_config_the_layer_is_off_and_writes_nothing(self):
        before = self.files()
        for args in (("status",), ("status", "--quick"), ("index",)):
            with self.subTest(args=args):
                self.assertIn("no knowledge config", self.run_script(*args))
        self.assertEqual(self.files(), before)

    def test_a_malformed_config_is_reported_in_one_line(self):
        for text, why in (("# Knowledge\n\nno block here\n", "knowledge block"),
                          ("```knowledge\ninbox: raw\n```\n", "index"),
                          ("```knowledge\ninbox: raw\nindex: i.jsonl\nentries: e\ncolour: blue\n```\n", "colour")):
            with self.subTest(why=why):
                self.configure(text)
                out = self.run_script("status", code=2)
                self.assertEqual(len(out.strip().splitlines()), 1, out)
                self.assertIn(why, out)

    def raw(self, rel, text="the owner wants one price per deal\n"):
        path = self.repo / "docs" / "knowledge" / "raw" / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        return path

    def rows(self, root=None):
        index = (root or self.repo) / "docs" / "knowledge" / "index.jsonl"
        return [json.loads(line) for line in index.read_text().splitlines()]

    def test_the_index_has_one_sorted_row_per_source_and_a_second_run_changes_nothing(self):
        self.configure()
        self.raw("2026-09-08-pricing/email.md")
        self.raw("notes.txt", "call notes\n")
        (self.repo / "docs" / "rulings.md").write_text("RULED 8 October: one price\n")
        self.run_script("index")
        rows = self.rows()
        self.assertEqual(sorted(r["path"] for r in rows),
                         ["docs/knowledge/raw/2026-09-08-pricing/email.md", "docs/knowledge/raw/notes.txt",
                          "docs/rulings.md"])
        self.assertEqual([r["id"] for r in rows], sorted(r["id"] for r in rows))
        email = next(r for r in rows if r["path"].endswith("email.md"))
        self.assertTrue(email["id"].startswith("src-"))
        self.assertEqual(email["date"], "2026-09-08")
        self.assertEqual((email["scan"], email["topics"], email["distilled"], email["cited_by"]), ("clean", [], "", []))
        self.assertEqual(len(email["hash"]), 64)
        first = (self.repo / "docs" / "knowledge" / "index.jsonl").read_bytes()
        self.run_script("index")
        self.assertEqual((self.repo / "docs" / "knowledge" / "index.jsonl").read_bytes(), first)

    def test_a_worktree_reads_the_main_checkouts_inbox(self):
        self.configure()
        git(self.repo, "add", "docs/agents/knowledge.md")
        git(self.repo, "commit", "-qm", "config")
        self.raw("2026-10-01-ask.md")
        tree = self.tmp / "tree"
        git(self.repo, "worktree", "add", "-q", str(tree), "-b", "feat")
        self.run_script("index", cwd=tree)
        self.assertEqual([r["path"] for r in self.rows(tree)], ["docs/knowledge/raw/2026-10-01-ask.md"])

    def counts(self, *flags):
        return json.loads(self.run_script("status", "--json", *flags))

    def entry(self, name, text):
        path = self.repo / "docs" / "knowledge" / "entries" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)

    def test_the_report_counts_what_needs_attention(self):
        self.configure()
        a = self.raw("2026-09-01-a.md", "aaaa\n")
        self.raw("2026-09-02-b.md", "bbbb\n")
        self.run_script("index")
        zero = {"new": 0, "undistilled": 0, "changed": 0, "missing": 0, "absent": 0}
        self.assertEqual(self.counts(), {**zero, "undistilled": 2})
        ids = {r["path"]: r["id"] for r in self.rows()}
        self.run_script("distilled", ids["docs/knowledge/raw/2026-09-01-a.md"])
        self.assertEqual(self.counts("--quick"), {**zero, "undistilled": 1})
        self.raw("2026-09-03-c.md", "cccc\n")
        self.entry("price.md", f"sources: {ids['docs/knowledge/raw/2026-09-01-a.md']}, src-0123456789\n")
        a.write_text("aaaa, revised\n")
        (self.repo / "docs" / "knowledge" / "raw" / "2026-09-02-b.md").unlink()
        expected = {"new": 1, "undistilled": 0, "changed": 1, "missing": 1, "absent": 1}
        self.assertEqual(self.counts("--quick"), expected)
        self.assertEqual(self.counts(), expected)
        line = self.run_script("status")
        for words in ("1 new", "1 changed since distilled", "1 cited but missing", "1 not on this machine"):
            with self.subTest(words=words):
                self.assertIn(words, line)

    def test_the_quick_report_never_hashes(self):
        self.configure()
        a = self.raw("2026-09-01-a.md", "aaaa\n")
        self.run_script("index")
        self.run_script("distilled", self.rows()[0]["id"])
        stat = a.stat()
        a.write_text("bbbb\n")                      # the same size; its time put back
        os.utime(a, ns=(stat.st_atime_ns, stat.st_mtime_ns))
        self.assertEqual(self.counts("--quick")["changed"], 0)
        self.assertEqual(self.counts()["changed"], 1)

    def test_distilled_needs_an_indexed_source(self):
        self.configure()
        self.raw("a.md")
        self.run_script("index")
        self.assertIn("src-nothere", self.run_script("distilled", "src-nothere", code=1))

    def test_a_source_holding_a_credential_is_flagged_and_its_value_never_written(self):
        self.configure()
        secrets = ["AKIAIOSFODNN7EXAMPLE", "sk-ant-api03-abcdefghijklmnopqrstuv", "ghp_" + "a1B2" * 9,
                   "Zx9!long-secret-value"]
        self.raw("2026-09-15-chat.md", "hi team\nAPI-Key: AKIAIOSFODNN7EXAMPLE\nkey sk-ant-api03-abcdefghijklmnopqrstuv\n"
                 f"token {secrets[2]}\nsecret: Zx9!long-secret-value\ncall +44 7700 900123\n")
        self.raw("plain.md", "the owner wants a single price\n")
        (self.repo / "docs" / "knowledge" / "raw" / "scan.pdf").write_bytes(b"%PDF-1.7\n\x00\x01binary")
        out = self.run_script("index") + self.run_script("status") + self.run_script("status", "--json")
        rows = {Path(r["path"]).name: r for r in self.rows()}
        self.assertEqual((rows["2026-09-15-chat.md"]["scan"], rows["plain.md"]["scan"], rows["scan.pdf"]["scan"]),
                         ("secrets", "clean", "unscanned"))
        written = out + (self.repo / "docs" / "knowledge" / "index.jsonl").read_text()
        for value in secrets + ["7700 900123"]:
            with self.subTest(value=value):
                self.assertNotIn(value, written)

    def test_an_email_is_scanned_as_text(self):
        self.configure()
        self.raw("2026-07-01-thread.eml", "From: owner\nSubject: keys\n\npassword: hunter2-but-longer\n")
        self.run_script("index")
        self.assertEqual(self.rows()[0]["scan"], "secrets")

    def test_a_moved_source_keeps_its_id_and_its_old_path(self):
        self.configure()
        old = self.raw("july-plan/2026-07-02-plan.md", "the plan\n")
        self.run_script("index")
        before = self.rows()[0]
        self.run_script("topics", before["id"], "pricing, deals,pricing")
        new = self.repo / "docs" / "knowledge" / "raw" / "2026-07-02-july-plan" / "2026-07-02-plan.md"
        new.parent.mkdir(parents=True)
        old.rename(new)
        self.run_script("index")
        (after,) = self.rows()
        self.assertEqual((after["id"], after["path"], after["aka"], after["topics"]),
                         (before["id"], "docs/knowledge/raw/2026-07-02-july-plan/2026-07-02-plan.md",
                          ["docs/knowledge/raw/july-plan/2026-07-02-plan.md"], ["deals", "pricing"]))
        self.assertEqual(self.counts()["absent"], 0)

    def test_a_source_not_on_this_machine_keeps_its_row(self):
        self.configure()
        gone = self.raw("2026-08-01-a.md")
        self.run_script("index")
        gone.unlink()
        self.run_script("index")
        self.assertEqual(len(self.rows()), 1)
        self.assertEqual(self.counts()["absent"], 1)

    def test_only_local_git_reads_run(self):
        self.configure()
        self.raw("a.md")
        bin_ = self.tmp / "bin"
        bin_.mkdir()
        log = self.tmp / "git.log"
        real = subprocess.run(["which", "git"], capture_output=True, text=True).stdout.strip()
        (bin_ / "git").write_text(f'#!/bin/sh\necho "$*" >> {log}\nexec {real} "$@"\n')
        (bin_ / "git").chmod(0o755)
        for args in (("index",), ("status",), ("status", "--quick")):
            done = subprocess.run([sys.executable, "-B", str(SCRIPT), *args], cwd=self.repo, capture_output=True,
                                  text=True, env={**os.environ, "PATH": f"{bin_}{os.pathsep}{os.environ['PATH']}"})
            self.assertEqual(done.returncode, 0, done.stderr)
        verbs = {line.split()[0] for line in log.read_text().splitlines()}
        self.assertEqual(verbs, {"rev-parse"})

    def test_a_corrupt_index_is_reported_in_one_line(self):
        self.configure()
        self.raw("a.md")
        self.run_script("index")
        index = self.repo / "docs" / "knowledge" / "index.jsonl"
        index.write_text(index.read_text() + "{not json\n")
        for args in (("status",), ("status", "--quick"), ("index",)):
            with self.subTest(args=args):
                out = self.run_script(*args, code=2)
                self.assertEqual(len(out.strip().splitlines()), 1, out)
                self.assertIn("index", out)


if __name__ == "__main__":
    unittest.main()
