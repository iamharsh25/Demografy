"""Enumerate saved conversation threads for the chat widget.

Kept in a separate module so callers can ``from chat_history.thread_list
import list_threads`` without depending on every symbol in
``storage.py`` (helps with partial saves / stale bytecode during dev).

``list_threads`` lazily imports ``_user_dir`` from ``storage`` on each
call so there is no import cycle at module load time.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import List, Optional

_THREAD_FILE_RE = re.compile(r"^(\d{8}T\d{6})_([A-Za-z0-9]{8,})\.jsonl$")
_TITLE_MAX = 60


def list_threads(user_id: str) -> List[dict]:
    """Return non-empty threads for ``user_id``, newest activity first.

    Each entry is::

        {
            "thread_id": str,
            "title": str,
            "updated_at": str,
            "message_count": int,
        }
    """
    from chat_history.storage import _user_dir

    directory = _user_dir(user_id)
    if not directory.exists():
        return []

    rows: List[dict] = []
    try:
        files = sorted(directory.iterdir())
    except OSError:
        return []

    for path in files:
        if not path.is_file() or path.suffix != ".jsonl":
            continue
        meta = _read_thread_meta(path)
        if meta is None:
            continue
        rows.append(meta)

    rows.sort(key=lambda r: r.get("updated_at") or "", reverse=True)
    return rows


def _read_thread_meta(path: Path) -> Optional[dict]:
    match = _THREAD_FILE_RE.match(path.name)
    if not match:
        return None
    thread_id = match.group(2)

    title: Optional[str] = None
    last_ts: Optional[str] = None
    count = 0
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
                count += 1
                if title is None and role == "user":
                    title = _truncate_title(content)
                ts = record.get("ts")
                if isinstance(ts, str):
                    last_ts = ts
    except OSError:
        return None

    if count == 0:
        return None

    return {
        "thread_id": thread_id,
        "title": title or "New chat",
        "updated_at": last_ts or "",
        "message_count": count,
    }


def _truncate_title(text: str, limit: int = _TITLE_MAX) -> str:
    cleaned = " ".join((text or "").split())
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 1].rstrip() + "\u2026"
