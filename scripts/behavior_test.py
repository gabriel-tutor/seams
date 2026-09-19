#!/usr/bin/env python3
"""Headless routing probe for the matt-pocock-workflow plugin (spec: Testing Decisions, 5).

It measures which route a fresh session takes, not whether the work it then does is right:
a run's verdict is its first committing call, a Skill or AskUserQuestion call (a process
choice) or a change to the run's workspace (straight to code: an Edit/Write there, or a shell
command the gate's own classifier labels a mutation). Everything before it is exploration,
including writes outside the workspace (a throwaway script in /tmp). A committing call is
confirmed by its result: a call the gate refused (an error result carrying the gate's reason,
which starts with `Seams gate:`), or a change that failed, changed nothing, so it is counted
(`refusals`, `failed_calls`) and the scan goes on.

  behavior_test.py run --scenario S [--scenario T | --scenario all] --arm plugin|control
                       [--runs N] [--jobs 5] [--past-skill] [--superpowers] [--prompt TEXT]
                       [--label NAME] [--timeout 300] [--out DIR] [--assert]
      Runs `claude -p` in fresh fixture workspaces (scripts/prepare_run.sh S), with --settings
      allowing reads of Matt Pocock's skill files, the fixture's checks and a commit in the
      workspace, and disabling Superpowers (--superpowers keeps the user's own setting),
      adding --plugin-dir plugin for the plugin arm. Each run ends at its confirmed verdict,
      at the end of the reply, or at the timeout. Keeps every raw stream, appends one record
      per run to <out>/results.jsonl, prints a summary. The prompt, the run count and
      --past-skill default to plugin/evals/S/{prompt.md,expect.json}: the same directory
      `claude plugin eval` runs as a case (prompt.md's frontmatter is the eval's; the harness
      sends the body).
      --assert judges every run against expect.json (the first skill expected; `refusal`,
      whether a gate refusal is allowed) and exits 1 when any run is short, naming each miss
      and, apart from them, each run that was not a run at all: a timeout, a process that
      exited without a result, an error result, a reply with no tokens, a permission denial by
      the harness's own settings.

  behavior_test.py judge RESULTS.jsonl [...]
      The same judgement on saved records.

  behavior_test.py report RESULTS.jsonl [...]
      The counts docs/plugin-behavior-tests.md carries, from saved records, as Markdown: one
      row per scenario (runs, matched, runs with a refusal, failed calls, errors), the runs
      that did not match under it with the judge's reason, and the candidate and model the
      records name. Exits 1 only when a scenario has no expectation file.

  behavior_test.py scan [--past-skill] [--workspace DIR] STREAM
      Prints the record for a saved stream-json file.

With --past-skill, Skill calls are recorded (in order, as `skills`) but do not stop the run,
so a test can see what the skill does next: for the grill, its first question; for a gate
scenario, whether the change goes through once the route is declared. Headless runs have no
AskUserQuestion, so a question arrives as the reply; `text_questions` counts the question
marks in it, a formatting heuristic and not a count of decisions asked. `superpowers_skills`
counts the superpowers: skills the run loaded. `undeclared` counts changes that went through
before any declaration (what the gate exists to prevent, measured live); `denials` counts the
platform's permission denials (its `permission_denied` events and the result's list), less
the gate's own refusals.
"""
from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import sys
import tempfile
import threading
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Optional

REPO = Path(__file__).resolve().parent.parent
PLUGIN = REPO / "plugin"
PREPARE = REPO / "scripts" / "prepare_run.sh"
SCENARIOS = PLUGIN / "evals"                 # the scenarios, shared with `claude plugin eval`
EDIT_TOOLS = {"Edit", "Write", "MultiEdit", "NotebookEdit"}

sys.dont_write_bytecode = True                 # no __pycache__ in the plugin directory
sys.path.insert(0, str(PLUGIN / "hooks"))
import seams_gate as gate  # noqa: E402  (the gate's classifier: a shell write scores as the gate scores it)


def settings(superpowers: bool) -> str:
    """--settings for a run. Read access to Matt Pocock's skill files (the entries in
    ~/.claude/skills are symlinks, and permission checks use the resolved ~/.skills-manager
    path) and to the plugin's own reference files; a leading // makes a Read rule absolute.
    The fixture's own checks and a commit are allowed so a gate scenario can run to its end in
    the throwaway workspace, and the read-only forms the platform's own allowlist does not
    cover when they appear in a compound command (`git -C <path> status`, `echo "exit: $?"`,
    `ls`, `find`; the ticket-10 evidence set lost three runs to them); anything else the model
    runs is the platform's call to deny, and a denial makes the run an error, not a miss.
    Superpowers is forced off unless the run keeps the user's own setting."""
    allow = ["Read(~/.claude/skills/**)", "Read(~/.skills-manager/**)", f"Read(/{PLUGIN}/**)",
             "Bash(npm test:*)", "Bash(npm run typecheck:*)", "Bash(npx vitest:*)", "Bash(npx tsc:*)",
             "Bash(git add:*)", "Bash(git commit:*)",
             "Bash(git status:*)", "Bash(git diff:*)", "Bash(git log:*)", "Bash(git -C:*)",
             "Bash(echo:*)", "Bash(ls:*)", "Bash(find:*)"]
    config: dict = {"permissions": {"allow": allow}}
    if not superpowers:
        config["enabledPlugins"] = {"superpowers@claude-plugins-official": False}
    return json.dumps(config)


def _result_text(block: dict) -> str:
    """A tool_result's text, whether it came as a string or as content blocks."""
    content = block.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(b.get("text") or "" for b in content if isinstance(b, dict))
    return ""


class Scanner:
    """Follows one run's stream-json events up to its first committing call.

    A committing call is taken as the verdict when it is made and confirmed by its result: a
    call the gate refused (an error result carrying the gate's reason, `Seams gate: ...`) or a
    change that failed did not change anything, so it is counted and the scan goes on. A new
    turn of the model, which only follows the results, confirms too; a stream that ends before
    the result leaves the verdict as made.
    """

    def __init__(self, past_skill: bool = False, workspace: Optional[Path] = None):
        self.past_skill = past_skill
        self.workspace = workspace.resolve() if workspace else None
        self.record = {"model": None, "superpowers_skills": None, "first_tool": None, "label": None,
                       "skill": None, "skills": [], "skill_failed": None, "questions": None,
                       "before": [], "refusals": 0, "late_refusals": 0, "failed_calls": 0, "denials": 0,
                       "undeclared": 0, "text": "", "result": None, "result_subtype": None,
                       "result_error": None, "output_tokens": None, "text_questions": None,
                       "cost_usd": None, "ended": None}
        self.pending: dict = {}                # tool_use id -> what the call was
        self.awaiting: Optional[str] = None    # the verdict's call, until its result confirms it
        self.awaiting_message: Optional[str] = None
        self.first_skill_id: Optional[str] = None
        self.declared = False                  # a declaration went through
        self.denied_ids: set = set()           # the platform's permission denials, by call
        self.refused_ids: set = set()          # the gate's refusals, by call: never denials
        self.stopped = False

    def feed_line(self, line: str) -> bool:
        """Take one raw stream line, skipping anything that is not a JSON object."""
        try:
            event = json.loads(line)
        except ValueError:
            return False
        return self.feed(event)

    def feed(self, event: object) -> bool:
        """Take one event; True once the verdict is confirmed or the reply has ended."""
        if self.stopped or not isinstance(event, dict):
            return self.stopped
        kind = event.get("type")
        if kind == "system" and event.get("subtype") == "init":
            self.record["model"] = event.get("model")
            self.record["superpowers_skills"] = sum(
                1 for s in event.get("skills") or [] if isinstance(s, str) and s.startswith("superpowers:"))
        elif kind == "system" and event.get("subtype") == "permission_denied":
            self.denied_ids.add(event.get("tool_use_id"))
            self._count_denials()
        elif kind == "result":
            self._reply(event)
            self.stopped = True
        elif kind == "assistant":
            message = event.get("message") or {}
            if self.awaiting is not None and message.get("id") != self.awaiting_message:
                # a new turn of the model, which only follows the results: the call went through
                self._confirm(self.awaiting, self.pending.pop(self.awaiting))
                return True
            content = message.get("content")
            for block in content if isinstance(content, list) else []:
                if not isinstance(block, dict):
                    continue
                if block.get("type") == "text" and block.get("text"):
                    self.record["text"] = "\n".join(filter(None, (self.record["text"], block["text"])))
                elif block.get("type") == "tool_use":
                    self._call(block, message.get("id"))
        elif kind == "user":
            content = (event.get("message") or {}).get("content")
            for block in content if isinstance(content, list) else []:
                if isinstance(block, dict) and block.get("type") == "tool_result":
                    self._returned(block)
                    if self.stopped:
                        break
        return self.stopped

    def _count_denials(self) -> None:
        """The platform's permission denials, less any the gate made (a refusal is a decision
        of the plugin under test, a denial one of the harness's settings)."""
        self.record["denials"] = len(self.denied_ids - self.refused_ids)

    def _reply(self, event: dict) -> None:
        denials = event.get("permission_denials")
        for denial in denials if isinstance(denials, list) else []:
            if isinstance(denial, dict):
                self.denied_ids.add(denial.get("tool_use_id"))
        self._count_denials()
        usage = event.get("usage") if isinstance(event.get("usage"), dict) else {}
        self.record.update({
            "result": event.get("result"),
            "text_questions": (event.get("result") or "").count("?"),
            "cost_usd": event.get("total_cost_usd"),
            "result_subtype": event.get("subtype"),
            "result_error": bool(event.get("is_error")),
            "output_tokens": usage.get("output_tokens"),
            "ended": self.record["ended"] or "reply",
        })

    def _call(self, block: dict, message_id: Optional[str]) -> None:
        """A tool call: exploration is recorded now; a committing call is the verdict until its
        result says otherwise."""
        name, inputs, call_id = block.get("name"), block.get("input") or {}, block.get("id")
        info = {"name": name, "label": None, "change": False, "skill": None, "ask": False}
        if name in EDIT_TOOLS:
            if self._outside_workspace(inputs):
                self.record["before"].append(f"{name}(outside)")
            else:
                info["change"] = True
        elif name == "Bash":
            info["label"] = gate.classify_command(inputs.get("command") or "")
            info["change"] = bool(info["label"])
            if not info["change"]:
                self.record["before"].append(name)
        elif name == "Skill":
            info["skill"] = inputs.get("skill")
            self.record["skills"].append(info["skill"])
            if self.record["skill"] is None:
                self.record["skill"], self.first_skill_id = info["skill"], call_id
        elif name == "AskUserQuestion":
            info["ask"] = True
            self.record["questions"] = len(inputs.get("questions") or [])
        else:
            self.record["before"].append(name)
        self.pending[call_id] = info
        if self._commits(info) and self.awaiting is None and self.record["first_tool"] is None:
            self._take(call_id, info, message_id)

    def _commits(self, info: dict) -> bool:
        return info["change"] or info["ask"] or (info["skill"] is not None and not self.past_skill)

    def _take(self, call_id: Optional[str], info: dict, message_id: Optional[str] = None) -> None:
        self.record["first_tool"], self.record["label"] = info["name"], info["label"]
        self.awaiting, self.awaiting_message = call_id, message_id

    def _retract(self) -> None:
        self.record["first_tool"], self.record["label"] = None, None
        self.awaiting, self.awaiting_message = None, None

    def _returned(self, block: dict) -> None:
        """A call's result confirms the verdict, or counts a refusal or a failure."""
        call_id = block.get("tool_use_id")
        info = self.pending.pop(call_id, None)
        error = bool(block.get("is_error"))
        refused = error and gate.REFUSAL_PREFIX in _result_text(block)
        if refused:
            self.record["refusals"] += 1
            self.refused_ids.add(call_id)
            self._count_denials()
            if self.declared:                  # the gate should be open: a refusal now is a defect
                self.record["late_refusals"] += 1
        elif error:
            self.record["failed_calls"] += 1
        if info is None:
            return
        if info["skill"] is not None:
            if call_id == self.first_skill_id:
                self.record["skill_failed"] = error
            if not error and gate.is_declaration(info["skill"]):
                self.declared = True
        if not self._commits(info):
            return
        if error and not info["ask"]:                  # nothing happened: not the verdict
            if info["change"]:
                self.record["before"].append(f"{info['name']}({'refused' if refused else 'failed'})")
                if call_id == self.awaiting:
                    self._retract()
                return
        if call_id != self.awaiting:                   # the verdict retracted earlier; this one is it
            if self.record["first_tool"] is not None:
                return
            self._take(call_id, info)
        self._confirm(call_id, info)

    def _confirm(self, call_id: Optional[str], info: dict) -> None:
        if info["change"] and not self.declared:
            self.record["undeclared"] += 1
        self.record["ended"] = "verdict"
        self.awaiting, self.awaiting_message, self.stopped = None, None, True

    def _outside_workspace(self, inputs: dict) -> bool:
        """True for an edit whose target lies outside the run's workspace."""
        raw = inputs.get("file_path") or inputs.get("notebook_path")
        if self.workspace is None or not raw:
            return False
        path = Path(raw)
        if not path.is_absolute():
            path = self.workspace / path
        return not path.resolve().is_relative_to(self.workspace)


def scan(stream: Path, past_skill: bool = False, workspace: Optional[Path] = None) -> dict:
    scanner = Scanner(past_skill, workspace)
    for line in stream.read_text().splitlines():
        if scanner.feed_line(line):
            break
    return scanner.record


def stop(proc: subprocess.Popen, sig: int) -> None:
    """Signal the run's whole process group (claude plus the MCP servers it started), falling
    back to claude alone when the group cannot be signalled (macOS can refuse with EPERM)."""
    try:
        os.killpg(proc.pid, sig)
    except ProcessLookupError:
        pass
    except OSError:
        try:
            proc.send_signal(sig)
        except OSError:
            pass


def prepare_workspace(scenario: str, run_dir: Path) -> None:
    """A fresh fixture copy at the scenario's baseline, in <run_dir>/workspace."""
    subprocess.run([str(PREPARE), scenario, str(run_dir)], check=True, capture_output=True)


def run_once(scenario: str, arm: str, prompt: str, run_dir: Path, timeout: float,
             past_skill: bool, superpowers: bool, prepare=prepare_workspace, grace: float = 15) -> dict:
    """One headless run. The record says how it ended: `verdict` (stopped once the verdict was
    confirmed), `reply` (the result event arrived, and claude was given `grace` seconds to exit
    on its own so `exit_code` is its own; None when it had to be stopped), `timeout`, or `exit` (the
    process ended without a result, `exit_code` says how)."""
    run_dir.mkdir(parents=True, exist_ok=True)
    prepare(scenario, run_dir)
    workspace = run_dir / "workspace"
    cmd = ["claude", "-p", prompt, "--output-format", "stream-json", "--verbose",
           "--permission-mode", "acceptEdits", "--settings", settings(superpowers)]
    if arm == "plugin":
        cmd += ["--plugin-dir", str(PLUGIN)]
    scanner, expired = Scanner(past_skill, workspace), threading.Event()
    started = time.monotonic()
    with open(run_dir / "stream.jsonl", "w") as raw, open(run_dir / "stderr.txt", "w") as err:
        proc = subprocess.Popen(cmd, cwd=workspace, stdin=subprocess.DEVNULL,
                                stdout=subprocess.PIPE, stderr=err, text=True, start_new_session=True)
        timer = threading.Timer(timeout, lambda: (expired.set(), stop(proc, signal.SIGKILL)))
        timer.start()
        killed = False
        try:
            for line in proc.stdout:
                raw.write(line)
                if scanner.feed_line(line):
                    break
        finally:
            timer.cancel()
            if proc.poll() is None and scanner.record["ended"] == "reply" and not expired.is_set():
                try:                           # the reply is out: let claude exit on its own
                    proc.wait(timeout=grace)
                except subprocess.TimeoutExpired:
                    pass
            if proc.poll() is None:
                killed = True
                stop(proc, signal.SIGTERM)
                try:
                    proc.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    stop(proc, signal.SIGKILL)
                    proc.wait()
            proc.stdout.close()
    record = dict(scanner.record)
    if expired.is_set():
        record["ended"] = "timeout"
    elif record["ended"] is None:
        record["ended"] = "exit"
    # The exit code is claude's own after a reply; a process the harness stopped has none to judge.
    exit_code = None if (killed and record["ended"] == "reply") else proc.returncode
    return {**record, "exit_code": exit_code, "seconds": round(time.monotonic() - started),
            "timed_out": expired.is_set(), "stream": str(run_dir / "stream.jsonl")}


def verdict(record: dict) -> str:
    if record["first_tool"] == "Skill":
        return f"Skill {record['skill']}"
    if record["first_tool"] == "Bash":
        return f"Bash ({record.get('label')})"
    if record["first_tool"]:
        return record["first_tool"]
    if record.get("timed_out"):
        return "timeout"
    return "reply" if record["result"] is not None else "no commit"


def prompt_text(scenario: str) -> str:
    """The prompt the scenario sends: plugin/evals/<scenario>/prompt.md without the eval's
    frontmatter block."""
    text = (SCENARIOS / scenario / "prompt.md").read_text()
    if text.startswith("---\n"):
        end = text.find("\n---", 4)
        if end != -1:
            text = text[end + 4:]
    return text.strip()


def expectation(scenario: str) -> Optional[dict]:
    """plugin/evals/<scenario>/expect.json: the first skill the scenario expects (`skill`, one
    name or a list of acceptable ones), whether a gate refusal is allowed in it (`refusal`),
    whether runs continue past skill calls (`past_skill`), and how many runs its evidence
    takes (`runs`). None when there is none."""
    path = SCENARIOS / scenario / "expect.json"
    if not path.is_file():
        return None
    data = json.loads(path.read_text())
    skill = data.get("skill")
    data["skill"] = [skill] if isinstance(skill, str) else list(skill or [])    # one, or any of several
    return {"refusal": False, "past_skill": False, "runs": 5, **data}


def _first_line(text: Optional[str]) -> str:
    return (text or "").strip().splitlines()[0][:120] if (text or "").strip() else ""


def _plural(count: int, noun: str) -> str:
    if count == 1:
        return f"{count} {noun}"
    return f"{count} {noun}es" if noun.endswith("s") else f"{count} {noun}s"


def judge_run(record: dict, expect: dict) -> "tuple[str, str]":
    """One run against its expectation: ("match", ""), ("miss", why) or ("error", why).

    An error is the run not being a run: the harness or the platform got in the way, so it
    says nothing about the routing either way and is listed apart. A miss is the model doing
    something other than what the expectation says.
    """
    if record.get("timed_out"):
        return "error", "timed out"
    if record.get("ended") == "exit":
        return "error", f"claude exited with code {record.get('exit_code')} before any result"
    if record.get("ended") == "reply" and record.get("exit_code") not in (0, None):
        return "error", f"claude exited with code {record.get('exit_code')} after its reply"
    subtype = record.get("result_subtype")
    if record.get("result_error") or (subtype is not None and subtype != "success"):
        return "error", f"the result was an error ({subtype}): {_first_line(record.get('result'))}"
    if record.get("output_tokens") == 0:
        return "error", f"the reply carried no tokens: {_first_line(record.get('result'))}"
    denials = record.get("denials") or 0
    if denials:
        return "error", f"{_plural(denials, 'permission denial')}: the harness settings blocked a call the model made"
    skill, first_tool, expected = record.get("skill"), record.get("first_tool"), " or ".join(expect["skill"])
    if skill is None:
        what = first_tool or ("replied" if record.get("ended") == "reply" else "no committing call")
        return "miss", f"no skill was invoked ({what}); expected {expected}"
    if record.get("skill_failed"):
        return "miss", f"the first skill call failed: {skill}"
    if skill not in expect["skill"]:
        return "miss", f"first skill {skill}, expected {expected}"
    undeclared = record.get("undeclared") or 0
    if undeclared:
        return "miss", f"{_plural(undeclared, 'change')} went through before any declaration"
    if record.get("late_refusals"):
        return "miss", "the gate refused a call after the declaration"
    refusals = record.get("refusals") or 0
    if refusals and not expect["refusal"]:
        return "miss", f"{_plural(refusals, 'refusal')}: a change was attempted before the route"
    return "match", ""


def outcomes_by_scenario(records: list) -> list:
    """The records grouped by scenario, each judged against its expectation file: a list of
    (scenario, expect, outcomes, tally), `expect` None when the scenario has no expectation
    file (then `outcomes` and `tally` are empty), `outcomes` the (record, kind, why) triples
    from `judge_run`, and `tally` the counts a report needs: runs, matched, misses, errors,
    refused (runs with a refusal) and failed (failed calls)."""
    by_scenario: dict = {}
    for r in records:
        by_scenario.setdefault(r.get("scenario"), []).append(r)
    grouped = []
    for scenario, runs in by_scenario.items():
        expect = expectation(scenario or "")
        if expect is None:
            grouped.append((scenario, None, [], {"runs": len(runs)}))
            continue
        outcomes = [(r, *judge_run(r, expect)) for r in runs]
        tally = {"runs": len(runs),
                 "matched": sum(1 for _, kind, _ in outcomes if kind == "match"),
                 "misses": sum(1 for _, kind, _ in outcomes if kind == "miss"),
                 "errors": sum(1 for _, kind, _ in outcomes if kind == "error"),
                 "refused": sum(1 for r in runs if r.get("refusals")),
                 "failed": sum(r.get("failed_calls") or 0 for r in runs)}
        grouped.append((scenario, expect, outcomes, tally))
    return grouped


def judge_records(records: list) -> "tuple[bool, str]":
    """Every scenario in `records` against its expectation file. True when each one has
    every run matching; the report names each shortfall, misses and errors apart."""
    lines, ok = [], True
    for scenario, expect, outcomes, tally in outcomes_by_scenario(records):
        if expect is None:
            lines.append(f"== {scenario}: no expectation file (plugin/evals/{scenario}/expect.json)")
            ok = False
            continue
        policy = "a refusal allowed" if expect["refusal"] else "no refusal"
        lines.append(f"== {scenario}: expected first skill {' or '.join(expect['skill'])}, {policy}; "
                     f"{tally['matched']} of {tally['runs']} runs matched; refusals in {tally['refused']} of {tally['runs']}")
        for r, kind, why in outcomes:
            if kind != "match":
                lines.append(f"   {kind:6} run {r.get('run')}: {why}")
        if tally["matched"] < tally["runs"]:
            ok = False
            lines.append(f"FAIL: {scenario} short by {tally['runs'] - tally['matched']} "
                         f"({_plural(tally['misses'], 'miss')}, {_plural(tally['errors'], 'error')})")
        else:
            lines.append(f"PASS: {scenario} {tally['matched']} of {tally['runs']}")
    return ok, "\n".join(lines)


def _named(items: "list[str]") -> str:
    """Each item in backticks, comma-separated; `unknown` when there are none."""
    return ", ".join(f"`{item}`" for item in items) or "unknown"


def report_records(records: list) -> "tuple[bool, str]":
    """The counts docs/plugin-behavior-tests.md carries, from the records, so the document
    cannot say more than they do: a Markdown table with one row per scenario (runs, matched,
    runs with a refusal, failed calls, errors), the runs that did not match listed under it
    with the judge's reason, and the candidates and models the records name. False when a
    scenario has no expectation file."""
    candidates = sorted({r.get("candidate") for r in records if r.get("candidate")})
    models = sorted({r.get("model") for r in records if r.get("model")})
    lines = [f"Candidate: {_named(candidates)}; model: {_named(models)}; {_plural(len(records), 'run')}.", "",
             "| Scenario | Expected first skill | Runs | Matched | Refused | Failed calls | Errors |",
             "| --- | --- | --- | --- | --- | --- | --- |"]
    notes, ok = [], True
    for scenario, expect, outcomes, tally in outcomes_by_scenario(records):
        if expect is None:
            lines.append(f"| `{scenario}` | no expectation file (plugin/evals/{scenario}/expect.json) "
                         f"| {tally['runs']} | | | | |")
            ok = False
            continue
        lines.append(f"| `{scenario}` | {' or '.join(f'`{s}`' for s in expect['skill'])} | {tally['runs']} "
                     f"| {tally['matched']} | {tally['refused']} | {tally['failed']} | {tally['errors']} |")
        notes += [f"- `{scenario}` run {r.get('run')}: {kind}, {why}" for r, kind, why in outcomes if kind != "match"]
    if notes:
        lines += ["", "Runs that did not match:", ""] + notes
    return ok, "\n".join(lines)


def print_summary(label: str, arm: str, out: Path, records: list) -> None:
    print(f"{label} [{arm}] x{len(records)} -> {out}")
    for r in records:
        before = ",".join(r["before"]) or "-"
        skills = ",".join(s or "?" for s in r["skills"]) or "-"
        marks = "-" if r["text_questions"] is None else r["text_questions"]
        print(f"  run {r['run']}: {verdict(r):40} skills={skills:44.44} ?={marks!s:<3}"
              f" sp={r['superpowers_skills']!s:<3} before={before:24.24} {r['seconds']:>4}s"
              f"  refused={r.get('refusals', 0)} failed={r.get('failed_calls', 0)} denied={r.get('denials', 0)}"
              f" ended={r.get('ended')}({r.get('exit_code')})")
    counts = Counter(verdict(r) for r in records)
    print("  first committing call: " + ", ".join(f"{k} x{v}" for k, v in counts.most_common()))


def candidate() -> Optional[str]:
    """The plugin revision under test: this repository's HEAD, when git can say."""
    try:
        return subprocess.run(["git", "-C", str(REPO), "rev-parse", "--short", "HEAD"], capture_output=True,
                              text=True, check=True).stdout.strip() or None
    except (OSError, subprocess.CalledProcessError):
        return None


def all_scenarios() -> list:
    """Every case directory under plugin/evals; `_fixture`, `_shared` and `results` are not cases."""
    return sorted(p.parent.name for p in SCENARIOS.glob("*/prompt.md") if not p.parent.name.startswith("_"))


def run_scenario(args, scenario: str, sha: Optional[str]) -> list:
    """Every run of one scenario, records appended to <out>/results.jsonl."""
    expect = expectation(scenario)
    runs = args.runs or (expect["runs"] if expect else 5)
    past_skill = args.past_skill or bool(expect and expect["past_skill"])
    prompt = args.prompt or prompt_text(scenario)
    label = scenario if not args.label else (args.label if len(args.scenario) == 1 else f"{args.label}-{scenario}")
    if args.out:
        out = args.out if len(args.scenario) == 1 else args.out / scenario
    else:
        out = Path(tempfile.mkdtemp(prefix=f"mpw-{label}-{args.arm}-"))
    out.mkdir(parents=True, exist_ok=True)

    def one(n: int) -> dict:
        record = run_once(scenario, args.arm, prompt, out / f"{args.arm}-{n}", args.timeout, past_skill,
                          args.superpowers)
        return {"label": label, "scenario": scenario, "arm": args.arm, "superpowers": args.superpowers,
                "candidate": sha, "run": n, **record}

    with ThreadPoolExecutor(max_workers=args.jobs) as pool:
        records = list(pool.map(one, range(1, runs + 1)))
    with open(out / "results.jsonl", "a") as f:
        for record in records:
            f.write(json.dumps(record) + "\n")
    print_summary(label, args.arm, out, records)
    return records


def main(argv: Optional[list] = None) -> int:
    parser = argparse.ArgumentParser(description="Headless behavior tests for the plugin.")
    sub = parser.add_subparsers(dest="cmd", required=True)
    scan_p = sub.add_parser("scan", help="print the record for a saved stream")
    scan_p.add_argument("--past-skill", action="store_true")
    scan_p.add_argument("--workspace", type=Path)
    scan_p.add_argument("stream", type=Path)
    judge_p = sub.add_parser("judge", help="judge saved results.jsonl records against their expectation files")
    judge_p.add_argument("results", type=Path, nargs="+")
    report_p = sub.add_parser("report", help="the docs' counts table, as Markdown, from saved results.jsonl records")
    report_p.add_argument("results", type=Path, nargs="+")
    run_p = sub.add_parser("run", help="run headless sessions and record their first commits")
    run_p.add_argument("--scenario", action="append", required=True,
                       help="a scenario under plugin/evals (repeatable), or `all`")
    run_p.add_argument("--arm", choices=("plugin", "control"), required=True)
    run_p.add_argument("--runs", type=int, help="default: the scenario's expect.json `runs`, else 5")
    run_p.add_argument("--jobs", type=int, default=5)
    run_p.add_argument("--past-skill", action="store_true")
    run_p.add_argument("--superpowers", action="store_true",
                       help="keep the user's own Superpowers setting instead of forcing it off")
    run_p.add_argument("--prompt")
    run_p.add_argument("--label")
    run_p.add_argument("--timeout", type=float, default=300)
    run_p.add_argument("--out", type=Path)
    run_p.add_argument("--assert", dest="check", action="store_true",
                       help="judge the runs against each scenario's expect.json; exit 1 when any run is short")
    args = parser.parse_args(argv)

    if args.cmd == "scan":
        print(json.dumps(scan(args.stream, args.past_skill, args.workspace)))
        return 0
    if args.cmd in ("judge", "report"):
        records = [json.loads(line) for path in args.results for line in path.read_text().splitlines()
                   if line.strip()]
        ok, text = (judge_records if args.cmd == "judge" else report_records)(records)
        print(text)
        return 0 if ok else 1

    if args.scenario == ["all"]:
        args.scenario = all_scenarios()
    sha = candidate()
    records = [r for scenario in args.scenario for r in run_scenario(args, scenario, sha)]
    if not args.check:
        return 0
    ok, report = judge_records(records)
    print()
    print(report)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
