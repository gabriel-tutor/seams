# Once a design is confirmed, the flow runs on to the real gates

ADR 0002 kept Seams' own `to-spec`, `to-tickets` and `implement` "gated by a question before they start and before they publish", and the routing added that each step of the flow asks before it starts. On a confirmed design those opening questions only ever got a yes: a feature went from grill to release through half a dozen of them, each one a round trip that decided nothing the confirmation had not already decided.

We decided, for 4.0.0, that the user's confirmation of a design (the grill's last question, or a spec the user calls agreed) starts a continuous flow: spec, tickets, build, review and release each start the next without an opening question, and still write the progress file at every step. The flow stops only at the real gates, each asked with a question that names it when it comes, and no earlier general yes covers one: the user's decisions, integrating a branch, a push, a deploy, a publish, anything destructive, and a paid run. The question before publishing a spec or tickets stays; the question before starting goes. Where `implement` builds is asked with the grill's confirmation (the user's choice, 2026-10-03) and recorded as a branch by its name or a new worktree, so a later step builds where the user said, not on whatever branch is current, without asking again.

We chose this over keeping a question at every step, which taxed every feature for no decision, and over a flow that also runs through the gates, which would let a push, a deploy or a paid run happen on an old yes.

## Consequences

- After a `/clear` or in a new session, a confirmation recorded in a committed progress file counts as the user's, so a "continue" on the resume note goes on without a question, even when someone else wrote that file (a clone, a teammate's push). We accept it (the user's choice, 2026-10-03): `implement`'s Resuming already trusts the file the same way, the "continue" answers a resume note that names the step, and every real gate still asks.
- A limit the user sets ("just the spec for now"), a ticket with an unmet row in its definition of done, or a handover that says to `/clear` stops the flow; only the user restarts it.
- Reversing it means restoring the opening questions in the three skills and the routing's "each step asks before it starts", which the tests of 3.4.0 describe.
