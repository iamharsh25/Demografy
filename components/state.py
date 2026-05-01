"""Session state initialisation and URL-based user restore.

Centralised so every component reads from a single, predictable shape.
"""

import streamlit as st

from auth.rbac import get_user


SESSION_DEFAULTS = [
    ("user", None),
    ("question_count", 0),
    ("show_user_menu", False),
    ("chat_messages", []),
    ("chat_open", False),
    ("chat_pending", False),
    ("chat_pending_armed", False),
    ("chat_pending_question", None),
    ("chat_last_ts", None),
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
                else:
                    st.query_params.clear()
            except Exception:
                st.query_params.clear()
