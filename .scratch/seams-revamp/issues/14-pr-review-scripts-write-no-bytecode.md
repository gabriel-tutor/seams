# 14: pr-review's scripts write no bytecode into the plugin

**What to build:** running `/pr-review` leaves no `__pycache__` in the plugin. Found at 5.0.0's release check (2026-10-05): `plugin/skills/pr-review/scripts/__pycache__/` held `post_reviews.cpython-314.pyc` and `review_payload.cpython-314.pyc`, written on 2026-10-04 by `/pr-review` runs in the user's other sessions, since a local-directory marketplace loads the plugin in place and the scripts, run as `python3 <script>`, import one another. The plugin suite's bytecode check then fails on `main`; the hooks already write none. The cache was removed by hand.

**Blocked by:** None (can start immediately)

**Status:** needs-triage

- [ ] Running each pr-review script that imports another leaves no `__pycache__` under `plugin/` (e.g. `sys.dont_write_bytecode` set before the local imports, or the skill running them with `python3 -B`).
- [ ] pr-review's own suites still pass unchanged; its steps, checks and posting behave as in 5.0.0 (the user's constraint: don't ruin pr-review).
