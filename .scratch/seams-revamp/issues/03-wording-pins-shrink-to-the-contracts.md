# 03: Wording pins shrink to the contracts

**What to build:** rewording a skill or the README no longer breaks the suite. The static test keeps only the contracts Claude Code and the routing rely on: skill and reference size bounds, frontmatter fields, the routing table's rows, the injected commands, the version's single source, the third-party notices, the manifests and checksums. The roughly 750 phrase pins go.

**Blocked by:** 01 (A suite that runs in under a minute).

**Status:** ready-for-agent

- [ ] Each remaining pin guards a contract named above; each removed one is listed by kind in the commit.
- [ ] Rewording a sentence in a skill that changes no contract leaves the suite green (shown by doing it in a scratch copy).
- [ ] Must not happen: a skill over its size bound, a frontmatter field Claude Code needs missing, a routing row changed, or an injected command added, without a failing test.

**How to verify:** `scripts/test.sh` green; in a scratch copy, reword a skill sentence (green) and drop a routing row (red).
