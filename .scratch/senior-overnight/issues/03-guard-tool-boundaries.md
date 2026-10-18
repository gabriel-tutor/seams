# 03: The overnight guard's tool boundaries

**What to build:** in sleep mode, every tool that doesn't touch production runs without blocking, and production (the production environment or a production service, the live workflow instance, real contacts) is refused cleanly.

**Blocked by:** None (can start immediately).

**Status:** ready-for-agent

- [ ] Message and CRM-contact sends (WhatsApp, email, CRM) are allowed only to recipients in a list file beside the guard; an unlisted recipient is refused; an empty or missing list refuses every send.
- [ ] Deployment tools and CLI calls are refused when they name the production environment, a production service, or no environment; staging is allowed.
- [ ] The workflow instance's writes and runs (update, publish, unpublish, archive, execute, restore, data-table changes) are refused; its reads, validation and inactive drafts are allowed.
- [ ] A tool listed as "ask" in the project's settings that the guard would otherwise allow is refused with a reason, so nothing waits on a prompt.
- [ ] Must not happen: a send to an unlisted recipient; a production deploy or variable change; any change by these rules to a day session (the guard runs only in sleep mode).

**How to verify:** the guard's own suite on Python 3.14 and 3.9 (`python3 -B -m unittest discover -s tests` in the sleep-mode folder).
