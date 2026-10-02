# A route lasts until another replaces it, and process is proportional to the change

ADR 0001 made the workflow enforced: a hook refuses any change to the project until a process skill has been invoked for the current request. "Current request" meant every typed message: a reply that was not a short go-ahead lapsed the declaration, so the next change was refused until the skill was invoked again. On a long grill or build that was one more Skill call, and the skill's body read again, after almost every answer the user typed. Alongside it, every skill ran its full process whatever the change: scouts "however small the codebase", two reviewers on every build, a full done table for a typo.

We decided, for 4.0.0, that a declaration holds until another process skill is invoked or the session is cleared, through typed replies and commits; and that scouts, reviewers and question rounds scale with the change's size and risk, a one-line fix getting one check and a feature or anything sensitive the full set. The gate still refuses work no skill has routed, and the done-check still asks for verification before a turn that changed the project ends.

We chose this over keeping the old lapse, which taxed every answer, and over making the gate advisory, which would give up the enforcement ADR 0001 exists for. The proportional rule keeps a feature's process exactly as it was; it stops a typo from paying a feature's price.

## Consequences

- An unrelated request typed in the middle of a task rides on the current route instead of being refused until it is routed. The bootstrap's routing still tells Claude to route new work; the gate now guards against no route at all, not against a stale one.
- What counts as a small change is judged by the skill from the bootstrap's table (size and risk), so a wrong judgement errs toward less process; anything in the sensitive list always gets the full set.
- Reversing it means restoring the per-request lapse in the gate and the fixed steps in the skills, which the tests of 3.4.0 describe.
