"""LangChain SQL Agent for Demografy Insights Chatbot.

Thin orchestrator: runs the guardrail/template fast-path layers in order,
falling back to the Gemini LLM SQL agent only when nothing else matches.
"""

from __future__ import annotations

import ast
import io
import os
import re
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from dotenv import load_dotenv

# Load .env before importing LangChain so tracing env vars are visible at init.
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from langchain_community.agent_toolkits import create_sql_agent
from langchain_community.utilities import SQLDatabase
from langchain_google_genai import ChatGoogleGenerativeAI

from agent.guardrails import (
    _is_kpi_overview_question,
    _is_metric_definition_question,
    _is_property_price_question,
    _is_schema_probe,
    _kpi_overview_answer,
    _metric_definition_answer,
    _property_price_redirect_answer,
    _unsupported_topic_redirect_answer,
)
from agent.kpis import DEFAULT_LIMIT, GEOGRAPHY_CLARIFICATION_CHIPS, USER_FACING_UNANSWERABLE_REPLY
from agent.prompts import FEW_SHOT_PREFIX
from agent.templates import (
    _affirmative_followup_question,
    _answer_previous_result_metric_question,
    _answer_template_question,
    _contextual_metric_followup_question,
    _detect_affirmative_followup,
    _detect_state_only_followup,
    _geography_clarification_meta,
    _is_show_more_request,
    _needs_diversity_geography_clarification,
    _normalise_question,
    _show_more_answer,
    _template_followup_answer,
)

# Re-export public symbols consumed by other modules.
__all__ = [
    "ask",
    "DEFAULT_LIMIT",
    "GEOGRAPHY_CLARIFICATION_CHIPS",
    "USER_FACING_UNANSWERABLE_REPLY",
    # Template internals re-exported for guardrail_smoke.py
    "_answer_previous_result_metric_question",
    "_contextual_metric_followup_question",
    "_format_template_answer",
    "_template_sql_for_question",
]

# Expose template internals that guardrail_smoke.py imports directly.
from agent.templates import _format_template_answer, _template_sql_for_question  # noqa: E402

_agent = None
_db = None


def _get_db():
    global _db
    if _db is None:
        _db = SQLDatabase.from_uri(
            "bigquery://demografy/prod_tables",
            include_tables=["a_master_view"],
        )
    return _db


def _create_agent():
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash-lite",
        google_api_key=os.getenv("GEMINI_API_KEY"),
        temperature=0,
    )
    return create_sql_agent(
        llm=llm,
        db=_get_db(),
        agent_type="openai-tools",
        prefix=FEW_SHOT_PREFIX,
        verbose=True,
        max_iterations=10,
        return_intermediate_steps=True,
    )


def _extract_sql_from_intermediate_steps(result: dict) -> str | None:
    steps = result.get("intermediate_steps") or []
    for step in reversed(steps):
        action = step[0] if isinstance(step, (tuple, list)) and step else step
        tool_input = getattr(action, "tool_input", None)
        if isinstance(tool_input, dict):
            query = tool_input.get("query") or tool_input.get("sql")
            if isinstance(query, str) and query.strip():
                return query.strip()
        if isinstance(tool_input, str) and tool_input.strip():
            text = tool_input.strip()
            if text.upper().startswith(("SELECT", "WITH")):
                return text
    return None


def _extract_sql_from_text(output_text: str) -> str | None:
    for match in re.finditer(r"\{[^{}]*['\"]query['\"]\s*:\s*.+?\}", output_text, re.DOTALL):
        try:
            payload = ast.literal_eval(match.group(0))
            query = payload.get("query")
            if isinstance(query, str) and query.strip():
                return query.strip()
        except Exception:
            pass
    m = re.search(r"```sql\s*(.+?)```", output_text, re.DOTALL | re.IGNORECASE)
    if m:
        return m.group(1).strip()
    m = re.search(r"===SQL_START===\s*(.+?)\s*===SQL_END===", output_text, re.DOTALL)
    if m:
        return m.group(1).strip()
    return None


def _strip_sql_from_answer(answer: str) -> str:
    """Remove SQL blocks and inline schema identifiers before showing users."""
    text = (answer or "").strip()
    if not text:
        return text

    text = re.sub(r"===SQL_START===.*?===SQL_END===", "", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"```sql.*?```", "", text, flags=re.DOTALL | re.IGNORECASE)

    sqlish = re.compile(
        r"^\s*(SELECT|WITH|FROM|WHERE|JOIN|LEFT JOIN|RIGHT JOIN|INNER JOIN|"
        r"ORDER BY|GROUP BY|LIMIT|HAVING|UNION|INSERT|UPDATE|DELETE|CREATE|DROP)\b",
        flags=re.IGNORECASE,
    )
    kept_lines = [
        line for line in text.splitlines()
        if not sqlish.match(line) and not line.strip().startswith("SQL Query:")
    ]
    text = "\n".join(kept_lines)

    text = re.sub(r"`?demografy\.(?:prod_tables|ref_tables)\.[a-z_0-9]+`?", "", text, flags=re.IGNORECASE)
    text = re.sub(r"`?\ba_master_view\b`?", "", text, flags=re.IGNORECASE)
    text = re.sub(r"`?\bdev_customers\b`?", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*\(\s*(?:kpi_\d+_(?:val|ind)|sa2_(?:name|code)|sa[34]_name)\s*\)", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\b(?:kpi_\d+_(?:val|ind)|sa2_(?:name|code)|sa[34]_name)\b", "", text, flags=re.IGNORECASE)

    text = re.sub(r"\(\s*\)", "", text)
    text = re.sub(r"`\s*`", "", text)
    text = re.sub(r"[ \t]+([,.;:%])", r"\1", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r" +\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


def ask(
    question: str,
    callbacks=None,
    history: list[dict] | None = None,
    context_meta: dict | None = None,
) -> tuple[str, str | None, dict | None]:
    """Answer a user question using fast-path layers before falling back to the LLM.

    Returns ``(answer, sql, meta)``. ``meta`` carries intent/rows for charting
    on template answers; ``None`` for LLM answers. A clarification meta dict
    (``{"clarification": True, ...}``) is returned when geography is required.
    """
    global _agent

    norm = _normalise_question(question)

    if _is_schema_probe(norm):
        return (
            "I can only answer questions about Australian demographic data — suburbs, states, "
            "and the KPIs in the overview. Try asking something like "
            "\"top diverse suburbs in Victoria\" or \"prosperity score in Forde\".",
            None,
            None,
        )

    context_answer = _answer_previous_result_metric_question(question, context_meta)
    if context_answer:
        return context_answer

    if _is_show_more_request(norm) and context_meta:
        result = _show_more_answer(context_meta)
        if result:
            return result

    if _is_kpi_overview_question(norm):
        return _kpi_overview_answer(), None, None

    if _is_metric_definition_question(norm):
        answer = _metric_definition_answer(norm)
        if answer:
            return answer, None, None

    if _is_property_price_question(norm):
        return _property_price_redirect_answer(), None, None

    unsupported_answer = _unsupported_topic_redirect_answer(norm)
    if unsupported_answer:
        return unsupported_answer, None, None

    if _detect_affirmative_followup(question):
        if context_meta and context_meta.get("clarification"):
            clarify = (
                "I still need a state or city to narrow the results. "
                "Pick one of the suggestions below, or type a place name (for example Melbourne or NSW)."
            )
            return clarify, None, _geography_clarification_meta()
        resolved = _affirmative_followup_question(history)
        if resolved:
            template_answer = _answer_template_question(resolved)
            if template_answer:
                return template_answer

    template_answer = _answer_template_question(question)
    if template_answer:
        return template_answer

    resolved_metric_followup = _contextual_metric_followup_question(question, history)
    if resolved_metric_followup:
        template_answer = _answer_template_question(resolved_metric_followup)
        if template_answer:
            return template_answer

    new_state = _detect_state_only_followup(question)
    if new_state and history:
        followup = _template_followup_answer(history, new_state)
        if followup:
            return followup

    if _needs_diversity_geography_clarification(question):
        clarify = (
            "I can list the most diverse suburbs, but I need a state or city to narrow the results. "
            "Pick one of the suggestions below, or type a place name (for example Melbourne or NSW)."
        )
        return clarify, None, _geography_clarification_meta()

    if _agent is None:
        _agent = _create_agent()

    agent_input = question
    context_parts: list[str] = []
    if history:
        from chat_history.context import build_context_block
        context_block = build_context_block(history)
        if context_block:
            context_parts.append(context_block)
    if context_meta and context_meta.get("sql"):
        context_parts.append(
            f"Previous SQL query (you may modify this to answer the follow-up):\n"
            f"```sql\n{context_meta['sql']}\n```\n"
        )
    if context_parts:
        full_context = "".join(context_parts)
        if len(full_context) > 3000:
            full_context = full_context[-3000:]
        agent_input = full_context + f"Current question: {question}"

    captured_output = io.StringIO()
    with redirect_stdout(captured_output), redirect_stderr(captured_output):
        result = _agent.invoke({"input": agent_input}, config={"callbacks": callbacks or []})

    output_text = captured_output.getvalue()
    sql_query = _extract_sql_from_intermediate_steps(result) or _extract_sql_from_text(output_text)

    if sql_query:
        try:
            print("SQL Query:", sql_query)
        except Exception:
            pass

    answer = (result.get("output") or "").strip()
    answer = _strip_sql_from_answer(answer)
    if not answer:
        answer = USER_FACING_UNANSWERABLE_REPLY
    return answer, sql_query, None
