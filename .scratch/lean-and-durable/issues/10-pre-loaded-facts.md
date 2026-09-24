# 10: Pre-loaded facts

**What to build:** `implement`, the grill and `release` start with the facts they always look up already in hand:
- the branch;
- the short HEAD;
- the first lines of `git status --short`;
- the list of progress files.

These arrive through `` !`cmd` `` lines that can't fail and are pre-approved. When shell injection is disabled, each skill still works and says how to get the facts another way.

**Blocked by:** 08 (Every skill under the bound, lighter always-on cost)

**Status:** ready-for-agent

- [ ] Only fixed, read-only commands are injected. Each is written so it can't fail, and each is pre-approved in the skill's `allowed-tools`.
- [ ] Must not happen:
  - a user argument appears inside an injected command;
  - an injected command aborts the skill, for example because the directory isn't a git repository, there are no progress files, or `disableSkillShellExecution` is on.
- [ ] The static test checks every injected command against the read-only list and the never-fail rule.
- [ ] A headless run of each of the three skills shows the facts in its first message and no permission abort. With `disableSkillShellExecution: true`, each skill still completes.
- [ ] Every edited skill stays within the size bound.

**How to verify:**
- `scripts/test.sh`.
- Headless runs of each skill in a fixture copy, first as is and then with `--settings '{"disableSkillShellExecution": true}'`.
