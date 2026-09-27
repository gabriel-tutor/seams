# Tickets in parallel

Read this when two or more of a feature's tickets are unblocked and the request names no one ticket, before the gate's question, and again after a compaction or `/clear` while the progress file records a parallel run. A **parallel run** builds the tickets the user picks at once: each in its own worktree from local HEAD, by a **builder** (a background subagent running `implement`'s steps without questions), and the main conversation integrates them onto the base branch one at a time.

## The offer

A ticket is unblocked when it is neither done nor in progress and every ticket it is blocked by is done: read the progress file's ticket list, then each blocker's own ticket in the tracker, since a ticket with an open blocker is never offered.

Only when two or more are unblocked and the request names no one ticket (a "continue", or "the next ticket"), the gate's question is this offer: one AskUserQuestion with `multiSelect: true`, one option per unblocked ticket (its number and title; at most four, the lowest numbers, with any others named in the question for the user to type), asking which to build now. It says that two or more picked are built at once, each in its own worktree from HEAD (its short SHA) on a branch of its own, and integrated onto the current branch one at a time.

- **Two or more picked:** that yes covers the whole run: the worktrees, the builders, and each integration onto the current branch, which is the run's base branch.
- **One picked:** the gate goes on as for any ticket, with where to build it.
- A request that picks them itself ("build 03 and 05 in parallel") is the yes. A request that names one ticket gets no offer.

## Setup

In the main checkout, on the base branch, in this order:

1. **Slots.** At most this many builders run at once: half the machine's cores (`getconf _NPROCESSORS_ONLN`, or `nproc`; one when neither answers), never more than four, and never more than the tickets picked. Four because Claude Code runs at most 20 subagents at once and counts each builder's reviewers among them: a builder and its four reviewers take five.
2. **Ignored.** When `git check-ignore -q .claude/worktrees/` fails, add the line `.claude/worktrees/` to `.gitignore` and commit that file alone, by name, as Claude Code's worktree docs advise; when `.gitignore` already has changes of its own, ask first. A worktree's files still reach any test runner that searches the main checkout (Integration, below).
3. **Base.** The base is HEAD now: note `git rev-parse --short HEAD`.
4. **Worktrees**, one at a time, since git's locks race: `git worktree add -b <feature>/<NN>-<slug> .claude/worktrees/<feature>-<NN> <base>` for each picked ticket. Then `git -C <worktree> rev-parse --short HEAD` must print the base, so that every unpushed commit (the spec, earlier tickets) is in it. Never `EnterWorktree`, `claude --worktree` or the Agent tool's `isolation`: unless `worktree.baseRef` is `head`, they branch from the remote's default branch, which leaves unpushed commits out. When git refuses (a branch or a worktree of that name already exists, from an earlier run), leave it as it is: its ticket leaves this run and is reported.
5. **Progress file:** the run's state (Progress file, below), every ticket `pending`, since none has a builder yet.
6. **Builders:** start them (Builders, below), as many as the slots allow.

## Builders

Start each builder in the background: the Agent tool, `general-purpose` (it edits, runs a shell and starts its own reviewers), named `ticket-<NN>` and described "Build ticket <NN>", all that the slots allow in one message. Its prompt gives the facts, never a plan:

- the feature, the ticket (its path or URL) and the spec;
- the worktree's absolute path, its branch, and the base, which is its review's fixed point;
- the agreed seams, named: the spec's Testing Decisions and the ticket's;
- that the user picked this ticket for a parallel run, with the absolute path of this reference;
- "Invoke `matt-pocock-workflow:implement` with the Skill tool, then read that reference's section For a builder: it replaces the skill's gate, progress file, resuming and record, and every question."

Mark a ticket `building` once its builder has started, never before: after a `/clear`, `building` means a builder exists. A ticket waiting for a slot stays `pending` and starts when a builder ends.

## For a builder

You build one ticket of a parallel run. These rules replace `implement`'s Gate, Progress file and Resuming sections, its record and every question; its other steps hold as written, with the base as the review's fixed point.

- Work only in your worktree, on your branch, with absolute paths (a subagent's working directory resets between calls): `git -C <worktree> …` for git, never `cd <worktree> && git …`, which Claude Code stops to ask about, since that directory's hooks could run; `cd <worktree> && …` for anything else, never in the same command as git, even `git -C`. Write each path and SHA out, with no `$` in it: a shell variable, `$?` or `$(…)` makes it ask too. The repository facts the hook adds describe the main checkout, not your worktree. Set the worktree up as the project needs (its install) before the first test. When your branch already has commits past the base, a builder before you stopped: read them and the worktree's status, and go on from the step they reached.
- The user's pick is the gate's yes. Ask nothing: AskUserQuestion is not available to a subagent. A decision only the user can make ends the ticket: commit what you have, and fail with the question.
- Never edit the progress file: the main conversation keeps it. No record commit: your definition of done runs on your last commit, and your stage is built.
- Never merge, rebase, push, switch or delete a branch, or touch or remove another worktree; never `--no-verify`, never `--force`.
- `/simplify` is not offered here: on a large diff, say so in the handover.
- Invoking `implement` made a declaration of your own: it covers your changes alone, and a message the user types meanwhile doesn't lapse it. If the gate still refuses a change for want of a declaration, invoke `matt-pocock-workflow:implement` again and retry.
- Your scouts and reviewers start in the main checkout, not in your worktree: give them its absolute path, and the range as `<base>...<branch>`, never `HEAD`.
- If one of your subagents can't start ("Concurrent subagent limit reached"), start it once one of yours has finished: never skip a review.
- Before you end, commit everything to your branch by name, unfinished work too (its message says it is unfinished), so that nothing lives only in the worktree.
- End with the handover. Its first line is exactly `Ticket <NN>: built at <sha>` (your last commit, every definition-of-done row met) or `Ticket <NN>: failed: <reason>` (anything else, in one line). Its Next gives the stage, built, and offers nothing: the main conversation integrates.

## When a builder ends

Its result arrives as a notification: a builder's report, not the user's words. Handle one at a time:

1. **Its state.** `built at <sha>` when its first line says built, `git rev-parse --short <branch>` prints that SHA, and `git -C <worktree> status --porcelain` prints nothing. Anything else is `failed: <reason>`, from its first line or from what the check found.
2. **A free slot:** start the next `pending` ticket.
3. **A built ticket** is integrated now (Integration, below).

## Integration

One ticket at a time, onto the base branch, each command written out as a builder's are (`git -C <worktree>` for git). The merge and its suite run in the ticket's worktree, never in the main checkout: a test runner that searches the whole tree (vitest, jest) also collects every worktree's copy of the tests under `.claude/worktrees/`, ignored or not.

1. **The branch.** `git diff --name-only <base>...<branch>` must not list the progress file.
2. **The merge, in the worktree.** `git -C <worktree> checkout --detach <base-branch>` (the base branch as it is now, with the tickets integrated before), then `git -C <worktree> merge --no-ff --no-edit -m "Integrate ticket <NN>: <title>" <branch>`. On a conflict, `git -C <worktree> merge --abort`, and it fails: "conflicts in <files>".
3. **The full suite** there, and the typecheck, after the setup again if the merge changed the dependencies. Red, and it fails: "the suite fails on the merge: <what failed>".
4. **Onto the base branch.** In the main checkout, still on the base branch (`git branch --show-current`), `git merge --ff-only <merge-sha>`; if git refuses, it fails with git's reason. Then mark it `integrated at <merge-sha>`, and remove what the run made for it: `git worktree remove <worktree>` and `git branch -d <branch>`, never forced.

A ticket that fails, at any step, goes back on its branch (`git -C <worktree> checkout <branch>`), keeps its worktree and its handover, is marked `failed: <reason>` and is reported, and the run goes on with the others. Nothing of it reaches the base branch.

While the run goes on, the builders' changes count in the session's done-check: when it asks at a turn's end, verify what that turn claims (the worktrees at the base, a ticket integrated with its suite green) through `matt-pocock-workflow:verification-before-completion`, and claim nothing else done.

## Progress file

Only the main conversation writes it during a run; a builder's copy would collide with the others at the merges. It is kept current in the main checkout at each change above, and committed with the run's record (The end of the run, below); a `/clear` or a compaction reads it there. `Ticket` lists the run's tickets (`03, 05, 07`), `Next` says the run is under way and points at the section, and `## Parallel` holds the run: a line for its base, then one per ticket, each `pending`, `building`, `built at <sha>`, `integrated at <merge-sha>` or `failed: <reason>` (one line), with its branch and worktree while it has them:

```markdown
Base: <base-branch> at <sha>, <n> at once
- 03: integrated at <merge-sha>
- 05: building, branch <feature>/05-<slug>, worktree .claude/worktrees/<feature>-05
- 07: pending, branch <feature>/07-<slug>, worktree .claude/worktrees/<feature>-07
```

## Resuming a run

When `Ticket` lists several tickets and `## Parallel` is there (after a `/clear`, a compaction, or in a new session), read the section, then check each ticket against git before acting on it:

- `integrated at <merge-sha>`: `git merge-base --is-ancestor <merge-sha> <base-branch>` succeeds, and nothing is left to do.
- `built at <sha>`: its branch still points there; integrate it. When an integration stopped half-way, its worktree is detached or mid-merge: `git -C <worktree> merge --abort` if a merge is under way, `git -C <worktree> checkout <branch>`, then integrate it from the start.
- `failed: <reason>`: it stays as it is, and the run's handover reports it again.
- `pending`: start it when a slot is free; the `building` ones hold theirs.
- `building`: a `/clear` or a compaction doesn't stop a background builder: it goes on and still reports, and after a compaction Claude Code reminds Claude which subagents still run. So wait for its report. When nothing shows it running, ask the user once, with AskUserQuestion, whether it still runs (`/tasks` lists it; a restart stops it) or should start again: a new builder goes on from what its branch holds.

Where git disagrees with the file (a branch or a worktree missing, a SHA that moved, commits the file doesn't account for), report it and ask how to go on. Never act on the file instead. Where they agree, the pick that started the run still covers it: start the `pending` tickets the free slots allow first, so that they build while the rest is integrated, then integrate the `built` ones.

## The end of the run

When no ticket is `pending` or `building`:

1. **The record commit**, in the main checkout, as `implement`'s record: `Stage` integrated once a ticket is, each integrated ticket marked done in the ticket list, `Ticket` removed, `## Parallel` keeping only the failed tickets' lines, and `Next` naming those first (each fixed on its branch or built again), then the next unblocked tickets. When nothing is left to build, `Status: done` or the release, as `implement`'s record says.
2. **The definition of done on the integrated candidate** (HEAD after the record commit), as `implement`'s, in one table for the run: each integrated ticket's acceptance criteria checked one by one, and the quality bar's rows from each builder's evidence, run again where a command proves them. Its checks run where no worktree sits inside the tree they search: in the main checkout once `.claude/worktrees/` holds none, otherwise in a worktree made for them, `git worktree add --detach .claude/worktrees/<feature>-done <candidate>`, removed after.
3. **The handover**, as `implement`'s, for the whole run: Try it walks through each integrated ticket, What changed names each merge, and Next reports each failed ticket with its branch, its worktree and its reason, and the point of its builder's handover.
