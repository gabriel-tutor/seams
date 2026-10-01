# pr-review posts by itself when a review is fully verified

Until 3.3, `pr-review` posted nothing to GitHub without a yes that named the pull request and the event, every time, and said so in its opening, its README and its tests. A batch of reviews therefore ended with the person answering a posting question for work the review had already proven.

We decided that a review posts without asking when it is *fully verified* at the pull request's current head, in a repository the user can push to, for all three events, and that the code decides, not the model: `post_reviews.py --auto` reads the evidence on disk (every check ran on both trees and none "could not run" or flaky, nothing under not verified, every finding verified and every blocking one proven, each requirement line of the reference answered) and re-reads the head just before it posts. Anything short of that prints `needs your yes` and is asked about as before. `draft only` in the request turns it off. An approval auto-posts only against an independent reference, never the pull request's own description. The footer says that no person read the review first, and a label with its own prefix records its state.

We chose a rule the poster enforces over a rule the skill's text asks the model to follow. A yes the model must remember to ask for is a yes the model can skip; a poster that refuses to post what the evidence does not support cannot be talked past. We kept the review's other gates as they were: an untrusted pull request's code still runs only on a yes, and nothing merges.

## Consequences

- Reversing "nothing posts without a yes" is the point, and it is hard to reverse back: a review that is public on a colleague's pull request cannot be unsaid. The cost of a wrong auto-post is that, which is why the rule fails closed: missing, unreadable or unconvincing evidence is evidence of nothing, and a head that moved is reviewed again, never posted stale.
- In a batch the post step runs in a later turn, outside the skill's pre-approval, so hands-off posting needs the user's own `Bash(python3 *post_reviews.py *)` permission. Without it Claude Code asks, and the reviews wait, drafted.
- A take-over pushes to someone else's branch, so its push is deliberately not pre-approved and not part of this decision: the user's yes, and Claude Code's own prompt naming the branch and commit, stay.
- A review of the user's own pull request is only a comment, and an approval cannot be exercised on a pull request the user opened: GitHub allows neither.
