# Shared rules

The rules the Seams skills share, each written once, here. A skill names the section a step needs, "(shared rules: Evidence)": read this file then, and again after a compaction or `/clear`. Where `using-git-worktrees` or `verification-before-completion`, copied from Superpowers unchanged, says otherwise, the rule here holds. `pr-review` takes only the effort rule from here: its steps and checks are its own, whatever a pull request's size.

## Effort

Every step, gate and check runs at every effort level. At `low`, a skill skips only the extra its Effort line names, and nothing when it names none. Effort never sets how much process a change gets: its size and risk do (Process by size and risk, below).

## Repository facts

As `implement`, the grill or `release` starts, the Seams hook adds the branch, the short HEAD, the first lines of the status and the progress files. They are a snapshot: once git may have moved (a commit, a checkout, a new worktree, a resumed session), run git again, and look up yourself any fact the hook did not give.

## Progress file

Its format, who writes what in it, and its rules (what never goes in it, `Updated` at each step, a pointer and never the truth) are in `progress-file.md` beside this file: read it before a skill's first write. A skill keeps it at its own step and commits it by name with the work it describes; the continuous flow skips questions, never this record.

## Sensitive changes

A change is sensitive, at any size, when it touches auth, permissions, secrets, billing, migrations, infrastructure, CI or deploy configuration, a public API, or anything destructive, or when its ticket says it is. This is checked first, before the size: a sensitive change is never trivial, however few its lines, and the Sensitive row below adds to whatever its size row gives.

## Process by size and risk

How much process a change gets: its row, picked as the bootstrap picks a route, the sensitive list first. A builder's ticket is a feature.

| The change | Scouts | Questions | Reviews | Checks |
| --- | --- | --- | --- | --- |
| Trivial: no effect on behavior, data shape or security | none | none: `trivial`'s test | none | the narrowest check that proves it |
| One-line fix: a bug or a bounded change confined to one line or expression | none | only the seam, when no test covers it | none | one: the test at the seam, red then green |
| Bug or bounded change to existing code | only for a fact the conversation lacks | a few rounds: interfaces and seams, failure modes, testing | offered: `code-review` and a correctness review | the tests at the seam and the typecheck as you go, the full suite once at the end |
| Feature: new behavior, a ticket, any build through `implement` | one per independent question that needs facts the conversation lacks | the full grill: every lens axis that applies | both run: `code-review` and a correctness review | `implement`'s definition of done |
| Several sessions, or a new app | as a feature, per area | every lens axis, into the spec | as a feature, per ticket | as a feature, per ticket, then `release` |
| Sensitive, any size | its size row's | the security and failure axes first, then its size row's | `code-review`, a correctness review and the security review, all required, never only offered | its size row's, then `verification-before-completion`, always |
| Large: over 400 changed lines (insertions plus deletions) or 15 files, by `git diff --shortstat <fixed-point>...HEAD` | | | `/simplify` too, offered and never run unasked | |

- **Scouts** are `matt-pocock-workflow:scout` agents, started only when a question needs facts the conversation lacks: a fact already in view needs none, and neither does a file or two you read yourself. Beyond a few files, start one per independent question, all in one message, and keep their conclusions rather than the files.
- **Reviews** run as `matt-pocock-workflow:reviewer` agents, `code-review`'s two subagents included; how each runs is in `implement`'s `references/reviews.md`. Offered reviews are one question at the end, recommended answer first.
- **Every row** ends with `verification-before-completion`, which the done-check asks for, on the evidence its row names.

## Stages

The furthest point a piece of work has evidence for, one of six, which every handover names: *designed* (the design confirmed), *built* (the candidate committed on a branch), *integrated* (on the base branch), *release-ready* (every readiness row of `release` ready), *deployed* (`release` verified the exact candidate running in the named environment), *operated* (monitoring, an alert owner and a runbook exist for it). Work is never "done" without its stage, and never *deployed* before `release` verified it. A progress file says `designing` until the design is confirmed.

## Evidence

Evidence belongs to a candidate: the commit it ran on, with a clean tree. Evidence gathered in this conversation on an unchanged candidate (the same `git rev-parse HEAD` and an empty `git status --short`, both shown when it ran and checked again now) is reused, not re-run: two skills asking for the suite share one run, `finishing-a-development-branch`'s first step and `release`'s readiness reuse what `implement`'s definition of done showed for that SHA, and the claim shows that evidence again with its command, its output and the SHA. That is what `verification-before-completion`'s fresh evidence means here: evidence from this candidate. Any change (an edit, a commit, a merge) makes a new candidate: in a review-fix loop only the checks the fix affects re-run, and the definition of done then runs the full suite once on the final candidate.

## Worktrees

A worktree starts from local HEAD, so that every unpushed commit (the spec, earlier tickets) is in it: `git worktree add -b <branch> <path> HEAD`. A native tool (`EnterWorktree`, `claude --worktree`, the Agent tool's `isolation`) is used only when the settings set `worktree.baseRef` to `head`: by default, `fresh`, it branches from the remote's default branch and leaves those commits out (code.claude.com/docs/en/worktrees, "Choose the base branch"). This rule holds over `using-git-worktrees`' step 1a; its consent, directory, ignore check, setup and baseline stand. A parallel run makes each of its worktrees with git at its setup and starts its builders without `isolation` (`implement`'s `references/parallel.md`).

## Official docs

Before writing or reviewing code that uses a third-party library, framework, platform, CLI or API, check its official docs for the version in use (the lockfile, the manifest or its `--version` says which): the vendor's documentation, or a docs server such as Context7 when one is installed, through a scout when it takes more than a lookup or two. Cite what decided something, with the URL and the version, where the decision is written: the spec, a finding, the handover. Repo-internal logic needs no lookup. What the docs don't settle is reported as unconfirmed, never guessed.

## The continuous flow

Once the user confirms a design (the grill's last question, or a spec the user calls agreed), the flow runs on: each flow skill goes on to the next step its row names without offering it, and `to-spec`, `to-tickets` and `implement` start without an opening question. The flow reached a step when this conversation or the progress file shows the design confirmed and names that step next; a "continue" on it is the flow going on. Asked directly by the user, a skill starts at once, as before. The flow skips questions, never the record: each step still writes the progress file and commits it, so the file and the handovers show everything the flow did.

It stops only at the real gates:

- **The user's decisions:** the grill's questions, the seams when none were agreed, where to build when nothing settled it, the tickets' breakdown, the parallel offer, the readiness rows to close.
- **Integrating a branch:** `finishing-a-development-branch`'s menu (merge locally, a pull request, or keep), and a discard only when the user asks for one in so many words.
- **A push, a deploy, a publish:** the spec's and the tickets' publish, the push behind a pull request, and `release`'s questions: its opening one before readiness, whose rows can build, bill or reach a host, then each deploy's.
- **Anything destructive:** discarding work, a force, deleting data, a branch or files that exist nowhere else.
- **A paid run:** a cloud review (`ultra`), a billed eval or service.

Each is asked with a question that names it, when it comes; an earlier general yes ("go all the way") covers none of them. A limit the user set ("just the spec for now") stops the flow there, and so does a ticket with an unmet row in its definition of done. So does a handover that says to `/clear` before the next step, since only the user can type `/clear`: the resume note then brings the step back, and a "continue" goes on.
