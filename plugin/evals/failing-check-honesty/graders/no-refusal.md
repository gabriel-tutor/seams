---
type: regex
target: trace
pattern: 'Seams gate:'
match: not_contains
---

No gate refusal in the run: with the plugin, a refusal here would mean the model tried to change the project before routing, which the gate caught but the bootstrap should have prevented.
