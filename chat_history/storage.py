"""Disk persistence for per-user chat transcripts.

Pure I/O: no Streamlit imports, no LangChain dependencies. Each user has
a single append-only ``ChatHistory/<safe_user_id>.jsonl`` file with one
JSON record per message. JSONL is preferred over a single JSON array so
appends are crash-safe (we never rewrite earlier turns) and so it's
trivial to migrate to a real database later.

Record shape::

    {"ts": "2026-05-02T01:39:18+00:00",
     "role": "user" | "assistant",
     "content": "...",
     "sql": "SELECT ..." | null}
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, List, Optional


HISTORY_DIR = Path(__file__).resolve().parent.parent / "ChatHistory"


_SAFE_ID_RE = re.compile(r"[^A-Za-z0-9_-]+")


def _safe_user_id(user_id: str) -> str:
    """Reduce ``user_id`` to characters safe for use in a filename.

    Anything outside ``[A-Za-z0-9_-]`` is replaced with ``_``. Falls back
    to ``"unknown"`` if the result would be empty so we never end up
    writing to a hidden or unnamed file.
    """
    cleaned = _SAFE_ID_RE.sub("_", (user_id or "").strip())
    return cleaned or "unknown"


def _user_path(user_id: str) -> Path:
    return HISTORY_DIR / f"{_safe_user_id(user_id)}.jsonl"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _ensure_dir() -> None:
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)


def load_history(user_id: str) -> List[dict]:
    """Return the full chronological transcript for ``user_id``.

    Missing file -> empty list. Malformed lines are skipped silently so
    one bad write never poisons the rest of the history.
    """
    path = _user_path(user_id)
    if not path.exists():
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
                out.append(record)
    except OSError:
        return []
    return out


def append_message(
    user_id: str,
    role: str,
    content: str,
    *,
    sql: Optional[str] = None,
    ts: Optional[str] = None,
) -> None:
    """Append one message record to the user's transcript file.

    Best-effort: any I/O error is swallowed by the caller (this function
    raises, but ``chat_engine`` wraps the call in try/except so a disk
    issue never blocks the agent flow).
    """
    if role not in ("user", "assistant"):
        raise ValueError(f"unsupported role: {role!r}")
    if not isinstance(content, str):
        raise TypeError("content must be a string")

    record = {
        "ts": ts or _now_iso(),
        "role": role,
        "content": content,
        "sql": sql,
    }

    _ensure_dir()
    path = _user_path(user_id)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")
        fh.flush()


def last_n_turns(user_id: str, n: int = 5) -> List[dict]:
    """Return the most recent ``n`` user turns plus their assistant replies.

    A "turn" is a user message and the assistant message that immediately
    follows it. Orphan user messages (no reply yet) are still included so
    the agent can see what was asked. Output is in chronological order.
    """
    if n <= 0:
        return []
    return _select_last_turns(load_history(user_id), n)


def _select_last_turns(history: Iterable[dict], n: int) -> List[dict]:
    """Pure helper used by ``last_n_turns`` and exposed for tests."""
    items = list(history)

    # Walk backwards collecting up to n user messages along with the
    # assistant message that came right after them (if any).
    selected_indices: List[int] = []
    user_count = 0
    i = len(items) - 1
    while i >= 0 and user_count < n:
        record = items[i]
        if record.get("role") == "user":
            selected_indices.append(i)
            # The assistant reply, if present, sits at i+1.
            if i + 1 < len(items) and items[i + 1].get("role") == "assistant":
                selected_indices.append(i + 1)
            user_count += 1
        i -= 1

    if not selected_indices:
        return []

    selected_indices.sort()
    return [items[idx] for idx in selected_indices]
