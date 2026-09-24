# 03: Typed skills, the lapse hint, a calmer done-check

**What to build:**
- **Typed skills:** a skill the user types is recorded as a declaration from the `UserPromptExpansion` event, whichever form it was typed in: stacked, bare name or full name.
- **The lapse hint:** when a typed message starts a new request and the previous request had declarations, Claude is told, as facts, which declaration lapsed. It then re-declares before its next edit instead of hitting a refusal.
- **The done-check:** it asks for verification as hook feedback (`additionalContext`), not as a hook error.

This change is sensitive: `code-review` is required.

**Blocked by:** 01 (Release 3.2.1)

**Status:** ready-for-agent

- [ ] A typed process skill is recorded from `UserPromptExpansion`: e.g. `/matt-pocock-workflow:grill`, a bare `/pr-review 42`, `/tdd`, a stacked `/grill /tdd …`. When the event is absent, UserPromptSubmit's own parse still records it.
- [ ] Must not happen: a typed non-process skill or an MCP prompt is recorded as a declaration.
- [ ] When a typed message starts a new request after one with declarations, the prompt hook's context names the lapsed declarations. It says that re-invoking them continues that work, and that new work needs its route.
- [ ] Must not happen:
  - the hint restores a declaration by itself: the next change is still refused until a skill is invoked;
  - a hint is sent for a go-ahead message, a machine notice, or a request that had no declarations.
- [ ] The done-check still asks once per turn and still honours `stop_hook_active`. Its request reads as hook feedback, not a hook error.
- [ ] Unit and hook-suite tests pass under Python 3.9 and the current Python.
- [ ] A two-step headless run: in the second message of a resumed session, which continues the same work, Claude re-invokes the skill before editing and no call is refused.
- [ ] Reviewed with `code-review` (required for a sensitive change).

**How to verify:** `scripts/test.sh`, then a two-step headless run in a fixture copy with the plugin loaded:
1. `claude -p "<declare and start a small change>"`
2. `claude -p --resume <id> "<continue it>"`

The second run's transcript shows the skill invoked before the edit and no refusal. Record the run in the evidence doc.
