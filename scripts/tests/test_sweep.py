"""The worktree sweep (worktree-sweep decisions 1, 2 and 4), through sweep_worktrees.py's command line, against
temporary repositories: `list` offers only worktrees that are clean and whose work is in the base branch (or whose
pull request is merged, for a squash merge), never the main worktree or a locked one; `remove` takes only paths that
still qualify, without force, and deletes a fully merged branch with -d."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
SWEEP = REPO / "plugin" / "skills" / "finishing-a-development-branch" / "scripts" / "sweep_worktrees.py"
GIT_ENV = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@e", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@e"}


def git(cwd, *args):
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=True,
                          env={**os.environ, **GIT_ENV}).stdout.strip()


class SweepTest(unittest.TestCase):

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp()).resolve()
        self.addCleanup(subprocess.run, ["rm", "-rf", str(self.tmp)])
        self.main = self.tmp / "repo"
        self.main.mkdir()
        git(self.main, "init", "-q", "-b", "main")
        (self.main / "a.txt").write_text("a\n")
        git(self.main, "add", "a.txt")
        git(self.main, "commit", "-qm", "base")
        self.bin = self.tmp / "bin"
        self.bin.mkdir()

    def worktree(self, name, commit=True, merge=False):
        path = self.tmp / name
        git(self.main, "worktree", "add", "-q", "-b", name, str(path), "main")
        if commit:
            (path / f"{name}.txt").write_text(name + "\n")
            git(path, "add", f"{name}.txt")
            git(path, "commit", "-qm", name)
        if merge:
            git(self.main, "merge", "-q", "--no-edit", name)
        return path

    def sweep(self, *args, gh=None):
        env = {**os.environ, **GIT_ENV, "PATH": f"{self.bin}{os.pathsep}{os.environ['PATH']}"}
        if gh is not None:                     # a stand-in for the gh CLI: prints what a merged-PR query returns
            (self.bin / "gh").write_text(f"#!/bin/sh\necho '{gh}'\n")
            (self.bin / "gh").chmod(0o755)
        else:
            (self.bin / "gh").write_text("#!/bin/sh\nexit 1\n")
            (self.bin / "gh").chmod(0o755)
        out = subprocess.run([sys.executable, "-B", str(SWEEP), *args, "--repo", str(self.main), "--base", "main"],
                             capture_output=True, text=True, env=env)
        return out

    def listed(self, **kw):
        out = self.sweep("list", **kw)
        self.assertEqual(out.returncode, 0, out.stderr)
        return {Path(c["path"]).name: c for c in json.loads(out.stdout)["candidates"]}

    def test_a_merged_clean_worktree_is_offered_and_the_main_one_never(self):
        self.worktree("done", merge=True)
        listed = self.listed()
        self.assertEqual(set(listed), {"done"})
        self.assertEqual(listed["done"]["reason"], "merged")
        self.assertEqual(listed["done"]["branch"], "done")

    def test_unmerged_dirty_and_locked_worktrees_are_never_offered(self):
        self.worktree("open")                                  # a commit not in main
        dirty = self.worktree("dirty", merge=True)
        (dirty / "scratch.txt").write_text("x\n")              # untracked work
        locked = self.worktree("locked", merge=True)
        git(self.main, "worktree", "lock", str(locked))
        self.assertEqual(self.listed(), {})

    def test_a_squash_merged_branch_is_offered_when_its_pull_request_is_merged(self):
        self.worktree("squashed")                              # its commit never reached main
        self.assertEqual(self.listed(gh="[]"), {})
        self.assertEqual(self.listed(gh='[{"number":7}]')["squashed"]["reason"], "pull request merged")

    def test_remove_takes_an_approved_merged_worktree_and_its_branch(self):
        path = self.worktree("done", merge=True)
        out = self.sweep("remove", str(path))
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertFalse(path.exists())
        self.assertNotIn("done", git(self.main, "branch", "--list", "done"))
        self.assertEqual(json.loads(out.stdout)["removed"], [str(path)])

    def test_remove_refuses_a_path_that_no_longer_qualifies(self):
        path = self.worktree("done", merge=True)
        (path / "late.txt").write_text("work after the list\n")
        out = self.sweep("remove", str(path))
        self.assertTrue(path.exists())
        self.assertEqual(json.loads(out.stdout)["removed"], [])
        self.assertIn("not clean", json.loads(out.stdout)["refused"][str(path)])

    def test_remove_never_touches_the_main_worktree(self):
        out = self.sweep("remove", str(self.main))
        self.assertTrue((self.main / "a.txt").exists())
        self.assertIn(str(self.main), json.loads(out.stdout)["refused"])


if __name__ == "__main__":
    unittest.main()
