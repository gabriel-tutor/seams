# Seams

The vocabulary of the Seams plugin: a Claude Code workflow in which Matt Pocock's engineering skills lead every session, from a request to production. This file names the concepts; the skills say what to do with them.

## Language

**Route**:
The process skill that work is sent to, chosen from the bootstrap's table by its size and risk. It lasts until another process skill replaces it or the session is cleared; from a confirmed design, the continuous flow moves it on from step to step.
_Avoid_: classification, triage (that word belongs to `/triage`)

**Continuous flow**:
What follows the user's confirmation of a design: spec, tickets, build, review and release, each step starting the next without asking. It stops only at the user's decisions and the gates (integrating a branch, a push, a deploy, a publish, anything destructive, a paid run), and each step still writes the progress file.
_Avoid_: autopilot, auto mode (a Claude Code permission mode)

**Bootstrap**:
The routing policy injected into every session at start, resume, clear, compaction and fork.
_Avoid_: system prompt, preamble

**Declaration**:
A Skill invocation of a process skill, by Claude or typed by the user, that opens the gate until another process skill replaces it or the session is cleared: a typed reply does not end it. A subagent's own declaration opens it for that subagent alone.
_Avoid_: unlock, override

**Gate**:
The hook that refuses any change to the project until a declaration has routed the work, and holds a read-only agent to reads whatever is declared. In a flow skill, also the question that must get a yes at one of the continuous flow's stops: between those, the flow runs on.
_Avoid_: guard, blocker, permission

**Ledger**:
The per-session record of declarations and changes that the gate and the done-check read, and of the skills a typed prompt expanded to, until that prompt starts its request.
_Avoid_: state file, cache, log

**Read-only agent**:
One of the two agents Seams ships for delegated reading: `scout` finds facts in the code and docs, on Sonnet, and `reviewer` reviews a named diff, on the session's model. Each returns its conclusions with their citations and what it couldn't confirm. Neither writes: the gate holds both to a short list of reads, whatever the request has declared, so a check or a probe a finding needs is run by the main conversation.
_Avoid_: helper, worker (a subagent is any agent Claude starts)

**Trivial change**:
A change with no effect on behavior, data shape or security-relevant configuration, reversible in one commit.
_Avoid_: quick fix, small change (a small change can still change behavior)

**Sensitive change**:
A change, of any size, to auth, permissions, secrets, billing, data migrations, infrastructure, CI or deploy configuration, a public API, or anything destructive. Never trivial.
_Avoid_: risky change, careful change

**Done-check**:
The hook that refuses to end a turn once, when the project changed and verification did not follow.
_Avoid_: stop guard, completion hook

**Design lens**:
The ten axes the grill checks its design tree against before calling the frontier empty.

**Shared rules**:
The one reference that holds each rule several Seams skills follow (effort, the repository facts, the sensitive list, the stages, evidence, worktrees, official docs, the continuous flow, and the table of how much process a change gets by its size and risk); a skill names the section a step needs instead of repeating it.
_Avoid_: common rules, policy (the bootstrap is the routing policy)

**Handover**:
The four-part closing message of a ticket: run it, try it, what changed, next.
_Avoid_: summary, wrap-up

## Lifecycle

**Candidate**:
The exact committed state that a review, a verification or a release refers to; a later change makes a new candidate.
_Avoid_: the branch, the work, current changes

**Record commit**:
A ticket's last commit, made just before its definition of done: it brings the progress file to the stage reached and the next step, and it is the candidate the definition of done refers to.
_Avoid_: wrap-up commit, bookkeeping commit

**Parallel run**:
Two or more unblocked tickets that the user picked to build at once: each by a builder in its own worktree from local HEAD, then integrated onto the base branch one ticket at a time by the main conversation, with the full suite after each. A ticket that fails stays on its branch. The progress file's `## Parallel` section holds each ticket's state.
_Avoid_: batch (a `pr-review` word), fan-out

**Builder**:
The background subagent that builds one ticket of a parallel run in its worktree, through `implement`'s steps without questions, and ends with its handover. It never touches the progress file or another branch.
_Avoid_: worker, helper

**Quality bar**:
What every candidate that ships must meet: a definition of done covering how the change fails, is attacked, performs, is observed, is documented and is rolled back, each item proven by evidence, with scope and architecture sized to the stated needs plus the next order of growth.
_Avoid_: perfection, gold-plating, bare minimum, best effort

**Stage**:
The furthest point a piece of work has evidence for: designed, built, integrated, release-ready, deployed, operated. A handover names it; until the design is agreed, a progress file says `designing`.
_Avoid_: gate (that is the hook), phase, status

**Progress file**:
A feature's durable record of work in progress, kept beside its spec: the grill's settled decisions and open questions, the ticket in progress, the candidate, the stage and the next step. Unlike the ledger, it outlives the session. It is committed with the work it describes, so it holds decisions and pointers only. Its `Status` says whether work remains (`active`) or the feature is finished (`done`); that is not its Stage. A `pr-review` batch keeps one of the same shape beside its evidence, under the temp directory and never committed: its pull requests, each one's step and the command that continues it.
_Avoid_: state file, work log, notes

**Repository facts**:
The branch, the short HEAD, the first lines of the status and the progress files, which the Seams hooks add as context when `implement`, the grill or `release` starts. A snapshot, framed as data, with any name holding `<` or `>` left out: a skill re-reads git once it may have moved, and looks up a fact the hook did not give.
_Avoid_: pre-loaded context, git context

**Resume note**:
The few factual lines the session-start hook injects from the active progress files and the repository's unfinished `pr-review` batch (the newest three) at startup, resume, `/clear`, compaction and fork, so a fresh context continues where the work stopped; the user sees a one-line notice of it. It is data and a pointer: a skill re-reads the spec, the tickets and the git state before acting on it.
_Avoid_: summary, handoff (that is `/handoff`)

**Walking skeleton**:
The first ticket of a new app: one trivial path through build, CI, deploy and a smoke check, before any feature ticket.
_Avoid_: scaffold, boilerplate, MVP

**Incident**:
An outage or degradation that users feel now. Contain and restore come before diagnosis.
_Avoid_: bug, hotfix, emergency

**Containing action**:
The safest reversible action that stops users being affected, matched to what changed last; it stays in place until the fixed candidate runs.
_Avoid_: mitigation, remediation, workaround

**Outward action**:
An action that reaches users or the host during an incident (a rollback, a redeploy, a config or flag change, a restart, a message to users); never taken without a yes that names it.

**Post-mortem note**:
The record of an incident under `docs/incidents/`: timeline, impact, cause, what stopped it, what prevents it, and the follow-up tickets.
_Avoid_: RCA, incident report

**Incident handover**:
The closing message of an incident: the service now, what changed, the fix's stage, next and its owner.
_Avoid_: summary, wrap-up

**Release**:
Taking a candidate to the deployment target and proving that exact candidate is what runs.
_Avoid_: deploy (one step of it), ship, launch

**Operations handover**:
The closing message of a release: monitoring and alert owner, runbook, follow-ups, stage reached.
_Avoid_: summary, wrap-up

## Review

**Baseline**:
The merge-base of a pull request with its base branch, checked the same way as the candidate, so a failure the change did not cause is not blamed on it.
_Avoid_: main, master (a base branch moves; its merge-base with the candidate does not)

**Check**:
A command the repository itself treats as the bar for passing: a step its CI runs, a script that a CI step or a git hook runs, or a package script named as a check. Each check runs on the baseline and on the candidate, so every failure is attributed.
_Avoid_: test (one kind of check), CI job (where some checks run)

**Probe**:
A test a review writes to prove or disprove a finding. It belongs to the review, not to the pull request: it is never committed, never left in a tree a check runs on, and is offered to the author as a suggested test.
_Avoid_: repro, scratch test

**Finding**:
A review's point about a candidate: a claim with its severity (blocking, should fix, nit) and the evidence behind it (a failing check, a failing probe test, a reproduced behavior, or a cited line with its reasoning), or a question the review could not settle. A suspicion without evidence is only ever a question.
_Avoid_: issue (the tracker's word), comment (where a finding gets posted)

**Review handover**:
The closing message of a pull request review: whether each pull request is ready to merge, a note for each author whose pull request is not, each review posted or drafted, what was not verified, and what comes next.
_Avoid_: summary, report

**Fully verified**:
A review is fully verified at a pull request's head when at least one check ran and every check ran on both trees (none "could not run", none flaky), every finding but a question or praise is verified at that head and every blocking finding is proven, nothing is left under "not verified", every requirement line of the reference has an answer, and the head is unchanged at the moment of posting. The poster tests it against the evidence on disk, not the model's judgement.
_Avoid_: reviewed, checked (a review can be both and still not be this)

**Auto-post**:
Posting a review to GitHub, with its label, without asking: for any event, when the review is fully verified and the viewer can push to the repository (an approval also needs an independent reference with a requirement met, none unmet, and nothing blocking or broken, and no review posts that mentions a local path or a secret). A review that is not fully verified, or is in a repository the viewer cannot push to, is drafted and asked about, and `draft only` in the request turns auto-post off.
_Avoid_: automatic review (the review always runs; only the posting is automatic)

**Review label**:
The one label a posted review leaves on its pull request, in the prefix `pr-review:` (`approved`, `changes requested`, `commented`). It replaces the one a newer review left, and it never touches a label the repository itself uses.
_Avoid_: status, tag

**Take-over**:
The viewer fixing a pull request's findings themselves, on its author's branch where GitHub lets them push, else on a branch and pull request of their own that names the author's, instead of waiting for the author. Never a force push; the author keeps credit by `Co-authored-by:`; the push waits for the viewer's yes, and so does the merge.
_Avoid_: hijack, rewrite

**Reference**:
What a pull request is meant to do and what output is expected of it, from a source other than its author's own description: a path or issue URL in the request, a Seams ticket or spec found from its branch or commits, or a linked issue. Its acceptance criteria and "must not happen" items are the review's requirements, each verified and recorded. One inside the pull request's own branch is read from the baseline, so a pull request cannot edit its own acceptance.
_Avoid_: spec (one kind of reference), description (the author's own claim)

## Evidence

**Scenario**:
One prompt, the fixture setup it runs in, its expectation and the graders that agree with it: a `claude plugin eval` case, one directory under `plugin/evals/`.
_Avoid_: test case (the deterministic suites' unit), benchmark

**Arm**:
One set of a scenario's runs under one condition: with the plugin loaded, or without it. The difference between the two arms' scores is what the plugin contributed.
_Avoid_: variant, control group

**Run record**:
What one headless run did, as the eval wrote it down: the first committing call, refusals, failed calls, denials, how it ended.
_Avoid_: log, transcript (that is the raw stream the record was read from)

