---
name: using-matt-pocock-skills
description: Use when starting any conversation - how development work here is routed to Matt Pocock's skills
---

Development work in this project starts with the skill its row below names, invoked with the Skill tool before any read, command or edit; a 1% chance is enough. Between two rows the lower applies; mid-task complexity moves down, never up. * marks this plugin's skills (`seams:<name>`); bare names are Matt Pocock's. Subagents skip this routing.

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

**Enforced.** A hook refuses project changes until one of these skills routes the work, and refuses to end a turn that changed the project without `verification-before-completion`*, due before any claim of done, fixed or passing. A branch ends with `finishing-a-development-branch`*; on the base branch, work ends at the commit.

**Quality bar.** What ships meets a definition of done covering how it fails, is attacked, performs, is observed, is documented and is rolled back, each item proven; nothing is added that nobody asked for.

**Rules.**
1. Questions use AskUserQuestion, recommended answer first; seams the grill settled are never asked again.
2. Third-party code follows its official docs for the version in use, cited.
3. Flow: once the user confirms a design, later steps start unasked, stopping only for the user's decisions, integrating a branch, push, deploy, publish, anything destructive or paid.
4. Grill → spec → tickets share one context. Phase boundaries, on-ramps, Superpowers: `${CLAUDE_PLUGIN_ROOT}/skills/using-matt-pocock-skills/references/routing.md`; shared rules, which a bug fix reads too: `rules.md` beside it; code: `simplicity-ladder.md`.
