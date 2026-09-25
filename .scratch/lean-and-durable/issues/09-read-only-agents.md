# 09: Read-only agents and explicit delegation

**What to build:** Seams ships two read-only agents. Each has a turn cap and pins no model, effort or permission mode.
- **`scout`:** exploration, docs lookups and fact-finding. Its tools are Read, Glob, Grep, WebFetch and WebSearch, and it skips CLAUDE.md.
- **`reviewer`:** correctness or security review of a named diff. Its tools are Read, Glob, Grep and Bash, with no Edit, Write or NotebookEdit.

The gate refuses any project change either agent attempts. The grill, `to-spec`, `implement` and `foundations` say when to delegate and which agent to use, and start independent reads in parallel. Naming the agent matters: on Opus 5, Claude Code tells Claude not to spawn subagents unless asked.

**Blocked by:** 08 (Every skill under the bound, lighter always-on cost)

**Status:** done

- [x] Both agents pass `claude plugin validate --strict`, and their tool lists are exactly as specified. They return conclusions with file:line or URL citations, and say what they couldn't confirm.
- [x] Must not happen: a project change attempted by either agent goes through, even with a declaration in the ledger. Examples: a `reviewer` running `git commit`, or a `scout` writing through any tool.
- [x] Each skill names the agent to use and when:
  - the grill for fact-finding;
  - `to-spec` for exploring the repository;
  - `implement` for reading beyond a few files, and for reviews;
  - `foundations` for its survey.

  Independent reads start together.
- [x] Every edited skill stays within the size bound.
- [x] A new or extended eval case shows the grill's fact-finding done by `scout`, through a `tool_used` grader on `Agent`.

**How to verify:**
- `scripts/test.sh` runs the static checks and the gate's unit cases for these agent types.
- `claude plugin validate --strict plugin`.
- The eval case through `claude plugin eval`. The run is paid, so ask first.

## Comments

From ticket 08 (2026-09-25, decision 26): the agents' descriptions count toward always-on cost.
- **The static test's limit:** it holds the listing, every skill's and agent's name and description, to 2,650 characters. The listing is at 2,496, so 154 are left. `matt-pocock-workflow:scout: ` and `matt-pocock-workflow:reviewer: ` take 59 of them, which leaves about 95 for the two descriptions.
- **By `claude plugin details`:** the plugin is at about 825 tokens, and ticket 14 needs 873 or fewer (25% below 3.2.1's 1,165).
- **So keep the descriptions short.** Each skill names the agent it delegates to, so a description doesn't need to route.

Built 2026-09-26 on local `main`, not pushed. The commits:
- `af9b011`, the build. It carries the grill's firm rule and the grader's fix from the eval runs.
- `5bab189`, the review fixes: the read list (decision 30).
- The commit carrying this record.

**What shipped.**
- **The agents** (`plugin/agents/`):
  - `scout`: Read, Glob, Grep, WebFetch and WebSearch, 25 turns, `omitClaudeMd`.
  - `reviewer`: Read, Glob, Grep and Bash, with Edit, Write and NotebookEdit disallowed, 40 turns.

  Neither pins a model, effort or permission mode. Each prompt asks for conclusions with `file:line` or URL citations, and what couldn't be confirmed. The reviewer reviews by reading, along the axis its task names.
- **The gate** (`seams_gate.read_only_problem`): a call from either agent is held to a list of reads, whatever the ledger says.
  - Its shell runs only git's read subcommands, `gh`'s views and a short list of file readers, named plainly.
  - It redirects only into the temp directory or the scratchpad, never into a git directory, and its editor tools write only there.
  - Nothing it does reaches the ledger.
- **Delegation, named in each skill:**
  - the grill: fact-finding, however small the codebase;
  - `to-spec`: exploring beyond a few files;
  - `foundations`: its survey;
  - `implement`, in a standing rule before its first step: reading beyond a few files to scouts, and every review's subagents, `code-review`'s two included, to reviewers.

  Independent ones start together, in one message.
- **Sizes** (bytes): `implement` 10,252 (748 left under the bound for tickets 10 to 12), `to-spec` 6,664, the grill 5,276, `foundations` 4,742. The listing is 2,626 of 2,650 characters, about 857 tokens always on by `claude plugin details`.
- **The harness** records each Agent call's type and judges an `agents` expectation. `ScenarioFilesTest` holds each Agent grader to it, as an indicator (`arm: with-only`), since a plugin's agent cannot run without the plugin. The new case is `grill-fact-finding`.
- **Docs:** the README's gate section, workflow diagrams, layout and eval commands. `CONTEXT.md` gains **Read-only agent**, and its **Gate** entry names the refusal no declaration lifts.

**Evidence** (`docs/plugin-behavior-tests.md`, "3.3, ticket 09"):
- **The suites:** `scripts/test.sh` passes 9 of 9 on `5bab189`, on Python 3.14.6 and 3.9.6. The unit, hook and static suites pass on 3.12.13.
- **The probe** (Haiku 4.5, $0.094): a reviewer's `git commit` was refused after a `trivial` declaration. The hook input named the agents `matt-pocock-workflow:scout` and `matt-pocock-workflow:reviewer`.
- **The eval** (Opus 5.5, `--ablation none`, 3 runs):
  - the first wording started no scout in 3 of 3 runs ($0.69);
  - the firm rule started two scouts in each of 3 runs ($1.24). All six scout reports cite `file:line` and say what they couldn't confirm.

**Review of `af9b011`.** Matt Pocock's `code-review` (Standards, Spec) and a correctness and security reviewer. Each finding was checked against the code or the docs first.
- **Acted on in `5bab189`:**
  - The reviewer's shell passed any write the classifier doesn't know: `npm version`, formatters, build and test scripts, `gh pr merge`, `git diff --output`, scripts it wrote. Both the Spec and the correctness reviewer found it. The user chose the list of reads (decision 30).
  - A read-only agent's editor write to the Claude config directory passed.
  - A task's report shape could drop the reviewer's citations.
  - The README and a test comment overstated the tool lists.
  - The glossary's Gate entry didn't name the refusal no declaration lifts.
  - The static fixture didn't break every rule its comment claimed.
  - "Baseline" was used outside its glossary sense.

  A further pass found two holes in the new list, now closed: `sort --compress-program` runs a program, and a redirect into a repository's `.git` under the temp directory could plant a program for `git status`.
- **Recorded as mine:** decision 31 (the reviewer's wider axes) and decision 32 (the grill delegates however small the codebase). The Spec review flagged both.
- **Not acted on:**
  - **The grill should wait for every scout:** Matt Pocock's grilling asks the questions that don't wait on a running exploration, and interactive sessions run subagents in the background with no way to ask for the foreground.
  - **The smells** (a duplicated phrase, three list coercions, test shapes, a helper's envelope, a third inline parse): decision 12.
  - **`pr-review`'s risk reviewer:** outside this ticket, and recorded as open.

**Open.**
- `pr-review`'s risk reviewer still starts as `general-purpose`.
- The grader's follow-up allowance was not re-run.
- `implement` has 748 bytes left for tickets 10 to 12.
- The session that built this ticket had neither agent in its agent list, which was set when it started, so its own reviews ran as general-purpose agents. The eval's fresh sessions listed both.
