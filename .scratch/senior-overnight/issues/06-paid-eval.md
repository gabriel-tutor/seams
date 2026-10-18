# 06: One paid eval of an unattended night

**What to build:** proof, before release, that an unattended night on a sample repository routes every ticket through the Seams flow, records its auto-answers and claims, and merges only what passes.

**Blocked by:** 01, 02, 05.

**Status:** ready-for-agent

**Changed (decision 22):** no paid eval; the first real `sleepclaude` night is the proof, its morning summary and progress files checked against the criteria below (the eval-only criteria, the eval and its cost question, fall away).

- [ ] A `claude plugin eval` scenario runs an unattended night on a sample repository with two small tickets.
- [ ] It passes when: each builder invoked a routing skill before changing code; the progress files have Auto-answered entries; the morning summary lists outward claims with sources; nothing merged that failed its checks.
- [ ] The run is asked for before it starts, with its cost.
- [ ] Must not happen: a run started without that yes.

**How to verify:** the eval's report (`claude plugin eval` output), with its graders' results.
