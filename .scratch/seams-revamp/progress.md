# Progress: Seams revamp, faster and lighter at the same quality

Status: active
Stage: designed
Next: Build ticket 01 (A suite that runs in under a minute) with implement, in a worktree, never live in plugin/; then 02, 03 and 04 are unblocked.
Updated: 2026-10-02

## Spec

`.scratch/seams-revamp/spec.md` (Seams 4.0: fast and continuous, at the same quality), ready-for-agent.

## Tickets

- 01 A suite that runs in under a minute (blocked by: none)
- 02 No test sleeps, each behavior tested once (blocked by: 01)
- 03 Wording pins shrink to the contracts (blocked by: 01)
- 04 A route lasts (blocked by: 01)
- 05 Lighter hooks (blocked by: 04)
- 06 A continuous flow (blocked by: 03, 04)
- 07 One shared reference, process in proportion (blocked by: 03, 06)
- 08 Docs and proof (blocked by: 02, 05, 07)
- 09 Release 4.0.0 (blocked by: 08)

## Decisions

1. Phased, speed first (the user's choice, 2026-10-02). Phase 1: faster and lighter (hooks, skill text, the test suite, a continuous flow). Phase 2: project-type intelligence, e2e through MCPs, official-docs lookup. Phase 3: Claude Code's bundled skills woven into the flow. Each phase is a release the user can use. This continues the four-phase roadmap of 2026-09-25 (lean-and-durable was its phase 1; its phase 2 was docs grounding and the MCP toolbelt).
2. A continuous flow (the user's choice): once a design is confirmed, grill, spec, tickets, build, review and release chain by themselves; the flow stops only for the user's decisions, deploys and publishes, pushes, destructive actions, and paid runs. This replaces the routing rule that each step asks before it starts.
3. Official docs (the user's choice): always, for anything third-party. Before writing or reviewing code that uses a library, framework, platform, CLI or API, check its official docs for the version in use (Context7 or the vendor's site) and cite them; repo-internal logic needs no lookup.
4. How the revamp is built (the user's standing rule after 2026-10-02, memory "protect the user's machine"): in a git worktree, never live in `plugin/`, which the user's other sessions load in place; nothing CPU-heavy runs on the user's Mac without asking first.
5. The context management stays (the user's words, 2026-10-02: "please don't remove the feature of our plugin skills like the context management so even next session it can pickup the actual context", and "because i like the skills how it note every changes"): the committed progress files that note every decision and step, the session-start bootstrap and its resume note, and the repository facts a skill starts with all stay, so a new session, `/clear` or a compaction picks up where the work was. The revamp may make them cheaper, never remove them or note less.
6. Enforcement stays, without the friction (the user's choice, 2026-10-02): the gate still refuses changes no skill has routed and the done-check still asks for verification before a turn that changed the project ends; but a declaration lasts until the work it routed is committed or another route is invoked, so a typed reply no longer lapses it; the hooks become one lighter script. Accepted risk: an unrelated request typed mid-task rides on the current route.
7. The test suite becomes fast and behavior-first (the user's choice): suites run in parallel; the macOS Python 3.9 compatibility run moves to one CI job instead of re-running everything locally; the ~750 wording pins shrink to the few that guard real contracts (sizes, frontmatter, routing rows, injected commands); real sleeps become fake clocks. Target: under a minute on the user's Mac.
8. The eval scenarios stay, the custom harness goes (the user's choice): `plugin/evals` stays for Claude Code's own `claude plugin eval`; `scripts/behavior_test.py`, `scripts/prepare_run.sh`, `scripts/fixture_deps.sh` and their tests are removed, and with them the suite's only need for Node.
9. Python and bash stay, made fast (the user's choice): the time is in waiting, not in Python; the gate is split so each hook loads only what it needs (37 ms toward about 20), the suites run in parallel, and no test sleeps.
10. Process is proportional to size and risk (the user's choice): scouts, reviewers and question rounds scale with the change; a one-line fix gets one check, a feature or anything sensitive gets the full set (both reviews, the security review, verification). Each rule is written once, in one shared reference the skills point to.
11. Design depth (the user's choice): phase 1 is grilled to the end and specced now; phases 2 (stack intelligence, e2e drivers, docs lookup) and 3 (bundled skills in the flow) are outlined now and grilled in full when each starts, with that day's facts.
12. Proof (the user's choice): the eval scenarios run with `claude plugin eval` on 3.4.0 and on the candidate (paid, each run asked first): no scenario may get worse; and cost is measured on 3 scripted tasks (tool calls, tokens, wall time), one run at a time so the Mac stays usable.
13. pr-review in phase 1 (the user's choice): only the shared rules; it points to the one shared reference like the other skills, and its steps, scripts and checks stay exactly as in 3.4.0. The cancelled lighter-checks change is not revived.
14. Phase 1 ships as 4.0.0 (the user's choice): the continuous flow and the declaration's new lifetime change how every session works.
15. A declaration ends when another process skill is invoked or the session is cleared (the user's choice): it holds through typed replies and commits; the routing text still tells Claude to route new work. CONTEXT.md's Declaration and Gate say so.
16. Integrating a finished branch stays a real gate (the user's choice): it always asks how (merge locally, a pull request, keep or discard), as today; decision 2's chain stops there.
17. Scouts run on Sonnet 5.5, reviewers on the session's model (the user's choice): fact-finding faster and cheaper; reviews, where quality decides, unchanged.
18. Phase 1's tests (the user's choice): the declaration's lifetime and the refusals on the gate module in process; one command-line smoke per hook event; the contract pins (sizes, frontmatter, routing rows, injected commands); and a test that fails when the suite runs over its time budget.
19. Design-lens points, mine (the user may overrule them): the merged hook still fails open, as every hook does today (a crash never blocks the user's work); 4.0.0 reads 3.4.0's per-session ledger or starts it fresh, never refuses on an old one; removing the eval harness and the duplicated tests touches nobody's install; CI gains one Python 3.9 job (a CI change, so it gets the security review); a rollback is reinstalling 3.4.0. The stale manual-only declaration code in the gate goes with the split.

20. ADR 0005 records decisions 6, 10 and 15 (the user's yes, 2026-10-02). The user confirmed the shared understanding of phase 1 and asked for the spec.

## Outline of phases 2 and 3 (grilled in full when each starts)

- Phase 2, the project's own stack and its official docs: the session start or `foundations` reads the stack from its manifests (package.json, pyproject, go.mod, Cargo.toml, app.json, Podfile, build.gradle, Dockerfile) and the drivers installed; an e2e check uses the stack's driver, CLI first where the vendor says it is cheaper (Playwright CLI or MCP and Chrome DevTools for the web, Claude in Chrome when the plan allows it, Maestro, MobileBuildMCP, the Android CLI and adb for mobile, plain runs for CLIs and APIs, computer use last); missing drivers are offered, never installed unasked; Context7 or the vendor's docs back decision 3.
- Phase 3, Claude Code's bundled skills in the flow: where each fits (`/code-review` and `/security-review` can be invoked by Claude; `/simplify` at the refactor step; `/run` and `/run-skill-generator` for launching an app; `/verify` only the user can run, so the flow offers it rather than calling it), without replacing Matt Pocock's skills the user relies on.

## Open questions

- None for phase 1; phases 2 and 3 are grilled when they start.

## Facts

- Hook cost, measured 2026-10-02 on the user's Mac at load 2: each firing of the gate's hooks (PreToolUse, Stop, UserPromptSubmit) takes about 37 ms, of which 12 ms is starting Python and the rest importing the 1,567-line gate module. PreToolUse fires on every Edit, Write, Bash, PowerShell and Monitor call (subagents included), PostToolUse on every Skill call, Stop at every turn's end, UserPromptSubmit on every prompt.
- The bigger cost of the enforcement is round trips, not milliseconds: every typed reply that is not a short go-ahead lapses the declaration, so the next change is refused until a skill is invoked again (one more Skill call, and its body read again); a turn that changed the project without the verification skill gets one more Stop round. This grill hit it twice in one exchange on 2026-10-02.
- The skills (14, about 95 KB of SKILL.md) force extras whatever the size of the change: scouts "however small the codebase" (grill, foundations), always `code-review` plus a correctness reviewer in `implement`, a progress-file write after every grill round, a 12-row done table. The same rules are written in several places (the Effort line in 10 skills, the repository-facts paragraph in 3, the sensitive-areas list in 7, the progress-file rules in 6 or 7), and two pairs contradict (fresh evidence against reused evidence; EnterWorktree preferred against never).
- The test suite: `scripts/test.sh` runs 8 suites one after another; 326 Python tests and about 329 shell checks test behavior, and `test_plugin.sh` holds about 750 pins on skill and README wording. On macOS every Python test, `test_hooks.sh` and `test_plugin_hook.sh` run a second time under the system Python 3.9. 1,136 test lines guard the eval tooling (`behavior_test.py`, `prepare_run.sh`, `fixture_deps.sh`), the only part that needs Node. Rewriting the runner in Rust or Go would remove almost none of the time: it waits on the processes it must start (the hooks and scripts under test are Python), on git, bash and Node, and on fixed sleeps and timeouts.
- E2E drivers (official docs, 2026-10-02): Playwright MCP (`@playwright/mcp`, or the token-cheaper `@playwright/cli` with skills), Chrome DevTools MCP, Claude in Chrome (Pro/Max/Team/Enterprise with `/login`), Maestro MCP (`maestro mcp`, needs Java), Expo MCP (Expo account, SDK 54+), MobileBuildMCP (XcodeBuildMCP's new name since 2026-09-23), the Android CLI and adb, computer use (macOS research preview, Pro/Max, interactive only, used last). Docs lookup: Context7 (free 1,000 calls a month), Microsoft Learn MCP, AWS Knowledge MCP. Anthropic and Microsoft both say CLI tools are more context-efficient than MCP servers.

- Bundled skills (Claude Code docs mirror, 2026-09-24): /code-review is model-invocable; /verify runs only when the user invokes it (since 2.1.215) and cannot be preloaded into a subagent; /security-review and /init can be called through the Skill tool; /run and /verify find how to launch an app from the project type and README, package.json or Makefile, and /run-skill-generator records it as a project skill; a plugin skill loads beside a bundled one of the same name; a plugin can ship MCP servers in `.mcp.json` that start when it is enabled.
- Hooks: PreToolUse and PostToolUse fire on every tool call and block until they finish; Stop fires at the end of every reply; SessionStart hooks should be fast (the docs); /doctor flags slow hooks.
- The skill listing budget is 1% of the context window, at most 1,536 characters a description.
