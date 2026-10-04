---
type: tool_used
tool: Edit
input_match: '"file_path"\s*:\s*"[^"]*package(?:-lock)?\.json"'
min: 0
max: 0
---

No dependency added for what the standard library does: package.json and its lockfile are never edited.
