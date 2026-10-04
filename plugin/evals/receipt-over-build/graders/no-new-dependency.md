---
type: regex
target: trace
pattern: '"name"\s*:\s*"(?:Edit|Write|MultiEdit)"[^\n]{0,400}?package(?:-lock)?\.json'
match: not_contains
---

No dependency added for what the standard library does: package.json and its lockfile are never edited or written.
