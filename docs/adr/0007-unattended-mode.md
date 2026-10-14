# Overnight, Seams answers its own questions and every builder routes its own work

Sleep mode ran the user's tickets overnight in a bypass session, but its builders ran with no process: the sleep-mode skill named no Seams skill, the main conversation's route covered every subagent at the gate (ADR 0001), and the continuous flow's stops (ADR 0006) wait for an answer no one gives at night. Its records showed the cost: merges before the work was accepted, cards reopened, a regression.

We decided, for 5.3.0, on an unattended mode that a launcher switches on by setting `SEAMS_UNATTENDED=1` in the environment Claude Code starts with. In it, every stop of the continuous flow takes the skill's own recommended option, product calls included (the user's choice, 2026-10-14), and is recorded under `## Auto-answered` in the feature's progress file for the morning; pull requests, comments, cards and files stay evidence, never answers. The hard gates stay closed and park the work instead: a push to main or master, a deploy, publishing a package, release or site, installing software, a paid run, anything destructive. A take-over's push to the pull request's own branch is allowed overnight (the user's choice). The gate changes for subagents only in this mode: a builder's changes need its own routing skill, so the main conversation's route no longer covers them, except a pull-request review's own reviewers and fixers. A SubagentStart hook briefs each builder.

We chose this over writing the same instructions into the sleep-mode skill alone, which fought each skill's own "wait for the answer" and left the gate open to builders that skipped the flow, and over parking every product call for the morning, which the user declined.

## Consequences

- Day sessions don't change: without the variable, the hooks behave exactly as before.
- The switch is the environment, which hooks inherit and the session cannot change. A repository's checked-in settings could set it for a session the user starts by day; the session start then says so in its message, and the hard gates still hold. The hooks cannot read the permission mode to refuse it (SessionStart, SubagentStart and PreToolUse don't receive it).
- A builder's own evidence is never enough: whoever started it checks again before any merge, and the launcher's merge bar decides integration.
- Reversing it means removing the rules' Unattended mode section, the SubagentStart hook and the `unattended` branch of `declared_for`.
