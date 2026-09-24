---
type: regex
target: last_message
pattern: 'tier discount[\s\S]*out[- ]of[- ]stock|out[- ]of[- ]stock[\s\S]*tier discount'
flags: i
---

The reply takes up both questions the progress file records as open: the tier discount order, and what happens to the held amount when checkout fails out of stock. The second follows from a decision recorded only in that file, so a grill that started over would not ask it. They are independent, so the grill asks them in the same round.
