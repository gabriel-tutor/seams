# Seams

The vocabulary of the Seams plugin: a Claude Code workflow in which Matt Pocock's engineering skills lead every session, from a request to production. This file names the concepts; the skills say what to do with them.

## Language

**Route**:
The first skill a request is sent to, chosen from the bootstrap's table by the request's size and risk.
_Avoid_: classification, triage (that word belongs to `/triage`)

**Bootstrap**:
The routing policy injected into every session at start, clear and compaction.
_Avoid_: system prompt, preamble

**Declaration**:
A Skill invocation of a process skill, by Claude or typed by the user, that opens the gate for the current request.
_Avoid_: unlock, override

**Gate**:
The hook that refuses any change to the project until the current request has a declaration. In a flow skill, also the question that must get a yes before the skill starts or publishes.
_Avoid_: guard, blocker, permission

**Ledger**:
The per-session record of declarations and changes that the gate and the done-check read.
_Avoid_: state file, cache, log

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

**Handover**:
The four-part closing message of a ticket: run it, try it, what changed, next.
_Avoid_: summary, wrap-up

## Lifecycle

**Candidate**:
The exact committed state that a review, a verification or a release refers to; a later change makes a new candidate.
_Avoid_: the branch, the work, current changes

**Stage**:
The furthest point a piece of work has evidence for: designed, built, integrated, release-ready, deployed, operated. A handover names it.
_Avoid_: gate (that is the hook), phase, status

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

## Evidence

**Scenario**:
One prompt, the fixture setup it runs in, and its expectation: the routing harness's unit and a `claude plugin eval` case are the same directory under `plugin/evals/`.
_Avoid_: test case (the deterministic suites' unit), benchmark

**Arm**:
One set of a scenario's runs under one condition: with the plugin loaded, or without it. The difference between the two arms' scores is what the plugin contributed.
_Avoid_: variant, control group

**Run record**:
What one headless run did, as the harness or the eval wrote it down: the first committing call, refusals, failed calls, denials, how it ended.
_Avoid_: log, transcript (that is the raw stream the record was read from)

