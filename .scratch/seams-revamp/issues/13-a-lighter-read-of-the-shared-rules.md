# 13: A lighter read of the shared rules

**What to build:** spec-and-tickets work costs no more on 4.x than on 3.4.0. Ticket 08's proof measured task 2 (a confirmed design taken to its published tickets) at 1,862k tokens, $1.93 and 409 s on the candidate, against 1,348k, $1.50 and 315 s on 3.4.0, at the same 3 prompts. The cause: the session reads all of `rules.md` (9,077 bytes) at the first prompt, besides `routing.md` and `progress-file.md`, and carries it through every later turn. Open, decided when the ticket starts: whether `to-spec` and `to-tickets` read only the sections they name, whether those sections move into the skills that need them, or whether the bootstrap's pointer stops sending a fresh session to the whole file.

**Blocked by:** 09 (Release 4.0.0).

**Status:** needs-triage

- [ ] Task 2, re-measured as `docs/plugin-behavior-tests.md` "4.0.0: the proof" ran it, takes no more median tokens, cost or wall time than 3.4.0's figures above.
- [ ] No eval scenario scores lower than on 4.0.0.
- [ ] Each rule is still written once (seams-revamp decision 10).
