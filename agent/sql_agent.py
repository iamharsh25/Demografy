"""
LangChain SQL Agent for Demografy Insights Chatbot.
...
"""

import os
import re
from pathlib import Path

from dotenv import load_dotenv

# Load ``.env`` from the Demografy repo root *before* importing LangChain so
# ``LANGCHAIN_TRACING_V2`` / ``LANGCHAIN_API_KEY`` / ``LANGCHAIN_PROJECT``
# are visible when tracing initialises. Using an explicit path also works
# when Streamlit is started from a parent directory (cwd would miss ``.env``).
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from langchain_community.utilities import SQLDatabase
from langchain_community.agent_toolkits import create_sql_agent
from langchain_google_genai import ChatGoogleGenerativeAI
from agent.prompts import FEW_SHOT_PREFIX

# Single source of truth for the "I cannot help with this" copy. Used as the
# empty-answer fallback in ``ask()`` and matched in ``agent.suggestions`` to
# trigger the AI-powered recovery chip prompt.
USER_FACING_UNANSWERABLE_REPLY = (
    "Sorry, I cannot answer this question. I do not have information for that. "
    "Could you try asking another question?"
)

# Module-level agent instance (created once, reused for all questions)
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


def _normalise_question(question: str) -> str:
    return " ".join(question.lower().strip().rstrip("?").split())


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

# Major cities / city phrases → state (follow-ups like "Brisbane", or "in Melbourne" in one line).
# Keys are lowercase phrases matching _normalise_question output.
MAJOR_CITY_TO_STATE: dict[str, str] = {
    "sydney": "New South Wales",
    "newcastle": "New South Wales",
    "wollongong": "New South Wales",
    "melbourne": "Victoria",
    "geelong": "Victoria",
    "ballarat": "Victoria",
    "bendigo": "Victoria",
    "brisbane": "Queensland",
    "gold coast": "Queensland",
    "sunshine coast": "Queensland",
    "townsville": "Queensland",
    "cairns": "Queensland",
    "toowoomba": "Queensland",
    "adelaide": "South Australia",
    "perth": "Western Australia",
    "fremantle": "Western Australia",
    "hobart": "Tasmania",
    "launceston": "Tasmania",
    "canberra": "Australian Capital Territory",
    "darwin": "Northern Territory",
}

RANKABLE_METRICS = [
    {
        "keywords": ("migration", "migration footprint"),
        "column": "kpi_3_val",
        "alias": "migration_footprint",
        "intent": "ranked_percent",
        "order": "DESC",
    },
    {
        "keywords": ("young family", "families"),
        "column": "kpi_10_val",
        "alias": "young_family_presence",
        "intent": "ranked_percent",
        "order": "DESC",
    },
    {
        "keywords": ("prosperity", "prosperity score"),
        "column": "kpi_1_val",
        "alias": "prosperity_score",
        "intent": "ranked_metric",
        "order": "DESC",
    },
    {
        "keywords": ("learning", "education"),
        "column": "kpi_4_val",
        "alias": "learning_level",
        "intent": "ranked_percent",
        "order": "DESC",
    },
    {
        "keywords": ("social housing",),
        "column": "kpi_5_val",
        "alias": "social_housing_percentage",
        "intent": "ranked_percent",
        "order": "DESC",
    },
    {
        "keywords": ("rental access", "affordability", "affordable"),
        "column": "kpi_7_val",
        "alias": "rental_access",
        "intent": "ranked_percent",
        "order": "DESC",
    },
    {
        "keywords": ("home ownership", "resident equity"),
        "column": "kpi_6_val",
        "alias": "resident_equity",
        "intent": "ranked_percent",
        "order": "DESC",
    },
    {
        "keywords": ("resident anchor", "stable", "stability"),
        "column": "kpi_8_val",
        "alias": "resident_anchor",
        "intent": "ranked_percent",
        "order": "DESC",
    },
]


def _extract_limit(text: str, default: int) -> int:
    match = re.search(r"\b(?:top|first)\s+(\d+)\b", text)
    if not match:
        return min(default, 10)
    return max(1, min(int(match.group(1)), 10))


def _extract_number_after(text: str, words: tuple[str, ...], default: float) -> float:
    pattern = rf"(?:{'|'.join(re.escape(word) for word in words)})\D+(\d[\d,]*(?:\.\d+)?)"
    match = re.search(pattern, text)
    return float(match.group(1).replace(",", "")) if match else default


def _extract_state(text: str) -> str | None:
    for alias, state in sorted(STATE_ALIASES.items(), key=lambda item: len(item[0]), reverse=True):
        if re.search(rf"\b{re.escape(alias)}\b", text):
            return state
    # Major cities imply a state (e.g. "diverse suburbs in Brisbane").
    for city, state in sorted(MAJOR_CITY_TO_STATE.items(), key=lambda item: len(item[0]), reverse=True):
        parts = city.split()
        if len(parts) == 1:
            pat = rf"\b{re.escape(parts[0])}\b"
        else:
            pat = r"\s+".join(rf"\b{re.escape(p)}\b" for p in parts)
        if re.search(pat, text):
            return state
    return None


# Shown when a diversity suburb ranking needs a state or city; user can tap or type (e.g. Melbourne).
GEOGRAPHY_CLARIFICATION_CHIPS: tuple[str, ...] = (
    "Victoria",
    "New South Wales",
    "Queensland",
)


def _wants_national_scope(text: str) -> bool:
    return any(
        phrase in text
        for phrase in (
            "australia",
            "australian",
            "nationwide",
            "national",
            "all states",
            "every state",
            "each state",
            "across australia",
            "across the country",
            "whole country",
            "country wide",
            "countrywide",
        )
    )


def _diversity_suburb_list_intent(text: str) -> bool:
    """User wants a list/ranking of diverse suburbs (or areas), not e.g. a single % only."""
    if not ("diversity" in text or "diverse" in text):
        return False
    wants_ranked_list = any(
        w in text
        for w in (
            "top",
            "highest",
            "most",
            "rank",
            "show",
            "find",
            "give",
            "list",
            "tell",
        )
    )
    mentions_suburb = any(w in text for w in ("suburb", "suburbs", "area", "areas", "sa2"))
    return wants_ranked_list or mentions_suburb


def _needs_diversity_geography_clarification(question: str) -> bool:
    """True when the user wants diverse-suburb rankings but gave no state/city."""
    text = _normalise_question(question)
    if _extract_state(text):
        return False
    if _wants_national_scope(text):
        return False
    return _diversity_suburb_list_intent(text)


def _geography_clarification_meta() -> dict:
    return {
        "clarification": True,
        "clarification_chips": list(GEOGRAPHY_CLARIFICATION_CHIPS),
    }


def _residential_filters(include_statistical_categories: bool = True) -> list[str]:
    filters = []
    if include_statistical_categories:
        filters.extend([
            "sa2_name NOT LIKE '%Migratory%'",
            "sa2_name NOT LIKE '%No usual address%'",
            "sa2_name NOT LIKE '%Offshore%'",
        ])
    filters.extend([
        "sa2_name NOT LIKE '%Industrial%'",
        "sa2_name NOT LIKE '%Military%'",
        "population > 100",
    ])
    return filters


def _where_clause(filters: list[str]) -> str:
    return "\n  AND ".join(filters)


def _rankable_metric(text: str) -> dict | None:
    for metric in RANKABLE_METRICS:
        if any(keyword in text for keyword in metric["keywords"]):
            return metric
    return None


def _is_ranking_request(text: str) -> bool:
    return any(word in text for word in ("top", "highest", "most", "show", "find", "rank", "based on"))


def _template_sql_for_question(question: str) -> tuple[str, str] | None:
    text = _normalise_question(question)
    state = _extract_state(text)

    is_diversity_question = "diversity" in text or "diverse" in text

    if is_diversity_question and "percentage" in text and state:
        threshold = _extract_number_after(text, ("above", "over", "greater than"), 0.7)
        filters = [
            f"state = '{state}'",
            "kpi_2_val IS NOT NULL",
            *_residential_filters(),
        ]
        sql = f"""SELECT ROUND(100 * SUM(CASE WHEN kpi_2_val > {threshold:g} THEN 1 ELSE 0 END) / COUNT(*), 2) AS percentage_high_diversity
FROM `demografy.prod_tables.a_master_view`
WHERE {_where_clause(filters)}
LIMIT 1;"""
        return "diversity_percentage", sql

    if is_diversity_question and _diversity_suburb_list_intent(text):
        limit = _extract_limit(text, 3)
        filters: list[str] | None
        if state:
            filters = [
                f"state = '{state}'",
                "kpi_2_val IS NOT NULL",
                *_residential_filters(),
            ]
        elif _wants_national_scope(text):
            filters = ["kpi_2_val IS NOT NULL", *_residential_filters()]
        else:
            # No state/city and not explicitly Australia-wide: ask() asks for geography.
            filters = None
        if filters is not None:
            sql = f"""SELECT sa2_name, state, kpi_2_val AS diversity_index
FROM `demografy.prod_tables.a_master_view`
WHERE {_where_clause(filters)}
ORDER BY kpi_2_val DESC
LIMIT {limit};"""
            return "ranked_metric", sql

    if "average" in text and "prosperity" in text and state:
        sql = f"""SELECT ROUND(AVG(kpi_1_val), 2) AS avg_prosperity_score
FROM `demografy.prod_tables.a_master_view`
WHERE state = '{state}'
  AND kpi_1_val IS NOT NULL
LIMIT 1;"""
        return "single_scalar", sql

    if "state" in text and "highest" in text and ("learning" in text or "education" in text):
        sql = """SELECT state, ROUND(AVG(kpi_4_val), 2) AS avg_learning_level
FROM `demografy.prod_tables.a_master_view`
WHERE kpi_4_val IS NOT NULL
  AND state NOT IN ('Australian Capital Territory', 'Northern Territory', 'Other Territories')
GROUP BY state
ORDER BY avg_learning_level DESC
LIMIT 1;"""
        return "single_name", sql

    if "social housing" in text and any(word in text for word in ("above", "over", ">")):
        threshold = _extract_number_after(text, ("above", "over"), 20)
        filters = [
            "kpi_5_val IS NOT NULL",
            f"kpi_5_val > {threshold:g}",
            *_residential_filters(include_statistical_categories=False),
        ]
        sql = f"""SELECT sa2_name, state, kpi_5_val AS social_housing_percentage
FROM `demografy.prod_tables.a_master_view`
WHERE {_where_clause(filters)}
ORDER BY kpi_5_val DESC
LIMIT 10;"""
        return "ranked_percent", sql

    if ("rental" in text or "affordable" in text) and state:
        limit = _extract_limit(text, 5)
        population = _extract_number_after(text, ("at least", "over", "above", "minimum"), 0)
        filters = [
            f"state = '{state}'",
            "kpi_7_val IS NOT NULL",
            *_residential_filters(include_statistical_categories=True),
        ]
        if population:
            filters.insert(1, f"population >= {int(population)}")
        sql = f"""SELECT sa2_name, state, population, kpi_7_val AS rental_access
FROM `demografy.prod_tables.a_master_view`
WHERE {_where_clause(filters)}
ORDER BY kpi_7_val DESC
LIMIT {limit};"""
        return "rental_access", sql

    if "young family" in text and ("learning" in text or "education" in text):
        family_threshold = _extract_number_after(text, ("family presence", "young family", "over"), 25)
        learning_match = re.search(r"learning level\D+(\d+(?:\.\d+)?)", text)
        learning_threshold = float(learning_match.group(1)) if learning_match else 70
        filters = [
            "kpi_10_val IS NOT NULL",
            "kpi_4_val IS NOT NULL",
            f"kpi_10_val > {family_threshold:g}",
            f"kpi_4_val > {learning_threshold:g}",
            *_residential_filters(),
        ]
        sql = f"""SELECT sa2_name, state, kpi_10_val AS young_family_presence, kpi_4_val AS learning_level
FROM `demografy.prod_tables.a_master_view`
WHERE {_where_clause(filters)}
ORDER BY kpi_10_val DESC, kpi_4_val DESC
LIMIT 10;"""
        return "young_family_learning", sql

    if ("stable" in text or "resident anchor" in text) and state:
        limit = _extract_limit(text, 1)
        filters = [
            f"state = '{state}'",
            "kpi_8_val IS NOT NULL",
            *_residential_filters(),
        ]
        sql = f"""SELECT sa2_name, state, kpi_8_val AS resident_anchor
FROM `demografy.prod_tables.a_master_view`
WHERE {_where_clause(filters)}
ORDER BY kpi_8_val DESC
LIMIT {limit};"""
        return "ranked_percent", sql

    if "compare" in text and ("home ownership" in text or "resident equity" in text) and "rental access" in text:
        sql = """SELECT state, ROUND(AVG(kpi_6_val), 2) AS avg_resident_equity, ROUND(AVG(kpi_7_val), 2) AS avg_rental_access
FROM `demografy.prod_tables.a_master_view`
WHERE kpi_6_val IS NOT NULL
  AND kpi_7_val IS NOT NULL
GROUP BY state
ORDER BY avg_resident_equity DESC
LIMIT 10;"""
        return "state_comparison", sql

    if "migration" in text and state and any(word in text for word in ("top", "highest", "most")):
        limit = _extract_limit(text, 5)
        filters = [
            f"state = '{state}'",
            "kpi_3_val IS NOT NULL",
            *_residential_filters(include_statistical_categories=False),
        ]
        sql = f"""SELECT sa2_name, state, kpi_3_val AS migration_footprint
FROM `demografy.prod_tables.a_master_view`
WHERE {_where_clause(filters)}
ORDER BY kpi_3_val DESC
LIMIT {limit};"""
        return "ranked_percent", sql

    metric = _rankable_metric(text)
    if metric and _is_ranking_request(text):
        limit = _extract_limit(text, 10)
        order = "ASC" if "lowest" in text or "least" in text else metric["order"]
        filters = [
            f"{metric['column']} IS NOT NULL",
            *_residential_filters(include_statistical_categories=True),
        ]
        if state:
            filters.insert(0, f"state = '{state}'")

        sql = f"""SELECT sa2_name, state, {metric['column']} AS {metric['alias']}
FROM `demografy.prod_tables.a_master_view`
WHERE {_where_clause(filters)}
ORDER BY {metric['column']} {order}
LIMIT {limit};"""
        return metric["intent"], sql

    return None


def _extract_sql_from_intermediate_steps(result: dict) -> str | None:
    """
    Pull the executed SQL from LangChain's structured agent steps.

    Scraping verbose stdout is brittle because SQL commonly contains quoted
    strings like 'Australian Capital Territory'. The returned intermediate
    steps keep the tool input structured, so prefer those whenever available.
    """
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
    """Fallback SQL extraction for older LangChain verbose output formats."""
    import ast
    import re

    # Prefer a complete Python dict-like tool payload over quote-based regex.
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
    """Remove SQL/debug blocks AND inline DB identifiers before showing users.

    Defence-in-depth: even if the prompt slips and the LLM mentions a column
    or table name, the user should never see it. We strip in this order:
      1. Marker/fenced SQL blocks (largest noise first).
      2. Lines that read like raw SQL (start with SELECT/WHERE/etc.).
      3. Inline schema/column/table tokens that occasionally surface in
         explanatory prose (e.g. "Diversity index (kpi_2_val) shown...").
      4. Whitespace tidy so removals don't leave dangling parens or "  ".
    """
    import re

    text = (answer or "").strip()
    if not text:
        return text

    # Remove explicit marker blocks first.
    text = re.sub(
        r"===SQL_START===.*?===SQL_END===",
        "",
        text,
        flags=re.DOTALL | re.IGNORECASE,
    )

    # Remove fenced SQL blocks.
    text = re.sub(r"```sql.*?```", "", text, flags=re.DOTALL | re.IGNORECASE)

    # Remove raw SQL line noise that occasionally leaks.
    sqlish = re.compile(
        r"^\s*(SELECT|WITH|FROM|WHERE|JOIN|LEFT JOIN|RIGHT JOIN|INNER JOIN|"
        r"ORDER BY|GROUP BY|LIMIT|HAVING|UNION|INSERT|UPDATE|DELETE|CREATE|DROP)\b",
        flags=re.IGNORECASE,
    )
    kept_lines = []
    for line in text.splitlines():
        if sqlish.match(line):
            continue
        if line.strip().startswith("SQL Query:"):
            continue
        kept_lines.append(line)

    text = "\n".join(kept_lines)

    # Strip inline schema/table references (with or without backticks).
    text = re.sub(
        r"`?demografy\.(?:prod_tables|ref_tables)\.[a-z_0-9]+`?",
        "",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(r"`?\ba_master_view\b`?", "", text, flags=re.IGNORECASE)
    text = re.sub(r"`?\bdev_customers\b`?", "", text, flags=re.IGNORECASE)

    # Strip parenthetical column refs first so we cleanly remove the
    # surrounding "()" instead of leaving "()" behind:
    #   "Diversity index (kpi_2_val) shown..." -> "Diversity index shown..."
    text = re.sub(
        r"\s*\(\s*(?:kpi_\d+_(?:val|ind)|sa2_(?:name|code)|sa[34]_name)\s*\)",
        "",
        text,
        flags=re.IGNORECASE,
    )

    # Strip bare inline column tokens.
    text = re.sub(
        r"\b(?:kpi_\d+_(?:val|ind)|sa2_(?:name|code)|sa[34]_name)\b",
        "",
        text,
        flags=re.IGNORECASE,
    )

    # Tidy artifacts left over from removals.
    text = re.sub(r"\(\s*\)", "", text)            # empty parens
    text = re.sub(r"`\s*`", "", text)              # empty backticks
    text = re.sub(r"[ \t]+([,.;:%])", r"\1", text)  # space before punctuation
    text = re.sub(r"[ \t]{2,}", " ", text)         # collapse runs of spaces
    text = re.sub(r" +\n", "\n", text)             # trailing space on lines
    text = re.sub(r"\n{3,}", "\n\n", text)         # excessive blank lines

    return text.strip()


def _rows_from_dataframe(df):
    if df is None or df.empty:
        return []
    return [tuple(row) for row in df.itertuples(index=False, name=None)]


def _fmt_number(value, suffix: str = "") -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return f"{value}{suffix}"

    text = f"{number:.2f}".rstrip("0").rstrip(".")
    return f"{text}{suffix}"


def _geo_phrase(state: str | None) -> str:
    return f" in {state}" if state else ""


def _template_lead_in(intent: str, rows: list, question: str, state: str | None) -> str:
    """One-sentence opener naming metric and geography (user-facing only)."""
    q = (question or "").lower()
    geo = _geo_phrase(state)
    n = len(rows) if rows else _extract_limit(_normalise_question(question), 3)

    if intent == "single_scalar":
        if "prosperity" in q:
            return f"Average prosperity score{geo}:"
        return f"Result for your query{geo}:"

    if intent == "single_name":
        return "The top state for this measure is:"

    if intent == "diversity_percentage":
        return f"Share of suburbs with high diversity{geo}:"

    if intent == "state_comparison":
        return "Home ownership and rental access by state:"

    if intent == "young_family_learning":
        return f"Suburbs with strong young family presence and learning level{geo}:"

    if intent == "rental_access":
        return f"Most affordable rental access suburbs{geo}:"

    if intent == "ranked_metric":
        if "diversity" in q or "diverse" in q:
            return f"Here are the top {n} most diverse suburbs{geo}:"
        if "prosperity" in q:
            return f"Here are the top {n} suburbs by prosperity score{geo}:"
        return f"Here are the top {n} ranked results{geo}:"

    if intent == "ranked_percent":
        if "migration" in q:
            return f"Here are the top {n} suburbs by migration footprint{geo}:"
        if "learning" in q or "education" in q:
            return f"Here are the top {n} suburbs by learning level{geo}:"
        if "social housing" in q:
            return f"Suburbs with the highest social housing share{geo}:"
        if "young family" in q or "families" in q:
            return f"Suburbs with the highest young family presence{geo}:"
        if "home ownership" in q or "resident equity" in q:
            return f"Suburbs by home ownership{geo}:"
        if "resident anchor" in q or "stable" in q or "stability" in q:
            return f"Most stable suburbs by resident anchor{geo}:"
        return f"Here are the top {n} results{geo}:"

    return f"Results for your question{geo}:"


def _format_template_answer(
    intent: str,
    rows: list,
    *,
    question: str,
    state: str | None,
) -> str:
    lead = _template_lead_in(intent, rows, question, state)

    if not rows:
        if intent == "young_family_learning":
            body = "No suburbs match both criteria."
        else:
            body = "No matching suburbs found for this query."
        return f"{lead}\n\n{body}"

    if intent == "single_scalar":
        body = _fmt_number(rows[0][0])
        return f"{lead}\n\n{body}"

    if intent == "single_name":
        body = str(rows[0][0])
        return f"{lead}\n\n{body}"

    if intent == "diversity_percentage":
        body = _fmt_number(rows[0][0], "%")
        return f"{lead}\n\n{body}"

    if intent == "state_comparison":
        body = "\n".join(
            f"{i}. {row[0]}: home ownership {_fmt_number(row[1], '%')}, rental access {_fmt_number(row[2], '%')}"
            for i, row in enumerate(rows, start=1)
        )
        return f"{lead}\n\n{body}"

    if intent == "young_family_learning":
        body = "\n".join(
            f"{i}. {row[0]}: young family {_fmt_number(row[2], '%')}, learning level {_fmt_number(row[3], '%')}"
            for i, row in enumerate(rows, start=1)
        )
        return f"{lead}\n\n{body}"

    value_index = 3 if intent == "rental_access" else 2
    suffix = "" if intent == "ranked_metric" else "%"

    body = "\n".join(
        f"{i}. {row[0]}: {_fmt_number(row[value_index], suffix)}"
        for i, row in enumerate(rows, start=1)
    )
    return f"{lead}\n\n{body}"


def _template_meta(intent: str, sql: str, rows: list, question: str, state: str | None) -> dict:
    """Serializable-ish dict for charting and session cache (rows are tuples)."""
    return {
        "intent": intent,
        "sql": sql,
        "rows": rows,
        "question": question,
        "state": state,
    }


def _answer_template_question(question: str) -> tuple[str, str, dict] | None:
    template = _template_sql_for_question(question)
    if not template:
        return None

    intent, sql = template
    text_norm = _normalise_question(question)
    state = _extract_state(text_norm)
    from db.bigquery_client import run_query

    rows = _rows_from_dataframe(run_query(sql))
    answer = _format_template_answer(intent, rows, question=question, state=state)
    meta = _template_meta(intent, sql, rows, question, state)
    return answer, sql, meta


# Words that commonly wrap a state in a follow-up question and should be
# stripped before deciding "is this just a state name?".
_FOLLOWUP_FILLERS = frozenset({
    "what", "about", "and", "now", "how", "for", "the", "please", "tell",
    "me", "also", "then", "so", "ok", "okay", "hey", "plus", "again", "in",
    "of", "to", "from", "on", "show",
})


def _detect_state_only_followup(text: str) -> str | None:
    """Return the canonical Australian state/territory if ``text`` is only geography.

    Matches state names and aliases ("NSW", "Queensland", "Tas") and short
    major-city picks ("Brisbane", "Melbourne") that imply a single state.
    Returns None when the line looks like a full question (many tokens) so we
    do not short-circuit real queries.
    """
    if not text:
        return None
    normalized = text.lower().strip()
    if not normalized or len(normalized.split()) > 6:
        return None
    cleaned = re.sub(r"[^a-z0-9\s]", " ", normalized)
    tokens = [tok for tok in cleaned.split() if tok and tok not in _FOLLOWUP_FILLERS]
    if not tokens:
        return None
    residue = " ".join(tokens).strip()
    st = STATE_ALIASES.get(residue)
    if st:
        return st
    return MAJOR_CITY_TO_STATE.get(residue)


def _template_followup_answer(
    history: list[dict] | None,
    new_state: str,
) -> tuple[str, str, dict] | None:
    """Reuse a prior templatable user turn with the state swapped.

    Walks history newest-to-oldest; for each user turn we either swap the
    existing state alias for ``new_state`` (if one is mentioned) or append
    "in <new_state>". The first rewrite that the deterministic template
    matcher can answer wins. Returns None when no prior turn is templatable
    so the caller can fall back to the LLM with full context.
    """
    if not history:
        return None
    aliases = sorted(STATE_ALIASES.keys(), key=len, reverse=True)
    for turn in reversed(history):
        if turn.get("role") != "user":
            continue
        prev = (turn.get("content") or "").strip()
        if not prev:
            continue
        # Skip lines that are only a state or city follow-up (e.g. "Brisbane",
        # "Queensland"); the substantive question is further back in history.
        if _detect_state_only_followup(prev) is not None:
            continue

        rewritten = prev
        replaced = False
        for alias in aliases:
            pattern = re.compile(rf"\b{re.escape(alias)}\b", flags=re.IGNORECASE)
            if pattern.search(rewritten):
                rewritten = pattern.sub(new_state, rewritten, count=1)
                replaced = True
                break
        if not replaced:
            rewritten = f"{prev.rstrip('?').rstrip()} in {new_state}"

        templated = _answer_template_question(rewritten)
        if templated:
            return templated
    return None


def _create_agent():
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash-lite",
        google_api_key=os.getenv("GEMINI_API_KEY"),
        temperature=0,
    )

    agent = create_sql_agent(
        llm=llm,
        db=_get_db(),
        agent_type="openai-tools",
        prefix=FEW_SHOT_PREFIX,
        verbose=True,
        max_iterations=10,
        return_intermediate_steps=True,
    )

    return agent


def ask(
    question: str,
    callbacks=None,
    history: list[dict] | None = None,
) -> tuple[str, str | None, dict | None]:
    """Answer a user question, optionally using prior chat history for context.

    ``history`` is a list of ``{"role": "user"|"assistant", "content": str}``
    records (most-recent-last). When provided, a short transcript is
    prepended to the agent input so follow-ups like "diversity" can resolve
    against the previous turn. Template fast-path answers ignore history
    since they're keyword-matched and don't benefit from context.

    Returns ``(answer, sql, meta)``. ``meta`` is set for templated answers
    (intent, rows, question, state) for charting; may include
    ``clarification`` + ``clarification_chips`` when geography is required;
    ``None`` for LLM answers.
    """
    global _agent

    template_answer = _answer_template_question(question)
    if template_answer:
        ans, sql, meta = template_answer
        return ans, sql, meta

    # Deterministic state-swap follow-up: "what about NSW?", "and Queensland?",
    # etc. We rewrite the most recent templatable user turn with the new state
    # and re-run the template matcher. Bypasses the LLM, so the answer is
    # identical in shape and reliability to the original templated reply.
    new_state = _detect_state_only_followup(question)
    if new_state and history:
        followup = _template_followup_answer(history, new_state)
        if followup:
            ans, sql, meta = followup
            return ans, sql, meta

    if _needs_diversity_geography_clarification(question):
        clarify = (
            "I can list the most diverse suburbs, but I need a state or city to narrow the results. "
            "Pick one of the suggestions below, or type a place name (for example Melbourne or NSW)."
        )
        return clarify, None, _geography_clarification_meta()

    if _agent is None:
        _agent = _create_agent()

    # Build the agent input. Plain question when there's no prior context;
    # otherwise prefix a "Previous conversation" block so the LLM can
    # interpret follow-up questions correctly.
    agent_input = question
    if history:
        # Local import to avoid a hard dependency for non-Streamlit callers.
        from chat_history.context import build_context_block

        context_block = build_context_block(history)
        if context_block:
            agent_input = f"{context_block}Current question: {question}"

    # Capture verbose output to extract SQL
    import io
    from contextlib import redirect_stdout, redirect_stderr

    captured_output = io.StringIO()

    with redirect_stdout(captured_output), redirect_stderr(captured_output):
        result = _agent.invoke({"input": agent_input}, config={"callbacks": callbacks or []})

    # Extract SQL from structured agent metadata first, then fallback to logs.
    output_text = captured_output.getvalue()
    sql_query = _extract_sql_from_intermediate_steps(result) or _extract_sql_from_text(output_text)

    # Server-side debugging: log the SQL (do NOT expose in UI)
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
