#!/usr/bin/env python3
"""Seams' knowledge index (ADR 0008): a repository opts in with a knowledge config, `docs/agents/knowledge.md`, whose
fenced `knowledge` block names its inbox (raw sources, gitignored), its tracked index, its entries and its other
source homes. This keeps the index current and reports what is new, undistilled, changed, missing or not on this
machine. It reads only local files and runs only local git reads; it never writes a source's content anywhere.

Two files, so nothing personal is committed (knowledge-layer decision 18):
- the tracked index (the config's `index`): one JSON row per source, sorted by id, holding only its id, date,
  topics, secrets scan (clean, secrets or unscanned) and the entries that cite it;
- the machine's own file, `<inbox>/.knowledge-local.jsonl` (gitignored with the inbox; refused when git would track
  it): each source's path, old paths, size, modified time, hash and the hash it was distilled at.

    knowledge.py status [--quick] [--json]   counts (--quick: sizes and times only, never hashing; without it, a
                                             source whose size or time moved is hashed to settle it)
    knowledge.py index                       add and update the rows
    knowledge.py distilled <id>...           mark sources distilled at their current content (and rescan them)
    knowledge.py topics <id> <a,b,...>       set a source's topics, as written (what an action searches by)
    knowledge.py move <folder>...            the plan to move folders of raw sources (from the repository's root)
                                             into the inbox: each to <inbox>/<date>-<name>/ with its size, and what
                                             stays
    knowledge.py move --yes <code> <folder>...   that plan carried out, only with the code the plan printed, within
                                             30 minutes, and while every file in it is as planned (the user's yes to
                                             the list shown)

The move never deletes or overwrites a file. Exact duplicates (of a source or of each other), tracked files, hidden
files and links stay where they are, outside the inbox: a duplicate's path joins its copy's old paths, and a tracked
file is listed and refused, so nothing leaves git silently. A folder that something not ignored names (a script, a
skill's instructions, a build file), or a folder holding it, stays where it is; the plan prints the sources line that
would index it in place, and the config is left to the user. A folder in another case than on disk, or holding or
inside another git repository, is refused. A moved file keeps the date it had where it was, and a move that stops
half-way is finished by the next plan. Only the plan names files, escaped; the move itself reports counts. The code
is not a secret, and the script can't tell who typed it: the user's yes is the consent, so a session runs --yes only
after the user agrees to the plan it showed them, and never unattended (a move is destructive).

The config's block, one `key: value` per line (paths from the repository's root, inside it; lists comma-separated):

    inbox            the raw sources' folder (gitignored; read from the main checkout, so worktrees see it)
    index            the tracked index
    entries          the folder(s) of knowledge entries; an entry cites a source by its id (src-<10 hex>)
    sources          other homes holding the owner's word outside the approval process, indexed in place
    format           the entry format: markdown (the default), or the project's own (a schema's path)
    approved         how an approved entry is recognised (for Claude, not this script)
    approval-record  the file the owner's approvals live in, if the project keeps one
    escalation       the tag for a question only the owner can answer (NEEDS-OWNER)

An id is random, so the tracked index reveals nothing about a file: the local file is the only link from an id to
its source, and a machine without it (a teammate's, or one that lost it) sees every row as not on this machine.

No config: the layer is off, and every command says so and writes nothing. A malformed config, index or local file
is reported in one line (exit 2). Standard library only; it writes no bytecode."""
from __future__ import annotations

import sys

sys.dont_write_bytecode = True

import email                                        # noqa: E402
import hashlib                                      # noqa: E402
import json                                         # noqa: E402
import os                                           # noqa: E402
import re                                           # noqa: E402
import secrets                                      # noqa: E402
import shlex                                        # noqa: E402
import stat as stat_kind                            # noqa: E402
import subprocess                                   # noqa: E402
import tempfile                                     # noqa: E402
import time                                         # noqa: E402

CONFIG = os.path.join("docs", "agents", "knowledge.md")
KEYS = {"inbox", "index", "entries", "format", "escalation", "sources", "approved", "approval-record"}
REQUIRED = ("inbox", "index", "entries")
LOCAL = ".knowledge-local.jsonl"
TRACKED_FIELDS = ("id", "date", "topics", "scan", "cited_by")
LOCAL_FIELDS = ("id", "path", "aka", "size", "mtime", "hash", "distilled")
SOURCE_ID = re.compile(r"(?<![0-9A-Za-z_-])src-[0-9a-f]{10}(?![0-9A-Za-z_])")
DATE = re.compile(r"(?<!\d)(\d{4})-(\d{2})-(\d{2})(?!\d)")
# A credential in a raw source (a chat export's API key): the source's row says "secrets", and nothing from the file
# is ever written. "clean" means every byte was read as text and nothing matched; anything else is "unscanned".
CREDENTIALS = re.compile("|".join((
    r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b",
    r"\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_\w{20,})",
    r"\bsk-[A-Za-z0-9_-]{20,}",
    r"\b(?:sk|rk|pk)_(?:live|test)_[A-Za-z0-9]{16,}",
    r"\bAIza[0-9A-Za-z_-]{35}",
    r"\bxox[abeprs]-[A-Za-z0-9-]{10,}|\bxapp-[A-Za-z0-9-]{10,}|hooks\.slack\.com/services/\S",
    r"\beyJ[A-Za-z0-9_-]{8,2048}\.eyJ[A-Za-z0-9_-]{8}",             # a JWT's header, then its payload's start
    r"\b(?:AC|SK)[0-9a-f]{32}\b",
    r"-----BEGIN [A-Z ]*PRIVATE KEY-----",
    r"(?<![a-z0-9+.-])[a-z][a-z0-9+.-]{0,30}://[^\s/:@]{1,256}:[^\s/@]{1,256}@",
    r"(?i:\bbearer\s{1,40}[A-Za-z0-9._~+/=-]{16})",
    r"(?i:(?:api[ _-]?key|secret|token|passw(?:or)?d|pwd|access[ _-]?key|private[ _-]?key|auth)[A-Za-z0-9_-]{0,40}"
    r"[\"']?\s{0,40}[:=]\s{0,40}[\"']?[^\s\"']{8})",              # aligned, or the value on the next line
)))
BINARY = (".pdf", ".png", ".jpg", ".jpeg", ".gif", ".webp", ".heic", ".tif", ".tiff", ".zip", ".gz", ".mp3", ".m4a",
          ".mp4", ".mov", ".wav", ".docx", ".docm", ".doc", ".xlsx", ".xlsm", ".xls", ".pptx", ".ppt", ".odt", ".ods",
          ".odp", ".pages", ".numbers", ".key", ".epub", ".rtfd")
SCAN_BYTES = 8 << 20                                # ceiling: a longer text file is "unscanned", never "clean"
MAIL = re.compile(rb"(?im)^(?:mime-version:|content-transfer-encoding:[ \t]*(?:base64|quoted-printable))")
MBOX_SPLIT = re.compile(rb"(?m)^(?=From )")         # a mailbox (a Gmail export): each message on its own


class KnowledgeError(Exception):
    """A config, index or local file the script can't trust: reported in one line, exit 2."""


# --- where things are ----------------------------------------------------------------------------------------------

def git(cwd: str, *args: str, input: "str | None" = None) -> "subprocess.CompletedProcess | None":
    try:
        return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, timeout=5, input=input,
                              stdin=None if input is not None else subprocess.DEVNULL)
    except (OSError, subprocess.TimeoutExpired):
        return None


def roots(cwd: str) -> "tuple[str, str]":
    """(the worktree's root, the main checkout's root): the index and the entries are tracked, so they are read
    where the session works; the inbox is gitignored, so it exists only in the main checkout."""
    done = git(cwd, "rev-parse", "--show-toplevel", "--git-common-dir")
    lines = done.stdout.splitlines() if done and done.returncode == 0 else []
    top = os.path.realpath(lines[0]) if lines else os.path.realpath(cwd)
    common = os.path.abspath(os.path.join(cwd, lines[1])) if len(lines) > 1 else ""
    main = os.path.dirname(common) if os.path.basename(common) == ".git" else top
    return top, os.path.realpath(main)


def inside(path: str, root: str) -> bool:
    return path != root and os.path.commonpath([path, root]) == root


def listed(value: str) -> "list[str]":
    return [part.strip() for part in value.split(",") if part.strip()]


def read_config(top: str, main: str) -> "dict | None":
    path = os.path.join(top, CONFIG)
    try:
        text = open(path, encoding="utf-8").read()
    except FileNotFoundError:
        return None
    except (OSError, ValueError):
        raise KnowledgeError(f"{CONFIG} can't be read as UTF-8 text")
    block = re.search(r"^```knowledge\s*\n(.*?)^```", text, re.S | re.M)
    if not block:
        raise KnowledgeError(f"{CONFIG} has no ```knowledge block")
    config = {}
    for line in block.group(1).splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        key, sep, value = line.partition(":")
        key = key.strip().lower()
        if not sep or key not in KEYS:
            raise KnowledgeError(f"{CONFIG}: unknown line in the knowledge block: {line.strip()[:60]}")
        config[key] = value.strip()
    missing = [k for k in REQUIRED if not config.get(k)]
    if missing:
        raise KnowledgeError(f"{CONFIG}: the knowledge block needs {', '.join(missing)}")
    for key, root, values in (("inbox", main, [config["inbox"]]), ("sources", main, listed(config.get("sources", ""))),
                              ("index", top, [config["index"]]), ("entries", top, listed(config["entries"]))):
        for value in values:
            real = os.path.realpath(os.path.join(root, value))
            if not inside(real, root) or ".git" in os.path.relpath(real, root).lower().split(os.sep):
                raise KnowledgeError(f"{CONFIG}: its {key} must stay inside the repository ({value[:60]})")
    return config


# --- reading sources -----------------------------------------------------------------------------------------------

def files_under(base: str):
    """(path, lstat) of every regular, readable file under base, in order: a symlink, a pipe or a device is never
    read, and hidden names (.DS_Store, the local file) are not sources."""
    try:
        top = os.lstat(base)
    except OSError:
        return
    if stat_kind.S_ISREG(top.st_mode):
        if os.access(base, os.R_OK):
            yield base, top
        return
    for folder, dirs, names in os.walk(base):
        dirs[:] = sorted(d for d in dirs if not d.startswith("."))
        for name in sorted(names):
            if name.startswith("."):
                continue
            path = os.path.join(folder, name)
            try:
                found = os.lstat(path)
            except OSError:
                continue
            if stat_kind.S_ISREG(found.st_mode) and os.access(path, os.R_OK):
                yield path, found


def present(config: dict, main: str) -> "dict[str, os.stat_result]":
    """Every source file on this machine, by its path from the main checkout."""
    homes = [config["inbox"]] + listed(config.get("sources", ""))
    return {os.path.relpath(path, main): found for home in homes for path, found in files_under(os.path.join(main, home))}


def hash_of(path: str) -> "str | None":
    digest = hashlib.sha256()
    try:
        with open(path, "rb") as handle:
            for chunk in iter(lambda: handle.read(1 << 20), b""):
                digest.update(chunk)
    except OSError:
        return None
    return digest.hexdigest()


def scan(path: str) -> str:
    if path.lower().endswith(BINARY):
        return "unscanned"
    try:
        with open(path, "rb") as handle:
            data = handle.read(SCAN_BYTES + 1)
    except OSError:
        return "unscanned"
    if b"\x00" in data[:8192]:
        return "unscanned"
    complete, texts = len(data) <= SCAN_BYTES, [data[:SCAN_BYTES].decode("utf-8", errors="replace")]
    if MAIL.search(data[:SCAN_BYTES]):               # an email's encoded bodies are read decoded
        try:
            for message in MBOX_SPLIT.split(data[:SCAN_BYTES]):
                for part in email.message_from_bytes(message).walk():
                    if part.is_multipart():
                        continue
                    payload = part.get_payload(decode=True) or b""
                    if part.get_content_maintype() != "text":
                        complete = complete and not payload     # an attachment it can't read
                        continue
                    try:
                        texts.append(payload.decode(part.get_content_charset() or "utf-8", errors="replace"))
                    except LookupError:                       # a charset it doesn't know
                        complete = False
        except Exception:                            # noqa: BLE001  a message the email module can't take apart
            complete = False
    if any(CREDENTIALS.search(text) for text in texts):
        return "secrets"
    return "clean" if complete else "unscanned"


def real_day(month: str, day: str) -> bool:
    return 1 <= int(month) <= 12 and 1 <= int(day) <= 31


def date_of(path: str, found: os.stat_result) -> str:
    for year, month, day in reversed(DATE.findall(path)):
        if real_day(month, day):
            return f"{year}-{month}-{day}"
    return time.strftime("%Y-%m-%d", time.gmtime(found.st_mtime))


def entry_citations(config: dict, top: str) -> "dict[str, set]":
    cites = {}
    for home in listed(config["entries"]):
        for path, _ in files_under(os.path.join(top, home)):
            try:
                text = open(path, encoding="utf-8", errors="replace").read()
            except OSError:
                continue
            cites[os.path.relpath(path, top)] = set(SOURCE_ID.findall(text))
    return cites


# --- the two files -------------------------------------------------------------------------------------------------

SHAPES = {"id": str, "date": str, "topics": list, "scan": str, "cited_by": list, "path": str, "aka": list, "size": int,
          "mtime": int, "hash": str, "distilled": str}


def read_rows(path: str, fields: "tuple[str, ...]", what: str) -> "dict[str, dict]":
    try:
        lines = open(path, encoding="utf-8").read().splitlines()
    except FileNotFoundError:
        return {}
    except (OSError, ValueError):
        raise KnowledgeError(f"{what} can't be read as UTF-8 text")
    rows = {}
    for number, line in enumerate(lines, 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except ValueError:
            row = None
        if not isinstance(row, dict) or not all(isinstance(row.get(k), SHAPES[k]) and not isinstance(row.get(k), bool)
                                                for k in fields) \
                or not all(isinstance(v, str) for k in fields if SHAPES[k] is list for v in row[k]):
            raise KnowledgeError(f"{what} has a line it can't read (line {number})")
        rows[row["id"]] = {k: row[k] for k in fields}   # an older version's extra keys are dropped
    return rows


def write_rows(path: str, rows: "dict[str, dict]") -> None:
    folder = os.path.dirname(path) or "."
    os.makedirs(folder, exist_ok=True)
    handle, temp = tempfile.mkstemp(dir=folder, prefix="." + os.path.basename(path) + ".")
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as out:
            for key in sorted(rows):
                out.write(json.dumps(rows[key], sort_keys=True, ensure_ascii=False) + "\n")
        os.replace(temp, path)
    except BaseException:
        os.unlink(temp)
        raise


class Store:
    """The tracked index and the machine's own file, read and written together."""

    def __init__(self, config: dict, top: str, main: str):
        self.config, self.top, self.main = config, top, main
        self.index_path = os.path.join(top, config["index"])
        self.local_path = os.path.join(main, config["inbox"], LOCAL)
        self.tracked = read_rows(self.index_path, TRACKED_FIELDS, "the knowledge index")
        self.local = read_rows(self.local_path, LOCAL_FIELDS, "the inbox's local file")

    def ignored(self) -> None:
        check = git(self.main, "check-ignore", "-q", os.path.relpath(self.local_path, self.main))
        if not check or check.returncode != 0:
            raise KnowledgeError(f"git would track the inbox ({self.config['inbox']}): add it to .gitignore first")

    def save(self) -> None:
        self.ignored()
        os.makedirs(os.path.join(self.main, self.config["inbox"]), exist_ok=True)
        write_rows(self.local_path, self.local)
        write_rows(self.index_path, self.tracked)


def new_id(taken: set) -> str:
    while True:
        source = "src-" + secrets.token_hex(5)
        if source not in taken:
            return source


def index(store: Store) -> None:
    found = present(store.config, store.main)
    by_path = {row["path"]: source for source, row in store.local.items()}
    for path, now in found.items():
        full = os.path.join(store.main, path)
        source = by_path.get(path)
        if source is not None:
            row = store.local[source]
            if source not in store.tracked:          # its tracked row went missing (another checkout, a lost write)
                store.tracked[source] = {"id": source, "date": date_of(path, now), "topics": [], "scan": scan(full),
                                         "cited_by": []}
            if (row["size"], row["mtime"]) != (now.st_size, now.st_mtime_ns):
                digest = hash_of(full)
                if digest is None:
                    continue
                row.update(size=now.st_size, mtime=now.st_mtime_ns, hash=digest)
                store.tracked[source]["scan"] = scan(full)
            continue
        digest = hash_of(full)
        if digest is None:
            continue
        same = [s for s, row in store.local.items() if row["hash"] == digest]
        owner = next((s for s in same if store.local[s]["path"] in found), None)
        if owner:                                    # an identical file elsewhere: the same source, seen twice
            store.local[owner]["aka"] = sorted(set(store.local[owner]["aka"]) | {path})
            continue
        moved = next((s for s in same if store.local[s]["path"] not in found), None)
        if moved:                                    # the same content at a new path: its id kept, its old path too
            row = store.local[moved]
            row["aka"] = sorted(set(row["aka"]) | {row["path"]})
            row.update(path=path, size=now.st_size, mtime=now.st_mtime_ns)
            by_path[path] = moved
            continue
        source = new_id(set(store.tracked) | set(store.local))
        store.local[source] = {"id": source, "path": path, "aka": [], "size": now.st_size, "mtime": now.st_mtime_ns,
                               "hash": digest, "distilled": ""}
        store.tracked[source] = {"id": source, "date": date_of(path, now), "topics": [], "scan": scan(full),
                                 "cited_by": []}
        by_path[path] = source
    cites = entry_citations(store.config, store.top)
    for source, row in store.tracked.items():
        row["cited_by"] = sorted(entry for entry, ids in cites.items() if source in ids)
    store.save()


def status(store: Store, quick: bool) -> dict:
    """The counts: files on this machine the index lacks (new); sources never distilled; sources whose content moved
    on since they were distilled; entries citing an id the index lacks; sources not on this machine (a teammate's
    checkout, or a file removed), which are never counted as changed."""
    found = present(store.config, store.main)
    rows = [row for source, row in store.local.items() if source in store.tracked]
    known = {row["path"] for row in rows} | {a for row in rows for a in row["aka"]}
    counts = {"new": sum(1 for path in found if path not in known), "undistilled": 0, "changed": 0, "missing": 0,
              "absent": 0}
    for source in store.tracked:
        row = store.local.get(source)
        now = found.get(row["path"]) if row else None
        if now is None:
            counts["absent"] += 1
        elif not row["distilled"]:
            counts["undistilled"] += 1
        else:
            moved = (now.st_size, now.st_mtime_ns) != (row["size"], row["mtime"])
            if quick:
                counts["changed"] += moved or row["hash"] != row["distilled"]
            else:
                digest = hash_of(os.path.join(store.main, row["path"])) if moved else row["hash"]
                counts["changed"] += digest != row["distilled"]
    counts["missing"] = sum(1 for ids in entry_citations(store.config, store.top).values() if ids - set(store.tracked))
    return counts


def report(counts: dict) -> str:
    return (f"Knowledge: {counts['undistilled']} not distilled, {counts['changed']} changed since distilled, "
            f"{counts['missing']} entries cite a missing source, {counts['new']} new, "
            f"{counts['absent']} not on this machine.")


def mark_distilled(store: Store, sources: "list[str]") -> int:
    if not sources:
        print("usage: knowledge.py distilled <id>...", file=sys.stderr)
        return 1
    found = present(store.config, store.main)
    for source in sources:
        row = store.local.get(source)
        now = found.get(row["path"]) if row and source in store.tracked else None
        full = os.path.join(store.main, row["path"]) if now else ""
        digest = hash_of(full) if now else None
        if digest is None:
            print(f"Knowledge: {source[:40]} is not an indexed source on this machine", file=sys.stderr)
            return 1
        row.update(size=now.st_size, mtime=now.st_mtime_ns, hash=digest, distilled=digest)
        store.tracked[source]["scan"] = scan(full)
    store.save()
    return 0


def set_topics(store: Store, source: str, topics: str) -> int:
    if source not in store.tracked:
        print(f"Knowledge: {source[:40]} is not an indexed source", file=sys.stderr)
        return 1
    store.tracked[source]["topics"] = list(dict.fromkeys(listed(topics)))
    store.save()
    return 0


# --- moving existing raw sources in (ticket 06) -------------------------------------------------------------------

def size_of(total: float) -> str:
    for unit in ("B", "KB", "MB"):
        if total < 1024:
            return f"{total:.0f} B" if unit == "B" else f"{total:.1f} {unit}"
        total /= 1024
    return f"{total:.1f} GB"


def dated(name: str) -> bool:
    found = DATE.match(name)
    return bool(found) and real_day(found.group(2), found.group(3))


def shown(text: str) -> str:
    """A name as the plan prints it: a name holding a line break or a terminal escape (an attachment's name comes
    from whoever sent it) is printed quoted and escaped, so it can't hide or forge a line of the plan."""
    return text if text.isprintable() else ascii(text)


# Ignore rules name folders without reading them; anything else that names a folder (code, a skill's
# instructions, a build file, an untracked script) may read it, so the folder stays: erring towards staying is safe.
NOT_READERS = (":(exclude)*ignore",)
CODE_MINUTES = 30                                   # how long a plan's yes stays good


def node(path: str) -> "tuple[int, int] | None":
    try:
        found = os.stat(path)
    except OSError:
        return None
    return found.st_dev, found.st_ino


def up_from(path: str, root: str) -> "set[tuple[int, int]]":
    """The identities of path and every folder above it up to root: compared by identity, not by spelling, so a
    case-insensitive disk (macOS) or a symlink can't make one folder look like two."""
    seen = set()
    while True:
        here = node(path)
        if here:
            seen.add(here)
        if path == root or os.path.dirname(path) == path:
            return seen
        path = os.path.dirname(path)


def overlap(a: str, b: str, root: str) -> bool:
    """a and b are one folder, or one holds the other (b need not exist yet: an index not written)."""
    a_id, b_id = node(a), node(b)
    return (a_id is not None and a_id in up_from(b, root)) or (b_id is not None and b_id in up_from(a, root))


def spelled_as_on_disk(rel: str, root: str) -> bool:
    here = root
    for part in rel.split(os.sep):
        try:
            if part not in os.listdir(here):
                return False
        except OSError:
            return False
        here = os.path.join(here, part)
    return True


def in_another_repository(real: str, root: str) -> bool:
    """A .git entry in the folder, under it or above it below the root: its files belong to another repository (a
    submodule, a worktree, a clone), and moving them would take them out of it."""
    here = real
    while here != root and inside(here, root):
        if os.path.lexists(os.path.join(here, ".git")):
            return True
        here = os.path.dirname(here)
    return any(".git" in dirs or ".git" in names for _, dirs, names in os.walk(real))


def reader_of(main: str, rel: str, inbox: str) -> str:
    """The first file, tracked or untracked but not ignored, outside the folder, that names the folder or a folder
    holding it as a path (quoted, or with a slash beside it), or "": a script that reads data/ reads data/owner/."""
    parts = rel.split(os.sep)
    folders = [os.sep.join(parts[:end]) for end in range(len(parts), 0, -1)]
    setting = git(main, "config", "--bool", "core.ignorecase")
    caseless = bool(setting) and setting.stdout.strip() == "true"     # a disk that ignores case reads Feeds/ as feeds/
    done = git(main, "grep", "--untracked", "-z", "-l", "-I", "-F", *(["-i"] if caseless else []),
               *(arg for f in folders for arg in ("-e", f)),
               "--", ".", *NOT_READERS, f":(exclude,literal){rel}", f":(exclude,literal){inbox}")
    if done is None or done.returncode not in (0, 1):
        raise KnowledgeError("git can't say which files name a folder, so nothing can move")
    name = "(?:" + "|".join(re.escape(f) for f in folders) + ")"
    named = re.compile(rf"(?<![\w.-])(?:(?<=[/'\"`]){name}(?![\w.-])|{name}(?=[/'\"`]))",
                       re.IGNORECASE if caseless else 0)
    for path in sorted(p for p in done.stdout.split("\0") if p):
        try:
            if named.search(open(os.path.join(main, path), encoding="utf-8", errors="replace").read()):
                return path
        except OSError:
            continue
    return ""


def tracked_in(main: str, rel: str) -> "set[str]":
    done = git(main, "ls-files", "-z", "--", f":(literal){rel}")
    if done is None or done.returncode != 0:
        raise KnowledgeError("git can't say which files it tracks, so nothing can move")
    return {path for path in done.stdout.split("\0") if path}


def started(store: Store, rel: str, inbox_rel: str) -> str:
    """The destination a move of this folder that stopped half-way began, when it holds only files moved from this
    folder (so the next plan finishes that move rather than refusing it), or ""."""
    rows = [row for row in store.local.values() if os.path.commonpath([row["path"], inbox_rel]) == inbox_rel
            and any(old.startswith(rel + os.sep) for old in row["aka"])]
    if not rows:
        return ""
    dest = os.path.join(inbox_rel, os.path.relpath(rows[0]["path"], inbox_rel).split(os.sep)[0])
    ours = {row["path"] for row in rows}
    held = {os.path.relpath(path, store.main) for path, _ in files_under(os.path.join(store.main, dest))}
    return dest if held <= ours else ""


def plan_move(store: Store, folders: "list[str]") -> "list[dict]":
    """One item per folder named: where its files go (<inbox>/<date>-<name>/), or why it stays."""
    main, inbox_rel = store.main, os.path.normpath(store.config["inbox"])
    inbox = os.path.join(main, inbox_rel)
    homes = [os.path.join(main, home) for home in listed(store.config.get("sources", ""))]
    layer = [os.path.join(root, part) for root in {store.top, main}
             for part in [CONFIG, store.config["index"]] + listed(store.config["entries"])]
    items, chosen, destinations, kept = [], [], set(), {}   # kept: a hash -> the one copy the index keeps
    found = present(store.config, main)
    for source, row in sorted(store.local.items()):
        now = found.get(row["path"])
        if now is not None and source in store.tracked:
            same = (now.st_size, now.st_mtime_ns) == (row["size"], row["mtime"])
            kept.setdefault(row["hash"] if same else hash_of(os.path.join(main, row["path"])), row["path"])
    for given in folders:
        real = os.path.realpath(os.path.join(main, given))
        rel = os.path.relpath(real, main)
        item = {"folder": os.path.normpath(given), "path": rel, "moves": [], "dups": [], "tracked": [], "why": "",
                "stays": False}
        items.append(item)
        try:
            is_folder = stat_kind.S_ISDIR(os.lstat(os.path.join(main, given)).st_mode)
        except OSError:
            is_folder = False
        if not given.isprintable():                 # the yes's command line couldn't carry it safely
            item["why"] = ": refused: its name holds a control character; rename it first"
        elif not inside(real, main) or ".git" in rel.lower().split(os.sep):
            item["why"] = ": refused: it is not inside the repository, or it is git's own"
        elif not is_folder:
            item["why"] = ": refused: not a folder here"
        elif not spelled_as_on_disk(rel, main):
            item["why"] = ": refused: the folder on disk is spelled in another case; name it as it is spelled"
        elif in_another_repository(real, main):
            item["why"] = ": refused: it holds or sits in another git repository"
        elif any(overlap(real, other, main) for other in chosen):
            item["why"] = ": refused: it overlaps a folder named before it"
        elif any(overlap(real, part, main) for part in layer):
            item["why"] = ": refused: it is, holds or sits in the knowledge config, the index or the entries"
        elif overlap(real, inbox, main):
            item["why"] = ": refused: it is, holds or sits in the inbox"
        elif any(overlap(real, home, main) for home in homes):
            item["why"] = " stays where it is, already a source the config indexes in place"
        if item["why"]:
            continue
        chosen.append(real)
        reader = reader_of(main, rel, inbox_rel)
        if reader:
            item["why"] = f" stays where it is, named in {shown(reader)}"
            item["stays"] = True
            continue
        tracked = tracked_in(main, rel)
        files = list(files_under(real))
        if not files:
            item["why"] = ": refused: it holds no files to move"
            continue
        name = os.path.basename(real)
        newest = max(now.st_mtime for _, now in files)
        resumed = started(store, rel, inbox_rel)
        item["dest"] = resumed or os.path.join(
            inbox_rel, name if dated(name) else time.strftime("%Y-%m-%d-", time.gmtime(newest)) + name)
        if item["dest"].casefold() in destinations or (os.path.lexists(os.path.join(main, item["dest"]))
                                                       and not resumed):
            item["why"] = f": refused: {shown(item['dest'])}/ already exists"
            continue
        destinations.add(item["dest"].casefold())
        for path, now in files:
            src = os.path.relpath(path, main)
            if src in tracked:                       # moving it into the inbox would take it out of git
                item["tracked"].append(src)
                continue
            digest = hash_of(path)
            if digest is None:
                continue
            if digest in kept:
                item["dups"].append({"src": src, "kept": kept[digest]})
                continue
            kept[digest] = os.path.join(item["dest"], os.path.relpath(path, real))
            item["moves"].append({"src": src, "dest": kept[digest], "size": now.st_size, "mtime": now.st_mtime_ns,
                                  "hash": digest, "stat": now})
    planned = [step["dest"] for item in items for step in item["moves"]]
    if planned:
        done = git(main, "check-ignore", "-z", "--stdin", input="\0".join(planned) + "\0")
        if done is None or done.returncode not in (0, 1) or not set(planned) <= set(done.stdout.split("\0")):
            raise KnowledgeError(f"git would not ignore every file the move would put in the inbox "
                                 f"({store.config['inbox']}): check its .gitignore rules first")
    return items


def render_plan(items: "list[dict]", sources: str) -> "list[str]":
    lines = ["Knowledge: the plan to move raw sources into the inbox (nothing has moved yet)."]
    for item in items:
        if item["why"]:
            lines.append(f"- {shown(item['folder'])}{item['why']}")
            continue
        count, total = len(item["moves"]), sum(m["size"] for m in item["moves"])
        lines.append(f"- {shown(item['folder'])} -> {shown(item['dest'])}/ ({count} file{'' if count == 1 else 's'}, "
                     f"{size_of(total)})" if count else f"- {shown(item['folder'])}: nothing moves")
        lines += [f"    duplicate, kept once: {shown(d['src'])} (the same as {shown(d['kept'])})" for d in item["dups"]]
        lines += [f"    tracked by git, refused: {shown(path)} (it stays; untrack it to move it)"
                  for path in item["tracked"]]
    lines.append("Nothing is deleted: duplicates, tracked files, hidden files and links stay where they are, outside "
                 "the inbox.")
    staying = [item["path"] for item in items if item["stays"]]
    if staying:
        listable = [path for path in staying if "," not in path and "\n" not in path]
        lines.append(f"The folders that stay are not indexed until the config ({CONFIG}) lists them; this script "
                     "never edits it. Its sources line would read:")
        lines.append("    sources: " + ", ".join(shown(path) for path in listed(sources) + listable))
        if len(listable) < len(staying):
            lines.append("    (a folder with a comma in its name can't be listed: rename it first)")
    return lines


def plan_code(items: "list[dict]") -> str:
    """The whole list (every file's path, size, time and hash, which the plan doesn't print), so a yes covers exactly
    what was planned; prefixed by the minute it was made, so it expires."""
    body = json.dumps([{k: v for k, v in item.items() if k != "moves"} | {
        "moves": [{k: v for k, v in m.items() if k != "stat"} for m in item["moves"]]} for item in items],
        sort_keys=True)
    return f"{int(time.time() // 60):x}-" + hashlib.sha256(body.encode()).hexdigest()[:12]


def move(store: Store, argv: "list[str]") -> int:
    agreed = argv[1] if argv[:1] == ["--yes"] and len(argv) > 1 else None
    folders = argv[2:] if agreed is not None else argv
    if not folders or folders[0] == "--yes":
        print("usage: knowledge.py move [--yes <code>] <folder>...", file=sys.stderr)
        return 1
    store.ignored()                                  # refused before the plan, so a yes can't be refused later
    items = plan_move(store, folders)
    code = plan_code(items)
    if agreed is None:
        print("\n".join(render_plan(items, store.config.get("sources", ""))))
        if any(item["moves"] or item["dups"] for item in items):
            print("To move exactly this, only after the user agrees to this plan, run: knowledge.py move --yes "
                  + code + " " + " ".join(shlex.quote(f) for f in folders))
        return 0
    minute, _, digest = agreed.partition("-")
    try:
        age = int(time.time() // 60) - int(minute, 16)
    except ValueError:
        age = -1
    if digest != code.partition("-")[2]:
        print("Knowledge: the plan changed since it was shown, or that code is not its own: nothing moved; run it "
              "again without --yes to see the plan", file=sys.stderr)
        return 1
    if not 0 <= age <= CODE_MINUTES:
        print(f"Knowledge: that plan's yes has expired (it lasts {CODE_MINUTES} minutes): nothing moved; run it "
              "again without --yes to see the plan", file=sys.stderr)
        return 1
    moved, total, emptied = 0, sum(len(item["moves"]) for item in items), set()
    try:
        for item in items:
            for step in item["moves"]:
                dest = os.path.join(store.main, step["dest"])
                os.makedirs(os.path.dirname(dest), exist_ok=True)
                if os.path.lexists(dest):            # never over a file: a rename would replace it
                    raise FileExistsError(17, "a file is already where one would go")
                os.rename(os.path.join(store.main, step["src"]), dest)
                record_move(store, step)
                moved += 1
                folder = os.path.dirname(step["src"])
                while folder and folder != os.path.dirname(item["path"]):
                    emptied.add(folder)
                    folder = os.path.dirname(folder)
    except BaseException as error:                   # an interrupt too: what moved keeps its old path
        store.save()
        if isinstance(error, OSError):
            raise KnowledgeError(f"the move stopped after {moved} of {total} files ({error.strerror}); nothing "
                                 "was deleted, the index records what moved, and the next plan finishes it")
        raise
    by_path = {row["path"]: source for source, row in store.local.items()}
    for item in items:                               # a duplicate stays where it is, its path kept with its copy
        for dup in item["dups"]:
            row = store.local[by_path[dup["kept"]]]
            row["aka"] = sorted(set(row["aka"]) | {dup["src"]})
    for folder in sorted(emptied, key=lambda f: -f.count(os.sep)):  # only what this move emptied; never a file
        try:
            os.rmdir(os.path.join(store.main, folder))
        except OSError:
            pass
    index(store)
    print(f"Knowledge: moved {moved} files from {sum(1 for i in items if i['moves'])} folders into the inbox; "
          f"{sum(len(i['dups']) for i in items)} duplicates stay where they were, kept once in the index; "
          f"{sum(len(i['tracked']) for i in items)} tracked files refused; "
          f"{sum(1 for i in items if i['stays'])} folders stay where they are. Nothing was deleted.")
    return 0


def record_move(store: Store, step: dict) -> None:
    """A moved file's rows: its old path kept, and its date read where it was (a folder's date prefix is not it).
    A source that left the inbox and comes back keeps its id, as index's moved sources do."""
    now = os.lstat(os.path.join(store.main, step["dest"]))
    back = next((s for s, row in sorted(store.local.items()) if row["hash"] == step["hash"] and s in store.tracked
                 and not os.path.isfile(os.path.join(store.main, row["path"]))), None)
    if back:
        row = store.local[back]
        row.update(aka=sorted(set(row["aka"]) | {row["path"], step["src"]}), path=step["dest"], size=now.st_size,
                   mtime=now.st_mtime_ns)
        return
    source = new_id(set(store.tracked) | set(store.local))
    store.local[source] = {"id": source, "path": step["dest"], "aka": [step["src"]], "size": now.st_size,
                           "mtime": now.st_mtime_ns, "hash": step["hash"], "distilled": ""}
    store.tracked[source] = {"id": source, "date": date_of(step["src"], step["stat"]), "topics": [],
                             "scan": scan(os.path.join(store.main, step["dest"])), "cited_by": []}


def main(argv: "list[str]") -> int:
    command = argv[0] if argv else "status"
    if command not in ("status", "index", "distilled", "topics", "move"):
        print(f"knowledge.py: unknown command {command[:40]}", file=sys.stderr)
        return 1
    top, main_root = roots(os.getcwd())
    try:
        config = read_config(top, main_root)
        if config is None:
            print("Knowledge: no knowledge config here, so the layer is off.")
            return 0
        store = Store(config, top, main_root)
        if command == "index":
            index(store)
        elif command == "move":
            return move(store, argv[1:])
        elif command == "distilled":
            return mark_distilled(store, argv[1:])
        elif command == "topics":
            if len(argv) != 3:
                print("usage: knowledge.py topics <id> <a,b,...>", file=sys.stderr)
                return 1
            return set_topics(store, argv[1], argv[2])
        else:
            counts = status(store, quick="--quick" in argv)
            print(json.dumps(counts, sort_keys=True) if "--json" in argv else report(counts))
    except KnowledgeError as error:
        print(f"Knowledge: {error}")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
