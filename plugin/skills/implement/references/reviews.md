# Reviews by risk

Read this when `implement`'s review starts, and read it again after a compaction or `/clear`. Every review reads the candidate against the fixed point, `<fixed-point>...HEAD`. None pins a model or an effort level, so each runs at the session's.

## Before the reviews

`code-review` reads `docs/agents/issue-tracker.md`; if the repository has none, offer `matt-pocock-workflow:foundations` first.

## Which reviews run

Which reviews run is the change's row (shared rules: Process by size and risk), and a build through `implement` is at least a feature. Start the reviewer agents in one message with `code-review`'s two subagents, each named by its axis in its description ("Correctness review", "Security review") and told the range, `<fixed-point>...HEAD`.

- **Correctness:** a `matt-pocock-workflow:reviewer` agent on the correctness axis. The bundled correctness review, `/review`, is out of Claude's reach: Matt Pocock's `code-review` takes its name, and the Skill tool answers "Unknown skill: review" (Claude Code 2.1.282).
- **Security:** `/security-review`, through the Skill tool, when its range is this candidate's. It takes no range: it reviews from its merge-base with `origin/HEAD` to the working tree, uncommitted files included, so run it only when `git merge-base origin/HEAD HEAD` prints the fixed point. Otherwise, or when it fails to start, a `matt-pocock-workflow:reviewer` agent on the security axis of `<fixed-point>...HEAD`, for security findings only: that covers no `origin` remote, no `origin/HEAD`, and a merge-base older than the fixed point, as on a base branch ahead of its upstream.
- **`/simplify`:** ask with AskUserQuestion, saying that it applies its cleanups itself. On a yes, point it at this candidate's changes: on a branch, the branch; on the base branch, the changed files (`git diff --name-only <fixed-point>...HEAD`), since on its own it cleans up everything ahead of the upstream. Its cleanups are the user's choice, made by that yes, so they skip `receiving-code-review`'s check; they are committed and re-checked like review fixes.
- **Never `ultra`** (a review in the cloud, billed) unless the user asks for one.

## Findings

Every finding, from any review, goes through `matt-pocock-workflow:receiving-code-review` before anything changes: verify it against the code first. Act only on correctness bugs and gaps against the ticket or spec. Anything else a reviewer suggests (a refactor, a style change, a feature nobody asked for, hardening the ticket didn't ask for) is reported with the reason it stays as it is, which is what the definition of done's Security row means by a finding left with a reason.
