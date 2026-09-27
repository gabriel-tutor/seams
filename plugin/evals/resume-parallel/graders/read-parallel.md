---
type: tool_used
tool: Read
input_match: 'implement/references/parallel\.md'
arm: with-only
---

The run read implement's parallel reference, which says how a run resumes: each ticket's recorded state checked against git, the pending tickets started first, then the built ones integrated. The file ships with the plugin, so in a two-arm run this is an indicator, not part of the score.
