"""Global CSS for the v4 Streamlit-rendered chrome (header, dropdown, etc.).

Lives separately from rendering so all selector rules have one owner.
The body iframe owns its own scoped CSS in `components/body.py` and
`components/chatbox.py`.
"""

import streamlit as st


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
