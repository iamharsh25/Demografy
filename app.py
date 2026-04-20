"""
Demografy Insights Chatbot — Streamlit App
Run with: streamlit run app.py
"""

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Demografy Insights",
    page_icon="🏘️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Open+Sans:wght@400;600;700;800&display=swap');

    html, body, .stApp, [class*="css"] {
        font-family: 'Open Sans', sans-serif;
    }

    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    .block-container {
        padding-top: 1rem;
        padding-bottom: 0rem;
        padding-left: 1rem;
        padding-right: 1rem;
    }

    /* Left panel — expanded */
    .left-panel {
        background: linear-gradient(160deg, #5e17eb 0%, #9a66ee 100%);
        border-radius: 16px;
        padding: 32px 24px;
        height: 92vh;
    }
    .left-title {
        color: white;
        font-size: 1.6rem;
        font-weight: 800;
        line-height: 1.2;
        margin-bottom: 10px;
        font-family: 'Open Sans', sans-serif;
    }
    .left-subtitle {
        color: rgba(255,255,255,0.75);
        font-size: 0.82rem;
        line-height: 1.5;
        margin-bottom: 20px;
    }
    .left-tag-cyan {
        background: rgba(141,242,237,0.2);
        color: #8df2ed;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.75rem;
        display: inline-block;
        margin-bottom: 6px;
        border: 1px solid rgba(141,242,237,0.35);
    }
    .left-tag-mint {
        background: rgba(216,242,208,0.2);
        color: #d8f2d0;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.75rem;
        display: inline-block;
        margin-bottom: 6px;
        border: 1px solid rgba(216,242,208,0.35);
    }
    .left-tag-sky {
        background: rgba(202,228,251,0.2);
        color: #cae4fb;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.75rem;
        display: inline-block;
        margin-bottom: 6px;
        border: 1px solid rgba(202,228,251,0.35);
    }
    .left-examples {
        color: rgba(255,255,255,0.5);
        font-size: 0.72rem;
        margin-top: 24px;
        line-height: 1.8;
    }

    /* Left panel — collapsed */
    .left-collapsed {
        background: linear-gradient(160deg, #5e17eb 0%, #9a66ee 100%);
        border-radius: 16px;
        padding: 24px 8px;
        height: 92vh;
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 12px;
    }

    /* Login screen */
    .login-container {
        max-width: 420px;
        margin: 80px auto;
        padding: 40px;
        background: white;
        border-radius: 20px;
        box-shadow: 0 8px 32px rgba(94,23,235,0.12);
        text-align: center;
    }
    .login-logo {
        font-size: 2rem;
        font-weight: 900;
        letter-spacing: -1px;
        margin-bottom: 8px;
        font-family: 'Open Sans', sans-serif;
    }
    .login-subtitle {
        color: #888;
        font-size: 0.85rem;
        margin-bottom: 28px;
    }

    /* Tier badge */
    .tier-badge-pro {
        background: linear-gradient(90deg, #f7971e, #ffd200);
        color: #333;
        padding: 3px 10px;
        border-radius: 12px;
        font-size: 0.7rem;
        font-weight: 700;
        display: inline-block;
        margin-left: 6px;
    }
    .tier-badge-basic {
        background: linear-gradient(90deg, #5e17eb, #9a66ee);
        color: white;
        padding: 3px 10px;
        border-radius: 12px;
        font-size: 0.7rem;
        font-weight: 700;
        display: inline-block;
        margin-left: 6px;
    }
    .tier-badge-free {
        background: #eee;
        color: #666;
        padding: 3px 10px;
        border-radius: 12px;
        font-size: 0.7rem;
        font-weight: 700;
        display: inline-block;
        margin-left: 6px;
    }

    /* Question counter */
    .question-counter {
        background: rgba(94,23,235,0.07);
        border-radius: 12px;
        padding: 12px 16px;
        margin-top: 12px;
        font-size: 0.82rem;
        color: #5e17eb;
        font-weight: 600;
    }

    div[data-testid="column"] > div > div > div > button {
        background: transparent;
        border: none;
        color: white;
        font-size: 1.1rem;
        cursor: pointer;
    }
</style>
""", unsafe_allow_html=True)

# ── Session state initialisation ──────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []
if "panel_open" not in st.session_state:
    st.session_state.panel_open = True
if "user" not in st.session_state:
    st.session_state.user = None
if "question_count" not in st.session_state:
    st.session_state.question_count = 0

# ── LOGIN SCREEN ──────────────────────────────────────────────────────────────
if st.session_state.user is None:
    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        st.markdown("""
        <div class="login-container">
            <div class="login-logo">
                D<span style="color:#5e17eb;">emografy</span>
            </div>
            <div class="login-subtitle">Insights Engine — enter your User ID to continue</div>
        </div>
        """, unsafe_allow_html=True)

        user_id_input = st.text_input(
            "User ID",
            placeholder="e.g. user_001",
            label_visibility="collapsed"
        )

        login_clicked = st.button("Sign In", use_container_width=True, type="primary")

        if login_clicked:
            if not user_id_input.strip():
                st.error("Please enter a User ID.")
            else:
                with st.spinner("Checking credentials..."):
                    try:
                        from auth.rbac import get_user
                        user = get_user(user_id_input.strip())
                        if user is None:
                            st.error("User not found or account is inactive. Please check your User ID.")
                        else:
                            st.session_state.user = user
                            st.session_state.question_count = 0
                            st.session_state.messages = []
                            st.rerun()
                    except Exception as e:
                        st.error(f"Could not connect to user database. Error: {str(e)}")
    st.stop()

# ── LOGGED IN — get user info ─────────────────────────────────────────────────
from auth.rbac import get_question_limit, is_limit_reached, should_show_warning

user = st.session_state.user
tier = user["tier"]
question_count = st.session_state.question_count
limit = get_question_limit(tier)

# ── Layout ────────────────────────────────────────────────────────────────────
if st.session_state.panel_open:
    left, right = st.columns([1, 3])
else:
    left, right = st.columns([0.08, 3])

# ── LEFT PANEL ────────────────────────────────────────────────────────────────
with left:
    if st.session_state.panel_open:
        if st.button("◀", help="Collapse panel", key="collapse"):
            st.session_state.panel_open = False
            st.rerun()

        # Tier badge HTML
        tier_badge = f'<span class="tier-badge-{tier}">{tier.upper()}</span>'

        st.markdown(f"""
        <div class="left-panel">
            <div style="margin-bottom:20px;">
                <span style="color:white;font-size:1.4rem;font-weight:900;letter-spacing:-1px;font-family:'Open Sans',sans-serif;">
                    D<span style="color:#8df2ed;">emografy</span>
                </span>
            </div>
            <div class="left-title">Insights<br>Engine</div>
            <div class="left-subtitle">
                Ask questions about Australian suburb demographics in plain English.
            </div>
            <div class="left-tag-cyan">🏘️ 2,329 suburbs</div><br>
            <div class="left-tag-mint">📊 10 KPIs</div><br>
            <div class="left-tag-sky">🤖 Gemini AI</div>

            <div style="margin-top: 24px; color: rgba(255,255,255,0.7); font-size: 0.78rem;">
                👤 {user['user_id']} {tier_badge}<br>
                <div style="margin-top: 10px; background: rgba(255,255,255,0.1); border-radius: 10px; padding: 10px 14px;">
                    Questions: {question_count} / {limit}
                </div>
            </div>

            <div class="left-examples">
                Try asking:<br>
                "Top 3 diverse suburbs in Victoria?"<br>
                "Avg prosperity score in NSW?"<br>
                "Cheapest rentals in QLD?"
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Logout button
        if st.button("Sign Out", key="logout"):
            st.session_state.user = None
            st.session_state.question_count = 0
            st.session_state.messages = []
            st.rerun()

    else:
        if st.button("▶", help="Expand panel", key="expand"):
            st.session_state.panel_open = True
            st.rerun()

        st.markdown("""
        <div class="left-collapsed">
            <div style="color:white;font-weight:900;font-size:1rem;writing-mode:vertical-rl;
                        text-orientation:mixed;letter-spacing:2px;margin-top:12px;font-family:'Open Sans',sans-serif;">
                DEMOGRAFY
            </div>
        </div>
        """, unsafe_allow_html=True)

# ── RIGHT PANEL ───────────────────────────────────────────────────────────────
with right:
    st.markdown("### 💬 Demografy Insights Chat")
    st.caption("Ask questions about Australian suburb demographics in plain English.")
    st.divider()

    # Chat history
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg.get("sql"):
                with st.expander("🔍 View SQL Query"):
                    st.code(msg["sql"], language="sql")

    # ── Tier limit checks ─────────────────────────────────────────────────────
    if is_limit_reached(tier, question_count):
        # Disable input, show upgrade prompt
        st.error(
            f"🚫 You've reached your **{tier.upper()}** plan limit of **{limit} questions** this session.\n\n"
            f"Upgrade your plan to continue asking questions.",
            icon="🔒"
        )
        st.chat_input("Question limit reached — upgrade to continue", disabled=True)

    else:
        # Show warning if approaching limit
        if should_show_warning(tier, question_count):
            remaining = limit - question_count
            st.warning(f"⚠️ You have **{remaining} question{'s' if remaining != 1 else ''}** remaining on your {tier.upper()} plan this session.")

        # Chat input
        question = st.chat_input("e.g. What are the top 3 suburbs in Victoria by diversity index?")

        if question:
            st.session_state.question_count += 1
            st.session_state.messages.append({"role": "user", "content": question})

            with st.chat_message("user"):
                st.markdown(question)

            with st.chat_message("assistant"):
                sql_query = None
                try:
                    from agent.sql_agent import ask
                    from langchain_community.callbacks.streamlit import StreamlitCallbackHandler
                    steps_container = st.container()
                    st_callback = StreamlitCallbackHandler(
                        steps_container,
                        expand_new_thoughts=True,
                        collapse_completed_thoughts=True,
                    )
                    answer, sql_query = ask(question, callbacks=[st_callback])
                except Exception:
                    try:
                        import os
                        from langchain_google_genai import ChatGoogleGenerativeAI
                        from langchain_core.messages import SystemMessage, HumanMessage
                        with st.spinner("Thinking..."):
                            llm = ChatGoogleGenerativeAI(
                                model="gemini-2.5-flash",
                                google_api_key=os.getenv("GEMINI_API_KEY"),
                                temperature=0,
                            )
                            response = llm.invoke([
                                SystemMessage(content=(
                                    "You are Demografy, an AI assistant specialising in Australian suburb demographics. "
                                    "You have knowledge of ABS census data, suburb statistics, KPIs like diversity index, "
                                    "prosperity score, rental costs, population density, and more. "
                                    "Answer questions helpfully and concisely. "
                                    "Note: live BigQuery data is not yet connected, so answers are based on general knowledge."
                                )),
                                HumanMessage(content=question),
                            ])
                        answer = response.content + "\n\n> ⚠️ *Live data not connected yet — this answer is from general AI knowledge, not the Demografy database.*"
                    except Exception as e2:
                        answer = f"⚠️ Could not get a response.\n\n**Error:** {str(e2)}"

                st.markdown(answer)
                if sql_query:
                    with st.expander("🔍 View SQL Query"):
                        st.code(sql_query, language="sql")

            st.session_state.messages.append({"role": "assistant", "content": answer, "sql": sql_query})
            st.rerun()
