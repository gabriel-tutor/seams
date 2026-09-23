"""The gate module (plugin/hooks/seams_gate.py), through its public functions.

The gate refuses a change to the project until the current request has a declaration. These
tests drive the module the way the hooks do: a shell command in, a label out; an event and a
ledger in, a decision out. Expected values come from the spec (.scratch/seams-3/spec.md), not
from the code.
"""
from __future__ import annotations

import importlib.util
import os
import stat
import tempfile
import time
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
MODULE = REPO / "plugin" / "hooks" / "seams_gate.py"


def load():
    spec = importlib.util.spec_from_file_location("seams_gate", MODULE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


gate = load()


class ClassifyCommand(unittest.TestCase):
    """classify_command: a label for a shell command that changes files, None otherwise."""

    MUTATIONS = {
        "echo changed > src/file.ts": "a redirect to a file",
        "cat <<'EOF' >> README.md\nline\nEOF": "a redirect to a file",
        "sed -i 's/a/b/' src/file.ts": "sed -i",
        "sed --in-place 's/a/b/' src/file.ts": "sed -i",
        "perl -pi -e 's/a/b/' src/file.ts": "perl -i",
        "rm -rf dist": "rm",
        "mv a.ts b.ts": "mv",
        "cp a.ts b.ts": "cp",
        "touch src/new.ts": "touch",
        "mkdir -p src/lib": "mkdir",
        "tee src/out.txt": "tee",
        "git add -A": "git add",
        "git commit -m 'x'": "git commit",
        "git checkout main": "git checkout",
        "git reset --hard HEAD~1": "git reset",
        "git push origin main": "git push",
        "npm install left-pad": "npm install",
        "pnpm add -D vitest": "pnpm add",
        "pip install requests": "pip install",
        "npx prettier --write .": "a --write flag",
        "npx eslint --fix src": "a --fix flag",
        "curl -o vendor.js https://example.com/x.js": "a download to a file",
        "find . -name '*.tmp' -delete": "find -delete",
        "python3 -c \"open('x.txt','w').write('hi')\"": "an inline program that writes",
        "python3 - <<'PY'\nfrom pathlib import Path\nPath('x').write_text('hi')\nPY": "an inline program that writes",
        "node -e \"require('fs').writeFileSync('x','y')\"": "an inline program that writes",
        "git status && echo done > out.txt": "a redirect to a file",
        "git stash": "git stash",
        "git stash pop": "git stash",
        "git tag v3.0.0": "git tag",
        "git worktree add ../x": "git worktree",
        "git branch -d old": "git branch -d",
        "git -C sub commit -m x": "git commit",
        "sudo rm -rf /tmp/x": "rm",
        "xargs rm < list.txt": "rm",
        "bash -c 'echo hi > out.txt'": "a redirect to a file",
        "FOO=1 touch a": "touch",
        "sudo -u bob rm x": "rm",
        "env FOO=1 rm -rf x": "rm",
        "xargs -I{} rm {} < list.txt": "rm",
        "timeout 5 touch a": "touch",
        "nice -n 10 mkdir out": "mkdir",
        "sed -ni 's/a/b/' f": "sed -i",
        "sed -Ei 's/a/b/' f": "sed -i",
        "perl -0pi -e 's/a/b/' f": "perl -i",
        "gofmt -w .": "a --write flag",
        "shfmt -w scripts": "a --write flag",
        "goimports -w main.go": "a --write flag",
        "perl -e 'open(F, \">out.txt\"); print F 1'": "an inline program that writes",
        "perl -e 'unlink(\"x\")'": "an inline program that writes",
        "ruby -e 'FileUtils.rm_rf(\"dist\")'": "an inline program that writes",
        "ruby -e 'File.delete(\"x\")'": "an inline program that writes",
        "node -e \"require('fs').rm('x', ()=>{})\"": "an inline program that writes",
        "python3 -c \"import os; os.replace('a','b')\"": "an inline program that writes",
        "uv pip install requests": "uv pip install",
        "git tag v3.0.0 -m release": "git tag",
        "git worktree add ../x": "git worktree",
        "git worktree remove ../x": "git worktree",
        "ls | tee listing.txt": "tee",
        # A newline, a subshell or a shell keyword ends one command and starts the next.
        "echo hi\nrm -rf src": "rm",
        "(rm -rf src)": "rm",
        "if true; then rm -rf src; fi": "rm",
        "for f in a b; do rm -f \"$f\"; done": "rm",
        "rm src/a.ts 2>&1": "rm",
    }

    READS = [
        "cat README.md",
        "grep -rn 'gate' plugin/",
        "git status --short",
        "git diff HEAD~1",
        "git log --oneline -5",
        "npm test",
        "npx vitest run",
        "npx tsc --noEmit",
        "python3 -c 'print(1+1)'",
        "python3 - <<'PY'\nprint('hello')\nPY",
        "echo 'a > b' | grep '>'",
        "ls -la 2>/dev/null",
        "npm test 2>&1 | tail -5",
        "make check &>/dev/null",
        "which claude",
        "sed -n '1,20p' README.md",
        "find . -name '*.py'",
        "curl -s https://example.com",
        "git diff main...HEAD",
        "git stash list",
        "git tag -l",
        "git tag --list 'v*'",
        "git worktree list",
        "git branch",
        "git branch -a",
        "git rev-parse HEAD",
        "git merge-base main HEAD",
        "git show HEAD:README.md",
        "grep -rn 'rm -rf' docs/",
        "grep -w foo file",
        "ruby -Ilib test.rb",
        "perl -MList::Util -e 'print 1'",
        "perl -Ilib script.pl",
        "python3 -c \"import shutil; print(shutil.which('x'))\"",
        "uv pip list",
        "uv pip freeze",
        "git tag",
        "git tag -n",
        "git worktree prune",
        "git worktree list",
    ]

    def test_mutations_get_the_label_the_refusal_will_name(self):
        for command, label in self.MUTATIONS.items():
            with self.subTest(command=command):
                self.assertEqual(gate.classify_command(command), label)

    def test_read_only_commands_are_not_mutations(self):
        for command in self.READS:
            with self.subTest(command=command):
                self.assertIsNone(gate.classify_command(command))


class LabelsAreFixedText(unittest.TestCase):
    """A label is a fixed string: nothing typed after a command ever reaches the ledger."""

    def test_labels_come_from_a_fixed_vocabulary(self):
        for command in ["uv pip SECRETWORD x", "npm SECRETWORD", "git SECRETWORD", "pip SECRETWORD"]:
            with self.subTest(command=command):
                label = gate.classify_command(command)
                self.assertTrue(label is None or "SECRETWORD" not in label, label)


class Declarations(unittest.TestCase):
    """A declaration is a Seams skill or one of Matt Pocock's process skills; nothing else."""

    def test_seams_and_matt_pocock_process_skills_declare(self):
        for skill in ["matt-pocock-workflow:grill", "matt-pocock-workflow:trivial",
                      "matt-pocock-workflow:implement", "grilling", "tdd", "diagnosing-bugs",
                      "domain-modeling", "code-review", "codebase-design", "setup-pre-commit",
                      "wayfinder", "to-spec", "implement"]:
            with self.subTest(skill=skill):
                self.assertTrue(gate.is_declaration(skill))

    def test_the_bootstrap_skill_is_not_a_declaration(self):
        # The routing policy itself is not a route: seen live in an eval run, the model invoked it
        # after an "Unknown skill" error and the gate opened. Every other Seams skill still declares.
        self.assertFalse(gate.is_declaration("matt-pocock-workflow:using-matt-pocock-skills"))
        self.assertTrue(gate.is_declaration("matt-pocock-workflow:trivial"))
        self.assertTrue(gate.is_declaration("matt-pocock-workflow:grill"))

    def test_other_plugins_and_domain_skills_do_not(self):
        for skill in ["superpowers:brainstorming", "superpowers:test-driven-development",
                      "frontend-design", "vercel:deploy", "pdf", "", "matt-pocock-workflow"]:
            with self.subTest(skill=skill):
                self.assertFalse(gate.is_declaration(skill))

    def test_a_typed_slash_command_for_a_process_skill_declares(self):
        self.assertEqual(gate.slash_declaration("/to-spec"), "to-spec")
        self.assertEqual(gate.slash_declaration("/matt-pocock-workflow:grill add coupons"),
                         "matt-pocock-workflow:grill")
        self.assertEqual(gate.slash_declaration("/setup-matt-pocock-skills"), "setup-matt-pocock-skills")
        self.assertEqual(gate.slash_declaration("  /wayfinder  "), "wayfinder")

    def test_a_manual_only_seams_skill_typed_by_its_bare_name_declares_under_its_full_name(self):
        # Claude Code runs a plugin skill typed bare (`/pr-review 42`) when no other command has the
        # name. A manual-only skill is only ever typed, so its bare form opens the gate like the
        # namespaced one. Every other bare name stays what it was: the model-invocable Seams skills
        # are declared through the Skill tool under their full names, and a bare name they share with
        # a Superpowers original or a project's own command (`/verification-before-completion`,
        # `/release`) may not be the Seams skill at all. The name must match exactly: a case-insensitive
        # file system finding `PR-REVIEW` is not the skill.
        self.assertEqual(gate.slash_declaration("/pr-review 42"), "matt-pocock-workflow:pr-review")
        self.assertEqual(gate.slash_declaration("/matt-pocock-workflow:pr-review https://github.com/o/r/pull/7"),
                         "matt-pocock-workflow:pr-review")
        self.assertEqual(gate.slash_declaration("/implement"), "implement")   # Matt Pocock's bare name wins, as it does in Claude Code
        for prompt in ["/grill", "/release", "/verification-before-completion", "/using-git-worktrees",
                       "/finishing-a-development-branch", "/receiving-code-review", "/using-matt-pocock-skills",
                       "/PR-REVIEW 42", "/Pr-Review", "/no-such-skill", "/..", "/.", "//etc/passwd"]:
            with self.subTest(prompt=prompt):
                self.assertIsNone(gate.slash_declaration(prompt))

    def test_other_slash_commands_and_plain_prompts_do_not(self):
        for prompt in ["/superpowers:brainstorming", "/compact", "/clear", "add a feature",
                       "run /tdd on this", ""]:
            with self.subTest(prompt=prompt):
                self.assertIsNone(gate.slash_declaration(prompt))


class Continuations(unittest.TestCase):
    """A short go-ahead keeps the request; anything else starts a new one."""

    def test_a_machine_generated_notice_keeps_the_request(self):
        # Claude Code delivers background-task and monitor notices, and a Stop hook's feedback, as
        # user turns; none of them is the user asking for something new. Seen three times in one
        # session: a declared build lost its declaration every time a monitor reported.
        for notice in ("[SYSTEM NOTIFICATION - NOT USER INPUT]\nThis is an automated background-task event",
                       "<task-notification>\n<task-id>abc</task-id>\n</task-notification>",
                       "<system-reminder>\nSomething changed on disk.\n</system-reminder>",
                       "Stop hook feedback:\nSeams done-check: 2 unverified changes"):
            self.assertTrue(gate.is_continuation(notice), notice[:40])
        self.assertFalse(gate.is_continuation("the notification says the build failed, fix it"))

    def test_a_subagents_hand_back_keeps_the_request(self):
        # A background subagent's final report reaches the session as a user turn in this form
        # (Claude Code 2.1.281). In a 15-pull-request review, 21 of the gate's 25 refusals followed
        # one: each hand-back started a new request and dropped the review's declaration.
        hand_back = ('Another Claude session sent a message:\n<agent-message from="a379f038d24b24732">\n'
                     '[Subagent hand-back] The text below is the final report of a subagent this session '
                     'delegated to.\n  #1411: request changes\n</agent-message>')
        self.assertTrue(gate.is_continuation(hand_back))
        self.assertFalse(gate.is_continuation("another claude session sent a message: delete the cache"))

    def test_go_aheads_and_bare_options_continue(self):
        for prompt in ["yes", "Yes.", "y", "ok", "OK!", "okay", "sure", "go ahead", "go on",
                       "continue", "proceed", "do it", "next", "approved", "confirmed",
                       "sounds good", "looks good", "lgtm", "yes please", "yes, do that",
                       "b", "2", "option 2", "carry on", "keep going"]:
            with self.subTest(prompt=prompt):
                self.assertTrue(gate.is_continuation(prompt))

    def test_requests_start_a_new_request(self):
        for prompt in ["add a feature to the cart", "fix the bug in pricing",
                       "please add a login page", "do the auth migration now", "keep the old API",
                       "ok delete the users table", "sure, drop the column", "continue with the refactor",
                       "next: add the endpoint", "please fix the login bug", "right, remove it",
                       "yes but also fix the bug in pricing and the tests", "no", "stop",
                       "why did you do that?", "/to-spec", "ok now change the threshold to 1500",
                       ""]:
            with self.subTest(prompt=prompt):
                self.assertFalse(gate.is_continuation(prompt))


class Ledger(unittest.TestCase):
    """One ledger per session under a root the hooks share; the current request lives in it."""

    def setUp(self):
        self.root = tempfile.mkdtemp()

    def test_a_fresh_session_has_an_empty_request(self):
        ledger = gate.load_ledger("s1", self.root)
        self.assertEqual(ledger["declarations"], [])
        self.assertEqual(ledger["changes"], [])
        self.assertIsNone(ledger["verified_at"])

    def test_a_declaration_survives_a_round_trip(self):
        ledger = gate.load_ledger("s1", self.root)
        gate.add_declaration(ledger, "matt-pocock-workflow:grill", agent_id="a1")
        gate.save_ledger("s1", ledger, self.root)
        again = gate.load_ledger("s1", self.root)
        self.assertEqual([d["skill"] for d in again["declarations"]], ["matt-pocock-workflow:grill"])
        self.assertEqual(again["declarations"][0]["agent"], "a1")

    def test_a_new_request_clears_declarations_changes_and_verification(self):
        ledger = gate.load_ledger("s1", self.root)
        gate.add_declaration(ledger, "tdd")
        gate.add_change(ledger, {"tool": "Edit", "path": "/p/src/a.ts", "doc": False})
        gate.mark_verified(ledger)
        gate.new_request(ledger)
        self.assertEqual(ledger["declarations"], [])
        self.assertEqual(ledger["changes"], [])
        self.assertIsNone(ledger["verified_at"])

    def test_reset_removes_the_session_file(self):
        ledger = gate.load_ledger("s1", self.root)
        gate.add_declaration(ledger, "tdd")
        gate.save_ledger("s1", ledger, self.root)
        gate.reset_ledger("s1", self.root)
        self.assertEqual(gate.load_ledger("s1", self.root)["declarations"], [])

    def test_the_file_and_directory_are_private_to_the_user(self):
        gate.save_ledger("s1", gate.load_ledger("s1", self.root), self.root)
        path = gate.ledger_path("s1", self.root)
        self.assertEqual(stat.S_IMODE(os.stat(path).st_mode), 0o600)
        self.assertEqual(stat.S_IMODE(os.stat(os.path.dirname(path)).st_mode), 0o700)

    def test_a_corrupt_file_reads_as_an_empty_request(self):
        path = gate.ledger_path("s1", self.root)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        Path(path).write_text("{not json")
        self.assertEqual(gate.load_ledger("s1", self.root)["declarations"], [])

    def test_cleanup_removes_ledgers_older_than_seven_days(self):
        for session in ("old", "new"):
            gate.save_ledger(session, gate.load_ledger(session, self.root), self.root)
        old = gate.ledger_path("old", self.root)
        stale = time.time() - 8 * 24 * 3600
        os.utime(old, (stale, stale))
        gate.cleanup_ledgers(self.root, days=7)
        self.assertFalse(os.path.exists(old))
        self.assertTrue(os.path.exists(gate.ledger_path("new", self.root)))

    def test_the_default_root_is_this_users_seams_directory_in_the_temp_dir(self):
        # Per user, the tmux convention (/tmp/tmux-1000): on a shared Linux /tmp a directory owned
        # by another user would make chmod raise EPERM and the gate fail open for everyone else.
        self.assertEqual(os.path.dirname(gate.ledger_path("s1")),
                         os.path.join(tempfile.gettempdir(), f"seams-{os.getuid()}"))


def event(tool: str, cwd: str = "/proj", agent_id: str = None, **tool_input: object) -> dict:
    data = {"session_id": "s1", "cwd": cwd, "hook_event_name": "PreToolUse",
            "tool_name": tool, "tool_input": tool_input}
    if agent_id:
        data["agent_id"] = agent_id
    return data


class ProjectChanges(unittest.TestCase):
    """change_for_event: what the gate treats as a change to the project."""

    def setUp(self):
        self.config = tempfile.mkdtemp()

    def change(self, ev):
        return gate.change_for_event(ev, config_dir=self.config)

    def test_editor_tools_on_project_files_are_changes(self):
        change = self.change(event("Edit", file_path="/proj/src/a.ts", old_string="a", new_string="b"))
        self.assertEqual(change["tool"], "Edit")
        self.assertEqual(change["path"], "/proj/src/a.ts")
        self.assertFalse(change["doc"])
        self.assertEqual(self.change(event("NotebookEdit", notebook_path="/proj/n.ipynb"))["path"], "/proj/n.ipynb")

    def test_relative_paths_resolve_against_the_session_cwd(self):
        change = self.change(event("Write", file_path="README.md", content="x"))
        self.assertEqual(change["path"], "/proj/README.md")

    def test_markdown_is_a_documentation_change(self):
        self.assertTrue(self.change(event("Write", file_path="/proj/docs/spec.md", content="x"))["doc"])
        self.assertTrue(self.change(event("Edit", file_path="/proj/CONTEXT.md"))["doc"])
        self.assertFalse(self.change(event("Edit", file_path="/proj/src/a.ts"))["doc"])

    def test_temp_and_config_directories_are_not_the_project(self):
        temp = os.path.join(tempfile.gettempdir(), "scratch", "x.py")
        for path in [temp, "/tmp/x.py", "/private/tmp/claude-501/x/scratchpad/notes.md",
                     os.path.join(self.config, "projects", "memory", "note.md"), "/dev/null"]:
            with self.subTest(path=path):
                self.assertIsNone(self.change(event("Write", file_path=path, content="x")))

    def test_a_project_that_lives_in_the_temp_dir_is_still_the_project(self):
        cwd = os.path.join(tempfile.gettempdir(), "runs", "workspace")
        change = self.change(event("Edit", cwd=cwd, file_path=os.path.join(cwd, "src", "a.ts")))
        self.assertIsNotNone(change)
        self.assertEqual(change["path"], os.path.join(cwd, "src", "a.ts"))
        scratch = self.change(event("Write", cwd=cwd, file_path=os.path.join(tempfile.gettempdir(), "notes.txt"), content="x"))
        self.assertIsNone(scratch)

    def test_a_worktree_outside_the_cwd_is_still_the_project(self):
        change = self.change(event("Edit", cwd="/proj", file_path="/proj.worktrees/feature/src/a.ts"))
        self.assertIsNotNone(change)

    def test_shell_mutations_are_changes_with_their_label(self):
        change = self.change(event("Bash", command="echo x > src/a.ts"))
        self.assertEqual(change["tool"], "Bash")
        self.assertEqual(change["label"], "a redirect to a file")
        self.assertFalse(change["doc"])
        self.assertIsNone(self.change(event("Bash", command="cat src/a.ts")))

    def test_a_shell_write_confined_to_the_temp_dir_is_not_a_change(self):
        # Edit and Write under the temp dir were never changes; the same work done from a shell
        # was, so a pull-request review writing only its evidence met the gate 25 times.
        t = tempfile.gettempdir()
        evid = f"{t}/seams-pr-review/o-r-12-abc1234"
        for command in [
            f"mkdir -p {evid}/checks",
            f"cat > {evid}/review.json <<'EOF'\n{{\"verdict\": \"approve\"}}\nEOF",
            f"echo done | tee -a {evid}/log.txt",
            f"rm -rf {evid}/head/tests/zz-probe.test.js",
            f"cp {evid}/probes/p.test.js {evid}/head/tests/p.test.js",
            "curl -s -o /dev/null -w '%{http_code}' http://localhost:4101/health",
            f'EVID="{evid}"; mkdir -p "$EVID/checks" && echo ok > "$EVID/checks/x.log"',
            'mkdir -p "${TMPDIR:-/tmp}/seams-pr-review/x"',
            f"git -C /proj worktree add --detach {evid}/head 0123abc",
            f"git -C /proj worktree remove --force {evid}/head",
            "mkdir -p /private/tmp/claude-501/x/scratchpad/forensics",
        ]:
            with self.subTest(command=command):
                self.assertIsNone(self.change(event("Bash", command=command)))

    def test_a_shell_write_that_reaches_the_project_or_cannot_be_placed_is_a_change(self):
        t = tempfile.gettempdir()
        for command, label in [
            ("mkdir -p src/new", "mkdir"),
            (f"cp {t}/p.test.js /proj/tests/p.test.js", "cp"),
            (f"mv /proj/src/a.ts {t}/a.ts", "mv"),
            (f"rm -rf {t}/x /proj/src", "rm"),
            ('mkdir -p "$EVID/checks"', "mkdir"),                     # a variable this command never set
            (f"echo x > {t}/log; rm -rf src", "rm"),
            (f"cat > {t}/notes <<'EOF'\nhello\nEOF\nrm -rf src", "rm"),     # the line after a heredoc runs
            (f"EVID='$HOME/x'; mkdir -p \"$EVID\"", "mkdir"),            # single quotes: a literal $HOME
            (f"npm ci > {t}/install.log", "npm ci"),                   # the install is the write, not the log
            (f"cd {t}/evid/head && npm ci", "npm ci"),
            (f"python3 - <<'EOF'\nopen('{t}/x.json', 'w').write('x')\nEOF", "an inline program that writes"),
            (f"git -C {t}/evid/head checkout -b fix", "git checkout"),
            (f"git -C /proj worktree add -b review {t}/evid/head", "git worktree"),
            (f"sed -i s/a/b/ {t}/x.txt", "sed -i"),                    # in-place editors always count
            (f"rm -rf {t}/evid/*", "rm"),                              # a glob is not placed
            (f"mkdir -p $(mktemp -d)/x", "mkdir"),
        ]:
            with self.subTest(command=command):
                change = self.change(event("Bash", command=command))
                self.assertIsNotNone(change)
                self.assertEqual(change["label"], label)

    def test_a_temp_path_that_leads_into_the_project_is_the_project(self):
        project = tempfile.mkdtemp()               # the session's cwd: the project, wherever it lives
        os.makedirs(os.path.join(project, "src"))
        link = os.path.join(tempfile.mkdtemp(), "proj-link")
        os.symlink(project, link)
        change = self.change(event("Bash", cwd=project, command=f"rm -rf {link}/src"))
        self.assertIsNotNone(change)
        self.assertEqual(change["label"], "rm")

    def test_other_tools_are_not_changes(self):
        self.assertIsNone(self.change(event("Read", file_path="/proj/src/a.ts")))
        self.assertIsNone(self.change(event("Grep", pattern="x")))


class PreToolUseDecision(unittest.TestCase):
    """decide_pre_tool_use: refuse a project change until the request has a declaration."""

    def setUp(self):
        self.config = tempfile.mkdtemp()
        self.ledger = gate.empty_ledger("s1")

    def decide(self, ev):
        return gate.decide_pre_tool_use(ev, self.ledger, config_dir=self.config)

    def test_a_change_without_a_declaration_is_refused_with_the_routes(self):
        decision = self.decide(event("Edit", file_path="/proj/src/a.ts"))
        self.assertEqual(decision["decision"], "deny")
        reason = decision["reason"]
        self.assertIn("Seams gate", reason)
        self.assertIn("/proj/src/a.ts", reason)
        for route in ["diagnosing-bugs", "matt-pocock-workflow:grill", "tdd",
                      "matt-pocock-workflow:implement", "matt-pocock-workflow:trivial"]:
            self.assertIn(route, reason)
        # Scratch work is not a change: the reason says so, so it is not declared as trivial.
        self.assertIn("absolute path under the temp directory needs no declaration", reason)

    def test_a_shell_mutation_without_a_declaration_is_refused_by_its_label(self):
        decision = self.decide(event("Bash", command="sed -i 's/a/b/' src/a.ts"))
        self.assertEqual(decision["decision"], "deny")
        self.assertIn("sed -i", decision["reason"])

    def test_a_change_with_a_declaration_is_allowed_and_recorded(self):
        gate.add_declaration(self.ledger, "tdd")
        decision = self.decide(event("Edit", file_path="/proj/src/a.ts"))
        self.assertEqual(decision["decision"], "allow")
        self.assertEqual(decision["change"]["path"], "/proj/src/a.ts")

    def test_a_non_change_is_allowed_without_a_declaration(self):
        self.assertEqual(self.decide(event("Read", file_path="/proj/src/a.ts"))["decision"], "allow")
        self.assertEqual(self.decide(event("Bash", command="npm test"))["decision"], "allow")
        self.assertEqual(self.decide(event("Write", file_path="/tmp/notes.txt", content="x"))["decision"], "allow")

    def test_a_subagent_is_judged_by_the_same_ledger(self):
        self.assertEqual(self.decide(event("Edit", agent_id="a1", file_path="/proj/src/a.ts"))["decision"], "deny")
        gate.add_declaration(self.ledger, "matt-pocock-workflow:implement")
        self.assertEqual(self.decide(event("Edit", agent_id="a1", file_path="/proj/src/a.ts"))["decision"], "allow")


class StopDecision(unittest.TestCase):
    """decide_stop: a turn that changed non-documentation project files ends only after verification."""

    def setUp(self):
        self.ledger = gate.empty_ledger("s1")
        gate.add_declaration(self.ledger, "tdd")

    def test_an_unverified_code_change_blocks_once_with_the_reason(self):
        gate.add_change(self.ledger, {"tool": "Edit", "path": "/proj/src/a.ts", "doc": False})
        reason = gate.decide_stop(self.ledger, stop_hook_active=False)
        self.assertIsNotNone(reason)
        self.assertIn("Seams done-check", reason)
        self.assertIn("1 unverified change", reason)
        self.assertIn("/proj/src/a.ts", reason)
        self.assertIn("matt-pocock-workflow:verification-before-completion", reason)
        self.assertIn("does not repeat", reason)

    def test_the_second_stop_of_the_turn_is_allowed(self):
        gate.add_change(self.ledger, {"tool": "Edit", "path": "/proj/src/a.ts", "doc": False})
        self.assertIsNone(gate.decide_stop(self.ledger, stop_hook_active=True))

    def test_no_changes_or_documentation_only_are_allowed(self):
        self.assertIsNone(gate.decide_stop(self.ledger, stop_hook_active=False))
        gate.add_change(self.ledger, {"tool": "Write", "path": "/proj/docs/spec.md", "doc": True})
        gate.add_change(self.ledger, {"tool": "Edit", "path": "/proj/CONTEXT.md", "doc": True})
        self.assertIsNone(gate.decide_stop(self.ledger, stop_hook_active=False))

    def test_verification_after_the_last_change_satisfies_it(self):
        gate.add_change(self.ledger, {"tool": "Edit", "path": "/proj/src/a.ts", "doc": False})
        gate.mark_verified(self.ledger)
        self.assertIsNone(gate.decide_stop(self.ledger, stop_hook_active=False))

    def test_a_change_after_verification_needs_verifying_again(self):
        gate.mark_verified(self.ledger)
        gate.add_change(self.ledger, {"tool": "Edit", "path": "/proj/src/b.ts", "doc": False})
        self.assertIn("/proj/src/b.ts", gate.decide_stop(self.ledger, stop_hook_active=False))

    def test_a_shell_mutation_counts_and_is_named_by_its_label(self):
        gate.add_change(self.ledger, {"tool": "Bash", "label": "sed -i", "doc": False})
        reason = gate.decide_stop(self.ledger, stop_hook_active=False)
        self.assertIn("sed -i", reason)

    def test_the_count_covers_every_unverified_file(self):
        for path in ("/proj/src/a.ts", "/proj/src/b.ts", "/proj/src/c.ts"):
            gate.add_change(self.ledger, {"tool": "Edit", "path": path, "doc": False})
        self.assertIn("3 unverified changes", gate.decide_stop(self.ledger, stop_hook_active=False))

    def test_a_commit_after_verification_does_not_need_verifying_again(self):
        gate.add_change(self.ledger, {"tool": "Edit", "path": "/proj/src/a.ts", "doc": False})
        gate.mark_verified(self.ledger)
        gate.add_change(self.ledger, {"tool": "Bash", "label": "git commit", "doc": False})
        gate.add_change(self.ledger, {"tool": "Bash", "label": "git push", "doc": False})
        self.assertIsNone(gate.decide_stop(self.ledger, stop_hook_active=False))

    def test_the_reason_speaks_of_the_request_not_the_turn(self):
        gate.add_change(self.ledger, {"tool": "Edit", "path": "/proj/src/a.ts", "doc": False})
        reason = gate.decide_stop(self.ledger, stop_hook_active=False)
        self.assertNotIn("this turn changed", reason)
        self.assertIn("since the last verification", reason)

    def test_a_ledger_from_an_older_format_reads_as_empty(self):
        root = tempfile.mkdtemp()
        path = gate.ledger_path("s1", root)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        Path(path).write_text('{"version": 1, "session": "s1", "declarations": [{"skill": "tdd"}], '
                              '"changes": [{"tool": "Edit", "path": "/p/a.ts", "doc": false}], "verified_at": null}')
        self.assertEqual(gate.load_ledger("s1", root)["declarations"], [])
        self.assertEqual(gate.LEDGER_VERSION, 2)

    def test_which_skills_count_as_verification(self):
        for skill in ["matt-pocock-workflow:verification-before-completion",
                      "superpowers:verification-before-completion", "verification-before-completion"]:
            with self.subTest(skill=skill):
                self.assertTrue(gate.is_verification(skill))
        for skill in ["tdd", "matt-pocock-workflow:trivial", "superpowers:brainstorming"]:
            with self.subTest(skill=skill):
                self.assertFalse(gate.is_verification(skill))


if __name__ == "__main__":
    unittest.main()
