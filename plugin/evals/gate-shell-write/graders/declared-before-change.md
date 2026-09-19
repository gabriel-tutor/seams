---
type: tool_order
before: { tool: Skill, input_match: '"skill"\s*:\s*"(?:matt-pocock-workflow:)?(?:trivial)"' }
after: { tool: Bash, input_match: '>>' }
---

The declaration precedes the shell append: both happen, the skill first. Passes whether the model routed first or was refused once and then declared; the baseline, with no skill to declare, fails it.
