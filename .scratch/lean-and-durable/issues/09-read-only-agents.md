# 09: Read-only agents and explicit delegation

**What to build:** Seams ships two read-only agents. Each has a turn cap and pins no model, effort or permission mode.
- **`scout`:** exploration, docs lookups and fact-finding. Its tools are Read, Glob, Grep, WebFetch and WebSearch, and it skips CLAUDE.md.
- **`reviewer`:** correctness or security review of a named diff. Its tools are Read, Glob, Grep and Bash, with no Edit, Write or NotebookEdit.

The gate refuses any project change either agent attempts. The grill, `to-spec`, `implement` and `foundations` say when to delegate and which agent to use, and start independent reads in parallel. Naming the agent matters: on Opus 5, Claude Code tells Claude not to spawn subagents unless asked.

**Blocked by:** 08 (Every skill under the bound, lighter always-on cost)

**Status:** ready-for-agent

- [ ] Both agents pass `claude plugin validate --strict`, and their tool lists are exactly as specified. They return conclusions with file:line or URL citations, and say what they couldn't confirm.
- [ ] Must not happen: a project change attempted by either agent goes through, even with a declaration in the ledger. Examples: a `reviewer` running `git commit`, or a `scout` writing through any tool.
- [ ] Each skill names the agent to use and when:
  - the grill for fact-finding;
  - `to-spec` for exploring the repository;
  - `implement` for reading beyond a few files, and for reviews;
  - `foundations` for its survey.

  Independent reads start together.
- [ ] Every edited skill stays within the size bound.
- [ ] A new or extended eval case shows the grill's fact-finding done by `scout`, through a `tool_used` grader on `Agent`.

**How to verify:**
- `scripts/test.sh` runs the static checks and the gate's unit cases for these agent types.
- `claude plugin validate --strict plugin`.
- The eval case through `claude plugin eval`. The run is paid, so ask first.
