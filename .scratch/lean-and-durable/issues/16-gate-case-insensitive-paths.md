# 16: The gate's path checks on a case-insensitive filesystem

**What to build:** The gate compares paths as strings (`_under` in `plugin/hooks/seams_gate.py`), after `os.path.realpath`, which resolves links but not case. On a case-insensitive volume, macOS's default, one directory has many spellings, so a path spelled in another case escapes a check it should meet. The three checks that use `_under` are the session's working directory (the project), the Claude config directory (never scratch, decision 47) and the temp roots. Make each compare what lies on disk, for instance by `os.path.samestat` over the path's nearest existing ancestors, so that every spelling of a directory counts as that directory.

**Blocked by:** 14 (Release 3.3.0)

**Status:** needs-triage

- [ ] A read-only agent's write to `<config dir>/…` spelled in another case (`Config` for `config`) is refused when the config directory lies inside a temp root, as the exact spelling is.
- [ ] A write under the session's working directory, spelled in another case, is the project and needs a declaration when that directory lies inside a temp root, as the exact spelling does.
- [ ] Nothing changes on a case-sensitive filesystem or for exact spellings; every existing gate test still passes on macOS and Linux.
- [ ] Must not happen: a check that raises (the hooks fail open, so a crash would switch the gate off), or a stat walk that makes a hook noticeably slower.

**How to verify:** new unit and hook cases that spell a directory in another case on this Mac's case-insensitive volume (red before the change), and the suites on macOS and in the Linux container, where the new cases must not fail for want of case-insensitivity.

## Comments

Found by the security review of `ac16b39`, the gate fix of the 3.3.0 release, on 2026-09-27, and verified then: with `CLAUDE_CONFIG_DIR=/private/tmp/…/config`, a `scout` `Write` to `/private/tmp/…/Config/settings.json` was allowed, while the exact spelling was refused. With the config directory where it normally lies (`~/.claude`, outside every temp root), `~/.CLAUDE/settings.json` was refused, since outside the temp roots nothing is scratch.

So the bypass needs all three: a config directory or a project inside a temp root (a CI job's, an eval run's, a scratch clone), a path deliberately spelled in another case, and a case-insensitive volume. The string comparison predates 3.3; the config-directory check that exposed it is new in 3.3.0. The user chose to ship 3.3.0 first and fix the class here. Until then it sits within the README's "What it won't do": the gate is a workflow guard, not a sandbox.
