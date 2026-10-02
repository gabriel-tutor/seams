# Seams owns adapted copies of the spec, tickets and implement skills

Matt Pocock marks `to-spec`, `to-tickets` and `implement` user-only, and Claude Code's docs say a blocked user-only call must not be reproduced another way. Seams 2.x read those files after a yes and followed them, which honored the consent but not the letter. We decided that Seams ships its own adaptations of the three (MIT, attributed in THIRD_PARTY_NOTICES.md with the upstream file hashes), model-invocable by design and still gated by a question before they start and before they publish. Nothing reads his user-only files at runtime, so the installer no longer touches settings.json, and the commit-before-review fix (his `code-review` diffs `<fixed-point>...HEAD`, so uncommitted work is invisible to it) lives in our own `implement`.

## Consequences

- His future edits to those three files do not flow in automatically; a test compares the recorded upstream hashes with the installed files and reports drift, and the port is a manual review.
- ADR 0006 drops the question before they start once the user has confirmed a design (the continuous flow); the question before they publish stays.
- Matt's model-invocable skills (`grilling`, `domain-modeling`, `tdd`, `diagnosing-bugs`, `code-review`, `codebase-design`, the `setup-*` skills) are still invoked by name; only the three orchestration flows were copied.
