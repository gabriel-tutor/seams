# 03: Typed skills, the lapse hint, a calmer done-check

**What to build:**
- **Typed skills:** a skill the user types is recorded as a declaration from the `UserPromptExpansion` event, whichever form it was typed in: stacked, bare name or full name.
- **The lapse hint:** when a typed message starts a new request and the previous request had declarations, Claude is told, as facts, which declaration lapsed. It then re-declares before its next edit instead of hitting a refusal.
- **The done-check:** it asks for verification as hook feedback (`additionalContext`), not as a hook error.

This change is sensitive: `code-review` is required.

**Blocked by:** 01 (Release 3.2.1)

**Status:** done

- [x] A typed process skill is recorded from `UserPromptExpansion`: e.g. `/matt-pocock-workflow:grill`, a bare `/pr-review 42`, `/tdd`, a stacked `/grill /tdd …`. When the event is absent, UserPromptSubmit's own parse still records it.
- [x] Must not happen: a typed non-process skill or an MCP prompt is recorded as a declaration.
- [x] When a typed message starts a new request after one with declarations, the prompt hook's context names the lapsed declarations. It says that re-invoking them continues that work, and that new work needs its route.
- [x] Must not happen:
  - the hint restores a declaration by itself: the next change is still refused until a skill is invoked;
  - a hint is sent for a go-ahead message, a machine notice, or a request that had no declarations.
- [x] The done-check still asks once per turn and still honours `stop_hook_active`. Its request reads as hook feedback, not a hook error.
- [x] Unit and hook-suite tests pass under Python 3.9 and the current Python.
- [x] A two-step headless run: in the second message of a resumed session, which continues the same work, Claude re-invokes the skill before editing and no call is refused.
- [x] Reviewed with `code-review` (required for a sensitive change).

**How to verify:** `scripts/test.sh`, then a two-step headless run in a fixture copy with the plugin loaded:
1. `claude -p "<declare and start a small change>"`
2. `claude -p --resume <id> "<continue it>"`

The second run's transcript shows the skill invoked before the edit and no refusal. Record the run in the evidence doc.

## Comments

Built 2026-09-25 on local `main`, not pushed. The commits:
- `f32ec75`, the build. The first live runs used this candidate.
- `0024a6c`, the review fixes. The two-step run was repeated on it.
- `c57768e`, the first record. Its definition of done found the unit suite's intermittent failure.
- `f3a83bb`, that failure's fix: `post_reviews.py` named the minute after GitHub's reset when the reset fell in a minute's last second.
- The commit carrying this record.

**What shipped.**
- **Typed skills declare from their expansion.** A `UserPromptExpansion` hook (`plugin/hooks/user-prompt-expansion`) records what each typed command expanded to, under the prompt's `prompt_id`, and the prompt hook adopts it when that prompt starts its request.
  - A bare `/grill` or `/pr-review 42` counts under the name it resolved to, and each skill of a stacked command counts.
  - An MCP prompt, a non-process skill and the routing policy skill never declare.
  - An expansion declares only its own prompt's request. One that arrives after its prompt hook, the order the hooks reference lists, declares that request directly.
  - The prompt's own parse of its leading command decides only when no expansion arrived.
- **The lapse hint.** A typed message that starts a new request after a declared one gets `additionalContext` naming the declarations that lapsed: invoking one again continues that work, and new work needs its own route.
  - It names at most five, plain skill names only. A skill only the user can type (`disable-model-invocation: true`) is named so: the user types it again, or the work takes a route Claude can invoke.
  - It restores nothing. No hint goes out for a go-ahead, a machine notice, a request that had no declarations, or a message that types its own route.
- **The done-check** asks through `hookSpecificOutput.additionalContext`: the same loop protections as a block, without the hook-error label.
- **Robustness:** a damaged ledger entry or list reads as empty and is never raised on, so the prompt hook always starts the new request.
- **Docs:** the README's declaration rule, its done-check line, the ledger's contents, and the test and hook lists. `CONTEXT.md` gains *Lapse hint* and the ledger's pending skills. The spec records the build's decisions.

**Evidence** (`docs/plugin-behavior-tests.md`, "3.3, ticket 03"):
- **The deterministic suites:** `scripts/test.sh` passes 9 of 9 with 0 skipped, on Python 3.14.6 and 3.9.6 (181 unit tests each). The unit and hook suites also pass on 3.12.13.
- **The capture:** what 2.1.282 sends for each typed form, at no cost. Expansions run before the prompt hook and share its `prompt_id`; a stacked command expands one skill per event in an interactive session and only the first in `-p`.
- **Live:** the two-step run passed on `f32ec75` and again on `0024a6c`. In each run, step 1's typed bare `/trivial` let the first edit through with no refusal, and step 2's resumed message got the hint and re-invoked `matt-pocock-workflow:trivial` before editing, with no refusal. A Haiku session showed the done-check's feedback keep the turn going with no `stop-hook-error`.
- **The fuzz, re-run on `0024a6c`:** 1,500 sequences without expansions differ from `b40f571` only by the hint. 2,000 with expansions crash nothing. 4,000 match a restatement of the rules at every step, a check that finds 279 mismatches in 1,000 on `f32ec75`.

**Review of `f32ec75`.** Matt Pocock's `code-review` (Standards and Spec), and a correctness and security review that drove the hooks with crafted events.
- **Acted on in `0024a6c`:**
  - the hint sent Claude to a Skill call Claude Code refuses, for a skill only the user can type;
  - the prompt's parse overrode an expansion that named what really ran;
  - an expansion after its prompt hook declared nothing;
  - a damaged ledger list kept the old request;
  - a trailing newline passed the name filter;
  - the stale docs, the done-check's docstring and two test messages;
  - the pending expansion's key, now `prompt_id`, since the ledger never holds prompt text.
- **Not acted on:** judgement-call smells (the hook list written twice in the hook suite, the output envelope built in three hooks, names).

**Decisions made in the build, not settled by the ticket.**
- **Expansions wait for their prompt,** keyed by `prompt_id`, because Claude Code runs them before the prompt hook that starts the request. An expansion after its prompt hook declares that request directly, since the reference lists that order.
- **The prompt's parse decides only when no expansion arrived.**
- **No hint for a message that types its own route** (decision 22): its request is already declared, and the hint would say the next change is refused. The user left it to Claude on 2026-09-25, and it stands.
- **Skills only the user can type** are read from their SKILL.md frontmatter: the plugin's own file, or the copy in the config directory or the project's `.claude/skills`.
- **The hint names at most five, plain names only.**
- **The unit suite's intermittent failure was fixed here,** in `f3a83bb`, though it lies in `pr-review`: the definition of done needs the full suite green, and its run on `c57768e` caught the failure by name for the first time since ticket 04 saw it. The user left this call to Claude too, and it stands.

**Open.**
- Not exercised live: a stacked command through Seams' hooks in an interactive session, a skill only the user can type lapsing, and an expansion after its prompt hook.
- `/security-review`: the spec requires it on sensitive changes from ticket 11 on, and it was not run here. The correctness and security review stood in for it.
- Gaps that were already there and remain:
  - the done-check puts a changed file's path into Claude's context as it stands;
  - a `Write` to the ledger under the temp directory needs no declaration, since that directory is scratch;
  - the done-check counts a background reviewer's scratch writes to paths it cannot place, so each turn end during a review is asked once (now as feedback, not an error).
