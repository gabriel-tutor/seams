---
name: trivial
description: Use before a change with no effect on behavior, data shape or security (copy, a typo, a comment, a rename that changes nothing observable)
---

# Trivial

A trivial change is declared, not assumed. Invoking this skill opens the gate for the current request and commits you to the test below.

**Effort** `${CLAUDE_EFFORT}`: every step, gate and check runs at every level; nothing here is optional.

## The test

It stays trivial only while all four hold:

1. **No behavior changes.** No test could tell the before from the after: copy, a comment, whitespace, a typo in a string nobody parses, a rename with no observable effect.
2. **No shape changes.** No data, config, schema or public interface changes shape.
3. **Nothing sensitive.** It does not touch auth, permissions, secrets, billing, migrations, infrastructure, CI or deploy configuration, a public API, or anything destructive. A one-line change there is not trivial.
4. **Reversible in one commit**, with nothing to migrate back.

If any of the four fails, stop and route up: `matt-pocock-workflow:grill` for a change to behavior or shape, `diagnosing-bugs` for something broken. Complexity found mid-edit moves you up a row, never down.

## Then

1. Make the edit.
2. Run the narrowest check that proves it: the typecheck, the test that covers the file, a link check, a render, a build of the one page.
3. Before saying it's done, run `matt-pocock-workflow:verification-before-completion` and show the check's real output. A trivial change still ends with evidence.
