# 06: pr-review under the cap, scripts without prompts

**What to build:** `pr-review`'s instructions fit whole in what compaction keeps:
- **The core:** a SKILL.md under the size bound (11,000 bytes, about 4,000 tokens), with its gates, must-nots and steps first.
- **References:** batch mode, checks, drafting and posting, and cleanup move to reference files. The core names each one with a "read this when…" line.
- **Scripts:** its bundled scripts are referenced through `${CLAUDE_SKILL_DIR}` and pre-approved in `allowed-tools`, so they never prompt.
- **Limits:** the claim that subagents can't start subagents is replaced by Claude Code's real limits.

This split prefactors tickets 07 and 08.

**Blocked by:** 01 (Release 3.2.1)

**Status:** ready-for-agent

- [ ] `pr-review`'s SKILL.md is at most 11,000 bytes, and `claude plugin details` shows its on-invoke cost at or under 4,000 tokens.
- [ ] Every reference file is named in the core's first screen, together with when to read it. Guidance that must hold for the whole review is written as standing instructions.
- [ ] Its scripts are referenced through `${CLAUDE_SKILL_DIR}` in the body and in `allowed-tools` rules. A headless run in default permission mode runs them without a permission denial.
- [ ] Limits:
  - Subagents can nest three levels deep by default.
  - At most 20 run concurrently.
  - Wide fan-outs can hit rate limits.
- [ ] Must not happen: behaviour is lost in the split. The existing `pr-review` tests and the static test's `pr-review` checks still pass. Every rule in 3.2.1's SKILL.md is present in the core or a reference, checked item by item in the ticket's comments.
- [ ] Stale `__pycache__` in the `pr-review` scripts is removed.

**How to verify:**
- `scripts/test.sh`.
- `claude plugin details matt-pocock-workflow@my-workflow-agent-skills` for the on-invoke figure.
- A headless `/pr-review` run on a throwaway pull request in this repository, with writes to GitHub blocked as in 3.2.1's live runs. It must show the scripts running without prompts.
