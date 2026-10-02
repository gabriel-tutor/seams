"""The gate's modules (plugin/hooks/seams_ledger.py, seams_gate.py and seams_shell.py), through their
public functions.

The gate refuses a change to the project until a declaration has routed the work. These
tests drive the module the way the hooks do: a shell command in, a label out; an event and a
ledger in, a decision out. Expected values come from the spec (.scratch/seams-3/spec.md), not
from the code.
"""
from __future__ import annotations

import contextlib
import os
import stat
import sys
import tempfile
import time
import unittest
from unittest import mock
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.dont_write_bytecode = True                 # no __pycache__ in the plugin directory, however this runs
sys.path.insert(0, str(REPO / "plugin" / "hooks"))
import seams_gate as gate  # noqa: E402  (the PreToolUse decision)
import seams_ledger  # noqa: E402  (the ledger, the prompts and the done-check)
import seams_shell as shell  # noqa: E402  (the shell reader)


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
        "echo hi\n> src/a.ts": "a redirect to a file",       # a newline right before the redirect
        # Commands that write, which the classifier once did not know.
        "tar -xf vendor.tar": "tar -x",
        "tar -xzf vendor.tgz -C lib": "tar -x",
        "tar -czf dist.tgz src": "tar -c",
        "unzip vendor.zip -d lib": "unzip",
        "rsync -a /tmp/a/ lib/": "rsync",
        "sort -o sorted.txt words.txt": "sort -o",
        "curl --output=vendor.js https://example.com/x.js": "a download to a file",
        # What a command substitution runs is a command too, in double quotes or backquotes.
        "echo \"$(rm -rf dist)\"": "rm",
        "echo \"`rm -rf dist`\"": "rm",
        "echo `touch src/x`": "touch",
        "V=\"$(git stash)\"": "git stash",
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
        "tar -tf vendor.tar",
        "unzip -l vendor.zip",
        "sort words.txt",
        "echo '$(rm -rf dist)'",                  # single quotes: text, not a command
        "echo $((1 << 2))",
        "V=\"$(git rev-parse HEAD)\"",
    ]

    def test_mutations_get_the_label_the_refusal_will_name(self):
        for command, label in self.MUTATIONS.items():
            with self.subTest(command=command):
                self.assertEqual(shell.classify_command(command), label)

    def test_read_only_commands_are_not_mutations(self):
        for command in self.READS:
            with self.subTest(command=command):
                self.assertIsNone(shell.classify_command(command))


class QuotedOperators(unittest.TestCase):
    """A `>` the shell reads as text is not a redirect; one it reads as a redirect always is.

    Reproduced: `x="$(awk '$1>0' f)"` was refused as "a redirect to a file", because a quote
    opening inside a word, or a quoted `>` inside a command substitution nested in double
    quotes, was read as ending the quote (lean-and-durable ticket 02).
    """

    FALSE_POSITIVES = [
        "x=\"$(awk '$1>0' f)\"",                                      # the reproduced case
        "echo \"$(awk '$1>0' f)\"",
        "export N=\"$(awk '$1>0' f)\"",
        "n=\"$(awk -F, '$3 >= 10 {c++} END {print c}' f.csv)\"",
        "awk '$1>0' f",
        "awk '{ if ($2 > max) max = $2 } END { print max }' data.txt",
        "x=\"a > b\"",
        "git log --format=\"%h > %s\" -5",
        "grep -e\"a > b\" notes.txt",
        # An input redirect reads.
        "sort < in.txt",
        "x=\"$(awk '$1>0' < f)\"",
        "while read -r line; do echo \"$line\"; done < list.txt",
        # A `#` inside a word is text, and one that starts a word opens a comment.
        "echo a#b",
        "echo hi # > out.txt",
        # Arithmetic compares; it redirects nothing.
        "echo $((n > 5))",
        "[ $((a >= b)) -eq 1 ] && echo big",
        # An unquoted heredoc's text is data, even beside a substitution the shell runs.
        "cat <<EOF\nnpm install left-pad\nbuilt on $(date)\nEOF",
    ]

    BYPASSES = {
        "x=\"$(cmd > out)\"": "a redirect to a file",
        "echo \"$(cat a)\" > b": "a redirect to a file",
        "x=\"$(awk '$1>0' f > out)\"": "a redirect to a file",
        "x=\"$(awk '$1>0' f)\" > out": "a redirect to a file",     # an assignment's redirect still creates the file
        "awk '$1>0' f > out": "a redirect to a file",
        "echo \"$(awk '$1>0' f)\" >> log.txt": "a redirect to a file",
        "git log --format=\"%h > %s\" > log.txt": "a redirect to a file",
        # Operators written against each other are each an operator.
        "true;>src/a.ts": "a redirect to a file",
        "echo hi|>src/a.ts": "a redirect to a file",
        "(>src/a.ts)": "a redirect to a file",
        # A `#` inside a word opens no comment, so what follows it still runs.
        "curl https://example.com/a#top > page.html": "a redirect to a file",
        "echo $# > count.txt": "a redirect to a file",
        # A `)` inside quotes does not end a command substitution.
        "echo \"$(echo ')' ; rm -rf src)\"": "rm",
        "x=$(printf '%s)' a; rm -rf src)": "rm",
        # A backslash-newline joins the lines, even inside a word.
        "r\\\nm -rf src": "rm",
        # `$((` not closed by `))` is a command substitution holding a subshell: every shell runs it.
        "x=$((echo a); touch made)": "touch",
        "echo $(( $(rm -rf src) + 1 ))": "rm",
        # Found by the review of 6faea1d, each written by bash and zsh and missed by it.
        # An apostrophe in a comment opens no quote.
        "# Stash what's there\nSTASHED=$(git stash)": "git stash",
        "echo hi # it's\nx=\"$(touch made)\"": "touch",
        "# don't\nx=${y:-$(touch made)}": "touch",
        "# don't\nn=$(( $(rm -rf src) + 1 ))": "rm",
        "# it's\nx=`touch made`": "touch",
        "x=$(true # it's\n) ; rm -rf src ; y=$(echo ')')": "rm",
        # An unquoted heredoc's text runs only its substitutions; its apostrophes are text.
        "cat > /dev/null <<EOF\nWe can't ship until $(date +%F)\nEOF\nrm -rf src # it's rebuilt below": "rm",
        "cat > /dev/null <<EOF\nThis doesn't change `true`.\nEOF\ngit checkout -q -b feature  # it's new": "git checkout",
        "cat > /dev/null <<EOF\nToday's run: $(touch made)\nEOF": "touch",
        # In an ANSI-C quote, `\\'` is an escaped quote.
        "printf $'Don\\'t edit\\n' > src/generated.ts  # it's generated": "a redirect to a file",
        "echo $'\\'' ; rm -rf src ; \\'": "rm",
        "x=$(echo $'\\')' ; rm -rf src)": "rm",
    }

    def test_text_the_shell_reads_as_text_is_not_a_change(self):
        for command in self.FALSE_POSITIVES:
            with self.subTest(command=command):
                self.assertIsNone(shell.classify_command(command))

    def test_a_real_redirect_or_write_in_the_same_shapes_is_still_caught(self):
        for command, label in self.BYPASSES.items():
            with self.subTest(command=command):
                self.assertEqual(shell.classify_command(command), label)


class NestingTooDeepToRead(unittest.TestCase):
    """A command nested far past any real one is refused as unreadable. Reading it would exhaust
    Python's recursion, and a hook that crashes lets the call through; the review of 6faea1d saw
    `rm -rf src` followed by a thousand `$((` pass that way."""

    def test_a_command_nested_too_deeply_to_read_is_refused(self):
        deep = 1000
        for command in ["rm -rf src\n: " + "$((" * deep,
                        "rm -rf src\n: " + "$(( " * deep + "1" + " ))" * deep,
                        "echo " + "$(echo " * deep + "x" + ")" * deep,
                        "eval " * deep + "rm -rf src"]:
            with self.subTest(command=command[:30]):
                self.assertIsNotNone(shell.classify_command(command))
                decision = gate.decide_pre_tool_use(event("Bash", command=command), seams_ledger.empty_ledger("s1"))
                self.assertEqual(decision["decision"], "deny")


class LabelsAreFixedText(unittest.TestCase):
    """A label is a fixed string: nothing typed after a command ever reaches the ledger."""

    def test_labels_come_from_a_fixed_vocabulary(self):
        for command in ["uv pip SECRETWORD x", "npm SECRETWORD", "git SECRETWORD", "pip SECRETWORD"]:
            with self.subTest(command=command):
                label = shell.classify_command(command)
                self.assertTrue(label is None or "SECRETWORD" not in label, label)


class Declarations(unittest.TestCase):
    """A declaration is a Seams skill or one of Matt Pocock's process skills; nothing else."""

    def test_seams_and_matt_pocock_process_skills_declare(self):
        for skill in ["matt-pocock-workflow:grill", "matt-pocock-workflow:trivial",
                      "matt-pocock-workflow:implement", "grilling", "tdd", "diagnosing-bugs",
                      "domain-modeling", "code-review", "codebase-design", "setup-pre-commit",
                      "wayfinder", "to-spec", "implement"]:
            with self.subTest(skill=skill):
                self.assertTrue(seams_ledger.is_declaration(skill))

    def test_the_bootstrap_skill_is_not_a_declaration(self):
        # The routing policy itself is not a route: seen live in an eval run, the model invoked it
        # after an "Unknown skill" error and the gate opened. Every other Seams skill still declares.
        self.assertFalse(seams_ledger.is_declaration("matt-pocock-workflow:using-matt-pocock-skills"))
        self.assertTrue(seams_ledger.is_declaration("matt-pocock-workflow:trivial"))
        self.assertTrue(seams_ledger.is_declaration("matt-pocock-workflow:grill"))

    def test_other_plugins_and_domain_skills_do_not(self):
        for skill in ["superpowers:brainstorming", "superpowers:test-driven-development",
                      "frontend-design", "vercel:deploy", "pdf", "", "matt-pocock-workflow"]:
            with self.subTest(skill=skill):
                self.assertFalse(seams_ledger.is_declaration(skill))

    def test_a_typed_slash_command_for_a_process_skill_declares(self):
        self.assertEqual(seams_ledger.slash_declaration("/to-spec"), "to-spec")
        self.assertEqual(seams_ledger.slash_declaration("/matt-pocock-workflow:grill add coupons"),
                         "matt-pocock-workflow:grill")
        self.assertEqual(seams_ledger.slash_declaration("/setup-matt-pocock-skills"), "setup-matt-pocock-skills")
        self.assertEqual(seams_ledger.slash_declaration("  /wayfinder  "), "wayfinder")

    def test_a_bare_seams_name_is_not_the_prompts_to_read(self):
        # The Seams skills are declared through the Skill tool or their expansion under their full names: a bare
        # name they share with a Superpowers original or a project's own command (`/verification-before-completion`,
        # `/release`) may not be the Seams skill at all. No Seams skill is manual-only, so no bare name is read from
        # the plugin's files either (Seams 4.0 removed that path).
        for prompt in ["/no-such-skill", "/..", "/.", "//etc/passwd"]:
            with self.subTest(prompt=prompt):
                self.assertIsNone(seams_ledger.slash_declaration(prompt))
        self.assertEqual(seams_ledger.slash_declaration("/matt-pocock-workflow:pr-review https://github.com/o/r/pull/7"),
                         "matt-pocock-workflow:pr-review")
        self.assertEqual(seams_ledger.slash_declaration("/implement"), "implement")   # Matt Pocock's bare name wins, as it does in Claude Code
        for prompt in ["/pr-review 42", "/grill", "/release", "/verification-before-completion", "/using-git-worktrees",
                       "/finishing-a-development-branch", "/receiving-code-review", "/using-matt-pocock-skills"]:
            with self.subTest(prompt=prompt):
                self.assertIsNone(seams_ledger.slash_declaration(prompt))

    def test_other_slash_commands_and_plain_prompts_do_not(self):
        for prompt in ["/superpowers:brainstorming", "/compact", "/clear", "add a feature",
                       "run /tdd on this", ""]:
            with self.subTest(prompt=prompt):
                self.assertIsNone(seams_ledger.slash_declaration(prompt))


def expansion(command_name: str, source: str, prompt_id: object = "p1", kind: str = "slash_command") -> dict:
    """A UserPromptExpansion event as Claude Code 2.1.282 sent it (captured 2026-09-25): the command's
    resolved name, so a bare `/grill` arrives as `matt-pocock-workflow:grill`, and the id of the prompt
    that typed it."""
    data = {"session_id": "s1", "hook_event_name": "UserPromptExpansion", "expansion_type": kind,
            "command_name": command_name, "command_args": "", "command_source": source,
            "prompt": "/" + command_name}
    if prompt_id is not None:
        data["prompt_id"] = prompt_id
    return data


def send(ledger: dict, prompt: str, *typed: tuple, prompt_id: object = "p1") -> bool:
    """The user sends a prompt: Claude Code runs the expansion hook once for each skill it expanded,
    then the prompt hook, in that order (seen in the capture above)."""
    for name, source in typed:
        seams_ledger.record_expansion(expansion(name, source, prompt_id), ledger)
    submitted = {"session_id": "s1", "cwd": "/proj", "hook_event_name": "UserPromptSubmit", "prompt": prompt}
    if prompt_id is not None:
        submitted["prompt_id"] = prompt_id
    return seams_ledger.submit_prompt(submitted, ledger)


def declared(ledger: dict) -> list:
    return [d["skill"] for d in ledger["declarations"]]


def gate_open(ledger: dict) -> bool:
    edit = {"session_id": "s1", "cwd": "/proj", "hook_event_name": "PreToolUse", "tool_name": "Edit",
            "tool_input": {"file_path": "/proj/src/a.ts", "old_string": "a", "new_string": "b"}}
    return gate.decide_pre_tool_use(edit, ledger)["decision"] == "allow"


class TypedSkills(unittest.TestCase):
    """A skill the user types is a declaration, recorded from the UserPromptExpansion event that
    expanded it, whatever form it was typed in (ticket 03)."""

    def test_a_typed_process_skill_is_recorded_from_its_expansion(self):
        # Each typed form with the expansion Claude Code sent for it. The prompt's own parse cannot
        # read a bare model-invocable Seams name (`/grill`); the expansion names what actually ran.
        for prompt, name, source in [
                ("/matt-pocock-workflow:grill add coupons", "matt-pocock-workflow:grill", "plugin"),
                ("/grill add coupons", "matt-pocock-workflow:grill", "plugin"),
                ("/pr-review 42", "matt-pocock-workflow:pr-review", "plugin"),
                ("/tdd add a test", "tdd", "userSettings")]:
            with self.subTest(prompt=prompt):
                ledger = seams_ledger.empty_ledger("s1")
                send(ledger, prompt, (name, source))
                self.assertEqual(declared(ledger), [name])
                self.assertTrue(gate_open(ledger))

    def test_a_stacked_command_records_each_process_skill_it_expanded(self):
        # An interactive session expands every stacked skill, each with its own event; the prompt's
        # parse sees only the first word, and cannot read `/grill` or `/pdf` as a route at all.
        ledger = seams_ledger.empty_ledger("s1")
        send(ledger, "/grill /tdd fix the coupon", ("matt-pocock-workflow:grill", "plugin"), ("tdd", "userSettings"))
        self.assertEqual(declared(ledger), ["matt-pocock-workflow:grill", "tdd"])
        ledger = seams_ledger.empty_ledger("s1")
        send(ledger, "/pdf /tdd fix the coupon", ("pdf", "userSettings"), ("tdd", "userSettings"))
        self.assertEqual(declared(ledger), ["tdd"])

    def test_a_bare_model_invocable_seams_name_without_its_event_records_nothing(self):
        # A bare model-invocable Seams name is not the prompt's to read (`/grill`, and `/pr-review` since it became
        # model-invocable): its expansion names it. Without the event, a review still needs no declaration: every
        # write it makes is under the temp directory.
        ledger = seams_ledger.empty_ledger("s1")
        send(ledger, "/pr-review 42")
        self.assertEqual(declared(ledger), [])

    def test_without_the_event_the_prompts_own_parse_still_records_it(self):
        for prompt, name in [("/tdd add a test", "tdd"),
                             ("/matt-pocock-workflow:grill add coupons", "matt-pocock-workflow:grill"),
                             ("/matt-pocock-workflow:pr-review 42", "matt-pocock-workflow:pr-review")]:
            with self.subTest(prompt=prompt):
                ledger = seams_ledger.empty_ledger("s1")
                send(ledger, prompt)
                self.assertEqual(declared(ledger), [name])
        ledger = seams_ledger.empty_ledger("s1")
        send(ledger, "/tdd add a test", ("tdd", "userSettings"))
        self.assertEqual(declared(ledger), ["tdd"], "a skill both expanded and parsed is recorded once")

    def test_an_expansion_after_its_prompt_hook_still_declares_that_request(self):
        # The hooks reference lists UserPromptSubmit before UserPromptExpansion; 2.1.282 ran them the
        # other way round. In either order a typed skill declares the request its own prompt started,
        # and no other.
        ledger = seams_ledger.empty_ledger("s1")
        send(ledger, "/grill add coupons")                    # the prompt hook first: its parse cannot read /grill
        self.assertFalse(gate_open(ledger))
        seams_ledger.record_expansion(expansion("matt-pocock-workflow:grill", "plugin", "p1"), ledger)
        self.assertEqual(declared(ledger), ["matt-pocock-workflow:grill"])
        self.assertTrue(gate_open(ledger))
        send(ledger, "now the label", prompt_id="p2")
        seams_ledger.record_expansion(expansion("tdd", "userSettings", "p1"), ledger)   # a late one from the earlier prompt
        self.assertEqual(declared(ledger), ["matt-pocock-workflow:grill"])
        # Late, a stacked command's expansions replace the route before it and make one route together, whichever
        # skill comes first, even one the route before it already held.
        for first, second in (("matt-pocock-workflow:grill", "tdd"), ("tdd", "matt-pocock-workflow:grill")):
            with self.subTest(first=first):
                seams_ledger.add_declaration(ledger, "tdd")
                send(ledger, "/grill /tdd fix the coupon", prompt_id="p3" + first)
                for name in (first, second, first):
                    seams_ledger.record_expansion(expansion(name, "plugin", "p3" + first), ledger)
                self.assertEqual(declared(ledger), [first, second])

    def test_once_an_expansion_arrived_the_prompts_own_parse_does_not_decide(self):
        # The expansion names what actually ran; the prompt's parse only guesses from the typed word. A
        # project's own `pr-review` is not Seams' manual-only one, another plugin's `code-review` is not
        # Matt Pocock's, and an MCP prompt is no skill at all.
        for prompt, name, source, kind in [("/pr-review 42", "pr-review", "projectSettings", "slash_command"),
                                           ("/code-review 42", "code-review:code-review", "plugin", "slash_command"),
                                           ("/tdd review", "tdd", "mcp", "mcp_prompt")]:
            with self.subTest(prompt=prompt, kind=kind):
                ledger = seams_ledger.empty_ledger("s1")
                seams_ledger.record_expansion(expansion(name, source, "p1", kind=kind), ledger)
                send(ledger, prompt)
                self.assertEqual(declared(ledger), [])
                self.assertFalse(gate_open(ledger))

    def test_a_damaged_ledger_entry_never_stops_a_prompt_or_the_route_it_types(self):
        # The prompt hook fails open: had it raised here, the new request would never have been saved, and
        # the route the next prompt typed would never have replaced the old one.
        ledger = seams_ledger.empty_ledger("s1")
        seams_ledger.add_declaration(ledger, "tdd")
        ledger["declarations"].append("tdd")
        ledger["declarations"].append({"skill": {"not": "a name"}})
        ledger["expanded"] = ["tdd", {"skill": ["tdd"], "prompt": "p2"}, {"skill": "pdf", "prompt": "p2"}]
        self.assertTrue(send(ledger, "delete the old tables", prompt_id="p2"))
        send(ledger, "/grill add coupons", ("matt-pocock-workflow:grill", "plugin"), prompt_id="p3")
        self.assertEqual(declared(ledger), ["matt-pocock-workflow:grill"])
        # Whole lists damaged: neither hook falls over on them, and a typed route still replaces them.
        for damage in ({"expanded": 5}, {"expanded": "tdd"}, {"declarations": True}, {"declarations": 3}):
            with self.subTest(damage=damage):
                ledger = seams_ledger.empty_ledger("s1")
                seams_ledger.add_declaration(ledger, "tdd")
                ledger.update(damage)
                seams_ledger.record_expansion(expansion("pdf", "userSettings", "p3"), ledger)
                send(ledger, "delete the old tables", prompt_id="p4")
                send(ledger, "/tdd add a test", ("tdd", "userSettings"), prompt_id="p5")
                self.assertEqual(declared(ledger), ["tdd"])
                self.assertTrue(gate_open(ledger))

    def test_a_typed_non_process_skill_or_an_mcp_prompt_is_not_a_declaration(self):
        for prompt, name, source in [
                ("/pdf merge these", "pdf", "userSettings"),
                ("/frontend-design:frontend-design a landing page", "frontend-design:frontend-design", "plugin"),
                ("/superpowers:brainstorming coupons", "superpowers:brainstorming", "plugin"),
                ("/using-matt-pocock-skills", "matt-pocock-workflow:using-matt-pocock-skills", "plugin")]:
            with self.subTest(prompt=prompt):
                ledger = seams_ledger.empty_ledger("s1")
                send(ledger, prompt, (name, source))
                self.assertEqual(declared(ledger), [])
                self.assertFalse(gate_open(ledger))
        # An MCP server's prompt is typed as a slash command too; a server can name one `tdd`.
        ledger = seams_ledger.empty_ledger("s1")
        seams_ledger.record_expansion(expansion("tdd", "mcp", kind="mcp_prompt"), ledger)
        send(ledger, "/mcp__docs__tdd review")
        self.assertEqual(declared(ledger), [])
        self.assertFalse(gate_open(ledger))

    def test_an_expansion_declares_only_the_request_its_own_prompt_starts(self):
        ledger = seams_ledger.empty_ledger("s1")
        seams_ledger.record_expansion(expansion("tdd", "userSettings", "p1"), ledger)
        self.assertFalse(gate_open(ledger), "nothing opens before the prompt that typed it is submitted")
        # p1's prompt hook never ran (it failed, or timed out): the next prompt is not declared by it.
        send(ledger, "delete the old tables", prompt_id="p2")
        self.assertEqual(declared(ledger), [])
        self.assertFalse(gate_open(ledger))
        # Without a prompt id there is nothing to tie the expansion to, so it is not kept.
        self.assertFalse(seams_ledger.record_expansion(expansion("tdd", "userSettings", None), ledger))
        send(ledger, "delete the old tables", prompt_id=None)
        self.assertEqual(declared(ledger), [])


class DeclarationLifetime(unittest.TestCase):
    """A declaration holds until another process skill replaces it or the session is cleared (Seams 4.0,
    ADR 0005): a typed reply of any length and a commit leave the next project write allowed."""

    def setUp(self):
        self.ledger = seams_ledger.empty_ledger("s1")
        send(self.ledger, "/matt-pocock-workflow:implement ticket 03", ("matt-pocock-workflow:implement", "plugin"))

    def test_a_typed_reply_of_any_length_keeps_the_route(self):
        for n, prompt in enumerate(["now make the coupon field required", "no",
                                    "use the second approach, and keep the old API working while the "
                                    "migration runs, then drop it in a later ticket " * 5]):
            with self.subTest(prompt=prompt[:30]):
                send(self.ledger, prompt, prompt_id=f"p{n + 2}")
                self.assertEqual(declared(self.ledger), ["matt-pocock-workflow:implement"])
                self.assertTrue(gate_open(self.ledger))

    def test_a_commit_keeps_the_route(self):
        for command in ("git add src/a.ts", "git commit -m 'Ticket 03: the coupon field'"):
            decision = gate.decide_pre_tool_use(event("Bash", command=command), self.ledger)
            self.assertEqual(decision["decision"], "allow")
            seams_ledger.add_change(self.ledger, decision["change"])
        self.assertTrue(gate_open(self.ledger))

    def test_another_process_skill_replaces_the_route(self):
        seams_ledger.add_declaration(self.ledger, "diagnosing-bugs")                      # Claude invokes it
        self.assertEqual(declared(self.ledger), ["diagnosing-bugs"])
        send(self.ledger, "/tdd add a test", ("tdd", "userSettings"), prompt_id="p2")   # the user types one
        self.assertEqual(declared(self.ledger), ["tdd"])
        send(self.ledger, "/grill /tdd fix the coupon", ("matt-pocock-workflow:grill", "plugin"), ("tdd", "userSettings"),
             prompt_id="p3")
        self.assertEqual(declared(self.ledger), ["matt-pocock-workflow:grill", "tdd"], "a stacked command is one route")
        self.assertTrue(gate_open(self.ledger))

    def test_a_skill_that_is_no_route_replaces_nothing(self):
        for skill in ("superpowers:brainstorming", "frontend-design", "matt-pocock-workflow:using-matt-pocock-skills"):
            with self.subTest(skill=skill):
                send(self.ledger, "/" + skill, (skill, "plugin"), prompt_id="p2" + skill)
                self.assertEqual(declared(self.ledger), ["matt-pocock-workflow:implement"])

    def test_clear_and_a_new_session_start_with_none(self):
        root = tempfile.mkdtemp()
        seams_ledger.save_ledger("s1", self.ledger, root)
        self.assertTrue(gate_open(seams_ledger.load_ledger("s1", root)))
        seams_ledger.reset_ledger("s1", root)                    # what SessionStart does on startup and clear
        self.assertFalse(gate_open(seams_ledger.load_ledger("s1", root)))
        self.assertFalse(gate_open(seams_ledger.load_ledger("s2", root)), "another session never shares this one's route")

    def test_nothing_but_a_process_skill_opens_a_session_with_no_route(self):
        ledger = seams_ledger.empty_ledger("s1")
        for n, prompt in enumerate(["yes", "fix the bug in pricing", "/superpowers:brainstorming coupons",
                                    "<task-notification>\n<task-id>b1</task-id>\n</task-notification>"]):
            send(ledger, prompt, prompt_id=f"q{n}")
            self.assertFalse(gate_open(ledger), prompt[:20])
        seams_ledger.add_declaration(ledger, "matt-pocock-workflow:implement", "builder-1")
        self.assertFalse(gate_open(ledger), "a subagent's route never opens the main conversation's")

    def test_a_lasting_route_never_lets_a_read_only_agent_write(self):
        send(self.ledger, "now commit it", prompt_id="p2")
        commit = event("Bash", agent_id="a2", agent_type="matt-pocock-workflow:reviewer", command="git commit -m fix")
        self.assertEqual(gate.decide_pre_tool_use(commit, self.ledger)["decision"], "deny")

    def test_the_done_check_still_asks_for_a_request_that_changed_the_project(self):
        seams_ledger.add_change(self.ledger, {"tool": "Edit", "path": "/proj/src/a.ts", "doc": False})
        seams_ledger.mark_verified(self.ledger)
        self.assertIsNone(seams_ledger.decide_stop(self.ledger, stop_hook_active=False))
        send(self.ledger, "now make the coupon field required", prompt_id="p2")
        self.assertIsNone(seams_ledger.decide_stop(self.ledger, stop_hook_active=False), "nothing changed since the prompt")
        decision = gate.decide_pre_tool_use(event("Edit", file_path="/proj/src/b.ts"), self.ledger)
        seams_ledger.add_change(self.ledger, decision["change"])
        self.assertIn("/proj/src/b.ts", seams_ledger.decide_stop(self.ledger, stop_hook_active=False))
        self.assertIsNone(seams_ledger.decide_stop(self.ledger, stop_hook_active=True), "once per turn")


# A ledger as 3.4.0's hooks wrote it (captured 2026-10-02 from 79e1741's hooks, the paths shortened): the main
# conversation's `implement` typed in prompt q1, a change, a builder's own `tdd`, and a waiting non-route expansion.
LEDGER_340 = """{"version": 2, "session": "s1", "started": 1790954127.286871, "seq": 3,
 "declarations": [{"skill": "matt-pocock-workflow:implement", "at": 1790954127.286873, "seq": 1, "agent": null},
                  {"skill": "tdd", "at": 1790954127.37248, "seq": 3, "agent": "b1"}],
 "changes": [{"tool": "Edit", "path": "/proj/src/a.ts", "doc": false, "at": 1790954127.324008, "seq": 2}],
 "verified_at": null, "verified_seq": 0, "expanded": [{"prompt_id": "q2", "skill": null}], "request_prompt": "q1"}"""


class LedgerFrom340(unittest.TestCase):
    """Upgrading mid-session: 4.0 reads the ledger 3.4.0 wrote, or treats a shape it does not know as empty. It is
    never a reason to refuse: the route it recorded holds as a 4.0 route does."""

    def setUp(self):
        self.root = tempfile.mkdtemp()
        os.makedirs(seams_ledger.ledger_root(self.root), exist_ok=True)

    def written(self, text: str) -> dict:
        Path(seams_ledger.ledger_path("s1", self.root)).write_text(text)
        return seams_ledger.load_ledger("s1", self.root)

    def test_its_route_holds_through_a_typed_reply_and_its_changes_still_count(self):
        ledger = self.written(LEDGER_340)
        self.assertTrue(gate_open(ledger))
        self.assertIn("/proj/src/a.ts", seams_ledger.decide_stop(ledger, stop_hook_active=False))
        send(ledger, "now make the coupon field required", prompt_id="q2")
        seams_ledger.save_ledger("s1", ledger, self.root)
        ledger = seams_ledger.load_ledger("s1", self.root)
        self.assertTrue(gate_open(ledger))
        send(ledger, "/tdd add a test", ("tdd", "userSettings"), prompt_id="q3")
        self.assertEqual([d["skill"] for d in ledger["declarations"] if not d["agent"]], ["tdd"])
        self.assertEqual([(d["skill"], d["agent"]) for d in ledger["declarations"] if d["agent"]], [("tdd", "b1")],
                         "the typed route replaced only the main conversation's")

    def test_a_shape_it_does_not_know_reads_as_empty_and_never_raises(self):
        for text in ('{"version": 1, "declarations": [{"skill": "tdd"}]}', '{"version": 3, "declarations": 5}',
                     "[1, 2]", "{not json", ""):
            with self.subTest(text=text):
                ledger = self.written(text)
                self.assertEqual(ledger["declarations"], [])
                send(ledger, "now the label", prompt_id="q2")
                seams_ledger.add_declaration(ledger, "tdd")
                self.assertTrue(gate_open(ledger))


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
            self.assertTrue(seams_ledger.is_continuation(notice), notice[:40])
        self.assertFalse(seams_ledger.is_continuation("the notification says the build failed, fix it"))

    def test_a_subagents_hand_back_keeps_the_request(self):
        # A background subagent's final report reaches the prompt hook in this form (captured from
        # the hook's own input, Claude Code 2.1.281); the transcript shows it under an "Another
        # Claude session sent a message:" line the hook never sees. In a 15-pull-request review, 21
        # of the gate's 25 refusals followed one: each hand-back dropped the review's declaration.
        hand_back = ('<agent-message from="a9da89eff2d60b60b">\n[Subagent hand-back] The text below is the '
                     'final report of a subagent this session delegated to.\n  done\n</agent-message>')
        self.assertTrue(seams_ledger.is_continuation(hand_back))
        self.assertTrue(seams_ledger.is_continuation("Another Claude session sent a message:\n" + hand_back))
        self.assertFalse(seams_ledger.is_continuation("the agent-message says the build failed, fix it"))

    def test_go_aheads_and_bare_options_continue(self):
        for prompt in ["yes", "Yes.", "y", "ok", "OK!", "okay", "sure", "go ahead", "go on",
                       "continue", "proceed", "do it", "next", "approved", "confirmed",
                       "sounds good", "looks good", "lgtm", "yes please", "yes, do that",
                       "b", "2", "option 2", "carry on", "keep going"]:
            with self.subTest(prompt=prompt):
                self.assertTrue(seams_ledger.is_continuation(prompt))

    def test_requests_start_a_new_request(self):
        for prompt in ["add a feature to the cart", "fix the bug in pricing",
                       "please add a login page", "do the auth migration now", "keep the old API",
                       "ok delete the users table", "sure, drop the column", "continue with the refactor",
                       "next: add the endpoint", "please fix the login bug", "right, remove it",
                       "yes but also fix the bug in pricing and the tests", "no", "stop",
                       "why did you do that?", "/to-spec", "ok now change the threshold to 1500",
                       ""]:
            with self.subTest(prompt=prompt):
                self.assertFalse(seams_ledger.is_continuation(prompt))


class Ledger(unittest.TestCase):
    """One ledger per session under a root the hooks share; the current request lives in it."""

    def setUp(self):
        self.root = tempfile.mkdtemp()

    def test_a_fresh_session_has_an_empty_request(self):
        ledger = seams_ledger.load_ledger("s1", self.root)
        self.assertEqual(ledger["declarations"], [])
        self.assertEqual(ledger["changes"], [])
        self.assertIsNone(ledger["verified_at"])

    def test_a_declaration_survives_a_round_trip(self):
        ledger = seams_ledger.load_ledger("s1", self.root)
        seams_ledger.add_declaration(ledger, "matt-pocock-workflow:grill", agent_id="a1")
        seams_ledger.save_ledger("s1", ledger, self.root)
        again = seams_ledger.load_ledger("s1", self.root)
        self.assertEqual([d["skill"] for d in again["declarations"]], ["matt-pocock-workflow:grill"])
        self.assertEqual(again["declarations"][0]["agent"], "a1")

    def test_a_new_request_clears_changes_and_verification_and_keeps_the_route(self):
        ledger = seams_ledger.load_ledger("s1", self.root)
        seams_ledger.add_declaration(ledger, "tdd")
        seams_ledger.add_change(ledger, {"tool": "Edit", "path": "/p/src/a.ts", "doc": False})
        seams_ledger.mark_verified(ledger)
        seams_ledger.new_request(ledger)
        self.assertEqual([d["skill"] for d in ledger["declarations"]], ["tdd"])
        self.assertEqual(ledger["changes"], [])
        self.assertIsNone(ledger["verified_at"])

    def test_reset_removes_the_session_file(self):
        ledger = seams_ledger.load_ledger("s1", self.root)
        seams_ledger.add_declaration(ledger, "tdd")
        seams_ledger.save_ledger("s1", ledger, self.root)
        seams_ledger.reset_ledger("s1", self.root)
        self.assertEqual(seams_ledger.load_ledger("s1", self.root)["declarations"], [])

    def test_the_file_and_directory_are_private_to_the_user(self):
        seams_ledger.save_ledger("s1", seams_ledger.load_ledger("s1", self.root), self.root)
        path = seams_ledger.ledger_path("s1", self.root)
        self.assertEqual(stat.S_IMODE(os.stat(path).st_mode), 0o600)
        self.assertEqual(stat.S_IMODE(os.stat(os.path.dirname(path)).st_mode), 0o700)

    def test_a_corrupt_file_reads_as_an_empty_request(self):
        path = seams_ledger.ledger_path("s1", self.root)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        Path(path).write_text("{not json")
        self.assertEqual(seams_ledger.load_ledger("s1", self.root)["declarations"], [])

    def test_cleanup_removes_ledgers_older_than_seven_days(self):
        for session in ("old", "new"):
            seams_ledger.save_ledger(session, seams_ledger.load_ledger(session, self.root), self.root)
        old = seams_ledger.ledger_path("old", self.root)
        stale = time.time() - 8 * 24 * 3600
        os.utime(old, (stale, stale))
        seams_ledger.cleanup_ledgers(self.root, days=7)
        self.assertFalse(os.path.exists(old))
        self.assertTrue(os.path.exists(seams_ledger.ledger_path("new", self.root)))

    def test_the_default_root_is_this_users_state_directory_outside_the_temp_and_config_directories(self):
        # A tool call writes the temp directory without a declaration, and an editor tool the config directory, so a
        # ledger in either could be forged (seams-revamp ticket 10). The hooks' own saves create it, private to the user.
        home = os.path.join(tempfile.mkdtemp(), "new-home")
        self.addCleanup(seams_ledger.home_state_dir.cache_clear)
        with mock.patch.dict(os.environ, {"HOME": home}):
            seams_ledger.home_state_dir.cache_clear()
            self.assertEqual(os.path.dirname(seams_ledger.ledger_path("s1")), os.path.join(home, ".local", "state", "seams"))
            ledger = seams_ledger.load_ledger("s1")
            seams_ledger.add_declaration(ledger, "tdd")
            seams_ledger.save_ledger("s1", ledger)
            self.assertEqual(declared(seams_ledger.load_ledger("s1")), ["tdd"])
            self.assertEqual(stat.S_IMODE(os.stat(seams_ledger.ledger_root()).st_mode), 0o700)

    def test_where_the_home_directory_cannot_hold_it_the_root_is_this_users_seams_directory_in_the_temp_dir(self):
        # Per user, the tmux convention (/tmp/tmux-1000): on a shared Linux /tmp a directory owned
        # by another user would make chmod raise EPERM and the gate fail open for everyone else.
        a_file, read_only = os.path.join(tempfile.mkdtemp(), "a-file"), tempfile.mkdtemp()
        Path(a_file).write_text("")
        os.chmod(read_only, 0o500)
        self.addCleanup(os.chmod, read_only, 0o700)
        self.addCleanup(seams_ledger.home_state_dir.cache_clear)
        homes = ["relative/home", f"{a_file}/home"] + ([read_only] if not os.access(read_only, os.W_OK) else [])
        for home in homes:
            with self.subTest(home=home), mock.patch.dict(os.environ, {"HOME": home}):
                seams_ledger.home_state_dir.cache_clear()
                self.assertEqual(os.path.dirname(seams_ledger.ledger_path("s1")),
                                 os.path.join(tempfile.gettempdir(), f"seams-{os.getuid()}"))

    def test_the_temp_dir_is_the_one_tempfile_finds(self):
        # The hooks find it without importing tempfile (seams-revamp ticket 05), and the ledger and the scratch rules
        # must stay where tempfile puts them: the first of $TMPDIR, $TEMP, $TMP and the usual directories this user can
        # write a file in.
        writable, read_only = tempfile.mkdtemp(), tempfile.mkdtemp()
        a_file = os.path.join(writable, "a-file")
        Path(a_file).write_text("")
        os.chmod(read_only, 0o500)
        self.addCleanup(os.chmod, read_only, 0o700)
        self.addCleanup(seams_ledger.temp_dir.cache_clear)
        self.addCleanup(setattr, tempfile, "tempdir", None)
        for env in ({"TMPDIR": writable}, {"TMPDIR": writable + "/"}, {"TMPDIR": os.path.relpath(writable)},
                    {"TMPDIR": read_only}, {"TMPDIR": "/no/such/dir"}, {"TMPDIR": a_file},
                    {"TMPDIR": "", "TEMP": writable}, {"TMP": writable}, {}):
            with self.subTest(env=env), mock.patch.dict(os.environ, env):
                for name in {"TMPDIR", "TEMP", "TMP"} - set(env):
                    os.environ.pop(name, None)
                seams_ledger.temp_dir.cache_clear()
                tempfile.tempdir = None
                self.assertEqual(seams_ledger.temp_dir(), tempfile.gettempdir())

    def test_no_one_can_move_the_temp_dir_by_planting_names_in_it(self):
        # tempfile probes a directory with random names; names another user on a shared /tmp could guess and create
        # first (this process's id and a counter) would push the ledger and the scratch rules somewhere else.
        shared = tempfile.mkdtemp()
        for attempt in range(100):
            Path(shared, f".seams-probe-{os.getpid()}-{attempt}").write_text("")
        self.addCleanup(seams_ledger.temp_dir.cache_clear)
        with mock.patch.dict(os.environ, {"TMPDIR": shared}):
            seams_ledger.temp_dir.cache_clear()
            self.assertEqual(seams_ledger.temp_dir(), shared)


def event(tool: str, cwd: str = "/proj", agent_id: str = None, agent_type: object = None,
          **tool_input: object) -> dict:
    data = {"session_id": "s1", "cwd": cwd, "hook_event_name": "PreToolUse",
            "tool_name": tool, "tool_input": tool_input}
    if agent_id:
        data["agent_id"] = agent_id
    if agent_type is not None:
        data["agent_type"] = agent_type
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
            # A heredoc's text is data: lines that read like commands are not run.
            f"cat > {evid}/notes.md <<'EOF'\nnpm install left-pad\ngit commit -m fix\ntouch x\nEOF",
            f"cat > {evid}/a.md <<-EOF\n\trm -rf src\n\tEOF",
            f"find {evid} -name '*.log' -delete",
            f"sort -o {evid}/sorted.txt {evid}/words.txt",
            f"cat > {evid}/y.md <<'EOF'\nrun $(rm -rf src) to break it\nEOF",   # a quoted heredoc is literal
            f'A={evid}/x; rm -rf "$A" $A',
            # A word may join quoted and bare parts, as the shell reads it (review of 6faea1d).
            f'EVID={evid}; echo ok > "$EVID"/log.txt',
            f'EVID={evid}; mkdir -p "$EVID"/checks && cp "$EVID"/a.log "$EVID"/checks/',
            f"mkdir -p '{evid}'/probes",
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
            # Found by the review of 3.2.1: each once let a write into the project through.
            (f"find {t} -maxdepth 0 -exec touch /proj/f \\;", "find -exec touch"),   # -exec writes where it likes
            (f"find {t} -name '*.log' -exec rm {{}} \\;", "find -exec rm"),
            ('rm -rf "${PROJ_ROOT:-/tmp/x}/src"', "rm"),               # an unknown variable, whatever its default
            (f"cp --target-directory=/proj {t}/x", "cp"),               # a target attached to its option
            (f"cp -t/proj {t}/x", "cp"),
            (f"git -C /proj worktree add {t}/evid/head", "git worktree"),          # makes a branch named head
            (f"git -C /proj worktree add {t}/evid/head main", "git worktree"),
            (f"echo hi\n> /proj/src/a.ts", "a redirect to a file"),
            (f"f={t}/x; for f in /proj/src/*; do rm \"$f\"; done", "rm"),         # the loop rebinds f
            (f"f={t}/x; read -r f < list.txt; rm \"$f\"", "rm"),
            (f"f={t}/x; unset f; rm \"$f\"", "rm"),
            ("rm -rf ~/.claude/settings.json", "rm"),                   # scratch means the temp directory only
            ('rm -rf "$HOME/.claude/projects"', "rm"),
            (f"echo \"<<EOF\"\nrm -rf src\nEOF", "rm"),                 # a quoted << opens no heredoc
            (f"cat > {t}/x <<EOF\nrm -rf src", "rm"),                   # an unterminated heredoc hides nothing
            (f"tar -xf {t}/v.tar -C /proj", "tar -x"),
            (f"unzip {t}/v.zip -d /proj", "unzip"),
            (f"rsync -a {t}/a/ /proj/b/", "rsync"),
            (f"sort -o /proj/o {t}/src", "sort -o"),
            # How the shell expands a word, which placing a path must follow.
            (f"cat > {t}/x <<EOF\n$(rm -rf src)\nEOF", "rm"),          # an unquoted heredoc runs $(...)
            (f"cat > {t}/x <<EOF\n`rm -rf src`\nEOF", "rm"),
            (f'A="{t}/x /proj/src"; rm -rf $A', "rm"),                  # unquoted, the value splits in two
            (f"IFS=x; A={t}/proxj; rm -rf $A", "rm"),                   # IFS decides where it splits
            (f"rm -rf {t}/{{x,../../proj}}", "rm"),                     # brace expansion
            (f'A={t}/x; A+=/../../proj; rm -rf "$A"', "rm"),            # an append is not followed
            ('eval "rm -rf src"', "rm"),                                # eval runs its text
            ("\\rm -rf src", "rm"),                                     # a backslash before the name
            ('EVID=/tmp/x; echo x > "$EVID"/../../proj/src/a.ts', "a redirect to a file"),   # the parts join first
            (f'EVID={t}/x; rm -rf "$EVID"/*', "rm"),                     # a bare part's glob
            (f'EVID={t}/x; rm -rf "$EVID"/$(echo src)', "rm"),          # a bare part's substitution
        ]:
            with self.subTest(command=command):
                change = self.change(event("Bash", command=command))
                self.assertIsNotNone(change)
                self.assertEqual(change["label"], label)

    def test_the_claude_config_directory_is_not_scratch_for_a_shell_write(self):
        # Edit and Write may keep notes there; a shell command deleting the user's settings is not scratch.
        change = gate.change_for_event(event("Bash", command="rm -rf /home/u/.claude/settings.json"),
                                       config_dir="/home/u/.claude")
        self.assertIsNotNone(change)
        self.assertEqual(change["label"], "rm")
        self.assertIsNone(gate.change_for_event(event("Write", file_path="/home/u/.claude/memory/n.md", content="x"),
                                                config_dir="/home/u/.claude"))

    def test_the_claude_config_directory_is_not_scratch_for_a_shell_write_inside_the_temp_directory_either(self):
        # self.config is a mkdtemp, so it lies under the temp directory, where a CI job's or an eval run's config
        # directory lies too: the temp directory's rule must not reach into it.
        change = gate.change_for_event(event("Bash", command=f"rm -rf {self.config}/settings.json"),
                                       config_dir=self.config)
        self.assertIsNotNone(change)
        self.assertEqual(change["label"], "rm")
        # Fail closed (decision 47): where the config directory contains the scratchpad, the scratchpad is gated too.
        pad = os.path.join(self.config, "scratchpad")
        ev = event("Bash", command=f"rm -rf {pad}/x.log")
        ev["scratchpad_dir"] = pad
        self.assertIsNotNone(gate.change_for_event(ev, config_dir=self.config))

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


class ScratchpadDir(unittest.TestCase):
    """The hook input's `scratchpad_dir` (Claude Code 2.1.257 and later) is scratch, alongside the
    temp directories; the session's working directory never is (ticket 02)."""

    SCRATCHPAD = "/seams-test-scratchpad/proj/s1/scratchpad"   # outside every temp root: only the field

    def setUp(self):
        self.config = tempfile.mkdtemp()

    def change(self, tool, scratchpad=None, **tool_input):
        ev = event(tool, **tool_input)
        if scratchpad is not None:
            ev["scratchpad_dir"] = scratchpad
        return gate.change_for_event(ev, config_dir=self.config)

    def test_a_write_under_the_scratchpad_is_scratch(self):
        s = self.SCRATCHPAD
        self.assertIsNone(self.change("Write", s, file_path=f"{s}/notes.md", content="x"))
        self.assertIsNone(self.change("Edit", s, file_path=f"{s}/probe.py"))
        self.assertIsNone(self.change("Bash", s, command=f"mkdir -p {s}/evid && echo ok > {s}/evid/log.txt"))
        self.assertIsNone(self.change("Monitor", s, command=f"tail -f /proj/server.log > {s}/copy.log"))

    def test_without_the_field_the_temp_rules_apply_unchanged(self):
        s, t = self.SCRATCHPAD, tempfile.gettempdir()
        self.assertEqual(self.change("Write", file_path=f"{s}/notes.md", content="x")["path"], f"{s}/notes.md")
        self.assertEqual(self.change("Bash", command=f"echo ok > {s}/log.txt")["label"], "a redirect to a file")
        self.assertIsNone(self.change("Write", file_path=f"{t}/notes.md", content="x"))
        self.assertIsNone(self.change("Bash", command=f"echo ok > {t}/log.txt"))

    def test_the_working_directory_is_never_scratch(self):
        for scratchpad in ("/proj", "/", "/proj/.scratch"):          # the cwd itself, above it, inside it
            with self.subTest(scratchpad=scratchpad):
                self.assertIsNotNone(self.change("Edit", scratchpad, file_path="/proj/src/a.ts"))
                self.assertIsNotNone(self.change("Bash", scratchpad, command="echo x > /proj/src/a.ts"))
        self.assertIsNotNone(self.change("Write", "/proj/.scratch", file_path="/proj/.scratch/n.md", content="x"))

    def test_a_field_that_is_not_an_absolute_path_changes_nothing(self):
        relative = os.path.join(os.getcwd(), "scratchpad", "n.md")   # where a relative field would resolve
        for scratchpad in ("scratchpad", "", 42, ["/seams-test-scratchpad"]):
            with self.subTest(scratchpad=scratchpad):
                self.assertEqual(self.change("Write", scratchpad, file_path=relative, content="x"),
                                 self.change("Write", file_path=relative, content="x"))
                self.assertIsNotNone(self.change("Write", scratchpad, file_path=f"{self.SCRATCHPAD}/n.md", content="x"))


class PreToolUseDecision(unittest.TestCase):
    """decide_pre_tool_use: refuse a project change until a declaration has routed the work."""

    def setUp(self):
        self.config = tempfile.mkdtemp()
        self.ledger = seams_ledger.empty_ledger("s1")

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
        # A route lasts, so the refusal must not send Claude back to a skill after every message.
        self.assertIn("routed this conversation's work since the session started or was cleared", reason)
        self.assertNotIn("this request", reason)
        # Scratch work is not a change: the reason says so, so it is not declared as trivial.
        self.assertIn("absolute path under the temp directory or the session's scratchpad needs no declaration", reason)

    def test_a_shell_mutation_without_a_declaration_is_refused_by_its_label(self):
        decision = self.decide(event("Bash", command="sed -i 's/a/b/' src/a.ts"))
        self.assertEqual(decision["decision"], "deny")
        self.assertIn("sed -i", decision["reason"])

    def test_a_change_with_a_declaration_is_allowed_and_recorded(self):
        seams_ledger.add_declaration(self.ledger, "tdd")
        decision = self.decide(event("Edit", file_path="/proj/src/a.ts"))
        self.assertEqual(decision["decision"], "allow")
        self.assertEqual(decision["change"]["path"], "/proj/src/a.ts")

    def test_a_non_change_is_allowed_without_a_declaration(self):
        self.assertEqual(self.decide(event("Read", file_path="/proj/src/a.ts"))["decision"], "allow")
        self.assertEqual(self.decide(event("Bash", command="npm test"))["decision"], "allow")
        self.assertEqual(self.decide(event("Write", file_path="/tmp/notes.txt", content="x"))["decision"], "allow")

    def test_a_subagent_is_judged_by_the_same_ledger(self):
        self.assertEqual(self.decide(event("Edit", agent_id="a1", file_path="/proj/src/a.ts"))["decision"], "deny")
        seams_ledger.add_declaration(self.ledger, "matt-pocock-workflow:implement")
        self.assertEqual(self.decide(event("Edit", agent_id="a1", file_path="/proj/src/a.ts"))["decision"], "allow")


class SubagentDeclarations(unittest.TestCase):
    """A subagent's own declaration covers that subagent alone (lean-and-durable ticket 12, the user's choice after
    its security review). A parallel run's builders invoke `implement` themselves; while declarations were the
    session's, a builder's reopened the gate for a message the user had typed mid-run, which no skill had routed
    (user story 48). So a subagent's declaration opens nothing for the main conversation or for another agent. The
    main conversation's declarations still cover every call, a subagent's included, as before."""

    def setUp(self):
        self.ledger = seams_ledger.empty_ledger("s1")

    def allowed(self, agent_id: str = None) -> bool:
        edit = event("Edit", agent_id=agent_id, file_path="/proj/src/a.ts", old_string="a", new_string="b")
        return gate.decide_pre_tool_use(edit, self.ledger)["decision"] == "allow"

    def test_a_subagents_declaration_opens_nothing_for_the_main_conversation_or_another_agent(self):
        seams_ledger.add_declaration(self.ledger, "matt-pocock-workflow:implement", "builder-1")
        self.assertTrue(self.allowed("builder-1"))
        self.assertFalse(self.allowed(), "the main conversation's request has no declaration of its own")
        self.assertFalse(self.allowed("builder-2"))

    def test_a_typed_message_keeps_every_route_and_each_owner_replaces_only_its_own(self):
        send(self.ledger, "/matt-pocock-workflow:implement tickets 03 and 05 in parallel",
             ("matt-pocock-workflow:implement", "plugin"))
        seams_ledger.add_declaration(self.ledger, "matt-pocock-workflow:implement", "builder-1")
        send(self.ledger, "also rename the README's title", prompt_id="p2")
        self.assertTrue(self.allowed() and self.allowed("builder-1") and self.allowed("builder-2"))
        seams_ledger.add_declaration(self.ledger, "tdd", "builder-1")
        seams_ledger.add_declaration(self.ledger, "matt-pocock-workflow:trivial")
        owners = [(d["skill"], d["agent"]) for d in self.ledger["declarations"]]
        self.assertEqual(sorted(owners, key=str), [("matt-pocock-workflow:trivial", None), ("tdd", "builder-1")])

    def test_a_subagents_route_still_opens_nothing_after_a_typed_message(self):
        seams_ledger.add_declaration(self.ledger, "matt-pocock-workflow:implement", "builder-1")
        send(self.ledger, "and the colour", prompt_id="p2")
        self.assertFalse(self.allowed(), "a typed message never borrows a builder's route")
        self.assertTrue(self.allowed("builder-1"))

    def test_a_typed_skill_still_declares_its_request_when_a_subagent_declared_the_same_skill(self):
        # The prompt hook first, then the prompt's own expansion: a subagent's declaration of the same skill is not
        # this request's.
        seams_ledger.add_declaration(self.ledger, "matt-pocock-workflow:grill", "helper-1")
        send(self.ledger, "/grill add coupons", prompt_id="p2")      # its parse cannot read a bare /grill
        seams_ledger.record_expansion(expansion("matt-pocock-workflow:grill", "plugin", "p2"), self.ledger)
        self.assertTrue(self.allowed())

    def test_an_entry_that_names_no_subagent_is_the_main_conversations(self):
        # A ledger written before ticket 12, or a damaged entry, opens what it opened before, and the main
        # conversation's next route replaces it.
        self.ledger["declarations"] = [{"skill": "tdd"}, {"skill": "matt-pocock-workflow:grill", "agent": 7}]
        self.assertTrue(self.allowed() and self.allowed("builder-1"))
        seams_ledger.add_declaration(self.ledger, "matt-pocock-workflow:trivial", "builder-1")
        self.assertEqual(len(self.ledger["declarations"]), 3, "a subagent's route replaces none of them")
        seams_ledger.add_declaration(self.ledger, "matt-pocock-workflow:implement")
        self.assertEqual(sorted(declared(self.ledger)), ["matt-pocock-workflow:implement", "matt-pocock-workflow:trivial"])


class ReadOnlyAgents(unittest.TestCase):
    """Seams' two read-only agents, `scout` and `reviewer`, read and never write, whatever the ledger says
    (lean-and-durable ticket 09, decision 30). A shell command passes only when every part of it is a read the
    gate can name (git's read subcommands, gh's views, the file readers) and its redirects land in the temp
    directory or the session's scratchpad; an editor tool writes only there; PowerShell keeps its read-only
    list. The hook input names a plugin's agent by its plugin-scoped name in `agent_type` (the hooks
    reference, SubagentStart)."""

    SCOUT, REVIEWER = "matt-pocock-workflow:scout", "matt-pocock-workflow:reviewer"

    def setUp(self):
        self.config = tempfile.mkdtemp()
        self.ledger = seams_ledger.empty_ledger("s1")
        seams_ledger.add_declaration(self.ledger, "matt-pocock-workflow:implement")      # the request is declared

    def decide(self, tool="Bash", agent=None, scratchpad=None, **tool_input):
        ev = event(tool, agent_id="a1", agent_type=agent or self.REVIEWER, **tool_input)
        if scratchpad:
            ev["scratchpad_dir"] = scratchpad
        return gate.decide_pre_tool_use(ev, self.ledger, config_dir=self.config)

    def test_a_reviewer_committing_is_refused_even_with_a_declaration(self):
        decision = self.decide(command="git commit -m fix")
        self.assertEqual(decision["decision"], "deny")
        self.assertIsNone(decision["change"])

    def test_the_refusal_names_the_agent_and_the_reads_and_sends_the_change_back(self):
        # A subagent has no Skill tool to route with, so the routes would mislead; the rule says what passes.
        reason = self.decide(command="git commit -m fix")["reason"]
        self.assertTrue(reason.startswith("Seams gate: "), reason)      # the harness counts refusals by it
        for needle in ("`matt-pocock-workflow:reviewer` is a read-only agent", "a git subcommand that is not a read",
                       "whatever the request has declared", "git's read subcommands", "the temp directory",
                       "Report what you would change or run instead"):
            self.assertIn(needle, reason)
        self.assertNotIn("Route it first", reason)
        self.assertIn("/proj/src/a.ts", self.decide("Edit", agent=self.SCOUT, file_path="/proj/src/a.ts")["reason"])

    def test_the_shell_runs_the_reads_a_review_needs(self):
        t = tempfile.gettempdir()
        for command in ["git diff e38023a...HEAD", "git -C /proj log --oneline -5", "git show HEAD:src/a.ts",
                        "git blame -L 1,20 src/a.ts", "git status --short", "git grep -n 'reserve(' -- src",
                        "git merge-base main HEAD", "git ls-files src", "git log --format='%h %s' -3",
                        "git --no-pager diff --stat", "cat src/a.ts", "head -50 src/a.ts | tail -10",
                        "grep -rn 'total$' src", "find src -name '*.ts' -newer package.json", "ls -la src",
                        "wc -l src/*.ts", "cd src && git diff -- a.ts", "diff -u src/a.ts src/b.ts",
                        "sort -u words.txt", "jq .scripts package.json", "gh pr view 12 --json title,body",
                        "gh issue view 45", "gh pr diff 12", "echo done", f"git diff HEAD~1 > {t}/d.patch",
                        f"cat src/a.ts > {t}/a.ts 2>/dev/null", "git log -1 2>&1 | head -3",
                        "git diff --quiet || echo changed", "git log --author='A B' --grep=fix"]:
            with self.subTest(command=command):
                decision = self.decide(command=command)
                self.assertEqual(decision["decision"], "allow", decision["reason"])
                self.assertIsNone(decision["change"])                    # a read reaches no ledger

    def test_every_other_shell_command_is_refused_declared_or_not(self):
        t = tempfile.gettempdir()
        for command in [
            # What the reviews of af9b011 ran past the classifier, and scratch work a read-only agent doesn't do.
            "npm version patch", "npm test -- -u", "npm run build", "npm publish", "make", "black .", "ruff format .",
            "cargo fmt", "go fmt ./...", f"python3 {t}/probe.py", f"bash {t}/p.sh", "gh pr merge 12",
            "gh pr review 12 --approve", "gh api repos/o/r/pulls/1/merge -X PUT", "git diff HEAD~1 --output=src/a.ts",
            "git diff HEAD~1 '--output=src/a.ts'", 'git diff HEAD~1 --out""put=src/a.ts', f"cp src/a.ts {t}/a.ts",
            f"git init -q {t}/probe",
            # git beyond its reads, or told to run a program.
            "git commit -m x", "git stash", "git checkout -- src", "git branch x", "git tag v1",
            "git config user.name x", "git reflog expire --all", "git -c core.pager=cat log",
            "git --exec-path=/tmp log", "git diff --ext-diff", "git grep -O reserve",
            "git grep --open-files-in-pager=vi x", "gh pr view 12 --web",
            # A glob or a brace can expand into an option: a planted file named --output=x.
            "git diff *", "git diff --out{put,x}=f", "find *", "sort *",
            # What runs another command, or a command the gate can't name before it runs.
            "sh -c 'git diff'", "eval git log", "exec git log", "env git log", "sudo cat x", "xargs cat < list.txt",
            "time git log", "./git log", "/usr/bin/git log", '"$GIT" log', "$(echo git) log", "git status $(touch x)",
            "cat `touch x`", "cat <<EOF\n$(rm -rf src)\nEOF", "A=1; git log", "GIT_EXTERNAL_DIFF=x git diff",
            "for f in a b; do cat $f; done", 'git log "$BASE"', "git log 'unterminated", "(rm -rf src)",
            "cat <(rm -rf src)",
            # Writes through a read's own options or its output, and a write after a read.
            "echo x > src/a.ts", "git diff > d.patch", "git log >> ~/notes.txt", "cat src/a.ts | tee copy.txt",
            "find . -name '*.log' -delete", "find . -exec cat {} \\;", "find . -fprint list.txt",
            "sort -o out.txt in.txt", "sort --output=out.txt in.txt", "awk '{print > \"f\"}' a", "sed -n 1p a",
            # A read that runs a program: sort compresses its temporary files with one.
            "sort --compress-program=sh big.txt",
            # A repository under the temp directory runs its config's programs (core.fsmonitor on git status),
            # so a redirect never writes into a git directory, scratch or not.
            f"echo '[core]' > {t}/repo/.git/config", f"cat x >> {t}/wt/.git",
            "git diff; rm -rf src", "git diff && npm install", "git diff | sh", "git log\nrm -rf src",
        ]:
            for agent in (self.SCOUT, self.REVIEWER):
                with self.subTest(command=command, agent=agent):
                    decision = self.decide(agent=agent, command=command)
                    self.assertEqual(decision["decision"], "deny")
                    self.assertIsNone(decision["change"])                # nothing reaches the ledger

    def test_an_editor_tool_writes_only_under_the_temp_directory_or_the_scratchpad(self):
        # Their tool lists hold no editor; the gate holds if one arrives. The Claude config directory, which a
        # declared main conversation may write, is not scratch for a read-only agent.
        t, pad = tempfile.gettempdir(), "/seams-test-scratchpad/s1/scratchpad"
        self.assertEqual(self.decide("Write", agent=self.SCOUT, file_path=f"{t}/notes.md", content="x")["decision"], "allow")
        self.assertEqual(self.decide("Write", agent=self.SCOUT, scratchpad=pad, file_path=f"{pad}/n.md",
                                     content="x")["decision"], "allow")
        # The config directory as it lies, outside the temp directory (the tests' own config dir is a mkdtemp).
        for path in ("/proj/src/a.ts", "README.md", "/home/u/.claude/settings.json", "/home/u/.claude/CLAUDE.md",
                     "/etc/hosts"):
            for tool in ("Edit", "Write", "MultiEdit"):
                with self.subTest(path=path, tool=tool):
                    decision = self.decide(tool, agent=self.SCOUT, file_path=path, content="x")
                    self.assertEqual(decision["decision"], "deny")
                    self.assertIsNone(decision["change"])
        self.assertEqual(self.decide("NotebookEdit", notebook_path="/proj/n.ipynb", new_source="x")["decision"], "deny")
        # The config directory inside the temp directory, where a CI job's or an eval run's lies (self.config is a
        # mkdtemp): still not scratch, by editor or by redirect. Ubuntu's CI, whose suite runs under /tmp, found a
        # scout's write to its settings allowed.
        settings = os.path.join(self.config, "settings.json")
        for tool in ("Edit", "Write", "MultiEdit"):
            with self.subTest(config_inside_temp=tool):
                self.assertEqual(self.decide(tool, agent=self.SCOUT, file_path=settings, content="x")["decision"], "deny")
        self.assertEqual(self.decide(command=f"git diff HEAD > {settings}")["decision"], "deny")
        # The refusal names the real reason: the path is inside the temp directory, but it is the config directory.
        self.assertIn("inside the Claude config directory",
                      self.decide("Write", agent=self.SCOUT, file_path=settings, content="x")["reason"])
        # Fail closed (decision 47): a scratchpad inside the config directory is no scratch for them either.
        pad = os.path.join(self.config, "scratchpad")
        self.assertEqual(self.decide("Write", agent=self.SCOUT, scratchpad=pad, file_path=f"{pad}/n.md",
                                     content="x")["decision"], "deny")
        # Nor into a git directory, even under the temp directory: its config names programs git runs.
        reason = self.decide("Write", agent=self.SCOUT, file_path=f"{t}/repo/.git/config", content="x")["reason"]
        self.assertIn("inside a git directory", reason)

    def test_powershell_and_a_monitor_watch_keep_to_the_same_reads(self):
        for command, expected in (("Get-Content README.md", "allow"), ("git log", "allow"),
                                  ("Remove-Item src -Recurse", "deny"), ("npm version patch", "deny")):
            with self.subTest(command=command):
                self.assertEqual(self.decide("PowerShell", command=command, description="x")["decision"], expected)
        t = tempfile.gettempdir()
        for tool_input, expected in (({"command": f"tail -f {t}/server.log"}, "allow"),
                                     ({"command": "tail -f server.log | tee src/copy.txt"}, "deny"),
                                     ({"command": "npm run dev"}, "deny"),
                                     ({"ws": {"url": "wss://events.example.com/stream"}}, "allow")):
            with self.subTest(tool_input=tool_input):
                self.assertEqual(self.decide("Monitor", description="watch", **tool_input)["decision"], expected)

    def test_other_agents_keep_the_ledgers_rule(self):
        # A built-in agent, and an agent of the user's own that happens to share a bare name, are not Seams'.
        for agent in ("general-purpose", "Explore", "reviewer", "scout", "other-plugin:reviewer"):
            with self.subTest(agent=agent):
                decision = self.decide("Edit", agent=agent, file_path="/proj/src/a.ts")
                self.assertEqual(decision["decision"], "allow")
                self.assertEqual(decision["change"]["path"], "/proj/src/a.ts")
                self.assertEqual(self.decide(agent=agent, command="npm version patch")["decision"], "allow")
        undeclared = gate.decide_pre_tool_use(event("Edit", agent_id="a1", agent_type="general-purpose",
                                                    file_path="/proj/src/a.ts"),
                                              seams_ledger.empty_ledger("s1"), config_dir=self.config)
        self.assertEqual(undeclared["decision"], "deny")
        self.assertIn("Route it first", undeclared["reason"])

    def test_an_agent_type_that_is_not_a_name_changes_nothing(self):
        # A list or a mapping must not raise (a hook that raises fails open) nor pass for a read-only agent.
        for agent in ([self.REVIEWER], {"name": self.REVIEWER}, 7, ""):
            with self.subTest(agent=agent):
                ev = event("Edit", agent_id="a1", file_path="/proj/src/a.ts")
                ev["agent_type"] = agent
                self.assertEqual(self.decide_event(ev)["decision"], "allow")

    def decide_event(self, ev):
        return gate.decide_pre_tool_use(ev, self.ledger, config_dir=self.config)


class LedgerOutOfReach(unittest.TestCase):
    """No tool call writes the gate's ledger as scratch (seams-revamp ticket 10, from ticket 04's security review). It
    lay under the temp directory, where any tool call may write, so an agent misled by a hostile pull request could
    forge a declaration there that opens the main conversation's gate, or erase the done-check's pending changes. A write
    to the ledger's directory or a ledger file is a change to the project, and a read-only agent's write there is refused
    like any other. It lies in the home directory's state directory, outside the temp and Claude config directories, so
    a write into a directory that holds it is a change too, even where the home directory lies under the temp
    directory; where the home directory cannot hold it, it lies in the temp directory itself, and a write into it still
    is a change."""

    # Where the ledger lies: in a home under the temp directory, the harder case for its own place (a home outside it
    # holds the ledger outside every scratch root), and where the home directory cannot hold it (no absolute path).
    PLACEMENTS = (("home", os.path.join(tempfile.mkdtemp(), "home")), ("temp", "relative/home"))

    def setUp(self):
        self.config = tempfile.mkdtemp()
        self.ledger = seams_ledger.empty_ledger("s1")
        self.declared = seams_ledger.empty_ledger("s1")
        seams_ledger.add_declaration(self.declared, "matt-pocock-workflow:implement")
        self.addCleanup(seams_ledger.home_state_dir.cache_clear)

    @contextlib.contextmanager
    def placed(self, home):
        """The ledger's root with HOME set to `home`, for the length of the with block."""
        with mock.patch.dict(os.environ, {"HOME": home}):
            seams_ledger.home_state_dir.cache_clear()
            try:
                yield seams_ledger.ledger_root()
            finally:
                seams_ledger.home_state_dir.cache_clear()

    def decide(self, ev, ledger=None):
        return gate.decide_pre_tool_use(ev, self.ledger if ledger is None else ledger, config_dir=self.config)

    def test_an_editor_tool_writing_the_ledger_is_a_change(self):
        for placement, home in self.PLACEMENTS:
            with self.placed(home):
                path = seams_ledger.ledger_path("s1")
                for tool in ("Write", "Edit", "MultiEdit"):
                    with self.subTest(placement=placement, tool=tool):
                        decision = self.decide(event(tool, file_path=path, content="{}"))
                        self.assertEqual(decision["decision"], "deny", "no declaration covers a write to the ledger")
                        self.assertIn(path, decision["reason"])
                decision = self.decide(event("Write", file_path=path, content="{}"), self.declared)
                self.assertEqual(decision["decision"], "allow")
                self.assertEqual(decision["change"]["path"], path, "with a declaration it is recorded as a change")

    def test_a_shell_command_writing_the_ledgers_directory_is_a_change(self):
        t = tempfile.gettempdir()
        forged = '{"version": 2, "declarations": [{"skill": "tdd"}]}'
        for placement, home in self.PLACEMENTS:
            with self.placed(home) as root:
                for tool, command, label in [("Bash", f"printf '%s' '{forged}' > {root}/s1.json", "a redirect to a file"),
                                             ("Bash", f"echo x >> {root}/other-session.json", "a redirect to a file"),
                                             ("Bash", f"cp {t}/forged.json {root}/s1.json", "cp"),
                                             ("Bash", f"rm -rf {root}", "rm"),
                                             ("Monitor", f"tail -f {t}/x.log > {root}/s1.json", "a redirect to a file")]:
                    with self.subTest(placement=placement, command=command):
                        decision = self.decide(event(tool, command=command))
                        self.assertEqual(decision["decision"], "deny")
                        self.assertIn(label, decision["reason"])
                        decision = self.decide(event(tool, command=command), self.declared)
                        self.assertEqual(decision["decision"], "allow")
                        self.assertEqual(decision["change"]["label"], label)

    def test_a_shell_command_writing_a_directory_that_holds_the_ledger_is_a_change(self):
        # Found by the review of the first candidate, when the ledger lay in the temp directory: each of these wrote or
        # erased it through the directory holding it, which was scratch. A home under the temp directory holds it too.
        t = tempfile.gettempdir()
        with self.placed(dict(self.PLACEMENTS)["home"]) as root:
            parent = os.path.dirname(root)
            for command, label in [(f"cp -R {t}/stage/seams {parent}", "cp"),
                                   (f"tar -xf {t}/forged.tar -C {parent}", "tar -x"),
                                   (f"unzip -o {t}/forged.zip -d {parent}", "unzip"),
                                   (f"find {parent} -name s1.json -delete", "find -delete"),
                                   (f"ln -s {parent} {t}/L && printf x > {t}/L/seams/s1.json", "ln")]:
                with self.subTest(command=command):
                    decision = self.decide(event("Bash", command=command))
                    self.assertEqual(decision["decision"], "deny")
                    self.assertIn(label, decision["reason"])

    def test_a_read_only_agent_writing_there_is_refused_declared_or_not(self):
        for placement, home in self.PLACEMENTS:
            with self.placed(home) as root:
                path = seams_ledger.ledger_path("s1")
                for agent in ("matt-pocock-workflow:reviewer", "matt-pocock-workflow:scout"):
                    for ledger in (self.ledger, self.declared):
                        for tool, tool_input in (("Bash", {"command": f"printf '%s' x > {root}/s1.json"}),
                                                 ("Bash", {"command": f"git diff HEAD >> {path}"}),
                                                 ("Write", {"file_path": path, "content": "{}"}),
                                                 ("Edit", {"file_path": f"{root}/other.json", "old_string": "a",
                                                           "new_string": "b"})):
                            with self.subTest(placement=placement, agent=agent, declared=ledger is self.declared,
                                              tool=tool, **tool_input):
                                decision = self.decide(event(tool, agent_id="a1", agent_type=agent, **tool_input), ledger)
                                self.assertEqual(decision["decision"], "deny")
                                self.assertIsNone(decision["change"])
                                self.assertIn("the gate's ledger directory", decision["reason"])
        # Its scratch is as it was: the temp directory, the ledger's own place or beside it.
        t = tempfile.gettempdir()
        for tool, tool_input in (("Bash", {"command": f"git diff HEAD > {t}/d.patch"}),
                                 ("Write", {"file_path": f"{t}/seams-notes.md", "content": "x"})):
            with self.subTest(scratch=tool):
                decision = self.decide(event(tool, agent_id="a1", agent_type="matt-pocock-workflow:reviewer", **tool_input))
                self.assertEqual(decision["decision"], "allow", decision["reason"])

    def test_a_write_beside_the_ledger_in_the_temp_dir_is_scratch_as_before_and_a_link_into_it_is_not(self):
        t = tempfile.gettempdir()
        home = dict(self.PLACEMENTS)["home"]
        with self.placed(home):
            for path in (f"{home}/notes.md", f"{home}/.local/state/other/x.log", f"{home}/.local/state/seams0/x.log"):
                with self.subTest(home_path=path):
                    self.assertIsNone(gate.change_for_event(event("Bash", command=f"echo x > {path}"), config_dir=self.config))
            self.assertIsNone(gate.change_for_event(event("Bash", command=f"cp {t}/a.log {t}"), config_dir=self.config),
                              "the temp directory itself is scratch as before, though it holds the home")
        with self.placed("relative/home") as root:
            for path in (f"{root}0/s1.json", f"{root}.bak/s1.json", f"{root}-notes.md", f"{t}/seams-pr-review/o-r-1-abc/x.log"):
                with self.subTest(path=path):
                    self.assertIsNone(gate.change_for_event(event("Write", file_path=path, content="x"), config_dir=self.config))
                    self.assertIsNone(gate.change_for_event(event("Bash", command=f"echo x > {path}"), config_dir=self.config))
            link = os.path.join(tempfile.mkdtemp(), "ledger-link")
            os.symlink(root, link)
            self.assertEqual(self.decide(event("Write", file_path=f"{link}/s1.json", content="{}"))["decision"], "deny")
            self.assertEqual(self.decide(event("Bash", command=f"echo x > {link}/s1.json"))["decision"], "deny")

    def test_a_damaged_declarations_field_opens_nothing(self):
        root = tempfile.mkdtemp()
        os.makedirs(seams_ledger.ledger_root(root), exist_ok=True)
        edit = event("Edit", file_path="/proj/src/a.ts")
        for declarations in ('"all"', "1", "true", '{"skill": "tdd"}', '["tdd"]', "[1]", "[true]", "[[]]", "[null]"):
            with self.subTest(declarations=declarations):
                Path(seams_ledger.ledger_path("s1", root)).write_text(f'{{"version": 2, "declarations": {declarations}}}')
                ledger = seams_ledger.load_ledger("s1", root)
                self.assertEqual(self.decide(edit, ledger)["decision"], "deny")
                self.assertIsNone(seams_ledger.decide_stop(ledger, stop_hook_active=False))
                seams_ledger.add_declaration(ledger, "tdd")              # the next declaration opens it as ever
                self.assertEqual(self.decide(edit, ledger)["decision"], "allow")


class MonitorCommands(unittest.TestCase):
    """A Monitor watch runs its command in the Bash tool's shell, so the gate judges that command
    as it judges a Bash command. A WebSocket watch runs nothing on the machine (ticket 02)."""

    def setUp(self):
        self.config = tempfile.mkdtemp()
        self.ledger = seams_ledger.empty_ledger("s1")

    def decide(self, **tool_input):
        tool_input = dict({"description": "watch", "timeout_ms": 300000}, **tool_input)
        return gate.decide_pre_tool_use(event("Monitor", **tool_input), self.ledger, config_dir=self.config)

    def test_a_watch_that_writes_to_the_project_is_refused_before_a_declaration(self):
        decision = self.decide(command="tail -f server.log | tee src/log-copy.txt")
        self.assertEqual(decision["decision"], "deny")
        self.assertIn("a shell command (`tee`) changes the project", decision["reason"])
        self.assertEqual(self.decide(command="while true; do date >> src/ticks.txt; sleep 1; done")["decision"], "deny")

    def test_a_read_only_watch_and_a_websocket_watch_are_not_changes(self):
        t = tempfile.gettempdir()
        for tool_input in ({"command": "tail -f server.log | grep --line-buffered ERROR"},
                           {"command": "until curl -sf localhost:3000/health; do sleep 1; done"},
                           {"command": f"tail -f {t}/x.log > {t}/copy.log"},     # scratch, as from Bash
                           {"ws": {"url": "wss://events.example.com/stream", "protocols": ["v1"]}}):
            with self.subTest(tool_input=tool_input):
                self.assertEqual(self.decide(**tool_input)["decision"], "allow")

    def test_after_a_declaration_the_watch_is_allowed_and_recorded_as_a_shell_change(self):
        seams_ledger.add_declaration(self.ledger, "matt-pocock-workflow:implement")
        decision = self.decide(command="tail -f server.log | tee src/log-copy.txt")
        self.assertEqual(decision["decision"], "allow")
        self.assertEqual((decision["change"]["tool"], decision["change"]["label"]), ("Monitor", "tee"))


class PowerShellCommands(unittest.TestCase):
    """Before a declaration a PowerShell command is a change, unless it is one of a short read-only
    list run on its own with plain arguments (ticket 02). The list grows only with tests."""

    READS = [
        "Get-Content README.md",
        "Get-ChildItem -Recurse -Filter *.ts",
        "Select-String -Path src/*.ts -Pattern TODO",
        "git status --short",
        "git diff HEAD~1",
        "git log --oneline -5",
        "get-content README.md",                     # PowerShell's names ignore case
        "  Get-ChildItem src  ",
        "Get-Content $env:TEMP/notes.txt -Tail 20",
    ]

    CHANGES = [
        "Set-Content src/a.txt 'x'",
        "Remove-Item src -Recurse",
        "git commit -m x",
        "New-Item -ItemType File x",
        "npm install",
        "Get-Process",                               # outside the list, even a read
        "git -C sub status",                         # the list is git's own subcommand, first
        # A listed command made to do more: a redirect, a pipe, a second statement, a subexpression,
        # a script block, a line continuation, a second line, or an output file.
        "Get-Content a.txt > b.txt",
        "Get-Content a.txt | Set-Content b.txt",
        "Get-ChildItem; Remove-Item x",
        "Get-Content (Remove-Item x)",
        "Get-Content $(Remove-Item x)",
        "& { Remove-Item x }",
        "Get-Content a.txt `\n; Remove-Item b",
        "Get-ChildItem\nRemove-Item x",
        "git diff --output=patch.diff",
        "git log --output patch.txt",
        'git diff "--output=patch.diff"',            # PowerShell removes the quotes before git reads it
        "git log '--output' log.txt",
        'git diff --out""put=patch.diff',
        "Select-String -Pattern 'a|b' -Path x",      # strict: a pipe character counts, quoted or not
    ]

    def setUp(self):
        self.config = tempfile.mkdtemp()
        self.ledger = seams_ledger.empty_ledger("s1")

    def decide(self, command):
        return gate.decide_pre_tool_use(event("PowerShell", command=command, description="x"), self.ledger,
                                        config_dir=self.config)

    def test_the_read_only_list_runs_before_a_declaration(self):
        for command in self.READS:
            with self.subTest(command=command):
                self.assertEqual(self.decide(command)["decision"], "allow")

    def test_every_other_command_is_refused_and_the_refusal_names_the_list(self):
        for command in self.CHANGES:
            with self.subTest(command=command):
                decision = self.decide(command)
                self.assertEqual(decision["decision"], "deny")
                for listed in ("Get-Content", "Get-ChildItem", "Select-String", "git status", "git diff", "git log"):
                    self.assertIn(listed, decision["reason"])

    def test_after_a_declaration_it_is_allowed_and_recorded(self):
        seams_ledger.add_declaration(self.ledger, "tdd")
        decision = self.decide("Remove-Item src -Recurse")
        self.assertEqual(decision["decision"], "allow")
        self.assertEqual(decision["change"]["tool"], "PowerShell")
        self.assertIsNone(self.decide("git status")["change"])

    def test_the_done_check_treats_a_lone_git_command_as_git(self):
        # As from Bash: a commit or a push after the checks needs no new verification; anything
        # else PowerShell runs, a git command joined to another included, still does.
        for command, blocks in (("git commit -m done", False), ("git push origin main", False),
                                ("Remove-Item src -Recurse", True), ("git commit -m x; Remove-Item src", True)):
            with self.subTest(command=command):
                self.ledger = seams_ledger.empty_ledger("s1")
                seams_ledger.add_declaration(self.ledger, "tdd")
                seams_ledger.mark_verified(self.ledger)
                seams_ledger.add_change(self.ledger, self.decide(command)["change"])
                self.assertEqual(seams_ledger.decide_stop(self.ledger, stop_hook_active=False) is not None, blocks)


class StopDecision(unittest.TestCase):
    """decide_stop: a turn that changed non-documentation project files ends only after verification."""

    def setUp(self):
        self.ledger = seams_ledger.empty_ledger("s1")
        seams_ledger.add_declaration(self.ledger, "tdd")

    def test_an_unverified_code_change_blocks_once_with_the_reason(self):
        seams_ledger.add_change(self.ledger, {"tool": "Edit", "path": "/proj/src/a.ts", "doc": False})
        reason = seams_ledger.decide_stop(self.ledger, stop_hook_active=False)
        self.assertIsNotNone(reason)
        self.assertIn("Seams done-check", reason)
        self.assertIn("1 unverified change", reason)
        self.assertIn("/proj/src/a.ts", reason)
        self.assertIn("matt-pocock-workflow:verification-before-completion", reason)
        self.assertIn("does not repeat", reason)

    def test_the_second_stop_of_the_turn_is_allowed(self):
        seams_ledger.add_change(self.ledger, {"tool": "Edit", "path": "/proj/src/a.ts", "doc": False})
        self.assertIsNone(seams_ledger.decide_stop(self.ledger, stop_hook_active=True))

    def test_no_changes_or_documentation_only_are_allowed(self):
        self.assertIsNone(seams_ledger.decide_stop(self.ledger, stop_hook_active=False))
        seams_ledger.add_change(self.ledger, {"tool": "Write", "path": "/proj/docs/spec.md", "doc": True})
        seams_ledger.add_change(self.ledger, {"tool": "Edit", "path": "/proj/CONTEXT.md", "doc": True})
        self.assertIsNone(seams_ledger.decide_stop(self.ledger, stop_hook_active=False))

    def test_verification_after_the_last_change_satisfies_it(self):
        seams_ledger.add_change(self.ledger, {"tool": "Edit", "path": "/proj/src/a.ts", "doc": False})
        seams_ledger.mark_verified(self.ledger)
        self.assertIsNone(seams_ledger.decide_stop(self.ledger, stop_hook_active=False))

    def test_a_change_after_verification_needs_verifying_again(self):
        seams_ledger.mark_verified(self.ledger)
        seams_ledger.add_change(self.ledger, {"tool": "Edit", "path": "/proj/src/b.ts", "doc": False})
        self.assertIn("/proj/src/b.ts", seams_ledger.decide_stop(self.ledger, stop_hook_active=False))

    def test_a_shell_mutation_counts_and_is_named_by_its_label(self):
        seams_ledger.add_change(self.ledger, {"tool": "Bash", "label": "sed -i", "doc": False})
        reason = seams_ledger.decide_stop(self.ledger, stop_hook_active=False)
        self.assertIn("sed -i", reason)

    def test_the_count_covers_every_unverified_file(self):
        for path in ("/proj/src/a.ts", "/proj/src/b.ts", "/proj/src/c.ts"):
            seams_ledger.add_change(self.ledger, {"tool": "Edit", "path": path, "doc": False})
        self.assertIn("3 unverified changes", seams_ledger.decide_stop(self.ledger, stop_hook_active=False))

    def test_a_commit_after_verification_does_not_need_verifying_again(self):
        seams_ledger.add_change(self.ledger, {"tool": "Edit", "path": "/proj/src/a.ts", "doc": False})
        seams_ledger.mark_verified(self.ledger)
        seams_ledger.add_change(self.ledger, {"tool": "Bash", "label": "git commit", "doc": False})
        seams_ledger.add_change(self.ledger, {"tool": "Bash", "label": "git push", "doc": False})
        self.assertIsNone(seams_ledger.decide_stop(self.ledger, stop_hook_active=False))

    def test_the_reason_speaks_of_the_request_not_the_turn(self):
        seams_ledger.add_change(self.ledger, {"tool": "Edit", "path": "/proj/src/a.ts", "doc": False})
        reason = seams_ledger.decide_stop(self.ledger, stop_hook_active=False)
        self.assertNotIn("this turn changed", reason)
        self.assertIn("since the last verification", reason)

    def test_a_ledger_from_an_older_format_reads_as_empty(self):
        root = tempfile.mkdtemp()
        path = seams_ledger.ledger_path("s1", root)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        Path(path).write_text('{"version": 1, "session": "s1", "declarations": [{"skill": "tdd"}], '
                              '"changes": [{"tool": "Edit", "path": "/p/a.ts", "doc": false}], "verified_at": null}')
        self.assertEqual(seams_ledger.load_ledger("s1", root)["declarations"], [])
        self.assertEqual(seams_ledger.LEDGER_VERSION, 2)

    def test_which_skills_count_as_verification(self):
        for skill in ["matt-pocock-workflow:verification-before-completion",
                      "superpowers:verification-before-completion", "verification-before-completion"]:
            with self.subTest(skill=skill):
                self.assertTrue(seams_ledger.is_verification(skill))
        for skill in ["tdd", "matt-pocock-workflow:trivial", "superpowers:brainstorming"]:
            with self.subTest(skill=skill):
                self.assertFalse(seams_ledger.is_verification(skill))


if __name__ == "__main__":
    unittest.main()
