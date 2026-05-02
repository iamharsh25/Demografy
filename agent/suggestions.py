"""LLM-generated follow-up question chips for the chat widget.

Called from ``components.chat_engine.resolve_pending_question`` right
after the assistant reply is persisted. Returns up to three short
follow-up questions that are *semantically* related to the last Q&A so
the user can keep exploring the dataset without typing.

Reliability rules (any failure -> empty list, never blocks the chat):

* The Gemini call runs in a daemon thread with a hard ``CHIP_TIMEOUT``
  wall clock so a slow API never delays the visible answer.
* Every chip passes through the same SQL/identifier sanitiser used for
  the main answer, plus an extra "looks like raw data" filter.
* Output is deduped, capped at 3, and chips that are too similar to the
  last user question are dropped (lowercase token-set Jaccard >= 0.8).
"""

from __future__ import annotations

import os
import re
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout
from threading import Lock
from typing import List, Optional


CHIP_TIMEOUT = 2.5  # seconds; budget for the Gemini call before we give up
RECOVERY_CHIP_TIMEOUT = 4.0  # user is already on the failure screen; small extra wait is acceptable
RECOVERY_HISTORY_TURNS = 10  # widen the window so recovery suggestions have more topic context
MAX_CHIPS = 3
MAX_CHIPS_WITH_CHART = 4  # "Show as a chart?" plus up to three LLM chips
MAX_WORDS = 12

CHART_CHIP_LABEL = "Show as a chart?"

_FORBIDDEN_TOKENS = (
    "kpi_",
    "a_master_view",
    "prod_tables",
    "ref_tables",
    "demografy.",
    "dev_customers",
    "sa2_name",
    "sa2_code",
    "sa3_name",
    "sa4_name",
    "select ",
    "from `",
    "```",
    "`",
)

_DIGIT_RUN = re.compile(r"\d{3,}")
_LEADING_NUMBERING = re.compile(r"^\s*(?:[-*\u2022\u2023]+|\d+[.)])\s*")
_TRIM_QUOTES = re.compile(r"""^["'\u201c\u201d\u2018\u2019\s]+|["'\u201c\u201d\u2018\u2019\s]+$""")


# Module-level single-thread executor + lazy LLM client. The chat agent
# already creates its own LangChain stack; we keep ours separate so the
# generator is dirt-cheap (one direct ``.invoke``) and decoupled from
# any future SQL-agent refactor.
_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="chip-suggest")
_llm = None
_llm_lock = Lock()


def _get_llm():
    """Lazily build the Gemini client; cache it for the process lifetime."""
    global _llm
    if _llm is not None:
        return _llm
    with _llm_lock:
        if _llm is not None:
            return _llm
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI

            api_key = os.getenv("GEMINI_API_KEY")
            if not api_key:
                return None
            _llm = ChatGoogleGenerativeAI(
                model="gemini-2.5-flash-lite",
                google_api_key=api_key,
                temperature=0.3,
                max_output_tokens=256,
            )
        except Exception:
            _llm = None
    return _llm


_SYSTEM_PROMPT = """You write SHORT follow-up question suggestions for users of Demografy,
a tool for exploring Australian SA2-level demographic data.

Available metrics (refer to them by these natural-language names only):
prosperity score, diversity index, migration footprint, learning level,
social housing, rental access, home ownership, resident anchor, young
family presence.

Geographic dimensions: states (Victoria, New South Wales, Queensland,
South Australia, Western Australia, Tasmania, ACT, Northern Territory),
suburbs (SA2), regions.

OUTPUT RULES (mandatory):
- Output exactly THREE follow-up questions, one per line (the app may add one
  extra non-question control chip separately; your lines must all be questions).
- Each question is at most 12 words and ends with "?".
- No numbering, no bullets, no quotes, no preamble, no markdown.
- Plain English only. NEVER mention SQL, column names (like kpi_*),
  table names, or backticks.
- Make each suggestion distinct from the others and from the user's
  previous question. Vary the dimension you change (state, metric,
  limit, comparison) instead of repeating the same shape.
- Stay relevant to the previous question and answer.
"""


_RECOVERY_SYSTEM_PROMPT = """The Demografy assistant could not answer the
user's last question. Suggest THREE short follow-up questions about
Australian SA2-level demographic data the user could ask instead. Use
the prior conversation in this thread to stay on the user's topic
(metric, geography, comparison they were exploring) and only deviate
when the prior topic is exhausted.

Available metrics (use natural-language names only):
prosperity score, diversity index, migration footprint, learning level,
social housing, rental access, home ownership, resident anchor, young
family presence.

Geographic dimensions: states (Victoria, New South Wales, Queensland,
South Australia, Western Australia, Tasmania, ACT, Northern Territory),
suburbs (SA2), regions.

OUTPUT RULES (mandatory):
- Output exactly THREE questions, one per line.
- At most 12 words each, ending with "?".
- No numbering, bullets, quotes, preamble, markdown.
- Plain English; never mention SQL, columns (kpi_*), tables, or backticks.
- Each question must be distinct and clearly different in shape from the
  user's last question (vary metric, geography, limit, or comparison).
- Do not repeat the user's failed question verbatim.
"""


def _build_user_prompt(question: str, answer: str, history: Optional[list]) -> str:
    parts: list[str] = []
    if history:
        # Keep the context tight: only the last user/assistant pair is
        # almost always enough for chip generation. Anything older just
        # dilutes the model's attention.
        recent = list(history)[-4:]
        for turn in recent:
            role = turn.get("role")
            content = (turn.get("content") or "").strip()
            if not content or role not in ("user", "assistant"):
                continue
            label = "User" if role == "user" else "Assistant"
            parts.append(f"{label}: {content}")
    parts.append(f"User just asked: {question.strip()}")
    parts.append(f"Assistant just answered:\n{answer.strip()}")
    parts.append("Now write three follow-up question suggestions.")
    return "\n\n".join(parts)


def _build_recovery_prompt(question: str, history: Optional[list]) -> str:
    """Wider-context prompt for the unanswerable case.

    The assistant has just told the user it cannot help. We give the model
    a longer view of the same thread (up to ``RECOVERY_HISTORY_TURNS``
    turns) so its three suggestions can carry forward the metric/geography
    the user was exploring instead of starting from scratch.
    """
    parts: list[str] = [
        "The assistant could not answer the user's last question. "
        "Use the prior conversation below to recover and propose alternative "
        "on-topic questions the user can ask next."
    ]
    if history:
        recent = list(history)[-RECOVERY_HISTORY_TURNS:]
        rendered: list[str] = []
        for turn in recent:
            role = turn.get("role")
            content = (turn.get("content") or "").strip()
            if not content or role not in ("user", "assistant"):
                continue
            label = "User" if role == "user" else "Assistant"
            rendered.append(f"{label}: {content}")
        if rendered:
            parts.append("Conversation so far:\n" + "\n".join(rendered))
    parts.append(f"Last user question (failed): {question.strip()}")
    parts.append(
        "Suggest three on-topic follow-up questions the user could try instead."
    )
    return "\n\n".join(parts)


def _invoke_llm(prompt: str, *, system_prompt: str = _SYSTEM_PROMPT) -> str:
    llm = _get_llm()
    if llm is None:
        return ""
    try:
        result = llm.invoke(
            [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ]
        )
    except Exception:
        return ""
    text = getattr(result, "content", None)
    if isinstance(text, list):
        text = "\n".join(part.get("text", "") if isinstance(part, dict) else str(part) for part in text)
    return (text or "").strip() if isinstance(text, str) else ""


def _looks_clean(chip: str) -> bool:
    lowered = chip.lower()
    if any(tok in lowered for tok in _FORBIDDEN_TOKENS):
        return False
    if _DIGIT_RUN.search(chip):
        # Raw-looking values (years/percentages with three+ digits) are
        # almost always copy-paste from the result, not a question.
        return False
    return True


def _normalise(chip: str) -> str:
    cleaned = _LEADING_NUMBERING.sub("", chip).strip()
    cleaned = _TRIM_QUOTES.sub("", cleaned).strip()
    cleaned = re.sub(r"\s+", " ", cleaned)
    if not cleaned:
        return ""
    if not cleaned.endswith("?"):
        cleaned = cleaned.rstrip(".!") + "?"
    if len(cleaned.split()) > MAX_WORDS:
        return ""
    return cleaned


def _too_similar(chip: str, reference: str, threshold: float = 0.8) -> bool:
    """Cheap Jaccard-on-tokens overlap test (no extra deps)."""
    a = {tok for tok in re.findall(r"[a-z0-9]+", chip.lower()) if len(tok) > 2}
    b = {tok for tok in re.findall(r"[a-z0-9]+", reference.lower()) if len(tok) > 2}
    if not a or not b:
        return False
    overlap = len(a & b) / len(a | b)
    return overlap >= threshold


def parse_suggestions(
    text: str,
    *,
    prev_question: str = "",
    max_chips: int = MAX_CHIPS,
) -> List[str]:
    """Parse raw LLM output into a clean, deduped list of chips (cap ``max_chips``)."""
    if not text:
        return []

    from agent.sql_agent import _strip_sql_from_answer

    cap = max(1, min(max_chips, MAX_CHIPS_WITH_CHART))
    seen: set[str] = set()
    chips: list[str] = []
    for raw_line in text.splitlines():
        sanitised = _strip_sql_from_answer(raw_line)
        chip = _normalise(sanitised)
        if not chip or not _looks_clean(chip):
            continue
        key = chip.lower()
        if key in seen:
            continue
        if prev_question and _too_similar(chip, prev_question):
            continue
        if chip.lower() == CHART_CHIP_LABEL.lower():
            continue
        seen.add(key)
        chips.append(chip)
        if len(chips) >= cap:
            break
    return chips


def generate_suggestions(
    question: str,
    answer: str,
    history: Optional[list] = None,
    chart_meta: Optional[dict] = None,
) -> List[str]:
    """Return follow-up chips (up to 3, or 4 when a chart chip is prepended).

    When ``chart_meta`` matches a chartable templated result, the first chip is
    ``CHART_CHIP_LABEL``; the client sends a chart bridge action when it is
    clicked instead of posting the text as a question.

    When ``answer`` is the user-facing "I cannot answer" reply, switch to the
    recovery prompt so chips are AI-generated alternatives grounded in the
    same thread; we never substitute a hardcoded list.

    Best-effort: any error (no API key, network failure, timeout, garbage
    output) returns an empty list so the chat experience is unchanged.
    """
    if not (question or "").strip() or not (answer or "").strip():
        return []

    from agent.chart_renderer import is_chartable
    from agent.sql_agent import USER_FACING_UNANSWERABLE_REPLY

    is_recovery = (answer or "").strip() == USER_FACING_UNANSWERABLE_REPLY.strip()

    prepend_chart = False
    if not is_recovery and chart_meta and is_chartable(
        str(chart_meta.get("intent") or ""),
        chart_meta.get("rows"),
    ):
        prepend_chart = True

    llm_cap = MAX_CHIPS_WITH_CHART - 1 if prepend_chart else MAX_CHIPS

    if is_recovery:
        prompt = _build_recovery_prompt(question, history)
        system_prompt = _RECOVERY_SYSTEM_PROMPT
        timeout = RECOVERY_CHIP_TIMEOUT
    else:
        prompt = _build_user_prompt(question, answer, history)
        system_prompt = _SYSTEM_PROMPT
        timeout = CHIP_TIMEOUT

    try:
        future = _executor.submit(_invoke_llm, prompt, system_prompt=system_prompt)
        raw = future.result(timeout=timeout)
    except FutureTimeout:
        return []
    except Exception:
        return []

    llm_chips = parse_suggestions(raw, prev_question=question, max_chips=llm_cap)
    if prepend_chart:
        return [CHART_CHIP_LABEL] + llm_chips
    return llm_chips
