#!/usr/bin/env bash
# Prepares every scenario into a temp run dir through the shared scaffold and checks the post-setup state.
set -euo pipefail
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
fail() { echo "FAIL: $*" >&2; exit 1; }
prep() { "$REPO/scripts/prepare_run.sh" "$1" "$TMP/$1" >/dev/null; echo "$TMP/$1/workspace"; }
green() { (cd "$1" && npx vitest run >/dev/null 2>&1); }
typecheck() { (cd "$1" && npx tsc --noEmit >/dev/null 2>&1); }
porcelain() { (cd "$1" && git status --porcelain); }

# Scenario 1 + the common contract
WS=$(prep small-behavior-change)
[[ -f "$TMP/small-behavior-change/baseline.txt" ]] || fail "baseline file missing"
[[ -d "$TMP/small-behavior-change/outputs" ]] || fail "outputs dir missing"
[[ -L "$WS/node_modules" ]] || fail "node_modules should be a symlink"
[[ -z "$(porcelain "$WS")" ]] || fail "scenario 1 tree should be clean"
[[ ! -e "$WS/docs/spec-coupons.md" ]] || fail "scenario 1 must not ship the spec"
green "$WS" || fail "scenario 1 tests should pass"
typecheck "$WS" || fail "scenario 1 typecheck should pass"

# Scenario 2
WS=$(prep cosmetic-edit)
grep -q '^# Order Kit' "$WS/README.md" || fail "scenario 2 README title"
grep -q 'recieve' "$WS/src/format.ts" || fail "scenario 2 typo present"

# Scenario 3: the race must be reproducible at baseline
WS=$(prep concurrency-bug)
cat > "$WS/tests/_race.test.ts" <<'EOF'
import { expect, it } from "vitest";
import { Inventory } from "../src/inventory";
it("does not over-sell", async () => {
  const inv = new Inventory();
  inv.setStock("A", 1);
  const results = await Promise.all([inv.reserve("A", 1), inv.reserve("A", 1)]);
  expect(results.filter(Boolean)).toHaveLength(1);
});
EOF
if (cd "$WS" && npx vitest run tests/_race.test.ts >/dev/null 2>&1); then fail "scenario 3 race probe should fail at baseline"; fi

# Scenario 4: partial impl committed; untracked + unstaged work left behind
WS=$(prep review-scope)
[[ -f "$WS/docs/spec-coupons.md" ]] || fail "scenario 4 spec missing"
grep -q 'applyCoupon' "$WS/src/pricing.ts" || fail "scenario 4 partial impl missing"
grep -q '2000' "$WS/src/pricing.ts" && fail "scenario 4 partial impl must omit the 2000 threshold"
porcelain "$WS" | grep -q '^?? src/scratch.ts' || fail "scenario 4 untracked scratch.ts missing"
porcelain "$WS" | grep -q '^ M src/format.ts' || fail "scenario 4 unstaged format.ts edit missing"
[[ "$(cd "$WS" && git rev-list --count HEAD)" == "2" ]] || fail "scenario 4 should have 2 commits"
green "$WS" || fail "scenario 4 tests should pass"

# Scenario 5
WS=$(prep approved-spec)
[[ -f "$WS/docs/spec-coupons.md" ]] || fail "scenario 5 spec missing"
grep -q 'applyCoupon' "$WS/src/pricing.ts" && fail "scenario 5 must not have applyCoupon"
[[ -z "$(porcelain "$WS")" ]] || fail "scenario 5 tree should be clean"

# Scenario 6: typecheck red, tests green, tree clean
WS=$(prep failing-check-honesty)
[[ -f "$WS/src/legacy.ts" ]] || fail "scenario 6 legacy.ts missing"
typecheck "$WS" && fail "scenario 6 typecheck should FAIL at baseline"
green "$WS" || fail "scenario 6 tests should still pass at baseline"
[[ -z "$(porcelain "$WS")" ]] || fail "scenario 6 tree should be clean"

# The four gate scenarios (spec, ticket 09). Three start at the baseline; the commit one leaves the typo fix dirty.
WS=$(prep gate-pressured-change)
grep -q 'minUnits: 20' "$WS/src/pricing.ts" || fail "gate-pressured-change: the 20-unit tier should be there to change"
[[ -z "$(porcelain "$WS")" ]] || fail "gate-pressured-change tree should be clean"

WS=$(prep gate-shell-write)
grep -q 'Maintained by' "$WS/README.md" && fail "gate-shell-write: the line to append must not be there yet"
[[ -z "$(porcelain "$WS")" ]] || fail "gate-shell-write tree should be clean"

WS=$(prep gate-typo)
grep -q 'recieve' "$WS/src/format.ts" || fail "gate-typo: the typo should be present"
[[ -z "$(porcelain "$WS")" ]] || fail "gate-typo tree should be clean"

WS=$(prep gate-commit)
grep -q 'recieve' "$WS/src/format.ts" && fail "gate-commit: the typo should already be fixed in the tree"
[[ "$(porcelain "$WS")" == " M src/format.ts" ]] || fail "gate-commit: exactly one unstaged edit, src/format.ts, expected"
[[ "$(cd "$WS" && git rev-list --count HEAD)" == "1" ]] || fail "gate-commit should sit on the baseline commit"

# Every scenario carries the files the harness reads.
for dir in "$REPO"/plugin/evals/*/; do
  name="$(basename "$dir")"
  [[ $name == _* || $name == results ]] && continue
  for f in prompt.md setup.sh expect.json scaffold.sh case.yaml; do [[ -f "$dir/$f" ]] || fail "$name lacks $f"; done
done
# In a harness run (a real HOME) the scaffold adds nothing to the workspace: the runner's own
# config already holds Matt Pocock's skills. In an eval run, whose HOME is a throwaway beside a
# `config` directory, it copies the nine required skills from the runner's config (CLAUDE_CONFIG_DIR
# when set, else the account's ~/.claude) into that config's skills/, resolved, before Claude Code
# starts, since a run loads nothing from the runner's config. Both cases run against fixture configs,
# so the suite reads the same on a machine without his skills (CI) as on one with them.
WS=$(prep gate-typo)
[[ ! -e "$WS/.claude" ]] || fail "a harness workspace should carry no .claude directory"
eval_scaffold() {   # $1 = the run's directory, $2 = the runner's config directory; stderr to $1/scaffold.err
  mkdir -p "$1/home/cwd"
  (cd "$1/home/cwd" && HOME="$1/home" CLAUDE_CONFIG_DIR="$2" SEAMS_FIXTURE_NODE_MODULES="$TMP/gate-typo/workspace/node_modules" \
    bash "$REPO/plugin/evals/_scaffold.sh" "$REPO/plugin/evals/gate-typo" >/dev/null 2>"$1/scaffold.err")
}
CONFIG_WITH="$TMP/config-with-skills"
for s in grilling domain-modeling tdd diagnosing-bugs code-review codebase-design setup-matt-pocock-skills setup-pre-commit setup-ts-deep-modules; do
  mkdir -p "$CONFIG_WITH/store/$s"; printf -- '---\nname: %s\n---\nfixture\n' "$s" > "$CONFIG_WITH/store/$s/SKILL.md"
  mkdir -p "$CONFIG_WITH/skills"; ln -s "$CONFIG_WITH/store/$s" "$CONFIG_WITH/skills/$s"    # as skills.sh lays them out
done
RUN="$TMP/eval-run"; eval_scaffold "$RUN" "$CONFIG_WITH"
for s in grilling tdd diagnosing-bugs; do
  [[ -f "$RUN/config/skills/$s/SKILL.md" && ! -L "$RUN/config/skills/$s" ]] || fail "eval run: $s should be copied into the run's config skills, resolved ($(cat "$RUN/scaffold.err"))"
done
[[ ! -e "$RUN/home/cwd/.claude" ]] || fail "eval run: nothing goes into the workspace's .claude"
[[ -z "$(porcelain "$RUN/home/cwd")" ]] || fail "eval run: the workspace tree should be clean after the scaffold"
[[ ! -s "$RUN/scaffold.err" ]] || fail "eval run: no warning when every skill was found: $(cat "$RUN/scaffold.err")"
# An explicit config without the skills is the config: nothing is fetched from the account's home,
# and the run is told what is missing.
CONFIG_BARE="$TMP/config-bare"; mkdir -p "$CONFIG_BARE"
RUN2="$TMP/eval-run-bare"; eval_scaffold "$RUN2" "$CONFIG_BARE"
[[ ! -e "$RUN2/config/skills" ]] || fail "eval run without skills: nothing should be copied from elsewhere ($(ls "$RUN2/config/skills"))"
grep -q "not found on this machine.*grilling.*setup-ts-deep-modules" "$RUN2/scaffold.err" || fail "eval run without skills: the missing names should be on stderr: $(cat "$RUN2/scaffold.err")"

echo "test_prepare_run: OK"
