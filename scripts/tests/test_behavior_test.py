"""The behavior-test harness: its stream scanner through `behavior_test.py scan <stream>`, its
judge through `behavior_test.py judge <results.jsonl>` against the real expectation files
under plugin/evals, and a run's record through `run_once` with a stub `claude` on PATH.

A run's verdict is its first committing call: a Skill or AskUserQuestion call (a process
choice), or a change to the workspace (an Edit/Write there, or a shell command the gate's
classifier labels a mutation), confirmed by its result: a call the gate refused or a change
that failed changed nothing, so it is counted and the scan goes on. The scanner records that
call, the exploring calls before it, the assistant text before it, and, when no such call
happens, the final result. With --past-skill, Skill calls are recorded but do not stop the
scan, so a test can see what the skill then does (the grill's first question, or whether a
gate scenario's change goes through once the route is declared).
"""
from __future__ import annotations

import importlib.util
import json
import os
import re
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
HARNESS = REPO / "scripts" / "behavior_test.py"


def load_harness():
    spec = importlib.util.spec_from_file_location("behavior_test", HARNESS)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

INIT = {"type": "system", "subtype": "init", "model": "claude-opus-5"}


_messages = iter(range(1, 10**6))


def assistant(*blocks: dict, mid: str | None = None) -> dict:
    """One assistant event. Claude Code emits one event per content block, all sharing the
    message's id; pass `mid` to put two events in one message, else each call is a new one."""
    return {"type": "assistant", "message": {"id": mid or f"msg_{next(_messages)}", "role": "assistant",
                                             "content": list(blocks)}}


def denied(tool_use_id: str, message: str = "This command requires approval") -> dict:
    """The system event Claude Code emits when its permission system denies a call."""
    return {"type": "system", "subtype": "permission_denied", "tool_name": "Bash", "tool_use_id": tool_use_id,
            "decision_reason_type": "other", "message": message}


def tool(name: str, **inputs: object) -> dict:
    return {"type": "tool_use", "id": inputs.pop("id", None) or f"toolu_{name}", "name": name, "input": inputs}


def tool_result(tool_use_id: str, content: str, error: bool = False) -> dict:
    """The user event Claude Code emits when a tool call returns (or is refused)."""
    return {"type": "user", "message": {"role": "user", "content": [
        {"type": "tool_result", "tool_use_id": tool_use_id, "content": content, "is_error": error}]}}


# A refused call's result as Claude Code 2.1.272 reports it (observed 2026-09-16, ticket 09's probe
# run): the gate's reason verbatim as the content, is_error true, and the call listed in the reply's
# permission_denials.
REFUSED = ("Seams gate: a shell command (`a redirect to a file`) changes the project, and this request "
           "has no declaration yet: no process skill has been invoked for it. Route it first, with the "
           "Skill tool: `diagnosing-bugs` for something broken, ... Then retry this call.")


def text(value: str) -> dict:
    return {"type": "text", "text": value}


def result(value: str, cost: float | None = None) -> dict:
    return {"type": "result", "subtype": "success", "result": value, "total_cost_usd": cost}


def scan(*items: dict | str, past_skill: bool = False, workspace: Path | None = None) -> dict:
    """Scan a stream built from event dicts and raw (possibly malformed) lines."""
    lines = (json.dumps(i) if isinstance(i, dict) else i for i in items)
    with tempfile.TemporaryDirectory() as d:
        stream = Path(d) / "stream.jsonl"
        stream.write_text("".join(line + "\n" for line in lines))
        cmd = [sys.executable, str(HARNESS), "scan", str(stream)]
        cmd += ["--past-skill"] if past_skill else []
        cmd += ["--workspace", str(workspace)] if workspace else []
        out = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return json.loads(out.stdout)


class RunContextTest(unittest.TestCase):
    """What a run record says about its surroundings: which skills loaded, where it wrote."""

    def test_superpowers_skills_are_counted_from_init(self):
        init = {**INIT, "skills": ["superpowers:brainstorming", "superpowers:writing-plans",
                                   "grilling", "matt-pocock-workflow:grill"]}
        r = scan(init, assistant(tool("Skill", skill="matt-pocock-workflow:grill")))
        self.assertEqual(r["superpowers_skills"], 2)

    def test_writes_outside_the_workspace_are_exploration(self):
        with tempfile.TemporaryDirectory() as d:
            ws = Path(d) / "workspace"
            ws.mkdir()
            r = scan(INIT,
                     assistant(tool("Write", file_path="/tmp/race-check.mts")),
                     assistant(tool("Write", file_path=str(ws / "docs" / "spec.md"))),
                     workspace=ws)
        self.assertEqual((r["first_tool"], r["before"]), ("Write", ["Write(outside)"]))


class ScanTest(unittest.TestCase):
    def test_first_skill_after_exploration(self):
        r = scan(INIT,
                 assistant(tool("Read", file_path="src/inventory.ts")),
                 assistant(text("Using diagnosing-bugs."), tool("Skill", skill="diagnosing-bugs")))
        self.assertEqual(r["first_tool"], "Skill")
        self.assertEqual(r["skill"], "diagnosing-bugs")
        self.assertEqual(r["before"], ["Read"])
        self.assertEqual(r["text"], "Using diagnosing-bugs.")
        self.assertEqual(r["model"], "claude-opus-5")

    def test_only_the_first_committing_call_counts(self):
        r = scan(INIT, assistant(tool("Skill", skill="tdd")), assistant(tool("Skill", skill="code-review")))
        self.assertEqual((r["skill"], r["skills"]), ("tdd", ["tdd"]))

    def test_an_edit_before_any_skill_is_the_verdict(self):
        r = scan(INIT,
                 assistant(tool("Read", file_path="README.md")),
                 assistant(tool("Edit", file_path="README.md")),
                 assistant(tool("Skill", skill="tdd")))
        self.assertEqual((r["first_tool"], r["skill"], r["before"]), ("Edit", None, ["Read"]))

    def test_skill_later_in_the_same_message(self):
        r = scan(INIT, assistant(tool("Grep", pattern="reserve"), tool("Skill", skill="diagnosing-bugs")))
        self.assertEqual((r["skill"], r["before"]), ("diagnosing-bugs", ["Grep"]))

    def test_ask_user_question_counts_its_questions(self):
        r = scan(INIT, assistant(tool("AskUserQuestion", questions=[{"question": "Which seam?"}])))
        self.assertEqual((r["first_tool"], r["skill"], r["questions"]), ("AskUserQuestion", None, 1))

    def test_no_committing_call_keeps_the_result(self):
        r = scan(INIT,
                 assistant(tool("Read", file_path="src/pricing.ts")),
                 assistant(text("Which coupon codes should stack?")),
                 result("Which coupon codes should stack?", cost=0.12))
        self.assertIsNone(r["first_tool"])
        self.assertEqual(r["before"], ["Read"])
        self.assertEqual(r["result"], "Which coupon codes should stack?")
        self.assertEqual(r["cost_usd"], 0.12)

    def test_malformed_lines_are_skipped(self):
        r = scan(INIT, "not json", "[1, 2]", assistant(tool("Skill", skill="diagnosing-bugs")))
        self.assertEqual(r["skill"], "diagnosing-bugs")

    def test_string_content_and_odd_blocks_are_skipped(self):
        r = scan(INIT,
                 {"type": "assistant", "message": {"role": "assistant", "content": "plain string"}},
                 {"type": "assistant", "message": {"role": "assistant", "content": ["not a block", 7]}},
                 assistant(tool("Skill", skill="diagnosing-bugs")))
        self.assertEqual(r["skill"], "diagnosing-bugs")


class ShellMutationTest(unittest.TestCase):
    """A shell command that changes the project is a committing call, scored the way the gate
    scores it (the same classifier), not as exploration."""

    def test_a_shell_write_before_the_first_skill_is_the_verdict(self):
        r = scan(INIT,
                 assistant(tool("Bash", command="echo x > src/f.ts")),
                 assistant(tool("Skill", skill="diagnosing-bugs")))
        self.assertEqual((r["first_tool"], r["label"], r["skill"]), ("Bash", "a redirect to a file", None))
        self.assertEqual(r["before"], [])

    def test_a_read_only_shell_command_is_exploration(self):
        r = scan(INIT,
                 assistant(tool("Bash", command="git status && npm test")),
                 assistant(tool("Skill", skill="diagnosing-bugs")))
        self.assertEqual((r["first_tool"], r["label"], r["skill"]), ("Skill", None, "diagnosing-bugs"))
        self.assertEqual(r["before"], ["Bash"])


class ToolResultTest(unittest.TestCase):
    """What a call's result says about it: refused by the gate, failed, or gone through."""

    def test_a_gate_refusal_is_counted_and_is_not_the_commit(self):
        r = scan(INIT,
                 assistant(tool("Bash", id="t1", command="echo x > src/f.ts")),
                 tool_result("t1", REFUSED, error=True),
                 assistant(tool("Skill", id="t2", skill="matt-pocock-workflow:trivial")),
                 tool_result("t2", "Launching skill: matt-pocock-workflow:trivial"),
                 assistant(tool("Bash", id="t3", command="echo x > src/f.ts")),
                 tool_result("t3", ""))
        self.assertEqual(r["refusals"], 1)
        self.assertEqual((r["first_tool"], r["skill"]), ("Skill", "matt-pocock-workflow:trivial"))
        self.assertEqual(r["before"], ["Bash(refused)"])
        self.assertEqual((r["failed_calls"], r["undeclared"]), (0, 0))

    def test_a_second_call_in_the_same_message_does_not_confirm_the_first(self):
        # Claude Code splits one message's blocks into events sharing the message id; the
        # verdict waits for its result, which a parallel call's event does not stand in for.
        r = scan(INIT,
                 assistant(tool("Edit", id="t1", file_path="src/f.ts", old_string="x", new_string="y"), mid="m1"),
                 assistant(tool("Bash", id="t2", command="cat src/f.ts"), mid="m1"),
                 tool_result("t1", "PreToolUse hook denied: Seams gate: editing `src/f.ts` changes the project", error=True),
                 tool_result("t2", "x"),
                 assistant(tool("Skill", id="t3", skill="matt-pocock-workflow:trivial")),
                 tool_result("t3", "Launching skill: matt-pocock-workflow:trivial"))
        self.assertEqual((r["refusals"], r["undeclared"]), (1, 0))
        self.assertEqual((r["first_tool"], r["skill"]), ("Skill", "matt-pocock-workflow:trivial"))
        self.assertEqual(r["before"], ["Bash", "Edit(refused)"])

    def test_a_denial_before_the_verdict_is_counted_live_and_a_refusal_is_not_one(self):
        r = scan(INIT,
                 assistant(tool("Bash", id="t1", command="ls -la && git remote -v")),
                 denied("t1"),
                 tool_result("t1", "This command requires approval", error=True),
                 assistant(tool("Bash", id="t2", command="echo x >> README.md")),
                 denied("t2", "Seams gate: a shell command (`a redirect to a file`) changes the project"),
                 tool_result("t2", REFUSED, error=True),
                 assistant(tool("Skill", id="t3", skill="matt-pocock-workflow:trivial")),
                 tool_result("t3", "Launching skill: matt-pocock-workflow:trivial"))
        self.assertEqual((r["denials"], r["refusals"], r["failed_calls"]), (1, 1, 1))
        self.assertEqual((r["first_tool"], r["skill"]), ("Skill", "matt-pocock-workflow:trivial"))

    def test_an_error_result_is_a_failed_call_and_a_failed_change_is_not_the_commit(self):
        r = scan(INIT,
                 assistant(tool("Bash", id="t1", command="npm test")),
                 tool_result("t1", "Exit code 1\nFAIL tests/pricing.test.ts", error=True),
                 assistant(tool("Edit", id="t2", file_path="src/pricing.ts", old_string="x", new_string="y")),
                 tool_result("t2", "String to replace not found in file.", error=True),
                 assistant(tool("Skill", id="t3", skill="tdd")),
                 tool_result("t3", "Launching skill: tdd"))
        self.assertEqual((r["failed_calls"], r["refusals"]), (2, 0))
        self.assertEqual((r["first_tool"], r["skill"], r["before"]), ("Skill", "tdd", ["Bash", "Edit(failed)"]))

    def test_a_change_that_goes_through_before_any_declaration_is_undeclared(self):
        r = scan(INIT,
                 assistant(tool("Edit", id="t1", file_path="src/pricing.ts", old_string="x", new_string="y")),
                 tool_result("t1", "The file src/pricing.ts has been updated successfully."))
        self.assertEqual((r["first_tool"], r["undeclared"], r["ended"]), ("Edit", 1, "verdict"))

    def test_a_change_after_a_declaration_is_guarded(self):
        r = scan(INIT,
                 assistant(tool("Skill", id="t1", skill="matt-pocock-workflow:trivial")),
                 tool_result("t1", "Launching skill: matt-pocock-workflow:trivial"),
                 assistant(tool("Edit", id="t2", file_path="src/format.ts", old_string="x", new_string="y")),
                 tool_result("t2", "The file src/format.ts has been updated successfully."),
                 past_skill=True)
        self.assertEqual((r["first_tool"], r["skill"], r["undeclared"]), ("Edit", "matt-pocock-workflow:trivial", 0))

    def test_a_failed_skill_invocation_is_recorded_as_such(self):
        failed = scan(INIT,
                      assistant(tool("Skill", id="t1", skill="matt-pocock-workflow:code-review")),
                      tool_result("t1", "Unknown skill: matt-pocock-workflow:code-review", error=True))
        ran = scan(INIT,
                   assistant(tool("Skill", id="t1", skill="code-review")),
                   tool_result("t1", "Launching skill: code-review"))
        self.assertEqual((failed["skill"], failed["skill_failed"], failed["failed_calls"]),
                         ("matt-pocock-workflow:code-review", True, 1))
        self.assertEqual((ran["skill"], ran["skill_failed"]), ("code-review", False))
        self.assertIsNone(scan(INIT, assistant(tool("Skill", skill="tdd")))["skill_failed"])

    def test_the_reply_records_denials_and_the_result_state(self):
        r = scan(INIT,
                 assistant(text("Done.")),
                 {"type": "result", "subtype": "success", "result": "Done.", "is_error": False,
                  "usage": {"output_tokens": 42}, "total_cost_usd": 0.1,
                  "permission_denials": [{"tool_name": "Bash", "tool_use_id": "t9"}]})
        self.assertEqual((r["denials"], r["result_subtype"], r["result_error"], r["output_tokens"], r["ended"]),
                         (1, "success", False, 42, "reply"))
        self.assertEqual(scan(INIT, assistant(tool("Skill", skill="tdd")))["denials"], 0)


class RunRecordTest(unittest.TestCase):
    """How a run ended, from run_once with a stub `claude` on PATH: the process exit code, a
    timeout, a reply, or a stop at the confirmed verdict."""

    SKILL_STREAM = [INIT, assistant(tool("Skill", id="t1", skill="diagnosing-bugs")),
                    tool_result("t1", "Launching skill: diagnosing-bugs")]

    def run_with_stub(self, script: str, timeout: float = 5.0) -> dict:
        harness = load_harness()
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            stub = root / "bin" / "claude"
            stub.parent.mkdir()
            stub.write_text("#!/bin/sh\n" + script)
            stub.chmod(stub.stat().st_mode | stat.S_IEXEC)
            saved = os.environ["PATH"]
            os.environ["PATH"] = f"{stub.parent}:{saved}"
            try:
                return harness.run_once("cosmetic-edit", "plugin", "fix it", root / "run", timeout,
                                        past_skill=False, superpowers=False, grace=0.5,
                                        prepare=lambda scenario, run_dir: (run_dir / "workspace").mkdir(parents=True))
            finally:
                os.environ["PATH"] = saved

    @staticmethod
    def emit(*events: dict) -> str:
        return "".join(f"echo '{json.dumps(e)}'\n" for e in events)

    def test_a_process_that_exits_without_a_result_is_recorded_with_its_code(self):
        r = self.run_with_stub(self.emit(INIT) + "exit 3\n")
        self.assertEqual((r["ended"], r["exit_code"], r["first_tool"], r["timed_out"]), ("exit", 3, None, False))

    def test_a_timeout_is_recorded(self):
        r = self.run_with_stub(self.emit(INIT) + "sleep 30\n", timeout=0.5)
        self.assertEqual((r["ended"], r["timed_out"]), ("timeout", True))

    def test_a_reply_ends_the_run_with_exit_zero(self):
        r = self.run_with_stub(self.emit(INIT, {"type": "result", "subtype": "success", "result": "ok?",
                                                "is_error": False, "usage": {"output_tokens": 5},
                                                "permission_denials": []}))
        self.assertEqual((r["ended"], r["exit_code"], r["denials"]), ("reply", 0, 0))

    def test_a_process_that_hangs_after_its_reply_is_stopped_without_an_exit_code(self):
        reply = {"type": "result", "subtype": "success", "result": "ok", "is_error": False,
                 "usage": {"output_tokens": 5}, "permission_denials": []}
        r = self.run_with_stub(self.emit(INIT, reply) + "sleep 30\n")
        self.assertEqual((r["ended"], r["exit_code"]), ("reply", None))

    def test_a_run_stopped_at_its_verdict_says_so_whatever_the_kill_code(self):
        r = self.run_with_stub(self.emit(*self.SKILL_STREAM) + "sleep 30\n")
        self.assertEqual((r["ended"], r["first_tool"], r["skill"]), ("verdict", "Skill", "diagnosing-bugs"))
        self.assertNotEqual(r["exit_code"], 0)


def record(scenario: str, run: int, **fields: object) -> dict:
    """A run record as results.jsonl holds it: a clean routing verdict unless overridden."""
    base = {"scenario": scenario, "arm": "plugin", "run": run, "first_tool": "Skill", "skill": None,
            "skill_failed": False, "refusals": 0, "late_refusals": 0, "failed_calls": 0, "denials": 0,
            "undeclared": 0, "ended": "verdict", "exit_code": -15, "timed_out": False, "result": None,
            "result_subtype": None, "result_error": None, "output_tokens": None}
    return {**base, **fields}


def cli(cmd: str, *records: dict) -> "tuple[int, str]":
    """`behavior_test.py <cmd> results.jsonl` on these records: the exit status and the output."""
    with tempfile.TemporaryDirectory() as d:
        results = Path(d) / "results.jsonl"
        results.write_text("".join(json.dumps(r) + "\n" for r in records))
        out = subprocess.run([sys.executable, str(HARNESS), cmd, str(results)], capture_output=True, text=True)
    return out.returncode, out.stdout + out.stderr


def judge(*records: dict) -> "tuple[int, str]":
    return cli("judge", *records)


def report(*records: dict) -> "tuple[int, str]":
    return cli("report", *records)


class JudgeTest(unittest.TestCase):
    """A run matches its scenario's expectation file, misses it, or was not a run at all
    (an infrastructure error, listed apart and never counted as a match)."""

    TRIVIAL = "matt-pocock-workflow:trivial"

    def test_every_run_matching_exits_zero(self):
        code, report = judge(record("cosmetic-edit", 1, skill=self.TRIVIAL),
                             record("cosmetic-edit", 2, skill=self.TRIVIAL))
        self.assertEqual(code, 0, report)
        self.assertIn("cosmetic-edit", report)
        self.assertIn("2 of 2", report)

    def test_a_wrong_first_skill_is_a_miss_named_with_its_shortfall(self):
        code, report = judge(record("cosmetic-edit", 1, skill=self.TRIVIAL),
                             record("cosmetic-edit", 2, skill="matt-pocock-workflow:grill"),
                             record("cosmetic-edit", 3, skill=self.TRIVIAL))
        self.assertEqual(code, 1)
        self.assertIn("2 of 3", report)
        self.assertRegex(report, r"run 2:.*matt-pocock-workflow:grill.*expected matt-pocock-workflow:trivial")

    def test_infrastructure_errors_are_listed_apart_and_never_match(self):
        code, report = judge(record("cosmetic-edit", 1, skill=self.TRIVIAL, timed_out=True, ended="timeout"),
                             record("cosmetic-edit", 2, skill=None, first_tool=None, ended="exit", exit_code=1),
                             record("cosmetic-edit", 3, skill=None, first_tool=None, ended="reply", exit_code=0,
                                    result_subtype="success", result_error=False, output_tokens=0,
                                    result="You have hit your session limit."),
                             record("cosmetic-edit", 4, skill=self.TRIVIAL, ended="reply", exit_code=0,
                                    result_subtype="success", result_error=False, output_tokens=90, denials=2),
                             record("cosmetic-edit", 5, skill=self.TRIVIAL, ended="reply", exit_code=2,
                                    result_subtype="success", result_error=False, output_tokens=90))
        self.assertEqual(code, 1)
        self.assertIn("0 of 5", report)
        self.assertRegex(report, r"error\s+run 5: .*exited with code 2 after its reply")
        self.assertRegex(report, r"error\s+run 1: timed out")
        self.assertRegex(report, r"error\s+run 2: .*exit.*1")
        self.assertRegex(report, r"error\s+run 3: .*no tokens.*session limit")
        self.assertRegex(report, r"error\s+run 4: .*2 permission denials")
        self.assertNotIn("miss ", report)

    def test_a_failed_skill_call_and_an_undeclared_change_are_misses(self):
        code, report = judge(record("cosmetic-edit", 1, skill=self.TRIVIAL, skill_failed=True),
                             record("cosmetic-edit", 2, skill=self.TRIVIAL, undeclared=1, first_tool="Edit"),
                             record("cosmetic-edit", 3, skill=None, first_tool="Edit", undeclared=1))
        self.assertEqual(code, 1)
        self.assertRegex(report, r"miss\s+run 1: .*skill call failed")
        self.assertRegex(report, r"miss\s+run 2: .*1 change went through before any declaration")
        self.assertRegex(report, r"miss\s+run 3: no skill was invoked \(Edit\)")

    def test_a_refusal_is_a_miss_where_none_is_expected_and_counted_where_one_is(self):
        code, report = judge(record("cosmetic-edit", 1, skill=self.TRIVIAL, refusals=1))
        self.assertEqual(code, 1)
        self.assertRegex(report, r"miss\s+run 1: .*1 refusal")
        code, report = judge(record("gate-typo", 1, skill=self.TRIVIAL, refusals=1, first_tool="Edit"),
                             record("gate-typo", 2, skill=self.TRIVIAL, refusals=0, first_tool="Edit"))
        self.assertEqual(code, 0, report)
        self.assertIn("refusals in 1 of 2", report)
        code, report = judge(record("gate-typo", 1, skill=self.TRIVIAL, refusals=2, late_refusals=1))
        self.assertEqual(code, 1)
        self.assertRegex(report, r"miss\s+run 1: .*after the declaration")

    def test_an_expectation_may_name_several_acceptable_first_skills(self):
        verify = "matt-pocock-workflow:verification-before-completion"
        code, report = judge(record("gate-commit", 1, skill=verify, first_tool="Bash", label="git add"),
                             record("gate-commit", 2, skill=self.TRIVIAL, first_tool="Bash", label="git add"))
        self.assertEqual(code, 0, report)
        self.assertIn(f"{verify} or {self.TRIVIAL}", report)
        code, report = judge(record("gate-commit", 1, skill="matt-pocock-workflow:grill"))
        self.assertEqual(code, 1)
        self.assertRegex(report, r"miss\s+run 1: first skill matt-pocock-workflow:grill, expected " + verify)

    def test_a_scenario_without_an_expectation_file_fails_loudly(self):
        code, report = judge(record("no-such-scenario", 1, skill=self.TRIVIAL))
        self.assertEqual(code, 1)
        self.assertIn("no-such-scenario", report)
        self.assertIn("expect.json", report)


class ReportTest(unittest.TestCase):
    """The counts docs/plugin-behavior-tests.md carries come from the records by one command: a
    table row per scenario (runs, matched, runs with a refusal, failed calls, errors), the runs
    that did not match listed under it with the judge's reason, and the candidate and model the
    records name, so the document cannot say more than the records do."""

    TRIVIAL = "matt-pocock-workflow:trivial"

    def test_the_table_counts_each_scenario_from_its_records(self):
        code, out = report(
            record("cosmetic-edit", 1, skill=self.TRIVIAL, candidate="abc1234", model="claude-opus-5"),
            record("cosmetic-edit", 2, skill="matt-pocock-workflow:grill", candidate="abc1234", model="claude-opus-5"),
            record("gate-typo", 1, skill=self.TRIVIAL, first_tool="Edit", refusals=1, failed_calls=1,
                   candidate="abc1234", model="claude-opus-5"),
            record("gate-typo", 2, skill=self.TRIVIAL, first_tool="Edit", refusals=1, timed_out=True, ended="timeout",
                   candidate="abc1234", model="claude-opus-5"))
        self.assertEqual(code, 0, out)
        self.assertIn("| `cosmetic-edit` | `matt-pocock-workflow:trivial` | 2 | 1 | 0 | 0 | 0 |", out)
        self.assertIn("| `gate-typo` | `matt-pocock-workflow:trivial` | 2 | 1 | 2 | 1 | 1 |", out)
        self.assertRegex(out, r"`cosmetic-edit` run 2: miss, first skill matt-pocock-workflow:grill, expected")
        self.assertRegex(out, r"`gate-typo` run 2: error, timed out")
        self.assertIn("`abc1234`", out)
        self.assertIn("`claude-opus-5`", out)

    def test_several_candidates_or_models_are_all_named(self):
        code, out = report(record("cosmetic-edit", 1, skill=self.TRIVIAL, candidate="abc1234", model="claude-opus-5"),
                           record("cosmetic-edit", 2, skill=self.TRIVIAL, candidate="def5678", model="claude-opus-5-1"))
        self.assertEqual(code, 0, out)
        self.assertIn("`abc1234`", out)
        self.assertIn("`def5678`", out)
        self.assertIn("`claude-opus-5`", out)
        self.assertIn("`claude-opus-5-1`", out)

    def test_a_scenario_without_an_expectation_file_is_reported_not_counted(self):
        code, out = report(record("no-such-scenario", 1, skill=self.TRIVIAL))
        self.assertEqual(code, 1, out)
        self.assertIn("no-such-scenario", out)
        self.assertIn("expect.json", out)


def grader_frontmatter(path: Path) -> dict:
    """A grader file's frontmatter as a flat dict of raw string values (enough for these checks)."""
    text = path.read_text()
    assert text.startswith("---\n"), path
    head = text[4:text.index("\n---", 4)]
    return {k.strip(): v.strip() for k, v in (l.split(":", 1) for l in head.splitlines() if ":" in l)}


class EvalReportTest(unittest.TestCase):
    """scripts/eval_report.py turns `claude plugin eval --json` documents into the docs' table:
    with and without scores, Δ, runs per arm, errored runs; a later document replaces a case."""

    @staticmethod
    def doc(name: str, with_scores: list, without_scores: list, delta: float, error_on: int = -1) -> dict:
        runs = lambda scores: [{"score": s, "error": ("timed out" if i == error_on else None),
                                "graders": [{"name": "skill-fired", "passed": s >= 1, "scored": False}]}
                               for i, s in enumerate(scores)]
        return {"schemaVersion": 1, "partial": False, "cases": [{"name": name, "aggregates": {"score": sum(with_scores) / len(with_scores), "delta": delta},
                                                                 "arms": {"with": runs(with_scores), "without": runs(without_scores)}}]}

    def test_the_table_reads_scores_delta_runs_and_errors(self):
        spec = importlib.util.spec_from_file_location("eval_report", REPO / "scripts" / "eval_report.py")
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        out = module.report([self.doc("cosmetic-edit", [1, 1, 1], [0.5, 0.5, 0.5], 0.5, error_on=1)])
        self.assertIn("| `cosmetic-edit` | 1.00 | 0.50 | +0.50 | 3 of 3 | 3 | 2 |", out)

    def test_a_later_document_replaces_a_case(self):
        spec = importlib.util.spec_from_file_location("eval_report", REPO / "scripts" / "eval_report.py")
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        out = module.report([self.doc("gate-typo", [0.5, 0.5, 0.5], [0.5, 0.5, 0.5], 0.0),
                             self.doc("gate-typo", [1, 1, 1], [0, 0, 0], 1.0)])
        self.assertIn("| `gate-typo` | 1.00 | 0.00 | +1.00 | 3 of 3 | 3 | 0 |", out)
        self.assertEqual(out.count("`gate-typo`"), 1)


class ScenarioFilesTest(unittest.TestCase):
    """Every scenario is one directory under plugin/evals, shared by the harness and by
    `claude plugin eval`: a prompt (its frontmatter is the eval's, the harness sends the body),
    a setup and a scaffold, an expectation whose first skill is a declaration, and graders that
    agree with that expectation, so the two suites cannot drift apart."""

    def test_the_scenarios_live_in_the_plugin_beside_the_fixture(self):
        harness = load_harness()
        self.assertEqual(harness.SCENARIOS, harness.PLUGIN / "evals")
        self.assertTrue((harness.SCENARIOS / "_fixture" / "package.json").is_file())
        self.assertTrue((harness.SCENARIOS / "_shared" / "spec-coupons.md").is_file())
        for name in harness.all_scenarios():
            self.assertFalse(name.startswith("_") or name == "results", name)

    def test_every_scenario_has_its_files_and_a_declaration_to_expect(self):
        harness = load_harness()
        names = harness.all_scenarios()
        self.assertGreaterEqual(len(names), 10)
        for name in names:
            with self.subTest(scenario=name):
                folder = harness.SCENARIOS / name
                self.assertTrue((folder / "setup.sh").is_file(), "setup.sh")
                self.assertTrue((folder / "scaffold.sh").is_file(), "scaffold.sh")
                prompt = harness.prompt_text(name)
                self.assertTrue(prompt and not prompt.startswith("---"), "the prompt body, no frontmatter")
                self.assertTrue((folder / "prompt.md").read_text().startswith("---\n"), "eval frontmatter")
                expect = harness.expectation(name)
                self.assertIsNotNone(expect, "expect.json")
                for skill in expect["skill"]:
                    self.assertTrue(harness.gate.is_declaration(skill), skill)
                self.assertIsInstance(expect["refusal"], bool)
                self.assertGreater(expect["runs"], 0)

    def test_every_scenario_has_a_skill_grader_that_agrees_with_its_expectation(self):
        harness = load_harness()
        for name in harness.all_scenarios():
            with self.subTest(scenario=name):
                expect = harness.expectation(name)
                graders = [grader_frontmatter(p) for p in sorted((harness.SCENARIOS / name / "graders").glob("*.md"))]
                self.assertTrue(graders, "graders/")
                skill_graders = [g for g in graders if g.get("type") == "tool_used" and g.get("tool") == "Skill"]
                self.assertEqual(len(skill_graders), 1, "one tool_used: Skill grader")
                pattern = re.compile(skill_graders[0]["input_match"].strip("'\""))
                for skill in expect["skill"]:
                    self.assertTrue(pattern.search(json.dumps({"skill": skill})), f"input_match should match {skill}")
                    bare = skill.split(":", 1)[-1]
                    self.assertTrue(pattern.search(json.dumps({"skill": bare})), f"input_match should match bare {bare}")
                self.assertFalse(pattern.search(json.dumps({"skill": "superpowers:brainstorming"})),
                                 "input_match must not match a Superpowers skill")
                refusal = [g for g in graders if g.get("type") == "regex" and "Seams gate" in g.get("pattern", "")]
                if expect["refusal"]:
                    self.assertFalse(refusal, "a gate scenario allows a refusal, so no refusal grader")
                else:
                    self.assertEqual(len(refusal), 1, "one grader forbidding a refusal")
                    self.assertEqual(refusal[0].get("match"), "not_contains")

    def test_the_gate_scenarios_allow_a_refusal_and_run_past_the_skill(self):
        harness = load_harness()
        gates = [n for n in harness.all_scenarios() if n.startswith("gate-")]
        self.assertEqual(len(gates), 4, gates)
        for name in gates:
            expect = harness.expectation(name)
            self.assertTrue(expect["refusal"] and expect["past_skill"], name)


class PastSkillTest(unittest.TestCase):
    def test_skills_are_recorded_and_the_scan_continues(self):
        r = scan(INIT,
                 assistant(tool("Skill", skill="matt-pocock-workflow:grill")),
                 assistant(tool("Read", file_path="/mp/grilling/SKILL.md")),
                 assistant(tool("Skill", skill="domain-modeling")),
                 assistant(text("Which rounding rule should SAVE10 use?")),
                 result("Which rounding rule should SAVE10 use?\n- Math.round (Recommended)\n- floor"),
                 past_skill=True)
        self.assertIsNone(r["first_tool"])
        self.assertEqual(r["skill"], "matt-pocock-workflow:grill")
        self.assertEqual(r["skills"], ["matt-pocock-workflow:grill", "domain-modeling"])
        self.assertEqual(r["text_questions"], 1)

    def test_an_edit_still_stops_the_scan(self):
        r = scan(INIT,
                 assistant(tool("Skill", skill="matt-pocock-workflow:grill")),
                 assistant(tool("Edit", file_path="src/pricing.ts")),
                 assistant(tool("Skill", skill="tdd")),
                 past_skill=True)
        self.assertEqual((r["first_tool"], r["skills"]), ("Edit", ["matt-pocock-workflow:grill"]))


if __name__ == "__main__":
    unittest.main()
