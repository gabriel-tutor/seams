---
name: using-matt-pocock-skills
description: Use when starting any conversation - how development work here is routed to Matt Pocock's skills
---

Development work in this project starts with the skill its row below names, invoked with the Skill tool before any read, command or edit; a 1% chance is enough. Between two rows the lower applies; mid-task complexity moves down, never up. * marks this plugin's skills (`matt-pocock-workflow:<name>`); bare names are Matt Pocock's. Subagents skip this routing.

| Request | First move |
| --- | --- |
| Trivial: copy, typo, comment, unobservable rename | `trivial`* |
| Broken, failing, throwing, slow | `diagnosing-bugs`, even when the fix looks obvious |
| Bounded change to existing code | `grill`*, `tdd` |
| New behavior in one session | `grill`* + `domain-modeling`, then `implement`* |
| Several sessions, or a new app | `grill`*, `to-spec`*, `to-tickets`*, `implement`* per ticket; a new app's ticket 01 is the walking skeleton |
| Sensitive, any size: auth, permissions, secrets, billing, migrations, infra, CI or deploy config, public API, anything destructive | its size row's move, `grill`* on the security and failure axes first, `code-review` required |
| Down or degraded for users now | `incident`* |
| Ship, deploy, release, publish | `release`* |

**Red flags** that a skill is due now: "it's a quick fix", "the requirements are clear", "let me read the code first".

**Enforced.** A hook refuses project changes until one of these skills is invoked for the request, and refuses to end a turn that changed the project without `verification-before-completion`*, due before any claim of done, fixed or passing. A branch ends with `finishing-a-development-branch`*; on the base branch, work ends at the commit.

**Quality bar.** What ships meets a definition of done covering how it fails, is attacked, performs, is observed, is documented and is rolled back, each item proven; nothing is added that nobody asked for.

**Rules.**
1. Questions use AskUserQuestion, recommended answer first.
2. Seams are settled in the grill; `tdd` and `to-spec` do not ask again.
3. `code-review` runs on features and builds, is offered on bounded changes and bugs.
4. Flow: spec → `to-tickets`*, tickets → `implement`*; each step asks before it starts; a yes covering later steps is not asked again; deploy and publish always ask.
5. Grill → spec → tickets share one context. Phase boundaries, durable state, on-ramps, Superpowers overlaps: `${CLAUDE_PLUGIN_ROOT}/skills/using-matt-pocock-skills/references/routing.md`
