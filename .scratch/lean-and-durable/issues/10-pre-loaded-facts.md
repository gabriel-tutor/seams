# 10: Pre-loaded facts

**What to build:** `implement`, the grill and `release` start with the facts they always look up already in hand:
- the branch;
- the short HEAD;
- the first lines of `git status --short`;
- the list of progress files.

These arrive through `` !`cmd` `` lines that can't fail and are pre-approved. When shell injection is disabled, each skill still works and says how to get the facts another way.

**Blocked by:** 08 (Every skill under the bound, lighter always-on cost)

**Status:** done

The criteria below were written for `` !`cmd` `` lines. Decision 33 replaced that mechanism while the ticket was built, and the Comments restate each criterion for it, as met.

- [ ] Only fixed, read-only commands are injected. Each is written so it can't fail, and each is pre-approved in the skill's `allowed-tools`.
- [ ] Must not happen:
  - a user argument appears inside an injected command;
  - an injected command aborts the skill, for example because the directory isn't a git repository, there are no progress files, or `disableSkillShellExecution` is on.
- [ ] The static test checks every injected command against the read-only list and the never-fail rule.
- [ ] A headless run of each of the three skills shows the facts in its first message and no permission abort. With `disableSkillShellExecution: true`, each skill still completes.
- [ ] Every edited skill stays within the size bound.

**How to verify:**
- `scripts/test.sh`.
- Headless runs of each skill in a fixture copy, first as is and then with `--settings '{"disableSkillShellExecution": true}'`.

## Comments

Built 2026-09-26 on local `main`, not pushed. The commits:
- `93fd081`, the build as the ticket says: `` !`cmd` `` lines in the three skills, pre-approved, with a static guard.
- `f74fe84`, the first review's fixes: the facts move into the Seams hooks (decision 33, the user's choice).
- `a9d1d03`, the second review's fixes.
- The commit carrying this record.

**Why the mechanism changed.** The first review found two problems, and probes confirmed both:
- **A session without the Bash tool can't load the skills.** A skill's injected commands run through the Bash tool, so in such a session the skill doesn't load at all. `claude plugin eval` gives that session to every case not granted Bash, and `--restricted` and a Bash deny rule do the same. A probe on 2.1.282 with `--tools "Read,Glob,Grep,Skill"` got "Permission to use Bash has been denied", and the model was never called.
- **Re-invocation got expensive.** The injected output changes as HEAD and the status change, so re-invoking a skill after an edit appended the whole skill again, against decision 15.

The user chose the hooks (decision 33). A hook fails open, and the skill's text stays the same.

**The criteria, as decision 33 restates them.**
- [x] **Nothing is injected.** No SKILL.md holds a `` !`cmd` `` line or a fenced block opened with `!`, which the static guard checks. The facts come from fixed, read-only git calls in `plugin/hooks/seams_facts.py`. Each call gets 3 s in its own process group, takes no optional lock, never prompts, runs in the C locale and fails open.
- [x] **No user argument reaches git, and nothing about the facts can stop a skill.** The hooks match the skill's name against a fixed set and never read `command_args`. Section 15 of the hook suite and the runs below cover each case that could:
  - not a repository, no progress files, `disableSkillShellExecution`, or a session without Bash;
  - git refusing the repository, failing its status, missing, hanging, or leaving a child that holds its output;
  - a broken facts module.
- [x] **The tests cover both mechanisms' risks.**
  - The static test fails any SKILL.md that injects a shell command, in each form Claude Code runs, and each form has a fixture.
  - The hook suite checks the facts, their caps, their failure paths, and that the hooks give them to exactly the skills that name them.
- [x] **Headless runs.** Each of the three skills gets the facts before its first answer, with no abort. Without the Bash tool and with `disableSkillShellExecution: true`, each still completes.
- [x] **Every edited skill stays within the size bound:** `implement` 10,612 bytes, the grill 5,595, `release` 9,738.

**What shipped.**
- **The facts.** As `implement`, the grill or `release` starts, context framed as data carries:
  - the branch;
  - the short HEAD;
  - the first ten lines of `git status --porcelain` (with `core.quotePath`, paths from the root);
  - the progress files, last modified first, ten at most.

  The Skill hook adds them for Claude's invocations, and the prompt-expansion hook for typed ones. A name holding `<` or `>` is not shown, since git accepts `</system-reminder>` as a branch name. Every line is capped at 200 characters. A progress file is left out and counted when it is:
  - a symlink out of the repository;
  - a FIFO;
  - a path that isn't plain text or doesn't fit on a line.
- **The hooks.** Both record declarations first, as before. A broken facts module costs only the facts, and both entries carry a 20 s timeout.
- **The skills.** Each names the repository facts and calls them a snapshot, to re-read once git may have moved. Each says to look up any fact the hook didn't give.
  - `implement`'s Gate and Resuming and the grill's Resuming take the facts.
  - A new worktree notes its own branch and HEAD.
  - `release` still reads its exact commit with `git rev-parse HEAD`.
- **Docs:**
  - the README's senior-engineer layer, test list and layout;
  - `CONTEXT.md` gains **Repository facts**;
  - the spec's pre-loading lines, test seams, risks and alternatives;
  - decisions 11 and 33.

**Evidence** (`docs/plugin-behavior-tests.md`, "3.3, ticket 10"):
- **The suites:** `scripts/test.sh` passes 9 of 9 on `a9d1d03`, on Python 3.14.6 and 3.9.6. Each new check failed first:
  - the no-injection guard, on `93fd081`'s skills;
  - the facts cases, before the module existed;
  - the escaping child and the broken module, against `f74fe84`'s hooks: 20 s and a lost declaration.
- **The probes,** Haiku 4.5, $0.14 in all. They measured:
  - how `allowed-tools` rules match;
  - `true` as a read-only command;
  - a rule holding parentheses;
  - the "(Bash completed with no output)" rendering;
  - the abort without Bash.
- **The runs:**
  - on `93fd081`: six Haiku runs, $0.46;
  - on `a9d1d03`: six Haiku runs, $1.14, and one `claude plugin eval` case, $0.04.

**Reviews.** Matt Pocock's `code-review` (Standards and Spec) and a correctness and security reviewer ran twice: on `93fd081` and on `f74fe84`. Every finding was checked against the code or the docs first.
- **The first round:**
  - the abort without Bash, blocking, confirmed by a probe;
  - the cost of a re-invocation (decision 15);
  - "an empty line means none", which hid git's failures;
  - the uncapped list;
  - the steps still looking up the facts.

  The user chose the hooks.
- **The second round:**
  - the unbounded wait after a kill;
  - the import that could lose a declaration;
  - tags in names;
  - the user's status config;
  - the progress files' refusals;
  - the stale snapshot in the worktree and release steps;
  - a ledger check that couldn't fail.

  All acted on in `a9d1d03`.
- **Not acted on,** per decision 12: the naming and duplication smells (the test helpers, `PLUGIN_PREFIX` written twice, the `slash_command` test), and a re-run of ticket 09's scout case.
- The session that built this had neither Seams agent in its agent list, so its reviews ran as general-purpose agents told to only read.

**Open.**
- The resume-grill eval case scored 0.8 on Haiku, because Haiku answered without invoking the grill, so the eval path's skill load has not been seen live. The runs without Bash show the same tool set.
- `scripts/behavior_test.py` switches off only the official Superpowers, so a synced copy can load in its place.
- `claude plugin eval` publishes its report unless given `--no-publish`.
- `pr-review`'s temp directory, from ticket 06.
- Paid spend ran over the estimate given before the second set: $1.18 against about $0.80.
