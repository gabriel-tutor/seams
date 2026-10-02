# Design lens

The axes a senior engineer's design review covers. The grill consults this before declaring the frontier empty: any axis that applies to the change and is still unsettled becomes a frontier question. An axis that doesn't apply is skipped without comment. Facts go in the question's facts section; only the decision goes to the user.

How much of the lens applies scales with the change: the axes its row's questions name (shared rules: Process by size and risk), and for a bounded change the rest only where the change touches them.

## The axes

1. **Data model.** What are the entities, their identities, their invariants? Which existing glossary terms does this touch, and does it need a new one? (Resolved terms go to `CONTEXT.md` through `domain-modeling`.)
2. **Interfaces and seams.** What is the public interface, in the `codebase-design` sense: types, invariants, ordering, error modes? Where is the seam, and is it one that already exists? Deep module or a pass-through?
3. **Failure modes and errors.** What can fail: bad input, a dependency down, a partial write, a concurrent caller? For each: fail loud, fail safe, retry, or roll back? What does the caller see?
4. **Scale and performance.** What are the expected sizes and rates, and what happens at ten times that? Is anything O(n²), unbounded, or held in memory that shouldn't be? Only when the change sits on a hot path or touches a collection that can grow.
5. **Security and trust boundaries.** Where does untrusted input enter: user input, network, files, environment? Is it validated at the boundary? Any secrets, credentials or personal data involved, and where do they live? (Code-level checks are the `security-guidance` plugin's job, if installed; the design decides where the boundaries are.)
6. **Observability.** How will we know it's broken in use, not only in tests? What gets logged at the boundaries, with which identifiers? Is there an error a user would report that the code swallows silently?
7. **Migration and rollout.** Does existing data, config or a public interface change shape? If so: expand–contract, a flag, or a one-shot cutover, and how it's reversed if wrong. Only when something existing changes shape.
8. **Testing strategy.** Which seams are tested, at which level (unit, integration, end to end), and what is deliberately not tested? What would a regression of this feature look like, and would the tests catch it?
9. **Operability.** How is it run, configured and verified by a person? Does anything need a README line, an environment variable, or a one-off setup step? Any dependency added, and is it worth its weight?
10. **Cost and reversibility.** Is any decision here hard to reverse? Those are the ADR candidates. Is there a cheaper design that gives most of the value?

## What this is not

It is not a questionnaire to walk through in order, and it is not a document to fill in. It is the checklist the grill runs against its own design tree before claiming the tree is complete. Most axes resolve from the code and the conversation without a question; the user is asked only when a decision is genuinely theirs.
