# Review handover

The closing message, in this order:

1. **Ready to merge?** `python3 <skill-dir>/scripts/batch_report.py --close "$EVID" ...` (every pull request's evidence directory, one pull request included): its table (pull request, author, candidate, ready to merge, blocking count, checks broken by the PR) and, for each author whose pull request is not ready, a Note for that author, ready to paste to them. Print it exactly as the script wrote it, not paraphrased.
2. **Each pull request,** in the table's order: posted (the review's URL and event, and "posted automatically" when `posted.json` says it posted by itself, with its label) or not (where the draft is, and why: the `needs your yes` line); the checks table; the findings by severity with their places; questions last.
3. **Not verified.** Every check that could not run and every axis left unchecked, with why. A review never implies more certainty than its evidence.
4. **Next.** What each author should fix first; re-review after they push with the same command, which compares with this review; and where the evidence stays (`$EVID`).
5. **Short on time?** For each pull request the review found not ready to merge (a blocking finding, a check broken by the PR, a conflict), ask with AskUserQuestion, one question per pull request, four per call: "Short on time? Take this PR over?", options "Take it over: fix it, verify, and ask before pushing" and "No, leave it to the author". Only the main session asks, and only after the table: on yes, `takeover.md`. A headless run asks the same question in text and ends the turn.
