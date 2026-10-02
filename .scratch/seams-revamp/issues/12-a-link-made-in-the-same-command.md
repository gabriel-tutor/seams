# 12: A link made in the same command is not placed through

**What to build:** a shell command that makes a link and then writes through it no longer passes as scratch work. The cheap parts: `link` joins the commands that change files, and the inline-program check catches `os.symlink` and `os.link`. Open, decided when the ticket starts: what a command that can make a link counts as (an archive extracted with `tar -x` or `unzip -d`, `git worktree add` or a checkout of a commit that holds a link), and whether a temp root stays scratch where HOME lies under it.

**Blocked by:** 09 (Release 4.0.0).

**Status:** needs-triage

- [ ] With an empty ledger, `link <ledger>/<sid>.json <tmp>/h && printf … > <tmp>/h` is refused for want of a declaration.
- [ ] With an empty ledger, `python3 -c 'import os; os.symlink(…)'` followed by a write through that link, in one command, is refused for want of a declaration.
- [ ] Each command the start of the ticket decides can make a link (archive extraction, `git worktree add`) is handled as decided, with a test.
- [ ] A `reviewer` or `scout` making such a write is refused, declared or not.
- [ ] Must not happen: a hook crash (the hooks fail open); a refusal of a write that makes no link and was allowed before; a slower hook beyond noise (PreToolUse medians measured before and after).

**How to verify:** in-process gate tests through `decide_pre_tool_use`, red before the change, then `scripts/test.sh` green.

## Comments

Found by ticket 11's security review (80461e3, then ed0faab) on 2026-10-03, each checked in process with an empty ledger and each allowed on the base and in 3.4.0 too. High: a link made in the same command, with no `..` (`tar -xf … -C <tmp>/x` or `unzip -d` of an archive holding a symlink, `git worktree add --detach <tmp>/wt <hostile head>` where that commit holds one, or `python3 -c 'os.symlink(…)'`, which the inline-program check has no pattern for), followed by `printf > <tmp>/x/L/<sid>.json`. Medium: `link <ledger>/<sid>.json <tmp>/h && printf … > <tmp>/h`; `link` is not on the list of commands that change files, and `realpath` can't see a hard link. Low: with HOME under a temp directory (CI, eval runs), `ln -s /tmp /tmp/C && printf … > /tmp/C/<home-rel>/…`, since a temp directory's top level stays scratch. The user chose a ticket after 4.0.0, which makes none of them worse.
