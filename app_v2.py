"""
Demografy V2 — default landing scaffold.
Run directly with: streamlit run app_v2.py
"""

import streamlit as st


def _init_v2_state() -> None:
    for key, default in [
        ("v2_show_login_modal", False),
        ("v2_user", None),
    ]:
        if key not in st.session_state:
            st.session_state[key] = default


@st.dialog("Login")
def _render_login_modal() -> None:
    st.caption("Enter your User ID to continue")
    user_id_input = st.text_input(
        "User ID",
        placeholder="e.g. user_001",
        label_visibility="collapsed",
        key="v2_user_id_input",
    )

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Cancel", use_container_width=True, key="v2_login_cancel"):
            st.session_state.v2_show_login_modal = False
            st.rerun()
    with col2:
        if st.button("Sign In", use_container_width=True, type="primary", key="v2_login_submit"):
            if not user_id_input.strip():
                st.error("Please enter a User ID.")
                return

            with st.spinner("Checking credentials..."):
                try:
                    from auth.rbac import get_user

                    user = get_user(user_id_input.strip())
                    if user is None:
                        st.error("User not found or account is inactive. Please check your User ID.")
                        return

                    st.session_state.v2_user = user
                    st.session_state.v2_show_login_modal = False
                    st.rerun()
                except Exception as exc:
                    st.error(f"Could not connect to user database. Error: {str(exc)}")


def _load_v2_css() -> None:
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Open+Sans:wght@400;600;700;800;900&display=swap');

        html, body, .stApp, [class*="css"] { font-family: 'Open Sans', sans-serif; }
        #MainMenu { visibility: hidden; }
        footer { visibility: hidden; }
        header { visibility: hidden; }

        .block-container {
            padding-top: 0 !important;
            padding-bottom: 0 !important;
            padding-left: 0 !important;
            padding-right: 0 !important;
            max-width: 100% !important;
        }

        [data-testid="stVerticalBlock"]:has(.v2-root-marker) {
            min-height: auto;
            background: linear-gradient(135deg, #ffffff 0%, #f5f0ff 55%, #ede8ff 100%);
            padding: 10px 18px 14px;
        }
        [data-testid="stVerticalBlock"]:has(.v2-root-marker) > .v2-root-marker {
            display: none;
        }
        [data-testid="stVerticalBlock"]:has(.v2-header-marker) {
            border-bottom: 1px solid #efe8ff;
            padding-bottom: 8px;
            margin-bottom: 2px;
        }
        [data-testid="stVerticalBlock"]:has(.v2-header-marker) > .v2-header-marker {
            display: none;
        }
        [data-testid="stVerticalBlock"]:has(.v2-hero-marker) > .v2-hero-marker {
            display: none;
        }
        [data-testid="stVerticalBlock"]:has(.v2-hero-marker) {
            margin-top: 0 !important;
            padding-top: 2px !important;
        }
        [data-testid="stVerticalBlock"]:has(.v2-auth-marker) > .v2-auth-marker {
            display: none;
        }
        .v2-left {
            display: flex;
            align-items: center;
            gap: 16px;
            min-width: 0;
        }
        .v2-logo {
            font-size: 1.35rem;
            font-weight: 900;
            color: #1a1a2e;
            letter-spacing: -0.5px;
            white-space: nowrap;
        }
        .v2-logo span { color: #5e17eb; }
        .v2-menu {
            display: flex;
            align-items: center;
            gap: 16px;
            font-size: 0.88rem;
            font-weight: 600;
            color: #4b4b5a;
            white-space: nowrap;
            overflow-x: auto;
        }
        .v2-menu span {
            white-space: nowrap;
        }
        [data-testid="stVerticalBlock"]:has(.v2-auth-marker) [data-testid="stButton"] button {
            background: #fff !important;
            border: 1.5px solid #ddd !important;
            color: #1a1a2e !important;
            border-radius: 8px !important;
            font-size: 0.84rem !important;
            font-weight: 600 !important;
            height: 36px !important;
            padding: 0 10px !important;
            min-width: 86px !important;
        }
        [data-testid="stVerticalBlock"]:has(.v2-auth-marker) [data-testid="stButton"] {
            display: flex;
            justify-content: flex-end;
        }
        .v2-user-pill {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            border: 1px solid #ddd;
            border-radius: 999px;
            color: #34344a;
            font-size: 0.8rem;
            font-weight: 600;
            padding: 5px 10px;
            white-space: nowrap;
            margin-right: 8px;
        }
        .v2-hero-wrap {
            margin-top: 0;
            max-width: 640px;
        }
        .v2-tag {
            display: inline-block;
            font-size: 0.66rem;
            font-weight: 700;
            color: #5e17eb;
            letter-spacing: 1px;
            text-transform: uppercase;
            border: 1.5px solid #c9a5ff;
            border-radius: 20px;
            padding: 3px 12px;
            margin-bottom: 16px;
            background: rgba(94,23,235,0.04);
        }
        .v2-h1 {
            font-size: clamp(2.1rem, 3.6vw, 3.2rem);
            line-height: 1.13;
            font-weight: 800;
            margin: 0 0 10px;
            color: #1a1a2e;
            letter-spacing: -0.7px;
        }
        .v2-h1 b { color: #5e17eb; }
        .v2-sub {
            max-width: 58ch;
            color: #666;
            line-height: 1.62;
            font-size: 0.96rem;
        }
        .v2-actions {
            margin-top: 12px;
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
        }
        .v2-btn {
            height: 42px;
            border-radius: 10px;
            padding: 0 18px;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            text-decoration: none;
            font-size: 0.88rem;
            font-weight: 600;
        }
        .v2-btn.secondary {
            background: #fff;
            color: #1a1a2e;
            border: 1.5px solid #ddd;
        }
        .v2-btn.primary {
            background: linear-gradient(135deg, #5e17eb, #9a66ee);
            color: #fff;
            border: none;
        }
        .v2-card {
            background: #fff;
            border-radius: 18px;
            box-shadow: 0 12px 48px rgba(94,23,235,0.15);
            padding: 16px 16px;
            font-size: 0.75rem;
            max-width: 500px;
            margin-left: auto;
        }
        .v2-card-title {
            font-size: 1rem;
            font-weight: 900;
            color: #1a1a2e;
            margin-bottom: 8px;
        }
        .v2-card-title span { color: #5e17eb; }

        @media (max-width: 1200px) {
            [data-testid="stVerticalBlock"]:has(.v2-root-marker) {
                padding: 12px 14px 18px;
            }
            .v2-menu { gap: 12px; font-size: 0.8rem; }
            .v2-left { gap: 12px; }
            .v2-h1 { font-size: clamp(1.8rem, 3.5vw, 2.6rem); }
        }

        @media (max-width: 768px) {
            [data-testid="stVerticalBlock"]:has(.v2-root-marker) {
                min-height: auto;
                padding: 10px 12px 20px;
            }
            .v2-menu { gap: 10px; font-size: 0.76rem; }
            .v2-menu span:nth-child(n+6) { display: none; }
            .v2-user-pill { margin-right: 4px; }
            .v2-hero-wrap { margin-top: 0; }
            .v2-h1 {
                font-size: clamp(1.7rem, 8vw, 2.2rem);
                line-height: 1.15;
            }
            .v2-sub { font-size: 0.9rem; line-height: 1.55; }
            .v2-actions { gap: 8px; }
            .v2-btn { width: 100%; height: 40px; }
            .v2-card {
                margin-left: 0;
                margin-top: 8px;
                max-width: 100%;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def run_app() -> None:
    _init_v2_state()
    st.set_page_config(
        page_title="Demografy V2",
        page_icon="🏘️",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    _load_v2_css()
    if st.session_state.get("v2_show_login_modal"):
        _render_login_modal()

    user = st.session_state.get("v2_user")

    st.markdown('<div class="v2-root-marker"></div>', unsafe_allow_html=True)
    st.markdown('<div class="v2-header-marker"></div>', unsafe_allow_html=True)
    left_col, right_col = st.columns([8, 2], vertical_alignment="center")
    with left_col:
        st.markdown(
            """
            <div class="v2-left">
              <div class="v2-logo"><span>D</span>emografy</div>
              <div class="v2-menu">
                <span>Home</span><span>Features</span><span>Testimonials</span>
                <span>Use Case</span><span>Pricing</span><span>Career</span>
                <span>Property Calculator</span>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with right_col:
        st.markdown('<div class="v2-auth-marker"></div>', unsafe_allow_html=True)
        if user is None:
            if st.button("Login", key="v2_login_btn"):
                st.session_state.v2_show_login_modal = True
                st.rerun()
        else:
            st.markdown(
                f'<span class="v2-user-pill">{user.get("user_id", "Signed in")}</span>',
                unsafe_allow_html=True,
            )
            if st.button("Sign Out", key="v2_signout_btn"):
                st.session_state.v2_user = None
                st.session_state.v2_show_login_modal = False
                st.rerun()

    st.markdown('<div class="v2-hero-marker"></div>', unsafe_allow_html=True)
    hero_left, hero_right = st.columns([1.25, 0.9], gap="large", vertical_alignment="top")
    with hero_left:
        st.markdown('<div class="v2-hero-wrap">', unsafe_allow_html=True)
        st.markdown(
            """
            <span class="v2-tag">▸ Explore in beta</span>
            <h1 class="v2-h1">Australian<br>property insights,<br><b>propelled by data.</b></h1>
            <div class="v2-sub">
              Ditch the guesswork. Our platform gives investors, homebuyers, and pros
              the hard numbers on suburb growth, so you can make your move with
              confidence, not just a hunch.
            </div>
            <div class="v2-actions">
              <a class="v2-btn secondary" href="#">Discover more</a>
              <a class="v2-btn primary" href="#">Get early access →</a>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)
    with hero_right:
        st.markdown(
            """
            <div class="v2-card">
              <div class="v2-card-title"><span>D</span>emografy</div>
              <div>V2 shell is active. Chatbot integration hooks come in phase 2.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


if __name__ == "__main__":
    run_app()
