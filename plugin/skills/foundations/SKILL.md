---
name: foundations
description: Use when starting in a repo for the first time, or when it lacks run, test or typecheck commands, lint, pre-commit hooks, CI, a glossary, boundary rules, or the production basics (deploys, environments, backups, monitoring, scanning)
---

# Foundations

A senior engineer's first hour in a repo: find out what's there, name what's missing, and offer to set it up. This skill reports first and writes nothing without a yes.

**Effort** `${CLAUDE_EFFORT}`: at `low`, skip only the report's line on why each gap matters (shared rules: Effort).

## 1. Survey

Look, don't ask. Hand the rows below to `seams:scout` agents, split between two or three of them and all started in one message. Each item comes back *present*, *missing* or *partial*, with the evidence (the file or script found):

| Item | What counts as present |
| --- | --- |
| Run instructions | a README that says how to start and use the project |
| Verify commands | test and typecheck scripts (`package.json`, `Makefile`, or the language's equivalent), and how to run them |
| Lint and format | a linter or formatter configured and runnable |
| Pre-commit hooks | hooks that run format, typecheck and tests on commit (`.husky/`, `.pre-commit-config.yaml`, `lefthook`) |
| CI | a workflow that runs the verify commands on push or PR (`.github/workflows/`, or the host's equivalent) |
| Glossary and decisions | `CONTEXT.md` at the root, `docs/adr/` |
| CLAUDE.md within budget | CLAUDE.md under 200 lines, the rest in `docs/` or path-scoped `.claude/rules/` (shared rules: Where docs go); Claude Code loads it whole into every session |
| Issue tracker config | `docs/agents/issue-tracker.md` (what `to-spec`, `to-tickets`, `code-review` and `triage` read) |
| Boundary enforcement | dependency rules such as `.dependency-cruiser.*`, or a monorepo tool that enforces package boundaries |
| Environment and secrets | `.env.example` naming every variable the code reads, and `.env` in `.gitignore` |
| Deploy target and pipeline | where the code runs (a platform config, a deploy workflow or script, a store or registry manifest) and how a commit gets there |
| Environments and config | the environments named (staging, production, or the target's tracks), where each variable's value comes from per environment (the platform's config, not the repo), secrets in the platform's store |
| Backups and restore | for persistent data: scheduled backups, and a restore that has been rehearsed (a runbook line or a script) |
| Monitoring and alerts | error tracking or logs a person can reach, an alert that reaches a person, a health or version endpoint |
| Dependency and secret scanning | a dependency audit and a secret scan in CI or pre-commit (`npm audit`, Dependabot or Renovate, gitleaks, `detect-secrets`) |

An item that can't apply is marked *not applicable* with the reason, never left out (no CI for a scratch script; no boundary rules for a single file). The five production rows are not applicable for a library or package that is published nowhere and for a script that is deployed nowhere. A published package has a target (its registry), a pipeline and scanning; only backups and monitoring are not applicable for it.

## 2. Report

One table: item, status, evidence, and for each gap one line on why it matters *for this repo*. Then a recommendation: the two or three gaps worth closing first, in order. Small repos need less; say so when that's the case, rather than recommending everything.

## 3. Offer

Ask with AskUserQuestion which gaps to close now, multi-select, recommended ones first. Close each chosen gap through the skill that owns it, one at a time, and each of those asks its own questions:

- Issue tracker, glossary layout, triage labels → `/setup-matt-pocock-skills` (user-only: tell the user to run it, and stop until they have)
- Pre-commit hooks → `setup-pre-commit`
- Boundary enforcement in a TypeScript repo → `setup-ts-deep-modules`
- Run instructions, verify commands, `.env.example`, a CI workflow → write them yourself, matching the repo's package manager and existing conventions; show each file before writing it
- Deploy target and pipeline, environments and config, monitoring → the platform's skill when one is installed (for example `vercel:deploy`, `expo:eas-workflows`, `wrangler`); otherwise write the CI or deploy workflow, a per-environment `.env.example` and a runbook skeleton (`docs/runbook.md`: deploy, roll back, restore, who to page) yourself, each shown before writing
- Backups and restore, dependency and secret scanning → the platform's scheduled backups and a rehearsed restore in the runbook; an audit and a secret scan added to CI or the pre-commit hooks
- CLAUDE.md over budget → split it yourself, only on the user's yes to a plan naming each section and its destination: each section moved verbatim, one about a part of the code to `.claude/rules/<topic>.md` with `paths:` globs for that code, any other to `docs/agents/<topic>.md`; CLAUDE.md keeps the commands, the conventions, the gotchas and the agent-skills block, with one plain-text line naming each moved file, never an `@` import. Show the new CLAUDE.md before writing, and commit the split on its own
- Permission prompts on routine read-only commands (not a survey row: offer it in the same question) → `/fewer-permission-prompts`, which the user runs: it reads past sessions' transcripts for the read-only Bash and MCP calls that keep asking, and adds an allowlist to the project's `.claude/settings.json`. Permission rules are the user's to set, so tell them to type it.

Anything not chosen stays in the report for another day. Done when every chosen gap is closed and its verify command has been run once with the output shown.
