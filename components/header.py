"""Top header: 3-column layout composing Logo + Menu + UserProfile.

Layout responsibility lives here; visuals come from `components/styles.py`.
The `nav-action-anchor` placement is delegated to `render_user_profile()`
since it must be the first child of the actions column.
"""

import streamlit as st

from components.logo import render_logo
from components.menu import render_menu
from components.user_profile import render_user_profile


def render_header() -> None:
    c_logo, c_nav, c_actions = st.columns([1.2, 5, 2])

    with c_logo:
        render_logo()

    with c_nav:
        render_menu()

    with c_actions:
        render_user_profile()
