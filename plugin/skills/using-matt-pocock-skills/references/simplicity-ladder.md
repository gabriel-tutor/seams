# Simplicity ladder

Read this before writing code, in `implement`'s build or a `tdd` slice, and when a review reads a diff. The ladder shortens the solution, never the reading: understand the problem and trace the code it touches first, then climb.

## The ladder

Stop at the first rung that holds:

1. **Does it need to exist at all?** A need nobody stated is skipped, and the skip said in one line.
2. **Does the codebase already have it?** A helper, type or pattern a few files over is reused, not written again.
3. **Does the standard library do it?** Use it.
4. **Does a native platform feature cover it?** `<input type="date">` over a picker library, CSS over JavaScript, a database constraint over application code.
5. **Does an installed dependency solve it?** Use it. No new dependency for what a few lines can do.
6. **Can it be one line?** One line.
7. **Only then** the least code that works.

When two rungs work, take the higher. When two standard options are the same size, take the one that is correct on edge cases: less code, not a flimsier algorithm.

## Rules

- **A bug is fixed at its root.** Before editing a function, find its callers: one guard in the shared function beats a guard in each caller, and fixing only the path a report names leaves its siblings broken.
- **No unrequested abstraction:** no interface with one implementation, no factory for one product, no setting for a value that never changes, no scaffolding for later.
- **Deletion over addition, boring over clever, the fewest files.** The shortest working diff wins once the problem is understood; the smallest change in the wrong place is a second bug.
- **A deliberate shortcut is marked** where it is made, with a `ceiling:` comment naming its limit and its upgrade path: `# ceiling: one global lock; per-account locks if throughput matters`.
- **What was skipped is said** in the handover's What changed: skipped X, add it when Y.
- **Checks stay as the process sets them** (shared rules: Process by size and risk), never fewer because the code is short.

## Never cut

The ladder never simplifies away validation at a trust boundary, error handling that prevents data loss, security measures, accessibility basics, or anything the user asked for. A sensitive change keeps every review its row requires. When the user insists on the fuller version, build it.

## In a review

The correctness review also reads the diff up the ladder. Code the ticket didn't need, or a re-implementation of what the codebase, the standard library, a native feature or an installed dependency already does, is a gap against the ticket and is fixed: deleted, or replaced by what exists. The never-cut list holds for a review too.

Adapted from ponytail's `ponytail` skill (github.com/dietrichgebert/ponytail, `skills/ponytail/SKILL.md` at commit `c982cd411abb53323c4baa1baa3c2f020b8d0b08`), MIT License, Copyright (c) 2026 DietrichGebert; the full notice is in this plugin's `THIRD_PARTY_NOTICES.md`.
