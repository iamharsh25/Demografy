"""
Conversation helpers for the Streamlit app.

These helpers keep the evaluated SQL path stable while making the UI feel more
like a conversation: short follow-ups can inherit the previous metric, geography,
and result context.
"""

import re


STATE_ALIASES = {
    "act": "Australian Capital Territory",
    "australian capital territory": "Australian Capital Territory",
    "nsw": "New South Wales",
    "new south wales": "New South Wales",
    "nt": "Northern Territory",
    "northern territory": "Northern Territory",
    "qld": "Queensland",
    "queensland": "Queensland",
    "sa": "South Australia",
    "south australia": "South Australia",
    "tas": "Tasmania",
    "tasmania": "Tasmania",
    "vic": "Victoria",
    "victoria": "Victoria",
    "wa": "Western Australia",
    "western australia": "Western Australia",
}

METRIC_NOTES = {
    "kpi_1_val": "Prosperity score is Demografy's 0-100 measure of relative socioeconomic advantage.",
    "kpi_2_val": "Diversity index runs from 0 to 1, where higher values indicate a broader mix of ancestry groups.",
    "kpi_3_val": "Migration footprint is the share of residents with at least one overseas-born parent.",
    "kpi_4_val": "Learning level is the share of residents who completed Year 12.",
    "kpi_5_val": "Social housing is the share of dwellings that are public or community housing.",
    "kpi_6_val": "Resident equity is the share of dwellings owned outright or with a mortgage.",
    "kpi_7_val": "Rental access is the share of rentals below $450 per week.",
    "kpi_8_val": "Resident anchor measures the share of residents who stayed in the same community for 5+ years.",
    "kpi_10_val": "Young family presence is the share of the population aged 0-14.",
}

METRIC_DEFINITIONS = {
    ("migration footprint", "migration"): METRIC_NOTES["kpi_3_val"],
    ("diversity index", "diversity", "diverse"): METRIC_NOTES["kpi_2_val"],
    ("prosperity score", "prosperity"): METRIC_NOTES["kpi_1_val"],
    ("learning level", "education"): METRIC_NOTES["kpi_4_val"],
    ("social housing",): METRIC_NOTES["kpi_5_val"],
    ("resident equity", "home ownership"): METRIC_NOTES["kpi_6_val"],
    ("rental access", "affordability", "affordable"): METRIC_NOTES["kpi_7_val"],
    ("resident anchor", "stability", "stable"): METRIC_NOTES["kpi_8_val"],
    ("young family", "families"): METRIC_NOTES["kpi_10_val"],
}

METRIC_LABELS = {
    ("migration footprint", "migration"): "migration footprint",
    ("diversity index", "diversity", "diverse"): "diversity index",
    ("prosperity score", "prosperity"): "prosperity score",
    ("learning level", "education"): "learning level",
    ("social housing",): "social housing",
    ("resident equity", "home ownership"): "home ownership",
    ("rental access", "affordability", "affordable"): "rental access",
    ("resident anchor", "stability", "stable"): "resident anchor",
    ("young family", "families"): "young family presence",
}

METRIC_WORDS = (
    "diverse", "diversity", "prosperity", "learning", "education", "social housing",
    "rental", "affordable", "home ownership", "resident equity", "stable",
    "resident anchor", "migration", "young family", "families",
)


def _normalise(text: str) -> str:
    return " ".join(text.lower().strip().rstrip("?").split())


def _extract_state(text: str) -> str | None:
    normalised = _normalise(text)
    for alias, state in sorted(STATE_ALIASES.items(), key=lambda item: len(item[0]), reverse=True):
        if re.search(rf"\b{re.escape(alias)}\b", normalised):
            return state
    return None


def _replace_state(question: str, state: str) -> str:
    for alias, old_state in sorted(STATE_ALIASES.items(), key=lambda item: len(item[0]), reverse=True):
        pattern = re.compile(rf"\b{re.escape(old_state)}\b|\b{re.escape(alias)}\b", re.IGNORECASE)
        if pattern.search(question):
            return pattern.sub(state, question, count=1)
    return f"{question} in {state}"


def _replace_limit(question: str, user_text: str) -> str:
    match = re.search(r"\b(?:top|first|only)\s+(\d+)\b|\bshow\s+(?:top\s+)?(\d+)\b", user_text, re.IGNORECASE)
    if not match:
        return question

    limit = match.group(1) or match.group(2)
    if re.search(r"\b(?:top|first)\s+\d+\b", question, re.IGNORECASE):
        return re.sub(r"\b(?:top|first)\s+\d+\b", f"top {limit}", question, count=1, flags=re.IGNORECASE)
    return f"Top {limit} {question}"


def has_new_metric(question: str) -> bool:
    text = _normalise(question)
    return any(word in text for word in METRIC_WORDS)


def resolve_followup(question: str, context: dict | None) -> tuple[str, str | None]:
    """
    Convert short follow-ups into standalone questions using the last turn.
    """
    if not context or not context.get("question"):
        return question, None

    text = _normalise(question)
    if _definition_note(text) and len(text.split()) <= 5:
        return question, None

    if has_new_metric(question):
        return question, None

    previous = context["question"]
    state = _extract_state(question)
    resolved = previous

    if state:
        resolved = _replace_state(resolved, state)

    resolved = _replace_limit(resolved, question)

    followup_markers = (
        "what about", "how about", "and ", "same for", "show ", "show me", "top ", "only ",
        "what if", "compare with", "compare to",
    )
    if state or resolved != previous or any(text.startswith(marker) for marker in followup_markers):
        return resolved, f"I treated that as: {resolved}"

    return question, None


def answer_contextual_question(question: str, context: dict | None) -> str | None:
    """
    Answer lightweight explanation follow-ups without issuing a new query.
    """
    text = _normalise(question)
    is_explanation = any(text.startswith(prefix) for prefix in ("why", "what does", "explain", "what is", "what are"))

    direct_note = _definition_note(text)
    metric_label = _metric_label(text)
    if metric_label and text.startswith("based on"):
        return (
            f"Sure - how would you like to use {metric_label}? For example, I can show the top suburbs "
            "nationally, focus on a specific state, or compare averages by state."
        )

    if direct_note and (is_explanation or len(text.split()) <= 5):
        return direct_note

    if metric_label and _looks_like_metric_fragment(text):
        return (
            f"Sure - how would you like to use {metric_label}? For example, I can show the top suburbs "
            "nationally, focus on a specific state, or compare averages by state."
        )

    if not is_explanation:
        return None

    if not context:
        return None

    sql = context.get("sql") or ""
    note = _metric_note(sql)
    if not note:
        return None

    if "why" in text:
        return (
            f"{note}\n\n"
            "The ranking comes directly from the most recent result: areas with higher metric values "
            "appear earlier in the list."
        )

    return note


def _metric_note(sql: str) -> str | None:
    for column, note in METRIC_NOTES.items():
        if column in sql:
            return note
    return None


def _definition_note(text: str) -> str | None:
    for keywords, note in METRIC_DEFINITIONS.items():
        if any(keyword in text for keyword in keywords):
            return note
    return None


def _metric_label(text: str) -> str | None:
    for keywords, label in METRIC_LABELS.items():
        if any(keyword in text for keyword in keywords):
            return label
    return None


def _looks_like_metric_fragment(text: str) -> bool:
    action_words = (
        "top", "highest", "lowest", "average", "compare", "show", "find", "which",
        "what is", "what are", "explain", "why", "over", "above", "below", "under",
    )
    return text.startswith("based on") or not any(word in text for word in action_words)


def sanitize_user_answer(answer: str) -> str:
    """
    Remove internal implementation details from user-facing chat text.
    """
    if not answer:
        return answer

    sanitized = re.sub(
        r"(?:the\s+)?`?(?:demografy\.[\w.]+|a_master_view)`?\s+table\s+contains",
        "The Demografy dataset includes",
        answer,
        flags=re.IGNORECASE,
    )
    sanitized = re.sub(
        r"(?:the\s+)?`?kpi_\d+_(?:val|ind)`?\s+column\s+represents",
        "This metric represents",
        sanitized,
        flags=re.IGNORECASE,
    )
    sanitized = re.sub(r"`?demografy\.[\w.]+`?", "the Demografy dataset", sanitized, flags=re.IGNORECASE)
    sanitized = re.sub(r"`?a_master_view`?", "the Demografy dataset", sanitized, flags=re.IGNORECASE)
    sanitized = re.sub(r"`?kpi_\d+_(?:val|ind)`?", "this metric", sanitized, flags=re.IGNORECASE)
    sanitized = sanitized.replace("BigQuery-backed answers", "live data answers")
    sanitized = re.sub(
        r"(?i)\bcolumn\s+in\s+the\s+database\b",
        "value in the Demografy data",
        sanitized,
    )
    sanitized = re.sub(
        r"(?i)\b(?:the\s+)?database\s+column\b",
        "the published metric",
        sanitized,
    )
    return sanitized


def polish_answer(question: str, answer: str, sql: str | None, rewrite_note: str | None = None) -> str:
    """
    Make backend answers feel conversational in the UI while preserving the data.
    """
    if not answer:
        return "I could not find a result for that query."

    parts = []
    if rewrite_note:
        parts.append(f"_{rewrite_note}_")

    note = _metric_note(sql or "")
    lines = answer.strip().splitlines()
    is_numbered_list = bool(lines and re.match(r"^\d+\.\s+", lines[0]))

    if answer.startswith("No matching") or answer.startswith("No suburbs"):
        parts.append(answer)
        if note:
            parts.append(note)
        return sanitize_user_answer("\n\n".join(parts))

    if is_numbered_list:
        parts.append("Here are the matching SA2 areas from Demografy's dataset:")
        parts.append(answer)
        if note:
            parts.append(note)
        return sanitize_user_answer("\n\n".join(parts))

    if len(lines) == 1:
        parts.append(f"The result is **{answer.strip()}**.")
        if note:
            parts.append(note)
        return sanitize_user_answer("\n\n".join(parts))

    return sanitize_user_answer("\n\n".join([*parts, answer]))
