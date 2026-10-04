---
type: tool_used
tool: Skill
input_match: '"skill"\s*:\s*"(?:seams:)?(?:pr-review)"'
---

The expected first skill, `pr-review`, was invoked at least once: a GitHub pull request named by number is its to review, not `code-review`'s. In a two-arm run this is the plugin-fired indicator, not part of the score.
