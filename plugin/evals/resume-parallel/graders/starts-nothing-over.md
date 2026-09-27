---
type: regex
target: trace
pattern: 'Build ticket 0[12]'
match: not_contains
---

No builder for ticket 01, which is integrated, or for ticket 02, which is built and waits only for its integration: a resumed run starts nothing over.
