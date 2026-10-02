# Progress file

Read this before writing a feature's progress file. It is the feature's durable record of work in progress: what has been settled and what is still open, the ticket in progress, the candidate, the stage and the next step. The Seams skills write this format, and at every session start (new, resumed, cleared, compacted or forked) the session-start hook reads its header into the resume note, so a fresh context continues where the work stopped.

## Where

`.scratch/<feature>/progress.md` at the repository root, beside the feature's spec, whatever tracker the repository uses. `<feature>` is the feature's short kebab-case name, the folder its spec uses. The file is committed with the work it describes.

## Format

```markdown
# Progress: gift cards

Status: active
Stage: designing
Next: Ask the open questions on the tier discount and the out-of-stock hold, then check the design lens.
Updated: 2026-09-20

## Decisions
1. A gift card is a code with a balance in integer cents; checkout redeems it against the order total.
2. Partial redemption is allowed: what the order doesn't use stays on the card.

## Open questions
- Does the gift card apply before or after the tier discount?
- When checkout fails out of stock after the hold, is the held amount released at once or after a timeout?

## Facts
- Totals are integer cents (src/format.ts); the tier discount is applied in src/pricing.ts.
```

The header is the `Key: value` lines before the first `##` heading, one line each:

| Key | Value |
| --- | --- |
| `Status` | `active` while work remains; `done` once the feature is finished, which takes it out of the resume note |
| `Stage` | `designing` while the grill runs, then the stage reached: designed, built, integrated, release-ready, deployed or operated |
| `Next` | the next step, in one sentence |
| `Updated` | the date of the last change, `YYYY-MM-DD`, which a time may follow (`2026-09-25T10:00`); the note lists the newest three |
| `Ticket` | optional: the ticket in progress, by its number or id (`05`, `#123`), or the tickets of a parallel run (`03, 05, 07`) |
| `Candidate` | optional: while a ticket is in progress, the short SHA of the commit its review ran on (a commit can't name itself; `Next` says what the ticket's later commits do) |

A file without a `Status`, a `Stage`, a `Next` and a dated `Updated` is skipped. The note shows each field as one line of plain text of at most 200 characters (a ticket in at most 60 characters), with markup removed, so keep the header plain.

After the header come the sections: `## Decisions`, each settled decision with its reason when it isn't obvious; `## Open questions`, the questions still to ask; `## Facts`, what was found that is worth keeping, with a file and line or a URL. A skill adds a section for its own step, as below.

## Who keeps it

Each flow skill updates the file at its own step and commits it by name with the work it describes:

- `grill`: creates it at the first settled decision (`Stage: designing`) and records each answered round, then the user's confirmation of the design with `Stage: designed`, which starts the continuous flow, and where `implement` builds it.
- `to-spec`: `Stage: designed`, the spec's path or URL under `## Spec`, and `Next` the split into tickets; committed with the spec after the publish yes.
- `to-tickets`: the ticket list under `## Tickets` and `Next` the first unblocked ticket; committed with the tickets after the approval.
- `implement`: `Ticket` after its gate, `Candidate` when the review starts, and the review's findings to fix under `## Review`. Its record commit, just before the definition of done, sets the stage reached, marks the ticket done and removes those three; after the last ticket it sets `Status: done`, unless the spec has a Release section. A parallel run (`implement`'s `references/parallel.md`) keeps each of its tickets' state under `## Parallel`, which only the main conversation writes.
- `finishing-a-development-branch`: `Stage: integrated` after a local merge, committed on the base branch.
- `release`: the stage reached at its operations handover, and `Status: done` once the last environment the spec's Release section names is verified.
- `pr-review`: a batch keeps a file of this shape beside its evidence, under the temp directory rather than the repository (ADR 0003 names the exception), which its scripts write and bring up to date as each pull request moves on. Its `Stage` counts the pull requests by step (`3 pull requests: 1 drafted, 2 pinned`), its `Updated` carries the time, and two more keys name the session's repository (`Repository`) and the evidence directories (`Evidence`). The resume note lists an unfinished batch of the session's repository among its entries; the same `/pr-review` command, typed again or run by Claude when asked, continues it.

## Rules

- Decisions and pointers only: never a secret, a credential, a token or personal data. The file is committed, and anyone who clones the repository reads it.
- Update it at each step, setting `Updated` to today's date.
- It is a pointer, not the truth. Before acting on it, re-read the spec, the tickets and the git state; where they disagree with the file, report the mismatch instead of acting on the file.
