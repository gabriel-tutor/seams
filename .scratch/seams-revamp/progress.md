# Progress: Seams revamp, faster and lighter at the same quality

Status: active
Stage: designing
Next: Read the scouts' facts (the plugin's per-session cost, the test suite, the e2e drivers), then ask the next round: the gate and done-check, what goes from the test suite and in what language, and the phase-1 scope.
Updated: 2026-10-02

## Decisions

1. Phased, speed first (the user's choice, 2026-10-02). Phase 1: faster and lighter (hooks, skill text, the test suite, a continuous flow). Phase 2: project-type intelligence, e2e through MCPs, official-docs lookup. Phase 3: Claude Code's bundled skills woven into the flow. Each phase is a release the user can use. This continues the four-phase roadmap of 2026-09-25 (lean-and-durable was its phase 1; its phase 2 was docs grounding and the MCP toolbelt).
2. A continuous flow (the user's choice): once a design is confirmed, grill, spec, tickets, build, review and release chain by themselves; the flow stops only for the user's decisions, deploys and publishes, pushes, destructive actions, and paid runs. This replaces the routing rule that each step asks before it starts.
3. Official docs (the user's choice): always, for anything third-party. Before writing or reviewing code that uses a library, framework, platform, CLI or API, check its official docs for the version in use (Context7 or the vendor's site) and cite them; repo-internal logic needs no lookup.
4. How the revamp is built (the user's standing rule after 2026-10-02, memory "protect the user's machine"): in a git worktree, never live in `plugin/`, which the user's other sessions load in place; nothing CPU-heavy runs on the user's Mac without asking first.
5. The context management stays (the user's words, 2026-10-02: "please don't remove the feature of our plugin skills like the context management so even next session it can pickup the actual context", and "because i like the skills how it note every changes"): the committed progress files that note every decision and step, the session-start bootstrap and its resume note, and the repository facts a skill starts with all stay, so a new session, `/clear` or a compaction picks up where the work was. The revamp may make them cheaper, never remove them or note less.

## Open questions

- The gate and the done-check: keep, lighten, or replace (asked alone: it is the plugin's enforcement).
- The test suite: what is removed, what stays, how it is made fast, and in which language.
- Which skills, references, scripts and evals go, and which stay.
- Bundled Claude Code skills: which the flow uses, and how (Claude can invoke /code-review and /security-review; /verify only the user can run).
- Project-type intelligence and e2e drivers per stack.
- Seams of the tests for whatever is built.

## Facts

- Hook cost, measured 2026-10-02 on the user's Mac at load 2: each firing of the gate's hooks (PreToolUse, Stop, UserPromptSubmit) takes about 37 ms, of which 12 ms is starting Python and the rest importing the 1,567-line gate module. PreToolUse fires on every Edit, Write, Bash, PowerShell and Monitor call (subagents included), PostToolUse on every Skill call, Stop at every turn's end, UserPromptSubmit on every prompt.
- The bigger cost of the enforcement is round trips, not milliseconds: every typed reply that is not a short go-ahead lapses the declaration, so the next change is refused until a skill is invoked again (one more Skill call, and its body read again); a turn that changed the project without the verification skill gets one more Stop round. This grill hit it twice in one exchange on 2026-10-02.
- The skills (14, about 95 KB of SKILL.md) force extras whatever the size of the change: scouts "however small the codebase" (grill, foundations), always `code-review` plus a correctness reviewer in `implement`, a progress-file write after every grill round, a 12-row done table. The same rules are written in several places (the Effort line in 10 skills, the repository-facts paragraph in 3, the sensitive-areas list in 7, the progress-file rules in 6 or 7), and two pairs contradict (fresh evidence against reused evidence; EnterWorktree preferred against never).
- The test suite: `scripts/test.sh` runs 8 suites one after another; 326 Python tests and about 329 shell checks test behavior, and `test_plugin.sh` holds about 750 pins on skill and README wording. On macOS every Python test, `test_hooks.sh` and `test_plugin_hook.sh` run a second time under the system Python 3.9. 1,136 test lines guard the eval tooling (`behavior_test.py`, `prepare_run.sh`, `fixture_deps.sh`), the only part that needs Node. Rewriting the runner in Rust or Go would remove almost none of the time: it waits on the processes it must start (the hooks and scripts under test are Python), on git, bash and Node, and on fixed sleeps and timeouts.
- E2E drivers (official docs, 2026-10-02): Playwright MCP (`@playwright/mcp`, or the token-cheaper `@playwright/cli` with skills), Chrome DevTools MCP, Claude in Chrome (Pro/Max/Team/Enterprise with `/login`), Maestro MCP (`maestro mcp`, needs Java), Expo MCP (Expo account, SDK 54+), MobileBuildMCP (XcodeBuildMCP's new name since 2026-09-23), the Android CLI and adb, computer use (macOS research preview, Pro/Max, interactive only, used last). Docs lookup: Context7 (free 1,000 calls a month), Microsoft Learn MCP, AWS Knowledge MCP. Anthropic and Microsoft both say CLI tools are more context-efficient than MCP servers.

- Bundled skills (Claude Code docs mirror, 2026-09-24): /code-review is model-invocable; /verify runs only when the user invokes it (since 2.1.215) and cannot be preloaded into a subagent; /security-review and /init can be called through the Skill tool; /run and /verify find how to launch an app from the project type and README, package.json or Makefile, and /run-skill-generator records it as a project skill; a plugin skill loads beside a bundled one of the same name; a plugin can ship MCP servers in `.mcp.json` that start when it is enabled.
- Hooks: PreToolUse and PostToolUse fire on every tool call and block until they finish; Stop fires at the end of every reply; SessionStart hooks should be fast (the docs); /doctor flags slow hooks.
- The skill listing budget is 1% of the context window, at most 1,536 characters a description.
