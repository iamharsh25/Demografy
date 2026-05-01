"""Chat lifecycle: take a user question -> run the agent -> append the reply.

Owns all session-state mutations for ``chat_messages`` and mirrors every
turn into a per-user JSONL transcript via ``chat_history.storage`` so the
conversation survives reloads and logouts. Designed to run inside an
``@st.fragment`` so the (potentially slow) ``ask()`` call only shows a
fragment-scoped running indicator, not the page-wide fade overlay.

Two functions form the state machine driven by ``app_v4.py``:

  * ``maybe_consume_bridge`` - turns a fresh ``{question, ts}`` payload from
    the chat widget into chat-history + pending-flag mutations. Deduped by
    timestamp so reruns that surface the same sticky payload don't
    double-process.

  * ``resolve_pending_question`` - if a pending question is stashed, calls
    ``agent.sql_agent.ask`` synchronously with the last 5 user turns as
    context, and appends the assistant reply to both session state and
    the on-disk transcript. The chat widget JS shows the optimistic
    Thinking bubble, so we don't need any extra rerun/arming step on the
    Python side.
"""

from typing import Optional

import streamlit as st

from auth.rbac import (
    get_question_limit,
    is_limit_reached,
    should_show_warning,
)
from chat_history.storage import append_message, last_n_turns


# Number of recent user turns (with their assistant replies) to feed back
# into the agent as context for follow-up questions.
HISTORY_TURNS = 5


def _get_user_id() -> Optional[str]:
    user = st.session_state.get("user") or {}
    return user.get("user_id")


def _get_tier() -> str:
    user = st.session_state.get("user") or {}
    return user.get("tier", "free")


def _append(role: str, content: str) -> None:
    st.session_state.chat_messages.append({"role": role, "content": content})


def _persist(role: str, content: str, *, sql: Optional[str] = None) -> None:
    """Append a message to the on-disk transcript, swallowing I/O errors.

    Disk problems must never block the chat flow, so this is best-effort.
    """
    user_id = _get_user_id()
    if not user_id:
        return
    try:
        append_message(user_id, role, content, sql=sql)
    except Exception:
        # Intentionally silent: persistence is a nicety, not a hard
        # requirement for the live UI.
        pass


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

    history = []
    user_id = _get_user_id()
    if user_id:
        try:
            history = last_n_turns(user_id, n=HISTORY_TURNS)
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


def maybe_consume_bridge(bridge_value: Optional[dict]) -> None:
    """Forward a fresh chat-widget payload into ``handle_new_question``.

    The chat widget's component value is sticky across reruns, so we dedupe
    by ``ts`` using ``st.session_state.chat_last_ts``. A None payload (no
    submission yet) is a no-op.
    """
    if not bridge_value:
        return

    ts = bridge_value.get("ts")
    question = bridge_value.get("question")
    if not question or ts is None:
        return

    last_ts = st.session_state.get("chat_last_ts")
    if last_ts == ts:
        return

    st.session_state.chat_last_ts = ts
    handle_new_question(question)
