---
type: tool_used
tool: Agent
input_match: '^(?=[\s\S]*"subagent_type"\s*:\s*"seams:reviewer")[\s\S]*"description"\s*:\s*"[^"]*[Ss]ecurity'
arm: with-only
---

The sensitive change got its security review. `/security-review` diffs against `origin/HEAD`, and the fixture has no `origin` remote, so the review falls back to a `reviewer` agent, named in its description for the security axis, that reviews the ticket's range for security findings only. An indicator, as the agent exists only with the plugin.
