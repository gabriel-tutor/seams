"""Unattended mode (.scratch/sleep-unattended): when a launcher sets SEAMS_UNATTENDED=1, no one answers, so every
stop of the flow takes its recommended option and is recorded, the hard gates stay closed, and every builder runs
the flow itself. Tested through the text the skills read and the hooks that switch it on: the shared rules' section,
each stopping skill's pointer to it, the session start's notice and the subagent start's brief. The gate's part
(a builder needs its own route) is in test_gate.py.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
PLUGIN = REPO / "plugin"
RULES = PLUGIN / "skills" / "using-matt-pocock-skills" / "references" / "rules.md"
# using-git-worktrees stops too (a worktree's consent), but it stays byte-identical to its Superpowers original: the
# rule names that stop itself.
STOPPING_SKILLS = ("grill", "to-spec", "to-tickets", "implement", "finishing-a-development-branch", "release",
                   "foundations", "incident", "pr-review")


def run_hook(name: str, event: dict, unattended: bool) -> dict:
    home = tempfile.mkdtemp()
    env = {k: v for k, v in os.environ.items() if k not in ("SEAMS_UNATTENDED", "CLAUDE_CONFIG_DIR")}
    env.update(HOME=home, CLAUDE_PLUGIN_ROOT=str(PLUGIN), PYTHONDONTWRITEBYTECODE="1")
    if unattended:
        env["SEAMS_UNATTENDED"] = "1"
    done = subprocess.run([sys.executable, str(PLUGIN / "hooks" / name)], input=json.dumps(event),
                          capture_output=True, text=True, env=env, timeout=30, cwd=home)
    subprocess.run(["rm", "-rf", home])
    if done.returncode != 0:
        raise AssertionError(f"{name} exited {done.returncode}: {done.stderr}")
    return json.loads(done.stdout) if done.stdout.strip() else {}


def context(output: dict) -> str:
    return (output.get("hookSpecificOutput") or {}).get("additionalContext") or ""


class UnattendedRule(unittest.TestCase):

    def setUp(self):
        text = RULES.read_text()
        self.assertIn("## Unattended mode", text)
        self.section = text.split("## Unattended mode", 1)[1].split("\n## ", 1)[0]

    def test_the_rule_answers_with_the_recommended_option_and_records_it(self):
        for words in ("SEAMS_UNATTENDED=1", "recommended", "## Auto-answered", "a yes recorded in a file",
                      "a worktree's consent"):
            with self.subTest(words=words):
                self.assertIn(words, self.section)

    def test_the_hard_gates_stay_closed(self):
        for words in ("main or master", "deploy", "publishing a package", "installing software", "paid run",
                      "destructive", "BLOCKED"):
            with self.subTest(words=words):
                self.assertIn(words, self.section)

    def test_a_builder_routes_itself_and_carries_its_verification(self):
        for words in ("invokes the skill", "verification-before-completion", "never merges", "evidence, never answers"):
            with self.subTest(words=words):
                self.assertIn(words, self.section)

    def test_the_night_starts_by_reconciling_and_the_morning_lists_its_outward_claims(self):
        # senior-overnight ticket 02 (decisions 8 and 9): no builder starts on a stale record, and each claim the night
        # made to a person reaches the morning with what it rests on.
        for words in ("`seams:reconcile`", "before any builder starts", "the memories the night reads", "the card",
                      "## Outward claims", "the morning summary lists", "with its source"):
            with self.subTest(words=words):
                self.assertIn(words, self.section)

    def test_every_skill_that_stops_points_at_the_rule(self):
        for skill in STOPPING_SKILLS:
            with self.subTest(skill=skill):
                texts = " ".join(p.read_text() for p in (PLUGIN / "skills" / skill).rglob("*.md"))
                self.assertIn("(shared rules: Unattended mode)", texts)


class SwitchedOnByTheEnvironment(unittest.TestCase):

    def test_the_session_start_says_so_only_when_it_is_on(self):
        event = {"session_id": "s1", "hook_event_name": "SessionStart", "source": "startup"}
        on, off = run_hook("session-start", event, True), run_hook("session-start", event, False)
        self.assertIn("Unattended mode is on", context(on))
        self.assertIn("unattended", (on.get("systemMessage") or "").lower())
        self.assertNotIn("Unattended mode is on", context(off))

    def test_a_builder_is_briefed_and_a_read_only_agent_is_not(self):
        builder = {"session_id": "s1", "hook_event_name": "SubagentStart", "agent_id": "a1",
                   "agent_type": "general-purpose"}
        brief = context(run_hook("subagent-start", builder, True))
        self.assertTrue(brief.startswith("## Unattended mode is on"))
        for words in ("If you were started to build or fix a ticket", "the skill your instructions name", "Skill tool",
                      "verification-before-completion", "Auto-answered", "Never merge"):
            with self.subTest(words=words):
                self.assertIn(words, brief)
        scout = dict(builder, agent_type="seams:scout")
        self.assertEqual(context(run_hook("subagent-start", scout, True)), "")
        self.assertEqual(context(run_hook("subagent-start", builder, False)), "")

    def test_the_subagent_start_hook_is_registered(self):
        hooks = json.loads((PLUGIN / "hooks" / "hooks.json").read_text())["hooks"]
        commands = [h for entry in hooks.get("SubagentStart", []) for h in entry["hooks"]]
        self.assertTrue(any("subagent-start" in " ".join(h.get("args", [])) for h in commands), hooks.get("SubagentStart"))


if __name__ == "__main__":
    unittest.main()
