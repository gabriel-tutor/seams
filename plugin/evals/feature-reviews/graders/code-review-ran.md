---
type: tool_order
before: { tool: Skill, input_match: '"skill"\s*:\s*"(?:matt-pocock-workflow:)?(?:implement)"' }
after: { tool: Skill, input_match: '"skill"\s*:\s*"code-review"' }
---

The review ran Matt Pocock's `code-review` (Standards and Spec) after implement took up the ticket: both calls happen, implement's first.
