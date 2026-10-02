"""The gate's shell reader: what a shell command writes, and whether a read-only agent's command only reads.

A shell command is read the way the shell reads it, as far as a best-effort mesh can: its quotes, heredocs,
substitutions, redirections, wrappers and variables. classify_command labels a command that changes files (the
gate refuses it before a declaration and the done-check counts it after one); shell_read_problem holds a
read-only agent's command to a list of reads. Only the PreToolUse hook loads it, for a call that needs it.
Python 3.9: macOS's system interpreter runs the hooks when nothing newer is first on PATH.
"""
from __future__ import annotations

import os
import re
from collections.abc import Callable

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


def _end_of(text: str, i: int) -> int | None:
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
# write counts. So does an option with its value attached (`--target-directory=DIR`, `-tDIR`), and
# a path with a `..` segment: the kernel follows a symlink before the `..` after it, and the
# command itself may make that link (seams-revamp ticket 11). Single quotes are literal, as in the shell.

VARIABLE = re.compile(r"\$(?:\{([A-Za-z_][A-Za-z0-9_]*)(?:(:?-)([^}$]*))?\}|([A-Za-z_][A-Za-z0-9_]*))")
GLOB_CHARS = set("*?[{")                      # { for brace expansion
PLAIN_OPTION = re.compile(r"^--?[A-Za-z0-9][A-Za-z0-9-]*$")      # an option with no value attached
SHORT_OPTIONS = re.compile(r"^-[A-Za-z]+$")


def _initial_env() -> dict:
    """The variables known before the command runs: TMPDIR, as the hook sees it (None when unset,
    so `${TMPDIR:-/tmp}` is /tmp). Any other variable is unknown until the command sets it."""
    return {"TMPDIR": os.environ.get("TMPDIR") or None}


def _expand(token: str, env: dict) -> str | None:
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


def _expand_part(text: str, env: dict, bare: bool) -> str | None:
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


def _placed_path(token: str, env: dict) -> str | None:
    """The absolute path a token names, or None when it is not placed."""
    text = _expand(token, env)
    if text is None or not text or GLOB_CHARS & set(text) or not os.path.isabs(text) or ".." in text.split(os.sep):
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


def _operands(args: list) -> list | None:
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


def git_label(words: list) -> str | None:
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


def _worktree_paths(words: list) -> list | None:
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


def _manager_label(base: str, args: list) -> str | None:
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
        label = git_label(words)
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


def _all_exempt(tokens: list | None, env: dict, is_exempt) -> bool:
    if tokens is None:
        return False
    for token in tokens:
        path = _placed_path(token, env)
        if path is None or not is_exempt(path):
            return False
    return True


def _segment_label(segment: list, command: str, env: dict, is_exempt, depth: int = 0) -> str | None:
    words, redirects = _split_redirects(segment)
    label, targets = _what_it_writes(words, command, env, is_exempt, depth)
    if is_exempt is None:                     # every write counts; a redirection names it first
        return "a redirect to a file" if redirects else label
    if label and not _all_exempt(targets, env, is_exempt):
        return label
    if redirects and not _all_exempt(redirects, env, is_exempt):
        return "a redirect to a file"
    return None


def _classify(command: str, is_exempt, env: dict, depth: int = 0) -> str | None:
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


def classify_command(command: str, is_exempt: Callable[[str], bool] | None = None) -> str | None:
    """The label for what a shell command changes, or None when it looks read-only.

    With `is_exempt`, a write whose every path is placed (see above) and exempt is not a change:
    the gate passes its scratch rule. Without it every write counts, which is how the routing
    harness scores a shell write before the first Skill call.
    """
    try:
        return _classify(command, is_exempt, _initial_env())
    except (_TooDeep, RecursionError):
        return TOO_DEEP


# --- Read-only agents ------------------------------------------------------------------------
# Seams' read-only agents (plugin/agents/) read and never write, whatever the request has declared
# (lean-and-durable decision 30). The classifier above is a best-effort mesh of writes; a read-only
# agent's shell is held to the opposite, a list of reads: every simple command in the line is one of
# them, named plainly, with no variable, substitution, assignment or wrapper, and its redirects land in
# the temp directory or the session's scratchpad.

READ_COMMANDS = {"cat", "head", "tail", "wc", "ls", "pwd", "grep", "egrep", "fgrep", "diff", "cmp", "comm", "cut",
                 "tr", "nl", "paste", "sort", "basename", "dirname", "realpath", "readlink", "echo", "printf", "test",
                 "[", "true", "false", "which", "jq", "stat", "du", "find", "cd", "shasum", "sha256sum", "md5",
                 "md5sum", "od", "hexdump", "strings", "git", "gh"}
GIT_READS = {"status", "diff", "log", "show", "blame", "grep", "ls-files", "ls-tree", "rev-parse", "merge-base",
             "cat-file", "rev-list", "describe", "shortlog", "diff-tree", "name-rev", "show-ref", "for-each-ref"}
GIT_READ_OPTIONS = {"--no-pager", "-P", "--no-optional-locks"}       # git's own options a read may take, and -C DIR
GIT_WRITES_OR_RUNS = ("--output", "--ext-diff", "--open-files-in-pager")      # a file written, a program run
GH_READS = {(group, verb) for group in ("pr", "issue", "repo", "run", "release", "workflow")
            for verb in ("view", "list", "diff", "checks", "status")}
FIND_WRITES = {"-exec", "-execdir", "-ok", "-okdir", "-delete", "-fprint", "-fprint0", "-fprintf", "-fls"}
EXPANDS_INTO_OPTIONS = {"git", "gh", "find", "sort"}      # a glob here could name a planted `--output=x` file
READ_ONLY_RULE = (
    "A read-only agent reads: its shell runs git's read subcommands (" + ", ".join(sorted(GIT_READS)) + "; no -c, "
    "--output, --ext-diff or grep -O), gh's view, list, diff, checks and status (no --web), and "
    + ", ".join(sorted(READ_COMMANDS - {"git", "gh"})) + " (find with no -exec, -ok, -delete or -fprint; sort "
    "with no -o or --compress-program), each by its plain name, with no variable, substitution, or glob in a git, gh, find or sort "
    "command, joined by pipes, &&, || or ;, and redirected only into the temp directory or the session's "
    "scratchpad, where its editor tools may also write, never into a git directory, the Claude config directory or "
    "the gate's ledger.")


def in_git_dir(path: str) -> bool:
    """Whether a path lies in a git directory (or is a worktree's `.git` file), whose config names
    programs git runs: `core.fsmonitor` on `git status`, a diff driver on `git diff`."""
    return ".git" in path.split(os.sep)


def _unquoted_text(token: str) -> str:
    """The characters of a shell word that stand outside its quotes, where a glob or a brace expands."""
    out, quote, i = [], None, 0
    while i < len(token):
        char = token[i]
        if quote == "'":
            quote = None if char == "'" else quote
        elif quote == '"':
            if char == "\\":
                i += 1
            elif char == '"':
                quote = None
        elif char == "\\":
            i += 1
        elif char in "'\"":
            quote = char
        else:
            out.append(char)
        i += 1
    return "".join(out)


def _git_read_problem(args: list) -> str | None:
    i = 0
    while i < len(args) and args[i].startswith("-"):
        if args[i] == "-C" and i + 1 < len(args):
            i += 2
        elif args[i] in GIT_READ_OPTIONS:
            i += 1
        else:
            return "passes git one of its own options, which a read does not take"
    if i >= len(args) or args[i] not in GIT_READS:
        return "runs a git subcommand that is not a read"
    rest = args[i + 1:]
    pager = args[i] == "grep" and any(a.startswith("-") and not a.startswith("--") and "O" in a for a in rest)
    if pager or any(a.startswith(GIT_WRITES_OR_RUNS) for a in rest):
        return "passes git an option that writes a file or runs a program"
    return None


def _read_problem(words: list, env: dict) -> str | None:
    """Why one simple command, its redirections removed, is not a read, as fixed text; None when it is."""
    if ASSIGNMENT.match(words[0]):
        return "sets a variable"
    plain = [_expand(word, env) for word in words]
    if None in plain:
        return "has a word that cannot be read before it runs"
    name, args = plain[0], plain[1:]
    if name not in READ_COMMANDS:
        return "runs a command that is not a read"
    if name in EXPANDS_INTO_OPTIONS and any(set(_unquoted_text(w)) & set("*?[{") for w in words[1:]):
        return "leaves a glob or a brace to expand into an option"
    if name == "git":
        return _git_read_problem(args)
    if name == "gh" and (len(args) < 2 or (args[0], args[1]) not in GH_READS):
        return "runs a gh command that is not a read"
    if name == "gh" and ("-w" in args or "--web" in args):
        return "opens a browser"
    if name == "find" and FIND_WRITES & set(args):
        return "gives find an action that writes or runs a command"
    if name == "sort" and any(a.startswith("--output") or (a.startswith("-") and not a.startswith("--") and "o" in a)
                              for a in args):
        return "writes the sort to a file"
    if name == "sort" and any(a.startswith("--compress-program") for a in args):
        return "gives sort a program to run"
    return None


def shell_read_problem(command: str, is_scratch: Callable[[str], bool]) -> str | None:
    """Why a read-only agent may not run this shell command, as fixed text, or None when every simple
    command in it is a read and every redirect lands where `is_scratch` says scratch lies."""
    if not command.strip():
        return None
    text, heredocs = _without_heredoc_text(command)
    tokens = _tokens(text)
    try:
        runs = [run for body in heredocs for run in _runs(body)] + [run for t in tokens for run in _word_runs(t)]
    except (_TooDeep, RecursionError):
        runs = [TOO_DEEP]
    if runs:
        return "runs a command substitution"
    env = _initial_env()
    for segment in _segments(tokens):
        words, targets = _split_redirects(segment)
        if targets and not _all_exempt(targets, env, is_scratch):
            return ("redirects outside the temp directory and the session's scratchpad, or into the Claude config "
                    "directory or the gate's ledger directory")
        if any(in_git_dir(_placed_path(target, env)) for target in targets):
            return "redirects into a git directory"
        problem = _read_problem(words, env) if words else None
        if problem:
            return problem
    return None
