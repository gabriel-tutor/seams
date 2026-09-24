# 02: The gate sees every shell and stops tripping on quotes

**What to build:** Commands that Claude runs through `Monitor` or `PowerShell` are gated like Bash commands. The classifier stops mistaking a quoted `>` inside a double-quoted command substitution for a redirect, and writes under the session's scratchpad count as scratch. Before a declaration:
- A `Monitor` command goes through the Bash classifier. A WebSocket watch changes nothing.
- A `PowerShell` command is a change unless it is `Get-Content`, `Get-ChildItem`, `Select-String`, or `git status`, `git diff` or `git log`.

The hooks run in exec form.

This change is sensitive. The grill has already covered the security and failure axes, and `code-review` is required.

**Blocked by:** 01 (Release 3.2.1)

**Status:** ready-for-agent

- [ ] These are not changes:
  - the reproduced false positive, `x="$(awk '$1>0' f)"`;
  - a quoted `>` in an awk program inside `"$(…)"`, with or without an assignment around it;
  - an input redirect (`< file`).
- [ ] Must not happen: a real output redirect in the same shapes slips through, e.g. `x="$(cmd > out)"` or `echo "$(cat a)" > b`.
- [ ] Before a declaration, a `Monitor` command that writes to the project is refused. A read-only `Monitor` command and a WebSocket watch are not.
- [ ] Before a declaration, a `PowerShell` command outside the read-only list is refused, e.g. `Set-Content`, `Remove-Item`, `git commit`. The listed read-only commands are not.
- [ ] Scratch paths:
  - A write under the hook input's `scratchpad_dir` is scratch.
  - When the field is absent, today's temp-root rules apply unchanged.
  - Must not happen: a path under the session's working directory counts as scratch.
- [ ] The PreToolUse entry also matches `PowerShell` and `Monitor`. Every hook entry uses exec form (`args`), and every hook still fails open.
- [ ] Unit tables (false positives, bypasses, `Monitor`, `PowerShell`, scratchpad) and hook-suite cases pass under Python 3.9 and the current Python.
- [ ] Stale `__pycache__` in the hooks directory is removed.
- [ ] Reviewed with `code-review` (required for a sensitive change).

**How to verify:** `scripts/test.sh`. The hook suite feeds the PreToolUse hook synthetic `Monitor` and `PowerShell` events, with and without a declaration, and with and without `scratchpad_dir`.
