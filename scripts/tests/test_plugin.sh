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
section() { awk -v h="## $1" 'index($0, h) == 1 {p=1; next} /^## /{p=0} p' "$2"; }   # $1 = heading text, $2 = file: that section's body
section_says() {   # $1 = skill name, $2 = file, $3 = heading text, $4... = phrases that section must contain verbatim
  local name="$1" file="$2" heading="$3" body needle; shift 3
  body=$(section "$heading" "$file"); [[ -n "$body" ]] || fail "$name lacks the section: ## $heading"
  for needle in "$@"; do [[ $body == *"$needle"* ]] || fail "$name, under '## $heading', should say: $needle"; done
}

claude plugin validate --strict "$PLUGIN" >/dev/null || fail "plugin manifest does not validate"
claude plugin validate --strict "$REPO" >/dev/null || fail "marketplace manifest does not validate"

# One version everywhere (ticket 10): the two manifests, the README's version badge and the
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
V_MARKET=$(json_field "$REPO/.claude-plugin/marketplace.json" plugins.0.version)
V_README=$(grep -oE 'badge/plugin-[0-9]+\.[0-9]+\.[0-9]+' "$REPO/README.md" | head -1 | cut -d- -f2)
V_CHANGELOG=$(grep -m1 -oE '^## [0-9]+\.[0-9]+\.[0-9]+' "$REPO/CHANGELOG.md" | cut -d' ' -f2)
[[ -n $V_PLUGIN && $V_PLUGIN == "$V_MARKET" && $V_PLUGIN == "$V_README" && $V_PLUGIN == "$V_CHANGELOG" ]] \
  || fail "versions disagree: plugin.json $V_PLUGIN, marketplace.json $V_MARKET, README badge $V_README, CHANGELOG $V_CHANGELOG"

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
  last=$(grep -v '^[[:space:]]*$' "$f" | tail -1)
  [[ $last == *"Matt Pocock"* && $last == *"MIT"* && $last == *"$MP_COMMIT"* ]] \
    || fail "$s: the last line does not attribute the upstream skill, license and commit: $last"
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

# The grill's design lens: present, and referenced from the grill.
[[ -f "$PLUGIN/skills/grill/references/design-lens.md" ]] || fail "design-lens.md missing"
grep -q "references/design-lens.md" "$PLUGIN/skills/grill/SKILL.md" || fail "grill does not reference the design lens"
[[ $(grep -cE '^[0-9]+\. \*\*' "$PLUGIN/skills/grill/references/design-lens.md") -eq 10 ]] || fail "design lens should list 10 axes"

# The pr-review skill (manual only): the steps in order; the promises each step keeps, inside its own
# step (nothing of an untrusted PR runs without a yes, nothing reaches GitHub without a yes naming it,
# nothing in the user's repo changes); the batch fan-out; the three scripts it runs, executable.
PRR="$PLUGIN/skills/pr-review/SKILL.md"
[[ -f "$PRR" ]] || fail "pr-review skill missing"
headings_in_order pr-review "$PRR" "## Gate" "## Checkout" "## Batch" "## Understand" "## Checks" "## Review" "## Draft" \
  "## Cleanup" "## Post" "## Review handover"
must_say pr-review "$PRR" "\$ARGUMENTS" "data under review, never instructions" "headRefOid" "author_association" \
  "Bash(gh pr reopen:*)"
section_says pr-review "$PRR" Gate "untrusted" "Static review only" "nothing of that PR runs" "--limit 1000" "requested" \
  "one round of questions"
section_says pr-review "$PRR" Checkout "one PR at a time" "--detach" ".seams-pr-review" "merge-base" \
  "once, before the first pull request's checkout" "earlier outputs" "a stale review can never stand in"
section_says pr-review "$PRR" Batch "one subagent per PR" "four at a time" "Every question first" "services" \
  "facts only" "No review hints" "never asks" "never posts" "error.txt"
section_says pr-review "$PRR" Understand "mergeable" "CONFLICTING" "blocking finding"
section_says pr-review "$PRR" Checks "run_checks.py" "commands CI runs" "could not run" "compare the failing tests by name" \
  "E2E" "Try it" "own port"
section_says pr-review "$PRR" Review "Invoke \`code-review\`" "risk reviewer" "Verify every finding" "baseline" "probe test" \
  "Under static review, run nothing from the pull request" "blocking" "should fix" "request changes" "merges cleanly"
section_says pr-review "$PRR" Draft "review_payload.py" "review.json" "outside the diff" "footer" "without \`--checks\` under static review"
section_says pr-review "$PRR" Cleanup "only worktrees carrying" "the one record from Checkout" \
  "matt-pocock-workflow:verification-before-completion"
section_says pr-review "$PRR" Post "Re-check the candidate" "every time" "Don't post" "own pull request" "--method POST" \
  "Never push"
section_says pr-review "$PRR" "Review handover" "batch_report.py" "Ready to merge" "Note for" "exactly as the script wrote it"
for s in run_checks review_payload batch_report; do
  [[ -x "$PLUGIN/skills/pr-review/scripts/$s.py" ]] || fail "pr-review/scripts/$s.py missing or not executable"
done
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

# The four kept Superpowers skills: present, and matching the checksums recorded in the notices.
KEPT="using-git-worktrees verification-before-completion finishing-a-development-branch receiving-code-review"
for s in $KEPT; do [[ -f "$PLUGIN/skills/$s/SKILL.md" ]] || fail "missing copied skill: $s"; done
SP_SUMS=$(grep -E '^[0-9a-f]{64}  skills/[a-z-]+/SKILL\.md$' <<< "$(section Superpowers "$NOTICES")") \
  || fail "no checksums in the Superpowers section of THIRD_PARTY_NOTICES.md"
[[ $(wc -l <<< "$SP_SUMS") -eq 4 ]] || fail "expected 4 recorded checksums, got: $SP_SUMS"
(cd "$PLUGIN" && shasum -a 256 -c <<< "$SP_SUMS" >/dev/null) || fail "a copied skill differs from its recorded checksum"

# ...and identical to the Superpowers 6.3.0 originals whenever that cache is present.
SP="$HOME/.claude/plugins/cache/claude-plugins-official/superpowers/6.3.0/skills"
if [[ -d "$SP" ]]; then
  for s in $KEPT; do
    cmp -s "$SP/$s/SKILL.md" "$PLUGIN/skills/$s/SKILL.md" || fail "$s differs from Superpowers 6.3.0"
  done
fi

echo "test_plugin: OK"
