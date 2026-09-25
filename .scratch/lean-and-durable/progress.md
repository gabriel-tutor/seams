# Progress: lean and durable (Seams roadmap, phase 1 of 4)

Status: active
Stage: integrated
Next: Ticket 02's build is committed on main; review it with code-review against starting commit 7ba5a98, then fix the findings and run the definition of done.
Updated: 2026-09-25
Ticket: 02

- Designed: the grill finished on 2026-09-25, the user confirmed it, and ADR 0003 is written. The spec is `.scratch/lean-and-durable/spec.md`, and the 14 tickets are `.scratch/lean-and-durable/issues/01–14`.
- Done: ticket 01 (3.2.1, released 2026-09-25 at `3a234bd`, which is still `origin/main`); ticket 04 (the progress file and the resume note) and ticket 05 (specs, tickets and builds keep the progress file), both integrated on local `main`, not pushed. Their records are in the tickets' Comments. The user chose 04 first, so that every later `/clear` resumes by itself.

## Decisions

1. Quality bar: a full bar with right-sized scope. Everything that ships meets a wider definition of done, each item proven: failure paths tested, security, performance, observability, docs, rollback. Scope and architecture fit the stated needs plus the next order of growth, and nothing is added that nobody asked for. (`CONTEXT.md`: Quality bar)
2. Order: optimize first, one phase at a time. Each phase is grilled, specced, built and released on its own:
   1. speed, tokens, `/clear` and compaction, and reliability of today's skills;
   2. grounding in official docs, plus MCP, Chrome and Playwright;
   3. system design with diagrams;
   4. delivery, versioning, operations, security and performance.
3. Durable state: a progress file beside the feature's spec, updated at every step. The session-start hook injects a resume note from it at startup, resume, `/clear`, compaction and fork. (`CONTEXT.md`: Progress file, Resume note)
4. Built-ins: phase 1 wires in the Claude Code built-ins that make today's flow faster and more reliable:
   - `/review` (the bundled correctness review) alongside Matt Pocock's `code-review`;
   - `/security-review` on sensitive changes;
   - `/simplify` on offer;
   - `/verify` and `/run` for user-facing changes;
   - `/skill-doctor` for measuring;
   - `/fewer-permission-prompts` in foundations.

   Phase 3 adds `/design` mockups for UI tickets, which it triggers only when the project and the ticket have a UI, and `frontend-design` for building them.
5. Grill pace: the grill asks every independent frontier question at once, up to four in one AskUserQuestion call. Gate, security and destructive questions still come one at a time.
6. Skill size: every SKILL.md stays under 4,000 tokens (headroom below the 5,000-token compaction cap). Gates, must-nots and the step list come first, and detail moves to references read on demand. A test fails the build on any skill over the cap. `pr-review` (about 8.8k tokens by `claude plugin details`) is split first.
7. Progress file: always `.scratch/<feature>/progress.md`, even when tickets live on GitHub or Linear. It is committed with the work it describes (the spec commit and each ticket's commit). The resume note lists up to three unfinished features, newest first, in under 1,500 characters.
8. Recurring cost: descriptions lead with their trigger and drop repetition, about a quarter shorter. Today they are about 1,165 tokens always on, plus a 2,580-byte bootstrap. The bootstrap keeps its 2,900-byte cap but is rephrased as the project's routing facts instead of commands. Any wording change must keep the routing evals at their current pass rate.
9. Model and effort: no skill pins either. Skills read `${CLAUDE_EFFORT}` and pass it on, for example `/review high`. At low effort a skill skips only optional extras, never a gate or a check. (A differing `model` in frontmatter would also force a prompt-cache miss.)
10. Subagents: each flow skill says when to delegate and asks for it by name: exploring beyond a few files, docs, fact-finding, and every review. Independent reads run in parallel. Seams ships read-only agent definitions (limited `tools`, a `maxTurns` cap) so that delegated work can't edit. The main context keeps decisions and edits.
11. Pre-loading: skills use `` !`cmd` `` only for fast, read-only facts (branch, HEAD, short status, the progress file). Each command is written so it can't fail and is pre-approved in `allowed-tools`. Bundled scripts use `${CLAUDE_SKILL_DIR}` paths, pre-approved the same way, so they run without prompts. Every skill still works when `disableSkillShellExecution` is on.
12. Reviews scale with risk:
    - Features and builds get Matt Pocock's `code-review` plus `/review` at the session's effort.
    - Sensitive changes also get `/security-review`, which is required.
    - `/simplify` is offered only on large diffs.
    - User-facing changes end by offering `/verify`.
    - Every finding goes through `receiving-code-review`, so only correctness and requirement gaps are acted on.
    - Confirm in the build that Claude can invoke `/review` itself. If it can't, use a Seams correctness-review subagent.
13. Parallel tickets: when two or more tickets have no open blockers, `implement` offers to build them at once. Each ticket gets one background subagent in its own worktree, running the full implement flow on seams the grill already settled. Integration is one ticket at a time, with the full suite run on each. The user picks the tickets. (Build note: create those worktrees from local HEAD. `worktree.baseRef` defaults to `fresh`, which leaves out unpushed commits such as the spec.)
14. Gate shells (sensitive):
    - `Monitor` commands go through the Bash classifier; a WebSocket watch changes nothing.
    - Before a declaration, every PowerShell command counts as a change, except a short read-only list: `Get-Content`, `Get-ChildItem`, `Select-String`, and `git status`/`diff`/`log`.
    - Both fixes ship with regression tests, including bypass cases:
      - the false positive where `>` inside a quoted `$(…)` counted as a write;
      - typed skill declarations recorded from `UserPromptExpansion`.
15. Gate mid-turn (sensitive): every typed message still starts a new request. The prompt hook tells Claude which declaration just lapsed, so before its next edit Claude re-invokes that skill (if the message continues the same work) or routes the new work. No refused calls. A re-invocation with identical content costs only a short note.

16. Proof: phase 1 ships when all of these hold:
    - every SKILL.md is under 4,000 tokens;
    - always-on cost is at least 25% lower (`claude plugin details`);
    - the unit, hook and plugin-guard suites pass: the gate's false-positive and bypass tables, the resume note for each source, the token caps, and `claude plugin validate --strict`;
    - no routing or gate eval case drops;
    - new cases prove that a grill, a ticket and a `pr-review` batch continue correctly after `/clear` (a fresh session over a progress file) and after `/compact` (headless `--resume`).

    Paid eval runs are asked before each run.
17. Release: 3.2.1 is released first, through `release` and the user's yes. Phase 1 ships as 3.3.0, and later phases as 3.4, 3.5 and 3.6.
18. A bounded change's grill (the next step is `tdd`: no spec, no `implement`) closes its own progress file: its `Next` says to set `Status: done` in the commit that ships the change. Every grill keeps the file. (The user's choice while building ticket 04, 2026-09-25.)
19. `finishing-a-development-branch` becomes a Seams adaptation of the Superpowers copy, so the skill that merges also records integration. The other three Superpowers copies stay byte-identical. (The user's choice while building ticket 05, 2026-09-25.)
20. A ticket resumed in a fresh session continues without `implement`'s gate question when the progress file's ticket, branch and candidate match the git state: the yes given when the ticket started still covers it. A mismatch is reported and asked about instead. (The user's choice while building ticket 05, 2026-09-25.)
21. The resume note names a ticket in progress, in at most 60 characters, and says that `implement` continues it, as it says the grill continues a grill in progress. A resumed ticket then routes as reliably as a resumed grill. (Made while building ticket 05, beyond its criteria, and not the user's choice; the review flagged it, and the user may revert it.)

Design-lens defaults (confirmed by the user):
- Failure: a missing, unreadable or stale progress file never blocks anything, because the note is only a pointer. Skills re-read the spec, the tickets and the git state before acting, and report any mismatch.
- Security: the progress file is committed, so it holds decisions and pointers only, never secrets or personal data. The resume note is built from its fields, length-capped and stripped of markup, and framed as the repository's record, so a planted file can't pass as instructions.
- Scale: parallel tickets share the machine's check slots (half the cores, as in `pr-review`) and stay within the 20-subagent limit.
- Observability: when unfinished work exists, the user also sees a one-line notice, "resuming <feature> at <stage>". The README documents how to measure token use: `claude plugin details`, `/skill-doctor`, and OTel with skill names.
- Operability: the README gets a table of surfaces showing where Seams loads fully and where it doesn't, and lists the settings that silently switch it off: `disableAllHooks`, `allowManagedHooksOnly`, `--bare` and `--safe-mode`.
- Reversibility: ADR 0003, "Work in progress lives in a committed progress file", is the one decision that is costly to reverse once repos accumulate these files.

Other fixes that need no decision (from the full docs read):
- SessionStart also runs on `resume` and `fork`.
- The Stop done-check gives its feedback through `hookSpecificOutput.additionalContext` instead of a hook-error block.
- Hooks run in exec form (`args`).
- The temp-write exemption uses the hook input's `scratchpad_dir` (v2.1.257 and later).
- The version lives only in `plugin.json`, not also in the marketplace entry.
- The stale `__pycache__` in `plugin/` is removed.
- `pr-review`'s wrong claim that subagents can't start subagents is fixed.

Surfaces: plugins that a repo enables don't load in cloud sessions (the user enables Seams on their claude.ai account instead). Desktop WSL loads no plugins. `-p` disables AskUserQuestion, and skills fall back to asking in text.

## Tickets (blockers first)

| # | Ticket | Blocked by |
| --- | --- | --- |
| 01 | Release 3.2.1 (done: `3a234bd`, deployed 2026-09-25) | none |
| 02 | The gate sees every shell and stops tripping on quotes (sensitive) | 01 |
| 03 | Typed skills, the lapse hint, a calmer done-check (sensitive) | 01 |
| 04 | Progress file and resume note, end to end through the grill (done, on local `main`) | 01 |
| 05 | Specs, tickets and builds keep the progress file (done, on local `main`) | 04 |
| 06 | pr-review under the cap, scripts without prompts | 01 |
| 07 | A pr-review batch resumes | 04, 06 |
| 08 | Every skill under the bound, lighter always-on cost | 06 |
| 09 | Read-only agents and explicit delegation | 08 |
| 10 | Pre-loaded facts | 08 |
| 11 | The quality bar in the definition of done; reviews scaled to risk | 09 |
| 12 | Unblocked tickets built in parallel | 05, 11 |
| 13 | Docs: resuming, surfaces, off switches, measuring, versions | 02, 03, 07, 10, 12 |
| 14 | Release 3.3.0 | 01–13 |

## Open questions

- Nothing open in the design. The grill's frontier is empty and confirmed, and the spec and tickets are published.

## Later phases: facts already verified (2026-09-25, official sources)

- **Phase 2:**
  - Docs lookup:
    - The Claude Code docs MCP: `claude mcp add --transport http claude-code-docs https://code.claude.com/docs/mcp`.
    - Context7: `mcp.context7.com/mcp`; the API key raises rate limits.
    - Microsoft Learn MCP.
  - Browser:
    - Playwright MCP: `claude mcp add playwright npx @playwright/mcp@latest`.
    - Playwright CLI: `@playwright/cli`, which its README says uses fewer tokens than the MCP server.
    - Chrome DevTools MCP.
    - Claude in Chrome needs a claude.ai login, and is unavailable on Bedrock, Vertex, Foundry and WSL.
  - Vendor MCP servers verified: GitHub, Vercel, Netlify, Railway, AWS, Azure, Supabase, Neon, Prisma, PlanetScale, Sentry, Datadog, Grafana, PagerDuty, Stripe, Figma, Linear and Atlassian.
  - The MCP Registry is still in preview.
  - WebSearch is unavailable on Bedrock.
  - WebFetch is lossy, so use `curl` for raw pages.
- **Phase 3:**
  - `/design` needs v2.1.265 or later and a session with artifacts, so not Bedrock, Vertex or Foundry.
  - Mermaid 12.0.0 (2026-09-10) made ELK the default layout. Its C4 diagrams are experimental, and `architecture-beta` is beta.
  - C4 model; arc42 9.0; MADR 4.0.0.
- **Phase 4:**
  - Versioning and changelogs: SemVer 2.0.0, Conventional Commits 1.0.0, and Keep a Changelog 2.0.0 (2026-06-07, which adds a `**Breaking:**` marker).
  - Release tools: release-please 17.11, semantic-release 25, and Changesets 3.0 (ESM-only).
  - Delivery metrics: DORA's five metrics (rework rate added).
  - Feature flags: OpenFeature spec 0.9.0.
  - Security:
    - OWASP Top 10:2025, ASVS 5.0.0, the LLM Top 10 2026, and the Agentic Top 10 2026.
    - NIST SSDF 1.1 is final and 1.2 is a draft.
    - SLSA 1.2.
    - SBOM formats: CycloneDX 1.7 and SPDX 3.0.1.
  - Observability: OpenTelemetry spec 1.61 and semantic conventions 1.44.
  - WCAG 2.2; WCAG 3 is only a draft.
  - Core Web Vitals: LCP ≤ 2.5 s, INP ≤ 200 ms, CLS ≤ 0.1.
  - MCP spec revision 2026-07-28 (stateless).

## Facts

All from the Claude Code docs mirror at `/Users/gabrieltutor/claude-docs/code.claude.com-docs-en`, fetched 2026-09-24:
- After compaction, invoked skills keep their first 5,000 tokens each and 25,000 tokens in total, newest first. `SessionStart` hooks with the `compact` source re-inject. Hook-added context is summarized. (`context-window`, `skills` §Skill content lifecycle)
- Hook `additionalContext` is capped at 10,000 characters and should be written as facts. `SessionStart` sources are `startup`, `resume`, `clear`, `compact` and `fork`. `PreCompact` can only block. `PostCompact` has no decision control. (`hooks`)
- Skill frontmatter includes `model`, `effort`, `context: fork`, `agent`, `background`, `paths`, `hooks` and `when_to_use`. Descriptions are capped at 1,536 characters, and the skill listing gets 1% of the context window. `/skill-doctor` needs v2.1.252 or later. (`skills`)
- A plugin output style with `force-for-plugin: true` overrides the user's style. A plugin-root CLAUDE.md is not loaded. `claude plugin details` shows each component's token cost. `claude plugin eval` needs v2.1.269 or later. (`output-styles`, `plugins-reference`, `plugin-evals`)
- Ten parallel readers covered all 276 files, 276 of 276 read in full: parts 1–10 read 16, 23, 19, 50, 21, 37, 29, 40, 1 and 40 files. Their key facts are folded into the decisions above.
