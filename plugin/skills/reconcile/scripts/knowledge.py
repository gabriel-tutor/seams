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
    knowledge.py pending [--json]            what waits to be distilled on this machine (id, path, date, scan, why)
    knowledge.py distilled <id>[:<hash>]...  mark sources distilled (and rescan them); with the hash pending showed,
                                             a source changed since it was read is refused
    knowledge.py topics <id> <a,b,...>       set a source's topics, as written (what an action searches by)
    knowledge.py move <folder>...            the plan to move folders of raw sources (from the repository's root)
                                             into the inbox: each to <inbox>/<date>-<name>/ with its size, and what
                                             stays
    knowledge.py move --yes <code> <folder>...
                                             that plan carried out, only with the code the plan printed, within 30
                                             minutes, and while every file in it is as planned (the user's yes to the
                                             list shown)

The move never deletes or overwrites a file. Exact duplicates (of a source or of each other), tracked files (known by
identity, so a case-only rename can't hide one), hidden files and links stay where they are, outside the inbox, and the
plan counts them: a duplicate's path joins its copy's old paths, and a tracked file is listed and refused, so nothing
leaves git silently. A folder that something not ignored names (a script, a skill's instructions, a build file), or a
folder holding it, stays where it is; the plan prints the sources line that would index it in place, and the config is
left to the user. A folder in another case than on disk, or holding or inside another git repository, is refused, and
so is a move git wouldn't ignore every file of. A moved file keeps the date it had where it was. Before the first file
moves, every step goes into a journal in the inbox (.knowledge-move.json), so a move stopped at any point (an error,
an interrupt, a kill) keeps every old path, and the next plan of the folder (or the next index) finishes it in the
same destination; a journal that points outside the inbox, or that names a file outside the repository, is refused.
A run that writes (index, distilled, topics, move) holds a lock in git's own folder (seams-knowledge.lock), so a
second one at once is refused rather than dropping the first's rows; status needs none. Only
the plan names files, escaped; the move itself reports counts. The code is not a secret, and the script can't tell who
typed it: the user's yes is the consent, so a session runs --yes only after the user agrees to the plan it showed
them, and never unattended (a move is destructive).

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
import errno                                        # noqa: E402
import fcntl                                        # noqa: E402
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
JOURNAL = ".knowledge-move.json"                    # a move under way (ticket 06), in the inbox beside LOCAL
LOCK = "seams-knowledge.lock"                       # in git's own folder: one writing run at a time
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
ENTRY_BYTES = 1 << 20                              # an entry's citations are in its first megabyte
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


def roots(cwd: str) -> "tuple[str, str, bool]":
    """(the worktree's root, the main checkout's root, whether they belong together): the index and the entries are
    tracked, so they are read where the session works; the inbox is gitignored, so it exists only in the main
    checkout. A linked worktree's git directory must point back at it, and a checkout that isn't one must be its own
    main checkout: a `.git` file naming another repository's git directory would otherwise read that one's inbox."""
    done = git(cwd, "rev-parse", "--show-toplevel", "--git-dir", "--git-common-dir")
    lines = done.stdout.splitlines() if done and done.returncode == 0 else []
    top = os.path.realpath(lines[0]) if lines else os.path.realpath(cwd)
    if len(lines) < 3:
        return top, top, True
    gitdir, common = (os.path.realpath(os.path.join(cwd, line)) for line in lines[1:3])
    main = os.path.realpath(os.path.dirname(common)) if os.path.basename(common) == ".git" else top
    if gitdir == common:
        return top, main, main == top
    try:                                             # a linked worktree: its git directory names its .git file
        back = read_text(os.path.join(gitdir, "gitdir"), "the worktree's git directory", limit=4096).strip()
    except (OSError, KnowledgeError):
        return top, main, False
    return top, main, os.path.realpath(os.path.dirname(back)) == top


def read_text(path: str, what: str, limit: "int | None" = None, strict: bool = True) -> str:
    """A file's text, only when it is a regular file (never a pipe, a device or a link), at most `limit` bytes.
    FileNotFoundError passes through; anything else it can't trust is a KnowledgeError."""
    try:                                             # opened once, the open file itself checked: no swap between
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    except FileNotFoundError:
        raise
    except OSError:                                  # a link (O_NOFOLLOW), or a file it may not read
        raise KnowledgeError(f"{what} isn't a regular file it can read")
    try:
        if not stat_kind.S_ISREG(os.fstat(fd).st_mode):
            raise KnowledgeError(f"{what} isn't a regular file")
        with os.fdopen(fd, "rb") as handle:
            fd = -1
            data = handle.read() if limit is None else handle.read(limit)
        return data.decode("utf-8", errors="strict" if strict else "replace")
    except ValueError:
        raise KnowledgeError(f"{what} can't be read as UTF-8 text")
    except OSError:
        raise KnowledgeError(f"{what} can't be read")
    finally:
        if fd >= 0:
            os.close(fd)


def inside(path: str, root: str) -> bool:
    return path != root and os.path.commonpath([path, root]) == root


def listed(value: str) -> "list[str]":
    return [part.strip() for part in value.split(",") if part.strip()]


def read_config(top: str, main: str) -> "dict | None":
    path = os.path.join(top, CONFIG)
    try:
        text = read_text(path, CONFIG)
    except FileNotFoundError:
        return None
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
            try:                                     # ceiling: an entry's first ENTRY_BYTES; entries are short
                text = read_text(path, "an entry", limit=ENTRY_BYTES, strict=False)
            except (OSError, KnowledgeError):
                continue
            cites[os.path.relpath(path, top)] = set(SOURCE_ID.findall(text))
    return cites


# --- the two files -------------------------------------------------------------------------------------------------

SHAPES = {"id": str, "date": str, "topics": list, "scan": str, "cited_by": list, "path": str, "aka": list, "size": int,
          "mtime": int, "hash": str, "distilled": str}


SCANS = ("clean", "unscanned", "secrets")         # in rising strictness
HEX64 = re.compile(r"[0-9a-f]{64}")


def row_values_valid(row: dict, fields: "tuple[str, ...]") -> bool:
    """A committed row's values are what the script itself writes: its scan one of SCANS, its date a real date,
    its id a source id, its hashes 64 hex digits (an empty distilled hash: never distilled)."""
    if not re.fullmatch(r"src-[0-9a-f]{10}", row["id"]):
        return False
    if "scan" in fields and row["scan"] not in SCANS:
        return False
    if "date" in fields and not (re.fullmatch(r"\d{4}-\d{2}-\d{2}", row["date"])
                                 and 1 <= int(row["date"][5:7]) <= 12 and 1 <= int(row["date"][8:]) <= 31):
        return False
    if "hash" in fields and not HEX64.fullmatch(row["hash"]):
        return False
    return "distilled" not in fields or row["distilled"] == "" or bool(HEX64.fullmatch(row["distilled"]))


def read_rows(path: str, fields: "tuple[str, ...]", what: str) -> "dict[str, dict]":
    try:
        lines = read_text(path, what).splitlines()
    except FileNotFoundError:
        return {}
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
        if not row_values_valid(row, fields):
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


def require_ignored(config: dict, main: str) -> None:
    check = git(main, "check-ignore", "-q", os.path.join(os.path.normpath(config["inbox"]), LOCAL))
    if not check or check.returncode != 0:
        raise KnowledgeError(f"git would track the inbox ({config['inbox']}): add it to .gitignore first")


def hold_lock(main: str):
    """An exclusive lock for a run that writes the index or the inbox's files, taken before they are read: two runs
    at once would each save their own copy, and the last would drop the other's rows. Held until the process ends."""
    done = git(main, "rev-parse", "--git-common-dir")
    folder = os.path.join(main, done.stdout.strip()) if done and done.returncode == 0 else ""
    if not os.path.isdir(folder):
        raise KnowledgeError("git can't say where its own folder is, so nothing can be written")
    handle = open(os.path.join(folder, LOCK), "a")
    try:
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        handle.close()
        raise KnowledgeError("another knowledge.py run is writing the index; try again when it ends")
    return handle


class Store:
    """The tracked index and the machine's own file, read and written together."""

    def __init__(self, config: dict, top: str, main: str):
        self.config, self.top, self.main = config, top, main
        self.index_path = os.path.join(top, config["index"])
        self.local_path = os.path.join(main, config["inbox"], LOCAL)
        self.tracked = read_rows(self.index_path, TRACKED_FIELDS, "the knowledge index")
        self.local = read_rows(self.local_path, LOCAL_FIELDS, "the inbox's local file")

    def require_ignored(self) -> None:
        require_ignored(self.config, self.main)

    def save(self) -> None:
        self.require_ignored()
        os.makedirs(os.path.join(self.main, self.config["inbox"]), exist_ok=True)
        write_rows(self.local_path, self.local)
        write_rows(self.index_path, self.tracked)

    def add(self, path: str, aka: "list[str]", now: os.stat_result, digest: str, date: str) -> str:
        """A new source's two rows: what the team may see, and what only this machine keeps."""
        source = new_id(set(self.tracked) | set(self.local))
        self.local[source] = {"id": source, "path": path, "aka": aka, "size": now.st_size, "mtime": now.st_mtime_ns,
                              "hash": digest, "distilled": ""}
        self.tracked[source] = {"id": source, "date": date, "topics": [], "scan": scan(os.path.join(self.main, path)),
                                "cited_by": []}
        return source

    def relocate(self, source: str, path: str, now: os.stat_result, *old: str) -> None:
        """The same content at a new path: its id kept, and its old path (and any others) with it."""
        row = self.local[source]
        row["aka"] = sorted(set(row["aka"]) | {row["path"], *old})
        row.update(path=path, size=now.st_size, mtime=now.st_mtime_ns)


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
                if not any(real_day(month, day) for _, month, day in DATE.findall(path)):   # dated by its time
                    store.tracked[source]["date"] = date_of(path, now)
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
            store.relocate(moved, path, now)
            by_path[path] = moved
            continue
        by_path[path] = store.add(path, [], now, digest, date_of(path, now))
    cites = entry_citations(store.config, store.top)
    for source, row in store.tracked.items():
        row["cited_by"] = sorted(entry for entry, ids in cites.items() if source in ids)
    store.save()


def state_of(store: Store, source: str, found: dict, quick: bool) -> "tuple[str, str]":
    """(absent, undistilled, changed or current, the source's hash now): absent when its file isn't on this machine;
    quick reads sizes and times only, never hashing, so its hash is the index's; otherwise a file whose size or time
    moved is hashed to settle it."""
    row = store.local.get(source)
    now = found.get(row["path"]) if row else None
    if now is None:
        return "absent", ""
    moved = (now.st_size, now.st_mtime_ns) != (row["size"], row["mtime"])
    if quick:
        digest = row["hash"]
        changed = moved or digest != row["distilled"]
    else:
        digest = (hash_of(os.path.join(store.main, row["path"])) or "") if moved else row["hash"]
        changed = digest != row["distilled"]
    if not row["distilled"]:
        return "undistilled", digest
    return ("changed" if changed else "current"), digest


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
        state, _ = state_of(store, source, found, quick)
        if state != "current":
            counts[state] += 1
    counts["missing"] = sum(1 for ids in entry_citations(store.config, store.top).values() if ids - set(store.tracked))
    return counts


def pending(store: Store) -> "tuple[list[dict], int]":
    """What /seams:distill reads, on this machine: each indexed source never distilled, or whose content moved on
    since it was, with its id, path, date, scan and why; and how many files the index doesn't know yet (index first).
    Paths are printed for the session only, never written anywhere."""
    found = present(store.config, store.main)
    rows = [row for source, row in store.local.items() if source in store.tracked]
    known = {row["path"] for row in rows} | {a for row in rows for a in row["aka"]}
    waiting = []
    for source in sorted(store.tracked):
        state, digest = state_of(store, source, found, quick=False)
        if state not in ("undistilled", "changed"):
            continue
        path = store.local[source]["path"]
        fresh = scan(os.path.join(store.main, path))    # the committed flag could be forged: the stricter one stands
        flagged = max(store.tracked[source]["scan"], fresh, key=SCANS.index)
        waiting.append({"id": source, "path": path, "date": store.tracked[source]["date"], "scan": flagged,
                        "hash": digest, "why": "changed since distilled" if state == "changed" else "not distilled"})
    return waiting, sum(1 for path in found if path not in known)


def report(counts: dict) -> str:
    return (f"Knowledge: {counts['undistilled']} not distilled, {counts['changed']} changed since distilled, "
            f"{counts['missing']} entries cite a missing source, {counts['new']} new, "
            f"{counts['absent']} not on this machine.")


def mark_distilled(store: Store, sources: "list[str]") -> int:
    if not sources:
        print("usage: knowledge.py distilled <id>...", file=sys.stderr)
        return 1
    found = present(store.config, store.main)
    for given in sources:
        source, _, read_at = given.partition(":")      # <id>:<hash> as pending showed it: what was actually read
        row = store.local.get(source)
        now = found.get(row["path"]) if row and source in store.tracked else None
        full = os.path.join(store.main, row["path"]) if now else ""
        digest = hash_of(full) if now else None
        if digest is None:
            print(f"Knowledge: {source[:40]} is not an indexed source on this machine", file=sys.stderr)
            return 1
        if read_at and read_at != digest:
            print(f"Knowledge: {source[:40]} changed after it was read: read it again; nothing was marked",
                  file=sys.stderr)
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
    holding it as a path (quoted, or with a slash beside it), or "": a script that reads data/ reads data/owner/, and
    a script beside data/owner/ may name it as owner/. Ignore rules name folders without reading them, so they don't
    count; anything else may read it (code, a skill's instructions, a build file), and erring towards staying is
    safe."""
    parts = rel.split(os.sep)
    folders = [os.sep.join(parts[:end]) for end in range(len(parts), 0, -1)]
    parent, base = os.path.dirname(rel), parts[-1]
    setting = git(main, "config", "--bool", "core.ignorecase")
    caseless = bool(setting) and setting.stdout.strip() == "true"     # a disk that ignores case reads Feeds/ as feeds/
    done = git(main, "grep", "--untracked", "-z", "-l", "-I", "-F", *(["-i"] if caseless else []),
               *(arg for f in folders + [base] for arg in ("-e", f)),
               "--", ".", ":(exclude)*ignore", f":(exclude,literal){rel}", f":(exclude,literal){inbox}")
    if done is None or done.returncode not in (0, 1):
        raise KnowledgeError("git can't say which files name a folder, so nothing can move")

    def naming(names: "list[str]") -> "re.Pattern":
        name = "(?:" + "|".join(re.escape(f) for f in names) + ")"
        return re.compile(rf"(?<![\w.-])(?:(?<=[/'\"`]){name}(?![\w.-])|{name}(?=[/'\"`]))",
                          re.IGNORECASE if caseless else 0)
    far, near = naming(folders), naming(folders + [base])
    for path in sorted(p for p in done.stdout.split("\0") if p):
        try:
            with open(os.path.join(main, path), encoding="utf-8", errors="replace") as handle:
                text = handle.read(SCAN_BYTES + 1)
        except OSError:
            continue
        beside = bool(parent) and path.startswith(parent + os.sep)
        if (near if beside else far).search(text) or len(text) > SCAN_BYTES:   # too long to read: it may name it
            return path
    return ""


def tracked_nodes(main: str) -> "set[tuple[int, int]]":
    """Every tracked file, by identity: a disk that ignores case or Unicode normalization (macOS) can spell a
    tracked file otherwise than git's index does (a case-only rename, NFD against NFC), and the identity is the same."""
    done = git(main, "ls-files", "-z")
    if done is None or done.returncode != 0:
        raise KnowledgeError("git can't say which files it tracks, so nothing can move")
    return {here for here in (node(os.path.join(main, path)) for path in done.stdout.split("\0") if path) if here}


# --- the journal: a move's every step, written before the first file moves, so a stop at any point (an error, an
# interrupt, a kill) loses no old path, and the next plan of the same folder finishes it in the same destination.

def journal_path(store: Store) -> str:
    return os.path.join(store.main, store.config["inbox"], JOURNAL)


def read_journal(store: Store) -> dict:
    try:
        text = read_text(journal_path(store), "the inbox's move journal")
    except FileNotFoundError:
        return {"folders": {}, "steps": []}
    inbox = os.path.normpath(store.config["inbox"])

    def under(path: object, root: str) -> bool:      # a relative, normal path inside root ("" is the repository)
        return isinstance(path, str) and not os.path.isabs(path) and os.path.normpath(path) == path \
            and path not in (".", "..") and not path.startswith(".." + os.sep) \
            and ".git" not in path.lower().split(os.sep) and (not root or path.startswith(root + os.sep))

    def outside_inbox(path: object) -> bool:
        return under(path, "") and path != inbox and not path.startswith(inbox + os.sep)
    try:
        journal = json.loads(text)
        sound = isinstance(journal, dict) and isinstance(journal.get("folders"), dict) \
            and isinstance(journal.get("steps"), list) \
            and all(outside_inbox(f) and under(d, inbox) for f, d in journal["folders"].items()) \
            and all(isinstance(step, dict) and outside_inbox(step.get("src")) and under(step.get("dest"), inbox)
                    and isinstance(step.get("hash"), str) and re.fullmatch(r"[0-9a-f]{64}", step["hash"])
                    and isinstance(step.get("date"), str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", step["date"])
                    for step in journal["steps"])
    except ValueError:
        sound = False
    if not sound:                                    # hand-edited or restored: it could point anywhere
        raise KnowledgeError("the inbox's move journal holds a step it can't trust: settle it by hand, then remove it")
    return journal


def write_journal(store: Store, journal: dict) -> None:
    if not journal["steps"]:
        if os.path.lexists(journal_path(store)):
            os.unlink(journal_path(store))           # the move's own record, finished: never a user's file
        return
    folder = os.path.dirname(journal_path(store))
    os.makedirs(folder, exist_ok=True)
    handle, temp = tempfile.mkstemp(dir=folder, prefix=JOURNAL + ".")
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as out:
            json.dump(journal, out, sort_keys=True)
            out.flush()
            os.fsync(out.fileno())
        os.replace(temp, journal_path(store))
    except BaseException:
        os.unlink(temp)                              # it holds source paths
        raise


def recover(store: Store) -> "dict[str, str]":
    """Settles a journal a stopped move left: each file it moved gets its rows (old path, date), and each it didn't
    stays planned. Returns the destination of every folder still under way."""
    journal = read_journal(store)
    if not journal["steps"]:
        return {}
    found = present(store.config, store.main)
    recorded = {row["path"] for row in store.local.values()}
    left = []
    for step in journal["steps"]:
        if os.path.lexists(os.path.join(store.main, step["src"])):
            left.append(step)
        elif step["dest"] not in recorded and os.path.isfile(os.path.join(store.main, step["dest"])):
            record_move(store, step, found)
    journal = {"steps": left, "folders": {f: d for f, d in journal["folders"].items()
                                          if any(s["src"].startswith(f + os.sep) for s in left)}}
    store.save()
    write_journal(store, journal)
    return journal["folders"]


def left_behind(real: str, read: "set[str]") -> "dict[str, int]":
    """What a folder holds that the move leaves where it is, by kind: hidden files (an export's .env), links, and
    files it can't read."""
    counts = {"hidden file": 0, "link": 0, "unreadable file": 0}
    for folder, dirs, names in os.walk(real):
        counts["link"] += sum(1 for d in dirs if os.path.islink(os.path.join(folder, d)))
        hidden_here = any(part.startswith(".") for part in os.path.relpath(folder, real).split(os.sep) if part != ".")
        for name in names:
            path = os.path.join(folder, name)
            if path in read:
                continue
            kind = ("link" if os.path.islink(path) else "hidden file" if hidden_here or name.startswith(".")
                    else "unreadable file")
            counts[kind] += 1
    return {kind: count for kind, count in counts.items() if count}


def plan_move(store: Store, folders: "list[str]", pending: "dict[str, str]") -> "list[dict]":
    """One item per folder named: where its files go (<inbox>/<date>-<name>/, or the destination of its move still
    under way), or why it stays."""
    main, inbox_rel = store.main, os.path.normpath(store.config["inbox"])
    inbox = os.path.join(main, inbox_rel)
    homes = [os.path.join(main, home) for home in listed(store.config.get("sources", ""))]
    layer = [os.path.join(root, part) for root in {store.top, main}
             for part in [CONFIG, store.config["index"]] + listed(store.config["entries"])]
    items, chosen, destinations, kept, tracked = [], [], set(), {}, None   # kept: a hash -> the copy the index keeps
    found = present(store.config, main)
    for source, row in sorted(store.local.items()):
        now = found.get(row["path"])
        if now is not None and source in store.tracked:
            same = (now.st_size, now.st_mtime_ns) == (row["size"], row["mtime"])
            kept.setdefault(row["hash"] if same else hash_of(os.path.join(main, row["path"])), row["path"])
    for given in folders:
        real = os.path.realpath(os.path.join(main, given))
        rel = os.path.relpath(real, main)
        item = {"folder": os.path.normpath(given), "path": rel, "moves": [], "dups": [], "tracked": [], "left": {},
                "why": "", "stays": False}
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
        files = list(files_under(real))
        if not files:
            item["why"] = ": refused: it holds no files to move"
            continue
        tracked = tracked_nodes(main) if tracked is None else tracked
        name = os.path.basename(real)
        newest = max(now.st_mtime for _, now in files)
        item["dest"] = pending.get(rel) or os.path.join(
            inbox_rel, name if dated(name) else time.strftime("%Y-%m-%d-", time.gmtime(newest)) + name)
        if item["dest"].casefold() in destinations or (os.path.lexists(os.path.join(main, item["dest"]))
                                                       and rel not in pending):
            item["why"] = f": refused: {shown(item['dest'])}/ already exists"
            continue
        moves, mine = [], {}                         # this folder's copies: kept only once it is accepted
        for path, now in files:
            src = os.path.relpath(path, main)
            if (now.st_dev, now.st_ino) in tracked:  # moving it into the inbox would take it out of git
                item["tracked"].append(src)
                continue
            digest = hash_of(path)
            if digest is None:
                continue
            if digest in kept or digest in mine:
                item["dups"].append({"src": src, "kept": kept.get(digest) or mine[digest]})
                continue
            mine[digest] = os.path.join(item["dest"], os.path.relpath(path, real))
            moves.append({"src": src, "dest": mine[digest], "size": now.st_size, "mtime": now.st_mtime_ns,
                          "hash": digest, "date": date_of(src, now)})
        if any(os.path.lexists(os.path.join(main, step["dest"])) for step in moves):
            item.update(why=f": refused: a file already sits where one of its files would go in "
                            f"{shown(item['dest'])}/", dups=[], tracked=[])
            continue
        destinations.add(item["dest"].casefold())
        kept.update(mine)
        item["moves"] = moves
        item["left"] = left_behind(real, {path for path, _ in files})
    planned = [step["dest"] for item in items for step in item["moves"]]
    if planned:
        check = planned + [os.path.relpath(journal_path(store), main)]
        done = git(main, "check-ignore", "-z", "--stdin", input="\0".join(check) + "\0")
        if done is None or done.returncode not in (0, 1) or not set(check) <= set(done.stdout.split("\0")):
            raise KnowledgeError(f"git would not ignore every file the move would put in the inbox "
                                 f"({store.config['inbox']}): check its .gitignore rules first")
    return items


def counted(counts: "dict[str, int]") -> str:
    return ", ".join(f"{count} {kind}{'' if count == 1 else 's'}" for kind, count in counts.items())


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
        if item["left"]:
            lines.append(f"    left where they are, outside the inbox, where git may see them: {counted(item['left'])}")
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


def plan_code(items: "list[dict]", minute: int) -> str:
    """The whole list (every file's path, size, time and hash, which the plan doesn't print) and the minute the plan
    was made, so a yes covers exactly what was planned, then, and expires."""
    body = json.dumps([f"{minute:x}", items], sort_keys=True)
    return f"{minute:x}-" + hashlib.sha256(body.encode()).hexdigest()[:12]


def move(store: Store, argv: "list[str]") -> int:
    agreed = argv[1] if argv[:1] == ["--yes"] and len(argv) > 1 else None
    folders = argv[2:] if agreed is not None else argv
    if not folders or folders[0] == "--yes":
        print("usage: knowledge.py move [--yes <code>] <folder>...", file=sys.stderr)
        return 1
    store.require_ignored()                          # refused before the plan, so a yes can't be refused later
    items = plan_move(store, folders, recover(store))
    now = int(time.time() // 60)
    if agreed is None:
        print("\n".join(render_plan(items, store.config.get("sources", ""))))
        if any(item["moves"] or item["dups"] for item in items) and all(f.isprintable() for f in folders):
            print("To move exactly this, only after the user agrees to this plan, run: knowledge.py move --yes "
                  + plan_code(items, now) + " " + " ".join(shlex.quote(f) for f in folders))
        return 0
    try:
        minute = int(agreed.partition("-")[0], 16)
    except ValueError:
        minute = -1
    if minute < 0 or agreed != plan_code(items, minute):
        print("Knowledge: the plan changed since it was shown, or that code is not its own: nothing moved; run it "
              "again without --yes to see the plan", file=sys.stderr)
        return 1
    if not 0 <= now - minute <= CODE_MINUTES:
        print(f"Knowledge: that plan's yes has expired (it lasts {CODE_MINUTES} minutes): nothing moved; run it "
              "again without --yes to see the plan", file=sys.stderr)
        return 1
    steps = [step for item in items for step in item["moves"]]
    journal = read_journal(store)
    journal["steps"] = [s for s in journal["steps"] if s["src"] not in {step["src"] for step in steps}] + steps
    journal["folders"].update({item["path"]: item["dest"] for item in items if item["moves"]})
    write_journal(store, journal)                    # before the first file moves: a kill can't lose an old path
    found, moved, emptied = present(store.config, store.main), 0, set()
    inbox = os.path.realpath(os.path.join(store.main, store.config["inbox"]))
    try:
        for item in items:
            for step in item["moves"]:
                dest = os.path.join(store.main, step["dest"])
                os.makedirs(os.path.dirname(dest), exist_ok=True)
                here = os.path.realpath(os.path.dirname(dest))
                if here != inbox and not inside(here, inbox):   # a link inside the inbox can't lead a file out
                    raise NotADirectoryError(errno.ENOTDIR, "a destination's folder is not inside the inbox")
                if os.path.lexists(dest):            # never over a file: a rename would replace it
                    raise FileExistsError(errno.EEXIST, "a file is already where one would go")
                os.rename(os.path.join(store.main, step["src"]), dest)
                record_move(store, step, found)
                moved += 1
                folder = os.path.dirname(step["src"])
                while folder and folder != os.path.dirname(item["path"]):
                    emptied.add(folder)
                    folder = os.path.dirname(folder)
    except BaseException as error:                   # an interrupt too: what moved keeps its old path
        store.save()
        if isinstance(error, OSError):
            raise KnowledgeError(f"the move stopped after {moved} of {len(steps)} files ({error.strerror}); "
                                 "nothing was deleted, the index records what moved, and the next plan finishes it")
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
    recover(store)                                   # the journal keeps only what is still under way
    left = sum(sum(item["left"].values()) for item in items)
    print(f"Knowledge: moved {moved} files from {sum(1 for i in items if i['moves'])} folders into the inbox; "
          f"{sum(len(i['dups']) for i in items)} duplicates stay where they were, kept once in the index; "
          f"{sum(len(i['tracked']) for i in items)} tracked files refused; {left} files left where they were, "
          f"outside the inbox; {sum(1 for i in items if i['stays'])} folders stay where they are. "
          "Nothing was deleted.")
    return 0


def record_move(store: Store, step: dict, found: "dict[str, os.stat_result]") -> None:
    """A moved file's rows: its old path kept, and its date read where it was (a folder's date prefix is not it).
    A source that left the inbox and comes back keeps its id, as index's moved sources do."""
    now = os.lstat(os.path.join(store.main, step["dest"]))
    back = next((s for s, row in sorted(store.local.items()) if row["hash"] == step["hash"] and s in store.tracked
                 and row["path"] not in found), None)
    if back:
        store.relocate(back, step["dest"], now, step["src"])
    else:
        store.add(step["dest"], [step["src"]], now, step["hash"], step["date"])


def main(argv: "list[str]") -> int:
    command = argv[0] if argv else "status"
    if command not in ("status", "pending", "index", "distilled", "topics", "move"):
        print(f"knowledge.py: unknown command {command[:40]}", file=sys.stderr)
        return 1
    top, main_root, belongs = roots(os.getcwd())
    try:
        if not belongs:
            raise KnowledgeError("this checkout's .git points at another repository's, so its inbox isn't read")
        config = read_config(top, main_root)
        if config is None:
            print("Knowledge: no knowledge config here, so the layer is off.")
            return 0
        if command not in ("status", "pending"):    # a writing run: the lock first, then what it reads
            require_ignored(config, main_root)
            lock = hold_lock(main_root)              # noqa: F841  held until the process ends
        store = Store(config, top, main_root)
        if command == "index":
            recover(store)                           # a stopped move's old paths, before index sees its files
            index(store)
        elif command == "move":
            return move(store, argv[1:])
        elif command == "pending":
            waiting, new = pending(store)
            if "--json" in argv:
                print(json.dumps(waiting, sort_keys=True))
            else:
                for row in waiting:
                    print(f"{row['id']}:{row['hash']}  {row['date']}  {row['why']}, {row['scan']}: {shown(row['path'])}")
                if new:
                    print(f"Knowledge: {new} file{'s' if new != 1 else ''} the index doesn't know yet: run knowledge.py "
                          "index first.")
                if not waiting and not new:
                    print("Knowledge: nothing waits to be distilled.")
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
