---
description: "a routing scenario: the expected skill first, nothing changed before it, no refusal"
tags: [routing]
allowed_tools: [Read, Glob, Grep, Skill]
max_turns: 15
timeout_seconds: 300
---

Support says we sometimes oversell: when two customers check out the last unit of a SKU at the same time, both orders succeed. It's somewhere in src/inventory.ts (reserve). Please investigate and fix it properly.
