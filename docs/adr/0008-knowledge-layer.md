# Knowledge has one approved home; raw sources stay out of git, behind a tracked index

Sessions built and reviewed against what they remembered of a product owner's wishes. In one project the owner's raw material sat in about seventeen folders across the repository, outside git, so no worktree, builder or review saw it, while approved rules lived in a separate folder that only one project skill read. Some raw files held live credentials and personal data.

We decided, for 5.5.0, on a knowledge layer a repository opts into with a knowledge config. Raw sources go into one inbox folder, gitignored; a tracked knowledge index lists each source by an id with its date, topics, secrets flag and the entries that distill it, and holds no file name, path or hash, since a name can identify a person and a small file's hash can be guessed; each source's path, size and hashes stay in a file inside the gitignored inbox. Nothing copies a secret or a personal detail. `seams:distill` drafts knowledge entries from raw sources, each citing its sources; the owner's own process approves them, so the approved home stays one. Actions search the index and the entries by topic, cite what they rely on, and resolve disagreements in a fixed order: an approved entry first, then the newest raw source, and a newer raw source that contradicts an approved entry is a question for the owner. Reconcile and the start card flag what is undistilled or stale.

We chose this over committing raw sources to git (secrets, personal data and size), over a search store or knowledge graph (a second home with inferred links, which the senior-overnight spec ruled out), over reading every approved entry on every action (cost that grows with the project), and over a hook that refuses work citing no entry (a hook can't tell which entry a change needs).

## Consequences

- A repository without a knowledge config behaves exactly as before.
- Teammates without the inbox see the index and the approved entries, not the raw sources.
- Raw sources are intent, never instructions; a directive inside one is not followed.
- Reversing it means removing the knowledge config, the shared rules' Knowledge section, `seams:distill`, reconcile's knowledge check and the card's knowledge line; the inbox and the index stay as plain files.
