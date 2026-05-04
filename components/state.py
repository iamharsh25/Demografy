"""Session state initialisation and URL-based user restore.

Centralised so every component reads from a single, predictable shape.
On user restore (either via ``?u=`` URL parameter or a fresh login) we
prepare chat state with an **empty** conversation and a new thread id.
Older transcripts stay on disk and remain available from the chat
history overlay (``open_thread``); the main panel does not auto-load the
last thread.

Threading model
---------------
``chat_thread_id`` identifies which conversation the chat widget is
currently showing and writing to. ``hydrate_chat_history`` always mints
a fresh id for the signed-in user; the JSONL file is created on the first
``append_message`` call.
"""

import streamlit as st

from auth.cooldown import get_cooldown_until
from auth.rbac import get_user
from chat_history.storage import new_thread_id


SESSION_DEFAULTS = [
    ("user", None),
    ("question_count", 0),
    ("show_user_menu", False),
    ("chat_messages", []),
    ("chat_open", False),
    ("chat_pending", False),
    ("chat_pending_question", None),
    ("chat_last_ts", None),
    ("chat_thread_id", None),
    ("chat_suggestions", []),
    ("chat_last_query", None),
    ("chat_last_chartable_meta", None),
    ("chat_context_query", None),
    ("chat_cooldown_until", None),
]


def hydrate_chat_history(user_id: str) -> None:
    """Bind ``user_id`` to a fresh in-memory thread (no disk restore).

    Callers: URL ``?u=`` restore and post-login. Past conversations are
    unchanged on disk; users open them explicitly via the history overlay.
    """
    st.session_state.chat_thread_id = new_thread_id()
    st.session_state.chat_messages = []
    st.session_state.chat_pending = False
    st.session_state.chat_pending_question = None
    st.session_state.pop("chat_pending_label", None)
    st.session_state.chat_suggestions = []
    st.session_state.chat_last_query = None
    st.session_state.chat_last_chartable_meta = None
    st.session_state.chat_context_query = None

    # Restore any active cooldown so a hard refresh keeps the timer
    # ticking. ``chat_engine`` expires it on the next interaction if the
    # timestamp is already in the past.
    try:
        st.session_state.chat_cooldown_until = get_cooldown_until(user_id)
    except Exception:
        st.session_state.chat_cooldown_until = None


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
