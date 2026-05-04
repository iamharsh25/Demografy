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

import re
import time
from typing import Literal, Optional

import streamlit as st

ChartKind = Literal["pie", "bar"]

from auth.cooldown import clear_cooldown, set_cooldown_until
from auth.rbac import (
    COOLDOWN_SECONDS,
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


def _chart_visualization_followup(question: str) -> Optional[ChartKind]:
    """If the user is asking to visualize the last result, return ``pie`` or ``bar``."""
    q = " ".join(question.lower().strip().split())
    if not q:
        return None

    # Strip punctuation so "Show as a chart?" matches chip-style phrases.
    q_plain = " ".join(re.sub(r"[^\w\s]+", " ", q).split())

    # Chip text is "Show as a chart?" — match typed variants without relying on
    # ``"show "`` substring quirks or punctuation.
    chip_like = (
        "show as a chart",
        "show as chart",
        "show a chart",
        "show the chart",
        "show chart",
        "see chart",
        "see the chart",
        "see as chart",
        "see as a chart",
        "display chart",
        "display as chart",
        "view chart",
        "view as chart",
        "make a chart",
        "make chart",
        "build a chart",
        "build chart",
        "create a chart",
        "create chart",
        "generate a chart",
        "generate chart",
    )
    if any(s in q_plain for s in chip_like) or re.search(
        r"\b(as a chart|in a chart|on a chart)\b", q_plain
    ):
        if "bar" in q or "column" in q or "histogram" in q:
            return "bar"
        if "pie" in q or "donut" in q:
            return "pie"
        return "pie"

    strong_pie = (
        "pie chart",
        "piechart",
        "pie graph",
        "donut chart",
        " in pie",
        " as pie",
        " a pie chart",
        "pie?",
    )
    strong_bar = ("bar chart", "bar graph", "bar plot", "column chart", "histogram")

    if any(s in q for s in strong_pie):
        return "pie"
    if any(s in q for s in strong_bar):
        return "bar"

    has_viz = any(
        w in q
        for w in ("chart", "graph", "plot", "visualize", "visualise", "diagram")
    )
    wants_action = any(
        a in q
        for a in (
            "show ",
            "show me",
            "display ",
            "see ",
            "give me",
            "can you show",
            "could you show",
            "can you ",
            "could you ",
            "i want ",
            "put it in",
            "put this in",
        )
    )
    if has_viz and wants_action:
        if "bar" in q or "column" in q or "histogram" in q:
            return "bar"
        if "pie" in q or "donut" in q:
            return "pie"
        return "pie"

    # Short natural follow-ups like "show me in chart"
    if re.search(r"\b(show|see)\s+(me\s+)?(this\s+)?(in\s+)?(a\s+)?(pie\s+)?chart\b", q):
        return "pie"
    if re.search(r"\bin\s+(a\s+)?chart\b", q) and len(q.split()) <= 12:
        return "pie"

    # Short imperative: "chart this", "chart it", "visualize this"
    if re.search(r"^\s*(chart|graph|plot)\s+(this|it|that)\s*$", q):
        return "pie"
    if q in ("chart", "graph", "plot", "chart please", "a chart", "the chart"):
        return "pie"

    return None


def _infer_chart_intent_from_llm_rows(rows: list) -> str:
    """Pick a chart renderer intent for ad-hoc SQL rows (``llm_answer`` hydration)."""
    if not rows:
        return "ranked_metric"
    n = len(rows[0])
    if n == 2:
        return "state_learning_avg_list"
    return "ranked_metric"


def _prepare_meta_for_chart(meta: dict) -> Optional[dict]:
    """Return a copy of ``meta`` with ``rows`` filled from ``sql`` when missing.

    Template answers always ship rows, but ``llm_answer`` stores SQL with empty
    rows; re-query so typed "show chart" matches the chart chip behaviour.
    """
    if not isinstance(meta, dict):
        return None
    out = dict(meta)
    intent = str(out.get("intent") or "")
    rows = out.get("rows")
    sql = out.get("sql")

    if isinstance(rows, list) and len(rows) >= 1:
        return out

    if not isinstance(sql, str) or not sql.strip():
        return None

    from agent.chart_renderer import CHARTABLE_INTENTS

    try:
        from db.bigquery_client import run_query
    except Exception:
        return None

    try:
        df = run_query(sql)
    except Exception:
        return None
    if df is None or getattr(df, "empty", True):
        return None
    try:
        new_rows = [tuple(row) for row in df.itertuples(index=False, name=None)]
    except Exception:
        return None
    if not new_rows:
        return None
    out["rows"] = new_rows

    if intent == "llm_answer":
        out["intent"] = _infer_chart_intent_from_llm_rows(new_rows)
    elif intent not in CHARTABLE_INTENTS:
        return None

    return out


def _session_chart_source_meta() -> Optional[dict]:
    """Meta for building a chart: last chartable list survives clarification turns."""
    return st.session_state.get("chat_last_chartable_meta") or st.session_state.get(
        "chat_last_query"
    )


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


def _append(
    role: str,
    content: str,
    *,
    image_b64: Optional[str] = None,
) -> None:
    msg: dict = {"role": role, "content": content}
    if image_b64:
        msg["image_b64"] = image_b64
    st.session_state.chat_messages.append(msg)


def _check_and_expire_cooldown() -> None:
    """If the active cooldown has elapsed, reset the question count.

    This is what gives the user a fresh "mini-session" 30 seconds after
    they hit the tier cap: ``question_count`` goes back to zero and we
    drop both the in-session and on-disk cooldown markers. Called from
    every entry point that can submit a question so the next interaction
    after the timer never has to wait for an extra rerun.
    """
    cooldown_until = st.session_state.get("chat_cooldown_until")
    if not cooldown_until:
        return
    if time.time() < float(cooldown_until):
        return
    st.session_state.chat_cooldown_until = None
    st.session_state.question_count = 0
    user_id = _get_user_id()
    if user_id:
        try:
            clear_cooldown(user_id)
        except Exception:
            pass


def _persist(
    role: str,
    content: str,
    *,
    sql: Optional[str] = None,
    image_b64: Optional[str] = None,
) -> None:
    """Append a message to the active thread's JSONL, swallowing I/O errors.

    Disk problems must never block the chat flow, so this is best-effort.
    """
    user_id = _get_user_id()
    if not user_id:
        return
    thread_id = _ensure_thread_id()
    try:
        append_message(
            user_id,
            thread_id,
            role,
            content,
            sql=sql,
            image_b64=image_b64,
        )
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
    st.session_state.pop("chat_pending_label", None)
    st.session_state.chat_suggestions = []
    st.session_state.chat_last_query = None
    st.session_state.chat_last_chartable_meta = None
    st.session_state.chat_context_query = None


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
        {
            "role": r["role"],
            "content": r["content"],
            **(
                {"image_b64": r["image_b64"]}
                if r.get("image_b64") and isinstance(r.get("image_b64"), str)
                else {}
            ),
        }
        for r in records
        if r.get("role") in ("user", "assistant") and isinstance(r.get("content"), str)
    ]
    st.session_state.chat_pending = False
    st.session_state.chat_pending_question = None
    st.session_state.pop("chat_pending_label", None)
    st.session_state.chat_suggestions = []
    st.session_state.chat_last_query = None
    st.session_state.chat_last_chartable_meta = None
    st.session_state.chat_context_query = None


# ---------------------------------------------------------------------------
# Question lifecycle
# ---------------------------------------------------------------------------

def handle_new_question(question: str) -> None:
    """Append the user message and stash the question for ``resolve``."""
    question = (question or "").strip()
    if not question:
        return

    # If the cooldown has just expired, recover the user's quota before
    # we evaluate the limit on this submission.
    _check_and_expire_cooldown()

    tier = _get_tier()
    question_count = int(st.session_state.get("question_count", 0))
    cooldown_until = st.session_state.get("chat_cooldown_until")

    # Typed chart request: reuse the last result without calling the LLM when possible.
    chart_kind = _chart_visualization_followup(question)
    meta = _session_chart_source_meta()
    if chart_kind and meta:
        try:
            from agent.chart_renderer import is_chartable

            ready_meta = _prepare_meta_for_chart(meta)
            cand = ready_meta or meta
            if is_chartable(
                str(cand.get("intent") or ""),
                cand.get("rows"),
            ):
                st.session_state.chat_suggestions = []
                _append("user", question)
                _persist("user", question)
                if ready_meta:
                    st.session_state.chat_last_query = ready_meta
                handle_chart_request(chart_kind=chart_kind)
                return
        except Exception:
            pass

    # Wipe any chips from the previous turn the moment the user submits
    # something else (typed or chip-clicked). Prevents the old suggestions
    # from briefly hanging under the new bubble while the agent thinks.
    st.session_state.chat_suggestions = []
    st.session_state.chat_context_query = meta
    st.session_state.chat_last_query = None

    # Defensive: while a cooldown is active, drop the submission silently.
    # The widget should already be disabled, so this only fires if a stale
    # bridge payload sneaks through.
    if cooldown_until and time.time() < float(cooldown_until):
        return

    _append("user", question)
    _persist("user", question)

    if is_limit_reached(tier, question_count):
        # The visible cooldown banner replaces the old assistant nag;
        # we keep this state silent so the chat doesn't get spammed.
        return

    st.session_state.chat_pending = True
    st.session_state.chat_pending_question = question
    st.session_state.pop("chat_pending_label", None)


def resolve_pending_question() -> None:
    """If a question is stashed, invoke the agent and append the reply."""
    # Defensive: expire any stale cooldown before evaluating limits below
    # so a question that was queued just as the timer ended still runs.
    _check_and_expire_cooldown()

    if not st.session_state.get("chat_pending"):
        return

    question = st.session_state.get("chat_pending_question")
    if not question:
        st.session_state.chat_pending = False
        st.session_state.pop("chat_pending_label", None)
        return

    # Defer the import so we only pay LangChain / google-genai / BigQuery
    # startup cost once a real question is in flight.
    from agent.sql_agent import USER_FACING_UNANSWERABLE_REPLY, ask, strip_assistant_reply_for_ui

    history: list = []
    user_id = _get_user_id()
    thread_id = st.session_state.get("chat_thread_id")
    if user_id and thread_id:
        try:
            history = last_n_turns(user_id, thread_id, n=HISTORY_TURNS)
        except Exception:
            history = []

    sql_query: Optional[str] = None
    template_meta: Optional[dict] = None
    try:
        context_meta = st.session_state.pop("chat_context_query", None)
        answer, sql_query, template_meta = ask(question, history=history, context_meta=context_meta)
    except Exception:
        # Hide the raw exception from the user; recovery chips will offer
        # alternative on-topic questions based on the prior thread.
        answer = USER_FACING_UNANSWERABLE_REPLY

    final_answer = answer or USER_FACING_UNANSWERABLE_REPLY
    final_answer = strip_assistant_reply_for_ui(final_answer)
    if not (final_answer or "").strip():
        final_answer = USER_FACING_UNANSWERABLE_REPLY
    _append("assistant", final_answer)
    _persist("assistant", final_answer, sql=sql_query)

    try:
        from agent.chart_renderer import is_chartable

        if template_meta and is_chartable(
            str(template_meta.get("intent") or ""),
            template_meta.get("rows"),
        ):
            st.session_state.chat_last_query = template_meta
            st.session_state.chat_last_chartable_meta = dict(template_meta)
        elif sql_query and not template_meta:
            # Preserve LLM-generated SQL so follow-ups ("more?", state swaps)
            # can reference the prior query via context_meta injection.
            st.session_state.chat_last_query = {
                "sql": sql_query,
                "intent": "llm_answer",
                "rows": [],
                "question": question,
                "state": None,
            }
            hydrated = _prepare_meta_for_chart(dict(st.session_state.chat_last_query))
            if hydrated and is_chartable(
                str(hydrated.get("intent") or ""),
                hydrated.get("rows"),
            ):
                st.session_state.chat_last_chartable_meta = hydrated
        elif template_meta:
            st.session_state.chat_last_query = None
            if not template_meta.get("clarification"):
                st.session_state.chat_last_chartable_meta = None
        else:
            st.session_state.chat_last_query = None
    except Exception:
        st.session_state.chat_last_query = None

    # Best-effort chip generation. Failure (no API key, slow network,
    # timeout, garbage output) leaves chips empty - the chat itself is
    # already complete by this point.
    if template_meta and template_meta.get("clarification"):
        st.session_state.chat_suggestions = list(
            template_meta.get("clarification_chips") or []
        )
    else:
        try:
            from agent.suggestions import generate_suggestions

            st.session_state.chat_suggestions = generate_suggestions(
                question=question,
                answer=final_answer,
                history=history,
                chart_meta=_session_chart_source_meta(),
            )
        except Exception:
            st.session_state.chat_suggestions = []

    tier = _get_tier()
    question_count = int(st.session_state.get("question_count", 0)) + 1
    st.session_state.question_count = question_count

    # Hitting the tier cap arms the cooldown. We persist it so a hard
    # refresh keeps the timer ticking; the engine resets the count when
    # it expires via ``_check_and_expire_cooldown``.
    if is_limit_reached(tier, question_count):
        cooldown_until = time.time() + COOLDOWN_SECONDS
        st.session_state.chat_cooldown_until = cooldown_until
        user_id = _get_user_id()
        if user_id:
            try:
                set_cooldown_until(user_id, cooldown_until)
            except Exception:
                pass
    elif should_show_warning(tier, question_count):
        remaining = max(get_question_limit(tier) - question_count, 0)
        plural = "s" if remaining != 1 else ""
        # Soft UI nudge only; intentionally not persisted to the transcript.
        _append(
            "assistant",
            f"Heads up: only {remaining} question{plural} left in this session.",
        )

    st.session_state.chat_pending = False
    st.session_state.chat_pending_question = None
    st.session_state.pop("chat_pending_label", None)


def handle_chart_request(chart_kind: ChartKind = "pie") -> None:
    """Render the last chartable templated result as an inline image bubble."""
    from agent.chart_renderer import build_chart_png_b64, is_chartable

    meta = _session_chart_source_meta()
    if not meta or not is_chartable(
        str(meta.get("intent") or ""),
        meta.get("rows"),
    ):
        _append(
            "assistant",
            "I can only create a chart after a ranked list or comparison result. Ask for a suburb ranking first, then try the chart again.",
        )
        return

    built = build_chart_png_b64(
        str(meta.get("intent") or ""),
        list(meta.get("rows") or []),
        str(meta.get("question") or ""),
        chart_kind=chart_kind,
    )
    if not built:
        _append(
            "assistant",
            "I couldn't create the chart for that result. The data answer is still available above, but the visual failed to render.",
        )
        return

    title, png_b64 = built
    caption = (title or "Chart").strip() or "Chart"
    _append("assistant", caption, image_b64=png_b64)
    _persist(
        "assistant",
        caption,
        sql=meta.get("sql") if isinstance(meta.get("sql"), str) else None,
        image_b64=png_b64,
    )
    st.session_state.chat_last_query = None
    st.session_state.chat_last_chartable_meta = None
    st.session_state.chat_suggestions = []


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

    if action == "chart":
        handle_chart_request()
        return

    if action == "question":
        question = bridge_value.get("question")
        if question:
            handle_new_question(question)
        return

    # Unknown action: ignore silently rather than crash the panel.
