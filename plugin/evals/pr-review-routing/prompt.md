---
description: "a routing scenario: a GitHub pull request to review goes to pr-review, which Claude may start since 3.3.1; the expected skill first, nothing changed before it, no refusal"
tags: [routing]
allowed_tools: [Read, Glob, Grep, Skill]
max_turns: 15
timeout_seconds: 300
---

Can you review pull request #5 in this repository on GitHub and tell me whether it's ready to merge?
