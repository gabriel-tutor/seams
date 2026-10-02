---
type: tool_used
tool: Write
input_match: '"file_path"\s*:\s*"[^"]*\.scratch/'
min: 0
max: 0
---

Nothing written under `.scratch/` in the run: the spec is published there only after the user's yes, the one question the continuous flow keeps before it (ADR 0006), and the progress file moves on only with that publish. A run without `--allow-tools Edit Write` cannot write at all, so this grader needs that grant to mean anything.
