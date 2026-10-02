"""The gate's ledger and the rules every hook shares: the hook frame, what counts as a declaration and a
continuation, the per-session ledger, the prompts and the done-check.

A change to the project is refused until a declaration has routed the work: a Skill invocation of a
process skill, or a slash command the user typed for one. It holds until another process skill
replaces it or the session is cleared, through typed replies and commits (ADR 0005). The PreToolUse
hook's own rules (what a tool call changes, the scratch paths, the refusals, the read-only agents) are
in seams_gate, and its shell reader in seams_shell; the other hooks fire on every prompt and turn, so
they load this module alone, and it imports nothing a firing does not use. Python 3.9: macOS's system
interpreter runs the hooks when nothing newer is first on PATH.
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
from collections.abc import Callable
from functools import lru_cache

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
    """Whether invoking this skill declares a route. Every Seams skill
    but the bootstrap does (invoking the policy itself is not choosing a process: an eval run
    showed the model doing exactly that after an "Unknown skill" error), and so do Matt
    Pocock's process skills by bare name."""
    if not skill or skill == BOOTSTRAP_SKILL:
        return False
    if skill.startswith(PLUGIN_PREFIX):
        return len(skill) > len(PLUGIN_PREFIX)
    return skill in PROCESS_SKILLS


def slash_declaration(prompt: str) -> str | None:
    """The process skill a typed slash command names, or None. Matt Pocock's bare names win over
    this plugin's, as they do in Claude Code (`/implement` is his). A Seams skill counts here only by
    its full name: a bare one counts through its expansion, which reports the full name."""
    text = (prompt or "").strip()
    if not text.startswith("/"):
        return None
    parts = text[1:].split()
    name = parts[0] if parts else ""
    return name if is_declaration(name) else None


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


# --- Where Claude Code keeps its own files ---------------------------------------------------


def config_dir(explicit: str | None = None) -> str:
    return explicit or os.environ.get("CLAUDE_CONFIG_DIR") or os.path.expanduser("~/.claude")


@lru_cache(maxsize=None)
def temp_dir() -> str:
    """tempfile.gettempdir(), found the way it finds it, without importing tempfile, whose shutil and random
    cost a hook a fifth of its time: the first of $TMPDIR, $TEMP, $TMP, /tmp, /var/tmp, /usr/tmp and the
    working directory where this user can create and write a file, as an absolute path, kept for the
    process as tempfile keeps it. Raises FileNotFoundError when there is none, as tempfile does."""
    candidates = [os.environ.get(name) for name in ("TMPDIR", "TEMP", "TMP")] + ["/tmp", "/var/tmp", "/usr/tmp"]
    try:
        candidates.append(os.getcwd())
    except OSError:
        candidates.append(os.curdir)
    for directory in filter(None, candidates):
        if directory != os.curdir:
            directory = os.path.abspath(directory)
        for attempt in range(100):
            probe = os.path.join(directory, f".seams-probe-{os.getpid()}-{attempt}")
            try:
                fd = os.open(probe, os.O_RDWR | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), 0o600)
                try:
                    try:
                        os.write(fd, b"blat")
                    finally:
                        os.close(fd)
                finally:
                    os.unlink(probe)
                return directory
            except FileExistsError:
                continue
            except OSError:                    # not writable here: the next candidate
                break
    raise FileNotFoundError("No usable temporary directory found")


# --- The ledger ---------------------------------------------------------------------------
# One JSON file per session: the main conversation's route and each subagent's own, the current
# request's changes and last verification (for the done-check), and the skills a typed prompt
# expanded to, under its prompt id until it is submitted. Skill names, tool names, paths and ids
# only; never command or prompt text. 3.4.0 wrote the same shape, without a declaration's prompt_id,
# so its ledgers read as they are.

LEDGER_VERSION = 2                            # 2: events ordered by seq, not by the clock


def _safe_name(session_id: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]", "_", session_id or "unknown")[:120]


def ledger_root(root: str | None = None) -> str:
    """The ledger directory: per user, the tmux convention (`/tmp/tmux-1000`). On a shared
    Linux `/tmp` one directory for everyone would belong to whoever's session came first, and
    the next user's chmod would raise EPERM, failing their gate open."""
    return root or os.path.join(temp_dir(), f"seams-{os.getuid()}")


def ledger_path(session_id: str, root: str | None = None) -> str:
    return os.path.join(ledger_root(root), _safe_name(session_id) + ".json")


def empty_ledger(session_id: str) -> dict:
    return {"version": LEDGER_VERSION, "session": session_id, "started": time.time(), "seq": 0,
            "declarations": [], "changes": [], "verified_at": None, "verified_seq": 0, "expanded": [],
            "request_prompt": None}


def load_ledger(session_id: str, root: str | None = None) -> dict:
    """The session's ledger, or an empty one when there is none or it cannot be read."""
    try:
        with open(ledger_path(session_id, root), encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict) and data.get("version") == LEDGER_VERSION:
            return dict(empty_ledger(session_id), **data)
    except (OSError, ValueError):
        pass
    return empty_ledger(session_id)


def save_ledger(session_id: str, ledger: dict, root: str | None = None) -> None:
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


def reset_ledger(session_id: str, root: str | None = None) -> None:
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
    """A new request of the main conversation: the done-check starts counting its changes afresh. The
    declarations stay: a route lasts until another process skill replaces it or the session is cleared
    (ADR 0005)."""
    ledger["started"] = time.time()
    ledger["changes"] = []
    ledger["verified_at"] = None
    ledger["verified_seq"] = 0
    return ledger


def add_declaration(ledger: dict, skill: str, agent_id: str | None = None, prompt_id: object = None) -> None:
    """Declare a route: the main conversation's, or the subagent `agent_id`'s alone. It replaces that owner's
    earlier route, except what the same typed prompt declared (`prompt_id`): a stacked command is one route."""
    owner = agent_id if isinstance(agent_id, str) and agent_id else None
    kept = [d for d in _listed(ledger, "declarations") if _stays(d, owner, prompt_id)]
    ledger["declarations"] = kept + [{"skill": skill, "at": time.time(), "seq": _next_seq(ledger), "agent": owner,
                                      "prompt_id": prompt_id}]


def _stays(declaration: object, owner: str | None, prompt_id: object) -> bool:
    """Whether an earlier declaration stays beside a new one of `owner`'s: another owner's does, and so does one the
    same typed prompt made. A damaged entry counts as the main conversation's, as declared_for reads it."""
    if (subagent_of(declaration) if isinstance(declaration, dict) else None) != owner:
        return True
    return bool(prompt_id) and isinstance(declaration, dict) and declaration.get("prompt_id") == prompt_id


def subagent_of(declaration: dict) -> str | None:
    """The subagent whose own declaration this is, or None for the main conversation's (an entry that names no
    subagent, as every entry did before lean-and-durable ticket 12, is the main conversation's)."""
    agent = declaration.get("agent")
    return agent if isinstance(agent, str) and agent else None


def declared_for(ledger: dict, agent_id: object = None) -> bool:
    """Whether a call is covered: by the main conversation's declarations, which cover every call, a subagent's
    included, or by the calling subagent's own, which cover it alone. So a parallel run's builder never opens the
    gate for the main conversation (user story 48). A ledger whose declarations are not a list keeps the old rule."""
    declarations = ledger.get("declarations")
    if not isinstance(declarations, list):
        return bool(declarations)
    caller = agent_id if isinstance(agent_id, str) and agent_id else None
    for d in declarations:
        owner = subagent_of(d) if isinstance(d, dict) else None
        if owner is None or owner == caller:
            return True
    return False


def add_change(ledger: dict, change: dict) -> None:
    ledger["changes"].append(dict(change, at=time.time(), seq=_next_seq(ledger)))


def mark_verified(ledger: dict) -> None:
    ledger["verified_at"] = time.time()
    ledger["verified_seq"] = _next_seq(ledger)


def cleanup_ledgers(root: str | None = None, days: int = 7) -> None:
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
# id. A typed skill therefore waits in the ledger until its prompt is submitted and replaces the route.
# The hooks reference lists the two the other way round, so an expansion that arrives after its
# prompt hook joins that prompt's route directly.


def _listed(ledger: dict, key: str) -> list:
    """A ledger list, or an empty one when the file holds something else there: a hook that raised on
    it would fail open and drop what it was recording, a route the user typed among them."""
    value = ledger.get(key)
    return value if isinstance(value, list) else []


def record_expansion(event: dict, ledger: dict) -> bool:
    """Keep what a UserPromptExpansion event expanded, under its prompt's id, until the prompt is
    submitted: the process skill, or None for anything else, since once an expansion arrived it alone
    says what the prompt typed. An earlier prompt's leftovers go (its prompt hook never ran). When the
    prompt was submitted first and started the current request, a process skill joins that prompt's
    route at once. True when the ledger changed. Only a skill or command (`slash_command`) can declare; an
    MCP server's prompt (`mcp_prompt`) never does, whatever its name. Without a prompt id nothing ties
    it to a request."""
    prompt_id, skill = event.get("prompt_id"), event.get("command_name")
    if not prompt_id:
        return False
    declares = event.get("expansion_type") == "slash_command" and isinstance(skill, str) and is_declaration(skill)
    if prompt_id == ledger.get("request_prompt"):     # its prompt hook ran first: the request is this prompt's
        declared = [d.get("skill") for d in _listed(ledger, "declarations")
                    if isinstance(d, dict) and not subagent_of(d) and d.get("prompt_id") == prompt_id]
        if not declares or skill in declared:
            return False
        add_declaration(ledger, skill, prompt_id=prompt_id)
        return True
    kept = [e for e in _listed(ledger, "expanded") if isinstance(e, dict) and e.get("prompt_id") == prompt_id]
    ledger["expanded"] = kept + [{"prompt_id": prompt_id, "skill": skill if declares else None}]
    return True


def submit_prompt(event: dict, ledger: dict) -> bool:
    """A submitted prompt: a go-ahead or a machine notice keeps the request; anything else starts a new
    one for the done-check, which counts its changes afresh. The route stays, unless the prompt typed
    process skills: the expansions recorded for this prompt, or, when none arrived, its leading slash
    command, which replace it. True when the ledger changed. A damaged entry is skipped rather than
    raised on: a hook that fails here would drop the route the prompt typed."""
    prompt, prompt_id = event.get("prompt") or "", event.get("prompt_id")
    expanded = _listed(ledger, "expanded")
    mine = [e for e in expanded if isinstance(e, dict) and prompt_id and e.get("prompt_id") == prompt_id]
    if mine:                                   # what ran; the prompt's parse would only guess from the typed word
        typed = [e.get("skill") for e in mine if isinstance(e.get("skill"), str) and is_declaration(e["skill"])]
    else:
        typed = [s for s in [slash_declaration(prompt)] if s]
    ledger["expanded"] = []
    if not typed and is_continuation(prompt):
        return bool(expanded)
    new_request(ledger)
    ledger["request_prompt"] = prompt_id              # a late expansion of this prompt still declares it
    for skill in dict.fromkeys(typed):
        add_declaration(ledger, skill, prompt_id=prompt_id)
    return True


# --- The done-check -----------------------------------------------------------------------

VERIFICATION_SKILLS = {PLUGIN_PREFIX + "verification-before-completion",
                       "superpowers:verification-before-completion", "verification-before-completion"}


def is_verification(skill: str) -> bool:
    """Whether this skill running counts as verification of the changes before it.

    It proves the skill ran, not that its commands were run honestly: the skill's own rules
    make the model run them and show the output, and the transcript shows whether it did.
    """
    return skill in VERIFICATION_SKILLS


def describe(change: dict) -> str:
    """How a refusal or a block names a change: the file, the shell label, or a PowerShell command."""
    if change.get("path"):
        return f"`{change['path']}`"
    if change.get("tool") == "PowerShell":
        return "a PowerShell command"
    return f"a shell command (`{change.get('label')}`)"


def _needs_verification(change: dict) -> bool:
    """Code changes do; documentation and VCS operations (a commit after the checks) do not."""
    if change.get("doc"):
        return False
    return not str(change.get("label") or "").startswith("git ")


def unverified_changes(ledger: dict) -> list:
    """Changes that need verification, recorded after the last verification."""
    since = ledger.get("verified_seq") or 0
    return [c for c in ledger.get("changes", []) if _needs_verification(c) and c.get("seq", 0) > since]


def decide_stop(ledger: dict, stop_hook_active: bool) -> str | None:
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


def run_hook(handler: Callable[[dict], dict | None]) -> int:
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
        import traceback                       # here, not above: loading it would cost every firing milliseconds
        traceback.print_exc(file=sys.stderr)
    return 0
