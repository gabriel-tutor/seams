"""The eval scenarios under plugin/evals, run by `claude plugin eval` (.scratch/seams-revamp, ticket 01).

Each scenario is one directory: a prompt whose frontmatter is the eval's, a setup and a scaffold, an expectation
(expect.json, the scenario's own statement of what a run must do) and graders that agree with it, so the graders
`claude plugin eval` scores cannot drift from what the scenario expects. These checks came from the retired
routing harness's tests; the harness is gone, the scenarios and their contract stay."""
import json
import re
import sys
import unittest
from pathlib import Path

sys.dont_write_bytecode = True
REPO = Path(__file__).resolve().parents[2]
PLUGIN = REPO / "plugin"
SCENARIOS = PLUGIN / "evals"
sys.path.insert(0, str(PLUGIN / "hooks"))
import seams_gate as gate  # noqa: E402  (what counts as a declaration)


def all_scenarios() -> list:
    """Every case directory, with its prompt or without; `_fixture`, `_shared` and `results` are not cases."""
    return sorted(p.name for p in SCENARIOS.iterdir() if p.is_dir() and not p.name.startswith(("_", ".")) and p.name != "results")


def expectation(scenario: str) -> dict:
    """expect.json with its defaults; a key that may hold one name or several always holds a list."""
    data = json.loads((SCENARIOS / scenario / "expect.json").read_text())
    skill = data.get("skill")
    data["skill"] = [skill] if isinstance(skill, str) else list(skill or [])
    for key in ("reads", "agents", "skills", "tasks"):
        value = data.get(key)
        data[key] = [value] if isinstance(value, str) else list(value or [])
    return {"refusal": False, "past_skill": False, "runs": 5, "reply": [], "changes": False, **data}


def grader_frontmatter(path: Path) -> dict:
    """A grader file's frontmatter as a flat dict of raw string values (enough for these checks)."""
    text = path.read_text()
    assert text.startswith("---\n"), path
    head = text[4:text.index("\n---", 4)]
    return {k.strip(): v.strip() for k, v in (line.split(":", 1) for line in head.splitlines() if ":" in line)}


def graders(scenario: str) -> list:
    return [grader_frontmatter(p) for p in sorted((SCENARIOS / scenario / "graders").glob("*.md"))]


def pattern(value: str) -> "re.Pattern":
    return re.compile(value.strip("'\""))


class ScenarioFilesTest(unittest.TestCase):

    def test_the_scenarios_live_in_the_plugin_beside_the_fixture(self):
        self.assertTrue((SCENARIOS / "_fixture" / "package.json").is_file())
        self.assertTrue((SCENARIOS / "_shared" / "spec-coupons.md").is_file())
        for name in all_scenarios():
            self.assertFalse(name.startswith("_") or name == "results", name)

    def test_every_scenario_has_its_files_and_a_declaration_to_expect(self):
        names = all_scenarios()
        self.assertGreaterEqual(len(names), 10)
        for name in names:
            with self.subTest(scenario=name):
                folder = SCENARIOS / name
                for f in ("prompt.md", "setup.sh", "scaffold.sh", "case.yaml"):
                    self.assertTrue((folder / f).is_file(), f)
                prompt = (folder / "prompt.md").read_text()
                self.assertTrue(prompt.startswith("---\n"), "eval frontmatter")
                self.assertTrue(prompt[prompt.index("\n---", 4) + 4:].strip(), "a prompt body after the frontmatter")
                expect = expectation(name)
                for skill in expect["skill"]:
                    self.assertTrue(gate.is_declaration(skill), skill)
                self.assertIsInstance(expect["refusal"], bool)
                self.assertGreater(expect["runs"], 0)

    def test_every_scenario_has_a_skill_grader_that_agrees_with_its_expectation(self):
        for name in all_scenarios():
            with self.subTest(scenario=name):
                expect, found = expectation(name), graders(name)
                self.assertTrue(found, "graders/")
                skill_graders = [g for g in found if g.get("type") == "tool_used" and g.get("tool") == "Skill"]
                self.assertEqual(len(skill_graders), 1, "one tool_used: Skill grader")
                match = pattern(skill_graders[0]["input_match"])
                for skill in expect["skill"]:
                    self.assertTrue(match.search(json.dumps({"skill": skill})), f"input_match should match {skill}")
                    bare = skill.split(":", 1)[-1]
                    self.assertTrue(match.search(json.dumps({"skill": bare})), f"input_match should match bare {bare}")
                self.assertFalse(match.search(json.dumps({"skill": "superpowers:brainstorming"})),
                                 "input_match must not match a Superpowers skill")
                refusal = [g for g in found if g.get("type") == "regex" and "Seams gate" in g.get("pattern", "")]
                if expect["refusal"]:
                    self.assertFalse(refusal, "a gate scenario allows a refusal, so no refusal grader")
                else:
                    self.assertEqual(len(refusal), 1, "one grader forbidding a refusal")
                    self.assertEqual(refusal[0].get("match"), "not_contains")

    def test_a_scenario_that_expects_an_agent_has_an_agent_grader_that_agrees(self):
        # A plugin's agent cannot run without the plugin, so its grader is an indicator (arm: with-only), as the
        # Skill grader is, and never pushes the no-plugin arm's score down.
        shipped = {f"matt-pocock-workflow:{p.stem}" for p in (PLUGIN / "agents").glob("*.md")}
        expecting = []
        for name in all_scenarios():
            with self.subTest(scenario=name):
                expect = expectation(name)
                agent_graders = [g for g in graders(name) if g.get("type") == "tool_used" and g.get("tool") == "Agent"]
                self.assertEqual(bool(agent_graders), bool(expect["agents"]), "an Agent grader exactly where agents are expected")
                for agent in expect["agents"]:
                    self.assertIn(agent, shipped)
                    matching = [g for g in agent_graders if pattern(g["input_match"]).search(json.dumps({"subagent_type": agent}))]
                    self.assertTrue(matching, f"no Agent grader matches {agent}")
                    for g in matching:
                        self.assertEqual(g.get("arm"), "with-only")
                        for other in ("general-purpose", "Explore", "scout-helper"):
                            self.assertFalse(pattern(g["input_match"]).search(json.dumps({"subagent_type": other})), other)
                    expecting.append(name)
        self.assertIn("grill-fact-finding", expecting)

    def test_the_skills_a_scenario_expects_after_the_first_have_graders(self):
        # A scenario holds one Skill grader, on its first skill, so a later skill it expects (code-review in a build's
        # review) is graded by a tool_order whose `after` names it.
        expecting = []
        for name in all_scenarios():
            expect = expectation(name)
            if not expect["skills"]:
                continue
            with self.subTest(scenario=name):
                afters = [re.search(r"input_match:\s*'([^']*)'", g.get("after", "")) for g in graders(name)
                          if g.get("type") == "tool_order"]
                for skill in expect["skills"]:
                    self.assertTrue(any(m and re.search(m.group(1), json.dumps({"skill": skill})) for m in afters),
                                    f"no tool_order grader has {skill} after the first skill")
                expecting.append(name)
        self.assertEqual(sorted(expecting), ["feature-reviews", "sensitive-reviews"])

    def test_the_tasks_a_scenario_expects_have_graders_that_agree(self):
        # A build's review starts reviewer agents that differ only by what each is asked; a resumed parallel run starts
        # a builder named for its ticket and told its worktree. On sample calls, the expectation's `tasks` and the
        # eval's task graders agree on which calls count.
        reviewer = "matt-pocock-workflow:reviewer"
        calls = [{"subagent_type": reviewer, "description": f"{axis.capitalize()} review",
                  "prompt": f"Review 1a2b3c4...HEAD on the {axis} axis."} for axis in ("correctness", "security", "standards", "spec")]
        calls += [{"subagent_type": reviewer, "description": "Standards review",
                   "prompt": "Review 1a2b3c4...HEAD against the standards; correctness and security are reviewed apart."},
                  {"subagent_type": reviewer, "description": "CORRECTNESS REVIEW", "prompt": "Review 1a2b3c4...HEAD."}]
        calls += [{"subagent_type": "general-purpose", "description": f"Build ticket {n}",
                   "prompt": f"Build ticket {n} of shop-basics in the worktree /ws/.claude/worktrees/shop-basics-{n}."}
                  for n in ("02", "03")]
        calls += [{"subagent_type": "general-purpose", "description": "Build ticket 03", "prompt": "Build ticket 03 of shop-basics."}]
        expecting = []
        for name in all_scenarios():
            expect = expectation(name)
            if not expect["tasks"]:
                continue
            with self.subTest(scenario=name):
                found = graders(name)
                agent_graders = [pattern(g["input_match"]) for g in found if g.get("type") == "tool_used" and g.get("tool") == "Agent"]
                task_graders = [m for m in agent_graders if not m.search(json.dumps({"subagent_type": reviewer}))]
                task_graders += [pattern(g["pattern"]) for g in found
                                 if g.get("type") == "regex" and g.get("target") == "trace" and g.get("match") != "not_contains"]
                self.assertTrue(task_graders, "a scenario that expects tasks has a grader for them")
                for call in calls:
                    task = "\n".join(call[k] for k in ("subagent_type", "description", "prompt"))
                    wanted = any(re.search(p, task) for p in expect["tasks"])
                    graded = any(m.search(json.dumps(call)) for m in task_graders)
                    self.assertEqual(wanted, graded, f"the expectation and the graders disagree on: {call}")
                expecting.append(name)
        self.assertEqual(sorted(expecting), ["feature-reviews", "resume-parallel", "sensitive-reviews"])

    def test_the_gate_scenarios_allow_a_refusal_and_run_past_the_skill(self):
        gates = [n for n in all_scenarios() if n.startswith("gate-")]
        self.assertEqual(len(gates), 4, gates)
        for name in gates:
            expect = expectation(name)
            self.assertTrue(expect["refusal"] and expect["past_skill"], name)


if __name__ == "__main__":
    unittest.main()
