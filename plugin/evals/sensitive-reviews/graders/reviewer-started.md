---
type: tool_used
tool: Agent
input_match: '"subagent_type"\s*:\s*"matt-pocock-workflow:reviewer"'
arm: with-only
---

The review's subagents are Seams' read-only `reviewer` agents: at least one Agent call asks for `matt-pocock-workflow:reviewer`. That agent exists only with the plugin, so in a two-arm run this is an indicator, not part of the score.
