# 02: The gate sees every shell and stops tripping on quotes

**What to build:** Commands that Claude runs through `Monitor` or `PowerShell` are gated like Bash commands. The classifier stops mistaking a quoted `>` inside a double-quoted command substitution for a redirect, and writes under the session's scratchpad count as scratch. Before a declaration:
- A `Monitor` command goes through the Bash classifier. A WebSocket watch changes nothing.
- A `PowerShell` command is a change unless it is `Get-Content`, `Get-ChildItem`, `Select-String`, or `git status`, `git diff` or `git log`.

The hooks run in exec form.

This change is sensitive. The grill has already covered the security and failure axes, and `code-review` is required.

**Blocked by:** 01 (Release 3.2.1)

**Status:** done

- [x] These are not changes:
  - the reproduced false positive, `x="$(awk '$1>0' f)"`;
  - a quoted `>` in an awk program inside `"$(…)"`, with or without an assignment around it;
  - an input redirect (`< file`).
- [x] Must not happen: a real output redirect in the same shapes slips through, e.g. `x="$(cmd > out)"` or `echo "$(cat a)" > b`.
- [x] Before a declaration, a `Monitor` command that writes to the project is refused. A read-only `Monitor` command and a WebSocket watch are not.
- [x] Before a declaration, a `PowerShell` command outside the read-only list is refused, e.g. `Set-Content`, `Remove-Item`, `git commit`. The listed read-only commands are not.
- [x] Scratch paths:
  - A write under the hook input's `scratchpad_dir` is scratch.
  - When the field is absent, today's temp-root rules apply unchanged.
  - Must not happen: a path under the session's working directory counts as scratch.
- [x] The PreToolUse entry also matches `PowerShell` and `Monitor`. Every hook entry uses exec form (`args`), and every hook still fails open.
- [x] Unit tables (false positives, bypasses, `Monitor`, `PowerShell`, scratchpad) and hook-suite cases pass under Python 3.9 and the current Python.
- [x] Stale `__pycache__` in the hooks directory is removed.
- [x] Reviewed with `code-review` (required for a sensitive change).

**How to verify:** `scripts/test.sh`. The hook suite feeds the PreToolUse hook synthetic `Monitor` and `PowerShell` events, with and without a declaration, and with and without `scratchpad_dir`.

## Comments

Built 2026-09-25 on local `main`, not pushed. The commits:
- `6faea1d`, the build. The live headless run used this candidate.
- `c227c61`, the review fixes.
- The commit carrying this record.

**What shipped.**
- **The classifier reads a command as the shell does.** A hand-written tokenizer replaces `shlex`, whose non-POSIX mode opens no quote inside a word; that was the reproduced false positive's cause.
  - Quotes may open inside a word, and `$'…'` is a quote.
  - A command substitution keeps its own quotes and comments.
  - Operators split one by one. A `#` opens a comment only at a word's start. A backslash-newline joins the lines.
  - What a command runs is found in the tokenizer's own words. An unquoted heredoc's text is searched only for what its substitutions run.
  - A quote that never closes falls back to the old split, which never misses an operator.
  - A word that joins quoted and bare parts expands part by part, so `"$EVID"/log.txt` under the temp directory is scratch.
  - A command nested past 50 levels is refused as unreadable, instead of crashing the hook open.
- **`Monitor`** watches go through the classifier, scratch rule included. A WebSocket watch runs nothing.
- **`PowerShell`** before a declaration is a change unless it is on the read-only list, on its own with plain arguments. `git diff` or `log` with `--output`, however it is quoted, counts. The refusal names the list. After a declaration, a git command run on its own keeps git's label, so a commit after the checks needs no new verification.
- **`scratchpad_dir`** is scratch beside the temp roots. A field that is not an absolute path changes nothing, and the working directory is never scratch.
- **Exec form:** every hook entry runs `python3` with the script's path in `args`.
- **Housekeeping:** the stale `__pycache__` directories in `plugin/` are removed, and `test_gate.py` no longer writes one.
- **Docs:** the README's gate paragraph (`Monitor`, `PowerShell`, a quoted `>`, the scratchpad), the Windows note in the README and `docs/compatibility.md`, and the scratch refusal's text.

**Evidence** (`docs/plugin-behavior-tests.md`, "3.3, ticket 02"):
- **The deterministic suites:** `scripts/test.sh` passes 9 of 9 with 0 skipped, on Python 3.14.6 and 3.9.6 (166 unit tests each). The unit and hook suites also pass on 3.12.13.
- **The review's fuzz, re-run on `c227c61`:** 2,142 combinations of comments, heredocs and quotes holding apostrophes, around 18 real writes.
  - No write that bash 5.3, zsh or bash 3.2 performs is missed.
  - 60 verdicts dropped, all of them syntax errors that none of the three shells runs.
  - 378 write shapes are newly caught.
  - None of 49 realistic read-only commands is flagged.
- **One live headless session** on `6faea1d` (Haiku, $0.057): all five hooks spawned in exec form, and the gate refused `echo hi > probe.txt` until a declaration.

**Review of `6faea1d`.** Matt Pocock's `code-review` (Standards and Spec), and a correctness review that compared the old and new classifiers under bash and zsh.
- **Acted on in `c227c61`:**
  - three shapes the old gate caught and the build missed (a comment's apostrophe, an unquoted heredoc's text, `$'…'`);
  - deep nesting that crashed the hook open, in quadratic time;
  - a quoted `--output` through PowerShell;
  - `"$EVID"/log.txt` refused;
  - a PowerShell `git commit` asking for verification again;
  - the operator table's drift;
  - the stale docs and the test's key order.
- **Not acted on:** judgement-call smells (the two path rules' duplication, the two describe switches, names), and the routing harness scoring only Bash as a shell, which is outside this ticket.

**Decisions made in the build, not settled by the ticket.**
- **Exec form runs `python3` with the script's path,** not the script itself. Windows needs a real executable to spawn.
- **The tokenizer was rewritten rather than patched.** `shlex` cannot open a quote inside a word. The rewrite also closed seven misses the old one had: `true;>f`, `echo hi|>f`, `(>f)`, `curl …/a#top > f`, `echo $# > f`, `echo "$(echo ')' ; rm -rf src)"`, and a line continuation inside `rm`.
- **After a declaration, every PowerShell command outside the list is recorded as a change,** so the done-check sees PowerShell writes; there is no PowerShell classifier to tell them apart.
- **Nesting past 50 levels is refused unread.**

**Open.**
- Not exercised live: a `Monitor` or `PowerShell` call, and a write under a real `scratchpad_dir`.
- `/security-review`: the spec requires it on sensitive changes from ticket 11 on, and it was not run here. The correctness review stood in for it.
- Gaps that were already there and remain:
  - a `<<` inside a quote inside `"$(…)"` still reads as a heredoc to the text pre-pass, which can hide the lines after it;
  - on case-insensitive APFS, a project under a scratch root can be spelled into scratch.
- The minimum Claude Code version for `args` (the May 2026 releases, inside 3.3's 2.1.269) belongs in the README, with ticket 13.
