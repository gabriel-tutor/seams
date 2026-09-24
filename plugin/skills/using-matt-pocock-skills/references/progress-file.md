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
| `Updated` | the date of the last change, `YYYY-MM-DD`; the note lists the newest three |
| `Ticket` | optional: the ticket in progress |
| `Candidate` | optional: the candidate's short SHA |

A file without a `Status`, a `Stage`, a `Next` and a dated `Updated` is skipped. The note shows each field as one line of plain text of at most 200 characters, with markup removed, so keep the header plain.

After the header come the sections: `## Decisions`, each settled decision with its reason when it isn't obvious; `## Open questions`, the questions still to ask; `## Facts`, what was found that is worth keeping, with a file and line or a URL. A skill may add a section for its own step, such as the ticket list.

## Rules

- Decisions and pointers only: never a secret, a credential, a token or personal data. The file is committed, and anyone who clones the repository reads it.
- Update it at each step, setting `Updated` to today's date.
- It is a pointer, not the truth. Before acting on it, re-read the spec, the tickets and the git state; where they disagree with the file, report the mismatch instead of acting on the file.
