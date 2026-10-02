# Seams 4.0: fast and continuous, at the same quality

**Status:** ready-for-agent

Phase 1 of the revamp agreed in the grill of 2026-10-02 (`.scratch/seams-revamp/progress.md`, decisions 1 to 20). It continues the four-phase roadmap of 2026-09-25, whose phase 1 was 3.3's lean-and-durable. Phase 2 (the project's own stack, e2e drivers, official docs lookup) and phase 3 (Claude Code's bundled skills in the flow) are outlined in the progress file and grilled when each starts. The hard-to-reverse choice is ADR 0005.

## Problem Statement

The user likes what Seams does: every request routed to a senior engineer's process, every decision and step written down so the next session picks up where the work was, a review and verification before anything is called done. But using it is slow, and it does a lot that has nothing to do with the task in front of it.

- **Every typed answer costs a round trip.** A reply that is not a short go-ahead lapses the declaration, so the next change is refused until a skill is invoked again, and its body is read again. On a grill or a build that is one more Skill call after almost every answer. A turn that changed the project without the verification skill gets one more Stop round.
- **Every step asks before it starts.** Grill, spec, tickets, build, review and release each stop for a yes, even when the user already said where the work is going.
- **A typo pays a feature's price.** Scouts run "however small the codebase", every build gets two reviewers and a twelve-row done table, whatever the change.
- **The same rule is written many times.** The effort line is in 10 skills, the repository-facts paragraph in 3, the sensitive-areas list in 7, the progress-file rules in 6 or 7, and two pairs contradict each other. Each copy costs context when its skill loads, and drifts.
- **The repo's own tests take about ten minutes on the user's Mac.** Eight suites run one after another; on macOS every Python test and two hook suites run a second time under the system Python; about 750 tests pin the exact wording of skills and the README, so any rewording breaks them; real sleeps and timeouts add up; a custom eval harness needs Node and 1,136 lines of tests of its own.
- **The helpers run on the most expensive model.** Fact-finding scouts run on the session's model when a faster one does the job.

## Solution

Seams 4.0 keeps everything the user values and removes the waiting around it.

- **A continuous flow.** Once a design is confirmed, the flow runs on through spec, tickets, build, review and release. It stops for the user's decisions, for integrating a branch, for pushes, deploys and publishes, for anything destructive, and for paid runs.
- **A route lasts.** A declaration holds until another process skill is invoked or the session is cleared; a typed reply no longer lapses it. The gate still refuses work no skill has routed, and the done-check still asks for verification before a turn that changed the project ends.
- **Process in proportion.** Scouts, reviewers and question rounds scale with the change's size and risk. A one-line fix gets one check; a feature, or anything in the sensitive list, gets the full set: both reviews, the security review, verification. Each rule is written once, in one shared reference the skills point to.
- **Official docs for anything third-party.** Before writing or reviewing code that uses a library, framework, platform, CLI or API, the skills check its official docs for the version in use and cite them.
- **Lighter hooks.** The gate is split so each hook loads only what its event needs.
- **Faster helpers.** Scouts run on Sonnet 5.5; reviewers stay on the session's model.
- **The context management is untouched.** Progress files still note every decision and step, the session start still brings the resume note, and the flow skills still start with the repository facts.
- **A test suite that runs in under a minute.** Suites run in parallel, test behavior rather than wording, and never sleep. The Python 3.9 check becomes a CI job. The eval scenarios stay for Claude Code's own `claude plugin eval`; the custom harness goes.
- **Proven, not claimed.** Before 4.0.0 ships, the eval scenarios run on 3.4.0 and on the candidate, and no scenario may get worse; the cost of three scripted tasks is measured on both.

## User Stories

1. As a developer, I want the flow to run on from a confirmed design to a release, so that I am not asked to approve each phase I already agreed to.
2. As a developer, I want the flow to stop for my decisions, so that nothing I should choose is chosen for me.
3. As a developer, I want the flow to stop before it integrates a branch, so that I still pick merge, pull request, keep or discard.
4. As a developer, I want the flow to stop before any push, deploy or publish, so that nothing leaves my machine without my yes.
5. As a developer, I want the flow to stop before anything destructive, so that nothing is lost without my yes.
6. As a developer, I want the flow to stop before any run that costs money, so that I decide what I pay for.
7. As a developer, I want my typed answers to keep the current route, so that I am not made to invoke the same skill again after every reply.
8. As a developer, I want the gate to keep refusing work that no skill has routed, so that the workflow stays enforced.
9. As a developer, I want the done-check to keep asking for verification, so that nothing is called done without evidence.
10. As a developer, I want invoking a different process skill to replace the current route, so that a new kind of work gets its own process.
11. As a developer, I want `/clear` and a new session to reset the route, so that a fresh start is fresh.
12. As a developer, I want a one-line fix to get one check, so that a typo does not pay for a feature's process.
13. As a developer, I want a feature to keep its full process, so that quality does not drop where it matters.
14. As a developer, I want anything in the sensitive list to always get both reviews and the security review, so that risk is never judged small by accident.
15. As a developer, I want scouts started only when a question needs facts the conversation does not hold, so that small questions are answered without subagents.
16. As a developer, I want each rule written once, so that skills load less and cannot contradict each other.
17. As a developer, I want the contradictions between skills resolved, so that I always know which rule holds.
18. As a developer, I want code that uses a third-party library, framework, platform, CLI or API checked against its official docs for the version in use, so that the code matches what that version does.
19. As a developer, I want those docs cited, so that I can check the claim.
20. As a developer, I want repo-internal logic written without a docs lookup, so that no time goes on lookups that cannot help.
21. As a developer, I want progress files to keep noting every decision and step, so that the next session picks up the actual context.
22. As a developer, I want the resume note at every session start, `/clear` and compaction, so that unfinished work is never forgotten.
23. As a developer, I want the flow skills to keep starting with the repository facts, so that they act on the real state of git.
24. As a developer, I want each hook to load only what its event needs, so that every tool call waits less.
25. As a developer, I want a hook that crashes to never block my work, so that a Seams bug cannot stop me.
26. As a developer, I want scouts to run on a faster model, so that fact-finding takes less time and money.
27. As a developer, I want reviewers to stay on my session's model, so that reviews are as good as before.
28. As a developer, I want `pr-review` to keep every step, script and check it has in 3.4.0, so that the reviews I rely on do not change.
29. As a developer, I want `pr-review` to point to the same shared rules as the other skills, so that it does not carry its own copies.
30. As a maintainer, I want the test suite to run in under a minute on my Mac, so that I run it before every commit.
31. As a maintainer, I want the suites to run in parallel, so that the slowest one sets the time, not their sum.
32. As a maintainer, I want tests to check behavior rather than wording, so that rewording a skill does not break a test.
33. As a maintainer, I want the few contracts that matter (skill sizes, frontmatter, routing rows, injected commands) still pinned, so that what Claude Code and the routing rely on cannot drift.
34. As a maintainer, I want no test to sleep, so that time is never spent waiting on nothing.
35. As a maintainer, I want a test that fails when the suite runs over its time budget, so that slowness is caught when it creeps in.
36. As a maintainer, I want the macOS system Python checked once in CI, so that compatibility is covered without doubling every local run.
37. As a maintainer, I want duplicated tests removed, so that each behavior is tested once.
38. As a maintainer, I want the eval scenarios kept for `claude plugin eval`, so that routing quality is measured with Claude Code's own tool.
39. As a maintainer, I want the custom eval harness and its fixture builder removed, so that the suite needs no Node and has fewer lines to keep.
40. As a maintainer, I want stale code removed (the manual-only declaration path, stray bytecode), so that nothing dead is shipped.
41. As a maintainer, I want the eval scenarios run on 3.4.0 and on the candidate before release, with no scenario worse, so that "same quality" is evidence.
42. As a maintainer, I want the cost of three scripted tasks measured on both versions (tool calls, tokens, wall time), so that "faster" is evidence.
43. As a maintainer, I want every paid run asked first and the runs made one at a time, so that my bill and my Mac stay under my control.
44. As a maintainer, I want the revamp built in a worktree, never live in the plugin folder, so that my other sessions never run half-built code.
45. As a maintainer, I want 4.0.0 to read 3.4.0's per-session state or start it fresh, so that upgrading never refuses work.
46. As a maintainer, I want a rollback to be reinstalling 3.4.0, so that a bad release is one command away.
47. As a maintainer, I want the README, CHANGELOG and glossary to say what 4.0.0 changed, so that users know the flow no longer asks at each step.

## Implementation Decisions

**The gate and the hooks**

- The declaration's lifetime changes: it holds until another process skill is invoked or the session is cleared (`/clear`, a new session). A typed prompt no longer lapses it, and neither does a commit. The prompt hook keeps reading prompts only for what still needs them; the lapse hint goes.
- A subagent's own declaration is unchanged: it opens the gate for that subagent alone.
- The refusals are unchanged: no route at all is refused, read-only agents are held to reads, project writes through the shell are recognized as today.
- The done-check is unchanged in what it asks: once per turn, when the project changed and verification did not follow.
- The gate module is split so each hook event loads only the code it needs; the shared parts (the ledger, path classification) stay in one place. Target: about 20 ms a firing instead of 37, measured the same way.
- Every hook still fails open: a crash never blocks the user's work.
- The per-session ledger written by 3.4.0 is read by 4.0.0, or treated as empty when its shape is unknown; it is never a reason to refuse.
- The manual-only declaration path, which no current skill uses, is removed.

**The routing and the flow**

- The bootstrap's rule that each step asks before it starts is replaced by the continuous flow: once a design is confirmed, the flow skills chain by themselves and stop only at the real gates (the user's decisions, branch integration, pushes, deploys and publishes, destructive actions, paid runs).
- The flow skills' opening gate questions go where the chain no longer needs them (to-spec, to-tickets, implement); the questions before a publish, a push, a deploy, a destructive action and a paid run stay; finishing a branch still asks how to integrate it.
- The bootstrap gains the docs rule: anything third-party is checked against its official docs for the version in use, and cited. The bootstrap stays inside its size bound.

**The skills**

- One shared reference holds every rule that several skills repeat: the effort line's meaning, the repository facts, the progress-file rules, the sensitive-areas list, the stages, the proportional-process table, the evidence rule, the worktree rule, the docs rule. Each skill points to it at the step that needs it.
- The proportional-process table says, for each size and risk, which scouts, reviewers, question rounds and checks a change gets; anything in the sensitive list always gets the full set.
- The contradictions are resolved once, in the shared reference: evidence produced on the same commit is reused, not re-run; the worktree rule is one rule.
- Every skill keeps its steps and its handover; what changes is that extras scale with the change and repeated text is a pointer.
- `pr-review` changes only by pointing to the shared reference; its steps, scripts, references and checks are 3.4.0's.
- The progress-file format, the resume note and the repository facts are unchanged.

**The agents**

- `scout` runs on Sonnet 5.5; `reviewer` keeps the session's model.

**The test suite**

- One runner starts the suites in parallel and reports each one's result and time; the whole run has a time budget its own test enforces.
- The Python 3.9 compatibility check becomes a CI job; the local run uses one interpreter.
- Wording pins shrink to the contracts: skill and reference size bounds, frontmatter fields, the routing table's rows, the injected commands, the version's single source, the third-party notices. Everything else tests behavior.
- Tests that sleep use a fake clock or a condition to wait on.
- Duplicated tests are merged: the gate's rules are tested once in process, and each hook event once through its command line.
- The custom eval harness, its workspace builder, its Node fixture and their tests are removed; `plugin/evals` stays for `claude plugin eval`.

**Docs**

- README and CHANGELOG describe the continuous flow, the lasting route, the proportional process and the new suite; the glossary's Declaration and Gate already say so (the grill updated them); ADR 0005 records why.

## Testing Decisions

- A good test checks what a user or Claude Code observes (a refusal, an allowed write, an injected note, a script's output), never how the code is arranged. Rewording a skill must not break a test unless the wording is a contract.
- **Seams** (agreed in the grill, decision 18):
  - the gate module in process: the declaration's lifetime (holds through prompts and commits, replaced by another process skill, reset by `/clear` and a new session), the refusals, the done-check;
  - one command-line smoke per hook event, through the hooks as Claude Code runs them;
  - the contract pins listed above;
  - a test that fails when the suite runs over its budget.
- `pr-review`'s script tests stay as they are; they run in parallel with the rest.
- **Prior art:** the gate tables in the in-process gate tests; the hook suite fed JSON on stdin; the static plugin test's size and frontmatter checks; the eval scenarios run with `claude plugin eval`.
- **Proof before release** (decision 12): the eval scenarios on 3.4.0 and on the candidate, no scenario worse; the cost of three scripted tasks on both. Each paid run is asked first, and runs go one at a time.

## Out of Scope

- Phase 2: reading the project's stack, e2e drivers per stack (Playwright, Chrome DevTools, Claude in Chrome, Maestro, MobileBuildMCP, the Android CLI, computer use), Context7 or vendor docs servers. 4.0 states the docs rule; phase 2 gives it tools.
- Phase 3: Claude Code's bundled skills inside the flow (`/code-review`, `/security-review`, `/simplify`, `/run`, `/run-skill-generator`, offering `/verify`).
- Any change to `pr-review`'s behavior, scripts or checks, and the cancelled lighter-checks change.
- Rewriting hooks or tests in Go or Rust.
- Making the gate advisory, or removing the done-check.
- Changing Matt Pocock's own skills, which are installed per user.
- Branch integration without a question.

## Further Notes

The revamp is built in a worktree and copied into the plugin only when a ticket is finished and tested, because the user's other sessions load the plugin in place; nothing CPU-heavy runs on the user's Mac without asking first.

### Alternatives considered

- **A gate that only advises:** fastest, but it gives up the enforcement ADR 0001 exists for.
- **The per-request lapse kept:** it taxes every typed answer with a Skill call.
- **A route that ends at the next commit:** the grill and builds commit after every step, so it would end mid-task.
- **A route that expires after two hours idle:** adds a clock the user has to keep in mind, for little gain.
- **Every step on every change:** what 3.4.0 does; a typo pays a feature's price.
- **Rust or Go for the hooks and tests:** the time is in waiting on processes and sleeps, not in Python; a compiled hook would save about 30 ms a firing and add a build per platform.
- **Running the suites in parallel only:** keeps the ~750 wording pins that make every rewording expensive.
- **Keeping the custom eval harness:** `claude plugin eval` covers the scenarios with Claude Code's own tool.
- **Merging a finished branch by itself:** the user keeps that choice.
- **Scouts on Haiku 4.5:** cheapest, but more likely to miss a fact.
- The ADR: `docs/adr/0005-route-lasts-until-replaced-and-proportional-process.md`.

### Risks and failure modes

- **An unrelated request typed mid-task rides on the current route.** The bootstrap still tells Claude to route new work; the gate now guards against no route at all. Accepted in ADR 0005.
- **A change judged small that is not.** The proportional table errs toward the full set for anything in the sensitive list, which is checked first.
- **A flow that runs past something the user wanted to see.** The real gates are the ones the user named; everything else is visible in the progress file and the handover.
- **Fewer wording pins let a contract drift.** The contracts the routing and Claude Code rely on stay pinned.
- **A hook split that misses an event's dependency.** The command-line smoke per event catches a hook that fails to load; every hook still fails open.
- **A paid proof run that costs more than expected.** Each is asked first with its size.

### Rollout and migration

- What changes shape: the gate's per-session ledger (read compatibly or started fresh), the hooks' modules, the bootstrap's routing text, the skills' text, the test suite and CI (one new Python 3.9 job).
- Users update the plugin as usual; nothing they configure changes.
- Reversed by reinstalling 3.4.0.

### Observability

- A slow hook shows in `/doctor`, which flags slow hooks; the suite's own budget test fails when the suite slows.
- The progress file and the handover still show every decision and step, so a flow that ran on is readable after the fact.
- The proof runs record the eval scores and the measured cost in the evidence docs.

### Release

- Target: the marketplace repository `gabriel-tutor/seams`. CI on a throwaway staging pull request (macOS and Ubuntu, plus the new Python 3.9 job), then `main` fast-forwarded on the user's yes, as for 3.3 and 3.4. The local install loads the plugin from this repository.
- The last ticket takes the integrated candidate through `matt-pocock-workflow:release` with the proof of decision 12 in its readiness table.
