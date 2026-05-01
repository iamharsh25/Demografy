"""
Demografy Insights Chatbot - Streamlit App
Run with: streamlit run app.py
"""

import os
import uuid
import streamlit as st
import streamlit.components.v1 as components
import json
import threading
import time
from dotenv import load_dotenv
from datetime import date, timedelta

load_dotenv()

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Demografy Insights",
    page_icon="D",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# ══════════════════════════════════════════════════════════════════════════════
# CSS
# ══════════════════════════════════════════════════════════════════════════════
def load_css():
    st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Open+Sans:wght@400;600;700;800;900&display=swap');

    html, body, .stApp, [class*="css"] {
        font-family: 'Open Sans', sans-serif;
    }

    #MainMenu {visibility: hidden;}
    footer     {visibility: hidden;}
    header     {visibility: hidden;}

    .stApp {
        background: #f7f5fb;
        color: #272d2d;
    }

    .block-container {
        padding-top: 1rem;
        padding-bottom: 0;
        padding-left: 1rem;
        padding-right: 1rem;
        max-width: 100%;
    }

    /* ═══ SIDEBAR COLUMN (only in 2-column main layout, not login's 3-column layout) ═══ */
    [data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"]:nth-child(2):last-child) > [data-testid="stColumn"]:first-child {
        background: linear-gradient(160deg, #5e17eb 0%, #9a66ee 100%);
        border-radius: 16px;
    }
    [data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"]:nth-child(2):last-child) > [data-testid="stColumn"]:first-child > [data-testid="stVerticalBlockBorderWrapper"] > div > [data-testid="stVerticalBlock"] {
        padding: 16px 8px 16px;
        min-height: 92vh;
        display: flex;
        flex-direction: column;
        align-items: center;
    }

    /* Sidebar icon buttons */
    [data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"]:nth-child(2):last-child) > [data-testid="stColumn"]:first-child button {
        background: transparent !important;
        color: rgba(255,255,255,0.75) !important;
        border: none !important;
        border-radius: 12px !important;
        font-size: 1.4rem !important;
        padding: 10px 8px !important;
        width: 100% !important;
        text-align: center !important;
        justify-content: center !important;
        transition: background 0.15s, color 0.15s !important;
        line-height: 1 !important;
    }
    [data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"]:nth-child(2):last-child) > [data-testid="stColumn"]:first-child button:hover {
        background: rgba(255,255,255,0.18) !important;
        color: white !important;
    }

    /* ═══ SIDEBAR ICON LOGO ═══ */
    .sb-icon-logo {
        color: white;
        font-size: 1.5rem;
        font-weight: 900;
        text-align: center;
        padding: 8px 0 20px;
        letter-spacing: -1px;
        width: 100%;
    }

    /* ═══ EMPTY STATE ═══ */
    .empty-wrap {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        min-height: 58vh;
        text-align: center;
        padding: 20px;
    }
    .empty-orb      { font-size: 4rem; margin-bottom: 20px; }
    .empty-greeting { font-size: 1.9rem; font-weight: 800; color: #1a1a2e; margin-bottom: 8px; }
    .empty-sub      { font-size: 1rem; color: #888; margin-bottom: 36px; }

    /* Suggestion cards */
    .card-wrap button {
        background: #fafafa !important;
        color: #333 !important;
        border: 1px solid #ebebeb !important;
        border-radius: 14px !important;
        font-size: 0.85rem !important;
        font-weight: 500 !important;
        padding: 18px 16px !important;
        text-align: left !important;
        min-height: 80px !important;
        justify-content: flex-start !important;
        white-space: normal !important;
        line-height: 1.4 !important;
    }
    .card-wrap button:hover {
        background: #f3eeff !important;
        border-color: #c9a5ff !important;
        color: #5e17eb !important;
    }

    /* ═══ COUNTER PILL (fixed above chat input) ═══ */
    .counter-fixed {
        position: fixed;
        bottom: 72px;
        right: 24px;
        z-index: 999;
        background: rgba(255,255,255,0.92);
        border: 1px solid #e5e5e5;
        border-radius: 20px;
        padding: 4px 14px;
        font-size: 0.72rem;
        font-weight: 600;
        backdrop-filter: blur(8px);
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
    }
    .c-green  { color: #5e17eb; }
    .c-yellow { color: #d97706; }
    .c-red    { color: #dc2626; }

    /* ═══ LOGIN ═══ */
    .login-wrap {
        max-width: 420px;
        margin: 80px auto;
        padding: 42px;
        background: white;
        border-radius: 20px;
        box-shadow: 0 8px 32px rgba(94,23,235,0.12);
        text-align: center;
    }
    .login-logo { font-size: 2rem; font-weight: 900; letter-spacing: -1px; margin-bottom: 8px; }
    .login-sub  { color: #999; font-size: 0.85rem; margin-bottom: 28px; }

    /* ═══ TIER BADGES ═══ */
    .badge-pro   { background:linear-gradient(90deg,#f7971e,#ffd200); color:#333; padding:2px 9px; border-radius:10px; font-size:0.68rem; font-weight:700; }
    .badge-basic { background:linear-gradient(90deg,#5e17eb,#9a66ee); color:white; padding:2px 9px; border-radius:10px; font-size:0.68rem; font-weight:700; }
    .badge-free  { background:#eee; color:#666; padding:2px 9px; border-radius:10px; font-size:0.68rem; font-weight:700; }
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════════════
def _save_current(user_id: str):
    """Save the current active session to disk if it has messages."""
    from utils.chat_history import save_session
    msgs = st.session_state.get("messages", [])
    if msgs:
        title = msgs[0]["content"][:60]
        save_session(user_id, st.session_state.session_id, title, msgs)


# ══════════════════════════════════════════════════════════════════════════════
# MODAL — User account info
# ══════════════════════════════════════════════════════════════════════════════
@st.dialog("My Account")
def show_user_modal(user: dict, question_count: int, limit: int, tier: str):
    remaining = limit - question_count
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

    if remaining <= 0:
        st.error("Question limit reached for this session.")
    elif remaining <= 5:
        st.warning(f"⚠️ Only {remaining} question{'s' if remaining != 1 else ''} left.")
    else:
        st.success(f"✅ {remaining} questions remaining.")

    st.divider()
    if st.button("🚪  Sign Out", type="primary", use_container_width=True):
        print(f"[LOGOUT] user_id={user['user_id']} | questions={question_count}")
        for key in ["user", "question_count", "messages", "session_id", "pending_question"]:
            st.session_state.pop(key, None)
        st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# MODAL — Chat history
# ══════════════════════════════════════════════════════════════════════════════
@st.dialog("Chat History")
def show_history_modal(user: dict):
    from utils.chat_history import load_history
    sessions = load_history(user["user_id"])

    if not sessions:
        st.info("No previous chats yet. Start a conversation!")
        return

    today_str     = date.today().isoformat()
    yesterday_str = (date.today() - timedelta(days=1)).isoformat()

    grouped = {}
    for s in sessions:
        d = s.get("date", "")
        label = "Today" if d == today_str else "Yesterday" if d == yesterday_str else d
        grouped.setdefault(label, []).append(s)

    for group_label, group_sessions in list(grouped.items())[:7]:
        st.markdown(f"**{group_label}**")
        for s in group_sessions[:5]:
            title = s.get("title", "Untitled")
            short = (title[:55] + "…") if len(title) > 55 else title
            if st.button(f"· {short}", key=f"hm_{s['session_id']}", use_container_width=True):
                _save_current(user["user_id"])
                st.session_state.messages   = s["messages"]
                st.session_state.session_id = s["session_id"]
                st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# COMPONENT — Sidebar
# ══════════════════════════════════════════════════════════════════════════════
def render_sidebar(user: dict, question_count: int, limit: int, tier: str):
    # Demografy "D" logo mark
    st.markdown('<div class="sb-icon-logo">D</div>', unsafe_allow_html=True)

    # ✏️ New Chat
    if st.button("✏️", key="new_chat", help="Start New Chat", use_container_width=True):
        _save_current(user["user_id"])
        st.session_state.messages = []
        st.session_state.session_id = str(uuid.uuid4())
        st.rerun()

    # 🕐 History → dialog
    if st.button("🕐", key="history", help="Chat History", use_container_width=True):
        show_history_modal(user)

    # Spacer pushes user icon to bottom
    st.markdown("<div style='flex:1; min-height:20px;'></div>", unsafe_allow_html=True)

    # 👤 User account → modal
    if st.button("👤", key="user_footer", help=user["user_id"], use_container_width=True):
        show_user_modal(user, question_count, limit, tier)


# ══════════════════════════════════════════════════════════════════════════════
# COMPONENT — Empty state (no messages yet)
# ══════════════════════════════════════════════════════════════════════════════
def render_empty_state() -> str | None:
    """Renders the centered empty state. Returns suggestion text if a card was clicked."""
    from datetime import datetime
    hour = datetime.now().hour
    greeting = "Good Morning" if hour < 12 else "Good Afternoon" if hour < 17 else "Good Evening"
    name = st.session_state.user["user_id"].replace("_", " ").title()

    st.markdown(f"""
    <div class="empty-wrap">
        <div class="empty-orb">🔮</div>
        <div class="empty-greeting">{greeting}, {name}</div>
        <div class="empty-sub">What suburb are you <span style="color:#5e17eb;font-weight:700;">exploring today?</span></div>
    </div>
    """, unsafe_allow_html=True)

    suggestions = [
        ("🏘️", "Top 3 diverse suburbs in Victoria?"),
        ("📊", "Average prosperity score in NSW?"),
        ("🏡", "Cheapest rentals in Queensland?"),
        ("👨‍👩‍👧", "Best suburbs for young families in ACT?"),
    ]

    col1, col2 = st.columns(2)
    for i, (icon, text) in enumerate(suggestions):
        with (col1 if i % 2 == 0 else col2):
            st.markdown('<div class="card-wrap">', unsafe_allow_html=True)
            if st.button(f"{icon}  {text}", key=f"sug_{i}", use_container_width=True):
                return text
            st.markdown('</div>', unsafe_allow_html=True)

    return None


# ══════════════════════════════════════════════════════════════════════════════
# COMPONENT — Chat messages
# ══════════════════════════════════════════════════════════════════════════════
def render_chat_messages(messages: list):
    for msg in messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg.get("sql"):
                with st.expander("🔍 View SQL Query"):
                    st.code(msg["sql"], language="sql")


# ══════════════════════════════════════════════════════════════════════════════
# COMPONENT — Counter pill (fixed near chat input)
# ══════════════════════════════════════════════════════════════════════════════
def render_counter(question_count: int, limit: int, tier: str):
    remaining = limit - question_count
    if remaining <= 0:
        cls, label = "c-red", "❌ limit reached"
    elif remaining <= 3:
        cls, label = "c-red", f"🔴 {remaining} left"
    elif remaining <= int(limit * 0.25):
        cls, label = "c-yellow", f"🟡 {remaining} left"
    else:
        cls, label = "c-green", f"🟢 {remaining} left"

    st.markdown(
        f'<div class="counter-fixed"><span class="{cls}">{label} · {tier.upper()}</span></div>',
        unsafe_allow_html=True,
    )


# ══════════════════════════════════════════════════════════════════════════════
# COMPONENT — Login screen
# ══════════════════════════════════════════════════════════════════════════════
def render_login():
    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        st.markdown("""
        <div class="login-wrap">
            <div class="login-logo">D<span style="color:#5e17eb;">emografy</span></div>
            <div class="login-sub">AI Engine — enter your User ID to continue</div>
        </div>
        """, unsafe_allow_html=True)

        user_id_input = st.text_input(
            "User ID",
            placeholder="e.g. user_001",
            label_visibility="collapsed",
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
                            print(f"[LOGIN] Failed for user_id='{user_id_input.strip()}'")
                            st.error("User not found or account is inactive. Please check your User ID.")
                        else:
                            print(f"[LOGIN] {user['user_id']} logged in | tier={user['tier']}")
                            st.session_state.user         = user
                            st.session_state.question_count = 0
                            st.session_state.messages      = []
                            st.session_state.session_id    = str(uuid.uuid4())
                            st.rerun()
                    except Exception as e:
                        st.error(f"Could not connect to user database. Error: {str(e)}")


# ══════════════════════════════════════════════════════════════════════════════
# HANDLER — Process a question through the agent
# ══════════════════════════════════════════════════════════════════════════════
def handle_question(question: str, user: dict, tier: str, limit: int):
    from utils.chat_history import save_session

    st.session_state.question_count += 1
    print(f"[QUESTION] user_id={user['user_id']} | tier={tier} | q={st.session_state.question_count}/{limit} | '{question}'")

    st.session_state.messages.append({"role": "user", "content": question, "sql": None})

    with st.chat_message("user"):
        st.markdown(question)

    sql_query = None
    answer    = None

    with st.chat_message("assistant"):
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
            print(f"[AGENT] Response generated | sql={sql_query}")
        except Exception as agent_err:
            print(f"[AGENT] Agent failed, falling back to LLM. Error: {agent_err}")
            try:
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
                answer = response.content + "\n\n> ⚠️ *Live data not connected — answer from general AI knowledge.*"
                print("[LLM FALLBACK] Response generated successfully")
            except Exception as e2:
                print(f"[LLM FALLBACK] Also failed. Error: {e2}")
                answer = f"⚠️ Could not get a response.\n\n**Error:** {str(e2)}"

        if answer:
            st.markdown(answer)
            if sql_query:
                with st.expander("🔍 View SQL Query"):
                    st.code(sql_query, language="sql")

    st.session_state.messages.append({"role": "assistant", "content": answer or "", "sql": sql_query})

    # Auto-save session after every message
    save_session(
        user_id=user["user_id"],
        session_id=st.session_state.session_id,
        title=st.session_state.messages[0]["content"][:60],
        messages=st.session_state.messages,
    )

    st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════
load_css()

# Session state initialisation
for _key, _default in [
    ("user",             None),
    ("question_count",   0),
    ("messages",         []),
    ("session_id",       str(uuid.uuid4())),
    ("pending_question", None),
]:
    if _key not in st.session_state:
        st.session_state[_key] = _default

# ── Login gate ─────────────────────────────────────────────────────────────────
if st.session_state.user is None:
    render_login()
    st.stop()

# ── Logged-in layout ───────────────────────────────────────────────────────────
from auth.rbac import get_question_limit, is_limit_reached, should_show_warning

user           = st.session_state.user
tier           = user["tier"]
question_count = st.session_state.question_count
limit          = get_question_limit(tier)
messages       = st.session_state.messages


# Layout
if st.session_state.panel_open:
    left, right = st.columns([1, 3])
else:
    left, right = st.columns([0.08, 3])

# Left panel
with left:
    if st.session_state.panel_open:
        if st.button("Collapse", help="Collapse panel", key="collapse"):
            st.session_state.panel_open = False
            st.rerun()

        # Tier badge HTML
        tier_badge = f'<span class="tier-badge-{tier}">{tier.upper()}</span>'

        st.markdown(f"""
        <div class="left-panel">
            <div style="margin-bottom:20px;">
                <span style="color:white;font-size:1.4rem;font-weight:900;letter-spacing:-1px;font-family:'Open Sans',sans-serif;">
                    D<span style="color:#d8f2d0;">emografy</span>
                </span>
            </div>
            <div class="left-title">Insights<br>Engine</div>
            <div class="left-subtitle">
                Ask questions about Australian suburb demographics in plain English.
            </div>
            <div class="left-metric">
                <div class="left-metric-value">2,329</div>
                <div class="left-metric-label">SA2 areas</div>
            </div>
            <div class="left-metric">
                <div class="left-metric-value">10</div>
                <div class="left-metric-label">Demographic KPIs</div>
            </div>
            <div class="left-metric">
                <div class="left-metric-value">Live</div>
                <div class="left-metric-label">Live data answers</div>
            </div>

            <div style="margin-top: 24px; color: rgba(255,255,255,0.7); font-size: 0.78rem;">
                {user['user_id']} {tier_badge}<br>
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
            st.session_state.last_query_context = None
            # Clear persisted browser session and remove query param
            try:
                components.html(
                    "<script>localStorage.removeItem('demografy_user'); if(window.history && history.replaceState){ const u=new URL(window.location); u.searchParams.delete('user'); history.replaceState(null,'', u); }</script>",
                    height=0,
                )
            except Exception:
                pass
            try:
                st.experimental_set_query_params()
            except Exception:
                pass

left, right = st.columns([0.18, 3.82])

with left:
    render_sidebar(user, question_count, limit, tier)

with right:
    # Pick up any pending question from suggestion chips
    pending = st.session_state.pop("pending_question", None)

    if not messages:
        suggestion = render_empty_state()
        if suggestion:
            st.session_state.pending_question = suggestion
            st.rerun()
    else:
        render_chat_messages(messages)

    # Counter pill + chat input
    if is_limit_reached(tier, question_count):
        st.error(
            f"🚫 You've reached your **{tier.upper()}** plan limit of **{limit} questions** this session.\n\n"
            "Upgrade your plan to continue."
        )
        st.chat_input("Question limit reached — upgrade to continue", disabled=True)
    else:
        if should_show_warning(tier, question_count):
            remaining = limit - question_count
            st.warning(f"⚠️ You have **{remaining} question{'s' if remaining != 1 else ''}** remaining this session.")

        render_counter(question_count, limit, tier)
        question = st.chat_input("e.g. What are the top 3 suburbs in Victoria by diversity index?") or pending

        if question:
            handle_question(question, user, tier, limit)
