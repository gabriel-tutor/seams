---
name: to-spec
description: Use when a grilled design is agreed and the build will span more than one session
---

# To spec

Turn the current conversation into a spec and publish it to the project's issue tracker. No interview: the grill already settled the design, so this is synthesis of what is already known. Do not interview the user; the only questions here are the seams when none were agreed and the publish confirmation, and the gate's question only when nothing confirmed the design.

**Effort** `${CLAUDE_EFFORT}`: every step, gate and check runs at every level; nothing here is optional.

## Gate

Start at once, with no opening question, when the flow reached this skill from a confirmed design (the bootstrap's flow rule: the grill ended with the user's confirmation, here or in the progress file, and named the spec next), or when the user's last message asks for a spec or says yes to an offer to write one. Otherwise, before reading anything, ask "Write the spec now?" with AskUserQuestion, recommended answer first, and wait for a yes; a general go-ahead such as "let's get going" or "next" is not a request for a spec.

The issue tracker and the triage labels should already be in context (`docs/agents/issue-tracker.md`, `docs/agents/triage-labels.md`). If the repo has neither, offer `matt-pocock-workflow:foundations` before going on; its `/setup-matt-pocock-skills` step, which only the user can run, writes them.

## Process

1. **Explore the repo** to understand the current state of the codebase, if you haven't already. Beyond a few files, send `matt-pocock-workflow:scout` agents, one per area or question, all started in one message, and keep their conclusions rather than the files. Use the project's domain glossary (`CONTEXT.md`) throughout the spec, and respect any ADRs in the area you're touching.
2. **Seams.** Sketch the seams at which the feature will be tested. Prefer existing seams to new ones, and use the highest seam possible; if new seams are needed, propose them at the highest point you can. The fewer seams across the codebase, the better: the ideal number is one. When the grill already agreed the seams, write those into the spec instead of asking again. Only when no seams were agreed, check with the user that yours match their expectations, with AskUserQuestion.
3. **Write the spec** from the template below. Under **Further Notes**, add four short subsections, each from what the grill settled (write "none" where nothing applies, and never invent), and a fifth when the work has a deployment target:
   - **Alternatives considered:** the designs rejected and the one-line reason for each. A decision that is hard to reverse also gets an ADR through `domain-modeling`; the spec links it rather than repeating it.
   - **Risks and failure modes:** what can go wrong in use, and what the design does about each.
   - **Rollout and migration:** what changes shape (data, config, a public interface), how it's rolled out (expand–contract, a flag, a cutover), and how it's reversed.
   - **Observability:** how a person will know it's broken in use, and what gets logged at the boundaries.
   - **Release** (only when the work has a deployment target: a host, a store, a registry, a marketplace): the target, the environments it passes through, and what the first deploy is; for a new app, the walking skeleton's. The last ticket from `matt-pocock-workflow:to-tickets` takes the integrated candidate through `matt-pocock-workflow:release` on this basis.
4. **Publish.** Show the user the spec's title and where it will go (the path or tracker location the issue-tracker config names), and name the commit that follows: the spec when it is a file, the progress file, and the grill's `CONTEXT.md` and ADR changes. Wait for a yes. Then publish it there and apply the `ready-for-agent` triage label; no further triage is needed.
5. **Progress file.** Update the feature's progress file, `.scratch/<feature>/progress.md`, in the format `${CLAUDE_PLUGIN_ROOT}/skills/using-matt-pocock-skills/references/progress-file.md` describes (read it before the first write), creating it if the grill didn't: `Stage: designed`, the spec's path or URL under `## Spec`, `Next` the split into tickets through `matt-pocock-workflow:to-tickets`, `Updated` today. Decisions and pointers only: never a secret, a credential, a token or personal data. Then commit the files the question named, by name, with a message that names the spec.

## Spec template

<spec-template>

## Problem Statement

The problem that the user is facing, from the user's perspective.

## Solution

The solution to the problem, from the user's perspective.

## User Stories

A LONG, numbered list of user stories. Each user story should be in the format of:

1. As an <actor>, I want a <feature>, so that <benefit>

<user-story-example>
1. As a mobile bank customer, I want to see balance on my accounts, so that I can make better informed decisions about my spending
</user-story-example>

This list of user stories should be extremely extensive and cover all aspects of the feature.

## Implementation Decisions

A list of implementation decisions that were made. This can include:

- The modules that will be built/modified
- The interfaces of those modules that will be modified
- Technical clarifications from the developer
- Architectural decisions
- Schema changes
- API contracts
- Specific interactions

Do NOT include specific file paths or code snippets. They may end up being outdated very quickly.

Exception: if a prototype produced a snippet that encodes a decision more precisely than prose can (state machine, reducer, schema, type shape), inline it within the relevant decision and note briefly that it came from a prototype. Trim to the decision-rich parts, not a working demo, just the important bits.

## Testing Decisions

A list of testing decisions that were made. Include:

- A description of what makes a good test (only test external behavior, not implementation details)
- The seams the tests go at (from the grill, or agreed in step 2), and which modules will be tested
- Prior art for the tests (i.e. similar types of tests in the codebase)

## Out of Scope

A description of the things that are out of scope for this spec.

## Further Notes

Any further notes about the feature, then the subsections from step 3: Alternatives considered, Risks and failure modes, Rollout and migration, Observability, and Release when the work has a deployment target.

</spec-template>

## Next

Go on to `matt-pocock-workflow:to-tickets` without offering it: the flow continues (the bootstrap's flow rule).

Adapted from Matt Pocock's `to-spec` skill (github.com/mattpocock/skills, `skills/engineering/to-spec` at commit `3cca18b368ae95cdbdebbff572ccafa662551015`), MIT License, Copyright (c) 2026 Matt Pocock; the full notice is in this plugin's `THIRD_PARTY_NOTICES.md`.
