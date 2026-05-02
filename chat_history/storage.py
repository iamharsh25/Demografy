"""Disk persistence for per-user, per-thread chat transcripts.

Pure I/O: no Streamlit imports, no LangChain dependencies. Each user has
a directory under ``ChatHistory/<safe_user_id>/`` containing one
append-only ``<filename>.jsonl`` per conversation thread.

The filename embeds the creation timestamp and a short uuid so threads
sort chronologically on disk and ids stay unique across reboots:

    ChatHistory/
      user_026/
        20260502T013918_a1b2c3d4.jsonl
        20260502T150412_e5f6a7b8.jsonl

Thread ids exposed through the public API are the short uuid portion
(``a1b2c3d4``); we resolve filenames lazily so callers never deal with
paths.

Record shape per JSONL line::

    {"ts": "2026-05-02T01:39:18+00:00",
     "role": "user" | "assistant",
     "content": "...",
     "sql": "SELECT ..." | null,
     "image_b64": "<png base64>" | null}

JSONL is preferred over a single JSON array so appends are crash-safe
(we never rewrite earlier turns) and so it's trivial to migrate to a
real database later.
"""

from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, List, Optional


HISTORY_DIR = Path(__file__).resolve().parent.parent / "ChatHistory"

_SAFE_ID_RE = re.compile(r"[^A-Za-z0-9_-]+")


# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------

def _safe_user_id(user_id: str) -> str:
    """Reduce ``user_id`` to characters safe for use in a filename.

    Anything outside ``[A-Za-z0-9_-]`` is replaced with ``_``. Falls back
    to ``"unknown"`` if the result would be empty so we never end up
    writing to a hidden or unnamed directory.
    """
    cleaned = _SAFE_ID_RE.sub("_", (user_id or "").strip())
    return cleaned or "unknown"


def _user_dir(user_id: str) -> Path:
    """Return the per-user thread directory, migrating legacy files lazily.

    The first time we touch a user's directory we also move any legacy
    single-file transcript (``ChatHistory/<user>.jsonl`` from the v1
    layout) into the new folder so the View list still surfaces it.
    """
    safe = _safe_user_id(user_id)
    directory = HISTORY_DIR / safe
    _migrate_legacy_file(safe, directory)
    return directory


def _ensure_user_dir(user_id: str) -> Path:
    directory = _user_dir(user_id)
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _now_filename_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")


def new_thread_id() -> str:
    """Return a fresh short thread id (8 hex chars).

    The id is not tied to the filename's timestamp prefix; on first
    append we mint the filename ``<stamp>_<id>.jsonl``. This means
    callers can hand out a thread id immediately and the file only
    materialises once a real message is persisted.
    """
    return uuid.uuid4().hex[:8]


def _thread_path(user_id: str, thread_id: str, *, create: bool = False) -> Optional[Path]:
    """Resolve the JSONL path for ``thread_id`` under ``user_id``.

    If a file already exists with this id, return it. If ``create`` is
    True and no file exists yet, return a fresh path with a current
    timestamp prefix so the next append materialises it. Otherwise
    return ``None``.
    """
    directory = _user_dir(user_id)
    safe_id = _SAFE_ID_RE.sub("_", thread_id or "") or new_thread_id()

    if directory.exists():
        for path in directory.glob(f"*_{safe_id}.jsonl"):
            return path

    if not create:
        return None

    return directory / f"{_now_filename_stamp()}_{safe_id}.jsonl"


# ---------------------------------------------------------------------------
# Legacy migration
# ---------------------------------------------------------------------------

def _migrate_legacy_file(safe_user_id: str, directory: Path) -> None:
    """Move ``ChatHistory/<user>.jsonl`` into ``ChatHistory/<user>/`` once.

    Best-effort: if the legacy file exists, the new directory does not,
    and the move is permitted, we transfer the file in as a single
    legacy thread so it shows up in the View list. Any error is
    swallowed - chat must continue working even if migration fails.
    """
    legacy = HISTORY_DIR / f"{safe_user_id}.jsonl"
    if not legacy.exists() or directory.exists():
        return
    try:
        directory.mkdir(parents=True, exist_ok=True)
        target = directory / f"{_now_filename_stamp()}_legacy00.jsonl"
        legacy.replace(target)
    except OSError:
        pass


# ---------------------------------------------------------------------------
# Read / write API
# ---------------------------------------------------------------------------

def load_history(user_id: str, thread_id: str) -> List[dict]:
    """Return the full chronological transcript for ``thread_id``.

    Missing thread or file -> empty list. Malformed lines are skipped
    silently so one bad write never poisons the rest of the history.
    """
    if not thread_id:
        return []
    path = _thread_path(user_id, thread_id)
    if path is None or not path.exists():
        return []

    out: List[dict] = []
    try:
        with path.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if not isinstance(record, dict):
                    continue
                role = record.get("role")
                content = record.get("content")
                if role not in ("user", "assistant") or not isinstance(content, str):
                    continue
                # Normalise optional image payload (large; keep as-is for UI hydrate).
                if record.get("image_b64") is not None and not isinstance(
                    record.get("image_b64"), str
                ):
                    record = {**record, "image_b64": None}
                out.append(record)
    except OSError:
        return []
    return out


def append_message(
    user_id: str,
    thread_id: str,
    role: str,
    content: str,
    *,
    sql: Optional[str] = None,
    image_b64: Optional[str] = None,
    ts: Optional[str] = None,
) -> None:
    """Append one message record to ``thread_id``'s transcript file.

    Creates the user directory and the thread file on first use. Any
    I/O error propagates to the caller so a higher layer can decide
    whether to surface it; the chat engine swallows it as best-effort.
    """
    if role not in ("user", "assistant"):
        raise ValueError(f"unsupported role: {role!r}")
    if not isinstance(content, str):
        raise TypeError("content must be a string")
    if not thread_id:
        raise ValueError("thread_id is required")

    record = {
        "ts": ts or _now_iso(),
        "role": role,
        "content": content,
        "sql": sql,
        "image_b64": image_b64,
    }

    _ensure_user_dir(user_id)
    path = _thread_path(user_id, thread_id, create=True)
    assert path is not None  # create=True always returns a path
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")
        fh.flush()


def last_n_turns(user_id: str, thread_id: str, n: int = 5) -> List[dict]:
    """Return the most recent ``n`` user turns plus their assistant replies.

    A "turn" is a user message and the assistant message that immediately
    follows it. Orphan user messages (no reply yet) are still included so
    the agent can see what was asked. Output is in chronological order.

    Scoped strictly to ``thread_id`` so the agent never bleeds context
    across separate conversations.
    """
    if n <= 0 or not thread_id:
        return []
    return _select_last_turns(load_history(user_id, thread_id), n)


def _select_last_turns(history: Iterable[dict], n: int) -> List[dict]:
    """Pure helper used by ``last_n_turns`` and exposed for tests."""
    items = list(history)

    selected_indices: List[int] = []
    user_count = 0
    i = len(items) - 1
    while i >= 0 and user_count < n:
        record = items[i]
        if record.get("role") == "user":
            selected_indices.append(i)
            if i + 1 < len(items) and items[i + 1].get("role") == "assistant":
                selected_indices.append(i + 1)
            user_count += 1
        i -= 1

    if not selected_indices:
        return []

    selected_indices.sort()
    return [items[idx] for idx in selected_indices]


def __getattr__(name: str):
    """Backward compat: ``from chat_history.storage import list_threads``.

    Thread listing now lives in ``thread_list.py``; older call sites that
    still import ``list_threads`` from this module keep working.
    """
    if name == "list_threads":
        from chat_history.thread_list import list_threads as _list_threads

        return _list_threads
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
