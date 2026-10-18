"""The knowledge index (knowledge-layer ticket 01), through knowledge.py's command line, against temporary
repositories: a repository opts in with a knowledge config; the script keeps a tracked index of every raw source in
its inbox and its configured source homes, and reports what is new, undistilled, changed, missing or not on this
machine. The tracked index holds only what is safe to share (decision 18); each source's path, size, time and hashes
stay in a gitignored file inside the inbox. No config means the layer is off."""
from __future__ import annotations

import hashlib
import json
import os
import time
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
ZERO = {"new": 0, "undistilled": 0, "changed": 0, "missing": 0, "absent": 0}


def git(cwd, *args):
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=True,
                          env={**os.environ, **GIT_ENV}).stdout.strip()


class KnowledgeTest(unittest.TestCase):

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp()).resolve()
        self.addCleanup(subprocess.run, ["rm", "-rf", str(self.tmp)])
        self.addCleanup(subprocess.run, ["chmod", "-R", "u+rwx", str(self.tmp)])
        self.repo = self.tmp / "repo"
        self.repo.mkdir()
        git(self.repo, "init", "-q", "-b", "main")
        (self.repo / "README.md").write_text("r\n")
        git(self.repo, "add", "README.md")
        git(self.repo, "commit", "-qm", "base")

    # --- helpers ---------------------------------------------------------------------------------------------------

    def run_script(self, *args, cwd=None, code=0, timeout=60):
        done = subprocess.run([sys.executable, "-B", str(SCRIPT), *args], cwd=cwd or self.repo, capture_output=True,
                              text=True, timeout=timeout, env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
        self.assertEqual(done.returncode, code, done.stdout + done.stderr)
        return done.stdout + done.stderr

    def configure(self, text=CONFIG, ignored=True):
        (self.repo / "docs" / "agents").mkdir(parents=True, exist_ok=True)
        (self.repo / "docs" / "agents" / "knowledge.md").write_text(text)
        if ignored:                                  # a configured repository keeps its inbox out of git
            (self.repo / ".gitignore").write_text("docs/knowledge/raw/\n")

    def files(self):
        return sorted(str(p.relative_to(self.repo)) for p in self.repo.rglob("*") if p.is_file() and ".git" not in p.parts)

    def raw(self, rel, text="the owner wants one price per deal\n"):
        path = self.repo / "docs" / "knowledge" / "raw" / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        return path

    def rows(self, root=None):
        index = (root or self.repo) / "docs" / "knowledge" / "index.jsonl"
        return [json.loads(line) for line in index.read_text().splitlines()]

    def local(self):
        """The machine's own file: id -> its path, old paths, size, time and hashes."""
        path = self.repo / "docs" / "knowledge" / "raw" / ".knowledge-local.jsonl"
        return {r["id"]: r for r in (json.loads(line) for line in path.read_text().splitlines())}

    def ids(self):
        return {r["path"]: i for i, r in self.local().items()}

    def scans(self):
        return {Path(self.local()[r["id"]]["path"]).name: r["scan"] for r in self.rows()}

    def counts(self, *flags):
        return json.loads(self.run_script("status", "--json", *flags))

    def entry(self, name, text):
        path = self.repo / "docs" / "knowledge" / "entries" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)

    # --- the switch ------------------------------------------------------------------------------------------------

    def test_without_a_config_the_layer_is_off_and_writes_nothing(self):
        before = self.files()
        for args in (("status",), ("status", "--quick"), ("index",)):
            with self.subTest(args=args):
                self.assertIn("no knowledge config", self.run_script(*args))
        self.assertEqual(self.files(), before)

    def test_a_malformed_config_is_reported_in_one_line(self):
        for text, why in (("# Knowledge\n\nno block here\n", "knowledge block"),
                          ("```knowledge\ninbox: raw\n```\n", "index"),
                          ("```knowledge\ninbox: raw\nindex: i.jsonl\nentries: e\ncolour: blue\n```\n", "colour"),
                          ("```knowledge\ninbox: ../..\nindex: i.jsonl\nentries: e\n```\n", "inbox"),
                          ("```knowledge\ninbox: /\nindex: i.jsonl\nentries: e\n```\n", "inbox"),
                          ("```knowledge\ninbox: raw\nindex: ../outside.jsonl\nentries: e\n```\n", "index"),
                          ("```knowledge\ninbox: raw\nindex: i.jsonl\nentries: e\nsources: ../../etc\n```\n", "sources")):
            with self.subTest(text=text):
                self.configure(text)
                out = self.run_script("index", code=2)
                self.assertEqual(len(out.strip().splitlines()), 1, out)
                self.assertIn(why, out)
        self.assertFalse((self.tmp / "outside.jsonl").exists())

    def test_a_config_that_isnt_utf8_is_reported_in_one_line(self):
        (self.repo / "docs" / "agents").mkdir(parents=True)
        (self.repo / "docs" / "agents" / "knowledge.md").write_bytes(CONFIG.encode() + b"\xff\xfe caf\xe9\n")
        out = self.run_script("status", code=2)
        self.assertEqual(len(out.strip().splitlines()), 1, out)

    # --- the index -------------------------------------------------------------------------------------------------

    def test_the_index_has_one_sorted_row_per_source_and_a_second_run_changes_nothing(self):
        self.configure()
        self.raw("2026-09-08-pricing/email.md")
        self.raw("notes.txt", "call notes\n")
        (self.repo / "docs" / "rulings.md").write_text("RULED 8 October: one price\n")
        self.run_script("index")
        rows = self.rows()
        self.assertEqual(sorted(self.ids()), ["docs/knowledge/raw/2026-09-08-pricing/email.md",
                                              "docs/knowledge/raw/notes.txt", "docs/rulings.md"])
        self.assertEqual([r["id"] for r in rows], sorted(self.local()))
        email = next(r for r in rows if r["id"] == self.ids()["docs/knowledge/raw/2026-09-08-pricing/email.md"])
        self.assertTrue(email["id"].startswith("src-"))
        self.assertEqual(email, {"id": email["id"], "date": "2026-09-08", "topics": [], "scan": "clean",
                                 "cited_by": []})
        self.assertEqual(len(self.local()[email["id"]]["hash"]), 64)
        first = (self.repo / "docs" / "knowledge" / "index.jsonl").read_bytes()
        self.run_script("index")
        self.assertEqual((self.repo / "docs" / "knowledge" / "index.jsonl").read_bytes(), first)

    def test_the_tracked_index_holds_no_name_path_or_hash(self):
        self.configure()
        self.raw("ACME Team - jane.doe@acme.com +44 7700 900123/2026-09-15 chat.md", "hello\n")
        self.run_script("index")
        tracked = (self.repo / "docs" / "knowledge" / "index.jsonl").read_text()
        digest = self.local()[self.rows()[0]["id"]]["hash"]
        for word in ("jane.doe", "acme", "7700", "chat.md", "docs/knowledge/raw", digest):
            with self.subTest(word=word):
                self.assertNotIn(word, tracked)
        self.assertEqual(self.rows()[0]["date"], "2026-09-15")

    def test_a_date_must_be_a_real_date(self):
        self.configure()
        self.raw("2026-13-45-odd/notes-2026-07-02.md")
        self.run_script("index")
        self.assertEqual(self.rows()[0]["date"], "2026-07-02")

    def test_a_worktree_reads_the_main_checkouts_inbox(self):
        self.configure()
        git(self.repo, "add", "docs/agents/knowledge.md")
        git(self.repo, "commit", "-qm", "config")
        self.raw("2026-10-01-ask.md")
        tree = self.tmp / "tree"
        git(self.repo, "worktree", "add", "-q", str(tree), "-b", "feat")
        (tree / "sub").mkdir()
        self.run_script("index", cwd=tree / "sub")
        self.assertEqual(len(self.rows(tree)), 1)
        self.assertEqual(list(self.ids()), ["docs/knowledge/raw/2026-10-01-ask.md"])

    def test_identical_files_are_one_source(self):
        self.configure()
        self.raw("a/2026-06-01-final.md", "the same email\n")
        self.raw("b/2026-06-01-final copy.md", "the same email\n")
        self.run_script("index")
        (only,) = self.local().values()
        self.assertEqual(len(self.rows()), 1)
        self.assertEqual(only["aka"], ["docs/knowledge/raw/b/2026-06-01-final copy.md"])
        self.assertEqual(self.counts()["new"], 0)

    def test_a_moved_source_keeps_its_id_and_its_old_path(self):
        self.configure()
        old = self.raw("july-plan/2026-07-02-plan.md", "the plan\n")
        self.run_script("index")
        (before,) = self.rows()
        self.run_script("topics", before["id"], "Pricing, deals,Pricing")
        new = self.repo / "docs" / "knowledge" / "raw" / "2026-07-02-july-plan" / "2026-07-02-plan.md"
        new.parent.mkdir(parents=True)
        old.rename(new)
        self.run_script("index")
        (after,) = self.rows()
        local = self.local()[after["id"]]
        self.assertEqual((after["id"], after["topics"], local["path"], local["aka"]),
                         (before["id"], ["Pricing", "deals"], "docs/knowledge/raw/2026-07-02-july-plan/2026-07-02-plan.md",
                          ["docs/knowledge/raw/july-plan/2026-07-02-plan.md"]))
        self.assertEqual(self.counts()["absent"], 0)

    def test_a_new_file_at_an_old_path_is_a_new_source_with_its_own_id(self):
        self.configure()
        old = self.raw("2026-07-02-plan.md", "the plan\n")
        self.run_script("index")
        moved = self.repo / "docs" / "knowledge" / "raw" / "kept" / "2026-07-02-plan.md"
        moved.parent.mkdir()
        old.rename(moved)
        self.run_script("index")
        self.raw("2026-07-02-plan.md", "a different plan\n")
        self.run_script("index")
        ids = [r["id"] for r in self.rows()]
        self.assertEqual(len(ids), 2)
        self.assertEqual(len(set(ids)), 2)
        self.assertEqual(len(self.local()), 2)

    def test_a_source_not_on_this_machine_keeps_its_row(self):
        self.configure()
        gone = self.raw("2026-08-01-a.md")
        self.run_script("index")
        gone.unlink()
        self.run_script("index")
        self.assertEqual(len(self.rows()), 1)
        self.assertEqual(self.counts()["absent"], 1)

    def test_a_teammate_without_the_inbox_sees_every_row_as_not_on_this_machine(self):
        self.configure()
        self.raw("2026-08-01-a.md")
        self.run_script("index")
        (self.repo / "docs" / "knowledge" / "raw" / ".knowledge-local.jsonl").unlink()
        (self.repo / "docs" / "knowledge" / "raw" / "2026-08-01-a.md").unlink()
        self.assertEqual(self.counts("--quick"), {**ZERO, "absent": 1})

    def test_symlinks_and_special_files_in_the_inbox_are_not_read(self):
        self.configure()
        secret = self.tmp / "id_rsa"
        secret.write_text("-----BEGIN OPENSSH PRIVATE KEY-----\n")
        inbox = self.repo / "docs" / "knowledge" / "raw"
        inbox.mkdir(parents=True)
        (inbox / "notes.txt").symlink_to(secret)
        (inbox / "outside").symlink_to(self.tmp, target_is_directory=True)
        os.mkfifo(inbox / "pipe")
        self.raw("real.md")
        self.run_script("index", timeout=20)
        self.assertEqual(list(self.ids()), ["docs/knowledge/raw/real.md"])

    def test_an_unreadable_source_is_skipped_without_a_traceback_or_its_name(self):
        self.configure()
        hidden = self.raw("jane-doe-private.md", "x\n")
        hidden.chmod(0)
        self.raw("ok.md")
        out = self.run_script("index") + self.run_script("status")
        self.assertNotIn("Traceback", out)
        self.assertNotIn("jane-doe", out)
        self.assertEqual(list(self.ids()), ["docs/knowledge/raw/ok.md"])

    def test_a_corrupt_index_is_reported_in_one_line(self):
        self.configure()
        self.raw("a.md")
        self.run_script("index")
        index = self.repo / "docs" / "knowledge" / "index.jsonl"
        good = index.read_bytes()
        for bad in (b"{not json\n", b"\xff\xfe\n"):
            index.write_bytes(good + bad)
            for args in (("status",), ("status", "--quick"), ("index",)):
                with self.subTest(bad=bad, args=args):
                    out = self.run_script(*args, code=2)
                    self.assertEqual(len(out.strip().splitlines()), 1, out)
                    self.assertIn("index", out)

    # --- the report ------------------------------------------------------------------------------------------------

    def test_the_report_counts_what_needs_attention(self):
        self.configure()
        a = self.raw("2026-09-01-a.md", "aaaa\n")
        self.raw("2026-09-02-b.md", "bbbb\n")
        self.run_script("index")
        self.assertEqual(self.counts(), {**ZERO, "undistilled": 2})
        ids = self.ids()
        self.run_script("distilled", ids["docs/knowledge/raw/2026-09-01-a.md"])
        self.assertEqual(self.counts("--quick"), {**ZERO, "undistilled": 1})
        self.raw("2026-09-03-c.md", "cccc\n")
        self.entry("price.md", f"sources: {ids['docs/knowledge/raw/2026-09-01-a.md']}, src-0123456789\n")
        self.entry("terms.md", "sources: src-0123456789, src-abcdefabcd\n")
        a.write_text("aaaa, revised\n")
        (self.repo / "docs" / "knowledge" / "raw" / "2026-09-02-b.md").unlink()
        expected = {"new": 1, "undistilled": 0, "changed": 1, "missing": 2, "absent": 1}
        self.assertEqual(self.counts("--quick"), expected)
        self.assertEqual(self.counts(), expected)
        line = self.run_script("status")
        for words in ("1 new", "1 changed since distilled", "2 entries cite a missing source", "1 not on this machine"):
            with self.subTest(words=words):
                self.assertIn(words, line)

    def test_a_change_stays_counted_after_index_runs(self):
        self.configure()
        a = self.raw("2026-09-01-a.md", "aaaa\n")
        self.run_script("index")
        self.run_script("distilled", self.rows()[0]["id"])
        a.write_text("aaaa, revised\n")
        self.run_script("index")
        self.assertEqual(self.counts("--quick")["changed"], 1)
        self.assertEqual(self.counts()["changed"], 1)

    def test_the_quick_report_never_hashes_and_the_full_one_hashes_only_what_moved(self):
        self.configure()
        a = self.raw("2026-09-01-a.md", "aaaa\n")
        self.run_script("index")
        self.run_script("distilled", self.rows()[0]["id"])
        stat = a.stat()
        os.utime(a, ns=(stat.st_atime_ns, stat.st_mtime_ns + 5_000_000_000))   # touched, the same content
        self.assertEqual(self.counts("--quick")["changed"], 1)                 # sizes and times only
        self.assertEqual(self.counts()["changed"], 0)                          # the hash settles it

    def test_cited_by_lists_the_entries_that_cite_a_source_by_its_exact_id(self):
        self.configure()
        self.raw("2026-09-01-a.md")
        self.run_script("index")
        source = self.rows()[0]["id"]
        self.entry("price.md", f"sources: {source}\n")
        self.entry("other.md", f"sources: {source}f\n")
        self.run_script("index")
        self.assertEqual(self.rows()[0]["cited_by"], ["docs/knowledge/entries/price.md"])

    def test_distilled_needs_indexed_sources(self):
        self.configure()
        self.raw("a.md")
        self.run_script("index")
        self.assertIn("src-nothere", self.run_script("distilled", "src-nothere", code=1))
        self.run_script("distilled", code=1)

    # --- secrets ---------------------------------------------------------------------------------------------------

    def test_a_source_holding_a_credential_is_flagged_and_its_value_never_written(self):
        self.configure()
        secrets = ["AKIAIOSFODNN7EXAMPLE", "sk-ant-api03-abcdefghijklmnopqrstuv", "ghp_" + "a1B2" * 9,
                   "Zx9!long-secret-value"]
        self.raw("2026-09-15-chat.md", "hi team\nAPI-Key: AKIAIOSFODNN7EXAMPLE\nkey sk-ant-api03-abcdefghijklmnopqrstuv\n"
                 f"token {secrets[2]}\nsecret: Zx9!long-secret-value\ncall +44 7700 900123\n")
        self.raw("plain.md", "the owner wants a single price\n")
        (self.repo / "docs" / "knowledge" / "raw" / "scan.pdf").write_bytes(b"%PDF-1.7\n\x00\x01binary")
        out = self.run_script("index") + self.run_script("status") + self.run_script("status", "--json")
        scans = self.scans()
        self.assertEqual((scans["2026-09-15-chat.md"], scans["plain.md"], scans["scan.pdf"]),
                         ("secrets", "clean", "unscanned"))
        written = out + (self.repo / "docs" / "knowledge" / "index.jsonl").read_text()
        for value in secrets + ["7700 900123"]:
            with self.subTest(value=value):
                self.assertNotIn(value, written)

    def test_common_credential_formats_are_found_and_plain_prose_is_not(self):
        self.configure()
        found = {"client.md": "client_secret=8f3a9c2e1b7d4f60", "db.env": "DB_PASSWORD=hunter2hunter2",
                 "aws.txt": "aws_secret_access_key = wJalrXUtnFEMI/K7MDENG",
                 "stripe.md": "sk_live_" + "4eC39HqLyjWDarjtT1zdp7dc",
                 "google.md": "AIza" + "SyA1234567890abcdefghijklmnopqrstuv",
                 "slack.md": "https://hooks.slack.com/services/T0/B0/XYZ",
                 "jwt.md": "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U",
                 "twilio.md": "AC" + "0123456789abcdef0123456789abcdef",
                 "url.md": "postgres://admin:s3cretpass@db.example.com/x",
                 "bearer.md": "Authorization: Bearer abcdefghijklmnop1234",
                 "aligned.env": "DB_PASSWORD" + " " * 24 + "= hunter2hunter2",
                 "nextline.yml": "client_secret:\n    8f3a9c2e1b7d4f60a1b2",
                 "bearer-wide.md": "Authorization: Bearer" + " " * 12 + "abcdefghijklmnop1234",
                 "longjwt.md": "eyJhbGciOiJIUzI1NiJ9.eyJ" + "a" * 6000 + ".sig_sig_sig"}
        prose = {"rules.md": "The password requirements are long, and the secret of success is patience.",
                 "secretary.md": "secretary: Mary\nThe token budget is generous."}
        for name, text in {**found, **prose}.items():
            self.raw(name, text + "\n")
        self.run_script("index")
        scans = self.scans()
        for name in found:
            with self.subTest(name=name):
                self.assertEqual(scans[name], "secrets")
        for name in prose:
            with self.subTest(name=name):
                self.assertEqual(scans[name], "clean")

    def test_clean_means_every_byte_was_read(self):
        self.configure()
        big = self.repo / "docs" / "knowledge" / "raw" / "export.txt"
        big.parent.mkdir(parents=True)
        big.write_text("a" * (9 << 20))
        self.raw("2026-07-01-thread.eml", "From: owner\nSubject: keys\nMIME-Version: 1.0\nContent-Type: text/plain\n"
                 "Content-Transfer-Encoding: base64\n\ncGFzc3dvcmQ6IGh1bnRlcjItYnV0LWxvbmdlcgo=\n")
        self.raw("2026-07-02-plain.eml", "From: owner\nSubject: hi\n\nplease keep one price\n")
        for name in ("brief.odt", "deck.pages"):
            (self.repo / "docs" / "knowledge" / "raw" / name).write_bytes(b"PK\x03\x04 zipped " + name.encode())
        self.run_script("index")
        scans = self.scans()
        self.assertEqual(scans["export.txt"], "unscanned")
        self.assertEqual(scans["2026-07-01-thread.eml"], "secrets")
        self.assertEqual(scans["2026-07-02-plain.eml"], "clean")
        self.assertEqual((scans["brief.odt"], scans["deck.pages"]), ("unscanned", "unscanned"))

    def test_distilled_rescans_a_source(self):
        self.configure()
        a = self.raw("2026-09-01-a.md", "no keys here\n")
        self.run_script("index")
        a.write_text("api_key: 0123456789abcdef\n")
        self.run_script("distilled", self.rows()[0]["id"])
        self.assertEqual(self.rows()[0]["scan"], "secrets")

    # --- boundaries ------------------------------------------------------------------------------------------------

    def test_topics_are_kept_as_written(self):
        self.configure()
        self.raw("a.md")
        self.run_script("index")
        source = self.rows()[0]["id"]
        self.run_script("topics", source, "Pricing, HMO licensing,Pricing")
        self.assertEqual(self.rows()[0]["topics"], ["Pricing", "HMO licensing"])
        self.run_script("topics", source, code=1)

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
        self.assertEqual(verbs, {"rev-parse", "check-ignore"})

    def test_an_inbox_git_would_track_is_refused_before_anything_is_written(self):
        self.configure(ignored=False)
        self.raw("2026-09-01-a.md")
        out = self.run_script("index", code=2)
        self.assertIn("gitignore", out)
        self.assertFalse((self.repo / "docs" / "knowledge" / "raw" / ".knowledge-local.jsonl").exists())
        self.assertFalse((self.repo / "docs" / "knowledge" / "index.jsonl").exists())

    # --- the re-review of 5a6a53a ----------------------------------------------------------------------------------

    def test_a_source_whose_tracked_row_went_missing_gets_it_back(self):
        self.configure()
        self.raw("2026-09-01-a.md")
        self.run_script("index")
        (before,) = self.rows()
        (self.repo / "docs" / "knowledge" / "index.jsonl").unlink()
        self.assertEqual(self.counts("--quick")["new"], 1)
        self.run_script("index")
        self.assertEqual([r["id"] for r in self.rows()], [before["id"]])

    def test_old_keys_are_dropped_from_the_tracked_index(self):
        self.configure()
        self.raw("2026-09-01-jane-doe.md")
        self.run_script("index")
        index = self.repo / "docs" / "knowledge" / "index.jsonl"
        row = self.rows()[0]
        index.write_text(json.dumps({**row, "path": "docs/knowledge/raw/2026-09-01-jane-doe.md", "hash": "f" * 64}) + "\n")
        self.run_script("index")
        self.assertNotIn("jane-doe", index.read_text())
        self.assertEqual(set(self.rows()[0]), {"id", "date", "topics", "scan", "cited_by"})

    def test_an_id_reveals_nothing_about_its_file(self):
        self.configure()
        self.raw("2026-09-01-a.md")
        self.run_script("index")
        guess = "src-" + hashlib.sha1(b"docs/knowledge/raw/2026-09-01-a.md").hexdigest()[:10]
        self.assertNotEqual(self.rows()[0]["id"], guess)

    def test_every_message_in_a_mailbox_is_scanned(self):
        self.configure()
        self.raw("2026-07-01-takeout.mbox", "From a@x Mon Jul  1 00:00:00 2026\nSubject: hi\n\nhello\n\n"
                 "From b@x Mon Jul  1 00:00:01 2026\nSubject: keys\nMIME-Version: 1.0\nContent-Type: text/plain\n"
                 "Content-Transfer-Encoding: base64\n\ncGFzc3dvcmQ6IGh1bnRlcjItYnV0LWxvbmdlcgo=\n")
        part = "password: hunter2-but-longer\n".encode("utf-16")
        import base64
        self.raw("2026-07-02-utf16.eml", "From: owner\nMIME-Version: 1.0\nContent-Type: text/plain; charset=utf-16\n"
                 "Content-Transfer-Encoding: base64\n\n" + base64.b64encode(part).decode() + "\n")
        self.run_script("index")
        self.assertEqual(set(self.scans().values()), {"secrets"})

    def test_a_deeply_nested_or_broken_email_is_unscanned_not_a_traceback(self):
        self.configure()
        nested = "".join(f'Content-Type: multipart/mixed; boundary="b{i}"\n\n--b{i}\n' for i in range(3000))
        self.raw("2026-07-03-deep.eml", "From: x\nMIME-Version: 1.0\n" + nested)
        out = self.run_script("index")
        self.assertNotIn("Traceback", out)
        self.assertEqual(self.scans()["2026-07-03-deep.eml"], "unscanned")

    def test_a_git_folder_is_refused_whatever_its_case(self):
        self.configure("```knowledge\ninbox: raw\nindex: .GIT/x.jsonl\nentries: e\n```\n")
        out = self.run_script("index", code=2)
        self.assertIn("index", out)

    def test_rows_of_the_wrong_shape_are_reported_in_one_line(self):
        self.configure()
        self.raw("a.md")
        self.run_script("index")
        index = self.repo / "docs" / "knowledge" / "index.jsonl"
        row = self.rows()[0]
        for bad in ({**row, "id": []}, {**row, "id": 7}, {**row, "topics": "pricing"}):
            index.write_text(json.dumps(bad) + "\n")
            with self.subTest(bad=bad):
                out = self.run_script("status", code=2)
                self.assertEqual(len(out.strip().splitlines()), 1, out)

    def test_distilled_reads_only_a_regular_file_and_never_names_it(self):
        self.configure()
        a = self.raw("2026-09-01-jane-doe.md")
        self.run_script("index")
        source = self.rows()[0]["id"]
        a.unlink()
        a.symlink_to(self.tmp / "elsewhere")
        (self.tmp / "elsewhere").write_text("api_key: 0123456789abcdef\n")
        out = self.run_script("distilled", source, code=1)
        self.assertNotIn("jane-doe", out)
        self.assertNotIn("Traceback", out)

    def test_crafted_text_scans_in_linear_time(self):
        self.configure()
        for name, text in (("dots.txt", "a." * 500_000), ("secrets.txt", "secret" * 200_000),
                           ("jwt.txt", "eyJ" * 300_000), ("scheme.txt", "a+" * 500_000 + "://")):
            self.raw(name, text)
        started = time.monotonic()
        self.run_script("index", timeout=60)
        self.assertLess(time.monotonic() - started, 15)

    # --- moving existing raw material in (ticket 06) ---------------------------------------------------------------

    def scattered(self, rel, text="the owner's email\n", day="2026-08-20"):
        """A raw file outside the inbox, where an owner's material was dropped, last modified on day."""
        path = self.repo / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        moment = time.mktime(time.strptime(day + " 12:00", "%Y-%m-%d %H:%M"))
        os.utime(path, (moment, moment))
        return path

    def contents(self):
        """Every file's bytes under the repository, git's own aside: a move changes where, never what."""
        return sorted(p.read_bytes() for p in self.repo.rglob("*") if p.is_file() and ".git" not in p.parts
                      and p.name != ".knowledge-local.jsonl" and p.name != "index.jsonl")

    def plan(self, *folders, code=0):
        return self.run_script("move", *folders, code=code)

    def agree(self, *folders):
        """The plan, then the yes it ends with, as the user's command would carry it."""
        line = self.plan(*folders).strip().splitlines()[-1]
        self.assertIn("--yes ", line)
        return self.run_script("move", "--yes", line.split("--yes ")[1].split()[0], *folders)

    def test_the_plan_lists_each_folder_its_destination_and_size_and_moves_nothing(self):
        self.configure()
        self.scattered("owner mail/ask.md", "12345\n", day="2026-08-03")
        self.scattered("owner mail/old/note.txt", "abc\n", day="2026-08-20")
        self.scattered("2026-05-01 kickoff/notes.md", "kick\n", day="2026-09-30")
        before = self.files()
        out = self.plan("owner mail", "2026-05-01 kickoff")
        self.assertIn("owner mail -> docs/knowledge/raw/2026-08-20-owner mail/ (2 files, 10 B)", out)
        self.assertIn("2026-05-01 kickoff -> docs/knowledge/raw/2026-05-01 kickoff/ (1 file, 5 B)", out)
        self.assertEqual(self.files(), before)
        self.assertFalse((self.repo / "docs" / "knowledge" / "index.jsonl").exists())

    def test_on_the_yes_the_files_move_and_the_index_records_every_old_path(self):
        self.configure()
        self.scattered("jane doe mail/ask.md", "12345\n", day="2026-08-03")
        self.scattered("jane doe mail/old/2026-07-01 note.txt", "abc\n", day="2026-08-20")
        before = self.contents()
        out = self.agree("jane doe mail")
        self.assertNotIn("jane", out)                                    # the plan named them; the move doesn't
        self.assertIn("moved 2 files", out)
        self.assertFalse((self.repo / "jane doe mail").exists())         # emptied, so its folders are gone
        self.assertEqual(self.contents(), before)                        # nothing deleted, nothing changed
        inbox = "docs/knowledge/raw/2026-08-20-jane doe mail/"
        self.assertEqual({r["path"]: r["aka"] for r in self.local().values()},
                         {inbox + "ask.md": ["jane doe mail/ask.md"],
                          inbox + "old/2026-07-01 note.txt": ["jane doe mail/old/2026-07-01 note.txt"]})
        dates = {self.local()[r["id"]]["path"]: r["date"] for r in self.rows()}
        self.assertEqual(dates, {inbox + "ask.md": "2026-08-03", inbox + "old/2026-07-01 note.txt": "2026-07-01"})
        self.assertNotIn("jane", (self.repo / "docs" / "knowledge" / "index.jsonl").read_text())
        self.assertEqual(self.counts(), {**ZERO, "undistilled": 2})
        self.run_script("index")
        self.assertEqual(len(self.rows()), 2)

    def test_without_the_plans_own_yes_nothing_moves(self):
        self.configure()
        self.scattered("mail/ask.md")
        before = self.files()
        code = self.plan("mail").strip().splitlines()[-1].split("--yes ")[1].split()[0]
        self.run_script("move", "--yes", "0123456789ab", "mail", code=1)
        self.run_script("move", "--yes", code=1)
        self.scattered("mail/late.md", "added after the plan was shown\n")
        out = self.run_script("move", "--yes", code, "mail", code=1)
        self.assertIn("changed", out)
        self.assertEqual(self.files(), sorted(before + ["mail/late.md"]))

    def test_exact_duplicates_are_kept_once_and_every_copy_stays_on_disk(self):
        self.configure()
        self.raw("2026-06-01-final.md", "the final offer\n")
        self.run_script("index")
        (kept,) = self.rows()
        self.scattered("a/offer.md", "the final offer\n")                # already in the inbox
        self.scattered("a/brief.md", "the brief\n")
        self.scattered("b/brief copy.md", "the brief\n")                 # the same as a/brief.md
        self.scattered("b/other.md", "something else\n")
        before = self.contents()
        out = self.plan("a", "b")
        self.assertIn("duplicate, kept once: a/offer.md (the same as docs/knowledge/raw/2026-06-01-final.md)", out)
        self.assertIn("duplicate, kept once: b/brief copy.md (the same as docs/knowledge/raw/2026-08-20-a/brief.md)",
                      out)
        self.assertIn("a -> docs/knowledge/raw/2026-08-20-a/ (1 file, 10 B)", out)
        self.agree("a", "b")
        self.assertEqual(self.contents(), before)                        # the copies stay where they were
        self.assertTrue((self.repo / "a" / "offer.md").exists())
        self.assertTrue((self.repo / "b" / "brief copy.md").exists())
        by_path = {r["path"]: r for r in self.local().values()}
        self.assertEqual(len(by_path), 3)
        self.assertEqual(by_path["docs/knowledge/raw/2026-06-01-final.md"]["aka"], ["a/offer.md"])
        self.assertEqual(by_path["docs/knowledge/raw/2026-08-20-a/brief.md"]["aka"], ["a/brief.md", "b/brief copy.md"])
        self.assertEqual(self.local()[kept["id"]]["path"], "docs/knowledge/raw/2026-06-01-final.md")
        self.assertEqual(self.counts()["new"], 0)

    def test_the_move_is_refused_while_git_would_track_the_inbox(self):
        self.configure(ignored=False)
        self.scattered("mail/ask.md")
        before = self.files()
        self.assertIn("gitignore", self.plan("mail", code=2))
        self.assertIn("gitignore", self.run_script("move", "--yes", "0123456789ab", "mail", code=2))
        self.assertEqual(self.files(), before)

    def test_a_tracked_file_is_listed_and_refused_and_stays_in_git(self):
        self.configure()
        self.scattered("plans/2026-07-02-plan.md", "the plan\n")
        self.scattered("plans/scratch.md", "loose notes\n")
        git(self.repo, "add", "plans/2026-07-02-plan.md")
        git(self.repo, "commit", "-qm", "a tracked plan")
        out = self.plan("plans")
        self.assertIn("tracked by git, refused: plans/2026-07-02-plan.md", out)
        self.assertIn("plans -> docs/knowledge/raw/2026-08-20-plans/ (1 file, 12 B)", out)
        self.agree("plans")
        self.assertTrue((self.repo / "plans" / "2026-07-02-plan.md").exists())
        self.assertEqual(git(self.repo, "status", "--porcelain", "--untracked-files=no"), "")
        self.assertEqual([r["aka"] for r in self.local().values()], [["plans/scratch.md"]])

    def test_a_folder_a_script_reads_stays_and_is_indexed_in_place(self):
        self.configure()
        self.scattered("feeds/prices.csv", "sku,price\n")
        self.scattered("feeds-notes/a.md", "a note\n")                 # a longer name is another folder
        (self.repo / "tools").mkdir()
        self.scattered("data/owner/x.md", "x\n")                         # its parent is what the script reads
        (self.repo / "tools" / "load.py").write_text('ROWS = open("feeds/prices.csv").read()\nALL = glob("data/*")\n')
        (self.repo / "docs" / "how.md").write_text("Drop the owner's mail in feeds-notes/ for now.\n")
        (self.repo / ".gitignore").write_text("docs/knowledge/raw/\nfeeds-notes/\n")
        git(self.repo, "add", "tools/load.py", "docs/how.md", ".gitignore")
        git(self.repo, "commit", "-qm", "a loader")
        out = self.plan("feeds", "feeds-notes", "docs/rulings.md", "data/owner")
        self.assertIn("- feeds stays where it is, read by tools/load.py: indexed in place (the config's sources gain "
                      "it)", out)
        self.assertIn("- docs/rulings.md: refused: not a folder here", out)
        self.assertIn("- data/owner stays where it is, read by tools/load.py", out)
        self.assertIn("feeds-notes -> docs/knowledge/raw/2026-08-20-feeds-notes/", out)   # docs and ignore rules aren't scripts
        self.agree("feeds", "feeds-notes", "docs/rulings.md", "data/owner")
        self.assertTrue((self.repo / "feeds" / "prices.csv").exists())
        self.assertIn("sources: docs/rulings.md, feeds, data/owner\n", (self.repo / "docs" / "agents" / "knowledge.md").read_text())
        self.assertEqual(sorted(r["path"] for r in self.local().values()),
                         ["data/owner/x.md", "docs/knowledge/raw/2026-08-20-feeds-notes/a.md", "feeds/prices.csv"])
        self.assertEqual(self.counts()["new"], 0)
        self.assertIn("stays where it is, already a source the config indexes in place", self.plan("feeds"))

    def test_folders_that_cant_move_are_refused_with_the_reason(self):
        self.configure()
        self.raw("2026-06-01-final.md")
        self.scattered("mail/ask.md")
        self.scattered("mail/sub/b.md", "b\n")
        self.scattered("2026-08-20-dup/x.md", "x\n")
        self.raw("2026-08-20-dup/taken.md", "already there\n")
        (self.repo / "empty").mkdir()
        (self.repo / "link").symlink_to(self.repo / "mail", target_is_directory=True)
        (self.repo / "docs" / "knowledge" / "entries").mkdir(parents=True)
        (self.repo / "docs" / "knowledge" / "entries" / "draft.md").write_text("sources: src-0123456789\n")
        before = self.files()
        out = self.plan("mail", "mail/sub", "../outside", ".git", "docs/knowledge/raw", "docs/knowledge/raw/x",
                        "2026-08-20-dup", "empty", "link", "docs", "docs/knowledge/entries", "nowhere")
        for folder, why in (("mail/sub", "overlaps"), ("../outside", "not inside the repository"),
                            (".git", "not inside the repository"), ("docs/knowledge/raw", "inbox"),
                            ("2026-08-20-dup", "already exists"), ("empty", "no files"), ("link", "not a folder"),
                            ("docs", "knowledge config"), ("docs/knowledge/entries", "knowledge config"),
                            ("nowhere", "not a folder")):
            with self.subTest(folder=folder):
                self.assertIn(f"- {folder}: refused: ", out)
                self.assertIn(why, next(line for line in out.splitlines() if line.startswith(f"- {folder}: ")))
        self.assertIn("mail -> docs/knowledge/raw/2026-08-20-mail/ (2 files", out)
        self.assertEqual(self.files(), before)

    def test_a_source_that_left_the_inbox_comes_back_with_its_id(self):
        self.configure()
        old = self.raw("2026-07-02-plan.md", "the plan\n")
        self.run_script("index")
        (before,) = self.rows()
        (self.repo / "back").mkdir()
        old.rename(self.repo / "back" / "2026-07-02-plan.md")
        self.agree("back")
        (after,) = self.rows()
        self.assertEqual(after["id"], before["id"])
        self.assertEqual(self.local()[after["id"]]["aka"], ["back/2026-07-02-plan.md", "docs/knowledge/raw/2026-07-02-plan.md"])
        self.assertEqual(self.counts()["absent"], 0)

    def test_a_move_that_stops_half_way_records_what_moved_and_deletes_nothing(self):
        self.configure()
        self.scattered("mail/a.md", "a\n")
        self.scattered("mail/sub/jane-doe.md", "b\n")
        before = self.contents()
        line = self.plan("mail").strip().splitlines()[-1]
        (self.repo / "mail" / "sub").chmod(0o555)                        # its file can't leave it
        out = self.run_script("move", "--yes", line.split("--yes ")[1].split()[0], "mail", code=2)
        self.assertIn("stopped after 1 of 2 files", out)
        self.assertNotIn("jane-doe", out)
        self.assertEqual(self.contents(), before)
        self.assertEqual([r["aka"] for r in self.local().values()], [["mail/a.md"]])


if __name__ == "__main__":
    unittest.main()
