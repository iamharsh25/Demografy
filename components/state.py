"""Session state initialisation and URL-based user restore.

Centralised so every component reads from a single, predictable shape.
On user restore (either via ``?u=`` URL parameter or a fresh login) we
also hydrate the active chat thread from disk so the chat widget
renders the prior conversation immediately.

Threading model
---------------
``chat_thread_id`` identifies which conversation the chat widget is
currently showing and writing to. ``hydrate_chat_history`` resolves it
to the most recently active thread (if any) so users return to where
they left off; otherwise it mints a fresh id without materialising a
file - the file appears on the first ``append_message`` call.
"""

import streamlit as st

from auth.rbac import get_user
from chat_history.storage import load_history, new_thread_id
from chat_history.thread_list import list_threads


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
]


def hydrate_chat_history(user_id: str) -> None:
    """Restore the most recent thread for ``user_id`` into session state.

    Decision tree:
      1. If ``chat_messages`` already has content, do nothing - we don't
         clobber a live in-memory conversation.
      2. Otherwise look up ``list_threads`` newest-first.
         - Thread present: set ``chat_thread_id`` to its id, populate
           ``chat_messages`` from disk.
         - No threads: mint a fresh ``chat_thread_id`` so the engine
           always has a target to write to. No file is created until a
           message is actually persisted.
    """
    if st.session_state.get("chat_messages"):
        # Already populated; just ensure we have a thread id to write to.
        if not st.session_state.get("chat_thread_id"):
            st.session_state.chat_thread_id = new_thread_id()
        return

    try:
        threads = list_threads(user_id)
    except Exception:
        threads = []

    if threads:
        thread_id = threads[0]["thread_id"]
        try:
            records = load_history(user_id, thread_id)
        except Exception:
            records = []
        st.session_state.chat_thread_id = thread_id
        st.session_state.chat_messages = [
            {
                "role": r["role"],
                "content": r["content"],
                **(
                    {"image_b64": r["image_b64"]}
                    if r.get("image_b64") and isinstance(r.get("image_b64"), str)
                    else {}
                ),
            }
            for r in records
            if r.get("role") in ("user", "assistant") and isinstance(r.get("content"), str)
        ]
    else:
        st.session_state.chat_thread_id = new_thread_id()
        st.session_state.chat_messages = []

    # Suggestions are ephemeral; never restore stale chips from a prior
    # session. They only appear after a fresh answer this session.
    st.session_state.chat_suggestions = []
    st.session_state.chat_last_query = None


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
