# 11: The quality bar in the definition of done; reviews scaled to risk

**What to build:**
- **The definition of done:** `implement`'s definition of done proves five things, or says why each doesn't apply: failure paths, security, performance, observability and rollback.
- **Reviews that scale with risk:**
  - Features and builds get Matt Pocock's `code-review` plus the bundled correctness review, at the session's effort.
  - Sensitive changes also get `/security-review`.
  - `/simplify` is offered on large diffs.
  - `/verify` is offered for user-facing changes.
  - The `reviewer` agent stands in when a built-in can't run.

**Blocked by:** 09 (Read-only agents and explicit delegation)

**Status:** ready-for-agent

- [ ] The definition of done has the five new rows. Each is proven by a command's output or a check, or marked "n/a" with a one-line reason. The table stays a table, and `implement` stays within the size bound.
- [ ] First, the build confirms whether Claude can invoke `/review` through the Skill tool. Matt Pocock's personal `code-review` replaces the bundled `/code-review` by name, so the bundled review may only be reachable as `/review`.
  - If Claude can, features and builds run `/review <effort> <fixed-point>..HEAD` at the session's effort.
  - If not, the `reviewer` agent does the correctness review.

  The finding is recorded in the ticket's comments.
- [ ] Sensitive changes run `/security-review`. Without an `origin` remote, the `reviewer` agent reviews for security findings only.
- [ ] `/simplify` is offered only when the diff exceeds 400 changed lines or 15 files. The handover's "Try it" offers `/verify` for user-facing changes when the repository has a runnable app.
- [ ] Must not happen:
  - `ultra` is used without the user asking;
  - a bounded change or a bug runs the reviews instead of offering them;
  - a finding is acted on without `receiving-code-review`'s check;
  - anything outside correctness or the stated requirements is changed because a reviewer suggested it.
- [ ] New eval cases:
  - a feature build shows both reviews invoked;
  - a sensitive fixture shows `/security-review`, or the fallback.

**How to verify:**
- `scripts/test.sh`.
- The eval cases through `claude plugin eval`. The run is paid, so ask first.
- One headless `implement` run on a fixture ticket, showing the definition-of-done table with the new rows.
