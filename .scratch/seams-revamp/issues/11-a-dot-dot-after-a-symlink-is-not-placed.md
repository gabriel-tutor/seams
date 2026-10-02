# 11: A `..` after a symlink is not placed

**What to build:** a path the gate places is resolved the way the kernel resolves it, so a symlink followed by `..` can no longer make a write look like scratch: a shell operand or an editor tool's path holding a `..` segment counts as not placed (a change, refused without a declaration, recorded with one), or is resolved physically before it is placed. The first also refuses a `..` through real directories that is allowed today (`echo x > /tmp/a/../b`); the second keeps it. A read-only agent's write through such a path is refused like any other.

**Blocked by:** 10 (The ledger out of an agent's reach).

**Status:** ready-for-agent

- [ ] With an empty ledger, a redirect or an editor tool's write to `<scratch>/S/../<anything>`, where `S` is a symlink out of the temp directory, is refused for want of a declaration; with a declaration it is allowed and recorded as a change.
- [ ] A `reviewer` or `scout` writing through such a path is refused, declared or not.
- [ ] The two-step form is caught too: `ln -s /tmp /tmp/C && printf … > /tmp/C/../<home>/.local/state/seams/<sid>.json` in one command.
- [ ] A path with no `..` segment is placed exactly as before.
- [ ] Must not happen: a hook crash (the hooks fail open); a refusal of a write without `..` that was allowed before; a slower hook beyond noise (PreToolUse medians measured before and after).

**How to verify:** in-process gate tests, red before the change: `decide_pre_tool_use` on a reviewer's `printf x > /tmp/S/../<ledger dir>/<sid>.json` with `/tmp/S` a symlink, on a Write to the same path, and on the two-step `ln -s … && printf …`; then `scripts/test.sh` green.

## Comments

Found by ticket 10's security review (5090129, then 7c40507) on 2026-10-03, rated medium; the user chose a new ticket that 4.0.0 waits for. `seams_shell._placed_path` (plugin/hooks/seams_shell.py:428) and `seams_gate._editor_path` (plugin/hooks/seams_gate.py:110) apply `os.path.normpath` before any `realpath`, so `S/..` is dropped lexically while the kernel follows `S` first; one undeclared Bash call from the main conversation or a builder (scouts and reviewers lack `ln`, but a symlink planted earlier serves them) can then write the ledger at `~/.local/state/seams` or the project. Case-insensitive paths stay lean-and-durable ticket 16's.
