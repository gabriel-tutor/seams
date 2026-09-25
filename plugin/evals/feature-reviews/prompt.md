---
description: "a review scenario: a feature ticket's build is committed on main and its review is next, so implement's review runs Matt Pocock's code-review and a correctness review by the reviewer agent; it needs a shell for git, so run it with --allow-tools Bash where the sandbox starts, and the harness with --timeout 900"
tags: [review]
allowed_tools: [Read, Glob, Grep, Skill, Agent, Bash]
max_turns: 30
timeout_seconds: 900
---

Carry on with ticket 01 of the low-stock report on main: its build is committed, and its review is next.
