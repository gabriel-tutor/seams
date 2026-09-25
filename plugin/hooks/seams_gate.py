"""The gate: the rules the matt-pocock-workflow hooks share.

A change to the project is refused until the current request has a declaration: a Skill
invocation of a process skill, or a slash command the user typed for one. This module holds
the pure parts (what counts as a change, what counts as a declaration, what a continuation
is, the ledger's shape and the decisions) so the hooks stay thin. The routing harness scores a
shell write with the same classifier: it counts every write, where the gate also lets through
a write confined to the temp directory or the session's scratchpad. Python 3.9: macOS's system interpreter runs the hooks
when nothing newer is first on PATH.
"""
from __future__ import annotations

import json
import os
import re
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
GIT_VALUE_OPTIONS = {"-C", "-c", "--git-dir", "--work-tree"}   # git's own options that take a value
TARGET_DIRECTORY_COMMANDS = {"cp", "mv", "ln", "install"}         # -t DIR writes into DIR
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
NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
PUNCTUATION = set("();<>|&\n")
SEPARATOR_CHARS = set(";&|\n()")              # a token made of these alone ends a simple command
REDIRECT_TOKENS = {">", ">>", "&>", "&>>", ">|", ">&", "<>"}
INPUT_REDIRECTS = {"<", "<<", "<<-", "<<<", "<&"}
SHELL_KEYWORDS = {"if", "then", "else", "elif", "while", "until", "do", "!", "{", "}"}
ASSIGNING_BUILTINS = {"export", "declare", "local", "readonly", "typeset"}
# Builtins that may give a variable a value this module cannot follow.
REBINDING_BUILTINS = {"read", "mapfile", "readarray", "getopts", "unset", "printf", "let"}
HEREDOC = re.compile(r"<<(-?)[ \t]*(?:'([^'\n]*)'|\"([^\"\n]*)\"|(\\?)([A-Za-z_][A-Za-z0-9_]*))")
APPEND = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)\+=")
# Nesting far past any real command (substitutions in substitutions, arithmetic in arithmetic,
# `eval` of `eval`). Deeper is refused unread: reading it could exhaust Python's recursion, and a
# hook that crashes lets the call through.
MAX_NESTING = 50
TOO_DEEP = "a command nested too deeply to read"


class _TooDeep(Exception):
    """Raised past MAX_NESTING; classify_command turns it into the TOO_DEEP label."""


def _without_heredoc_text(command: str) -> tuple:
    """The command with each heredoc's text taken out, and the texts of its unquoted heredocs. A
    heredoc's lines are data, not commands; an unquoted one's `$(...)` and backquotes still run,
    which `_runs` finds in the text handed back. A `<<` inside quotes or a comment opens nothing;
    a heredoc whose end line never comes keeps all its lines as commands, which can never hide one."""
    lines = command.split("\n")
    out, texts, i, quote = [], [], 0, None
    while i < len(lines):
        line = lines[i]
        out.append(line)
        i += 1
        ends, j = [], 0
        while j < len(line):
            char = line[j]
            if quote:
                if char == "\\" and quote != "'":       # double and ANSI-C quotes escape; single quotes do not
                    j += 2
                    continue
                if char == quote[-1]:
                    quote = None
            elif char == "\\":
                j += 2
                continue
            elif line.startswith("$'", j):
                quote = "$'"
                j += 2
                continue
            elif char in "'\"":
                quote = char
            elif char == "#" and (j == 0 or line[j - 1] in " \t;|&("):
                break
            elif line.startswith("<<", j) and not line.startswith("<<<", j) and (j == 0 or line[j - 1] != "<"):
                found = HEREDOC.match(line, j)
                if found:
                    literal = found.group(2) is not None or found.group(3) is not None or found.group(4) == "\\"
                    ends.append((found.group(2) or found.group(3) or found.group(5), found.group(1) == "-", literal))
                    j = found.end()
                    continue
            j += 1
        for word, tabs, literal in ends:
            end = next((k for k in range(i, len(lines))
                        if (lines[k].lstrip("\t") if tabs else lines[k]) == word), None)
            if end is None:
                return "\n".join(out + lines[i:]), texts
            if not literal:
                texts.append("\n".join(lines[i:end]))
            i = end + 1
    return "\n".join(out), texts


def _end_of(text: str, i: int) -> Optional[int]:
    """Past the end of what opens at i, with whatever it nests, or None when it never ends: a
    quote (`'`, `"`, or ANSI-C `$'`), a backquote, `(`, or `$(` (i is the `$`). Inside single
    quotes everything is text; elsewhere a backslash escapes the next character. A command
    substitution's quotes and comments are its own, so the `)` in `"$(printf ')')"` ends nothing,
    and neither does the `>` in `'$1>0'`."""
    ansi = text.startswith("$'", i)
    start = i + 1 if ansi or text.startswith("$(", i) else i
    stack, j = ["$'" if ansi else text[start]], start + 1
    while stack and j < len(text):
        char, top = text[j], stack[-1]
        if top == "'":
            if char == "'":
                stack.pop()
        elif char == "\\":
            j += 1                                # the escaped character is text
        elif top == "$'":
            if char == "'":
                stack.pop()
        elif top == "(":
            if char == ")":
                stack.pop()
            elif char == "#" and text[j - 1] in " \t\n;&|(":
                end = text.find("\n", j)          # a comment runs to the end of its line
                j = len(text) if end == -1 else end
                continue
            elif text.startswith("$'", j):
                stack.append("$'")
                j += 1                            # past the `$`
            elif char in "'\"`(":
                stack.append(char)
        elif char == top:                         # the closing double quote or backquote
            stack.pop()
        elif top == '"' and char == "`":
            stack.append("`")
        elif top == '"' and text.startswith("$(", j):
            stack.append("(")
            j += 1                                # past the `$`
        j += 1
    return None if stack else j


def _is_arithmetic(text: str, i: int) -> bool:
    """Whether the `$((` at i is arithmetic: its inner parenthesis closes right before the outer
    one. `$((echo a); rm x)` is a command substitution holding a subshell, and runs both."""
    end, inner = _end_of(text, i), _end_of(text, i + 2)
    return end is not None and inner == end - 1


def _runs(text: str, depth: int = 0) -> list:
    """The commands that text runs where quotes are text, as inside double quotes or an unquoted
    heredoc: those of its `$(...)` and backquotes. Arithmetic, `$((...))`, runs only the
    substitutions it holds. One that never closes runs to the end of the text."""
    if depth > MAX_NESTING:
        raise _TooDeep
    out, j = [], 0
    while j < len(text):
        if text[j] == "\\":
            j += 2
            continue
        if text.startswith("$(", j) or text[j] == "`":
            start, end = j + (1 if text[j] == "`" else 2), _end_of(text, j)
            if end is None:
                out.append(text[start:])
                break
            if text.startswith("$((", j) and _is_arithmetic(text, j):
                out += _runs(text[j + 3:end - 2], depth + 1)
            else:
                out.append(text[start:end - 1])
            j = end
            continue
        j += 1
    return out


def _word_runs(word: str) -> list:
    """The commands a shell word runs: its command substitutions, bare or inside double quotes.
    Single and ANSI-C quotes run nothing. The word comes from `_tokens`, so its quotes close."""
    out, j = [], 0
    while j < len(word):
        char = word[j]
        if char == "\\":
            j += 2
            continue
        if char in "'\"`" or word.startswith("$(", j) or word.startswith("$'", j):
            end = _end_of(word, j)
            if end is None:                       # a rough token: its commands are segments already
                break
            if char == '"':
                out += _runs(word[j + 1:end - 1])
            elif char != "'" and not word.startswith("$'", j):
                out += _runs(word[j:end])
            j = end
            continue
        j += 1
    return out


OPERATORS = sorted(REDIRECT_TOKENS | INPUT_REDIRECTS | {"&&", "||", ";;", "|&"} | PUNCTUATION,
                   key=len, reverse=True)      # longest first
BLANKS = " \t\r"
ORDINARY = re.compile("[^" + re.escape("\\'\"`$" + BLANKS + "".join(sorted(PUNCTUATION))) + "]+")  # only themselves


def _rough_tokens(command: str) -> list:
    """A split on every operator, quoted or not: for a command whose quotes never close, which the
    shell would not run as written. It may see an operator in quoted text but never misses one."""
    return re.findall(r"\n|&&|\|\||[;|&()]|>>|>&|&>|>\||<<|<|>|[^\s;|&()<>]+", command.replace("\\\n", ""))


def _tokens(command: str) -> list:
    """Shell words with their quotes kept, so a quoted `>` is not an operator, and the operators
    between them, each on its own (`;>` is `;` then `>`). A quote may open inside a word
    (`x="a > b"`), and a command substitution is part of the word it stands in. A newline outside
    quotes ends a command as `;` does; a backslash-newline joins the lines; a `#` that starts a word
    opens a comment, and one inside a word (`a#b`, `$#`) is text."""
    out, word, i, n = [], [], 0, len(command)    # word: the current word's pieces, joined once
    while i < n:
        char = command[i]
        if char == "\\":
            if command.startswith("\n", i + 1):
                i += 2                            # a line continuation
                continue
            end = i + 2
        elif char in "'\"`" or command.startswith("$(", i) or command.startswith("$'", i):
            end = _end_of(command, i)
            if end is None:
                return _rough_tokens(command)
        elif char == "#" and not word:
            end = command.find("\n", i)
            i = n if end == -1 else end           # the newline still ends the command
            continue
        elif char in BLANKS or char in PUNCTUATION:
            if word:
                out.append("".join(word))
                word = []
            operator = "" if char in BLANKS else next((o for o in OPERATORS if command.startswith(o, i)), char)
            if operator:
                out.append(operator)
            i += len(operator) or 1
            continue
        else:
            run = ORDINARY.match(command, i)
            end = run.end() if run else i + 1     # a `$` that opens no substitution is itself
        word.append(command[i:end])
        i = end
    if word:
        out.append("".join(word))
    return out


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


def _command_name(token: str) -> str:
    """A command word as the shell finds it: quotes and a leading backslash (`\\rm`) aside."""
    return os.path.basename(_unquote(token)).lstrip("\\")


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
        if not words or _command_name(words[0]) not in WRAPPERS:
            return words
        wrapper = _command_name(words.pop(0))
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
# A write is let through only when every path it writes is placed and scratch (see
# change_for_event): the rule Edit and Write follow for the temp directory. A path is placed when
# it is written out in full, or built from $TMPDIR or from a variable an earlier assignment in the
# same command set. A relative path, a glob, a command substitution, an escape, a variable set
# anywhere else, or one a loop, `read`, `unset` or `eval` may have changed is not placed, and the
# write counts. So does an option with its value attached (`--target-directory=DIR`, `-tDIR`).
# Single quotes are literal, as in the shell.

VARIABLE = re.compile(r"\$(?:\{([A-Za-z_][A-Za-z0-9_]*)(?:(:?-)([^}$]*))?\}|([A-Za-z_][A-Za-z0-9_]*))")
GLOB_CHARS = set("*?[{")                      # { for brace expansion
PLAIN_OPTION = re.compile(r"^--?[A-Za-z0-9][A-Za-z0-9-]*$")      # an option with no value attached
SHORT_OPTIONS = re.compile(r"^-[A-Za-z]+$")


def _initial_env() -> dict:
    """The variables known before the command runs: TMPDIR, as the hook sees it (None when unset,
    so `${TMPDIR:-/tmp}` is /tmp). Any other variable is unknown until the command sets it."""
    return {"TMPDIR": os.environ.get("TMPDIR") or None}


def _expand(token: str, env: dict) -> Optional[str]:
    """A token's text after quote removal and variable expansion, or None when it cannot be known.
    A token may join quoted and bare parts (`"$EVID"/log.txt`), each read as the shell reads it:
    a single-quoted part is literal, and a bare part's value must not split or glob."""
    out, i = [], 0
    while i < len(token):
        if token[i] in "'\"":
            end = token.find(token[i], i + 1)
            if end == -1:
                return None
            part = token[i + 1:end] if token[i] == "'" else _expand_part(token[i + 1:end], env, bare=False)
            i = end + 1
        else:
            end = min([k for k in (token.find("'", i), token.find('"', i)) if k != -1] or [len(token)])
            part = _expand_part(token[i:end], env, bare=True)
            i = end
        if part is None:
            return None
        out.append(part)
    return "".join(out)


def _expand_part(text: str, env: dict, bare: bool) -> Optional[str]:
    """A double-quoted or bare part of a token after variable expansion, or None when unknown."""
    if "$(" in text or "`" in text or "\\" in text:
        return None
    unknown, values = [], []

    def value(match):
        name, operator, default = match.group(1) or match.group(4), match.group(2), match.group(3)
        if name not in env:               # set outside this command, or in a way it cannot follow
            unknown.append(name)
            return ""
        current = env[name]               # None: known to be unset
        if operator == ":-":
            result = current or default
        elif operator == "-":
            result = default if current is None else current
        else:
            result = current or ""
        values.append(result)
        return result

    text = VARIABLE.sub(value, text)
    if unknown or "$" in text:
        return None
    if bare and values and ("IFS" in env or any(set(v) & set(" \t\n*?[{") for v in values)):
        return None                       # unquoted, the value would split or glob
    return text


def _placed_path(token: str, env: dict) -> Optional[str]:
    """The absolute path a token names, or None when it is not placed."""
    text = _expand(token, env)
    if text is None or not text or GLOB_CHARS & set(text) or not os.path.isabs(text):
        return None
    return os.path.normpath(text)


def _take_assignments(segment: list, env: dict) -> bool:
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


def _forget_rebound(words: list, env: dict) -> None:
    """Forget the variables a loop or a builtin may give a value this module cannot follow;
    `eval`, `source` and `.` may set any of them."""
    words = [_unquote(w) for w in _words(words)]
    if not words:
        return
    head = words[0]
    if head in ("for", "select") and len(words) > 1:
        env.pop(words[1], None)
    elif head in ("eval", "source", "."):
        env.clear()
    elif head in REBINDING_BUILTINS or head in ASSIGNING_BUILTINS:
        for word in words[1:]:
            name = word.split("=", 1)[0]
            if NAME.match(name):
                env.pop(name, None)


def _operands(args: list) -> Optional[list]:
    """The arguments that are not options: everything after `--`, and every word that does not
    start with `-`. None when an option carries its value attached, since that value may be the
    path written. An option's separate value counts as an operand, which only makes a write count."""
    out, options_done = [], False
    for arg in args:
        bare = _unquote(arg)
        if not options_done and bare == "--":
            options_done = True
        elif options_done or not bare.startswith("-") or bare == "-":
            out.append(arg)
        elif not PLAIN_OPTION.match(bare):
            return None
    return out


def _into_target_directory(args: list) -> bool:
    """cp, mv, ln or install given -t DIR (in any spelling): what they write lies under DIR."""
    return any(a.startswith("--target-directory") or (SHORT_OPTIONS.match(a) and "t" in a) for a in args)


def _git_parts(words: list) -> tuple:
    """A git command's subcommand and its raw arguments, after git's own options (-C DIR and the like)."""
    rest = words[1:]
    while rest and _unquote(rest[0]).startswith("-"):
        rest = rest[2:] if _unquote(rest[0]) in GIT_VALUE_OPTIONS and len(rest) > 1 else rest[1:]
    return (_unquote(rest[0]), rest[1:]) if rest else ("", [])


def _git_label(words: list) -> Optional[str]:
    sub, raw = _git_parts(words)
    if not sub:
        return None
    args = [_unquote(r) for r in raw]
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


def _worktree_paths(words: list) -> Optional[list]:
    """The worktree paths `git worktree add --detach|remove|move` writes, or None when they cannot
    be told or a branch may change: without --detach, `add` makes a branch named after the path, or
    checks out (and may create) the one it names."""
    _, raw = _git_parts(words)
    if not raw:
        return None
    action, rest = _unquote(raw[0]), raw[1:]
    flags = {_unquote(a) for a in rest}
    if action == "add" and (not flags & {"--detach", "-d"} or flags & {"-b", "-B", "--orphan"}):
        return None
    operands, skip = [], False
    for arg in rest:
        bare = _unquote(arg)
        if skip:
            skip = False
        elif bare == "--reason":
            skip = True
        elif bare.startswith("-"):
            if not PLAIN_OPTION.match(bare):
                return None
        else:
            operands.append(arg)
    if action == "add":
        return operands[:1] or None           # the new worktree's path; the commit after it is read
    return operands or None


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


def _download(base: str, raw: list) -> tuple:
    """curl or wget writing a file: the label and the paths written, None for the paths when they
    lie under the working directory. (None, None) when the download only goes to stdout."""
    args = [_unquote(a) for a in raw]
    targets, somewhere = [], False           # somewhere: a file named by the server, in the cwd
    for i, arg in enumerate(args):
        after = raw[i + 1] if i + 1 < len(raw) else None
        if base == "curl":
            if arg in ("-o", "--output"):
                targets.append(after or "")
            elif arg.startswith("--output="):
                targets.append(arg[len("--output="):])
            elif arg in ("-O", "--remote-name", "--remote-name-all") or arg.startswith("--output-dir"):
                somewhere = True
            elif SHORT_OPTIONS.match(arg) and ("o" in arg or "O" in arg):
                if "O" in arg:
                    somewhere = True
                elif arg.endswith("o"):
                    targets.append(after or "")
                else:
                    targets.append(arg[arg.index("o") + 1:])
        else:
            if arg in ("-O", "--output-document"):
                targets.append(after or "")
            elif arg.startswith("--output-document="):
                targets.append(arg[len("--output-document="):])
            elif arg.startswith("-O") and len(arg) > 2 and not arg.startswith("--"):
                targets.append(arg[2:])
    if base == "wget":
        if any(a in ("-O-", "-qO-") for a in args) or any(_unquote(t) == "-" for t in targets):
            return None, None                 # to stdout
        return "a download to a file", (targets or None)
    if not targets and not somewhere:
        return None, None
    return "a download to a file", (None if somewhere else targets)


def _archive(base: str, raw: list) -> tuple:
    """tar extracting or creating, and unzip extracting: the label and the paths written, None when
    they lie under the working directory. (None, None) when it only lists or tests."""
    args = [_unquote(a) for a in raw]

    def value(*names: str):
        for i, arg in enumerate(args):
            for name in names:
                if arg == name and i + 1 < len(raw):
                    return [raw[i + 1]]
                if name.startswith("--") and arg.startswith(name + "="):
                    return [arg[len(name) + 1:]]
        return None

    if base == "unzip":
        if any(a in ("-l", "-t", "-v", "-Z", "-p", "-z") for a in args):
            return None, None
        return "unzip", value("-d")
    letters = set()
    for i, arg in enumerate(args):
        if SHORT_OPTIONS.match(arg) or (i == 0 and re.match(r"^[A-Za-z]+$", arg)):
            letters |= set(arg.lstrip("-"))
    longs = {a.split("=", 1)[0] for a in args if a.startswith("--")}
    if "x" in letters or longs & {"--extract", "--get"}:
        return "tar -x", value("-C", "--directory")
    if letters & set("cruA") or longs & {"--create", "--append", "--update", "--catenate", "--concatenate",
                                          "--delete"}:
        archive = value("--file")
        for i, arg in enumerate(args):
            if (SHORT_OPTIONS.match(arg) or (i == 0 and re.match(r"^[A-Za-z]+$", arg))) and "f" in arg \
                    and i + 1 < len(raw):
                archive = [raw[i + 1]]
        return "tar -c", archive
    return None, None


def _sort_output(raw: list) -> tuple:
    args = [_unquote(a) for a in raw]
    for i, arg in enumerate(args):
        if arg == "-o":
            return "sort -o", ([raw[i + 1]] if i + 1 < len(raw) else None)
        if arg.startswith("--output="):
            return "sort -o", [arg[len("--output="):]]
        if arg.startswith("-o") and len(arg) > 2:
            return "sort -o", [arg[2:]]
    return None, None


def _find_roots(args: list) -> list:
    roots = []
    for arg in args:
        if _unquote(arg)[:1] in {"-", "(", "!", ")"}:
            break
        roots.append(arg)
    return roots


def _inline_program_writes(base: str, args: list, command: str) -> bool:
    if not INTERPRETERS.match(base):
        return False
    inline = any(a in INLINE_FLAGS for a in args) or "<<" in command
    return bool(inline and WRITE_PATTERNS.search(command))


def _what_it_writes(segment: list, command: str, env: dict, is_exempt, depth: int = 0) -> tuple:
    """What a simple command (its redirections removed) writes: its label and the raw tokens of
    the paths it writes, or None for the paths when they cannot be told. (None, None): no write."""
    words = _words(segment)
    if not words:
        return None, None
    base = _command_name(words[0])
    raw = words[1:]
    args = [_unquote(w) for w in raw]
    by_xargs = any(_command_name(w) == "xargs" for w in segment[:len(segment) - len(words)])
    if base in {"bash", "sh", "zsh"} and "-c" in args:
        inner = args[args.index("-c") + 1:][:1]
        return (_classify(inner[0], is_exempt, dict(env), depth + 1) if inner else None), None
    if base == "eval":                        # it runs its arguments, joined, as a command
        return (_classify(" ".join(args), is_exempt, dict(env), depth + 1) if args else None), None
    if base in FILE_COMMANDS:                 # xargs supplies its operands; patch names its own files
        if by_xargs or base == "patch" or (base in TARGET_DIRECTORY_COMMANDS and _into_target_directory(args)):
            return base, None
        return base, _operands(raw)
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
    for known, parse in (({"curl", "wget"}, _download), ({"tar", "unzip"}, _archive)):
        if base in known:
            label, targets = parse(base, raw)
            if label:
                return label, targets
    if base == "rsync":                       # its options can write logs and backups anywhere
        return "rsync", None
    if base == "sort":
        label, targets = _sort_output(raw)
        if label:
            return label, targets
    if "--write" in args:
        return "a --write flag", None
    if "--fix" in args:
        return "a --fix flag", None
    if "-w" in args and any(a in FORMATTERS for a in [base] + args):
        return "a --write flag", None
    if base == "find":
        for flag in ("-exec", "-execdir", "-ok", "-okdir"):
            if flag in args:
                after = args[args.index(flag) + 1:]
                if after and os.path.basename(after[0]) in FILE_COMMANDS:   # it writes where its command says
                    return f"find -exec {os.path.basename(after[0])}", None
        if "-delete" in args:
            return "find -delete", _find_roots(raw) or None   # no root: the working directory
    if _inline_program_writes(base, args, command):
        return "an inline program that writes", None
    return None, None


def _all_exempt(tokens: Optional[list], env: dict, is_exempt) -> bool:
    if tokens is None:
        return False
    for token in tokens:
        path = _placed_path(token, env)
        if path is None or not is_exempt(path):
            return False
    return True


def _segment_label(segment: list, command: str, env: dict, is_exempt, depth: int = 0) -> Optional[str]:
    words, redirects = _split_redirects(segment)
    label, targets = _what_it_writes(words, command, env, is_exempt, depth)
    if is_exempt is None:                     # every write counts; a redirection names it first
        return "a redirect to a file" if redirects else label
    if label and not _all_exempt(targets, env, is_exempt):
        return label
    if redirects and not _all_exempt(redirects, env, is_exempt):
        return "a redirect to a file"
    return None


def _classify(command: str, is_exempt, env: dict, depth: int = 0) -> Optional[str]:
    if not command or not command.strip():
        return None
    if depth > MAX_NESTING:
        raise _TooDeep
    text, heredocs = _without_heredoc_text(command)
    tokens = _tokens(text)
    runs = [run for body in heredocs for run in _runs(body)] + [run for token in tokens for run in _word_runs(token)]
    for inner in runs:                            # what $(...) and backquotes run
        label = _classify(inner, is_exempt, dict(env), depth + 1)
        if label:
            return label
    for segment in _segments(tokens):
        _forget_rebound(_split_redirects(segment)[0], env)
        for word in segment:
            appended = APPEND.match(word)
            if appended:
                env.pop(appended.group(1), None)
        if _take_assignments(segment, env):
            continue
        label = _segment_label(segment, command, env, is_exempt, depth)
        if label:
            return label
    return None


def classify_command(command: str, is_exempt: Optional[Callable[[str], bool]] = None) -> Optional[str]:
    """The label for what a shell command changes, or None when it looks read-only.

    With `is_exempt`, a write whose every path is placed (see above) and exempt is not a change:
    the gate passes its scratch rule. Without it every write counts, which is how the routing
    harness scores a shell write before the first Skill call.
    """
    try:
        return _classify(command, is_exempt, _initial_env())
    except (_TooDeep, RecursionError):
        return TOO_DEEP


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
# A skill's name as Claude Code writes it (matched whole); anything else in a ledger is damage.
SKILL_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9:._-]{0,79}")


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
    except OSError:
        return None
    return PLUGIN_PREFIX + bare if _manual_only(os.path.join(SKILLS_DIR, bare, "SKILL.md")) else None


def _manual_only(path: str) -> bool:
    """Whether the SKILL.md at `path` says `disable-model-invocation: true` in its frontmatter: only the
    user can invoke that skill, and Claude Code refuses a Skill call for it."""
    try:
        with open(path, encoding="utf-8") as f:
            lines = f.read().split("\n")
    except (OSError, ValueError):
        return False
    if not lines or lines[0].strip() != "---":
        return False
    for line in lines[1:]:
        if line.strip() == "---":
            return False
        if line.strip() == "disable-model-invocation: true":
            return True
    return False


def typed_only(skill: str, config: Optional[str] = None, cwd: Optional[str] = None) -> bool:
    """Whether only the user can invoke this skill, so the Skill tool cannot declare it again: a Seams
    skill by the plugin's own file; one of Matt Pocock's by the copy Claude Code loads, from the config
    directory or the project's .claude/skills (either one marking it counts). A name that is not a
    plain skill name, or a skill with no file there, is taken as invocable."""
    if skill.startswith(PLUGIN_PREFIX):
        return manual_seams_skill(skill[len(PLUGIN_PREFIX):]) is not None
    if not SKILL_NAME.fullmatch(skill) or ":" in skill:
        return False
    roots = [os.path.join(config_dir(config), "skills")] + ([os.path.join(cwd, ".claude", "skills")] if cwd else [])
    return any(_manual_only(os.path.join(root, skill, "SKILL.md")) for root in roots)


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
# for something new. A hand-back reaches the hook as `<agent-message from="...">`; the transcript
# shows it under an "Another Claude session sent a message:" line, kept here as well.
MACHINE_NOTICES = ("[SYSTEM NOTIFICATION", "<task-notification>", "<system-reminder>", "Stop hook feedback:",
                   "<agent-message ", "Another Claude session sent a message:")


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
# verification, and the skills a typed prompt expanded to, under its prompt id until it is
# submitted. Skill names, tool names, paths and ids only; never command or prompt text.

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
            "declarations": [], "changes": [], "verified_at": None, "verified_seq": 0, "expanded": [],
            "request_prompt": None}


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


# --- Prompts ------------------------------------------------------------------------------
# Claude Code runs the UserPromptExpansion hook once for each skill a typed prompt expands, and only
# then the UserPromptSubmit hook for the prompt itself (captured on 2.1.282), both with the prompt's
# id. A typed skill therefore waits in the ledger until its prompt starts the request it declares.
# The hooks reference lists the two the other way round, so an expansion that arrives after its
# prompt hook declares that prompt's request directly.


def _listed(ledger: dict, key: str) -> list:
    """A ledger list, or an empty one when the file holds something else there: a hook that raised on
    it would fail open and leave the old request, and its declarations, in place."""
    value = ledger.get(key)
    return value if isinstance(value, list) else []


def record_expansion(event: dict, ledger: dict) -> bool:
    """Keep what a UserPromptExpansion event expanded, under its prompt's id, until the prompt is
    submitted: the process skill, or None for anything else, since once an expansion arrived it alone
    says what the prompt typed. An earlier prompt's leftovers go (its prompt hook never ran). When the
    prompt was submitted first and started the current request, a process skill declares that request
    at once. True when the ledger changed. Only a skill or command (`slash_command`) can declare; an
    MCP server's prompt (`mcp_prompt`) never does, whatever its name. Without a prompt id nothing ties
    it to a request."""
    prompt_id, skill = event.get("prompt_id"), event.get("command_name")
    if not prompt_id:
        return False
    declares = event.get("expansion_type") == "slash_command" and isinstance(skill, str) and is_declaration(skill)
    if prompt_id == ledger.get("request_prompt"):     # its prompt hook ran first: the request is this prompt's
        declared = [d.get("skill") for d in _listed(ledger, "declarations") if isinstance(d, dict)]
        if not declares or skill in declared:
            return False
        add_declaration(ledger, skill)
        return True
    kept = [e for e in _listed(ledger, "expanded") if isinstance(e, dict) and e.get("prompt_id") == prompt_id]
    ledger["expanded"] = kept + [{"prompt_id": prompt_id, "skill": skill if declares else None}]
    return True


def submit_prompt(event: dict, ledger: dict, config_dir: Optional[str] = None) -> dict:
    """A submitted prompt: a go-ahead or a machine notice keeps the request; anything else starts a new
    one, declared by the process skills typed in it: the expansions recorded for this prompt, or, when
    none arrived, its leading slash command. After a declared request, a new one that typed no route of
    its own gets the lapse hint. Returns {"changed": whether the ledger changed, "context": the lapse
    hint or None}. A damaged entry is skipped rather than raised on: a hook that fails here would leave
    the old request, and its declarations, in place."""
    prompt, prompt_id = event.get("prompt") or "", event.get("prompt_id")
    expanded = _listed(ledger, "expanded")
    mine = [e for e in expanded if isinstance(e, dict) and prompt_id and e.get("prompt_id") == prompt_id]
    if mine:                                   # what ran; the prompt's parse would only guess from the typed word
        typed = [e.get("skill") for e in mine if isinstance(e.get("skill"), str) and is_declaration(e["skill"])]
    else:
        typed = [s for s in [slash_declaration(prompt)] if s]
    ledger["expanded"] = []
    if not typed and is_continuation(prompt):
        return {"changed": bool(expanded), "context": None}
    lapsed = [] if typed else [d.get("skill") for d in _listed(ledger, "declarations") if isinstance(d, dict)]
    new_request(ledger)
    ledger["request_prompt"] = prompt_id              # a late expansion of this prompt still declares it
    for skill in dict.fromkeys(typed):
        add_declaration(ledger, skill)
    return {"changed": True, "context": _lapse_hint(lapsed, config_dir, event.get("cwd"))}


LAPSE_NAMES = 5


def _lapse_hint(skills: list, config: Optional[str] = None, cwd: Optional[str] = None) -> Optional[str]:
    """The facts a new request after a declared one gives Claude: which declarations lapsed, that
    invoking one again continues that work (or, for a skill only the user can type, that the user
    types it again or the work takes a route Claude can invoke), that new work routes afresh. None
    when nothing lapsed."""
    names = list(dict.fromkeys(s for s in skills if isinstance(s, str) and SKILL_NAME.fullmatch(s)))[:LAPSE_NAMES]
    if not names:
        return None
    manual = {name for name in names if typed_only(name, config, cwd)}
    listed = ", ".join(f"`{name}`" + (" (only the user can type it)" if name in manual else "") for name in names)
    which = f"`{names[0]}`" if len(names) == 1 else "the one it used"
    if not manual:
        how = f"invoking {which} again with the Skill tool restores the declaration"
    elif len(manual) == len(names):
        how = f"the Skill tool cannot invoke {which}: the user types it again, or the work takes a route Claude can invoke"
    else:
        how = (f"invoking {which} again with the Skill tool restores the declaration, unless only the user can "
               "type it: then the user types it again, or the work takes a route Claude can invoke")
    noun = "declaration" if len(names) == 1 else "declarations"
    return (f"Seams: this message started a new request, so the previous request's {noun} lapsed: {listed}. "
            "The gate refuses the next change to the project until a process skill is invoked for this request. "
            f"If this message continues that work, {how}; new work needs its own route.")


# --- Project changes and the decision ------------------------------------------------------

EDITOR_TOOLS = {"Edit": "file_path", "Write": "file_path", "MultiEdit": "file_path",
                "NotebookEdit": "notebook_path"}
DOC_SUFFIXES = (".md", ".markdown", ".mdx")
TEMP_ROOTS = ("/tmp", "/private/tmp")     # plus tempfile.gettempdir(), which honors TMPDIR
# PowerShell has no classifier here: before a declaration only these run, each on its own with
# plain arguments. A pipe, a separator, a redirect, a parenthesis (a subexpression or a call), a
# script block, a backtick (PowerShell's escape and line continuation) or a second line makes a
# command something else, quoted or not.
POWERSHELL_READS = {"get-content", "get-childitem", "select-string"}
POWERSHELL_GIT_READS = {"status", "diff", "log"}
POWERSHELL_UNSAFE = set(";|&<>(){}`\n\r")
POWERSHELL_QUOTES = re.compile("[\"'\u2018\u2019\u201a\u201b\u201c\u201d\u201e]")   # PowerShell's, typographic ones too


def config_dir(explicit: Optional[str] = None) -> str:
    return explicit or os.environ.get("CLAUDE_CONFIG_DIR") or os.path.expanduser("~/.claude")


def _under(path: str, root: str) -> bool:
    root = os.path.realpath(root)
    return path == root or path.startswith(root.rstrip(os.sep) + os.sep)


def _scratchpad_roots(scratchpad: object) -> tuple:
    """The session's scratchpad (the hook input's `scratchpad_dir`, Claude Code 2.1.257 and later) as
    a scratch root: none when the field is absent or is not an absolute path, so a missing field
    leaves the temp directories' rules as they were."""
    return (scratchpad,) if isinstance(scratchpad, str) and os.path.isabs(scratchpad) else ()


def is_exempt_path(path: str, config: Optional[str] = None, cwd: Optional[str] = None,
                   scratchpad: object = None) -> bool:
    """Temp directories, the session's scratchpad and the Claude config directory are not the project.

    A path under the session's working directory is the project wherever that directory
    lives, so a repo checked out under the temp dir is still gated.
    """
    real = os.path.realpath(path)
    if real == "/dev/null":
        return True
    if cwd and _under(real, cwd):
        return False
    roots = (tempfile.gettempdir(), config_dir(config)) + TEMP_ROOTS + _scratchpad_roots(scratchpad)
    return any(_under(real, root) for root in roots)


def is_scratch_path(path: str, cwd: Optional[str] = None, scratchpad: object = None) -> bool:
    """Where a shell command may write without a declaration: /dev/null, or under a temp directory or
    the session's scratchpad, and outside the session's working directory. Narrower than
    is_exempt_path: the Claude config directory is not scratch, since a shell command there could
    delete the user's settings."""
    real = os.path.realpath(path)
    if real == "/dev/null":
        return True
    if cwd and _under(real, cwd):
        return False
    roots = (tempfile.gettempdir(),) + TEMP_ROOTS + _scratchpad_roots(scratchpad)
    return any(_under(real, root) for root in roots)


def powershell_reads(command: str) -> bool:
    """Whether a PowerShell command is on the read-only list, run on its own with plain arguments.
    `git diff` and `git log` write a file when given --output, however it is quoted: PowerShell
    removes the quotes, and joins `--out""put` into one argument, before git reads it."""
    text = (command or "").strip()
    if not text or POWERSHELL_UNSAFE & set(text):
        return False
    words = text.lower().split()
    if words[0] == "git":
        return (len(words) > 1 and words[1] in POWERSHELL_GIT_READS
                and "--output" not in POWERSHELL_QUOTES.sub("", text.lower()))
    return words[0] in POWERSHELL_READS


def _powershell_label(command: str) -> str:
    """git's own label for a git command run on its own, so the done-check treats a commit after the
    checks as it treats one from Bash; "PowerShell" for anything else."""
    text = command.strip()
    words = text.split()
    if words[0].lower() == "git" and not POWERSHELL_UNSAFE & set(text):
        return _git_label(words) or "PowerShell"
    return "PowerShell"


def change_for_event(event: dict, config_dir: Optional[str] = None) -> Optional[dict]:
    """The project change a PreToolUse event would make, or None when it makes none.

    Editor tools: the file, unless it is under a temp directory, the session's scratchpad or the
    config directory. Bash, and a Monitor watch, whose command runs in the Bash tool's shell: the
    classifier's label, unless every path the command writes is placed and scratch (a pull-request
    review writes only its evidence under the temp directory); a WebSocket watch runs no command.
    PowerShell: every command, unless it is on the read-only list. Anything else: nothing.
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
        if is_exempt_path(path, config_dir, event.get("cwd"), event.get("scratchpad_dir")):
            return None
        return {"tool": tool, "path": path, "doc": path.lower().endswith(DOC_SUFFIXES)}
    if tool in ("Bash", "Monitor"):
        cwd, scratchpad = event.get("cwd"), event.get("scratchpad_dir")
        label = classify_command(tool_input.get("command") or "",
                                 is_exempt=lambda path: is_scratch_path(path, cwd, scratchpad))
        if label:
            return {"tool": tool, "label": label, "doc": False}
    if tool == "PowerShell":
        command = tool_input.get("command") or ""
        if command.strip() and not powershell_reads(command):
            return {"tool": "PowerShell", "label": _powershell_label(command), "doc": False}
    return None


def describe(change: dict) -> str:
    """How a refusal or a block names a change: the file, the shell label, or a PowerShell command."""
    if change.get("path"):
        return f"`{change['path']}`"
    if change.get("tool") == "PowerShell":
        return "a PowerShell command"
    return f"a shell command (`{change.get('label')}`)"


ROUTES = ("Route it first, with the Skill tool: `diagnosing-bugs` for something broken, "
          "`matt-pocock-workflow:grill` for a change to behavior, `tdd` or "
          "`matt-pocock-workflow:implement` to keep building an agreed design, "
          "`matt-pocock-workflow:trivial` for a change with no effect on behavior, data shape "
          "or security. Then retry this call.")


REFUSAL_PREFIX = "Seams gate: "                # a refused call's reason starts with it; the harness counts by it


SCRATCH = ("Scratch work is not a change: a write whose every path is an absolute path under the temp "
           "directory or the session's scratchpad needs no declaration, from Edit, Write or a shell command.")


POWERSHELL_LIST = ("Before a declaration PowerShell runs only `Get-Content`, `Get-ChildItem`, `Select-String`, "
                   "`git status`, `git diff` and `git log`, each on its own with plain arguments: no pipe, "
                   "separator, redirect, parenthesis, script block, backtick or second line.")


def deny_reason(change: dict) -> str:
    if change["tool"] == "PowerShell":
        what, rule = "a PowerShell command outside the read-only list counts as a change", POWERSHELL_LIST
    else:
        what = (f"editing {describe(change)}" if change.get("path") else describe(change)) + " changes the project"
        rule = SCRATCH
    return (f"{REFUSAL_PREFIX}{what}, and this request has no declaration yet: no process skill has been "
            f"invoked for it. {ROUTES} {rule}")


# Seams' read-only agents (plugin/agents/), as the hook input's `agent_type` names a plugin's agent: by its
# plugin-scoped name. They never change the project, whatever the request has declared.
READ_ONLY_AGENTS = {PLUGIN_PREFIX + "scout", PLUGIN_PREFIX + "reviewer"}


def read_only_reason(agent: str, change: dict) -> str:
    what = (f"editing {describe(change)}" if change.get("path") else describe(change)) + " changes the project"
    return (f"{REFUSAL_PREFIX}`{agent}` is a read-only agent, and {what}: a read-only agent never changes the "
            "project, whatever the request has declared. Report the change instead, and the main conversation "
            f"makes it. {SCRATCH}")


def decide_pre_tool_use(event: dict, ledger: dict, config_dir: Optional[str] = None) -> dict:
    """Allow, or deny with a reason. The change to record travels with an allow."""
    change = change_for_event(event, config_dir)
    if change is None:
        return {"decision": "allow", "reason": None, "change": None}
    agent = event.get("agent_type")
    if isinstance(agent, str) and agent in READ_ONLY_AGENTS:
        return {"decision": "deny", "reason": read_only_reason(agent, change), "change": None}
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
    """The done-check's request for verification at this stop, or None. Asks at most once per turn:
    the second stop of a turn (stop_hook_active) always ends it."""
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
