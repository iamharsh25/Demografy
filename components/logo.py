"""Pure-render logo block. CSS lives in `components/styles.py`."""

import streamlit as st


def render_logo() -> None:
    st.markdown(
        '<div class="logo"><span class="accent">D</span>emografy</div>',
        unsafe_allow_html=True,
    )
