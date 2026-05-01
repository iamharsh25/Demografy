"""Session state initialisation and URL-based user restore.

Centralised so every component reads from a single, predictable shape.
On user restore (either via ``?u=`` URL parameter or a fresh login) we
also hydrate ``chat_messages`` from the on-disk transcript so the chat
widget renders the prior conversation immediately.
"""

import streamlit as st

from auth.rbac import get_user
from chat_history.storage import load_history


SESSION_DEFAULTS = [
    ("user", None),
    ("question_count", 0),
    ("show_user_menu", False),
    ("chat_messages", []),
    ("chat_open", False),
    ("chat_pending", False),
    ("chat_pending_question", None),
    ("chat_last_ts", None),
]


def hydrate_chat_history(user_id: str) -> None:
    """Populate ``st.session_state.chat_messages`` from disk for ``user_id``.

    No-op if the in-memory thread already has messages, so we don't
    clobber the live conversation if this is called mid-session.
    """
    if st.session_state.get("chat_messages"):
        return
    try:
        records = load_history(user_id)
    except Exception:
        records = []
    st.session_state.chat_messages = [
        {"role": r["role"], "content": r["content"]}
        for r in records
        if r.get("role") in ("user", "assistant") and isinstance(r.get("content"), str)
    ]


def init_session_state() -> None:
    for key, default in SESSION_DEFAULTS:
        if key not in st.session_state:
            st.session_state[key] = default

    if st.session_state.user is None:
        uid = st.query_params.get("u")
        if uid:
            try:
                user = get_user(uid)
                if user:
                    st.session_state.user = user
                    hydrate_chat_history(user["user_id"])
                else:
                    st.query_params.clear()
            except Exception:
                st.query_params.clear()
