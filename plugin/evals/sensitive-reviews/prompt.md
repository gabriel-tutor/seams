---
description: "a review scenario: a sensitive ticket's build (a permission check) is committed on main and its review is next, so implement's review adds a security review; the fixture has no origin remote, so /security-review can't run and the reviewer agent reviews for security findings only; it needs a shell for git, so run it with --allow-tools Bash where the sandbox starts, and the harness with --timeout 900"
tags: [review]
allowed_tools: [Read, Glob, Grep, Skill, Agent, Bash]
max_turns: 30
timeout_seconds: 900
---

Carry on with ticket 01 of manager-only price overrides on main: its build is committed, and its review is next.
