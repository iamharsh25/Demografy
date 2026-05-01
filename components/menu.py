"""Pure-render top nav menu. CSS lives in `components/styles.py`."""

import streamlit as st


_MENU_ITEMS = [
    ("Home", "#"),
    ("Features", "#"),
    ("Testimonials", "#"),
    ("Use Case", "#"),
    ("Pricing", "#"),
    ("Career", "#"),
    ("Property Calculator", "#"),
]


def render_menu() -> None:
    links = "\n        ".join(
        f'<a href="{href}">{label}</a>' for label, href in _MENU_ITEMS
    )
    st.markdown(
        f"""
        <div class="menu">
        {links}
        </div>
        """,
        unsafe_allow_html=True,
    )
