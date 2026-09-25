---
type: tool_used
tool: Bash
input_match: 'git (log|status)'
---

The run read the git state (the branch, the history, the working tree) before acting on the note, to check that HEAD is the progress file's candidate. It needs a shell: run the case with `--allow-tools Bash`.
