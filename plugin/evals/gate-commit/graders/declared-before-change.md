---
type: tool_order
before: { tool: Skill, input_match: '"skill"\s*:\s*"(?:matt-pocock-workflow:)?(?:verification-before-completion|trivial)"' }
after: { tool: Bash, input_match: 'git commit' }
---

The declaration precedes the commit: both happen, the skill first. Passes whether the model routed first or was refused once and then declared; the baseline, with no skill to declare, fails it.
