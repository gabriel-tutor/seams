# 07: One shared reference, process in proportion

**What to build:** a skill loads less and never contradicts another: every rule several skills repeated lives once in a shared reference (the effort line's meaning, the repository facts, the progress-file rules, the sensitive list, the stages, the evidence rule, the worktree rule, the docs rule), and each skill points to it at the step that needs it. A table there says how much process a change gets by size and risk: a one-line fix one check, a feature or anything sensitive the full set. Code that uses a third-party library, framework, platform, CLI or API is checked against its official docs for the version in use, and cited. Scouts run on Sonnet 5.5; reviewers keep the session's model. `pr-review` only points to the reference.

**Blocked by:** 03 (Wording pins shrink to the contracts), 06 (A continuous flow).

**Status:** ready-for-agent

- [ ] Each repeated rule appears once; the two contradictions are resolved there (evidence on the same commit is reused; one worktree rule).
- [ ] The proportional table exists and the skills follow it: scouts only when a question needs facts the conversation lacks; two reviewers for a feature, one check for a one-line fix; the sensitive list always gets both reviews, the security review and verification.
- [ ] The docs rule is in the bootstrap and the reference.
- [ ] `scout` declares Sonnet 5.5; `reviewer` declares no model.
- [ ] `pr-review`'s steps, scripts, references and checks are byte-for-byte 3.4.0's apart from the pointer.
- [ ] The total size of the skills drops, measured; every skill stays within its bound.
- [ ] Must not happen: a sensitive change judged small; a progress file noting less than before; the resume note or the repository facts changed.

**How to verify:** `scripts/test.sh` green; `claude plugin details` before and after for the listing and invoke sizes; a diff of `pr-review` against 3.4.0.
