"""
Demografy - app_v4.py

Thin orchestrator: configure the page, render header + body, then run the
chat lifecycle inside a fragment so the agent call doesn't fade the rest
of the page.

Run via: ``streamlit run app.py``.
"""

import streamlit as st

from auth.rbac import is_limit_reached
from chat_history.thread_list import list_threads
from components.body import render_body
from components.chat_engine import maybe_consume_bridge, resolve_pending_question
from components.chat_widget import CHAT_WIDGET_KEY, render_chat_widget
from components.header import render_header
from components.state import init_session_state
from components.styles import load_global_css


st.set_page_config(
    page_title="Demografy v4",
    page_icon="\U0001f3d8\ufe0f",
    layout="wide",
    initial_sidebar_state="collapsed",
)

init_session_state()
load_global_css()
render_header()
render_body()


@st.fragment
def _chat_panel() -> None:
    """Chat lifecycle, scoped to a fragment.

    Reruns triggered from inside the fragment (when the user submits a
    question or when ``ask()`` finishes) stay fragment-scoped, so Streamlit
    only shows a small running indicator near the chat widget instead of
    the full-page fade overlay.

    The order matters: we read the latest component value from session
    state, advance the engine state machine (which may call ``ask()``),
    and only THEN render the chat widget so the iframe receives the
    freshest ``messages`` / ``pending`` values in a single push - never
    a stale empty thread followed by the real one.
    """
    # 1. Pick up any submission JS made on the previous render.
    payload = st.session_state.get(CHAT_WIDGET_KEY)
    maybe_consume_bridge(payload)

    # 2. If a question is pending, run the agent. Blocks the fragment, but
    #    not the page; the rest of the UI stays interactive and unfaded.
    resolve_pending_question()

    # 3. Render with the post-update state. Streamlit reuses the same iframe
    #    across reruns; the JS reconciles the DOM in place (no flicker).
    user = st.session_state.get("user") or {}
    tier = user.get("tier", "free")
    question_count = int(st.session_state.get("question_count", 0))

    # Past-chats list for the View overlay. Cheap directory scan; refreshes
    # on every fragment render so a thread persisted moments ago appears
    # without a manual reload.
    threads: list = []
    user_id = user.get("user_id")
    if user_id:
        try:
            threads = list_threads(user_id)
        except Exception:
            threads = []

    render_chat_widget(
        messages=st.session_state.get("chat_messages", []),
        pending=bool(st.session_state.get("chat_pending")),
        limit_reached=is_limit_reached(tier, question_count),
        threads=threads,
        active_thread_id=st.session_state.get("chat_thread_id"),
    )


if st.session_state.get("user"):
    _chat_panel()
