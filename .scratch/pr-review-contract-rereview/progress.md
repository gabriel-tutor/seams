# pr-review: a re-review checks the rules, not just closure

Status: done
Stage: built
Updated: 2026-10-20
Next: none; shipped on branch pr-review/contract-rereview (not pushed; release through seams:release).

## Why
A re-review checked only that its earlier findings had closed and approved a take-over's own code, which
wrote a value outside the code's closed set of states and let a declared label outrank the content it describes. The
take-over had carried the wrong values into lines it rewrote, and the poster approved the viewer's own commit by
itself. No test pinned the value to its set.

## Decisions
1. Independence: a review of commits the viewer wrote (take-over or fix round) is drafted as COMMENT, never APPROVE;
   before merge a person or a fresh-context reviewer with an adversarial brief and facts only reviews the whole delta,
   and the handover names who. (user, 20 Oct)
2. Invariants come from the baseline's docs (knowledge, CONTEXT.md, ADRs) AND the code's own constants near the touched
   lines (exported closed sets, enums, precedence/ranking functions); each gets a check that can go red. (user)
3. A re-review reviews the whole delta since the earlier review's commit, afresh, against the spec, the knowledge and the
   invariants; earlier findings closing is necessary, never sufficient. (user)
4. Tests: STOPS phrase tests in scripts/tests/test_plugin.sh, scoped to each step, with the existing drop-probe. (user)
5. Placement: the references, not SKILL.md (it sits at 11,075 of its 11,200-byte bound): understand-and-review.md,
   takeover.md, and (after code review) post.md and handover.md. (fact; amended after code review)
7. Confirmed by the user 20 Oct; build in a worktree, branch pr-review/contract-rereview; stop before pushing.
6. The take-over keeps "smallest change", but every line it rewrites is its own and must meet the invariants. (lens)

8. The poster enforces decision 1 in code (code review, 20 Oct): `post_reviews.py --auto` refuses an APPROVE when a
   commit of the pull request is the viewer's, failing closed on an unreadable list, the 250-commit limit or an
   unnamed author; post.md never offers APPROVE on such a pull request; ADR 0004 amended. A rule the poster enforces
   beats one the text asks for (ADR 0004).

## Facts
- understand-and-review.md Understand 3 asks only which earlier findings still hold; the risk reviewer's axes have no
  invariants axis; takeover.md step 2 says "fix only what the findings asked for".
- References bound: 16,000 bytes each; both are about 6,000 today.
