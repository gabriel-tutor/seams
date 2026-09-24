# Seams 3.3: lean and durable

**Status:** ready-for-agent

Phase 1 of the four-phase roadmap agreed in the grill of 2026-09-25. Phase 2 grounds the skills in official docs, with MCP, Chrome and Playwright. Phase 3 adds system design with diagrams, including `/design` mockups for UI tickets. Phase 4 covers delivery, versioning, operations, security and performance. The grill's record is `.scratch/lean-and-durable/progress.md`, and the one hard-to-reverse decision is ADR 0003.

## Problem Statement

The user runs Seams every day and likes its workflow. What they want now is for it to be faster, cheaper in tokens, and reliable enough to trust completely, with nothing lost across `/clear` and compaction and no drop in the quality of what it produces. Today it falls short in four ways.

- **Work is lost between contexts.**
  - A grill's answers live only in the conversation until `to-spec` writes the spec, so `/clear` in the middle of a grill loses them. Compaction keeps only a summary.
  - After compaction, each invoked skill keeps only its first 5,000 tokens. `pr-review`'s instructions are about 8,800 tokens, so a long batch loses its posting, cleanup and handover steps.
  - The routing policy comes back after compaction, but nothing says what was in progress. After `/clear`, the user has to explain where they were.
  - The session-start hook ignores resumed and forked sessions.
- **It costs more tokens and time than it needs to.**
  - Every session carries about 1,165 tokens of skill descriptions plus a 2,580-byte bootstrap. An invoked skill's full text stays in context on every turn.
  - No skill uses the Claude Code features that save round trips or context: pre-loaded facts, delegation to subagents, pre-approved scripts.
  - The grill asks one question per turn.
  - Independent tickets are built one after another.
  - Reading and research fill the main context.
- **The gate trips when it shouldn't and misses what it should catch.**
  - A reproduced false positive: `x="$(awk '$1>0' f)"` is refused as "a redirect to a file".
  - Two tools that run shell commands, `Monitor` and `PowerShell`, bypass the gate.
  - Every message the user sends mid-turn resets the request. The next edit is then refused until the same skill is invoked again, which happened four times in one session.
  - The Stop hook's request for verification shows as a hook error.
  - The hooks use shell form.
  - One skill states a limit that no longer holds: that subagents can't start subagents.
- **The quality bar is narrower than the user's standard.**
  - `implement`'s definition of done checks tests, typecheck and lint, acceptance criteria, leftovers, docs and the commit message. It does not check failure paths, security, performance, observability or rollback.
  - Claude Code's built-in reviews go unused: `/review` for correctness, `/security-review`, `/simplify` and `/verify`.

## Solution

Seams 3.3 keeps the workflow exactly as it is, and makes it lean and durable.

- **Nothing is lost.** Every flow skill keeps a committed progress file for its feature (ADR 0003). The session-start hook turns it into a short resume note at startup, resume, `/clear`, compaction and fork. A grill, a ticket or a `pr-review` batch continues where it stopped, and the user sees a one-line "resuming…" notice.
- **Cheaper in tokens.**
  - Every skill's instructions stay under 4,000 tokens, with the rules first and detail in reference files read on demand. `pr-review` is split.
  - Descriptions are about a quarter shorter.
  - The bootstrap reads as the project's routing facts instead of commands.
  - No skill pins a model or effort level; skills pass the session's level on.
- **Faster.**
  - The grill asks up to four independent questions at once.
  - Skills pre-load read-only facts that cannot fail, and bundled scripts run without permission prompts.
  - Reading and research go to read-only subagents that Seams ships.
  - Tickets with no open blockers can be built in parallel worktrees.
- **Higher quality.**
  - The quality bar joins the definition of done: failure paths, security, performance, observability and rollback. Each is proven, or marked not applicable with a reason.
  - Reviews scale with risk. Matt Pocock's `code-review` runs alongside the bundled `/review`, and `/security-review` is required on sensitive changes. `/simplify` is offered on large diffs, and `/verify` for user-facing changes.
- **A gate that doesn't trip itself.**
  - The false positive is fixed.
  - `Monitor` goes through the Bash classifier, and `PowerShell` is strict apart from a short read-only list.
  - Typed skills are recorded from `UserPromptExpansion`.
  - A mid-turn message tells Claude which declaration lapsed, so it re-declares instead of having an edit refused.
  - The Seams read-only agents can never change the project.
  - Writes under the session's scratchpad are scratch.
  - The Stop hook's request reads as feedback, not an error.
- **Proven, not claimed.** Phase 1 ships only when all of the following hold:
  - the token budgets are met, and always-on cost is at least 25% lower by `claude plugin details`;
  - every suite is green;
  - no routing or gate eval case drops;
  - new cases show a grill, a ticket and a `pr-review` batch resuming correctly after `/clear` and after `/compact`.

## User Stories

1. As a developer, I want a grill's answers written down as they land, so that `/clear` in the middle of a grill loses nothing.
2. As a developer, I want the ticket I was building, its candidate commit and its next step written down, so that a fresh context picks the ticket up where it stopped.
3. As a developer, I want a `pr-review` batch's progress written down, so that after `/clear` or compaction the batch continues with the pull requests not yet reviewed, and does not start again.
4. As a developer, I want each new, resumed, cleared, compacted or forked session to be told what work is in progress, so that I never have to re-explain where I was.
5. As a developer, I want to see a one-line "resuming…" notice when unfinished work exists, so that I know what Claude was told.
6. As a developer, I want the resume note limited to the three most recent unfinished pieces of work, so that an old abandoned feature doesn't crowd the context.
7. As a developer, I want the resume note kept short (under 1,500 characters), so that it costs almost nothing per session.
8. As a developer, I want a missing, unreadable or stale progress file never to block a session or a skill, so that a bad file costs a question at most, never a stall.
9. As a developer, I want skills to re-read the spec, the tickets and the git state before acting on a resume note, so that a stale note never drives a wrong change.
10. As a developer, I want the progress file committed with the work it describes, so that it travels with the branch to another machine, a colleague or a self-hosted runner.
11. As a developer whose tickets live on GitHub or Linear, I want the progress file kept locally in the same place, so that resuming works whatever tracker I use.
12. As a developer, I want the progress file never to contain secrets or personal data, so that committing it is always safe.
13. As a developer cloning someone else's repository, I want the resume note built only from the progress file's fields, capped and stripped of markup, and presented as data, so that a planted file cannot pass as instructions.
14. As a developer, I want every skill's instructions to survive compaction whole, so that a long session never runs on half a skill.
15. As a developer, I want each skill's gates, must-nots and steps at the top, with detail in reference files it reads when needed, so that the part that matters is always in context.
16. As a developer, I want the plugin's always-on cost cut by at least a quarter, so that every session starts lighter.
17. As a developer, I want the routing policy written as the project's facts, so that Claude treats it as context and not as a suspicious out-of-band command.
18. As a developer, I want a wording change to the bootstrap to ship only if routing stays as good as before, so that saving tokens never costs accuracy.
19. As a developer, I want skills to use the effort level I chose, so that a skill never quietly lowers my `max` or raises my `low`.
20. As a developer, I want the review a skill starts to run at my session's effort level, so that depth follows my choice.
21. As a developer, I want skills to start with the branch, HEAD and working-tree status already in hand, so that they don't spend round trips looking them up.
22. As a developer, I want that pre-loading never to abort a skill, so that a missing `gh` or a disabled shell setting leaves the skill working.
23. As a developer, I want the plugin's own scripts to run without permission prompts, so that `pr-review` doesn't stop to ask about its own tools.
24. As a developer, I want exploration, docs lookups, fact-finding and reviews done by subagents that return conclusions with file and line or URL references, so that my main context keeps only decisions and edits.
25. As a developer, I want those subagents unable to change my project, so that delegating a read never becomes an unreviewed write.
26. As a developer, I want independent reads started in parallel, so that fact-finding takes as long as the slowest read, not the sum of them.
27. As a developer, I want the grill to ask every independent question at once (up to four), so that a design settles in fewer round trips.
28. As a developer, I want gate, security and destructive questions still asked one at a time, so that the risky decisions get my full attention.
29. As a developer with several unblocked tickets, I want to be offered to build them in parallel, so that independent work doesn't wait in a queue.
30. As a developer, I want to pick which tickets run in parallel, so that I stay in control of what happens at once.
31. As a developer, I want each parallel ticket built in its own worktree from my local HEAD, so that an unpushed spec or earlier ticket is never missing from it.
32. As a developer, I want parallel tickets integrated one at a time with the full suite on each, so that two green tickets never combine into a red main.
33. As a developer, I want parallel builds capped by my machine's cores and Claude Code's subagent limit, so that parallel work never grinds the machine down.
34. As a developer, I want a ticket that fails in parallel to stay on its own branch with its handover, so that one failure never blocks or corrupts the others.
35. As a developer, I want the definition of done to prove failure paths, security, performance, observability and rollback, or say why each doesn't apply, so that "done" meets my standard.
36. As a developer, I want nothing added that nobody asked for, so that the higher bar never becomes gold-plating.
37. As a developer, I want features and builds reviewed for correctness bugs as well as for standards and the spec, so that both kinds of defect are caught before the merge.
38. As a developer, I want sensitive changes to get a security review every time, so that auth, secrets and permissions never ship unreviewed.
39. As a developer, I want a cleanup review offered on large diffs only, so that small changes stay fast.
40. As a developer, I want every review finding checked against the code before it's acted on, and only correctness and requirement gaps fixed, so that reviews don't cause over-engineering.
41. As a developer, I want to be offered `/verify` after a user-facing change, so that I can confirm the change in the running app as well as in the tests.
42. As a developer, I want `foundations` to offer `/fewer-permission-prompts`, so that routine read-only commands stop interrupting me.
43. As a developer, I want read-only shell commands never refused by the gate, so that exploring the code before routing is never blocked.
44. As a developer, I want commands run through `Monitor` or `PowerShell` gated like Bash commands, so that no shell tool is a way around the workflow.
45. As a developer on Windows, I want common read-only PowerShell commands allowed before routing, so that looking around a repo there costs nothing.
46. As a developer, I want a skill I type recorded as a declaration however I typed it (a stacked command or a bare name), so that typing `/pr-review` or `/to-spec` always opens the gate.
47. As a developer, I want Claude told which declaration lapsed when I send a message mid-turn, so that it re-declares in one cheap call instead of hitting a refused edit.
48. As a developer, I want each new message to still need its own route, so that a declaration made for one piece of work never silently covers a different one.
49. As a developer, I want writes to the session's scratchpad treated as scratch, so that Claude's own working files never need a declaration.
50. As a developer, I want the verification reminder to read as feedback rather than as a hook error, so that the transcript stays readable.
51. As a developer, I want the hooks to run correctly even when the plugin's path contains spaces, so that where it's installed doesn't matter.
52. As a developer, I want to measure what Seams costs (always-on and per skill), so that I can see the savings myself.
53. As a developer, I want to know where Seams loads fully and where it doesn't (cloud sessions, Desktop WSL, `-p`), so that I'm never surprised by a missing gate.
54. As a developer, I want the README to name the settings that silently switch Seams off, so that I can tell why it isn't running.
55. As a developer, I want phase 1's claims proven by tests and evals before release, so that "faster and just as good" is evidence rather than a promise.
56. As a developer, I want to be asked before any paid eval run, so that I'm never billed by surprise.
57. As a developer, I want 3.2.1's `pr-review` fixes released before phase 1, so that I get them without waiting.

## Implementation Decisions

### The quality bar in the flow

- The bootstrap states the Quality bar as a fact: everything that ships meets a definition of done that covers how the change fails, is attacked, performs, is observed, is documented and is rolled back. Each item is proven, and nothing is added that nobody asked for.
- `implement`'s definition of done keeps its rows and gains five: **Failure paths**, **Security**, **Performance**, **Observability** and **Rollback**. Each is proven by the output of a command or a check, or marked "n/a" with a one-line reason. The table stays a table.
  - **Failure paths:** each new way the change can fail has a test.
  - **Security:** for a sensitive change, `/security-review`'s findings are resolved; and the diff introduces no secret.
  - **Performance:** a change on a hot path or to a growing collection is measured before and after.
  - **Observability:** a new failure is logged at its boundary or shown to the user.
  - **Rollback:** how this candidate is undone (a revert, a flag, a down-migration).
- Right-sized scope stays enforced. Review findings pass through `receiving-code-review`, and only correctness and requirement gaps are acted on. The grill's rule against features nobody asked for is unchanged.

### Durable state: progress files and the resume note (ADR 0003)

- **The progress file** is `.scratch/<feature>/progress.md`, beside the spec, whatever tracker the repo uses.
  - It opens with key-value lines:
    - `Status` (`active` or `done`);
    - `Stage` (a Stage from the glossary, or `designing`);
    - `Next` (one sentence);
    - `Updated` (a date);
    - optional `Ticket` and `Candidate`.
  - Then come sections for the grill's decisions, what is still open, and the facts gathered that are worth keeping.
  - It holds decisions and pointers only, never secrets, credentials or personal data.
- **Who writes it:**
  - The grill creates it at its first decision and appends each settled decision and the remaining open questions as answers land.
  - `to-spec` sets the stage to designed and points to the spec.
  - `to-tickets` records the ticket list and the next unblocked ticket.
  - `implement` records the ticket in progress, the candidate and the stage reached. After the last ticket it sets `done`, unless the spec has a Release section, in which case `release` sets `done` at its operations handover.
  - `finishing-a-development-branch` records integration.
- **When it's committed:** with the work it describes, by name. The spec commit covers the grill's record and the spec, and each ticket's commit covers that ticket's progress. `to-spec` and `to-tickets` commit their own files after the publish yes, and the question names the commit.
- **A `pr-review` batch** keeps a progress file of the same shape in the batch's evidence root: which pull requests are pinned, and each one's step (checked, reviewed, drafted, posted). Re-invoking `/pr-review` on the same pull requests continues the batch.
  - It reuses every pull request whose head hasn't moved and whose review finished.
  - It restarts only the unfinished ones, from their last completed step.
  - A pull request whose head moved is reviewed afresh, as today.
- **The resume note:**
  - The session-start hook runs at `startup`, `resume`, `clear`, `compact` and `fork`. After the bootstrap, it adds a resume note built from the `active` progress files of the session's repository and the repository's unfinished `pr-review` batch.
  - It lists three entries at most, newest `Updated` first. Each entry has the feature, its stage, its next step and the file's path.
  - It stays under 1,500 characters, and the whole injection stays well under Claude Code's 10,000-character hook cap.
  - It is framed as data from files in the repository. Every field is capped at 200 characters, flattened to one line and stripped of markup.
  - A file that doesn't parse is skipped.
  - When at least one entry exists, the hook also returns a one-line `systemMessage` for the user: "Seams: resuming <feature> (<stage>): <next>".
- **The resume note is a pointer, not the truth.** Every flow skill re-reads the spec, the tickets and the git state before acting on it, and reports a mismatch instead of acting on the note.
- The ledger keeps today's rules: reset at `startup` and `clear`, kept at `compact` and `resume`. A fork is a new session, so it starts with an empty ledger.

### Leaner skills

- **Size:**
  - Every SKILL.md stays under 4,000 tokens, which leaves headroom below the 5,000-token slice kept after compaction.
  - The static guard enforces it as a byte bound calibrated from `claude plugin details` on this plugin (about 2.9 characters per token): 11,000 bytes.
  - The release records the measured figures.
- **Layout:**
  - Frontmatter comes first, then the gates, the must-nots and the step list.
  - Detail moves to reference files next to the skill, each named in the first screen with a "read this when…" line.
  - Guidance that must hold throughout a task is written as standing instructions, not one-time steps, because a loaded skill isn't re-read.
- **`pr-review`** is split first: a core under the bound, with batch mode, checks, drafting and posting, and cleanup in their own references. `release`, `to-tickets` and `finishing-a-development-branch` are checked against the bound and trimmed if needed.
- **Descriptions:**
  - Each leads with its trigger and drops repetition.
  - The plugin's always-on cost drops at least 25%: from about 1,165 to about 875 tokens or fewer by `claude plugin details`.
  - `pr-review` stays user-invoked only (`disable-model-invocation`). Every other skill stays model-invocable, because the routing needs Claude to call it.
- **The bootstrap:**
  - It keeps its 2,900-byte cap.
  - It drops the `<EXTREMELY_IMPORTANT>` wrapper and imperative framing, and states the routing as the project's facts ("development work in this project starts with…"), as Claude Code's hook documentation advises.
  - It keeps every row and rule. Any wording change must keep the routing evals at their current pass rate.
- **Model and effort:**
  - No SKILL.md or agent definition sets `model` or `effort`. A differing `model` would also force a prompt-cache miss on that turn.
  - Skills that start a review pass the session's level from `${CLAUDE_EFFORT}`.
  - At low effort a skill skips only extras it marks optional, never a gate or a check.

### Faster work: delegation, pre-loading, parallel tickets

- **Agents that Seams ships:** two, both read-only, and neither pins a model, effort or permission mode.
  - **`scout`** handles exploration, docs lookups and fact-finding.
    - Its tools are Read, Glob, Grep, WebFetch and WebSearch. Leaving out Bash also brings Glob and Grep back on macOS and Linux.
    - It has a turn cap and skips CLAUDE.md.
    - It returns conclusions with file:line or URL citations, and says what it couldn't confirm.
  - **`reviewer`** handles correctness or security review of a named diff.
    - Its tools are Read, Glob, Grep and Bash, with Edit, Write and NotebookEdit disallowed. It has a turn cap.
    - It is the fallback for `/review` and `/security-review`.
  - The gate refuses any project change from either agent type, even when the request is declared.
- **Delegation rules:** each flow skill says when to delegate, and names the agent explicitly (on Opus 5, Claude Code tells Claude not to spawn subagents unless asked). Delegation happens when:
  - exploring beyond a few files;
  - reading docs;
  - fact-finding in the grill, `to-spec` and `foundations`;
  - running reviews.

  Independent reads start in parallel. The main context keeps decisions and edits.
- **Pre-loading:**
  - Skills use `` !`cmd` `` only for fast, read-only, fixed commands: the branch, the short HEAD, the first lines of `git status --short`, and the list of progress files.
  - Each command is written so it can't fail (`|| true`) and is pre-approved in the skill's `allowed-tools`.
  - No user argument is ever placed in an injected command.
  - Every skill says what to do when a pre-loaded fact is missing, which happens when `disableSkillShellExecution` replaces it.
- **Scripts:** bundled scripts are referenced through `${CLAUDE_SKILL_DIR}` in both the body and an `allowed-tools` rule, so `pr-review`'s scripts run without prompts from any working directory.
- **Parallel tickets:**
  - When two or more tickets have no open blockers, `implement` offers to build them at once. The user picks the tickets in one multi-select question.
  - The main session creates one worktree per ticket under `.claude/worktrees/` on a ticket branch from local HEAD. `worktree.baseRef` defaults to `fresh`, which would leave out unpushed commits.
  - It starts one background subagent per ticket. Each gets the ticket, its worktree, the agreed seams and `implement`'s steps, which run without questions because subagents can't ask them.
  - Concurrency is at most half the machine's cores, at most Claude Code's limit of 20, and never more than the tickets picked.
  - Each subagent ends with its handover on its branch. The main session integrates the tickets one at a time onto the base branch, runs the full suite after each, and runs the definition of done on the integrated candidate.
  - A failed ticket stays on its branch with its handover and is reported, and the others go on.

### Claude Code built-ins in the flow

- **Reviews scale with risk:**
  - **Features and builds:** `implement` runs Matt Pocock's `code-review` (standards and spec) and the bundled correctness review, `/review <effort> <fixed-point>..HEAD`, at the session's effort. `ultra` is never used unless the user asks, because it runs in the cloud and is paid.
  - **Bounded changes and bugs:** reviews are offered, as today.
  - **Sensitive changes:** `/security-review` is required. It needs an `origin` remote; without one, the `reviewer` agent reviews for security findings only.
  - **Large diffs:** `/simplify` is offered when the diff exceeds 400 changed lines or 15 files.
  - **User-facing changes:** the handover's "Try it" section offers `/verify`, which only the user can start, when the repo has a runnable app.
  - The build first confirms whether Claude can invoke `/review` through the Skill tool. Matt Pocock's personal `code-review` replaces the bundled `/code-review` by name, so the bundled review is reachable only as the `/review` alias. If Claude can't invoke it, the `reviewer` agent does the correctness review.
- **`foundations`** offers `/fewer-permission-prompts`, which the user runs. The README's measuring section names `/skill-doctor` and `claude plugin details`.
- `/design` and `frontend-design` for UI tickets are phase 3. Nothing about them ships in 3.3.

### The gate and the hooks

- **PreToolUse** matches `Edit|Write|MultiEdit|NotebookEdit|Bash|PowerShell|Monitor`.
  - A `Monitor` command goes through the Bash classifier; a WebSocket watch (`ws` input) is not a change.
  - Before a declaration, a `PowerShell` command is a change unless it is `Get-Content`, `Get-ChildItem`, `Select-String`, or `git status`, `git diff` or `git log`.
- **The classifier** tracks quoting inside a command substitution nested in double quotes, so a `>` inside single quotes there is not a redirect. The reproduced false positive becomes a regression test, alongside bypass cases proving that a real redirect in the same shapes is still caught.
- **Declarations:**
  - A `UserPromptExpansion` hook records a typed process skill from the expansion's command name. That covers stacked and bare-name forms.
  - UserPromptSubmit's own parse stays as a fallback.
- **The lapse hint:** when UserPromptSubmit starts a new request and the previous one had declarations, it returns `additionalContext` stating which declaration lapsed. If the message continues that work, invoking that skill again before the next change restores the declaration; new work needs its route. No other rule changes: go-ahead messages and machine notices still keep the request, and every other typed message starts a new one.
- **Scratch:** writes under the hook input's `scratchpad_dir` are scratch, alongside today's temp roots. When the field is absent, as on Claude Code before 2.1.257, today's rules apply.
- **Read-only agents:** PreToolUse refuses a project change whose `agent_type` is one of Seams' read-only agents, whatever the ledger says.
- **Stop:** the done-check asks for verification through `hookSpecificOutput.additionalContext`, which reads as hook feedback, not a hook error. It still asks once per turn and still checks `stop_hook_active`.
- **SessionStart** matches `startup|resume|clear|compact|fork`.
- **Exec form:** every hook entry uses exec form (`args`), so no path needs quoting.
- Every hook still fails open, as before.

### Housekeeping

- The version is kept in `plugin.json` only. The marketplace entry's copy is removed, because the docs say Claude Code silently uses `plugin.json`.
- The stale `__pycache__` files in the plugin are removed.
- `pr-review` no longer says subagents can't start subagents; they can nest three levels deep. Its batch notes name Claude Code's real limits: 20 concurrent subagents, and rate limits on wide fan-outs.

### Docs

- **README:**
  - how resuming works;
  - a table of surfaces showing where Seams fully loads: CLI, VS Code (a subset of skills), Desktop local. In cloud sessions it loads only when enabled on the claude.ai account, it doesn't load in Desktop WSL, and in `-p` questions come as text;
  - the settings that silently switch it off: `disableAllHooks`, `allowManagedHooksOnly`, `strictPluginOnlyCustomization` for skills, `--bare`, `--safe-mode`;
  - how to measure its cost: `claude plugin details`, `/skill-doctor`, and OpenTelemetry with `OTEL_LOG_TOOL_DETAILS=1`, since third-party plugin skill names are otherwise replaced;
  - the minimum Claude Code version.
- **CHANGELOG** gets a 3.3.0 entry.
- **The evidence doc** gets the resume and budget evidence.
- `CONTEXT.md` already gained *Quality bar*, *Progress file* and *Resume note*. ADR 0003 is written.

### Supported versions

3.3 supports Claude Code 2.1.269 or later and is tested on 2.1.281. Some features arrived after 2.1.214 and are optional; the older behavior applies without them:
- the `fork` source (2.1.214);
- `scratchpad_dir` in hook input (2.1.257);
- `omitClaudeMd` for agents (2.1.271).

## Testing Decisions

- **What counts as a good test:** a test observes behavior at a seam: a hook's output for a given event, the classifier's verdict for a command, a skill's routing in a real session. It never inspects internals. Expected values come from the docs, a reproduced incident, or a worked example, never from recomputing the code.
- **The seams agreed in the grill:**
  1. **The gate module (unit).**
     - The classifier's false-positive table: the reproduced `x="$(awk '$1>0' f)"`, input redirects, and quoted `>` in awk programs, inside and outside substitutions.
     - The bypass table: real redirects in the same shapes.
     - `Monitor` commands, `PowerShell` commands and the read-only list.
     - Refusing a read-only agent's change.
     - The `scratchpad_dir` exemption.
     - The lapse hint's content.
     - Declarations recorded from `UserPromptExpansion`.
     - All run under Python 3.9 and the current Python.
  2. **The hooks (hook suite).** The session-start output for each source (startup, resume, clear, compact, fork):
     - with no progress files, one, and four (only three shown, newest first);
     - with a stale, unparseable or planted file (skipped, or rendered as capped plain data);
     - the size caps: bootstrap at most 2,900 bytes, resume note under 1,500 characters, the whole injection well under 10,000;
     - the one-line `systemMessage`.

     Also the Stop hook's feedback form, and exec-form entries in the hook config.
  3. **The plugin guards (static test).**
     - Every SKILL.md within the byte bound.
     - The descriptions' total within its target.
     - No `model` or `effort` in any SKILL.md or agent.
     - The agents' tool lists read-only as specified.
     - The version in `plugin.json` only.
     - `claude plugin validate --strict` passing on the plugin, its skills and its agents.
  4. **Behavior (evals and the routing probes).**
     - Every existing routing and gate case keeps its score.
     - New cases:
       - A fresh session over a fixture with a progress file mid-grill continues the grill, asking the recorded open questions and not restarting.
       - A fresh session with a progress file mid-ticket continues that ticket.
       - A fresh session with an unfinished `pr-review` batch continues the batch.
       - A second message in a resumed session re-declares before editing, with no refused call.
     - Compaction is proven headless: a session is resumed with `/compact` and then continued, and each of the three flows is checked the same way.
     - Paid eval runs are asked before each run.
- **Prior art:** the gate tables in the unit suite; the hook suite and the bootstrap size check; the static plugin test; the routing harness and the `claude plugin eval` scenarios; the live-run evidence document.
- **Deliberately not tested:** routing quality beyond the scenarios; cloud, Desktop WSL and VS Code surfaces, which are documented, not tested; model quality in general.

## Out of Scope

- Phase 2:
  - grounding every claim in official docs of the exact installed version;
  - research at decision points;
  - MCP servers, Claude in Chrome and Playwright as a toolbelt.
- Phase 3: system design and diagrams, `/design` mockups for UI tickets, `frontend-design`, and tech-stack selection.
- Phase 4:
  - delivery and versioning standards: SemVer, Conventional Commits, changelogs, progressive delivery;
  - operations: SLOs, observability standards;
  - security standards: OWASP, ASVS, supply chain;
  - performance budgets.
- An Agent SDK test harness. The headless CLI and `claude plugin eval` prove resume without a new dependency.
- A forced plugin output style for the routing policy. It would override the user's own style and collide with other plugins.
- Changing Matt Pocock's own skills. They are installed per user and are not Seams'.
- Using dynamic workflows, agent teams or `/goal` inside the flow skills.
- Making hooks run natively on Windows without Git Bash. Beyond the gate's `PowerShell` handling, that is unchanged.
- Enforcing with `bashEditDiff`: it is beta, and the docs say it's for finding what to review, not for enforcing a policy.

## Further Notes

The grill's full record, with every rejected option, is `.scratch/lean-and-durable/progress.md`. The docs facts come from a complete read of the Claude Code documentation mirror fetched 2026-09-24 (276 files) and from official sources verified 2026-09-25.

### Alternatives considered

- **Progress outside the repo** (the plugin's data folder), or durable state only at phase ends: rejected. See ADR 0003.
- **A resume note for the checked-out branch's feature only:** rejected, because on the base branch with several features open it shows nothing.
- **Leaving the bootstrap's wording as it is:** rejected, because the docs warn that command-framed hook text can trip Claude's prompt-injection defenses. A forced output style was rejected too (see Out of Scope).
- **Pinning effort by skill role, or `max` everywhere:** rejected. A pin overrides the user's own level both ways, and the docs call `max` prone to overthinking.
- **A 5,000-token skill cap** (no headroom) or **a 2,500-token cap** (too many reference reads): rejected in favor of 4,000.
- **Leaving delegation to judgment:** rejected, because on Opus 5 Claude rarely delegates unless asked. **Delegating almost everything:** rejected for latency and cold starts.
- **Pre-loading slow commands:** rejected, because one failure aborts the whole skill. **No pre-loading at all:** rejected as needless round trips.
- **Every review on every change:** rejected for cost and noise. **The bundled review alone:** rejected, because it drops the spec and standards checks.
- **`/batch` for parallel tickets:** rejected, because it plans its own units and skips Seams' seams and reviews. **Strictly one ticket at a time:** rejected as slow.
- **Leaving `Monitor` and `PowerShell` ungated:** rejected as a bypass. **Making both fully strict:** rejected, because even tailing a log would need a route.
- **Letting mid-turn messages join the turn:** rejected. After an Esc interrupt the Stop hook never fires, so a new task could ride the old declaration. **Keeping today's refusal:** rejected as a needless refused call.

### Risks and failure modes

- **A reworded bootstrap routes worse:** the evals gate the change, and the old wording is one revert away.
- **A resume note that's stale or wrong:** it's a pointer. Skills re-read the real state and report mismatches, and a bad file is skipped.
- **A planted progress file in a cloned repo:** only capped, flattened fields are shown, framed as data. Its effect is no stronger than the repo's own CLAUDE.md, which Claude Code already loads.
- **A reference file never read after the split:** the first screen names each reference with a "read this when…" line, and the resume and routing evals exercise the split skills.
- **Pre-loading disabled, or a command missing:** each command can't fail, and each skill says how to get the fact another way.
- **`/review` not invocable by Claude:** the `reviewer` agent covers correctness. The build confirms which applies.
- **`/security-review` without an `origin` remote:** the `reviewer` agent reviews for security findings only.
- **Parallel tickets:**
  - Conflicts show up at the one-at-a-time integration.
  - Rate limits and machine load are bounded by the cap. A 429 is retried by Claude Code, and the docs advise fewer parallel subagents.
  - A failed ticket stays on its branch.
- **PowerShell false positives on Windows:** one declaration each. The allowlist grows only with tests.
- **Older Claude Code without newer hook fields:** each field is optional, and old behavior applies.
- **A surface that doesn't load plugins** (cloud without account enablement, Desktop WSL): documented in the README. The workflow is absent there, not half-present.

### Rollout and migration

- **What changes shape:**
  - The hook config: more matchers, two new events, exec form.
  - The plugin gains agents.
  - Skills are restructured into core and references.
  - The bootstrap's wording.
  - A new committed file per feature.
  - The marketplace entry loses its version field.
- **Existing repos:** features without a progress file get no resume note until a flow skill writes one, and nothing else changes for them.
- **Rollout:**
  1. 3.2.1 is released first through `release`, on the user's yes.
  2. Phase 1 ships as 3.3.0 through the existing marketplace.
  3. The local directory install picks it up at the next session start or `/reload-plugins`.
- **Reversal:** disabling the plugin turns everything off. Reinstalling 3.2.1 from the repository's history restores the old behavior. Progress files can be deleted without harm.

### Observability

- **The resume notice:** the user sees the one-line "resuming…" notice whenever unfinished work exists. The full note is in the transcript as hook context.
- **Refusals and lapses:** a refusal shows as the denied call and its reason. A lapse hint and the done-check's feedback appear as hook context and feedback in the transcript.
- **Hook failures:** they go to Claude Code's debug log, as before.
- **Token cost:** measured with `claude plugin details` (always-on and per skill), `/skill-doctor`, and, for users who want it, OpenTelemetry token metrics with Seams' skill names shown through `OTEL_LOG_TOOL_DETAILS=1`.
- **Evidence:** the eval reports and the headless resume runs are recorded in the evidence doc as counts.

### Release

- **Target:** the GitHub repository `gabriel-tutor/seams` (marketplace `my-workflow-agent-skills`), and this machine's local directory install, which loads the working tree in place.
- **Environments:** CI on macOS and Ubuntu is the staging check. The local install is where it first runs.
- **Sequence:**
  1. 3.2.1 goes out first: its own `release` run and its own yes.
  2. Phase 1's last ticket takes the integrated candidate through `release` as 3.3.0: the version bumped in `plugin.json`, the CHANGELOG entry, green CI, the measured budgets and eval evidence recorded, then the push on the user's yes.
