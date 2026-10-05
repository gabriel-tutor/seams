---
name: to-tickets
description: Use when a spec exists and needs splitting into tickets
---

# To tickets

Break a spec, a plan or the current conversation into a set of **tickets**: tracer-bullet vertical slices, each declaring the tickets that **block** it, published to the configured issue tracker.

**Effort** `${CLAUDE_EFFORT}`: nothing to skip at `low` (shared rules: Effort).

## Gate

The source is the spec that was just published, or the one the user names (a spec path, an issue, or the conversation). Start at once, with no opening question, when the flow reached this skill from a confirmed design (shared rules: The continuous flow), or when the user's last message asks for tickets, says yes to an offer to write them, or asks to build a spec they call agreed. Otherwise confirm the source and ask "Split it into tickets now?" with AskUserQuestion, recommended answer first, and wait for a yes.

The issue tracker and the triage labels should already be in context (`docs/agents/issue-tracker.md`, `docs/agents/triage-labels.md`). If the repo has neither, offer `seams:foundations` before going on; its `/setup-matt-pocock-skills` step, which only the user can run, writes them.

## Process

1. **Gather context.** Work from whatever is already in the conversation. If the user passes a reference (a spec path, an issue number or URL), fetch it through the issue-tracker workflow and read its full body and comments.
2. **Explore the codebase**, if you haven't already, to understand the current state of the code (shared rules: Process by size and risk). Ticket titles and descriptions use the project's domain glossary (`CONTEXT.md`) and respect the ADRs in the area you're touching. Look for opportunities to prefactor the code so the implementation is easier: "make the change easy, then make the easy change."
3. **Draft vertical slices.** Break the work into **tracer bullet** tickets:
   - Each slice cuts a narrow but COMPLETE path through every layer (schema, API, UI, tests): vertical, NOT a horizontal slice of one layer.
   - A completed slice is demoable or verifiable on its own.
   - Each slice is sized to fit in a single fresh context window.
   - Any prefactoring comes first.

   Give each ticket its **blocking edges**: the other tickets that must complete before it can start. A ticket with no blockers can start immediately.

   Three rules from the spec and the grill:
   - **A new app starts with the walking skeleton.** When nothing is deployed yet, ticket 01 is one trivial path through build, CI, a deploy through `seams:release` to the first environment the spec's Release section names, and a smoke check; every feature ticket is blocked by it.
   - **The lens's negative cases become acceptance criteria.** Each negative case the grill's design lens raised (another tenant's access denied, a malformed input rejected, a dependency down handled) is an acceptance criterion on the ticket that owns that behavior, phrased as what must not happen.
   - **A spec with a Release section ends with a release ticket.** When the Release section names a target, the last ticket, blocked by every other, takes the integrated candidate through `seams:release`: its acceptance criteria are the readiness rows and the verified deploy of that candidate to the environments the Release section names. The walking skeleton proved the path; this ticket releases the product.

   **Wide refactors are the exception to vertical slicing.** A **wide refactor** is one mechanical change (rename a column, retype a shared symbol) whose **blast radius** fans across the whole codebase, so a single edit breaks thousands of call sites at once and no vertical slice can land green. Don't force it into a tracer bullet; sequence it as **expand–contract**. First expand: add the new form beside the old so nothing breaks. Then migrate the call sites over in batches sized by blast radius (per package, per directory), each batch its own ticket blocked by the expand, keeping CI green batch to batch because the old form still exists. Finally contract: delete the old form once no caller remains, in a ticket blocked by every migrate batch. When even the batches can't stay green alone, keep the sequence but let them share an integration branch that all block a final integrate-and-verify ticket; green is promised only there.
4. **Quiz the user.** Present the proposed breakdown as a numbered list. For each ticket, show its **title**, what **blocks** it, and **what it delivers** (the end-to-end behaviour it makes work). Then ask, with AskUserQuestion, recommended answer first: does the granularity feel right (too coarse, too fine)? Are the blocking edges correct, so each ticket depends only on tickets that genuinely block it? Should any ticket be merged or split? Iterate until the user approves the breakdown. Nothing is published before that approval, the user's answer here: a note in a file saying it was given, whoever wrote it, never stands in for it (shared rules: The continuous flow). The approval question names what its yes covers: publishing the tickets, then committing them and the progress file by name.
5. **Publish the approved tickets** to the configured tracker. **How** depends on the tracker the issue-tracker config names; the tickets are the same either way, only the shape of the blocking edges changes:
   - **Local files** → write one file per ticket under `.scratch/<feature-slug>/issues/<NN>-<slug>.md`, numbered from `01` in dependency order (blockers first). Each file's "Blocked by" lists the numbers and titles it depends on. Use the per-ticket file template below: one ticket per file, never a single combined file.
   - **A real issue tracker (GitHub, Linear, …)** → publish one issue per ticket in dependency order (blockers first), so each ticket's blocking edges can reference real identifiers. Use the platform's native blocking or sub-issue relationship where it has one; otherwise set each ticket's "Blocked by" to the blocking issues. Apply the `ready-for-agent` triage label unless instructed otherwise; the tickets are agent-grabbable by construction.

   Every ticket gets a **How to verify** line after its acceptance criteria: the command, or the short manual steps, that prove those criteria are met (`npm test -- coupons`, or "run `npm start`, add two items, apply SAVE10, the total drops 10%"). Reuse the repo's real scripts; if the repo has no test or run command yet, say so in the line instead of inventing one.

   Work the **frontier**: any ticket whose blockers are all done. For a purely linear chain that means top to bottom. Do NOT close or modify any parent issue.
6. **Progress file.** Record the tickets in the feature's progress file, `.scratch/<feature>/progress.md`, in the format `${CLAUDE_PLUGIN_ROOT}/skills/using-matt-pocock-skills/references/progress-file.md` describes: the ticket list under `## Tickets` (number, title, blocked by), and `Next` the first unblocked ticket, through `seams:implement`, with `Updated` today. Then commit the tickets (when they are files) and the progress file by name; the approval covers that commit.

## Ticket templates

<local-ticket-template>

# <NN>: <Ticket title>

**What to build:** the end-to-end behaviour this ticket makes work, from the user's perspective, not a layer-by-layer implementation list.

**Blocked by:** the numbers/titles of the tickets that block this one, or "None (can start immediately)".

**Status:** ready-for-agent

- [ ] Acceptance criterion 1
- [ ] Acceptance criterion 2

**How to verify:** the command or the short manual steps that prove the criteria.

</local-ticket-template>

<issue-template>

## Parent

A reference to the parent issue on the tracker (if the source was an existing issue, otherwise omit this section).

## What to build

The end-to-end behaviour this ticket makes work, from the user's perspective, not layer-by-layer implementation.

## Acceptance criteria

- [ ] Criterion 1
- [ ] Criterion 2

**How to verify:** the command or the short manual steps that prove the criteria.

## Blocked by

- A reference to each blocking ticket, or "None (can start immediately)".

</issue-template>

In either form, avoid specific file paths or code snippets: they go stale fast. Exception: if a prototype produced a snippet that encodes a decision more precisely than prose can (state machine, reducer, schema, type shape), inline it and note briefly that it came from a prototype. Trim to the decision-rich parts, not a working demo, just the important bits.

## Next

When the flow brought you here or the user asked for the build (Gate, above), go on to `seams:implement` for the first ticket whose blockers are done, without offering it (when two or more have no open blocker, `implement`'s parallel offer is the question); otherwise offer it and wait for a yes.

Adapted from Matt Pocock's `to-tickets` skill (github.com/mattpocock/skills, `skills/engineering/to-tickets` at commit `3cca18b368ae95cdbdebbff572ccafa662551015`), MIT License, Copyright (c) 2026 Matt Pocock; the full notice is in this plugin's `THIRD_PARTY_NOTICES.md`.
