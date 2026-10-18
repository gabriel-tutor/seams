# 03: The overnight guard's tool boundaries

**What to build:** in sleep mode, every tool that doesn't touch production runs without blocking, and production (the production environment or a production service, the live workflow instance, real contacts) is refused cleanly.

**Blocked by:** None (can start immediately).

**Status:** ready-for-agent

- [ ] Every message send and CRM record write (WhatsApp, email, CRM) is refused overnight with a reason that says to draft it for the morning (decision 17: the project's ask rules would otherwise stall the night).
- [ ] Deployment tools and CLI calls are refused when they name the production environment, a production service, or no environment; staging is allowed.
- [ ] The workflow instance's writes and runs (update, publish, unpublish, archive, execute, restore, data-table changes) are refused; its reads, validation and inactive drafts are allowed.
- [ ] A tool listed as "ask" in the project's settings that the guard would otherwise allow is refused with a reason, so nothing waits on a prompt.
- [ ] Must not happen: any message reaching a person overnight; a production deploy or variable change; any change by these rules to a day session (the guard runs only in sleep mode).

**How to verify:** the guard's own suite on Python 3.14 and 3.9 (`python3 -B -m unittest discover -s tests` in the sleep-mode folder).
