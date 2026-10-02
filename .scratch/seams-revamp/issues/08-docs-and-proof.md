# 08: Docs and proof

**What to build:** the user can read what 4.0.0 changed and see that it is no worse and faster. README, CHANGELOG and the compatibility record describe the continuous flow, the lasting route, the proportional process, the lighter hooks and the new suite. The eval scenarios run with `claude plugin eval` on 3.4.0 and on the candidate, and the cost of three scripted tasks (tool calls, tokens, wall time) is measured on both, each paid run asked first and the runs made one at a time.

**Blocked by:** 02 (No test sleeps), 05 (Lighter hooks), 07 (One shared reference, process in proportion).

**Status:** ready-for-agent

- [ ] No eval scenario scores lower on the candidate than on 3.4.0.
- [ ] The three tasks take fewer tool calls and no more tokens or wall time on the candidate, or the difference is explained.
- [ ] The results are recorded in the evidence docs with the date, the model and the Claude Code version.
- [ ] README and CHANGELOG say plainly that the flow no longer asks at each step and where it still stops.
- [ ] Must not happen: a paid run without the user's yes; several heavy runs at once on the user's Mac.

**How to verify:** the eval report for both versions side by side in the evidence docs; the measured table for the three tasks.
