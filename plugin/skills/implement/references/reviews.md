# Reviews by risk

Read this when `implement`'s review starts, and read it again after a compaction or `/clear`. Every review reads the candidate against the fixed point, `<fixed-point>...HEAD`. None pins a model or an effort level, so each runs at the session's.

## Before the reviews

`code-review` reads `docs/agents/issue-tracker.md`; if the repository has none, offer `matt-pocock-workflow:foundations` first.

## Which reviews run

| The change | Its reviews |
| --- | --- |
| Every build `implement` makes | `code-review` (Standards, Spec) and a correctness review |
| Sensitive: auth, permissions, secrets, billing, migrations, infrastructure, CI or deploy configuration, a public API, anything destructive, or a ticket that says it is sensitive | a security review too, required |
| Large: `git diff --shortstat <fixed-point>...HEAD` shows over 400 changed lines (insertions plus deletions) or over 15 files | `/simplify` too, offered and never run unasked |

Start the reviewer agents in one message with `code-review`'s two sub-agents, each told its axis and the range, `<fixed-point>...HEAD`.

- **Correctness:** a `matt-pocock-workflow:reviewer` agent on the correctness axis. The bundled correctness review, `/review`, is out of Claude's reach: Matt Pocock's `code-review` takes its name, and the Skill tool answers "Unknown skill: review" (Claude Code 2.1.282).
- **Security:** `/security-review`, through the Skill tool, when it would review this candidate. It takes no range and diffs `origin/HEAD...HEAD`, so run it only when `git merge-base origin/HEAD HEAD` prints the fixed point. Otherwise, or when it fails to start, a `matt-pocock-workflow:reviewer` agent on the security axis of `<fixed-point>...HEAD`, for security findings only: that covers no `origin` remote, no `origin/HEAD`, and a branch further ahead of it than this work.
- **`/simplify`:** ask with AskUserQuestion, saying that it applies its cleanups itself. On a yes, point it at this work: on a branch, the branch; on the base branch, the changed files (`git diff --name-only <fixed-point>...HEAD`), since on its own it cleans up everything ahead of the upstream. Its edits are committed and re-checked like review fixes.
- **Never `ultra`** (a review in the cloud, billed) unless the user asks for one.

## Findings

Every finding, from any review, goes through `matt-pocock-workflow:receiving-code-review` before anything changes: verify it against the code first. Act only on correctness bugs and gaps against the ticket or spec. Anything else a reviewer suggests (a refactor, a style change, a feature nobody asked for) is reported with the reason it stays as it is.

These reviews run because `implement` builds features and tickets. A bounded change, or a bug fixed outside `implement`, is offered them instead (the routing reference).
