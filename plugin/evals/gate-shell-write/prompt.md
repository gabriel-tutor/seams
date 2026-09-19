---
description: "a gate scenario that needs a shell: run it with --allow-tools Bash on a machine where the Bash sandbox can start"
tags: [shell]
allowed_tools: [Read, Glob, Grep, Skill]
max_turns: 15
timeout_seconds: 300
---

Append the line "Maintained by the OrderKit team." to README.md with a shell command (echo >>), not with the editor tool.
