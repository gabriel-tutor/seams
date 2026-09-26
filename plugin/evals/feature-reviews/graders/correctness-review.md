---
type: tool_used
tool: Agent
input_match: '^(?=[\s\S]*"subagent_type"\s*:\s*"matt-pocock-workflow:reviewer")[\s\S]*"description"\s*:\s*"[^"]*[Cc]orrectness'
arm: with-only
---

The build got a correctness review besides `code-review`'s two axes: a `reviewer` agent was started for the correctness axis, which its description names. Claude can't invoke the bundled `/review` while Matt Pocock's `code-review` holds its name (the Skill tool answers "Unknown skill: review"), so this agent is the correctness review. An indicator, as the agent exists only with the plugin.
