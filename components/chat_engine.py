"""Chat lifecycle: take a user question -> show pending -> call agent -> render.

Owns all session-state mutations for ``chat_messages``. The flow is split
into two phases so the iframe can show a "Thinking..." bubble during the
potentially slow ``ask()`` call:

  Phase 1 (handle_new_question):
    - Append the user message to chat history.
    - Apply RBAC: if limit reached, append a single assistant message and stop.
    - Otherwise mark ``chat_pending`` True (so the next render shows the
      Thinking bubble) and stash the question for phase 2 to pick up.
    - Trigger ``st.rerun()`` so the user sees the bubble immediately.

  Phase 2 (resolve_pending_question):
    - Detect that we have a stashed pending question on this run, call the
      agent, append the assistant reply, increment ``question_count``, and
      append a soft warning if the user is approaching their tier limit.
"""

from typing import Optional

import streamlit as st

from auth.rbac import (
    get_question_limit,
    is_limit_reached,
    should_show_warning,
)


def _get_tier() -> str:
    user = st.session_state.get("user") or {}
    return user.get("tier", "free")


def _append(role: str, content: str) -> None:
    st.session_state.chat_messages.append({"role": role, "content": content})


def handle_new_question(question: str) -> None:
    """Phase 1: react to a fresh user question coming from the bridge."""
    question = (question or "").strip()
    if not question:
        return

    tier = _get_tier()
    question_count = int(st.session_state.get("question_count", 0))

    _append("user", question)

    if is_limit_reached(tier, question_count):
        _append(
            "assistant",
            "You\u2019ve reached your question limit for this session. "
            "Upgrade your tier to continue asking questions.",
        )
        return

    st.session_state.chat_pending = True
    st.session_state.chat_pending_armed = False
    st.session_state.chat_pending_question = question
    st.rerun()


def resolve_pending_question() -> None:
    """Phase 2: invoke the agent for the stashed question (if any).

    Called once per Streamlit run before rendering. If a question was stashed
    by ``handle_new_question``, this clears the pending flag, runs ``ask()``,
    and appends the assistant reply so the same run can render the result.
    """
    if not st.session_state.get("chat_pending"):
        return

    question = st.session_state.get("chat_pending_question")
    if not question:
        st.session_state.chat_pending = False
        st.session_state.chat_pending_armed = False
        return

    # First pending run: render "Thinking..." state, then rerun once more
    # before doing the expensive agent call. This keeps the UI responsive.
    if not st.session_state.get("chat_pending_armed"):
        st.session_state.chat_pending_armed = True
        st.rerun()

    # Defer the import so we only hit the agent's heavy deps (LangChain,
    # google-genai, BigQuery) once a real question is in flight.
    from agent.sql_agent import ask

    try:
        answer, _sql = ask(question)
    except Exception as exc:
        answer = f"Sorry, I hit an error answering that. ({exc})"

    _append("assistant", answer or "Sorry, I could not format an answer for that query.")

    tier = _get_tier()
    question_count = int(st.session_state.get("question_count", 0)) + 1
    st.session_state.question_count = question_count

    if should_show_warning(tier, question_count):
        remaining = max(get_question_limit(tier) - question_count, 0)
        _append(
            "assistant",
            f"Heads up: only {remaining} question{'s' if remaining != 1 else ''} "
            "left in this session.",
        )

    st.session_state.chat_pending = False
    st.session_state.chat_pending_armed = False
    st.session_state.chat_pending_question = None
    st.rerun()


def maybe_consume_bridge(bridge_value: Optional[dict]) -> None:
    """Glue between the bridge component and ``handle_new_question``.

    The bridge returns the same payload on every rerun until a new message
    arrives, so we dedupe by timestamp using ``st.session_state.chat_last_ts``.
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
