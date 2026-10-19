"""The gate: the PreToolUse hook's rules. A change to the project is refused until a declaration has routed
the work (seams_ledger keeps the declarations, ADR 0005 their lifetime), and a read-only agent's call is held to a
list of reads, declared or not.

This module says what a tool call changes (an editor's file, a shell command's label from seams_shell, which it
loads only for a call that needs it, a PowerShell command off the read-only list), where scratch lies (the temp
directory and the session's scratchpad, written without a declaration), how a refusal reads, and the decision.
Python 3.9: macOS's system interpreter runs the hooks when nothing newer is first on PATH.
"""
from __future__ import annotations

import os
import re

from seams_ledger import PLUGIN_PREFIX, config_dir, declared_for, describe, ledger_root, temp_dir, unattended

# --- Project changes and the decision ------------------------------------------------------

EDITOR_TOOLS = {"Edit": "file_path", "Write": "file_path", "MultiEdit": "file_path",
                "NotebookEdit": "notebook_path"}
DOC_SUFFIXES = (".md", ".markdown", ".mdx")
TEMP_ROOTS = ("/tmp", "/private/tmp")     # plus temp_dir(), tempfile's, which honors TMPDIR
# PowerShell has no classifier here: before a declaration only these run, each on its own with
# plain arguments. A pipe, a separator, a redirect, a parenthesis (a subexpression or a call), a
# script block, a backtick (PowerShell's escape and line continuation) or a second line makes a
# command something else, quoted or not.
POWERSHELL_READS = {"get-content", "get-childitem", "select-string"}
POWERSHELL_GIT_READS = {"status", "diff", "log"}
POWERSHELL_UNSAFE = set(";|&<>(){}`\n\r")
POWERSHELL_QUOTES = re.compile("[\"'\u2018\u2019\u201a\u201b\u201c\u201d\u201e]")   # PowerShell's, typographic ones too


def _under(path: str, root: str) -> bool:
    root = os.path.realpath(root)
    return path == root or path.startswith(root.rstrip(os.sep) + os.sep)


def _climbs(path: str) -> bool:
    """Whether a path has a `..` segment, which is never placed: the kernel follows a symlink before the `..` after it,
    so the path lands wherever that link leads, and a command can make the link it then writes through (seams-revamp
    ticket 11)."""
    return ".." in path.split(os.sep)


def _scratchpad_roots(scratchpad: object) -> tuple:
    """The session's scratchpad (the hook input's `scratchpad_dir`, Claude Code 2.1.257 and later) as
    a scratch root: none when the field is absent or is not an absolute path, so a missing field
    leaves the temp directories' rules as they were."""
    return (scratchpad,) if isinstance(scratchpad, str) and os.path.isabs(scratchpad) else ()


def is_exempt_path(path: str, config: str | None = None, cwd: str | None = None,
                   scratchpad: object = None) -> bool:
    """Temp directories, the session's scratchpad and the Claude config directory are not the project.

    A path under the session's working directory is the project wherever that directory
    lives, so a repo checked out under the temp dir is still gated. So is the gate's own ledger, wherever
    it lies (under the temp directory when the home directory cannot hold it): a tool call that wrote it
    could forge a declaration. So is a path with a `..` segment (_climbs).
    """
    if _climbs(path):
        return False
    real = os.path.realpath(path)
    if real == "/dev/null":
        return True
    if (cwd and _under(real, cwd)) or _under(real, ledger_root()):
        return False
    roots = (temp_dir(), config_dir(config)) + TEMP_ROOTS + _scratchpad_roots(scratchpad)
    return any(_under(real, root) for root in roots)


def is_scratch_path(path: str, cwd: str | None = None, scratchpad: object = None,
                    config: str | None = None) -> bool:
    """Where a shell command may write without a declaration: /dev/null, or under a temp directory or
    the session's scratchpad, and outside the session's working directory. Narrower than
    is_exempt_path: the Claude config directory is not scratch, even where it lies inside a temp
    directory (a CI job's or an eval run's does), since a shell command there could delete the
    user's settings. Nor is the gate's ledger, nor a directory that holds it below a temp root (a home under the temp
    directory): a recursive copy, an archive or a find there reaches it. A temp root itself stays scratch. Nor is a path
    with a `..` segment (_climbs)."""
    if _climbs(path):
        return False
    real = os.path.realpath(path)
    if real == "/dev/null":
        return True
    if (cwd and _under(real, cwd)) or _under(real, config_dir(config)):
        return False
    ledger = os.path.realpath(ledger_root())
    if _under(real, ledger):
        return False
    roots = (temp_dir(),) + TEMP_ROOTS + _scratchpad_roots(scratchpad)
    if _under(ledger, real) and real not in {os.path.realpath(root) for root in roots}:
        return False
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
        import seams_shell
        return seams_shell.git_label(words) or "PowerShell"
    return "PowerShell"


def _editor_path(event: dict) -> str:
    """The file an editor tool writes, absolute (a relative one lies under the session's cwd), or "". Normalized unless
    it has a `..` segment, which normalizing would drop as text (_climbs)."""
    path = (event.get("tool_input") or {}).get(EDITOR_TOOLS[event.get("tool_name")]) or ""
    if path and not os.path.isabs(path):
        path = os.path.join(event.get("cwd") or os.getcwd(), path)
    return os.path.normpath(path) if path and not _climbs(path) else path


def change_for_event(event: dict, config_dir: str | None = None) -> dict | None:
    """The project change a PreToolUse event would make, or None when it makes none.

    Editor tools: the file, unless it is under a temp directory, the session's scratchpad or the
    config directory, and outside the gate's ledger. Bash, and a Monitor watch, whose command runs in the Bash tool's shell: the
    classifier's label, unless every path the command writes is placed and scratch (a pull-request
    review writes only its evidence under the temp directory); a WebSocket watch runs no command.
    PowerShell: every command, unless it is on the read-only list. Anything else: nothing.
    """
    tool = event.get("tool_name") or ""
    tool_input = event.get("tool_input") or {}
    if tool in EDITOR_TOOLS:
        path = _editor_path(event)
        if not path:
            return None
        if is_exempt_path(path, config_dir, event.get("cwd"), event.get("scratchpad_dir")):
            return None
        return {"tool": tool, "path": path, "doc": path.lower().endswith(DOC_SUFFIXES)}
    if tool in ("Bash", "Monitor"):
        import seams_shell                     # here, not above: compiling it costs a fifth of a firing
        cwd, scratchpad = event.get("cwd"), event.get("scratchpad_dir")
        label = seams_shell.classify_command(tool_input.get("command") or "",
                                             is_exempt=lambda path: is_scratch_path(path, cwd, scratchpad, config_dir))
        if label:
            return {"tool": tool, "label": label, "doc": False}
    if tool == "PowerShell":
        command = tool_input.get("command") or ""
        if command.strip() and not powershell_reads(command):
            return {"tool": "PowerShell", "label": _powershell_label(command), "doc": False}
    return None



ROUTES = ("Route it first, with the Skill tool: `diagnosing-bugs` for something broken, "
          "`seams:grill` for a change to behavior, `tdd` or "
          "`seams:implement` to keep building an agreed design, "
          "`seams:trivial` for a change with no effect on behavior, data shape "
          "or security. Then retry this call.")


REFUSAL_PREFIX = "Seams gate: "                # a refused call's reason starts with it; the harness counts by it


SCRATCH = ("Scratch work is not a change: a write whose every path is an absolute path under the temp "
           "directory or the session's scratchpad needs no declaration, from Edit, Write or a shell command, "
           "unless a path has a `..` segment.")


POWERSHELL_LIST = ("Before a declaration PowerShell runs only `Get-Content`, `Get-ChildItem`, `Select-String`, "
                   "`git status`, `git diff` and `git log`, each on its own with plain arguments: no pipe, "
                   "separator, redirect, parenthesis, script block, backtick or second line.")


def deny_reason(change: dict) -> str:
    if change["tool"] == "PowerShell":
        what, rule = "a PowerShell command outside the read-only list counts as a change", POWERSHELL_LIST
    else:
        what = (f"editing {describe(change)}" if change.get("path") else describe(change)) + " changes the project"
        rule = SCRATCH
    return (f"{REFUSAL_PREFIX}{what}, and no declaration covers it yet: no process skill has routed this "
            f"conversation's work since the session started or was cleared. {ROUTES} {rule}")


# --- Read-only agents ------------------------------------------------------------------------
# Seams' read-only agents (plugin/agents/) read and never write, whatever the request has declared
# (lean-and-durable decision 30): their shell is held to seams_shell's list of reads, their editor tools to
# scratch. The hook input names a plugin's agent by its plugin-scoped name in `agent_type`.

READ_ONLY_AGENTS = {PLUGIN_PREFIX + "scout", PLUGIN_PREFIX + "reviewer"}


def read_only_problem(event: dict, config: str | None = None) -> str | None:
    """Why a read-only agent may not make this call, as text for its refusal, or None when it only reads,
    or writes scratch. Editor tools: only under the temp directory or the session's scratchpad (not the
    config directory, which a declared request may write, nor the gate's ledger). Bash and a Monitor watch: the list of reads.
    PowerShell: its read-only list."""
    tool, tool_input = event.get("tool_name") or "", event.get("tool_input") or {}
    cwd, scratchpad = event.get("cwd"), event.get("scratchpad_dir")
    if tool in EDITOR_TOOLS:
        path = _editor_path(event)
        if not path:
            return None
        if not is_scratch_path(path, cwd, scratchpad, config):
            if _under(os.path.realpath(path), config_dir(config)):
                return f"writes `{path}`, inside the Claude config directory"
            if _under(os.path.realpath(path), ledger_root()):
                return f"writes `{path}`, inside the gate's ledger directory"
            if _climbs(path):
                return f"writes `{path}`, a path with a `..` segment, which is never scratch"
            return f"writes `{path}`, outside the temp directory and the session's scratchpad"
        import seams_shell
        return f"writes `{path}`, inside a git directory" if seams_shell.in_git_dir(path) else None
    if tool in ("Bash", "Monitor"):
        import seams_shell
        return seams_shell.shell_read_problem(tool_input.get("command") or "",
                                              lambda path: is_scratch_path(path, cwd, scratchpad, config))
    if tool == "PowerShell":
        command = tool_input.get("command") or ""
        return None if not command.strip() or powershell_reads(command) else "runs PowerShell outside its read-only list"
    return None


def read_only_reason(agent: str, problem: str) -> str:
    import seams_shell
    return (f"{REFUSAL_PREFIX}`{agent}` is a read-only agent, and this call {problem}: a read-only agent never "
            f"writes, whatever the request has declared. {seams_shell.READ_ONLY_RULE} Report what you would change "
            "or run instead, and the main conversation does it.")


def decide_pre_tool_use(event: dict, ledger: dict, config_dir: str | None = None) -> dict:
    """Allow, or deny with a reason. The change to record travels with an allow. A read-only agent's call
    is held to the list of reads, whatever the ledger says, and never records a change."""
    agent = event.get("agent_type")
    if isinstance(agent, str) and agent in READ_ONLY_AGENTS:
        problem = read_only_problem(event, config_dir)
        if problem:
            return {"decision": "deny", "reason": read_only_reason(agent, problem), "change": None}
        return {"decision": "allow", "reason": None, "change": None}
    change = change_for_event(event, config_dir)
    if change is None:
        return {"decision": "allow", "reason": None, "change": None}
    overnight = unattended()
    if not declared_for(ledger, event.get("agent_id"), overnight):
        reason = deny_reason(change)
        if overnight and event.get("agent_id"):
            reason += (" In unattended mode a builder routes its own work: invoke the skill your instructions name, "
                       "or the one your ticket's size needs, yourself.")
        return {"decision": "deny", "reason": reason, "change": None}
    if overnight and _commits(event):
        missing = missing_for_commit(ledger, event.get("agent_id"))
        if missing and not _documentation_only(event):
            return {"decision": "deny", "reason": overnight_commit_reason(missing), "change": None}
    return {"decision": "allow", "reason": None, "change": change}


# --- Overnight, the whole flow (.scratch/overnight-full-flow) ------------------------------------
# By day the user answers the grill and confirms each step, so any route opens the gate. Overnight no one does, and
# builders took the shortest route (bare tdd, or trivial), so a commit needs its own agent's design step and tests.

DESIGN_STEPS = {PLUGIN_PREFIX + "grill", "diagnosing-bugs"}     # a bug's design step is its diagnosis
COMMIT_STEPS = (("design", "`seams:grill` (or `diagnosing-bugs` for a bug)"), ("tdd", "`tdd`"))


def missing_for_commit(ledger: dict, agent_id: object) -> list:
    """The steps a commit still needs from this agent's own history: its design step and tdd (which `implement`
    runs). Code review and verification come after the commit, as implement orders them, and are checked at the
    handover (seams_ledger.decide_subagent_stop)."""
    import seams_ledger
    ran = seams_ledger.ran_by(ledger, agent_id)
    have = {"design": bool(DESIGN_STEPS & set(ran)), "tdd": "tdd" in ran}
    return [label for step, label in COMMIT_STEPS if not have[step]]


def overnight_commit_reason(missing: list) -> str:
    return (f"{REFUSAL_PREFIX}in unattended mode a commit of code runs the whole Seams flow first, and this agent "
            f"has not yet run {' and '.join(missing)}. Invoke {missing[0]} with the Skill tool and carry the work "
            "through it, then commit; a commit that changes only documentation needs just a route.")


def _commits(event: dict) -> bool:
    tool, command = event.get("tool_name"), (event.get("tool_input") or {}).get("command") or ""
    if tool in ("Bash", "Monitor"):
        import seams_shell
        return seams_shell.commits(command)
    return tool == "PowerShell" and _powershell_label(command) == "git commit" if command.strip() else False


def _documentation_only(event: dict) -> bool:
    """Whether every change in the repository the command runs in, staged, unstaged or untracked, is documentation
    (Markdown, or a feature's records under .scratch/). A command that moves elsewhere first (cd, git -C) is read as
    code, since the repository it commits in can't be told here."""
    import subprocess
    cwd, command = event.get("cwd"), (event.get("tool_input") or {}).get("command") or ""
    if not cwd or re.search(r"(^|[\s;&|(])(cd|pushd)\s|\s-C\s|--git-dir|--work-tree|GIT_DIR=|GIT_WORK_TREE=", command):
        return False
    try:
        out = subprocess.run(["git", "-C", cwd, "status", "--porcelain", "-uall"], capture_output=True, text=True,
                             timeout=5)
    except (OSError, subprocess.SubprocessError):
        return False
    paths = [line[3:].split(" -> ")[-1].strip('"') for line in out.stdout.splitlines() if line.strip()]
    return out.returncode == 0 and bool(paths) and all(
        p.lower().endswith(DOC_SUFFIXES) or p.startswith(".scratch/") for p in paths)
