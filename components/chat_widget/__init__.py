"""Demografy chat widget custom component.

A single, persistent iframe that owns:
  - the chat FAB (toggles the panel open/closed)
  - the chat panel header, message thread, and input
  - the expand/split layout toggle
  - the new-chat (+) button and past-chats (history) overlay

Communication contract
----------------------
Python -> JS (component args, pushed every Streamlit render):

    messages          list[{"role", "content", "image_b64"?}]   thread bubbles
    pending           bool                        Thinking spinner on?
    thinking_label    str                         Text next to dots while ``pending``
    limit_reached     bool                        disable input + show
                                                  cooldown banner when True
    threads           list[{"thread_id", ...}]    newest-first list for
                                                  the View overlay
    active_thread_id  str | None                  highlights the current
                                                  thread in the list
    suggestions       list[str]                   follow-up question chips
                                                  shown under the latest
                                                  assistant bubble
    cooldown_until_ms int                         epoch ms when the limit
                                                  cooldown ends; 0 means no
                                                  active cooldown. Drives
                                                  the live countdown label.

JS reconciles the DOM in place (no innerHTML rewrite, no iframe reload).

JS -> Python (one of three sticky payload shapes via setComponentValue):

    { "action": "question",     "question": str,    "ts": int }
    { "action": "new_chat",                           "ts": int }
    { "action": "open_thread",  "thread_id": str,   "ts": int }
    { "action": "chart",                              "ts": int }

Follow-up chips use ``"question"`` except the chart chip, which sends
``"chart"`` so the server can render the last chartable result without
re-querying.

``maybe_consume_bridge`` in ``chat_engine.py`` dedupes on ``ts`` and
dispatches on ``action``.

The component is declared (not ``components.html``) so Streamlit reuses
the same iframe across reruns - this is what kills the visible flicker
the previous body-embedded chat had.
"""

from pathlib import Path
from typing import Iterable, Optional

import streamlit.components.v1 as components


CHAT_WIDGET_KEY = "demografy_chat_widget_v1"

_FRONTEND_DIR = Path(__file__).parent / "frontend"

_component_func = components.declare_component(
    "demografy_chat_widget",
    path=str(_FRONTEND_DIR),
)


def render_chat_widget(
    messages: Iterable[dict],
    pending: bool,
    limit_reached: bool,
    *,
    thinking_label: str = "Thinking...",
    threads: Optional[Iterable[dict]] = None,
    active_thread_id: Optional[str] = None,
    suggestions: Optional[Iterable[str]] = None,
    cooldown_until_ms: int = 0,
    key: str = CHAT_WIDGET_KEY,
) -> Optional[dict]:
    """Render the persistent chat widget.

    Returns the latest payload submitted by the user (sticky across
    reruns; callers must dedupe by ``ts``) or ``None`` if no submission
    has happened yet.
    """
    return _component_func(
        messages=list(messages or []),
        pending=bool(pending),
        thinking_label=str(thinking_label or "Thinking..."),
        limit_reached=bool(limit_reached),
        threads=list(threads or []),
        active_thread_id=active_thread_id or "",
        suggestions=[str(s) for s in (suggestions or []) if s],
        cooldown_until_ms=int(cooldown_until_ms or 0),
        default=None,
        key=key,
    )
