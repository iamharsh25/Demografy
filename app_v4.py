"""
Demografy — app_v4.py
Thin orchestrator: configure the page, run chat lifecycle, then render UI.
Run via: streamlit run app.py
"""

import streamlit as st

from auth.rbac import is_limit_reached
from components.body import render_body
from components.chat_bridge import render_bridge
from components.chat_engine import maybe_consume_bridge, resolve_pending_question
from components.chatbox import render_chatbox
from components.header import render_header
from components.state import init_session_state
from components.styles import load_global_css


st.set_page_config(
    page_title="Demografy v4",
    page_icon="🏘️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

init_session_state()
load_global_css()
render_header()

user = st.session_state.get("user")
chat_visible = user is not None

if chat_visible:
    # Phase 1: forward any new bridge value into the chat engine.
    maybe_consume_bridge(render_bridge())

    tier = (user or {}).get("tier", "free")
    question_count = int(st.session_state.get("question_count", 0))
    limit_reached = is_limit_reached(tier, question_count)
else:
    limit_reached = False

render_body(
    show_chat_widget=chat_visible,
    messages=st.session_state.get("chat_messages", []),
    pending=bool(st.session_state.get("chat_pending")),
    limit_reached=limit_reached,
)
render_chatbox()

if chat_visible:
    # Phase 2 runs after render so the user can see immediate pending UI.
    resolve_pending_question()
