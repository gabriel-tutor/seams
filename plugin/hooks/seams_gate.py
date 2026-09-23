"""The gate: the rules the matt-pocock-workflow hooks share.

A change to the project is refused until the current request has a declaration: a Skill
invocation of a process skill, or a slash command the user typed for one. This module holds
the pure parts (what counts as a change, what counts as a declaration, what a continuation
is, the ledger's shape and the decisions) so the hooks stay thin and the routing harness can
score a shell write the same way the gate does. Python 3.9: macOS's system interpreter runs
the hooks when nothing newer is first on PATH.
"""
from __future__ import annotations

import json
import os
import re
import shlex
import sys
import tempfile
import time
import traceback
from typing import Callable, Optional

# --- Shell commands -----------------------------------------------------------------------
# A best-effort mesh: the common ways of changing files from a shell. It never proves a
# command has no side effects. Every label is fixed text, so nothing typed reaches the ledger.

FILE_COMMANDS = {"rm", "rmdir", "unlink", "mv", "cp", "touch", "mkdir", "ln", "chmod", "chown",
                 "truncate", "tee", "install", "dd", "patch", "shred"}
GIT_WRITES = {"add", "commit", "rm", "mv", "checkout", "switch", "restore", "reset", "rebase",
              "merge", "cherry-pick", "revert", "apply", "am", "clean", "push", "pull", "init",
              "clone"}
GIT_STASH_READS = {"list", "show"}
GIT_TAG_READ_FLAGS = {"-l", "--list", "-n"}
GIT_WORKTREE_WRITES = {"add", "remove", "move"}
GIT_BRANCH_WRITE_FLAGS = {"-d", "-D", "-m", "-M", "--delete", "--move", "--force"}
NODE_MANAGERS = {"npm", "pnpm", "yarn", "bun"}
NODE_WRITES = {"install", "i", "add", "remove", "rm", "uninstall", "un", "update", "up", "upgrade",
               "link", "unlink", "init", "create", "ci", "dedupe", "prune"}
OTHER_MANAGERS = {"pip": {"install", "uninstall"}, "pip3": {"install", "uninstall"},
                  "uv": {"add", "remove", "sync"}, "poetry": {"add", "remove", "install", "update"},
                  "cargo": {"add", "remove", "install"}, "go": {"get", "install"},
                  "gem": {"install", "uninstall"}}
UV_PIP_WRITES = {"install", "uninstall", "sync"}
FORMATTERS = {"prettier", "biome", "gofmt", "goimports", "gofumpt", "shfmt"}
# Wrappers that run another command; the flags that take a value; positional counts to skip.
WRAPPERS = {"sudo", "env", "time", "nice", "nohup", "command", "exec", "xargs", "timeout", "doas"}
WRAPPER_VALUE_FLAGS = {"-u", "-g", "-C", "-D", "-h", "-p", "-r", "-t", "-n", "-I", "-L", "-P", "-s",
                       "-a", "-E", "-k"}
WRAPPER_POSITIONALS = {"timeout": 1}
INTERPRETERS = re.compile(r"^(python[0-9.]*|node|ruby|perl|deno|bun)$")
INLINE_FLAGS = {"-c", "-e", "--eval", "-p", "--print", "-"}
SED_IN_PLACE = re.compile(r"^(-[a-zA-Z]*i|--in-place)")
PERL_RUBY_IN_PLACE = re.compile(r"^-[a-z0-9]*i")        # -i, -pi, -0pi; not -Ilib, not -MList::Util
WRITE_PATTERNS = re.compile(
    r"open\([^)]*['\"][wax]b?\+?['\"]"          # open(path, 'w') / 'a' / 'x' in any language
    r"|open\([^)]*['\"]>"                          # perl: open(F, ">out")
    r"|mode\s*=\s*['\"][wax]"
    r"|\.write_text\(|\.write_bytes\(|\.writelines\("
    r"|\bwriteFile(Sync)?\(|\bappendFile(Sync)?\(|createWriteStream\("
    r"|\.rm\(|\.rmdir\(|\brmSync\(|\brmdirSync\(|\bunlinkSync\(|\brenameSync\(|\bmkdirSync\(|copyFile"
    r"|os\.(remove|unlink|rename|replace|rmdir|removedirs|makedirs)\("
    r"|shutil\.(copy|copy2|copyfile|copytree|move|rmtree)\("
    r"|\.unlink\(|\.rename\(|\.mkdir\(|\.truncate\("
    r"|\bunlink\(|\brename\("                      # perl builtins
    r"|FileUtils\.|File\.(delete|write|rename|unlink|open\([^)]*['\"][wa])|IO\.write")
ASSIGNMENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
SEPARATOR_CHARS = set(";&|\n()")              # a token made of these alone ends a simple command
REDIRECT_TOKENS = {">", ">>", "&>", "&>>", ">|", ">&", "<>"}
INPUT_REDIRECTS = {"<", "<<", "<<-", "<<<", "<&"}
SHELL_KEYWORDS = {"if", "then", "else", "elif", "while", "until", "do", "!", "{", "}"}
ASSIGNING_BUILTINS = {"export", "declare", "local", "readonly", "typeset"}


def _tokens(command: str) -> list:
    """Shell words with quotes kept, so a quoted '>' is not an operator. A newline outside quotes
    ends a command as `;` does; a backslash-newline continues it."""
    text = command.replace("\\\n", " ")
    lexer = shlex.shlex(text, posix=False, punctuation_chars="();<>|&\n")
    lexer.whitespace = " \t\r"
    lexer.whitespace_split = True
    try:
        return list(lexer)
    except ValueError:                        # unbalanced quotes: fall back to a rough split
        return re.findall(r"\n|&&|\|\||[;|&()]|>>|>&|&>|>\||<<|<|>|[^\s;|&()<>]+", text)


def _segments(tokens: list) -> list:
    """The simple commands of a list, pipeline, subshell or compound command, each a token list."""
    out, current = [], []
    for token in tokens:
        if token and set(token) <= SEPARATOR_CHARS:
            if current:
                out.append(current)
            current = []
        else:
            current.append(token)
    if current:
        out.append(current)
    return out


def _unquote(token: str) -> str:
    if len(token) >= 2 and token[0] == token[-1] and token[0] in "'\"":
        return token[1:-1]
    return token


def _words(segment: list) -> list:
    """The command and its arguments, after leading keywords, assignments and wrappers.

    `sudo -u bob rm x`, `env FOO=1 rm -rf x`, `xargs -I{} rm {}`, `timeout 5 touch a` and
    `then rm x` all resolve to the wrapped command.
    """
    words = list(segment)
    while True:
        while words and (ASSIGNMENT.match(words[0]) or _unquote(words[0]) in SHELL_KEYWORDS):
            words.pop(0)
        if not words or os.path.basename(_unquote(words[0])) not in WRAPPERS:
            return words
        wrapper = os.path.basename(_unquote(words.pop(0)))
        while words and words[0].startswith("-"):
            flag = words.pop(0)
            if flag in WRAPPER_VALUE_FLAGS and words and not words[0].startswith("-"):
                words.pop(0)
        for _ in range(WRAPPER_POSITIONALS.get(wrapper, 0)):
            if words:
                words.pop(0)


def _split_redirects(segment: list) -> tuple:
    """The segment's words without its redirections, and the files its redirections write, as
    raw tokens. A duplicated descriptor (`2>&1`) and /dev/null are not files; input is read."""
    words, targets, i = [], [], 0
    while i < len(segment):
        token, after = segment[i], (segment[i + 1] if i + 1 < len(segment) else None)
        if token.isdigit() and (after in REDIRECT_TOKENS or after in INPUT_REDIRECTS):
            i += 1                            # the descriptor number of `2> file`
            continue
        if token.endswith(">") and token[:-1].isdigit():
            token = ">"                       # `2>` as the rough split leaves it
        if token in REDIRECT_TOKENS or token in INPUT_REDIRECTS:
            if after is not None and token in REDIRECT_TOKENS:
                target = _unquote(after)
                duplicate = token == ">&" and (target.isdigit() or target == "-")
                if not duplicate and not target.startswith("&") and target != "/dev/null":
                    targets.append(after)
            i += 2
            continue
        words.append(token)
        i += 1
    return words, targets


# --- Where a shell write lands --------------------------------------------------------------
# A write is let through only when every path it writes is placed and not the project: the
# rule Edit and Write already follow. A path is placed when it is written out in full, or built
# from $TMPDIR, $HOME or a variable an earlier assignment in the same command set. A relative
# path, a glob, a command substitution, an escape or any other variable is not placed, and the
# write counts. Single quotes are literal, as in the shell.

VARIABLE = re.compile(r"\$(?:\{([A-Za-z_][A-Za-z0-9_]*)(?:(:?-)([^}$]*))?\}|([A-Za-z_][A-Za-z0-9_]*))")
GLOB_CHARS = set("*?[")


def _initial_env() -> dict:
    env = {}
    for name in ("TMPDIR", "HOME"):
        if os.environ.get(name):
            env[name] = os.environ[name]
    return env


def _expand(token: str, env: dict) -> Optional[str]:
    """A token's text after quote removal and variable expansion, or None when it cannot be known."""
    if token[:1] == "'":
        inner = token[1:-1]
        return inner if len(token) >= 2 and token[-1] == "'" and "'" not in inner else None
    if token[:1] == '"':
        if len(token) < 2 or token[-1] != '"' or '"' in token[1:-1]:
            return None
        text = token[1:-1]
    else:
        if "'" in token or '"' in token:
            return None
        text = token
        if text == "~" or text.startswith("~/"):
            if "HOME" not in env:
                return None
            text = env["HOME"] + text[1:]
    if "$(" in text or "`" in text or "\\" in text:
        return None
    unknown = []

    def value(match):
        name, operator, default = match.group(1) or match.group(4), match.group(2), match.group(3)
        current = env.get(name)
        if operator == ":-" and not current or operator == "-" and current is None:
            return default
        if current is None:
            unknown.append(name)
            return ""
        return current

    text = VARIABLE.sub(value, text)
    return None if unknown or "$" in text else text


def _place(token: str, env: dict) -> Optional[str]:
    """The absolute path a token names, or None when it is not placed."""
    text = _expand(token, env)
    if text is None or not text or GLOB_CHARS & set(text) or not os.path.isabs(text):
        return None
    return os.path.normpath(text)


def _assigns(segment: list, env: dict) -> bool:
    """Whether the segment only assigns variables; if so, record them. `A=1 cmd` is not one: its
    assignment reaches cmd's environment, not the words the shell expands."""
    words = list(segment)
    if words and _unquote(words[0]) in ASSIGNING_BUILTINS:
        words = [w for w in words[1:] if not w.startswith("-")]
    if not words or not all(ASSIGNMENT.match(w) for w in words):
        return False
    for word in words:
        name, _, raw = word.partition("=")
        text = _expand(raw, env) if raw else ""
        if text is None:
            env.pop(name, None)
        else:
            env[name] = text
    return True


def _operands(args: list) -> list:
    """The arguments that are not options: everything after `--`, and every word that does not
    start with `-`. An option's value counts as an operand, which only ever makes a write count."""
    out, options_done = [], False
    for arg in args:
        if not options_done and arg == "--":
            options_done = True
        elif options_done or not _unquote(arg).startswith("-") or _unquote(arg) == "-":
            out.append(arg)
    return out


def _worktree_paths(words: list) -> Optional[list]:
    """The worktree paths `git worktree add|remove|move` writes, or None when it makes a branch."""
    rest = words[1:]
    while rest and rest[0].startswith("-"):
        rest = rest[2:] if rest[0] in {"-C", "-c", "--git-dir", "--work-tree"} and len(rest) > 1 else rest[1:]
    sub, args = (_unquote(rest[1]) if len(rest) > 1 else ""), rest[2:]
    if any(_unquote(a) in {"-b", "-B", "--orphan"} for a in args):
        return None
    operands, skip = [], False
    for arg in args:
        if skip:
            skip = False
        elif _unquote(arg) == "--reason":
            skip = True
        elif not _unquote(arg).startswith("-"):
            operands.append(arg)
    if sub == "add":
        return operands[:1] or None           # the new worktree's path; a commit after it is read
    return operands or None


def _download_targets(base: str, args: list) -> Optional[list]:
    """The files curl -o or wget -O write, or None when they write under the working directory."""
    flags = {"curl": ({"-o", "--output"}, "-o", "--output="),
             "wget": ({"-O", "--output-document"}, "-O", "--output-document=")}[base]
    targets = []
    for i, arg in enumerate(args):
        bare = _unquote(arg)
        if bare in flags[0] and i + 1 < len(args):
            targets.append(args[i + 1])
        elif bare.startswith(flags[2]):
            targets.append(bare[len(flags[2]):])
        elif bare.startswith(flags[1]) and len(bare) > 2 and not bare.startswith("--"):
            targets.append(bare[2:])
        elif base == "curl" and bare in {"-O", "--remote-name", "--remote-name-all"}:
            return None
    return targets or None


def _find_roots(args: list) -> list:
    roots = []
    for arg in args:
        if _unquote(arg)[:1] in {"-", "(", "!", ")"}:
            break
        roots.append(arg)
    return roots


def _git_label(words: list) -> Optional[str]:
    rest = words[1:]
    while rest and rest[0].startswith("-"):
        takes_value = rest[0] in {"-C", "-c", "--git-dir", "--work-tree"}
        rest = rest[2:] if takes_value and len(rest) > 1 else rest[1:]
    if not rest:
        return None
    sub, args = _unquote(rest[0]), [_unquote(r) for r in rest[1:]]
    if sub in GIT_WRITES:
        return f"git {sub}"
    if sub == "branch":                       # a write only with a delete or move flag
        return "git branch -d" if any(a in GIT_BRANCH_WRITE_FLAGS for a in args) else None
    if sub == "stash":                        # a write unless listing or showing
        return None if args and args[0] in GIT_STASH_READS else "git stash"
    if sub == "tag":                          # bare `git tag` lists; a name creates
        return None if not args or any(a in GIT_TAG_READ_FLAGS for a in args) else "git tag"
    if sub == "worktree":
        return "git worktree" if args and args[0] in GIT_WORKTREE_WRITES else None
    return None


def _manager_label(base: str, args: list) -> Optional[str]:
    """Package managers adding or removing dependencies. Labels are fixed vocabulary."""
    if base in NODE_MANAGERS:
        sub = args[0] if args else ("install" if base == "yarn" else "")
        return f"{base} {sub}" if sub in NODE_WRITES else None
    if base == "uv" and args[:1] == ["pip"]:
        return "uv pip install" if len(args) > 1 and args[1] in UV_PIP_WRITES else None
    if base in OTHER_MANAGERS and args and args[0] in OTHER_MANAGERS[base]:
        return f"{base} {args[0]}"
    return None


def _download_label(base: str, args: list) -> Optional[str]:
    if base == "curl":
        to_file = any(a in {"-o", "-O", "--output", "--remote-name"} or (a.startswith("-o") and len(a) > 2)
                      for a in args)
        return "a download to a file" if to_file else None
    if base == "wget":
        to_stdout = any(a in {"-O-", "-qO-"} for a in args)
        for i, a in enumerate(args):
            if a in {"-O", "--output-document"} and args[i + 1:i + 2] == ["-"]:
                to_stdout = True
        return None if to_stdout else "a download to a file"
    return None


def _inline_program_writes(base: str, args: list, command: str) -> bool:
    if not INTERPRETERS.match(base):
        return False
    inline = any(a in INLINE_FLAGS for a in args) or "<<" in command
    return bool(inline and WRITE_PATTERNS.search(command))


def _write(segment: list, command: str, env: dict, is_exempt) -> tuple:
    """What a simple command (its redirections removed) writes: its label and the raw tokens of
    the paths it writes, or None for the paths when they cannot be told. (None, None): no write."""
    words = _words(segment)
    if not words:
        return None, None
    base = os.path.basename(_unquote(words[0]))
    raw = words[1:]
    args = [_unquote(w) for w in raw]
    by_xargs = any(os.path.basename(_unquote(w)) == "xargs" for w in segment[:len(segment) - len(words)])
    if base in {"bash", "sh", "zsh"} and "-c" in args:
        inner = args[args.index("-c") + 1:][:1]
        return (_classify(inner[0], is_exempt, dict(env)) if inner else None), None
    if base in FILE_COMMANDS:                 # xargs supplies its operands; patch names its own files
        return base, (None if by_xargs or base == "patch" else _operands(raw))
    if base == "sed" and any(SED_IN_PLACE.match(a) for a in args):
        return "sed -i", None
    if base in {"perl", "ruby"} and any(PERL_RUBY_IN_PLACE.match(a) for a in args):
        return f"{base} -i", None
    if base == "git":
        label = _git_label(words)
        return label, (_worktree_paths(words) if label == "git worktree" else None)
    label = _manager_label(base, args)
    if label:
        return label, None
    label = _download_label(base, args)
    if label:
        return label, _download_targets(base, raw)
    if "--write" in args:
        return "a --write flag", None
    if "--fix" in args:
        return "a --fix flag", None
    if "-w" in args and any(a in FORMATTERS for a in [base] + args):
        return "a --write flag", None
    if base == "find":
        roots = _find_roots(raw) or None      # no root: the working directory
        if "-delete" in args:
            return "find -delete", roots
        for flag in ("-exec", "-execdir"):
            if flag in args:
                after = args[args.index(flag) + 1:]
                if after and os.path.basename(after[0]) in FILE_COMMANDS:
                    return f"find -exec {os.path.basename(after[0])}", roots
    if _inline_program_writes(base, args, command):
        return "an inline program that writes", None
    return None, None


def _all_exempt(tokens: Optional[list], env: dict, is_exempt) -> bool:
    if tokens is None:
        return False
    for token in tokens:
        path = _place(token, env)
        if path is None or not is_exempt(path):
            return False
    return True


def _segment_label(segment: list, command: str, env: dict, is_exempt) -> Optional[str]:
    words, redirects = _split_redirects(segment)
    label, targets = _write(words, command, env, is_exempt)
    if is_exempt is None:                     # every write counts; a redirection names it first
        return "a redirect to a file" if redirects else label
    if label and not _all_exempt(targets, env, is_exempt):
        return label
    if redirects and not _all_exempt(redirects, env, is_exempt):
        return "a redirect to a file"
    return None


def _classify(command: str, is_exempt, env: dict) -> Optional[str]:
    if not command or not command.strip():
        return None
    for segment in _segments(_tokens(command)):
        if _assigns(segment, env):
            continue
        label = _segment_label(segment, command, env, is_exempt)
        if label:
            return label
    return None


def classify_command(command: str, is_exempt: Optional[Callable[[str], bool]] = None) -> Optional[str]:
    """The label for what a shell command changes, or None when it looks read-only.

    With `is_exempt`, a write whose every path is placed (see above) and exempt is not a change:
    the gate passes the rule Edit and Write follow. Without it every write counts, which is how
    the routing harness scores a shell write before the first Skill call.
    """
    return _classify(command, is_exempt, _initial_env())


# --- Declarations and requests ------------------------------------------------------------

PLUGIN_PREFIX = "matt-pocock-workflow:"
# Matt Pocock's process skills, by bare name. Domain skills (frontend-design, pdf, ...) and
# other plugins' process skills (superpowers:brainstorming) do not open the gate. The three
# setup skills are the ones upstream ships; a wildcard would admit any third-party setup-*.
PROCESS_SKILLS = {
    "grilling", "grill-me", "grill-with-docs", "domain-modeling", "tdd", "diagnosing-bugs",
    "code-review", "codebase-design", "prototype", "resolving-merge-conflicts", "research",
    "wizard", "setup-matt-pocock-skills", "setup-pre-commit", "setup-ts-deep-modules",
    "wayfinder", "triage", "improve-codebase-architecture", "handoff", "ask-matt",
    "implement", "to-spec", "to-tickets",
}
# A continuation is a whole go-ahead phrase, optionally led by an assent word and trailed by
# a courtesy, or a bare option. Anything with its own content is a new request.
GO_PHRASES = {
    "y", "yes", "yep", "yeah", "yup", "ok", "okay", "k", "sure", "go", "go ahead", "go on",
    "go for it", "continue", "proceed", "do it", "do that", "do so", "next", "approved",
    "approve", "confirmed", "confirm", "agreed", "lgtm", "fine", "correct", "right",
    "thats right", "that is right", "carry on", "keep going", "sounds good", "looks good",
    "ship it", "make it so", "as recommended", "recommended", "your recommendation",
    "go with your recommendation", "the first option", "first option",
}
ASSENT_LEADS = {"y", "yes", "yep", "yeah", "yup", "ok", "okay", "sure", "great", "good", "perfect"}
COURTESIES = {"please", "pls", "thanks", "thank you", "ty"}
OPTION = re.compile(r"^(option\s+)?[a-d1-9]$")


BOOTSTRAP_SKILL = PLUGIN_PREFIX + "using-matt-pocock-skills"   # the routing policy: not a route


def is_declaration(skill: str) -> bool:
    """Whether invoking this skill declares a route for the current request. Every Seams skill
    but the bootstrap does (invoking the policy itself is not choosing a process: an eval run
    showed the model doing exactly that after an "Unknown skill" error), and so do Matt
    Pocock's process skills by bare name."""
    if not skill or skill == BOOTSTRAP_SKILL:
        return False
    if skill.startswith(PLUGIN_PREFIX):
        return len(skill) > len(PLUGIN_PREFIX)
    return skill in PROCESS_SKILLS


SKILLS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "skills")


def manual_seams_skill(bare: str) -> Optional[str]:
    """The full name of this plugin's manual-only skill called exactly `bare`, or None.

    Claude Code runs a plugin skill typed by its bare name (`/pr-review 42`) when no other command
    has that name, and a manual-only skill is only ever typed, so its bare form must declare. No
    other bare name does: a model-invocable Seams skill is declared through the Skill tool under its
    full name, and a bare name it shares with a Superpowers original or a project's own command may
    not be the Seams skill at all. The name is matched against the directory listing exactly, since
    a case-insensitive file system would find `PR-REVIEW` too."""
    if not bare or "/" in bare or bare.startswith("."):
        return None
    try:
        if bare not in os.listdir(SKILLS_DIR):
            return None
        with open(os.path.join(SKILLS_DIR, bare, "SKILL.md"), encoding="utf-8") as f:
            lines = f.read().split("\n")
    except OSError:
        return None
    if not lines or lines[0].strip() != "---":
        return None
    for line in lines[1:]:
        if line.strip() == "---":
            return None
        if line.strip() == "disable-model-invocation: true":
            return PLUGIN_PREFIX + bare
    return None


def slash_declaration(prompt: str) -> Optional[str]:
    """The process skill a typed slash command names, or None. Matt Pocock's bare names win over
    this plugin's, as they do in Claude Code (`/implement` is his); a manual-only Seams skill typed
    by its bare name declares under its full name."""
    text = (prompt or "").strip()
    if not text.startswith("/"):
        return None
    parts = text[1:].split()
    name = parts[0] if parts else ""
    if is_declaration(name):
        return name
    full = manual_seams_skill(name)
    return full if full and is_declaration(full) else None


# What Claude Code itself delivers as a user turn: a background task's or monitor's notice, a
# system reminder, a Stop hook's feedback, a subagent's hand-back. None of them is the user asking
# for something new.
MACHINE_NOTICES = ("[SYSTEM NOTIFICATION", "<task-notification>", "<system-reminder>", "Stop hook feedback:",
                   "Another Claude session sent a message:")


def is_continuation(prompt: str) -> bool:
    """A short go-ahead ("yes", "ok, do that", "option 2") that keeps the current request, or a
    notice Claude Code generated (a monitor's event, a system reminder, a Stop hook's feedback)."""
    if (prompt or "").lstrip().startswith(MACHINE_NOTICES):
        return True
    text = re.sub(r"[^\w\s-]", " ", (prompt or "").lower())
    text = re.sub(r"\s+", " ", text).strip()
    if not text or len(text) > 40:
        return False
    if OPTION.match(text):
        return True
    words = text.split()
    while len(words) > 1 and words[0] in ASSENT_LEADS:
        words = words[1:]
    for courtesy in sorted(COURTESIES, key=len, reverse=True):
        tail = courtesy.split()
        if len(words) > len(tail) and words[-len(tail):] == tail:
            words = words[:-len(tail)]
            break
    phrase = " ".join(words)
    return phrase in GO_PHRASES or phrase in COURTESIES or OPTION.match(phrase) is not None


# --- The ledger ---------------------------------------------------------------------------
# One JSON file per session: the current request's declarations, changes and last
# verification. Skill names, tool names and paths only; never command or prompt text.

LEDGER_VERSION = 2                            # 2: events ordered by seq, not by the clock


def _safe_name(session_id: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]", "_", session_id or "unknown")[:120]


def ledger_root(root: Optional[str] = None) -> str:
    """The ledger directory: per user, the tmux convention (`/tmp/tmux-1000`). On a shared
    Linux `/tmp` one directory for everyone would belong to whoever's session came first, and
    the next user's chmod would raise EPERM, failing their gate open."""
    return root or os.path.join(tempfile.gettempdir(), f"seams-{os.getuid()}")


def ledger_path(session_id: str, root: Optional[str] = None) -> str:
    return os.path.join(ledger_root(root), _safe_name(session_id) + ".json")


def empty_ledger(session_id: str) -> dict:
    return {"version": LEDGER_VERSION, "session": session_id, "started": time.time(), "seq": 0,
            "declarations": [], "changes": [], "verified_at": None, "verified_seq": 0}


def load_ledger(session_id: str, root: Optional[str] = None) -> dict:
    """The session's ledger, or an empty one when there is none or it cannot be read."""
    try:
        with open(ledger_path(session_id, root), encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict) and data.get("version") == LEDGER_VERSION:
            return dict(empty_ledger(session_id), **data)
    except (OSError, ValueError):
        pass
    return empty_ledger(session_id)


def save_ledger(session_id: str, ledger: dict, root: Optional[str] = None) -> None:
    """Write atomically, readable by this user only."""
    path = ledger_path(session_id, root)
    directory = os.path.dirname(path)
    os.makedirs(directory, mode=0o700, exist_ok=True)
    os.chmod(directory, 0o700)
    tmp = f"{path}.{os.getpid()}.tmp"
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(ledger, f)
    os.replace(tmp, path)


def reset_ledger(session_id: str, root: Optional[str] = None) -> None:
    try:
        os.remove(ledger_path(session_id, root))
    except OSError:
        pass


def _next_seq(ledger: dict) -> int:
    """Events are ordered by this counter, not by the clock, so a change and a verification
    written a microsecond apart cannot swap. (Two hooks writing the same ledger at once can
    still drop one event: the last save wins.)"""
    ledger["seq"] = ledger.get("seq", 0) + 1
    return ledger["seq"]


def new_request(ledger: dict) -> dict:
    ledger["started"] = time.time()
    ledger["declarations"] = []
    ledger["changes"] = []
    ledger["verified_at"] = None
    ledger["verified_seq"] = 0
    return ledger


def add_declaration(ledger: dict, skill: str, agent_id: Optional[str] = None) -> None:
    ledger["declarations"].append({"skill": skill, "at": time.time(), "seq": _next_seq(ledger),
                                   "agent": agent_id})


def add_change(ledger: dict, change: dict) -> None:
    ledger["changes"].append(dict(change, at=time.time(), seq=_next_seq(ledger)))


def mark_verified(ledger: dict) -> None:
    ledger["verified_at"] = time.time()
    ledger["verified_seq"] = _next_seq(ledger)


def cleanup_ledgers(root: Optional[str] = None, days: int = 7) -> None:
    """Remove ledgers no session has touched for `days`."""
    directory = ledger_root(root)
    cutoff = time.time() - days * 24 * 3600
    try:
        names = os.listdir(directory)
    except OSError:
        return
    for name in names:
        path = os.path.join(directory, name)
        try:
            if name.endswith(".json") and os.stat(path).st_mtime < cutoff:
                os.remove(path)
        except OSError:
            pass


# --- Project changes and the decision ------------------------------------------------------

EDITOR_TOOLS = {"Edit": "file_path", "Write": "file_path", "MultiEdit": "file_path",
                "NotebookEdit": "notebook_path"}
DOC_SUFFIXES = (".md", ".markdown", ".mdx")
TEMP_ROOTS = ("/tmp", "/private/tmp")     # plus tempfile.gettempdir(), which honors TMPDIR


def config_dir(explicit: Optional[str] = None) -> str:
    return explicit or os.environ.get("CLAUDE_CONFIG_DIR") or os.path.expanduser("~/.claude")


def _under(path: str, root: str) -> bool:
    root = os.path.realpath(root)
    return path == root or path.startswith(root.rstrip(os.sep) + os.sep)


def is_exempt_path(path: str, config: Optional[str] = None, cwd: Optional[str] = None) -> bool:
    """Temp directories and the Claude config directory are not the project.

    A path under the session's working directory is the project wherever that directory
    lives, so a repo checked out under the temp dir is still gated.
    """
    real = os.path.realpath(path)
    if real == "/dev/null":
        return True
    if cwd and _under(real, cwd):
        return False
    roots = (tempfile.gettempdir(), config_dir(config)) + TEMP_ROOTS
    return any(_under(real, root) for root in roots)


def change_for_event(event: dict, config_dir: Optional[str] = None) -> Optional[dict]:
    """The project change a PreToolUse event would make, or None when it makes none.

    Editor tools: the file, unless it is under a temp or config directory. Bash: the
    classifier's label, unless every path the command writes is placed and exempt by the same
    rule (a pull-request review writes only its evidence under the temp directory). Anything
    else: nothing.
    """
    tool = event.get("tool_name") or ""
    tool_input = event.get("tool_input") or {}
    if tool in EDITOR_TOOLS:
        path = tool_input.get(EDITOR_TOOLS[tool]) or ""
        if not path:
            return None
        if not os.path.isabs(path):
            path = os.path.join(event.get("cwd") or os.getcwd(), path)
        path = os.path.normpath(path)
        if is_exempt_path(path, config_dir, event.get("cwd")):
            return None
        return {"tool": tool, "path": path, "doc": path.lower().endswith(DOC_SUFFIXES)}
    if tool == "Bash":
        cwd = event.get("cwd")
        label = classify_command(tool_input.get("command") or "",
                                 is_exempt=lambda path: is_exempt_path(path, config_dir, cwd))
        if label:
            return {"tool": "Bash", "label": label, "doc": False}
    return None


def describe(change: dict) -> str:
    """How a refusal or a block names a change: the file, or the shell label."""
    if change.get("path"):
        return f"`{change['path']}`"
    return f"a shell command (`{change.get('label')}`)"


ROUTES = ("Route it first, with the Skill tool: `diagnosing-bugs` for something broken, "
          "`matt-pocock-workflow:grill` for a change to behavior, `tdd` or "
          "`matt-pocock-workflow:implement` to keep building an agreed design, "
          "`matt-pocock-workflow:trivial` for a change with no effect on behavior, data shape "
          "or security. Then retry this call.")


REFUSAL_PREFIX = "Seams gate: "                # a refused call's reason starts with it; the harness counts by it


SCRATCH = ("Scratch work is not a change: a write whose every path is an absolute path under the temp "
           "directory needs no declaration, from Edit, Write or a shell command.")


def deny_reason(change: dict) -> str:
    what = describe(change) if change["tool"] == "Bash" else f"editing {describe(change)}"
    return (f"{REFUSAL_PREFIX}{what} changes the project, and this request has no declaration yet: "
            f"no process skill has been invoked for it. {ROUTES} {SCRATCH}")


def decide_pre_tool_use(event: dict, ledger: dict, config_dir: Optional[str] = None) -> dict:
    """Allow, or deny with a reason. The change to record travels with an allow."""
    change = change_for_event(event, config_dir)
    if change is None:
        return {"decision": "allow", "reason": None, "change": None}
    if not ledger.get("declarations"):
        return {"decision": "deny", "reason": deny_reason(change), "change": None}
    return {"decision": "allow", "reason": None, "change": change}


# --- The done-check -----------------------------------------------------------------------

VERIFICATION_SKILLS = {PLUGIN_PREFIX + "verification-before-completion",
                       "superpowers:verification-before-completion", "verification-before-completion"}


def is_verification(skill: str) -> bool:
    """Whether this skill running counts as verification of the changes before it.

    It proves the skill ran, not that its commands were run honestly: the skill's own rules
    make the model run them and show the output, and the transcript shows whether it did.
    """
    return skill in VERIFICATION_SKILLS


def _needs_verification(change: dict) -> bool:
    """Code changes do; documentation and VCS operations (a commit after the checks) do not."""
    if change.get("doc"):
        return False
    return not str(change.get("label") or "").startswith("git ")


def unverified_changes(ledger: dict) -> list:
    """Changes that need verification, recorded after the last verification."""
    since = ledger.get("verified_seq") or 0
    return [c for c in ledger.get("changes", []) if _needs_verification(c) and c.get("seq", 0) > since]


def decide_stop(ledger: dict, stop_hook_active: bool) -> Optional[str]:
    """The reason to block this stop, or None. Blocks at most once per turn."""
    if stop_hook_active:
        return None
    pending = unverified_changes(ledger)
    if not pending:
        return None
    noun = "unverified change" if len(pending) == 1 else "unverified changes"
    return (f"Seams done-check: {len(pending)} {noun} to the project since the last verification "
            f"(for example {describe(pending[0])}). Run `{PLUGIN_PREFIX}verification-before-completion` "
            f"now with the Skill tool, show the verify commands' real output, then finish. This "
            f"check does not repeat in this turn.")


# --- The hook frame -----------------------------------------------------------------------


def run_hook(handler: Callable[[dict], Optional[dict]]) -> int:
    """Run a hook: the event from stdin, the handler's output (if any) to stdout as JSON.

    Any error, including unreadable input, prints nothing to stdout and writes the traceback
    to stderr for the debug log; the exit code is 0 either way, so a hook bug never blocks
    the user's work (fail open).
    """
    try:
        event = json.loads(sys.stdin.read() or "{}")
        output = handler(event)
        if output is not None:
            print(json.dumps(output))
    except Exception:
        traceback.print_exc(file=sys.stderr)
    return 0
