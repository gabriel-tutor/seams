#!/usr/bin/env bash
# Static checks on the plugin, held to the contracts Claude Code and the routing rely on (seams-revamp ticket 03):
# the manifests validate and nothing stray ships; the version has one source; the frontmatter fields Claude Code
# reads, scout's model the only pin; the size bounds of the skills, their references and the listing, and the paths a
# skill gives Claude, the shared rules' sections among them; no skill injects a shell command; the routing table's rows;
# the continuous flow's stops (ticket 06); the process table's floor and the docs rule (ticket 07); the third-party
# notices and the copies' checksums. No other check pins a skill's or the README's wording: rewording a sentence that
# changes none of these leaves it green.
set -euo pipefail
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PLUGIN="$REPO/plugin"
KEPT="using-git-worktrees verification-before-completion receiving-code-review"   # the Superpowers copies, byte-identical
fail() { echo "FAIL: $*" >&2; exit 1; }
last_line_says() {   # $1 = skill name, $2 = file, $3... = phrases its last non-blank line, the attribution, must contain
  local name="$1" file="$2" last needle; shift 2
  last=$(grep -v '^[[:space:]]*$' "$file" | tail -1)
  for needle in "$@"; do [[ $last == *"$needle"* ]] || fail "$name: the last line does not attribute the original ($needle): $last"; done
}
section() { awk -v h="## $1" 'index($0, h) == 1 {p=1; next} /^## /{p=0} p' "$2"; }   # $1 = heading text, $2 = file: that section's body
plugin_guards() {   # $1 = a plugin directory: a line for each SKILL.md over its bound (11,000 bytes; pr-review 11,200), each
                    # reference over 16,000 bytes, each effort pin, and each model pin but scout's `sonnet`
  python3 - "$1" <<'PY'
import pathlib, re, sys
root = pathlib.Path(sys.argv[1])
skills = sorted(root.glob("skills/*/SKILL.md"))
agents = sorted(root.glob("agents/**/*.md"))
bounds = {"pr-review": 11200}   # its core measures about 3.5k tokens on invoke (.scratch/pr-review-invocable decision 10)
models = {"scout": "sonnet"}    # seams-revamp decision 17: fact-finding on Sonnet; every other agent, and every skill, on the session's
sized = [(path, bounds.get(path.parent.name, 11000)) for path in skills]
sized += [(path, 16000) for path in sorted(root.glob("skills/*/references/*.md"))]
for path, bound in sized:
    if path.stat().st_size > bound:
        print(f"{path.relative_to(root)} is {path.stat().st_size} bytes, over the {bound:,}-byte bound")
for path in skills + agents:
    front = re.match(r"---\n(.*?)\n---\n", path.read_text(), re.S)
    fields = {k.strip(): v.strip() for k, v in (line.split(":", 1) for line in (front.group(1) if front else "").splitlines()
                                                if ":" in line and line[:1].isalpha())}
    want = models.get(path.stem) if path in agents else None
    if want and fields.get("model") != want:
        print(f"{path.relative_to(root)} declares model {fields.get('model', 'none')}, expected {want}")
    elif not want and "model" in fields:
        print(f"{path.relative_to(root)} sets model")
    if "effort" in fields:
        print(f"{path.relative_to(root)} sets effort")
PY
}
injected_commands() {   # $1 = a plugin directory: a line for each SKILL.md that injects a shell command
  python3 - "$1" <<'PY'
import pathlib, re, sys
root = pathlib.Path(sys.argv[1])
for path in sorted(root.glob("skills/*/SKILL.md")):
    name, text = path.relative_to(root), path.read_text()
    for cmd in re.findall(r"(?:^|(?<=\s))!`([^`]*)`", text, re.M):   # Claude Code runs !` at a line start or after whitespace
        print(f"{name} injects a shell command: !`{cmd}`")
    if re.search(r"(```|~~~)!", text):                               # any fence opened with !, anywhere in a line
        print(f"{name} injects a fenced block of shell commands")
PY
}

# Manifest validation needs the claude CLI, which CI does not install; every other check here is plain bash and Python
# and runs everywhere (lean-and-durable ticket 08: CI had skipped this whole file, so no static guard held there).
if command -v claude >/dev/null; then
  claude plugin validate --strict "$PLUGIN" >/dev/null || fail "plugin manifest does not validate"
  claude plugin validate --strict "$REPO" >/dev/null || fail "marketplace manifest does not validate"
else
  echo "skipped: manifest validation (no claude CLI)"      # the runner shows this line, so it is never silent
fi

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
# every skill but the ones typed by hand only, listed here. None is: pr-review was until 3.3.1, when workflow
# skills needed to start it.
USER_ONLY=""
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

# The three flow skills are Seams' own adaptations of Matt Pocock's (ADR-0002), under the MIT license: each one's last
# line attributes the upstream skill, the license and the commit recorded in the notices.
NOTICES="$PLUGIN/THIRD_PARTY_NOTICES.md"
MP_SECTION=$(section "Matt Pocock" "$NOTICES")
[[ -n "$MP_SECTION" ]] || fail "no 'Matt Pocock' section in THIRD_PARTY_NOTICES.md"
MP_COMMIT=$(grep -oE '\b[0-9a-f]{40}\b' <<< "$MP_SECTION" | sort -u) || fail "the notices name no upstream commit"
[[ $(wc -l <<< "$MP_COMMIT") -eq 1 ]] || fail "the notices should name one upstream commit, got: $MP_COMMIT"
for s in to-spec to-tickets implement; do
  last_line_says "$s" "$PLUGIN/skills/$s/SKILL.md" "Matt Pocock" "MIT" "$MP_COMMIT"
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

# The paths a skill gives Claude resolve: each one through ${CLAUDE_SKILL_DIR} or ${CLAUDE_PLUGIN_ROOT}, which Claude
# Code fills in when the skill loads (to a file, or a directory before a glob or a <placeholder>), and each bare
# references/<name>.md, which Claude reads beside the skill. Claude Code fills those two in only in a SKILL.md and its
# allowed-tools, so no reference names a path through them. A pointer into the shared rules (seams-revamp ticket 07),
# "(shared rules: Evidence)", names a section the rules have, so a step that sends Claude there finds what it needs. A
# fixture breaking each rule, beside pointers that hold, shows the check catching what it is for.
pointer_problems() {   # $1 = a plugin directory: a line for each pointer that does not resolve, or that is not filled in
  python3 - "$1" <<'PY'
import pathlib, re, sys
root = pathlib.Path(sys.argv[1])
VARIABLE = re.compile(r"\$\{(CLAUDE_SKILL_DIR|CLAUDE_PLUGIN_ROOT)\}/([^\s`'\"()\[\]<>*!#,;:]+)")   # ends at a glob, an anchor or a <placeholder>
BARE = re.compile(r"(?<![\w/.}-])(references/[\w.-]+\.md)")
for path in sorted(root.glob("skills/*/SKILL.md")):
    name, text = path.relative_to(root), path.read_text()
    pointers = [(f"${{{var}}}/{rel.rstrip('.')}", (path.parent if var == "CLAUDE_SKILL_DIR" else root) / rel.rstrip("."))
                for var, rel in VARIABLE.findall(text)]
    pointers += [(rel, path.parent / rel) for rel in BARE.findall(text)]
    for pointer, target in pointers:
        if not target.exists():                                  # a file, or a directory it names
            print(f"{name} points at {pointer}, which is not in the plugin")
for path in sorted(root.glob("skills/*/references/*.md")):
    for var in sorted(set(var for var, _ in VARIABLE.findall(path.read_text()))):
        print(f"{path.relative_to(root)} names a path through ${{{var}}}, which Claude Code fills in only in a SKILL.md")
RULES = root / "skills/using-matt-pocock-skills/references/rules.md"
sections = set(re.findall(r"(?m)^## (.+?)\s*$", RULES.read_text())) if RULES.is_file() else set()
for path in sorted(root.glob("skills/*/SKILL.md")) + sorted(root.glob("skills/*/references/*.md")):
    for names in re.findall(r"\(shared rules: ([^)]+)\)", path.read_text()):
        for section in names.split(", "):
            if section not in sections:
                print(f"{path.relative_to(root)} points at the shared rules' {section}, which rules.md has no section for")
PY
}
PTR_FIX=$(mktemp -d); mkdir -p "$PTR_FIX"/skills/{a,b,using-matt-pocock-skills}/references "$PTR_FIX/skills/a/scripts" "$PTR_FIX/hooks"
printf '# Shared rules\n\n## Evidence\n\nx\n\n## Process by size and risk\n\nx\n' > "$PTR_FIX/skills/using-matt-pocock-skills/references/rules.md"
printf -- '---\nname: a\ndescription: x\n---\n\n%s\n' \
  'Read `${CLAUDE_SKILL_DIR}/references/here.md`, then `${CLAUDE_SKILL_DIR}/references/missing.md`.' \
  'Shared: ${CLAUDE_PLUGIN_ROOT}/skills/b/references/gone.md and ${CLAUDE_PLUGIN_ROOT}/skills/b/references/there.md.' \
  'Pre-approved as `Bash(python3 ${CLAUDE_SKILL_DIR}/scripts/*)`; the hooks are in ${CLAUDE_PLUGIN_ROOT}/hooks/; see [it](${CLAUDE_SKILL_DIR}/references/here.md#top).' \
  'Beside it: `references/here.md` (next to this file), and `references/lost.md`.' \
  'Inside the references, `<skill-dir>` is `${CLAUDE_SKILL_DIR}`; a script runs as `${CLAUDE_SKILL_DIR}/scripts/<name>.py`.' \
  'Reuse it (shared rules: Evidence), scaled (shared rules: Process by size and risk, Evidence), cited (shared rules: Docs).' \
  > "$PTR_FIX/skills/a/SKILL.md"
printf 'Run `python3 ${CLAUDE_SKILL_DIR}/scripts/x.py`; here `${CLAUDE_SKILL_DIR}` stands for the skill.\n' > "$PTR_FIX/skills/a/references/here.md"
printf 'See ${CLAUDE_PLUGIN_ROOT}/skills/a/SKILL.md (shared rules: Stages).\n' > "$PTR_FIX/skills/b/references/there.md"
PTR_OUT=$(pointer_problems "$PTR_FIX"); rm -rf "$PTR_FIX"
for want in "skills/a/SKILL.md points at \${CLAUDE_SKILL_DIR}/references/missing.md" \
  "skills/a/SKILL.md points at \${CLAUDE_PLUGIN_ROOT}/skills/b/references/gone.md" "skills/a/SKILL.md points at references/lost.md" \
  "skills/a/references/here.md names a path through \${CLAUDE_SKILL_DIR}" \
  "skills/b/references/there.md names a path through \${CLAUDE_PLUGIN_ROOT}" \
  "skills/a/SKILL.md points at the shared rules' Docs, which rules.md has no section for" \
  "skills/b/references/there.md points at the shared rules' Stages, which rules.md has no section for"; do
  [[ $PTR_OUT == *"$want"* ]] || fail "the pointer check missed: $want (it said: $PTR_OUT)"
done
[[ $(wc -l <<< "$PTR_OUT") -eq 7 ]] || fail "the pointer check flagged a pointer that resolves: $PTR_OUT"
PTR_OUT=$(pointer_problems "$PLUGIN")
[[ -z $PTR_OUT ]] || fail "$PTR_OUT"

# Every skill stays whole in what compaction keeps of an invoked skill (lean-and-durable ticket 08): at most 11,000
# bytes, about 4,000 tokens (the spec's bound, calibrated from `claude plugin details`). No skill or agent pins an effort
# level, and no skill a model: a pin overrides the level the user chose, both ways, and a model that differs from the
# session's costs a prompt-cache miss. The one model pin is scout's `sonnet` (seams-revamp decision 17): fact-finding runs
# on Sonnet, which the alias makes Sonnet 5.5 on the Anthropic API from Claude Code 2.1.284 and the provider's own Sonnet
# elsewhere (code.claude.com/docs/en/model-config, "Model aliases"; a full model ID would fail where a provider lacks
# it); reviewer, where quality decides, keeps the session's model. A fixture that breaks each rule shows the guard
# catching what it is for.
GUARD_FIX=$(mktemp -d); mkdir -p "$GUARD_FIX"/skills/{big,at-bound,pinned} "$GUARD_FIX/agents" "$GUARD_FIX/skills/big/references"
# A reference is read whole with the Read tool each time its step comes, and again after a compaction, which keeps none
# of it: at most 16,000 bytes, about 5,800 tokens at the calibration above, with room over the largest
# (implement's parallel.md, 13,147 bytes at 3.4.0).
printf '%*s' 16000 '' > "$GUARD_FIX/skills/big/references/at-bound.md"
printf '%*s' 16001 '' > "$GUARD_FIX/skills/big/references/long.md"
# pr-review may take 11,200 bytes (3.3.1, .scratch/pr-review-invocable decision 10): its core measures about 3.5k
# tokens on invoke by `claude plugin details`, well under the 4,000-token cap the bound stands for. Both sides of it:
GUARD_BIG=$(mktemp -d); mkdir -p "$GUARD_BIG/skills/pr-review"
for s in big at-bound; do
  printf -- '---\nname: %s\ndescription: x\n---\n' "$s" > "$GUARD_FIX/skills/$s/SKILL.md"
  n=$(( $([[ $s == big ]] && echo 11001 || echo 11000) - $(wc -c < "$GUARD_FIX/skills/$s/SKILL.md") ))
  printf '%*s' "$n" '' >> "$GUARD_FIX/skills/$s/SKILL.md"
done
printf -- '---\nname: pinned\ndescription: x\nmodel: claude-opus-5\neffort: high\n---\n' > "$GUARD_FIX/skills/pinned/SKILL.md"
printf -- '---\nname: scout\ndescription: x\neffort: low\n---\n' > "$GUARD_FIX/agents/scout.md"
printf -- '---\nname: reviewer\ndescription: x\nmodel: sonnet\n---\n' > "$GUARD_FIX/agents/reviewer.md"
printf -- '---\nname: fine\ndescription: x\n---\n\nmodel: effort: lines in the body are not frontmatter\n' > "$GUARD_FIX/agents/fine.md"
GUARD_SCOUT=$(mktemp -d); mkdir -p "$GUARD_SCOUT/agents"   # scout on another model, and scout as decision 17 has it
printf -- '---\nname: scout\ndescription: x\nmodel: claude-opus-5-5\n---\n' > "$GUARD_SCOUT/agents/scout.md"
OUT_OTHER=$(plugin_guards "$GUARD_SCOUT")
printf -- '---\nname: scout\ndescription: x\nmodel: sonnet\n---\n' > "$GUARD_SCOUT/agents/scout.md"
OUT_SCOUT=$(plugin_guards "$GUARD_SCOUT"); rm -rf "$GUARD_SCOUT"
[[ $OUT_OTHER == "agents/scout.md declares model claude-opus-5-5, expected sonnet" ]] || fail "the guard missed scout on another model: $OUT_OTHER"
[[ -z $OUT_SCOUT ]] || fail "the guard flagged scout on sonnet: $OUT_SCOUT"
GUARD_OUT=$(plugin_guards "$GUARD_FIX"); rm -rf "$GUARD_FIX"
for size in 11200 11201; do
  printf -- '---\nname: pr-review\ndescription: x\n---\n' > "$GUARD_BIG/skills/pr-review/SKILL.md"
  printf '%*s' "$(( size - $(wc -c < "$GUARD_BIG/skills/pr-review/SKILL.md") ))" '' >> "$GUARD_BIG/skills/pr-review/SKILL.md"
  OUT_BIG=$(plugin_guards "$GUARD_BIG")
  if [[ $size == 11200 ]]; then [[ -z $OUT_BIG ]] || fail "pr-review at its 11,200-byte allowance was flagged: $OUT_BIG"
  else [[ $OUT_BIG == *"skills/pr-review/SKILL.md is 11201 bytes, over the 11,200-byte bound"* ]] || fail "pr-review over its allowance was missed: $OUT_BIG"; fi
done; rm -rf "$GUARD_BIG"
for want in "skills/big/SKILL.md is 11001 bytes, over the 11,000-byte bound" "skills/pinned/SKILL.md sets model" \
  "skills/pinned/SKILL.md sets effort" "agents/scout.md sets effort" "agents/scout.md declares model none, expected sonnet" \
  "agents/reviewer.md sets model" "skills/big/references/long.md is 16001 bytes, over the 16,000-byte bound"; do
  [[ $GUARD_OUT == *"$want"* ]] || fail "the guard missed: $want (it said: $GUARD_OUT)"
done
[[ $GUARD_OUT != *at-bound* && $GUARD_OUT != *fine* ]] || fail "the guard flagged a file within its rules: $GUARD_OUT"
GUARD_OUT=$(plugin_guards "$PLUGIN")
[[ -z $GUARD_OUT ]] || fail "$GUARD_OUT"
# No skill injects a shell command (lean-and-durable ticket 10, decision 33). Claude Code runs a SKILL.md's !`cmd` lines
# and its ```! blocks through the Bash tool before Claude sees the skill, and in a session without that tool (a plugin
# eval's, --restricted, a Bash deny rule) the invocation aborts: a probe on 2.1.282 with `--tools` without Bash got
# "Permission to use Bash has been denied" and no skill. New output on each invocation would also make a re-invocation
# append the whole skill again. The repository facts come from the Skill hooks instead. A fixture holding each form of
# injection, and one that only names the syntax, shows the guard catching what it is for.
INJ_FIX=$(mktemp -d); mkdir -p "$INJ_FIX"/skills/{inline,line-start,after-tab,fenced,tilde,four-ticks,mid-line,prose}
inj_skill() { printf -- '---\nname: %s\ndescription: x\n---\n\n%s\n' "$1" "$2" > "$INJ_FIX/skills/$1/SKILL.md"; }
inj_skill inline 'Branch: !`git branch --show-current || true`'
inj_skill line-start '!`git status --short`'
inj_skill after-tab $'Where:\t!`pwd`'
inj_skill fenced $'```!\ngit status --short\n```'
inj_skill tilde $'~~~!\ngit status --short\n~~~'
inj_skill four-ticks $'````!\ngit status --short\n````'
inj_skill mid-line $'Then: ```!\ngit status --short\n```'
inj_skill prose 'Prose names the syntax as `!`cmd`` and runs nothing.'
INJ_OUT=$(injected_commands "$INJ_FIX"); rm -rf "$INJ_FIX"
for want in "skills/inline/SKILL.md injects a shell command: !\`git branch --show-current || true\`" \
  "skills/line-start/SKILL.md injects a shell command" "skills/after-tab/SKILL.md injects a shell command" \
  "skills/fenced/SKILL.md injects a fenced block" "skills/tilde/SKILL.md injects a fenced block" \
  "skills/four-ticks/SKILL.md injects a fenced block" "skills/mid-line/SKILL.md injects a fenced block"; do
  [[ $INJ_OUT == *"$want"* ]] || fail "the injected-command guard missed: $want (it said: $INJ_OUT)"
done
[[ $INJ_OUT != *skills/prose/* ]] || fail "the injected-command guard flagged prose that only names the syntax: $INJ_OUT"
INJ_OUT=$(injected_commands "$PLUGIN")
[[ -z $INJ_OUT ]] || fail "$INJ_OUT"
# What every session pays for the plugin before any skill fires (lean-and-durable ticket 08): its listing, each skill's
# and agent's name and description, at most 875 tokens by `claude plugin details` (3.2.1 paid about 1,165). That tool
# counts through the count_tokens API for the active model, or estimates offline, so its figure moves with the machine;
# the guard is the listing's length instead: at most 2,650 characters, 875 tokens at the ratio the tool measured on
# 65988ac (2,426 characters, ~801 tokens). `claude --plugin-dir plugin plugin details matt-pocock-workflow` measures it.
LISTING=$(python3 - "$PLUGIN" <<'PY'
import pathlib, re, sys
root, total = pathlib.Path(sys.argv[1]), 0
for path in sorted(root.glob("skills/*/SKILL.md")) + sorted(root.glob("agents/**/*.md")):
    front = re.match(r"---\n(.*?)\n---\n", path.read_text(), re.S)
    fields = dict(line.split(":", 1) for line in front.group(1).splitlines() if ":" in line and line[:1].isalpha())
    total += len(f"matt-pocock-workflow:{fields['name'].strip()}: {fields.get('description', '').strip()}")
print(total)
PY
)
(( LISTING <= 2650 )) || fail "the plugin's listing is $LISTING characters, over 2,650 (about 875 tokens by claude plugin details)"
# Seams' read-only agents (lean-and-durable ticket 09): `scout` finds facts, `reviewer` reviews a named diff, and neither
# can change the project. Their tool lists are exactly the ticket's: scout has Read, Glob, Grep, WebFetch and WebSearch
# and skips CLAUDE.md; reviewer has Read, Glob, Grep and Bash, with Edit, Write and NotebookEdit disallowed. Each has a
# turn cap and pins no permission mode (plugin_guards holds model and effort; Claude Code ignores permissionMode in a
# plugin's agent, so a pin could only mislead). The gate refuses a change from exactly the agents that ship. A fixture
# breaking each rule shows the check catching it.
agent_problems() {   # $1 = a plugin directory: a line for each way its agents differ from the ticket's two
  python3 - "$1" <<'PY'
import pathlib, re, sys
root = pathlib.Path(sys.argv[1])
want = {"scout": {"tools": ["Read", "Glob", "Grep", "WebFetch", "WebSearch"], "omitClaudeMd": "true"},
        "reviewer": {"tools": ["Read", "Glob", "Grep", "Bash"], "disallowedTools": ["Edit", "Write", "NotebookEdit"]}}
files = {p.stem: p for p in sorted(root.glob("agents/**/*.md"))}
if sorted(files) != sorted(want):
    print(f"the agents are {sorted(files)}, expected {sorted(want)}")
items = lambda value: [v.strip() for v in value.strip("[] ").split(",") if v.strip()]
for name, spec in want.items():
    if name not in files:
        continue
    text = files[name].read_text()
    front = re.match(r"---\n(.*?)\n---\n", text, re.S)
    fields = dict((k.strip(), v.strip()) for k, v in (line.split(":", 1) for line in (front.group(1) if front else "").splitlines()
                                                      if ":" in line and line[:1].isalpha()))
    if fields.get("name") != name:
        print(f"agents/{name}.md is named {fields.get('name')!r}")
    for key in ("tools", "disallowedTools"):
        if sorted(items(fields.get(key, ""))) != sorted(spec.get(key, [])):
            print(f"{name}'s {key} are {items(fields.get(key, ''))}, expected {spec.get(key, [])}")
    if not re.fullmatch(r"[1-9][0-9]*", fields.get("maxTurns", "")):
        print(f"{name} has no turn cap (maxTurns)")
    if "permissionMode" in fields:
        print(f"{name} sets permissionMode")
    if fields.get("omitClaudeMd", "false") != spec.get("omitClaudeMd", "false"):
        print(f"{name}'s omitClaudeMd is {fields.get('omitClaudeMd', 'unset')}, expected {spec.get('omitClaudeMd', 'unset')}")
PY
}
AGENT_FIX=$(mktemp -d); mkdir -p "$AGENT_FIX/agents"
printf -- '---\nname: scouting\ndescription: x\ntools: Read, Glob, Grep, WebFetch, WebSearch, Bash\npermissionMode: plan\n---\n\nReport facts.\n' \
  > "$AGENT_FIX/agents/scout.md"
printf -- '---\nname: reviewer\ndescription: x\ntools: Read, Glob, Grep, Bash, Edit\nmaxTurns: 0\n---\n\nCite file:line.\n' \
  > "$AGENT_FIX/agents/reviewer.md"
printf -- '---\nname: extra\ndescription: x\n---\n' > "$AGENT_FIX/agents/extra.md"
AGENT_OUT=$(agent_problems "$AGENT_FIX"); rm -rf "$AGENT_FIX"
for want in "the agents are ['extra', 'reviewer', 'scout']" "agents/scout.md is named 'scouting'" "scout's tools are" \
  "scout has no turn cap" "scout sets permissionMode" "scout's omitClaudeMd is unset" \
  "reviewer's tools are" "reviewer's disallowedTools are [], expected" "reviewer has no turn cap"; do
  [[ $AGENT_OUT == *"$want"* ]] || fail "the agent check missed: $want (it said: $AGENT_OUT)"
done
AGENT_OUT=$(agent_problems "$PLUGIN")
[[ -z $AGENT_OUT ]] || fail "$AGENT_OUT"
GATE_AGENTS=$(PYTHONDONTWRITEBYTECODE=1 python3 -c 'import sys; sys.path.insert(0, sys.argv[1]); import seams_gate; print(" ".join(sorted(seams_gate.READ_ONLY_AGENTS)))' \
  "$PLUGIN/hooks")
[[ $GATE_AGENTS == "matt-pocock-workflow:reviewer matt-pocock-workflow:scout" ]] \
  || fail "the gate's read-only agents ($GATE_AGENTS) are not the agents the plugin ships"

# pr-review's permissions are the two lists in its frontmatter, which Claude Code enforces whatever the text says
# (lean-and-durable ticket 06, 3.4.0's take-over). allowed-tools pre-approves the gh commands that only read, and each
# script as the core runs it, `python3 ${CLAUDE_SKILL_DIR}/scripts/<name>.py`: Claude Code fills in ${CLAUDE_SKILL_DIR}
# in both places, so the rule matches the command, from any directory. takeover.py is pre-approved for `target` alone,
# which only decides; `push` pushes to someone else's branch, so Claude Code's own prompt, showing the branch and the
# commit, is the user's yes. disallowed-tools refuses pushing, merging, closing, reopening, editing, marking ready and
# reviewing. Each list is read under its own key and held to exactly these entries; a fixture with a refused command
# moved into the pre-approved list, and one with an extra pre-approval, shows the check catching both.
PRR="$PLUGIN/skills/pr-review/SKILL.md"
PRR_SCRIPTS="evidence run_checks review_payload post_reviews batch_report requirements"
PRR_ALLOWED=("Bash(gh auth status:*)" "Bash(gh repo view:*)" "Bash(gh pr view:*)" "Bash(gh pr list:*)" "Bash(gh pr diff:*)"
  "Bash(gh pr checks:*)" "Bash(gh issue view:*)")
for s in $PRR_SCRIPTS; do PRR_ALLOWED+=("Bash(python3 \${CLAUDE_SKILL_DIR}/scripts/$s.py *)"); done
PRR_ALLOWED+=("Bash(python3 \${CLAUDE_SKILL_DIR}/scripts/takeover.py target *)")
PRR_DISALLOWED=("Bash(git push:*)" "Bash(gh pr merge:*)" "Bash(gh pr close:*)" "Bash(gh pr reopen:*)" "Bash(gh pr edit:*)"
  "Bash(gh pr ready:*)" "Bash(gh pr review:*)")
permission_problems() {   # $1 = a SKILL.md: how its allowed-tools and disallowed-tools differ from PRR_ALLOWED and PRR_DISALLOWED
  python3 - "$1" "${#PRR_ALLOWED[@]}" "${PRR_ALLOWED[@]}" "${PRR_DISALLOWED[@]}" <<'PY'
import re, sys
n = int(sys.argv[2])
want = {"allowed-tools": sys.argv[3:3 + n], "disallowed-tools": sys.argv[3 + n:]}
front = re.match(r"---\n(.*?)\n---\n", open(sys.argv[1]).read(), re.S)
lists, key = {}, None
for line in (front.group(1) if front else "").splitlines():
    if line[:1].isalpha():
        key = line.split(":", 1)[0].strip()
        lists.setdefault(key, [])
    elif key and re.match(r"\s+- ", line):
        lists[key].append(line.split("- ", 1)[1].strip())
for key, entries in want.items():
    have = lists.get(key, [])
    for line in [f"{key} lacks {e}" for e in entries if e not in have] + [f"{key} adds {e}" for e in have if e not in entries]:
        print(line)
PY
}
PERM_FIX=$(mktemp -d)
grep -vxF -- "  - Bash(gh pr merge:*)" "$PRR" | awk '{print} $0 == "allowed-tools:" {print "  - Bash(gh pr merge:*)"}' > "$PERM_FIX/moved"
awk '{print} $0 == "allowed-tools:" {print "  - Bash(rm:*)"}' "$PRR" > "$PERM_FIX/extra"
PERM_OUT="$(permission_problems "$PERM_FIX/moved")"$'\n'"$(permission_problems "$PERM_FIX/extra")"; rm -rf "$PERM_FIX"
for want in "allowed-tools adds Bash(gh pr merge:*)" "disallowed-tools lacks Bash(gh pr merge:*)" "allowed-tools adds Bash(rm:*)"; do
  [[ $PERM_OUT == *"$want"* ]] || fail "the permission check missed: $want (it said: $PERM_OUT)"
done
PERM_OUT=$(permission_problems "$PRR")
[[ -z $PERM_OUT ]] || fail "pr-review's permissions changed: $PERM_OUT"
PRR_BODY=$(awk 'body; NR > 1 && /^---$/ {body = 1}' "$PRR")
for s in $PRR_SCRIPTS takeover; do
  [[ -x "$PLUGIN/skills/pr-review/scripts/$s.py" ]] || fail "pr-review/scripts/$s.py missing or not executable"
  [[ $PRR_BODY == *"\`python3 \${CLAUDE_SKILL_DIR}/scripts/$s.py\`"* ]] \
    || fail "pr-review's core does not name its script as: python3 \${CLAUDE_SKILL_DIR}/scripts/$s.py"
done

# The routing (seams-3 ticket 07): every Seams skill directory is named in the bootstrap or in routing.md, so none is
# unreachable, and every name they give as this plugin's (`<name>`* or matt-pocock-workflow:<name>) is a skill or an
# agent it ships, so no route leads nowhere. The bootstrap's table keeps its rows, in their order, since between two
# rows the lower applies; a table with a row dropped, reworded, swapped or added shows the check catching each, and one
# with another table above it shows the check finding the routing table by its rows. The session-start hook injects
# the bootstrap, so it carries no pseudo-tag: Claude Code's hook docs warn that text framed as out-of-band system
# commands can trip Claude's prompt-injection defenses.
ROUTING="$PLUGIN/skills/using-matt-pocock-skills/references/routing.md"
BOOT="$PLUGIN/skills/using-matt-pocock-skills/SKILL.md"
NAMED="$(cat "$BOOT" "$ROUTING")"
for d in "$PLUGIN"/skills/*/; do
  s=$(basename "$d"); [[ $s == using-matt-pocock-skills ]] && continue
  [[ $NAMED == *"\`$s\`"* || $NAMED == *"matt-pocock-workflow:$s"* ]] || fail "Seams skill named neither in the bootstrap nor in routing.md: $s"
done
for s in $(grep -ohE '`[a-z-]+`\*|matt-pocock-workflow:[a-z-]+' "$BOOT" "$ROUTING" | sed -E 's/^`//; s/`\*$//; s/^matt-pocock-workflow://' | sort -u); do
  [[ -f "$PLUGIN/skills/$s/SKILL.md" || -f "$PLUGIN/agents/$s.md" ]] || fail "the routing sends work to $s, which the plugin does not ship"
done
BOOT_ROWS=(
  "| Trivial: copy, typo, comment, unobservable rename | \`trivial\`* |"
  "| Broken, failing, throwing, slow | \`diagnosing-bugs\`, even when the fix looks obvious |"
  "| Bounded change to existing code | \`grill\`*, \`tdd\` |"
  "| New behavior in one session | \`grill\`* + \`domain-modeling\`, then \`implement\`* |"
  "| Several sessions, or a new app | \`grill\`*, \`to-spec\`*, \`to-tickets\`*, \`implement\`* per ticket; a new app's ticket 01 is the walking skeleton |"
  "| Sensitive, any size: auth, permissions, secrets, billing, migrations, infra, CI or deploy config, public API, anything destructive | its size row's move, \`grill\`* on the security and failure axes first, \`code-review\` required |"
  "| Down or degraded for users now | \`incident\`* |"
  "| Ship, deploy, release, publish | \`release\`* |")
routing_problem() {   # $1 = a bootstrap file: how its routing table's rows differ from BOOT_ROWS, or nothing
  python3 - "$1" "${BOOT_ROWS[@]}" <<'PY'
import re, sys
want, tables, rows = sys.argv[2:], [], None
for line in open(sys.argv[1]).read().splitlines():
    if re.fullmatch(r"\|(\s*:?-+:?\s*\|)+", line):            # a table's separator: its rows follow
        rows = []
        tables.append(rows)
    elif rows is not None and line.startswith("|"):
        rows.append(line)
    else:
        rows = None
have = max(tables, key=lambda t: len(set(t) & set(want)), default=[])   # the routing table shares the most rows
lost = [row for row in want if row not in have]
if lost:
    print(f"the bootstrap lost a routing row: {lost[0]}")
elif have != want:
    print("the bootstrap's routing rows changed (between two rows the lower applies, so their order is the routing too):")
    print("\n".join(have))
PY
}
ROW_FIX=$(mktemp -d)
table() { printf -- '---\nname: x\ndescription: x\n---\n\nIntro.\n\n| Request | First move |\n| --- | --- |\n'; printf '%s\n' "$@"; printf '\nAfter.\n'; }
table "${BOOT_ROWS[@]}" > "$ROW_FIX/same"
table "${BOOT_ROWS[@]:1}" > "$ROW_FIX/dropped"
table "${BOOT_ROWS[@]:0:2}" "| Bounded change to existing code | \`tdd\` |" "${BOOT_ROWS[@]:3}" > "$ROW_FIX/reworded"
table "${BOOT_ROWS[1]}" "${BOOT_ROWS[0]}" "${BOOT_ROWS[@]:2}" > "$ROW_FIX/swapped"
table "${BOOT_ROWS[@]}" "| Anything else | \`grill\`* |" > "$ROW_FIX/added"
{ printf '| Gate | When |\n| --- | --- |\n| Deploy | always asks |\n\n'; table "${BOOT_ROWS[@]}"; } > "$ROW_FIX/another-table-above"
for kept in same another-table-above; do
  problem=$(routing_problem "$ROW_FIX/$kept")
  [[ -z $problem ]] || { rm -rf "$ROW_FIX"; fail "the routing check flagged the rows as they are ($kept): $problem"; }
done
for probe in dropped reworded swapped added; do
  [[ -n $(routing_problem "$ROW_FIX/$probe") ]] || { rm -rf "$ROW_FIX"; fail "the routing check passed a table with a row $probe"; }
done
rm -rf "$ROW_FIX"
problem=$(routing_problem "$BOOT"); [[ -z $problem ]] || fail "$problem"
BOOT_BODY=$(awk 'body; NR > 1 && /^---$/ {body = 1}' "$BOOT")
grep -qE "<[A-Z_-]+>" <<< "$BOOT_BODY" && fail "a pseudo-tag in the bootstrap: $(grep -oE "<[A-Z_-]+>" <<< "$BOOT_BODY" | head -1)"

# The continuous flow's stops (seams-revamp ticket 06): once the user confirms a design, each step starts the next
# unasked, so a question is all that stands between the flow and an outward, irreversible or paid action. The
# bootstrap's flow rule says so and names every stop, and each skill that owns one still asks before it acts: the
# spec's and the tickets' publish, a parallel run's integrations, a branch's integration and its discard, release's
# readiness, deploy and production questions, an incident's outward action, the paid cloud review. Every skill that
# keeps the progress file still points at its format where it writes it, since the flow skips questions, never the
# record. The shared rules' process table (ticket 07) lets a small change skip extras, so its floor is held the same
# way: the sensitive list is checked before the size, a sensitive change of any size gets code-review, a correctness
# review and the security review, required, and verification, and a feature gets its two reviewers, and its scouts
# however small the codebase, in the shared rules and in the grill (ticket 08's proof); and the docs rule
# is in the bootstrap and in the shared rules. A copy with each stop dropped in turn shows the check catching that stop
# alone.
flow_stop_problems() {   # $1 = a plugin directory, $2 = "probe" to drop each stop from a copy: a line for each stop missed
  python3 - "$1" "${2:-}" <<'PY'
import pathlib, re, shutil, sys, tempfile
root, probe = pathlib.Path(sys.argv[1]), sys.argv[2] == "probe"
BOOT, FLOW = "skills/using-matt-pocock-skills/SKILL.md", r"(?m)^\d+\. Flow:.*$"
FIN = "skills/finishing-a-development-branch/SKILL.md"
STOPS = [("the bootstrap's flow rule lets the next steps start unasked", BOOT, FLOW, r"\bunasked\b")]
STOPS += [(f"the bootstrap's flow rule names {what}", BOOT, FLOW, pattern) for what, pattern in (
    ("the user's decisions", r"user's decisions"), ("integrating a branch", r"integrat\w*\s+(?:a\s+|the\s+)?branch"),
    ("a push", r"\bpush"), ("a deploy", r"\bdeploy"), ("a publish", r"\bpublish"),
    ("anything destructive", r"\bdestructive"), ("a paid run", r"\bpaid\b"))]
STOPS += [(what, path, None, pattern) for what, path, pattern in (
    ("to-spec asks before it publishes the spec", "skills/to-spec/SKILL.md", r"\*\*Publish\.\*\*[^\n]*\bwait for a yes"),
    ("to-tickets publishes nothing before the breakdown's approval", "skills/to-tickets/SKILL.md",
     r"Nothing is published before that approval"),
    ("a parallel run's offer names its integrations", "skills/implement/references/parallel.md",
     r"integrated onto the current branch one at a time"),
    ("finishing-a-development-branch waits for the integration choice", FIN,
     r"Wait for their answer;\s+the integration decision\s+is theirs"),
    ("finishing-a-development-branch discards only on the typed word", FIN, r"Type 'discard' to confirm"),
    ("release asks before its readiness checks", "skills/release/SKILL.md", r"check readiness now\?"),
    ("release asks before every deploy", "skills/release/SKILL.md", r"\*\*every time\*\*: \"Deploy candidate"),
    ("release asks again before production", "skills/release/SKILL.md", r"Production, or the public listing, gets its own question"),
    ("incident asks before any outward action", "skills/incident/SKILL.md", r"\*\*Ask before any outward action\.\*\*"),
    ("implement never starts the paid cloud review unasked", "skills/implement/references/reviews.md",
     r"\*\*Never `ultra`\*\*[^\n]*unless the user asks"))]
STOPS += [(f"{s} keeps the progress file in its format", f"skills/{s}/SKILL.md", None, r"references/progress-file\.md")
          for s in ("grill", "to-spec", "to-tickets", "implement", "finishing-a-development-branch", "release")]
RULES = "skills/using-matt-pocock-skills/references/rules.md"
SENSITIVE, SENSITIVE_ROW, FEATURE_ROW = r"(?ms)^## Sensitive changes\n.*?(?=^## |\Z)", r"(?m)^\| Sensitive.*$", r"(?m)^\| Feature.*$"
STOPS += [("the shared rules check the sensitive list before the size", RULES, SENSITIVE, r"checked first")]
STOPS += [(f"a sensitive change gets {what}", RULES, SENSITIVE_ROW, pattern) for what, pattern in (
    ("code-review", r"`code-review`"), ("a correctness review", r"correctness review"), ("the security review", r"security review"),
    ("its reviews as required", r"\brequired\b"), ("verification", r"verification-before-completion"))]
STOPS += [(f"a feature gets {what}", RULES, FEATURE_ROW, pattern) for what, pattern in (
    ("code-review", r"`code-review`"), ("a correctness review", r"correctness review"), ("both reviews run, not offered", r"\bboth run\b"),
    ("its scouts however small the codebase", r"however small the codebase"))]
STOPS += [("the grill starts a feature's scouts however small the codebase", "skills/grill/SKILL.md", None,
           r"feature[^\n]*however small the codebase"),
          ("the shared rules' Scouts line starts a feature's grill's scouts however small the codebase", RULES,
           r"(?m)^- \*\*Scouts\*\*.*$", r"in a feature's grill,? however small the codebase")]
STOPS += [(f"the docs rule is in {where}", path, None, r"official docs[^\n]*version in use")
          for where, path in (("the bootstrap", BOOT), ("the shared rules", RULES))]

def missed(plugin):
    out = []
    for what, path, scope, pattern in STOPS:
        text = (plugin / path).read_text() if (plugin / path).is_file() else ""
        if scope:
            text = (re.search(scope, text) or re.match("", "")).group(0)
        if not re.search(pattern, text, re.I):
            out.append(what)
    return out

def drop(text, scope, pattern):   # the text with the stop's pattern removed, inside its scope when it has one
    if not scope:
        return re.sub(pattern, "", text, flags=re.I)
    return re.sub(scope, lambda m: re.sub(pattern, "", m.group(0), flags=re.I), text, count=1)

if not probe:
    print("\n".join(missed(root)))
    sys.exit()
for what, path, scope, pattern in STOPS:
    with tempfile.TemporaryDirectory() as tmp:
        copy = pathlib.Path(tmp)
        for p in {stop[1] for stop in STOPS}:
            (copy / p).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(root / p, copy / p)
        (copy / path).write_text(drop((copy / path).read_text(), scope, pattern))
        said = missed(copy)
        if said != [what]:
            print(f"the flow-stop check missed: {what} (it said: {said})")
PY
}
STOP_OUT=$(flow_stop_problems "$PLUGIN")
[[ -z $STOP_OUT ]] || fail "a stop of the continuous flow, or a floor of the process table, is gone: $STOP_OUT"
STOP_OUT=$(flow_stop_problems "$PLUGIN" probe)
[[ -z $STOP_OUT ]] || fail "$STOP_OUT"

# The three kept Superpowers skills (KEPT, above): present, and matching the checksums recorded in the notices.
for s in $KEPT; do [[ -f "$PLUGIN/skills/$s/SKILL.md" ]] || fail "missing copied skill: $s"; done
SP_SECTION=$(section Superpowers "$NOTICES")
SP_SUMS=$(grep -E '^[0-9a-f]{64}  skills/[a-z-]+/SKILL\.md$' <<< "$SP_SECTION") \
  || fail "no checksums in the Superpowers section of THIRD_PARTY_NOTICES.md"
[[ $(wc -l <<< "$SP_SUMS") -eq 3 ]] || fail "expected 3 recorded checksums, got: $SP_SUMS"
(cd "$PLUGIN" && shasum -a 256 -c <<< "$SP_SUMS" >/dev/null) || fail "a copied skill differs from its recorded checksum"

# finishing-a-development-branch is Seams' adaptation of the Superpowers original (lean-and-durable ticket 05). Its
# last line attributes the original, and the notices record the original's checksum as `shasum -c` checks it in the
# plugin cache.
FIN="$PLUGIN/skills/finishing-a-development-branch/SKILL.md"
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
