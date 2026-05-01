"""
Demografy — app_v4.py
Thin orchestrator: configure the page, then call into `components/`.
Run via: streamlit run app.py
"""

import streamlit as st

from components.body import render_body
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
render_body(show_chat_widget=st.session_state.get("user") is not None)
render_chatbox()
