# 05: Sleep mode's takeover commands, nightly reconcile and independent checks

**What to build:** Gabriel says `takeover -soft` or `takeover -hard` and every open pull request in scope is fixed or rebuilt to the full bar and merged by its mode; each night starts by reconciling its records, the lead runs the gate and tests itself, a read-only reviewer judges, and the morning summary shows everything that needs his eye.

**Blocked by:** 02 (reconcile and the claims rule), 04 (the merge check and modes).

**Status:** ready-for-agent

- [ ] `takeover -soft` and `takeover -hard` start the night in their mode; soft leaves a pull request awaiting acceptance merge-ready; a pull request whose card can't be read is treated as awaiting acceptance.
- [ ] The night's first step is `/seams:reconcile` on the records it will use.
- [ ] Before a merge the lead runs the gate and the tests on the exact head itself and hands their output to a read-only reviewer, which judges the diff and the evidence.
- [ ] The morning summary lists the night's auto-answers, refusals and outward claims, each with its source.
- [ ] The launcher passes `--chrome`; Playwright is the overnight browser.
- [ ] Must not happen: a merge on a builder's own report; a soft-night merge awaiting acceptance.

**How to verify:** the sleep-mode launch tests (dry run shows `--chrome`), and a read of the skill against each criterion.
