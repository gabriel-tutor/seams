# 08: Every skill under the bound, lighter always-on cost

**What to build:** Every Seams skill fits whole in what compaction keeps, and every session starts lighter:
- **The guard:** a static guard enforces the size bound and forbids model and effort pins.
- **Descriptions:** each leads with its trigger, and together they shrink by about a quarter.
- **The bootstrap:** it states the routing as the project's facts with no out-of-band framing, and states the quality bar, within its 2,900-byte cap.
- **The version:** it lives only in `plugin.json`.

**Blocked by:** 06 (pr-review under the cap, scripts without prompts)

**Status:** ready-for-agent

- [ ] The static test fails the build when:
  - any SKILL.md exceeds 11,000 bytes;
  - any SKILL.md or agent sets `model` or `effort`;
  - the marketplace entry carries a version.
- [ ] Every SKILL.md is within the bound, with its gates, must-nots and steps first. `release`, `to-tickets` and `finishing-a-development-branch` are checked, and trimmed if needed.
- [ ] `claude plugin details` shows always-on cost at or under 875 tokens (from about 1,165).
- [ ] The injected bootstrap:
  - has no `<EXTREMELY_IMPORTANT>` wrapper and no imperative out-of-band framing;
  - states every routing row and rule, plus the quality bar, as the project's facts;
  - stays at or under 2,900 bytes.
- [ ] Each skill says which extras it skips at low effort, read from `${CLAUDE_EFFORT}`. It never skips a gate or a check.
- [ ] Must not happen: routing gets worse. Every routing and gate eval case keeps its score. The eval run is paid, so ask first.

**How to verify:**
- `scripts/test.sh`.
- `claude plugin details matt-pocock-workflow@my-workflow-agent-skills`.
- `claude plugin eval plugin --tag routing --tag gate --scaffold --allow-tools Edit Write --model <model> -j 3`, compared with the recorded 3.1 scores. The run is paid, so ask first.
