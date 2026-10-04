---
type: tool_used
tool: Agent
input_match: '"subagent_type"\s*:\s*"seams:scout"'
arm: with-only
---

The grill found its facts through the agent it names, Seams' read-only `scout`: at least one Agent call asks for `seams:scout`. That agent exists only with the plugin, so in a two-arm run this is an indicator, not part of the score.
