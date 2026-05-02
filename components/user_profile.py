"""User profile column: Login button, profile pill, dropdown, dialogs.

Owns:
  - `show_login_modal`  (`@st.dialog`)
  - `show_user_modal`   (`@st.dialog`)
  - `render_user_profile()` — renders Login button OR profile pill + dropdown

CSS for the dropdown / pill lives in `components/styles.py`. Anchor divs
(`nav-action-anchor`, `user-dropdown-anchor`) must remain at the exact
positions used here — `:has()` selectors depend on them.
"""

import streamlit as st

from auth.rbac import (
    get_question_limit,
    get_user,
    is_limit_reached,
    should_show_warning,
)
from components.state import hydrate_chat_history


@st.dialog("Sign In")
def show_login_modal() -> None:
    st.markdown(
        """
        <div style="text-align:center; margin-bottom:20px;">
            <div style="font-size:1.8rem; font-weight:900; letter-spacing:-1px; color:#272d2d;">
                <span style="color:#9a66ee;">D</span>emografy
            </div>
            <div style="color:#9ca3af; font-size:0.85rem; margin-top:6px;">
                Enter your User ID to continue
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    user_id_input = st.text_input(
        "User ID",
        placeholder="e.g. user_001",
        label_visibility="collapsed",
    )
    if st.button("Sign In", use_container_width=True, type="primary"):
        if not user_id_input.strip():
            st.error("Please enter a User ID.")
            return

        with st.spinner("Checking credentials..."):
            try:
                user = get_user(user_id_input.strip())
            except Exception as exc:
                st.error(f"Could not connect. Error: {exc}")
                return

            if user is None:
                st.error("User not found or account is inactive.")
                return

            st.session_state.user = user
            st.session_state.question_count = 0
            st.session_state.show_user_menu = False
            st.session_state.chat_messages = []
            st.session_state.chat_thread_id = None
            st.session_state.chat_pending = False
            st.session_state.chat_pending_question = None
            st.session_state.chat_last_ts = None
            hydrate_chat_history(user["user_id"])
            st.query_params["u"] = user["user_id"]
            st.rerun()


@st.dialog("My Account")
def show_user_modal() -> None:
    user = st.session_state.get("user")
    if not user:
        return

    tier = user.get("tier", "free")
    limit = get_question_limit(tier)
    question_count = st.session_state.get("question_count", 0)
    remaining = max(limit - question_count, 0)
    pct = min(question_count / max(limit, 1), 1.0)
    tier_emoji = {"pro": "🥇", "basic": "🥈", "free": "🥉"}.get(tier, "")

    st.markdown(
        f"**{user['user_id']}** &nbsp; "
        f"<span class='badge-{tier}'>{tier.upper()} {tier_emoji}</span>",
        unsafe_allow_html=True,
    )
    st.caption(user.get("email", ""))
    st.divider()

    c1, c2 = st.columns(2)
    c1.metric("Questions Used", question_count)
    c2.metric("Remaining", remaining)
    st.progress(pct, text=f"{question_count} / {limit} questions this session")

    if is_limit_reached(tier, question_count):
        st.error("Question limit reached for this session.")
    elif should_show_warning(tier, question_count):
        st.warning(f"⚠️ Only {remaining} question{'s' if remaining != 1 else ''} left.")
    else:
        st.success(f"✅ {remaining} questions remaining.")

    st.divider()
    if st.button("🚪  Sign Out", type="primary", use_container_width=True):
        _sign_out()


def _sign_out() -> None:
    for key in [
        "user",
        "question_count",
        "show_user_menu",
        "chat_messages",
        "chat_open",
        "chat_thread_id",
        "chat_pending",
        "chat_pending_question",
        "chat_last_ts",
    ]:
        st.session_state.pop(key, None)
    st.query_params.clear()
    st.rerun()


def render_user_profile() -> None:
    """Render the right-hand action area: Login button OR user pill + dropdown.

    Caller is responsible for placing this inside the actions column. The
    `nav-action-anchor` div MUST be the first child of that column so the
    `:has()` selectors in `components/styles.py` match correctly.
    """
    st.markdown('<div class="nav-action-anchor"></div>', unsafe_allow_html=True)
    user = st.session_state.get("user")

    if user is None:
        if st.button("Login", key="nav_login"):
            show_login_modal()
        return

    display_name = user.get("email", user["user_id"]).split("@")[0].title()
    if st.button(f"👤  {display_name} ▾", key="nav_profile"):
        st.session_state.show_user_menu = not st.session_state.get("show_user_menu", False)

    if st.session_state.get("show_user_menu"):
        st.markdown('<div class="user-dropdown-anchor"></div>', unsafe_allow_html=True)
        if st.button("👤  Account", key="menu_account", use_container_width=True):
            st.session_state.show_user_menu = False
            show_user_modal()
        if st.button("🚪  Sign Out", key="menu_signout", use_container_width=True):
            _sign_out()
