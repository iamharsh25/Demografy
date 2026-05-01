"""
Demografy — app_v4.py
V4 landing with modal login and user dropdown.
Run via: streamlit run app.py
"""

import streamlit as st
import streamlit.components.v1 as components

from auth.rbac import (
    get_question_limit,
    get_user,
    is_limit_reached,
    should_show_warning,
)


st.set_page_config(
    page_title="Demografy v4",
    page_icon="🏘️",
    layout="wide",
    initial_sidebar_state="collapsed",
)


def init_session_state() -> None:
    for key, default in [
        ("user", None),
        ("question_count", 0),
        ("show_user_menu", False),
        ("chat_messages", []),
        ("chat_open", False),
    ]:
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

    user_id_input = st.text_input("User ID", placeholder="e.g. user_001", label_visibility="collapsed")
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
        f"**{user['user_id']}** &nbsp; <span class='badge-{tier}'>{tier.upper()} {tier_emoji}</span>",
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
        for key in ["user", "question_count", "show_user_menu", "chat_messages", "chat_open"]:
            st.session_state.pop(key, None)
        st.query_params.clear()
        st.rerun()


def add_chat_response(prompt: str) -> None:
    st.session_state.chat_messages.append({"role": "user", "content": prompt})
    # Placeholder assistant response until SQL agent is wired into v4.
    st.session_state.chat_messages.append(
        {
            "role": "assistant",
            "content": "Got it. Chat widget is ready — next we can connect this to the full SQL agent flow.",
        }
    )


def load_global_css() -> None:
    st.markdown(
        """
        <style>
            [data-testid="stToolbar"] { display: none !important; }
            [data-testid="stDecoration"] { display: none !important; }
            #MainMenu { visibility: hidden !important; }
            header { visibility: hidden !important; }
            .block-container { padding: 0 !important; max-width: 100% !important; }

            [data-testid="stHorizontalBlock"]:has(.nav-action-anchor) {
                min-height: 66px;
                width: 100%;
                display: flex !important;
                align-items: center !important;
                justify-content: space-between;
                padding: 12px 26px !important;
                box-sizing: border-box;
                border-bottom: 1px solid #dbdddc;
                background: #ffffff;
                margin: 0 !important;
                gap: 12px !important;
                overflow: visible !important;
            }
            .header-left {
                display: flex;
                align-items: center;
                gap: 30px;
                min-width: 0;
            }
            .logo {
                font-family: "Open Sauce One", "Inter", "Segoe UI", sans-serif;
                font-size: 2.15rem;
                font-weight: 800;
                letter-spacing: -0.04em;
                color: #272d2d;
                line-height: 1;
                white-space: nowrap;
            }
            .logo .accent { color: #9a66ee; }

            .menu {
                display: flex;
                align-items: center;
                gap: 22px;
                flex-wrap: nowrap;
            }
            .menu a {
                font-family: "Open Sauce One", "Inter", "Segoe UI", sans-serif;
                font-size: 0.78rem;
                font-weight: 500;
                color: #272d2d;
                text-decoration: none;
                transition: color 0.15s ease;
                white-space: nowrap;
                opacity: 0.9;
            }
            .menu a:hover { color: #5e17eb; opacity: 1; }

            [data-testid="stColumn"]:has(.nav-action-anchor) {
                position: relative;
                overflow: visible !important;
            }
            [data-testid="stColumn"]:has(.nav-action-anchor) [data-testid="stButton"] {
                width: 100% !important;
                display: flex !important;
                justify-content: flex-end !important;
            }
            [data-testid="stColumn"]:has(.nav-action-anchor) [data-testid="stButton"] > button {
                background: #ffffff !important;
                color: #272d2d !important;
                border: 1px solid #dbdddc !important;
                border-radius: 10px !important;
                font-family: "Open Sauce One", "Inter", "Segoe UI", sans-serif !important;
                font-size: 0.84rem !important;
                font-weight: 600 !important;
                height: 36px !important;
                padding: 0 18px !important;
                width: auto !important;
                min-width: 0 !important;
                transition: all 0.15s ease !important;
                box-shadow: none !important;
            }
            [data-testid="stColumn"]:has(.nav-action-anchor) [data-testid="stButton"] > button:hover {
                background: #f7f8f8 !important;
            }

            /* Keep dropdown out of layout flow: pure overlay, no page movement */
            [data-testid="stColumn"]:has(.nav-action-anchor) [data-testid="stVerticalBlock"]:has(.user-dropdown-anchor) {
                position: absolute;
                top: 44px;
                right: 0;
                width: 230px;
                background: rgba(255, 255, 255, 0.97);
                border: 1px solid #e6e8ec;
                border-radius: 14px;
                box-shadow: 0 20px 40px rgba(24, 24, 39, 0.14), 0 2px 10px rgba(24, 24, 39, 0.08);
                backdrop-filter: blur(10px);
                -webkit-backdrop-filter: blur(10px);
                padding: 8px;
                z-index: 1000;
                margin: 0 !important;
            }
            [data-testid="stColumn"]:has(.nav-action-anchor) [data-testid="stVerticalBlock"]:has(.user-dropdown-anchor) [data-testid="stButton"] {
                width: 100% !important;
                margin-bottom: 4px !important;
            }
            [data-testid="stColumn"]:has(.nav-action-anchor) [data-testid="stVerticalBlock"]:has(.user-dropdown-anchor) [data-testid="stButton"] > button {
                width: 100% !important;
                height: 40px !important;
                background: transparent !important;
                border: none !important;
                border-radius: 10px !important;
                text-align: left !important;
                justify-content: flex-start !important;
                padding: 0 12px !important;
                font-family: "Open Sauce One", "Inter", "Segoe UI", sans-serif !important;
                font-size: 0.86rem !important;
                font-weight: 550 !important;
                color: #272d2d !important;
                box-shadow: none !important;
                transition: background 0.15s ease, color 0.15s ease, transform 0.12s ease !important;
            }
            [data-testid="stColumn"]:has(.nav-action-anchor) [data-testid="stVerticalBlock"]:has(.user-dropdown-anchor) [data-testid="stButton"] > button:hover {
                background: #f4efff !important;
                color: #5e17eb !important;
                transform: translateX(1px);
            }
            [data-testid="stColumn"]:has(.nav-action-anchor) [data-testid="stVerticalBlock"]:has(.user-dropdown-anchor) [data-testid="stButton"]:last-child > button {
                color: #7f1d1d !important;
            }
            [data-testid="stColumn"]:has(.nav-action-anchor) [data-testid="stVerticalBlock"]:has(.user-dropdown-anchor) [data-testid="stButton"]:last-child > button:hover {
                background: #fff1f2 !important;
                color: #b91c1c !important;
            }

            .badge-pro { background: linear-gradient(90deg,#f7971e,#ffd200); color:#333; padding:2px 9px; border-radius:10px; font-size:0.68rem; font-weight:700; }
            .badge-basic { background: linear-gradient(90deg,#8b5cf6,#7c3aed); color:white; padding:2px 9px; border-radius:10px; font-size:0.68rem; font-weight:700; }
            .badge-free { background:#f3f4f6; color:#6b7280; padding:2px 9px; border-radius:10px; font-size:0.68rem; font-weight:700; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_header() -> None:
    c_logo, c_nav, c_actions = st.columns([1.2, 5, 2])

    with c_logo:
        st.markdown('<div class="logo"><span class="accent">D</span>emografy</div>', unsafe_allow_html=True)

    with c_nav:
        st.markdown(
            """
            <div class="menu">
                <a href="#">Home</a>
                <a href="#">Features</a>
                <a href="#">Testimonials</a>
                <a href="#">Use Case</a>
                <a href="#">Pricing</a>
                <a href="#">Career</a>
                <a href="#">Property Calculator</a>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with c_actions:
        st.markdown('<div class="nav-action-anchor"></div>', unsafe_allow_html=True)
        user = st.session_state.get("user")

        if user is None:
            if st.button("Login", key="nav_login"):
                show_login_modal()
        else:
            display_name = user.get("email", user["user_id"]).split("@")[0].title()
            if st.button(f"👤  {display_name} ▾", key="nav_profile"):
                st.session_state.show_user_menu = not st.session_state.get("show_user_menu", False)

            if st.session_state.get("show_user_menu"):
                st.markdown('<div class="user-dropdown-anchor"></div>', unsafe_allow_html=True)
                if st.button("👤  Account", key="menu_account", use_container_width=True):
                    st.session_state.show_user_menu = False
                    show_user_modal()
                if st.button("🚪  Sign Out", key="menu_signout", use_container_width=True):
                    for key in ["user", "question_count", "show_user_menu", "chat_messages", "chat_open"]:
                        st.session_state.pop(key, None)
                    st.query_params.clear()
                    st.rerun()


def render_body(show_chat_widget: bool) -> None:
    chat_widget = """
        <div id="chat-fab" class="chat-fab">💬</div>
        <div id="chat-widget" class="chat-widget">
            <div class="cw-header">
                <div class="cw-title"><span class="cw-avatar">🤖</span>HubBot</div>
                <button id="cw-close" class="cw-close" aria-label="Close chat">✕</button>
            </div>
            <div class="cw-body">
                <div class="cw-bubble">here to help you find your way.</div>
                <div class="cw-prompt">What would you like to do?</div>
                <button class="cw-quick">Learn about products</button>
                <button class="cw-quick">Learn about pricing</button>
                <button class="cw-quick">Get educational content</button>
            </div>
            <div class="cw-input-wrap">
                <input class="cw-input" placeholder="Choose an option" />
                <button class="cw-send">➤</button>
            </div>
        </div>
    """ if show_chat_widget else ""

    body_html = """
        <style>
            @import url("https://fonts.googleapis.com/css2?family=Open+Sauce+One:wght@400;500;600;700;800&display=swap");

            #MainMenu { visibility: hidden; }
            footer { visibility: hidden; }
            header { visibility: hidden; }

            .page {
                min-height: 100vh;
                width: 100%;
                background: #ffffff;
                display: flex;
                flex-direction: column;
            }

            .canvas {
                flex: 1;
                width: 100%;
                background: linear-gradient(180deg, #f6f6fa 0%, #f3efff 100%);
                display: flex;
                justify-content: center;
                padding: 56px 40px 80px;
                box-sizing: border-box;
            }

            .hero {
                width: 100%;
                max-width: 1180px;
                display: grid;
                grid-template-columns: minmax(0, 1fr) minmax(0, 1.08fr);
                gap: 44px;
                align-items: center;
            }

            .hero-left { max-width: 540px; }

            .badge {
                display: inline-flex;
                align-items: center;
                padding: 5px 14px;
                border-radius: 999px;
                border: 1px solid #d8c9f7;
                background: #f2eafe;
                color: #9a66ee;
                font-family: "Open Sauce One", "Inter", "Segoe UI", sans-serif;
                font-size: 0.62rem;
                font-weight: 700;
                letter-spacing: 0.14em;
                text-transform: uppercase;
                margin-bottom: 20px;
            }

            .hero-title {
                margin: 0;
                font-family: "Open Sauce One", "Inter", "Segoe UI", sans-serif;
                font-size: 3.9rem;
                line-height: 0.98;
                letter-spacing: -0.05em;
                color: #272d2d;
                font-weight: 700;
            }
            .hero-title .accent { color: #5e17eb; }

            .hero-desc {
                margin: 22px 0 0;
                font-family: "Open Sauce One", "Inter", "Segoe UI", sans-serif;
                font-size: 1.05rem;
                line-height: 1.75;
                color: #444a4a;
                max-width: 490px;
            }

            .hero-cta-row {
                margin-top: 30px;
                display: flex;
                gap: 12px;
                align-items: center;
            }

            .hero-btn {
                height: 44px;
                padding: 0 22px;
                border-radius: 10px;
                font-family: "Open Sauce One", "Inter", "Segoe UI", sans-serif;
                font-size: 0.84rem;
                font-weight: 600;
                text-decoration: none;
                display: inline-flex;
                align-items: center;
                justify-content: center;
                border: 1px solid transparent;
            }

            .hero-btn-secondary {
                background: #ffffff;
                color: #272d2d;
                border-color: #dbdddc;
            }

            .hero-btn-primary {
                color: #ffffff;
                background: linear-gradient(135deg, #9a66ee, #5e17eb);
                box-shadow: 0 8px 24px rgba(94, 23, 235, 0.28);
            }

            .hero-right {
                display: flex;
                justify-content: center;
            }

            .mockup-card {
                width: 100%;
                max-width: 650px;
                background: #ffffff;
                border: 1px solid #e8e8ec;
                border-radius: 18px;
                box-shadow: 0 20px 55px rgba(50, 41, 102, 0.14);
                overflow: hidden;
            }

            .mockup-head {
                height: 56px;
                display: flex;
                align-items: center;
                padding: 0 18px;
                border-bottom: 1px solid #f0f0f3;
                font-family: "Open Sauce One", "Inter", "Segoe UI", sans-serif;
                font-size: 2rem;
                font-weight: 800;
                color: #272d2d;
            }
            .mockup-head .accent { color: #9a66ee; }

            .mockup-content { padding: 14px 16px 18px; }

            .mockup-top {
                display: grid;
                grid-template-columns: 1.2fr 1fr 1fr;
                gap: 10px;
                margin-bottom: 12px;
            }

            .panel {
                border: 1px solid #ececf0;
                border-radius: 10px;
                padding: 10px;
                background: #fcfcfe;
            }

            .panel-title {
                font-family: "Open Sauce One", "Inter", "Segoe UI", sans-serif;
                font-size: 0.58rem;
                text-transform: uppercase;
                letter-spacing: 0.12em;
                color: #9b9fa7;
                margin-bottom: 7px;
                font-weight: 700;
            }

            .panel-value {
                font-family: "Open Sauce One", "Inter", "Segoe UI", sans-serif;
                font-size: 2rem;
                color: #272d2d;
                font-weight: 700;
                line-height: 1.1;
            }

            .filters-label {
                font-family: "Open Sauce One", "Inter", "Segoe UI", sans-serif;
                font-size: 0.58rem;
                color: #9b9fa7;
                text-transform: uppercase;
                letter-spacing: 0.12em;
                margin-bottom: 9px;
                font-weight: 700;
            }

            .fake-select {
                border: 1px solid #e6e6ea;
                background: #ffffff;
                border-radius: 8px;
                height: 30px;
                display: flex;
                align-items: center;
                justify-content: space-between;
                padding: 0 9px;
                box-sizing: border-box;
                font-family: "Open Sauce One", "Inter", "Segoe UI", sans-serif;
                font-size: 0.68rem;
                color: #3f4444;
                margin-bottom: 6px;
            }

            .table {
                border: 1px solid #ececf0;
                border-radius: 10px;
                overflow: hidden;
            }

            .table-head, .table-row {
                display: grid;
                grid-template-columns: 66px 1fr 100px;
                align-items: center;
                gap: 8px;
                padding: 9px 12px;
            }

            .table-head {
                background: #fafafe;
                border-bottom: 1px solid #eeeeF3;
                font-family: "Open Sauce One", "Inter", "Segoe UI", sans-serif;
                font-size: 0.62rem;
                text-transform: uppercase;
                letter-spacing: 0.08em;
                color: #9b9fa7;
                font-weight: 700;
            }

            .table-row { border-bottom: 1px solid #f3f3f6; }

            .rank-pill {
                width: 34px;
                height: 22px;
                border-radius: 8px;
                display: flex;
                align-items: center;
                justify-content: center;
                font-family: "Open Sauce One", "Inter", "Segoe UI", sans-serif;
                font-size: 0.62rem;
                font-weight: 700;
                color: #ffffff;
                background: #f6b70e;
            }

            .area-name {
                font-family: "Open Sauce One", "Inter", "Segoe UI", sans-serif;
                font-size: 0.76rem;
                color: #272d2d;
                font-weight: 600;
            }

            .area-sub {
                font-family: "Open Sauce One", "Inter", "Segoe UI", sans-serif;
                font-size: 0.62rem;
                color: #9b9fa7;
                margin-top: 2px;
            }

            .population {
                font-family: "Open Sauce One", "Inter", "Segoe UI", sans-serif;
                font-size: 0.74rem;
                font-weight: 600;
                color: #3f4444;
                text-align: right;
            }

            @media (max-width: 1100px) {
                .hero { grid-template-columns: 1fr; gap: 30px; }
                .hero-left { max-width: 100%; }
                .hero-title { font-size: 3rem; }
            }
            @media (max-width: 760px) {
                .canvas { padding: 28px 16px 40px; }
                .hero-title { font-size: 2.4rem; }
                .hero-desc { font-size: 0.95rem; }
                .hero-cta-row { flex-wrap: wrap; }
                .mockup-top { grid-template-columns: 1fr; }
            }

            @keyframes cwIn {
                0% { opacity: 0; transform: translateY(14px) scale(0.98); }
                100% { opacity: 1; transform: translateY(0) scale(1); }
            }
            .chat-fab {
                position: fixed;
                right: 24px;
                bottom: 22px;
                width: 60px;
                height: 60px;
                border-radius: 999px;
                background: linear-gradient(135deg, #9a66ee, #5e17eb);
                color: #fff;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 1.45rem;
                cursor: pointer;
                box-shadow: 0 14px 30px rgba(94, 23, 235, 0.34), 0 4px 12px rgba(94, 23, 235, 0.24);
                z-index: 2200;
                transition: transform 0.15s ease, box-shadow 0.15s ease;
            }
            .chat-fab:hover {
                transform: translateY(-1px) scale(1.03);
                box-shadow: 0 18px 34px rgba(94, 23, 235, 0.4), 0 6px 16px rgba(94, 23, 235, 0.28);
            }
            .chat-widget {
                display: none;
                position: fixed;
                right: 22px;
                bottom: 94px;
                width: 360px;
                max-width: calc(100vw - 24px);
                background: #fff;
                border: 1px solid #e8e8ef;
                border-radius: 16px;
                overflow: hidden;
                box-shadow: 0 24px 48px rgba(24, 24, 39, 0.16), 0 6px 14px rgba(24, 24, 39, 0.08);
                z-index: 2195;
            }
            .chat-widget.open {
                display: block;
                animation: cwIn 0.2s ease-out;
            }
            .cw-header {
                height: 56px;
                padding: 0 14px;
                background: linear-gradient(135deg, #5f7490 0%, #4a607d 100%);
                color: #fff;
                display: flex;
                align-items: center;
                justify-content: space-between;
            }
            .cw-title { display: inline-flex; align-items: center; gap: 8px; font-weight: 700; font-size: 1rem; }
            .cw-avatar {
                width: 26px; height: 26px; border-radius: 50%;
                background: rgba(255,255,255,0.22);
                display: inline-flex; align-items: center; justify-content: center;
                font-size: 0.92rem;
            }
            .cw-close {
                border: none; background: transparent; color: #fff; font-size: 1rem; cursor: pointer;
                width: 28px; height: 28px; border-radius: 8px;
            }
            .cw-close:hover { background: rgba(255,255,255,0.15); }
            .cw-body { padding: 12px 14px 10px; }
            .cw-bubble {
                background: #e8edf4;
                color: #607287;
                border-radius: 10px;
                padding: 9px 11px;
                font-size: 0.9rem;
                font-weight: 600;
                margin-bottom: 10px;
            }
            .cw-prompt {
                background: #eef2f8;
                color: #596b81;
                border-radius: 10px;
                padding: 8px 11px;
                font-size: 0.92rem;
                font-weight: 700;
                margin-bottom: 10px;
            }
            .cw-quick {
                display: block;
                width: fit-content;
                min-width: 165px;
                margin-bottom: 8px;
                border: 1px solid #b7c2d0;
                background: #fff;
                color: #5a6f86;
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 0.88rem;
                font-weight: 600;
                cursor: pointer;
                text-align: left;
            }
            .cw-quick:hover { border-color: #9a66ee; color: #5e17eb; background: #f8f6ff; }
            .cw-input-wrap {
                border-top: 1px solid #edf1f6;
                padding: 10px 12px;
                display: flex;
                gap: 8px;
                align-items: center;
                background: #fff;
            }
            .cw-input {
                flex: 1;
                border: 1px solid #e2e8f1;
                background: #f6f8fb;
                border-radius: 8px;
                height: 38px;
                padding: 0 10px;
                font-size: 0.9rem;
                outline: none;
            }
            .cw-send {
                border: none;
                background: transparent;
                color: #a7b1bf;
                font-size: 1rem;
                cursor: pointer;
                width: 30px;
                height: 30px;
                border-radius: 8px;
            }
            .cw-send:hover { background: #f3f5f8; color: #5e17eb; }
        </style>

        <div class="page">
            <div class="canvas">
                <section class="hero">
                    <div class="hero-left">
                        <div class="badge">Coming in Beta</div>
                        <h1 class="hero-title">
                            <span class="accent">Australian</span><br>
                            <span class="accent">property insights,</span><br>
                            propelled by data.
                        </h1>
                        <p class="hero-desc">
                            Ditch the guesswork. Our platform gives investors, homebuyers,
                            and pros the hard numbers on suburb growth, so you can make
                            your move with confidence, not just a hunch.
                        </p>
                        <div class="hero-cta-row">
                            <a class="hero-btn hero-btn-secondary" href="#">Discover more</a>
                            <a class="hero-btn hero-btn-primary" href="#">Get early access -></a>
                        </div>
                    </div>

                    <div class="hero-right">
                        <div class="mockup-card">
                            <div class="mockup-head"><span class="accent">D</span>emografy</div>
                            <div class="mockup-content">
                                <div class="mockup-top">
                                    <div class="panel">
                                        <div class="filters-label">Filters</div>
                                        <div class="fake-select"><span>State</span><span>NSW</span></div>
                                        <div class="fake-select"><span>Local Govt Area</span><span>All LGAs</span></div>
                                        <div class="fake-select"><span>Region Type</span><span>All regions</span></div>
                                    </div>
                                    <div class="panel">
                                        <div class="panel-title">Total Areas</div>
                                        <div class="panel-value">644</div>
                                    </div>
                                    <div class="panel">
                                        <div class="panel-title">Active KPIs</div>
                                        <div class="panel-value">3</div>
                                    </div>
                                </div>

                                <div class="table">
                                    <div class="table-head">
                                        <div>Rank</div>
                                        <div>SA2</div>
                                        <div style="text-align:right;">Population</div>
                                    </div>
                                    <div class="table-row">
                                        <div><div class="rank-pill">#1</div></div>
                                        <div>
                                            <div class="area-name">Corowa</div>
                                            <div class="area-sub">NSW · Major Cities</div>
                                        </div>
                                        <div class="population">7,005</div>
                                    </div>
                                    <div class="table-row">
                                        <div><div class="rank-pill">#2</div></div>
                                        <div>
                                            <div class="area-name">Rosemeadow - Glen Alpine</div>
                                            <div class="area-sub">NSW · Major Cities</div>
                                        </div>
                                        <div class="population">25,636</div>
                                    </div>
                                    <div class="table-row">
                                        <div><div class="rank-pill">#3</div></div>
                                        <div>
                                            <div class="area-name">Leppington - Catherine Field</div>
                                            <div class="area-sub">NSW · Major Cities</div>
                                        </div>
                                        <div class="population">3,231</div>
                                    </div>
                                    <div class="table-row">
                                        <div><div class="rank-pill">#4</div></div>
                                        <div>
                                            <div class="area-name">Randwick - North</div>
                                            <div class="area-sub">NSW · Major Cities</div>
                                        </div>
                                        <div class="population">63,875</div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </section>
            </div>
        </div>
        __CHAT_WIDGET__
        <script>
            (function () {
                const fab = document.getElementById("chat-fab");
                const widget = document.getElementById("chat-widget");
                const closeBtn = document.getElementById("cw-close");
                if (!fab || !widget) return;
                fab.addEventListener("click", () => widget.classList.toggle("open"));
                if (closeBtn) closeBtn.addEventListener("click", () => widget.classList.remove("open"));
            })();
        </script>
        """.replace("__CHAT_WIDGET__", chat_widget)
    components.html(
        body_html,
        height=860,
        scrolling=False,
    )


init_session_state()
load_global_css()
render_header()
render_body(show_chat_widget=st.session_state.get("user") is not None)
