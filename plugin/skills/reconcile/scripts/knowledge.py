#!/usr/bin/env python3
"""Seams' knowledge index (ADR 0008): a repository opts in with a knowledge config, `docs/agents/knowledge.md`, whose
fenced `knowledge` block names its inbox (raw sources, gitignored), its tracked index, its entries and its other
source homes. This keeps the index current and reports what is undistilled, changed, missing or not on this machine.
It reads only local files and runs no network call; it never writes a source's content anywhere.

    knowledge.py status [--quick] [--json]   counts (--quick: sizes and times only, never hashing; without
                                                   it, every source on this machine is hashed)
    knowledge.py index                       add and update the index's rows
    knowledge.py distilled <id>...           mark sources distilled at their current content
    knowledge.py topics <id> <a,b,...>       set a source's topics (what an action searches by)

The config's block, one `key: value` per line (paths from the repository's root; lists comma-separated):

    inbox            the raw sources' folder (gitignored; read from the main checkout, so worktrees see it)
    index            the tracked index, one JSON row per source, sorted by id
    entries          the folder(s) of knowledge entries; an entry cites a source by its id (src-<10 hex>)
    sources          other homes holding the owner's word outside the approval process, indexed in place
    format           the entry format: markdown (the default), or the project's own (a schema's path)
    approved         how an approved entry is recognised (for Claude, not this script)
    approval-record  the file the owner's approvals live in, if the project keeps one
    escalation       the tag for a question only the owner can answer (NEEDS-OWNER)

No config: the layer is off, and every command says so and writes nothing. A malformed config or index is reported
in one line (exit 2)."""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import time

CONFIG = os.path.join("docs", "agents", "knowledge.md")
KEYS = {"inbox", "index", "entries", "format", "escalation", "sources", "approved", "approval-record"}
REQUIRED = ("inbox", "index", "entries")


class ConfigError(Exception):
    pass


def git(cwd: str, *args: str) -> "str | None":
    try:
        done = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, timeout=5,
                              stdin=subprocess.DEVNULL)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return done.stdout.strip() if done.returncode == 0 else None


def roots(cwd: str) -> "tuple[str, str]":
    """(the worktree's root, the main checkout's root): the index and the entries are tracked, so they are read
    where the session works; the inbox is gitignored, so it exists only in the main checkout."""
    top = git(cwd, "rev-parse", "--show-toplevel") or cwd
    common = git(cwd, "rev-parse", "--path-format=absolute", "--git-common-dir")
    main = os.path.dirname(common) if common and os.path.basename(common) == ".git" else top
    return top, main


def read_config(top: str) -> "dict | None":
    path = os.path.join(top, CONFIG)
    try:
        text = open(path, encoding="utf-8").read()
    except OSError:
        return None
    block = re.search(r"^```knowledge\s*\n(.*?)^```", text, re.S | re.M)
    if not block:
        raise ConfigError(f"{CONFIG} has no ```knowledge block")
    config = {}
    for line in block.group(1).splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        key, sep, value = line.partition(":")
        key = key.strip().lower()
        if not sep or key not in KEYS:
            raise ConfigError(f"{CONFIG}: unknown line in the knowledge block: {line.strip()[:60]}")
        config[key] = value.strip()
    missing = [k for k in REQUIRED if not config.get(k)]
    if missing:
        raise ConfigError(f"{CONFIG}: the knowledge block needs {', '.join(missing)}")
    return config


DATE = re.compile(r"(\d{4}-\d{2}-\d{2})")
# A credential in a raw source (a chat export's API key): the row says "secrets" and nothing from the file is ever
# written. A file it can't read as text (a PDF, an image, a document) is "unscanned", never "clean".
CREDENTIALS = re.compile(
    r"AKIA[0-9A-Z]{16}|\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_\w{20,}|sk-[A-Za-z0-9_-]{20,}|xox[abprs]-[\w-]{10,})"
    r"|-----BEGIN [A-Z ]*PRIVATE KEY-----"
    r"|(?i:\b(?:api[ _-]?key|secret|token|password|passwd|bearer|authorization)\b[\"']?\s*[:=]?\s*[\"']?[^\s\"']{8,})")
BINARY = (".pdf", ".png", ".jpg", ".jpeg", ".gif", ".webp", ".heic", ".docx", ".doc", ".xlsx", ".xls", ".pptx",
          ".zip", ".mp3", ".m4a", ".mp4", ".mov")
SCAN_BYTES = 8 << 20


def scan(path: str) -> str:
    if path.lower().endswith(BINARY):
        return "unscanned"
    with open(path, "rb") as handle:
        data = handle.read(SCAN_BYTES)
    if b"\x00" in data[:8192]:
        return "unscanned"
    return "secrets" if CREDENTIALS.search(data.decode("utf-8", errors="replace")) else "clean"


def hash_of(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def present(config: dict, main_root: str) -> "dict[str, os.stat_result]":
    """Every source file on this machine, by its path from the main checkout: the inbox's files and the other source
    homes (a file, or a folder's files). Hidden files (.DS_Store) are not sources."""
    homes = [config["inbox"]] + [s.strip() for s in config.get("sources", "").split(",") if s.strip()]
    found = {}
    for home in homes:
        base = os.path.join(main_root, home)
        if os.path.isfile(base):
            found[os.path.relpath(base, main_root)] = os.stat(base)
            continue
        for folder, dirs, files in os.walk(base):
            dirs[:] = sorted(d for d in dirs if not d.startswith("."))
            for name in sorted(files):
                if not name.startswith("."):
                    path = os.path.join(folder, name)
                    found[os.path.relpath(path, main_root)] = os.stat(path)
    return found


def read_index(path: str) -> "list[dict]":
    try:
        lines = open(path, encoding="utf-8").read().splitlines()
    except OSError:
        return []
    rows = []
    for number, line in enumerate(lines, 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except ValueError:
            row = None
        if not isinstance(row, dict) or not all(k in row for k in ("id", "path", "size", "mtime", "hash")):
            raise ConfigError(f"the knowledge index {os.path.basename(path)} has a line it can't read (line {number})")
        rows.append(row)
    return rows


def entry_texts(config: dict, top: str) -> "dict[str, str]":
    texts = {}
    for home in (s.strip() for s in config["entries"].split(",") if s.strip()):
        for folder, dirs, files in os.walk(os.path.join(top, home)):
            dirs[:] = sorted(d for d in dirs if not d.startswith("."))
            for name in sorted(files):
                path = os.path.join(folder, name)
                try:
                    texts[os.path.relpath(path, top)] = open(path, encoding="utf-8", errors="replace").read()
                except OSError:
                    pass
    return texts


def new_row(path: str, stat: os.stat_result, digest: str) -> dict:
    dated = DATE.findall(path)
    return {"id": "src-" + hashlib.sha1(path.encode()).hexdigest()[:10], "path": path, "aka": [],
            "date": dated[-1] if dated else time.strftime("%Y-%m-%d", time.gmtime(stat.st_mtime)),
            "size": stat.st_size, "mtime": stat.st_mtime_ns, "hash": digest, "scan": "", "topics": [],
            "distilled": "", "cited_by": []}


def index(config: dict, top: str, main_root: str) -> None:
    index_path = os.path.join(top, config["index"])
    rows = {r["path"]: r for r in read_index(index_path)}
    found = present(config, main_root)
    for path, stat in found.items():
        row = rows.get(path)
        if row and (row["size"], row["mtime"]) == (stat.st_size, stat.st_mtime_ns):
            continue
        digest = hash_of(os.path.join(main_root, path))
        moved = None if row else next((r for p, r in rows.items() if p not in found and r["hash"] == digest), None)
        if moved:                                   # the same content at a new path: the same source, its id kept
            del rows[moved["path"]]
            moved["aka"] = sorted(set(moved.get("aka", [])) | {moved["path"]})
            moved["path"] = path
            row = rows[path] = moved
            row.update(size=stat.st_size, mtime=stat.st_mtime_ns)
        elif row:
            row.update(size=stat.st_size, mtime=stat.st_mtime_ns, hash=digest)
        else:
            row = rows[path] = new_row(path, stat, digest)
        row["scan"] = scan(os.path.join(main_root, path))
    texts = entry_texts(config, top)
    for row in rows.values():
        row["cited_by"] = sorted(entry for entry, text in texts.items() if row["id"] in text)
    write_index(index_path, rows.values())


def write_index(index_path: str, rows) -> None:
    os.makedirs(os.path.dirname(index_path) or ".", exist_ok=True)
    temp = index_path + ".tmp"
    with open(temp, "w", encoding="utf-8") as out:
        for row in sorted(rows, key=lambda r: r["id"]):
            out.write(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n")
    os.replace(temp, index_path)


SOURCE_ID = re.compile(r"\bsrc-[0-9a-f]{10}\b")


def status(config: dict, top: str, main_root: str, quick: bool) -> dict:
    """The counts: sources on this machine the index lacks (new), present sources never distilled, present sources
    whose content moved on since they were distilled, ids entries cite that the index lacks, and rows whose file is
    not on this machine (a teammate's checkout, or a source removed): those are never counted as changed."""
    rows = read_index(os.path.join(top, config["index"]))
    found = present(config, main_root)
    known = {r["path"] for r in rows} | {a for r in rows for a in r.get("aka", [])}
    counts = {"new": sum(1 for path in found if path not in known), "undistilled": 0, "changed": 0, "missing": 0,
              "absent": 0}
    for row in rows:
        stat = found.get(row["path"])
        if stat is None:
            counts["absent"] += 1
        elif not row.get("distilled"):
            counts["undistilled"] += 1
        elif quick:
            counts["changed"] += (stat.st_size, stat.st_mtime_ns) != (row["size"], row["mtime"])
        else:
            counts["changed"] += hash_of(os.path.join(main_root, row["path"])) != row["distilled"]
    ids = {r["id"] for r in rows}
    cited = {i for text in entry_texts(config, top).values() for i in SOURCE_ID.findall(text)}
    counts["missing"] = len(cited - ids)
    return counts


def report(counts: dict) -> str:
    parts = [f"{counts['undistilled']} not distilled", f"{counts['changed']} changed since distilled",
             f"{counts['missing']} cited but missing", f"{counts['new']} new", f"{counts['absent']} not on this machine"]
    return "Knowledge: " + ", ".join(parts) + "."


def set_topics(config: dict, top: str, source: str, topics: str) -> int:
    index_path = os.path.join(top, config["index"])
    rows = {r["id"]: r for r in read_index(index_path)}
    if source not in rows:
        print(f"Knowledge: {source} is not an indexed source", file=sys.stderr)
        return 1
    rows[source]["topics"] = sorted({t.strip().lower() for t in topics.split(",") if t.strip()})
    write_index(index_path, rows.values())
    return 0


def mark_distilled(config: dict, top: str, main_root: str, ids: "list[str]") -> int:
    index_path = os.path.join(top, config["index"])
    rows = {r["id"]: r for r in read_index(index_path)}
    for source in ids:
        row = rows.get(source)
        path = os.path.join(main_root, row["path"]) if row else ""
        if not row or not os.path.isfile(path):
            print(f"Knowledge: {source} is not an indexed source on this machine", file=sys.stderr)
            return 1
        stat = os.stat(path)
        digest = hash_of(path)
        row.update(size=stat.st_size, mtime=stat.st_mtime_ns, hash=digest, distilled=digest)
    write_index(index_path, rows.values())
    return 0


def main(argv: "list[str]") -> int:
    command = argv[0] if argv else "status"
    if command not in ("status", "index", "distilled", "topics"):
        print(f"knowledge.py: unknown command {command}", file=sys.stderr)
        return 1
    top, main_root = roots(os.getcwd())
    try:
        config = read_config(top)
    except ConfigError as error:
        print(f"Knowledge config error: {error}")
        return 2
    if config is None:
        print("Knowledge: no knowledge config here, so the layer is off.")
        return 0
    try:
        if command == "index":
            index(config, top, main_root)
        elif command == "topics":
            if len(argv) != 3:
                print("usage: knowledge.py topics <id> <a,b,...>", file=sys.stderr)
                return 1
            return set_topics(config, top, argv[1], argv[2])
        elif command == "distilled":
            return mark_distilled(config, top, main_root, argv[1:])
        else:
            counts = status(config, top, main_root, quick="--quick" in argv)
            print(json.dumps(counts, sort_keys=True) if "--json" in argv else report(counts))
    except ConfigError as error:
        print(f"Knowledge index error: {error}")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
