# 06: Moving existing raw material into the inbox

**What to build:** A repository's scattered raw folders move into its inbox in one reviewed step: the script plans the move (each folder to `<inbox>/<date>-<name>/`, exact duplicates by hash kept once, every old path recorded in the index), shows the list, and moves only on the user's yes. Folders that scripts read stay where they are and are indexed in place.

**Blocked by:** 01 (the knowledge config and the knowledge index).

**Status:** ready-for-agent

- [ ] The plan lists each folder, its destination, its size, and the duplicates it would drop to one copy.
- [ ] The move happens only when the user says yes at that time, with the list shown; the index then records every old path.
- [ ] Must not happen: a file deleted; a move without that yes; a folder that a script reads moved; a tracked file moved out of git silently (it is listed and refused).

**How to verify:** `scripts/test.sh` (the plan and the move on a sample repository, including duplicates and a refused tracked file).
