---
type: regex
target: trace
pattern: '^(?:(?!"name"\s*:\s*"Skill")[\s\S])*"name"\s*:\s*"(?:Edit|Write|MultiEdit|NotebookEdit)"'
match: not_contains
---

No editor call before the first Skill call: the route comes before any change. The no-plugin baseline fails this whenever it edits first, which is what the plugin is for. A shell write before the skill is not caught here; the routing harness classifies those.
