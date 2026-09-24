# 13: Docs: resuming, surfaces, off switches, measuring, versions

**What to build:** From the README and the changelog, a user can find out:
- how resuming works;
- where Seams loads fully and where it doesn't;
- which settings silently switch it off;
- how to measure what it costs;
- which Claude Code versions it supports.

`foundations` offers `/fewer-permission-prompts`.

**Blocked by:** 02 (The gate sees every shell and stops tripping on quotes); 03 (Typed skills, the lapse hint, a calmer done-check); 07 (A pr-review batch resumes); 10 (Pre-loaded facts); 12 (Unblocked tickets built in parallel)

**Status:** ready-for-agent

- [ ] The README covers:
  - **Resuming:** progress files, the resume note, and the notice.
  - **A surfaces table:**
    - Seams loads fully in the CLI and in Desktop local sessions.
    - In VS Code it loads a subset of skills.
    - In cloud sessions it loads only when enabled on the claude.ai account.
    - It doesn't load in Desktop WSL.
    - In `-p`, questions come as text.
  - **Off switches:** `disableAllHooks`, `allowManagedHooksOnly`, `strictPluginOnlyCustomization` for skills, `--bare`, `--safe-mode`.
  - **Measuring:** `claude plugin details`, `/skill-doctor`, and OpenTelemetry with `OTEL_LOG_TOOL_DETAILS=1`.
  - **Supported versions:** 2.1.269 or later, tested on 2.1.281, with the optional fields named.
- [ ] `foundations` offers `/fewer-permission-prompts`, which the user runs, and stays within the size bound.
- [ ] The CHANGELOG has a 3.3.0 entry saying what changed and why. The evidence doc has a 3.3 section ready for the release's figures.
- [ ] Must not happen: the README makes a claim without evidence in this repository or the docs mirror, or a surface claim the docs don't support.

**How to verify:** Read the README and the CHANGELOG against the spec's decisions and the docs pages they cite. Then run `scripts/test.sh`, which includes the static test's README and attribution checks.
