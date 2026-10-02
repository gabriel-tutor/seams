# The workflow is enforced by hooks, not by prose alone

The bootstrap's routing held 5/5 in tests, but a rule in context is a promise the model keeps, not one the plugin keeps. We decided that a PreToolUse hook refuses any change to the project (file edits, and shell commands that look like writes) until a process skill has been declared for the current request, and that a Stop hook refuses to end a turn once when the project changed and verification did not follow. Both hooks fail open on their own errors and refuse with a reason rather than asking the user, so a false positive costs one cheap declaration, never a prompt. Shell commands are classified by pattern; that mesh is documented as best effort, because no hook can prove a command has no side effects.

ADR 0005 changes how long a declaration lasts: since 4.0.0, until another process skill is invoked or the session is cleared, no longer for the current request only.

## Considered options

- Prose only: no enforcement; rejected because "always" has to hold on the long tail, not only in tests.
- `permissionDecision: "ask"` instead of deny: gives the user an override, but turns every false positive into a prompt and lets a hurried yes bypass the workflow.
