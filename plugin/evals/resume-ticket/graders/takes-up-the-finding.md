---
type: regex
target: last_message
pattern: 'tier[- ]discounted|2,?040|1,?938|1,?438|102 cents'
flags: i
---

The reply takes up the review finding the progress file records: FLAT5's minimum is checked against the tier-discounted total instead of the subtotal (20 units at 102 cents: a 2040-cent subtotal, 1938 after the tier, 1438 by the spec). Those words and numbers are only in the uncommitted progress file; the ticket and the spec say "post-tier total" and "subtotal", so the pattern leaves those out, and a session that started the ticket over, or re-ran its review from nothing, would not name the finding.
