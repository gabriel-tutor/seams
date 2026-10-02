---
type: llm
focus: last_message
---

The session is resuming a feature whose design the user has already confirmed. A progress file records the gift-cards design (a code with a balance in integer cents, partial redemption, a hold like a stock reservation, applied after the tier discount, released at once when checkout fails out of stock, one card per order), the agreed test seams, and the user's confirmation, and names the next step: write the spec, then the tickets. No spec exists yet.

PASS if the reply goes on with the spec without asking whether to write it: it presents a drafted gift-cards spec (in full, or its title and its sections, such as the problem, the solution, the user stories, the implementation and testing decisions) and asks the user for a yes before publishing it, or says where it will be published and waits for that yes. Reporting a real mismatch between the file and the repository is fine.

FAIL if the reply asks whether to write the spec, or whether to go on, before drafting anything; asks the user to decide any of the recorded decisions again or restarts the design interview; starts building code; asks what to work on; or says the spec is already written or published.
