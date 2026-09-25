# Work in progress lives in a committed progress file

Until 3.2, a phase kept its in-progress state (a grill's answers, the ticket being built, the candidate) only in the conversation. `/clear` lost that state, and compaction kept only a summary. Each skill kept only its first 5,000 tokens after compaction, and hook-added context was summarized away.

We decided that every flow skill keeps `.scratch/<feature>/progress.md` current at each step, and commits it with the work it describes. The session-start hook reads it at startup, resume, `/clear`, compaction and fork, and injects a short resume note. It holds this location even when tickets live on GitHub or Linear, because the hook needs a local file.

We chose the repository over the plugin's data folder and over "phase ends only". A committed file travels with the branch, survives a machine change and self-hosted resumes, and can be reviewed. A file outside the repo is tied to one machine, and phase ends alone lose the middle of a grill or a ticket.

## Consequences

- The resume note is a pointer, not the truth. Skills re-read the spec, the tickets and the git state before acting, and a missing, stale or unreadable progress file never blocks a session.
- The file is committed, so it holds decisions and pointers only, never secrets or personal data. Because a cloned repository controls the file, the resume note is built from its fields, length-capped, stripped of markup and framed as the repository's record, so a planted file can't read as instructions.
- A `pr-review` batch is the exception: its progress file sits beside its evidence under the temp directory and is never committed. The evidence it points at (worktrees, check logs, drafts) lives only on that machine, so a committed pointer would lead nowhere anywhere else. The session-start hook reads it only when it is the user's own, and lists it only in the repository it names.
- Worktrees for this work are created from local HEAD. `worktree.baseRef` defaults to `fresh`, which leaves out unpushed commits.
- Moving the file later means migrating every repository that has one, which is why this is an ADR.
