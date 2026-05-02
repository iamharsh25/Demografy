"""Chat lifecycle: take a user question -> run the agent -> append the reply.

Owns all session-state mutations for ``chat_messages`` and ``chat_thread_id``,
and mirrors every turn into the per-thread JSONL transcript via
``chat_history.storage`` so the conversation survives reloads, logouts, and
thread switches. Designed to run inside an ``@st.fragment`` so the
(potentially slow) ``ask()`` call only shows a fragment-scoped running
indicator, not the page-wide fade overlay.

The bridge between the chat widget iframe and Python is ``maybe_consume_bridge``,
which dispatches on the payload's ``action`` field:

* ``"question"`` (default) - run the agent and append its reply to the
  active thread.
* ``"new_chat"`` - mint a fresh ``chat_thread_id`` and clear the live
  thread without deleting any on-disk transcripts.
* ``"open_thread"`` - load an existing thread's history into the widget
  so the user can continue the conversation.

Agent context (``last_n_turns``) is always scoped to ``chat_thread_id``
so follow-ups never bleed across separate conversations.
"""

from typing import Optional

import streamlit as st

from auth.rbac import (
    get_question_limit,
    is_limit_reached,
    should_show_warning,
)
from chat_history.storage import (
    append_message,
    last_n_turns,
    load_history,
    new_thread_id,
)


HISTORY_TURNS = 5


# ---------------------------------------------------------------------------
# Session helpers
# ---------------------------------------------------------------------------

def _get_user_id() -> Optional[str]:
    user = st.session_state.get("user") or {}
    return user.get("user_id")


def _get_tier() -> str:
    user = st.session_state.get("user") or {}
    return user.get("tier", "free")


def _ensure_thread_id() -> str:
    """Return the active ``chat_thread_id``, minting one if missing."""
    thread_id = st.session_state.get("chat_thread_id")
    if not thread_id:
        thread_id = new_thread_id()
        st.session_state.chat_thread_id = thread_id
    return thread_id


def _append(role: str, content: str) -> None:
    st.session_state.chat_messages.append({"role": role, "content": content})


def _persist(role: str, content: str, *, sql: Optional[str] = None) -> None:
    """Append a message to the active thread's JSONL, swallowing I/O errors.

    Disk problems must never block the chat flow, so this is best-effort.
    """
    user_id = _get_user_id()
    if not user_id:
        return
    thread_id = _ensure_thread_id()
    try:
        append_message(user_id, thread_id, role, content, sql=sql)
    except Exception:
        # Persistence is a nicety, not a hard requirement for the live UI.
        pass


# ---------------------------------------------------------------------------
# Thread switching
# ---------------------------------------------------------------------------

def start_new_chat() -> None:
    """Mint a fresh thread and clear the in-memory conversation.

    The new thread file is NOT created on disk yet; it materialises on
    the first persisted message. We also reset pending-question state so
    a half-submitted question from the previous thread doesn't leak in.

    NOTE: ``chat_last_ts`` is intentionally NOT cleared here. The bridge
    dispatcher already sets it to the current payload's ts before
    invoking us, and clearing it would let the same sticky payload
    re-fire on the next Streamlit rerun.
    """
    st.session_state.chat_thread_id = new_thread_id()
    st.session_state.chat_messages = []
    st.session_state.chat_pending = False
    st.session_state.chat_pending_question = None


def open_thread(thread_id: str) -> None:
    """Load ``thread_id`` into the widget so the user can continue it.

    No-op for an empty id. If the thread file is missing or unreadable,
    we still flip ``chat_thread_id`` so subsequent appends route to it
    (effectively recreating it under the same id).

    Like ``start_new_chat``, we leave ``chat_last_ts`` alone so dedupe
    in ``maybe_consume_bridge`` keeps working across reruns.
    """
    if not thread_id:
        return
    user_id = _get_user_id()
    records: list = []
    if user_id:
        try:
            records = load_history(user_id, thread_id)
        except Exception:
            records = []
    st.session_state.chat_thread_id = thread_id
    st.session_state.chat_messages = [
        {"role": r["role"], "content": r["content"]}
        for r in records
        if r.get("role") in ("user", "assistant") and isinstance(r.get("content"), str)
    ]
    st.session_state.chat_pending = False
    st.session_state.chat_pending_question = None


# ---------------------------------------------------------------------------
# Question lifecycle
# ---------------------------------------------------------------------------

def handle_new_question(question: str) -> None:
    """Append the user message and stash the question for ``resolve``."""
    question = (question or "").strip()
    if not question:
        return

    tier = _get_tier()
    question_count = int(st.session_state.get("question_count", 0))

    _append("user", question)
    _persist("user", question)

    if is_limit_reached(tier, question_count):
        _append(
            "assistant",
            "You\u2019ve reached your question limit for this session. "
            "Upgrade your tier to continue asking questions.",
        )
        return

    st.session_state.chat_pending = True
    st.session_state.chat_pending_question = question


def resolve_pending_question() -> None:
    """If a question is stashed, invoke the agent and append the reply."""
    if not st.session_state.get("chat_pending"):
        return

    question = st.session_state.get("chat_pending_question")
    if not question:
        st.session_state.chat_pending = False
        return

    # Defer the import so we only pay LangChain / google-genai / BigQuery
    # startup cost once a real question is in flight.
    from agent.sql_agent import ask

    history: list = []
    user_id = _get_user_id()
    thread_id = st.session_state.get("chat_thread_id")
    if user_id and thread_id:
        try:
            history = last_n_turns(user_id, thread_id, n=HISTORY_TURNS)
        except Exception:
            history = []

    sql_query: Optional[str] = None
    try:
        answer, sql_query = ask(question, history=history)
    except Exception as exc:
        answer = f"Sorry, I hit an error answering that. ({exc})"

    final_answer = answer or "Sorry, I could not format an answer for that query."
    _append("assistant", final_answer)
    _persist("assistant", final_answer, sql=sql_query)

    tier = _get_tier()
    question_count = int(st.session_state.get("question_count", 0)) + 1
    st.session_state.question_count = question_count

    if should_show_warning(tier, question_count):
        remaining = max(get_question_limit(tier) - question_count, 0)
        plural = "s" if remaining != 1 else ""
        # Soft UI nudge only; intentionally not persisted to the transcript.
        _append(
            "assistant",
            f"Heads up: only {remaining} question{plural} left in this session.",
        )

    st.session_state.chat_pending = False
    st.session_state.chat_pending_question = None


# ---------------------------------------------------------------------------
# Bridge dispatch
# ---------------------------------------------------------------------------

def maybe_consume_bridge(bridge_value: Optional[dict]) -> None:
    """Forward a fresh chat-widget payload into the appropriate handler.

    The chat widget's component value is sticky across reruns, so we
    dedupe by ``ts`` using ``st.session_state.chat_last_ts``. Branches
    on ``payload.action``; missing action defaults to ``"question"`` to
    stay compatible with any older JS clients in flight.
    """
    if not bridge_value:
        return

    ts = bridge_value.get("ts")
    if ts is None:
        return

    last_ts = st.session_state.get("chat_last_ts")
    if last_ts == ts:
        return
    st.session_state.chat_last_ts = ts

    action = bridge_value.get("action") or "question"

    if action == "new_chat":
        start_new_chat()
        return

    if action == "open_thread":
        thread_id = bridge_value.get("thread_id")
        if thread_id:
            open_thread(thread_id)
        return

    if action == "question":
        question = bridge_value.get("question")
        if question:
            handle_new_question(question)
        return

    # Unknown action: ignore silently rather than crash the panel.
