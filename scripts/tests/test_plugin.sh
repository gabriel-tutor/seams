#!/usr/bin/env bash
# Static checks on the plugin: manifests validate, skills are well-formed and model-invocable,
# the three adapted flow skills carry their required sections and attribution, the upstream files
# they came from are compared with the installed ones (a warning on drift), and the copied
# Superpowers skills are byte-identical to what THIRD_PARTY_NOTICES.md records.
set -euo pipefail
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PLUGIN="$REPO/plugin"
fail() { echo "FAIL: $*" >&2; exit 1; }
headings_in_order() {   # $1 = skill name, $2 = file, $3... = "## " headings that must appear in this order
  local name="$1" file="$2" prev=0 n h; shift 2
  for h in "$@"; do
    n=$(grep -nxF "$h" "$file" | head -1 | cut -d: -f1) || fail "$name lacks the heading: $h"
    (( n > prev )) || fail "$name: heading out of order: $h"
    prev=$n
  done
}
must_say() {   # $1 = skill name, $2 = file, $3... = phrases the file must contain verbatim
  local name="$1" file="$2" needle; shift 2
  for needle in "$@"; do grep -qF -- "$needle" "$file" || fail "$name should say: $needle"; done
}
last_line_says() {   # $1 = skill name, $2 = file, $3... = phrases its last non-blank line, the attribution, must contain
  local name="$1" file="$2" last needle; shift 2
  last=$(grep -v '^[[:space:]]*$' "$file" | tail -1)
  for needle in "$@"; do [[ $last == *"$needle"* ]] || fail "$name: the last line does not attribute the original ($needle): $last"; done
}
section() { awk -v h="## $1" 'index($0, h) == 1 {p=1; next} /^## /{p=0} p' "$2"; }   # $1 = heading text, $2 = file: that section's body
section_says() {   # $1 = skill name, $2 = file, $3 = heading text, $4... = phrases that section must contain verbatim
  local name="$1" file="$2" heading="$3" body needle; shift 3
  body=$(section "$heading" "$file"); [[ -n "$body" ]] || fail "$name lacks the section: ## $heading"
  for needle in "$@"; do [[ $body == *"$needle"* ]] || fail "$name, under '## $heading', should say: $needle"; done
}
plugin_guards() {   # $1 = a plugin directory: prints a line for each SKILL.md over 11,000 bytes and each pin of a
  python3 - "$1" <<'PY'   # model or an effort level in a skill's or an agent's frontmatter; prints nothing when all hold
import pathlib, re, sys
root = pathlib.Path(sys.argv[1])
skills = sorted(root.glob("skills/*/SKILL.md"))
for path in skills:
    if path.stat().st_size > 11000:
        print(f"{path.relative_to(root)} is {path.stat().st_size} bytes, over the 11,000-byte bound")
for path in skills + sorted(root.glob("agents/**/*.md")):
    front = re.match(r"---\n(.*?)\n---\n", path.read_text(), re.S)
    keys = {line.split(":", 1)[0].strip() for line in (front.group(1) if front else "").splitlines() if ":" in line and line[:1].isalpha()}
    for key in ("model", "effort"):
        if key in keys:
            print(f"{path.relative_to(root)} sets {key}")
PY
}

claude plugin validate --strict "$PLUGIN" >/dev/null || fail "plugin manifest does not validate"
claude plugin validate --strict "$REPO" >/dev/null || fail "marketplace manifest does not validate"

# No bytecode in the plugin (lean-and-durable ticket 06, the spec's housekeeping): a marketplace added from a local
# directory loads this folder in place, so what is in it is what runs. The suites, the hooks and the scripts write none.
STALE=$(find "$PLUGIN" \( -name __pycache__ -o -name '*.pyc' \) -print)
[[ -z "$STALE" ]] || fail "bytecode in the plugin, which a local-directory marketplace loads in place: $STALE"

# One version, kept in plugin.json only (lean-and-durable ticket 08): when the marketplace entry sets one too, Claude
# Code uses plugin.json's without a warning, so a second copy could only go stale. The README's version badge and the
# CHANGELOG's first entry name the same release, so a bump cannot land in one place only.
json_field() {   # $1 = a JSON file, $2 = a dotted path into it (a number selects a list item)
  python3 - "$1" "$2" <<'PY'
import json, sys
value = json.load(open(sys.argv[1]))
for key in sys.argv[2].split("."):
    value = value[int(key)] if isinstance(value, list) else value[key]
print(value)
PY
}
V_PLUGIN=$(json_field "$PLUGIN/.claude-plugin/plugin.json" version)
V_MARKET=$(python3 -c 'import json, sys; print(" ".join(e["version"] for e in json.load(open(sys.argv[1]))["plugins"] if "version" in e))' \
  "$REPO/.claude-plugin/marketplace.json")
[[ -z $V_MARKET ]] || fail "the marketplace entry carries a version ($V_MARKET); the version lives in plugin.json only"
V_README=$(grep -oE 'badge/plugin-[0-9]+\.[0-9]+\.[0-9]+' "$REPO/README.md" | head -1 | cut -d- -f2)
V_CHANGELOG=$(grep -m1 -oE '^## [0-9]+\.[0-9]+\.[0-9]+' "$REPO/CHANGELOG.md" | cut -d' ' -f2)
[[ -n $V_PLUGIN && $V_PLUGIN == "$V_README" && $V_PLUGIN == "$V_CHANGELOG" ]] \
  || fail "versions disagree: plugin.json $V_PLUGIN, README badge $V_README, CHANGELOG $V_CHANGELOG"

# Every skill: frontmatter naming its own directory and a description. Model invocation stays on for
# every skill but the ones typed by hand only: pr-review, which runs a PR's code, spends minutes of
# checks and can post to GitHub, is one of those, and stays one.
USER_ONLY="pr-review"
for f in "$PLUGIN"/skills/*/SKILL.md; do
  python3 - "$f" "$USER_ONLY" <<'PY' || fail "bad frontmatter: $f"
import pathlib, sys
p = pathlib.Path(sys.argv[1])
user_only = set(sys.argv[2].split())
text = p.read_text()
assert text.startswith("---\n"), "no frontmatter"
head = text[4:text.index("\n---\n", 4)]
fields = {k.strip(): v.strip() for k, v in (l.split(":", 1) for l in head.splitlines() if ":" in l and not l.startswith(" "))}
assert fields.get("name") == p.parent.name, f"name {fields.get('name')!r} != directory {p.parent.name!r}"
assert fields.get("description"), "empty description"
manual = fields.get("disable-model-invocation", "false") == "true"
assert manual == (p.parent.name in user_only), f"{p.parent.name}: disable-model-invocation {'true' if manual else 'unset'}, expected {'true' if not manual else 'unset'}"
PY
done

# The three flow skills are Seams' own adaptations of Matt Pocock's (ADR-0002): self-contained, so
# none names a SKILL.md to read at runtime; the sections the ticket requires, in order; the wording
# each must keep; and a last line attributing the upstream skill, the MIT license and the commit
# recorded in the notices.
NOTICES="$PLUGIN/THIRD_PARTY_NOTICES.md"
MP_SECTION=$(section "Matt Pocock" "$NOTICES")
[[ -n "$MP_SECTION" ]] || fail "no 'Matt Pocock' section in THIRD_PARTY_NOTICES.md"
MP_COMMIT=$(grep -oE '\b[0-9a-f]{40}\b' <<< "$MP_SECTION" | sort -u) || fail "the notices name no upstream commit"
[[ $(wc -l <<< "$MP_COMMIT") -eq 1 ]] || fail "the notices should name one upstream commit, got: $MP_COMMIT"
for s in to-spec to-tickets implement; do
  f="$PLUGIN/skills/$s/SKILL.md"
  grep -q 'SKILL\.md' "$f" && fail "$s still names a SKILL.md file to read"
  case $s in
    to-spec)    headings=("## Gate" "## Process" "## Spec template" "## Next")
                needles=("Write the spec now?" "instead of asking again" "Alternatives considered" "Risks and failure modes"
                         "Rollout and migration" "Observability" "**Release**" "deployment target" "spec's title and where it will go"
                         "ready-for-agent") ;;
    to-tickets) headings=("## Gate" "## Process" "## Ticket templates" "## Next")
                needles=("How to verify" "Blocked by" "granularity" "Iterate until the user approves" "ready-for-agent"
                         "walking skeleton" "ticket 01" "negative cases" "acceptance criteria" "matt-pocock-workflow:release") ;;
    implement)  headings=("## Gate" "## Build" "## Commit" "## Review" "## Review fixes" "## Definition of done" "## Handover")
                needles=("Invoke \`tdd\`" "by name" "excluded" "git merge-base" "nothing to review" "Invoke \`code-review\`"
                         "re-run the checks" "verification-before-completion" "candidate SHA"
                         "**Run it.**" "**Try it.**" "**What changed.**" "**Next.**" "stage reached"
                         "designed, built, integrated, release-ready, deployed, operated") ;;
  esac
  headings_in_order "$s" "$f" "${headings[@]}"
  must_say "$s" "$f" "${needles[@]}"
  last_line_says "$s" "$f" "Matt Pocock" "MIT" "$MP_COMMIT"
done

# The upstream files those three were adapted from: SHA-256 recorded at the upstream commit and
# compared with the installed copies. Drift is a warning, never a failure: the port is a manual
# review (ADR-0002), and a machine without his skills has nothing to compare.
MP_SUMS=$(grep -E '^[0-9a-f]{64}  skills/engineering/[a-z-]+/SKILL\.md$' <<< "$MP_SECTION") \
  || fail "no upstream checksums in the Matt Pocock section of THIRD_PARTY_NOTICES.md"
[[ $(wc -l <<< "$MP_SUMS") -eq 3 ]] || fail "expected 3 recorded upstream checksums, got: $MP_SUMS"
upstream_drift() {   # $1 = the Claude config directory; prints WARN lines, exit status always 0
  local skills="$1/skills" sum path name have
  while read -r sum path; do
    name=$(basename "$(dirname "$path")")
    if [[ ! -f "$skills/$name/SKILL.md" ]]; then echo "note: $skills/$name/SKILL.md is not installed; drift not checked"; continue; fi
    have=$(shasum -a 256 "$skills/$name/SKILL.md" | cut -d' ' -f1)
    [[ $have == "$sum" ]] || echo "WARN: installed $name/SKILL.md differs from the hash recorded in THIRD_PARTY_NOTICES.md" \
      "(Matt Pocock's $name has moved on since commit ${MP_COMMIT:0:7}; review the port)"
  done <<< "$MP_SUMS"
  return 0
}
upstream_drift "${CLAUDE_CONFIG_DIR:-$HOME/.claude}"
FIXTURE=$(mktemp -d); mkdir -p "$FIXTURE/skills/to-spec"; echo "a newer upstream to-spec" > "$FIXTURE/skills/to-spec/SKILL.md"
DRIFT=$(upstream_drift "$FIXTURE"); rm -rf "$FIXTURE"
[[ $DRIFT == *"WARN: installed to-spec/SKILL.md differs"* ]] || fail "the drift check did not warn on a changed upstream file: $DRIFT"
[[ $DRIFT == *"note: $FIXTURE/skills/implement/SKILL.md is not installed"* ]] || fail "the drift check did not note a missing upstream file: $DRIFT"

# The release skill (ticket 05): the sections past the merge, in order, and the rules that keep a
# deploy behind an explicit yes and a verified candidate.
REL="$PLUGIN/skills/release/SKILL.md"
[[ -f "$REL" ]] || fail "release skill missing"
headings_in_order release "$REL" "## Gate" "## Readiness" "## Deploy" "## Verify" "## Operations handover" "## Targets"
must_say release "$REL" "check readiness now?" "Anything unmet blocks" "the target, the environment and the candidate" \
  "every time" "staged environment" "running version" "smoke" "abort" "rollback" "runbook" "alert owner" "Stage reached" \
  "no deploy target" "Web host" "Container or VPS" "Mobile store" "CLI or library registry" "Browser extension store" "Desktop"

# Foundations (ticket 05): the five production rows, their not-applicable rule, and the new offers.
must_say foundations "$PLUGIN/skills/foundations/SKILL.md" "| Deploy target and pipeline |" "| Environments and config |" \
  "| Backups and restore |" "| Monitoring and alerts |" "| Dependency and secret scanning |" "not applicable" \
  "published nowhere" "runbook" ".env.example" "platform's skill"

# The incident skill (ticket 06): contain and restore before diagnosis, the seven steps in order,
# and each step's rule inside its own section: the three facts and no cause; the safest reversible
# action, every outward action behind a yes; verification before "no longer affected"; the cause
# through diagnosing-bugs; the fix on the normal route, regression test first, through implement
# and release; the note under docs/incidents/ with its follow-ups; the stage in the handover.
INC="$PLUGIN/skills/incident/SKILL.md"
[[ -f "$INC" ]] || fail "incident skill missing"
headings_in_order incident "$INC" "## Impact" "## Contain" "## Restore and confirm" "## Diagnose" "## Fix" "## Post-mortem" "## Incident handover"
section_says incident "$INC" Impact "Who is affected" "Since when" "What changed last" "no cause named here"
section_says incident "$INC" Contain "safest reversible action" "Ask before any outward action" "wait for the yes" "do not guess"
section_says incident "$INC" "Restore and confirm" "no longer affected" "matt-pocock-workflow:verification-before-completion"
section_says incident "$INC" Diagnose "Invoke \`diagnosing-bugs\`" "first hypothesis"
section_says incident "$INC" Fix "normal route" "regression test first" "matt-pocock-workflow:implement" "sensitive change" "matt-pocock-workflow:release"
section_says incident "$INC" Post-mortem "docs/incidents/" "**Follow-ups**" "follow-up ticket" "ends before the fix"
section_says incident "$INC" "Incident handover" "Stage reached" "designed, built, integrated, release-ready, deployed, operated"

# The grill (ticket 06): a decision the code or an earlier answer already settles is not a question,
# and the rule sits in the Presentation section, where the facts-then-one-question format is.
section_says grill "$PLUGIN/skills/grill/SKILL.md" Presentation "already settles is not a question; the fact goes in the facts section"

# The progress file (lean-and-durable ticket 04, ADR 0003): one format, defined once beside routing.md, that the skills
# write and the session-start hook reads. The grill keeps it from its first decision, resumes from it
# instead of starting over, closes it itself when no later skill will, and asks every independent
# question at once while a risky one still comes alone.
PF="$PLUGIN/skills/using-matt-pocock-skills/references/progress-file.md"
[[ -f "$PF" ]] || fail "progress-file.md missing"
must_say progress-file.md "$PF" "\`.scratch/<feature>/progress.md\`" "Status: active" "Stage: designing" "Next: " "Updated: " \
  "\`Ticket\`" "\`Candidate\`" "## Decisions" "## Open questions" "## Facts" "\`done\`" "is skipped" "200 characters" \
  "Decisions and pointers only" "never a secret" "personal data" "committed" "a pointer, not the truth" "report the mismatch" \
  "60 characters"
section_says progress-file.md "$PF" "Who keeps it" "\`grill\`" "\`to-spec\`" "\`## Spec\`" "\`to-tickets\`" "\`## Tickets\`" \
  "\`implement\`" "\`## Review\`" "record commit" "\`finishing-a-development-branch\`" "\`release\`"
GRILL="$PLUGIN/skills/grill/SKILL.md"
section_says grill "$GRILL" Presentation "up to four in one AskUserQuestion call" "A gate, security or destructive question is asked alone"
section_says grill "$GRILL" "Progress file" "\`.scratch/<feature>/progress.md\`" "references/progress-file.md" \
  "at the first settled decision" "After each answered round" "never a secret" \
  "typed as a message" "invoke \`matt-pocock-workflow:grill\` again before the update"
section_says grill "$GRILL" Resuming "resume note" "the spec, the tickets" "git state" "mismatch" \
  "Settled decisions are not asked again" "recorded open questions"
section_says grill "$GRILL" Done "\`Next\`" "set \`Status: done\` in the commit that ships the change"
must_say routing.md "$PLUGIN/skills/using-matt-pocock-skills/references/routing.md" "\`.scratch/<feature>/progress.md\`" "progress-file.md"

# The flow skills keep the progress file too (lean-and-durable ticket 05). implement records the ticket in progress, each
# candidate and the review's findings, commits the file with the ticket's commits, and closes the ticket
# with a record commit that the definition of done then runs on. It resumes a ticket in progress without
# its gate question when the file and git agree, and reports a mismatch instead of acting on the file.
IMPL="$PLUGIN/skills/implement/SKILL.md"
headings_in_order implement "$IMPL" "## Gate" "## Progress file" "## Resuming" "## Build"
section_says implement "$IMPL" Gate "resume a ticket in progress whose state matches its progress file" \
  "invoke \`matt-pocock-workflow:implement\` again before the next change"
# A commit cannot name itself (the live resume run kept the reviewed commit as the candidate and said what
# the fix did in Next): the candidate is the commit under review, and a resume checks that the history
# after it holds only commits the file accounts for.
section_says implement "$IMPL" "Progress file" "\`.scratch/<feature>/progress.md\`" "references/progress-file.md" \
  "stage it by name with each of the ticket's commits" "\`Ticket\`" "\`Candidate\` is the commit under review" \
  "\`## Review\`" "the stage reached" "\`Status: done\`" "Release section" "\`matt-pocock-workflow:release\`" "never a secret" \
  "naming the branch and the SHAs it needs"
section_says implement "$IMPL" Resuming "resume note" "the ticket and the spec" "git state" "report the mismatch" \
  "don't ask the gate question again" "the branch is not the one \`Next\` names" "commits the file doesn't account for"
# The live run's definition of done found a row unmet and still left the feature done: the rule to put the
# ticket back sits where the table is.
section_says implement "$IMPL" "Definition of done" "after the record commit" "put \`Ticket\` back"
# to-spec sets the stage to designed and points to the spec; its publish question names the commit that
# follows (the spec, the progress file, the grill's glossary and ADR changes), made by name after the yes.
section_says to-spec "$PLUGIN/skills/to-spec/SKILL.md" Process "name the commit that follows" "the progress file" \
  "\`CONTEXT.md\`" "ADR" "references/progress-file.md" "\`Stage: designed\`" "\`## Spec\`" \
  "\`matt-pocock-workflow:to-tickets\`" "never a secret" "commit the files the question named, by name"
# to-tickets records the ticket list and the first unblocked ticket, and after the approval commits the
# tickets and the progress file by name.
section_says to-tickets "$PLUGIN/skills/to-tickets/SKILL.md" Process "references/progress-file.md" "\`## Tickets\`" \
  "first unblocked ticket" "\`matt-pocock-workflow:implement\`" "never a secret" \
  "commit the tickets (when they are files) and the progress file by name" "the approval covers that commit" \
  "The approval question names what its yes covers"
# release records the stage it reached in the progress file at its operations handover, and sets it done
# once the candidate is verified in the last environment the spec's Release section names.
section_says release "$PLUGIN/skills/release/SKILL.md" "Operations handover" "references/progress-file.md" \
  "\`Status: done\`" "last environment the spec's Release section names" "what is left" "by name" "never a secret"
# The progress file's commits move HEAD past what the review saw: release's candidate is the one implement's
# definition of done covered, or that candidate as finishing-a-development-branch integrated and recorded it.
section_says release "$PLUGIN/skills/release/SKILL.md" Readiness "the candidate \`implement\`'s definition of done covered" \
  "integrated and recorded it"
# Each skill that writes the progress file reads its format first, and states the file's one must-not in the
# same words as the format reference, so that the rule cannot drift from one file to the next.
for s in to-spec to-tickets finishing-a-development-branch release; do
  must_say "$s" "$PLUGIN/skills/$s/SKILL.md" "read it before the first write"
done
for f in "$PF" "$PLUGIN"/skills/{grill,to-spec,to-tickets,implement,finishing-a-development-branch,release}/SKILL.md; do
  must_say "$(basename "$(dirname "$f")")" "$f" "never a secret, a credential, a token or personal data"
done
# Every skill stays whole in what compaction keeps of an invoked skill (lean-and-durable ticket 08): at most 11,000
# bytes, about 4,000 tokens (the spec's bound, calibrated from `claude plugin details`). No skill or agent pins a model
# or an effort level: a pin overrides the level the user chose, both ways, and a model that differs from the session's
# costs a prompt-cache miss. A fixture that breaks each rule shows the guard catching what it is for.
GUARD_FIX=$(mktemp -d); mkdir -p "$GUARD_FIX"/skills/{big,at-bound,pinned} "$GUARD_FIX/agents"
for s in big at-bound; do
  printf -- '---\nname: %s\ndescription: x\n---\n' "$s" > "$GUARD_FIX/skills/$s/SKILL.md"
  n=$(( $([[ $s == big ]] && echo 11001 || echo 11000) - $(wc -c < "$GUARD_FIX/skills/$s/SKILL.md") ))
  printf '%*s' "$n" '' >> "$GUARD_FIX/skills/$s/SKILL.md"
done
printf -- '---\nname: pinned\ndescription: x\nmodel: claude-opus-5\neffort: high\n---\n' > "$GUARD_FIX/skills/pinned/SKILL.md"
printf -- '---\nname: scout\ndescription: x\neffort: low\n---\n' > "$GUARD_FIX/agents/scout.md"
printf -- '---\nname: fine\ndescription: x\n---\n\nmodel: effort: lines in the body are not frontmatter\n' > "$GUARD_FIX/agents/fine.md"
GUARD_OUT=$(plugin_guards "$GUARD_FIX"); rm -rf "$GUARD_FIX"
for want in "skills/big/SKILL.md is 11001 bytes, over the 11,000-byte bound" "skills/pinned/SKILL.md sets model" \
  "skills/pinned/SKILL.md sets effort" "agents/scout.md sets effort"; do
  [[ $GUARD_OUT == *"$want"* ]] || fail "the guard missed: $want (it said: $GUARD_OUT)"
done
[[ $GUARD_OUT != *at-bound* && $GUARD_OUT != *fine* ]] || fail "the guard flagged a file within its rules: $GUARD_OUT"
GUARD_OUT=$(plugin_guards "$PLUGIN")
[[ -z $GUARD_OUT ]] || fail "$GUARD_OUT"
# What every session pays for the plugin before any skill fires (lean-and-durable ticket 08): its listing, the skills'
# and agents' names and descriptions, at most 875 tokens as `claude plugin details` measures this tree (3.2.1 paid about
# 1,165). Measured from disk (`--plugin-dir`, source "@inline"), never from an installed copy.
DETAILS=$(claude --plugin-dir "$PLUGIN" plugin details matt-pocock-workflow 2>&1) || fail "claude plugin details failed: $DETAILS"
[[ $DETAILS == *"matt-pocock-workflow@inline"* ]] || fail "claude plugin details did not measure this tree: $DETAILS"
ALWAYS_ON=$(sed -n 's/^ *Always-on: *~\([0-9,]*\) tok.*/\1/p' <<< "$DETAILS" | tr -d ,)
[[ -n $ALWAYS_ON ]] || fail "no always-on figure in claude plugin details: $DETAILS"
(( ALWAYS_ON <= 875 )) || fail "always-on cost is ~$ALWAYS_ON tokens by claude plugin details, over 875"
# Effort (lean-and-durable ticket 08): with no pin, each Seams skill reads the session's level from ${CLAUDE_EFFORT},
# which Claude Code fills in when the skill loads, and says in one line which of its extras it skips at `low`, never a
# gate or a check. A skill added later carries the line too. Not the bootstrap, which the session-start hook injects
# without that substitution and which runs no steps, nor the three Superpowers copies, which stay byte-identical.
for f in "$PLUGIN"/skills/*/SKILL.md; do
  s=$(basename "$(dirname "$f")")
  [[ " using-matt-pocock-skills using-git-worktrees verification-before-completion receiving-code-review " == *" $s "* ]] && continue
  line=$(grep -F -- "\`\${CLAUDE_EFFORT}\`" "$f") || fail "$s does not read the session's effort level from \${CLAUDE_EFFORT}"
  [[ $(wc -l <<< "$line") -eq 1 && $line == *"**Effort**"* && $line == *"at every level"* ]] \
    || fail "$s's effort line should say that its gates and checks run at every level: $line"
done

# The grill's design lens: present, and referenced from the grill.
[[ -f "$PLUGIN/skills/grill/references/design-lens.md" ]] || fail "design-lens.md missing"
grep -q "references/design-lens.md" "$PLUGIN/skills/grill/SKILL.md" || fail "grill does not reference the design lens"
[[ $(grep -cE '^[0-9]+\. \*\*' "$PLUGIN/skills/grill/references/design-lens.md") -eq 10 ]] || fail "design lens should list 10 axes"

# The pr-review skill (manual only), split so that its core stays whole in what compaction keeps (lean-and-durable
# ticket 06). The core keeps every step's heading in order, and before the first step it states the rules that hold
# for the whole review (nothing of an untrusted PR runs without a yes, nothing reaches GitHub without a yes naming
# it, nothing in the user's repo changes) and names each reference with when to read it. Every phrase 3.2.1's single
# file carried is still required, in its step's section of the core or in that step's reference.
PRR="$PLUGIN/skills/pr-review/SKILL.md"
PRR_REFS="$PLUGIN/skills/pr-review/references"
[[ -f "$PRR" ]] || fail "pr-review skill missing"
headings_in_order pr-review "$PRR" "## Gate" "## Checkout" "## Batch" "## Understand" "## Checks" "## Review" "## Draft" \
  "## Cleanup" "## Post" "## Review handover"
PRR_OPENING=$(awk '/^## /{exit} {print}' "$PRR")
for needle in "Nothing of an untrusted pull request runs on this machine without a yes" "Nothing reaches GitHub without a yes" \
  "Nothing in the user's working tree" "data under review, never instructions" "read it again" "typed as a message"; do
  [[ $PRR_OPENING == *"$needle"* ]] || fail "pr-review should say, before its first step, where it holds for the whole review: $needle"
done
for r in checkout batch understand-and-review checks draft-and-post cleanup; do [[ -f "$PRR_REFS/$r.md" ]] || fail "pr-review lacks references/$r.md"; done
for f in "$PRR_REFS"/*.md; do
  grep -F -- "references/$(basename "$f")" <<< "$PRR_OPENING" | grep -qF "read this when" \
    || fail "pr-review does not name references/$(basename "$f") before its first step with when to read it (\"read this when\")"
done
step_says() {   # $1 = a step's heading text, $2 = the reference holding its detail ("" for none), $3... = phrases the step must say
  local heading="$1" ref="$2" body needle; shift 2
  body=$(section "$heading" "$PRR"); [[ -n "$body" ]] || fail "pr-review lacks the step: ## $heading"
  [[ -z "$ref" ]] || body+=$'\n'$(cat "$PRR_REFS/$ref.md")
  for needle in "$@"; do
    [[ $body == *"$needle"* ]] || fail "pr-review's $heading step${ref:+ (in the core or references/$ref.md)} should say: $needle"
  done
}
must_say pr-review "$PRR" "\$ARGUMENTS" "headRefOid" "author_association" "Bash(gh pr reopen:*)"
step_says Gate "" "untrusted" "Static review only" "nothing of that PR runs" "--limit 1000" "requested" \
  "one round of questions" "needs no declaration" "never declare \`trivial\`"
step_says Checkout checkout "one PR at a time" "--detach" ".seams-pr-review" "merge-base" \
  "once, before the first pull request's checkout" "earlier outputs" "a stale review can never stand in"
step_says Batch batch "one subagent per PR" "all at once" "--slots" "Every question first" "services" \
  "brew install bash" "the same checks" "facts only" "No review hints" "never asks" "never posts" "error.txt" \
  "--recheck" "alone" "--merge" "never by hand"
# Claude Code's documented subagent limits, in place of 3.2.1's claim that a subagent cannot start subagents
# (lean-and-durable ticket 06): nesting three levels below the main conversation, at most 20 running at once, rate limits on a wide
# fan-out.
step_says Batch batch "three levels below the main conversation" "At most 20 subagents run at once" \
  "Concurrent subagent limit reached" "rate limits"
grep -rqiE "(nor|cannot|can't|can not) start subagents" "$PRR" "$PRR_REFS" && fail "pr-review still says a subagent cannot start subagents"
step_says Understand understand-and-review "mergeable" "CONFLICTING" "blocking finding"
step_says Checks checks "once per repository" "run_checks.py" "commands CI runs" "git hooks" ".husky" \
  "core.hooksPath" "named like checks" "could not run" "bash 4" "compare the failing tests by name" "E2E" "Try it" "own port"
step_says Review understand-and-review "Invoke \`code-review\`" "risk reviewer" "Verify every finding" "baseline" "probe test" \
  "Under static review, run nothing from the pull request" "blocking" "should fix" "request changes" "merges cleanly" \
  "\$EVID/probes/" "after that tree's checks"
step_says Draft draft-and-post "review_payload.py" "review.json" "outside the diff" "footer" "without \`--checks\` under static review"
step_says Cleanup cleanup "only worktrees carrying" "the one record from Checkout" \
  "never deleted with the tree" "matt-pocock-workflow:verification-before-completion"
step_says Post draft-and-post "Re-check the candidate" "every time" "Don't post" "own pull request" "post_reviews.py" \
  "needs no new yes" "stops" "Never push"
step_says "Review handover" "" "batch_report.py" "Ready to merge" "Note for" "exactly as the script wrote it"
# A step's gates and must-nots stay in the core where its detail moved out (the ticket's "gates, must-nots and steps
# first"): an unmarked evidence directory, services and credentials, a head that moved, the viewer's own pull request.
section_says pr-review "$PRR" Checkout "without the marker"
section_says pr-review "$PRR" Checks "only after a yes" "real credentials, paid APIs and production data are never used"
section_says pr-review "$PRR" Post "whose head moved is not posted" "only \`COMMENT\`"
# A headless run asks its post question in text, and the answer starts a turn the scripts' pre-approval no longer
# covers: the handover's table comes first, while it holds.
step_says Post draft-and-post "while the pre-approval holds"
# The pre-approval also ends when the session waits on background work: the live run on 8fbdca2 put run_checks.py
# and the risk reviewer in the background, and review_payload.py was refused in the turn their notifications began.
# So a single review runs its scripts and its reviewers in the foreground, and a batch says its fan-out ends the turn.
[[ $PRR_OPENING == *"in the foreground"* ]] || fail "pr-review's opening does not say to keep its scripts and subagents in the foreground"
step_says Checks checks "in the foreground"
step_says Review understand-and-review "in the foreground, in the same message as"
step_says Batch batch "The fan-out ends this turn"
# Its four scripts run without a permission prompt from any directory (lean-and-durable ticket 06): the core runs each as
# `python3 ${CLAUDE_SKILL_DIR}/scripts/<name>.py` and its allowed-tools pre-approves exactly that command, as the skills
# docs show. Claude Code fills in ${CLAUDE_SKILL_DIR} only in SKILL.md and its allowed-tools, so a reference writes a
# path in the skill as <skill-dir>/..., which the core defines, and nothing names the directory the old way.
PRR_FRONT=$(awk 'NR > 1 && /^---$/ {exit} NR > 1' "$PRR")
PRR_BODY=$(awk 'body; NR > 1 && /^---$/ {body = 1}' "$PRR")
for s in run_checks review_payload batch_report post_reviews; do
  [[ -x "$PLUGIN/skills/pr-review/scripts/$s.py" ]] || fail "pr-review/scripts/$s.py missing or not executable"
  grep -qxF -- "  - Bash(python3 \${CLAUDE_SKILL_DIR}/scripts/$s.py *)" <<< "$PRR_FRONT" \
    || fail "pr-review's allowed-tools does not pre-approve: Bash(python3 \${CLAUDE_SKILL_DIR}/scripts/$s.py *)"
  [[ $PRR_BODY == *"\`python3 \${CLAUDE_SKILL_DIR}/scripts/$s.py\`"* ]] \
    || fail "pr-review's core does not name its script as: python3 \${CLAUDE_SKILL_DIR}/scripts/$s.py"
done
[[ $PRR_OPENING == *"\`<skill-dir>\`"* ]] || fail "pr-review's opening does not say what <skill-dir> in its references stands for"
grep -F -- "\${CLAUDE_SKILL_DIR}/" "$PRR_REFS"/*.md && fail "a pr-review reference names a path through \${CLAUDE_SKILL_DIR}, which is not filled in there"
grep -rF -- "this skill's base directory" "$PRR" "$PRR_REFS" && fail "pr-review still names its directory as \"this skill's base directory\""
must_say routing.md "$PLUGIN/skills/using-matt-pocock-skills/references/routing.md" "/matt-pocock-workflow:pr-review"

# The trivial declaration: the cheap way through the gate, carrying the test of what is not trivial.
TRIV="$PLUGIN/skills/trivial/SKILL.md"
[[ -f "$TRIV" ]] || fail "trivial skill missing"
for needle in "behavior" "data" "auth" "migration" "verification-before-completion" "grill" "diagnosing-bugs"; do
  grep -qi "$needle" "$TRIV" || fail "trivial skill should mention: $needle"
done

# The Superpowers-overlap rule lives in routing.md, not in the bootstrap: ticket 03 moved it there to
# keep the injection within budget, and the gate enforces the precedence either way.
ROUTING="$PLUGIN/skills/using-matt-pocock-skills/references/routing.md"
must_say routing.md "$ROUTING" "If Superpowers is also enabled, these win" "not a declaration"
grep -qF "If Superpowers is also enabled" "$PLUGIN/skills/using-matt-pocock-skills/SKILL.md" \
  && fail "the Superpowers-overlap sentence is back in the bootstrap; it belongs in routing.md"
grep -qF "Superpowers overlaps" "$PLUGIN/skills/using-matt-pocock-skills/SKILL.md" \
  || fail "the bootstrap should point at routing.md for the Superpowers overlaps"

# The bootstrap (ticket 07): every Seams skill directory is named in the bootstrap or in routing.md;
# the table routes by risk as well as size (trivial, sensitive at any size, an incident, a new app's
# walking skeleton, a release); one sentence states the gate and the done-check; a yes covering
# later steps is not asked again while deploy and publish always ask; the two anchor red flags stay.
BOOT="$PLUGIN/skills/using-matt-pocock-skills/SKILL.md"
NAMED="$(cat "$BOOT" "$ROUTING")"
for d in "$PLUGIN"/skills/*/; do
  s=$(basename "$d"); [[ $s == using-matt-pocock-skills ]] && continue
  [[ $NAMED == *"\`$s\`"* || $NAMED == *"matt-pocock-workflow:$s"* ]] || fail "Seams skill named neither in the bootstrap nor in routing.md: $s"
done
must_say bootstrap "$BOOT" "| Trivial" "\`trivial\`*" "| Sensitive" "any size" "anything destructive" "\`grill\`* on the security and failure axes" "its size row" \
  "\`code-review\` required" "\`incident\`*" "\`release\`*" "walking skeleton" "A hook refuses" "\`verification-before-completion\`*" \
  "a yes covering later steps is not asked again" "deploy and publish always ask" "\"it's a quick fix\"" "\"the requirements are clear\""
grep -qF "config, rename" "$BOOT" && fail "the trivial row still lists config and rename without a qualifier"
# The bootstrap states the routing as the project's facts (lean-and-durable ticket 08): every row of the table as it
# was, every rule, and the quality bar, with nothing addressed to the reader ("you", "your") and no pseudo-tags.
BOOT_ROWS=(
  "| Trivial: copy, typo, comment, unobservable rename | \`trivial\`* |"
  "| Broken, failing, throwing, slow | \`diagnosing-bugs\`, even when the fix looks obvious |"
  "| Bounded change to existing code | \`grill\`*, \`tdd\` |"
  "| New behavior in one session | \`grill\`* + \`domain-modeling\`, then \`implement\`* |"
  "| Several sessions, or a new app | \`grill\`*, \`to-spec\`*, \`to-tickets\`*, \`implement\`* per ticket; a new app's ticket 01 is the walking skeleton |"
  "| Sensitive, any size: auth, permissions, secrets, billing, migrations, infra, CI or deploy config, public API, anything destructive | its size row's move, \`grill\`* on the security and failure axes first, \`code-review\` required |"
  "| Down or degraded for users now | \`incident\`* |"
  "| Ship, deploy, release, publish | \`release\`* |")
for row in "${BOOT_ROWS[@]}"; do grep -qxF -- "$row" "$BOOT" || fail "the bootstrap lost a routing row: $row"; done
must_say bootstrap "$BOOT" "Development work in this project" "a 1% chance" "the lower" "moves down, never up" \
  "AskUserQuestion, recommended answer first" "Seams are settled in the grill" "\`tdd\` and \`to-spec\` do not ask again" \
  "\`code-review\` runs on features and builds" "offered on bounded changes and bugs" "one context" "references/routing.md" \
  "\`finishing-a-development-branch\`*" "**Quality bar.**" "fails, is attacked, performs, is observed, is documented and is rolled back" \
  "each item proven" "nothing is added that nobody asked for"
BOOT_BODY=$(awk 'body; NR > 1 && /^---$/ {body = 1}' "$BOOT")
grep -qiwE "you|your" <<< "$BOOT_BODY" && fail "the bootstrap addresses the reader; it states the project's facts: $(grep -iwE "you|your" <<< "$BOOT_BODY")"
grep -qE "<[A-Z_-]+>" <<< "$BOOT_BODY" && fail "a pseudo-tag in the bootstrap: $(grep -oE "<[A-Z_-]+>" <<< "$BOOT_BODY" | head -1)"
# routing.md carries what moved out of the bootstrap and the rules the spec added: the worktree and
# review-feedback owners, the judgment rule at a phase boundary (no token figure), the named durable
# state, evidence reuse for an unchanged candidate, the greenfield path.
must_say routing.md "$ROUTING" "\`matt-pocock-workflow:using-git-worktrees\`" "\`matt-pocock-workflow:receiving-code-review\`" "Durable state" "\`CONTEXT.md\`" "ADRs" \
  "resumed" "unchanged candidate" "Greenfield" "walking skeleton" "\`/ask-matt\`"
for f in "$ROUTING" "$BOOT"; do grep -qE "[0-9]+k( |-)tokens?" "$f" && fail "a token figure is back in $(basename "$f"); the phase-boundary rule is a judgment rule"; done
# The design lens carries the Sensitive row's rule, and the four gated skills honour rule 4: a yes given
# earlier in the request that covered the step is the yes, while release's deploy question never is.
must_say design-lens "$PLUGIN/skills/grill/references/design-lens.md" "**A sensitive change, at any size**" "security boundaries and failure modes"
for s in to-spec to-tickets implement release; do must_say "$s" "$PLUGIN/skills/$s/SKILL.md" "a yes earlier in this request covered"; done
must_say release "$PLUGIN/skills/release/SKILL.md" "never skipped"

# The three kept Superpowers skills: present, and matching the checksums recorded in the notices.
KEPT="using-git-worktrees verification-before-completion receiving-code-review"
for s in $KEPT; do [[ -f "$PLUGIN/skills/$s/SKILL.md" ]] || fail "missing copied skill: $s"; done
SP_SECTION=$(section Superpowers "$NOTICES")
SP_SUMS=$(grep -E '^[0-9a-f]{64}  skills/[a-z-]+/SKILL\.md$' <<< "$SP_SECTION") \
  || fail "no checksums in the Superpowers section of THIRD_PARTY_NOTICES.md"
[[ $(wc -l <<< "$SP_SUMS") -eq 3 ]] || fail "expected 3 recorded checksums, got: $SP_SUMS"
(cd "$PLUGIN" && shasum -a 256 -c <<< "$SP_SUMS" >/dev/null) || fail "a copied skill differs from its recorded checksum"

# finishing-a-development-branch is Seams' adaptation of the Superpowers original (lean-and-durable ticket 05):
# after a local merge it records integration in the feature's progress file. Its last line attributes the
# original, and the notices record the original's checksum as `shasum -c` checks it in the plugin cache.
FIN="$PLUGIN/skills/finishing-a-development-branch/SKILL.md"
section_says finishing-a-development-branch "$FIN" "Step 5: Execute Choice" "record integration" "\`Stage: integrated\`" \
  "references/progress-file.md" "commit it by name on <base-branch>" "never a secret"
last_line_says finishing-a-development-branch "$FIN" "Superpowers" "6.3.0" "MIT" "Jesse Vincent" "THIRD_PARTY_NOTICES.md"
FIN_SUM=$(grep -E '^[0-9a-f]{64}  finishing-a-development-branch/SKILL\.md$' <<< "$SP_SECTION") \
  || fail "the notices do not record the checksum of finishing-a-development-branch's original"

# ...and the copies identical to the Superpowers 6.3.0 originals whenever that cache is present, which also
# confirms the adapted skill's recorded original.
SP="$HOME/.claude/plugins/cache/claude-plugins-official/superpowers/6.3.0/skills"
if [[ -d "$SP" ]]; then
  for s in $KEPT; do
    cmp -s "$SP/$s/SKILL.md" "$PLUGIN/skills/$s/SKILL.md" || fail "$s differs from Superpowers 6.3.0"
  done
  (cd "$SP" && shasum -a 256 -c <<< "$FIN_SUM" >/dev/null) \
    || fail "the recorded original of finishing-a-development-branch is not Superpowers 6.3.0's"
fi

echo "test_plugin: OK"
