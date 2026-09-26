# 11: The quality bar in the definition of done; reviews scaled to risk

**What to build:**
- **The definition of done:** `implement`'s definition of done proves five things, or says why each doesn't apply: failure paths, security, performance, observability and rollback.
- **Reviews that scale with risk:**
  - Features and builds get Matt Pocock's `code-review` plus the bundled correctness review, at the session's effort.
  - Sensitive changes also get `/security-review`.
  - `/simplify` is offered on large diffs.
  - `/verify` is offered for user-facing changes.
  - The `reviewer` agent stands in when a built-in can't run.

**Blocked by:** 09 (Read-only agents and explicit delegation)

**Status:** done

- [x] The definition of done has the five new rows. Each is proven by a command's output or a check, or marked "n/a" with a one-line reason. The table stays a table, and `implement` stays within the size bound.
- [x] First, the build confirms whether Claude can invoke `/review` through the Skill tool. Matt Pocock's personal `code-review` replaces the bundled `/code-review` by name, so the bundled review may only be reachable as `/review`.
  - If Claude can, features and builds run `/review <effort> <fixed-point>..HEAD` at the session's effort.
  - If not, the `reviewer` agent does the correctness review.

  The finding is recorded in the ticket's comments.
- [x] Sensitive changes run `/security-review`. Without an `origin` remote, the `reviewer` agent reviews for security findings only.
- [x] `/simplify` is offered only when the diff exceeds 400 changed lines or 15 files. The handover's "Try it" offers `/verify` for user-facing changes when the repository has a runnable app.
- [x] Must not happen:
  - `ultra` is used without the user asking;
  - a bounded change or a bug runs the reviews instead of offering them;
  - a finding is acted on without `receiving-code-review`'s check;
  - anything outside correctness or the stated requirements is changed because a reviewer suggested it.
- [x] New eval cases:
  - a feature build shows both reviews invoked;
  - a sensitive fixture shows `/security-review`, or the fallback.

**How to verify:**
- `scripts/test.sh`.
- The eval cases through `claude plugin eval`. The run is paid, so ask first.
- One headless `implement` run on a fixture ticket, showing the definition-of-done table with the new rows.

## Comments

Built 2026-09-26 on local `main`, not pushed. The commits:
- `2438aed`, the build.
- `327759e`, the review fixes.
- `a263282`, a fix from the live runs: the harness allows a review fix's `git rm`.
- The commit carrying this record.

**The finding on `/review`** (the ticket's first criterion). Checked 2026-09-26 in the session that built this, on Claude Code 2.1.282, with Matt Pocock's personal `code-review` installed, as every Seams setup has it:
- `Skill("review")` answered `Unknown skill: review`.
- `Skill("verify")` answered that it "cannot be used with Skill tool due to disable-model-invocation. Ask the user to run /verify themselves".

The docs and the binary agree:
- The bundled review is `/code-review` with the alias `/review`, and Claude may start it itself (the docs' code-review page, line 303).
- A personal skill of the same name replaces it, and the Skill tool doesn't resolve the alias. A user-only skill would give `/verify`'s error, not "Unknown skill".

So Claude can't reach the bundled review, and the `reviewer` agent does the correctness review. `/security-review` is in the Skill tool's listing, so Claude can run it. It takes no argument, and it reviews from its merge-base with `origin/HEAD` to the working tree (`git diff --merge-base`).

**What shipped.**
- **The definition of done** has five more rows: Failure paths, Security, Performance, Observability and Rollback. A row is proven by the command run or the check made, and a Quality bar row that doesn't apply says `n/a` and why, in one line. The Security row accepts each finding fixed or left with a reason, since only correctness and requirement gaps are acted on.
- **Reviews by risk,** in `implement`'s Review step, with the detail in `references/reviews.md`, named before the first step:
  - Every build gets `code-review` and a correctness review by the `reviewer` agent.
  - A sensitive change also gets a security review, as decision 34 says: `/security-review` when `git merge-base origin/HEAD HEAD` prints the fixed point, otherwise the `reviewer` agent on the security axis.
  - A diff over 400 changed lines or 15 files gets `/simplify` offered.
  - Try it offers `/verify` for a user-facing change to a runnable app.
  - Never `ultra` unasked.
- **Findings.** Every finding goes through `receiving-code-review`, and only correctness bugs and gaps against the ticket or spec are acted on. `/simplify`'s cleanups are the user's own choice, made by their yes.
- **Routing.** `routing.md` offers the reviews on bounded changes and bugs, and requires `code-review` and a security review on sensitive changes. The grill's `Next` names those reviews for a sensitive change, and `incident` says the same. The bootstrap is unchanged (decision 35).
- **Scenarios.** Two new ones, `feature-reviews` and `sensitive-reviews` (tag `review`, 900 s), each a ticket committed on `main` with its review next.
- **The harness.**
  - It records each Agent call's task and judges the new `skills` and `tasks` expectations.
  - It keeps a subagent's own calls out of the verdict and the refusals.
  - Each run waits for its scenario's `timeout_seconds`.
  - New tests hold the graders to the expectations.
- **Docs.** The README describes the reviews, the definition of done and fifteen scenarios.
- **Sizes** (bytes):

  | File | Bytes |
  | --- | --- |
  | `implement` | 10,973 (27 left under the bound) |
  | the grill | 5,796 |
  | `incident` | 7,033 |

  Always-on cost is unchanged, since no name or description changed.

**Evidence** (`docs/plugin-behavior-tests.md`, "3.3, ticket 11"):
- **The suites:** `scripts/test.sh` passes 9 of 9, on Python 3.14.6 and 3.9.6. Each new check failed first.
- **The harness,** paid, on the user's yes. Opus 5.5 on `327759e`, three runs of each case:
  - `feature-reviews` 3 of 3;
  - `sensitive-reviews` 2 of 3 and one error. That run's review fix ran `git rm`, which the harness's settings denied after it had started all four reviewers, and `a263282` now allows it.

  Every run started "Standards review", "Spec review" and "Correctness review" reviewers, and every `sensitive-reviews` run added a "Security review". The harness stops each run at its first change, before the result event, so their cost wasn't reported.
- **One headless `implement` run** on the `feature-reviews` fixture, from its review to its handover: $1.10, 230 s, 28 turns. Its definition of done showed the new rows, each proven or `n/a` with a reason. It acted on the two correctness gaps its review found (tests that couldn't fail) and left five other findings with reasons.
- **The eval.** `claude plugin eval` can't give the review cases a shell on this Mac (its sandbox won't start while `~/.docker` holds symlinks), so the cases ran through the harness only.

**Review of `2438aed`.** Matt Pocock's `code-review` (Standards, Spec) and a correctness reviewer. The session that built this had neither Seams agent in its agent list, so they ran as general-purpose agents told to only read. The build's diff was 652 lines, so `/simplify` was offered, and the user declined it. Each finding was checked against the code or the docs first.
- **Acted on in `327759e`:**
  - the harness took a subagent's own calls as the run's;
  - the harness ignored a scenario's timeout;
  - the Security row contradicted the rule on which findings are acted on;
  - the task patterns matched their axis anywhere in any prompt;
  - the lost "or a check";
  - `/simplify`'s cleanups and `receiving-code-review`;
  - `/security-review`'s working tree;
  - "the work", a word the glossary says to avoid;
  - the setup test's line count;
  - the setups' mode;
  - "sub-agents".
- **The user's calls:**
  - decision 34, `/security-review` only when its range is this ticket;
  - decision 35, the bootstrap left as it is.
- **Recorded as mine:** decision 36, an incident's fix gets a build's reviews.
- **Not acted on:**
  - The claim that `/review` is unreachable because Claude may not start `/code-review`: that came from an older changelog entry, which the current docs supersede.
  - The duplication and naming smells: the task text built in two places, the graders list and the rule written at many sites. The scanner's test pins the task format.
  - The two handover sentences the trim dropped: "not finished until the fourth is written" still carries them.

**Open.**
- `implement` has 27 bytes left, so ticket 12's parallel flow needs a reference of its own, and perhaps the record's rules moved into one, with the tests following them there.
- The eval path of the two review cases is unrun: it needs a machine where the Bash sandbox starts.
- `/security-review` itself has not run live: every fixture here lacks an `origin/HEAD` at the fixed point.
- The harness still loads the synced Superpowers copy (`sp=15` in every run), as ticket 10 found.
