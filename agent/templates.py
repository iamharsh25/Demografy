"""Deterministic SQL template engine, formatters, and conversational follow-up resolvers."""

from __future__ import annotations

import re
from typing import Optional

from agent.guardrails import (
    _mentions_learning,
    _mentions_prosperity,
    _short_metric_explanation,
)
from agent.kpis import (
    DEFAULT_LIMIT,
    GEOGRAPHY_CLARIFICATION_CHIPS,
    MAJOR_CITY_TO_STATE,
    RANKABLE_METRICS,
    STATE_ABBREVIATIONS,
    STATE_ALIASES,
    _AFFIRMATIVE_FOLLOWUPS,
    _FOLLOWUP_FILLERS,
    _PLACE_TAIL_BLACKLIST,
)

_SINGLE_AREA_TOPN_RE = re.compile(r"\btop\s+\d+\b")


def _prior_limit_from_sql(sql: str | None) -> int | None:
    if not sql:
        return None
    m = re.search(r"\bLIMIT\s+(\d+)\b", sql, flags=re.IGNORECASE)
    return int(m.group(1)) if m else None


def _prior_turn_was_learning_ranking(context_meta: dict | None, history: list[dict] | None) -> bool:
    """True when the last answer was a learning-level (kpi_4) suburb ranking."""
    sql = (context_meta or {}).get("sql") or ""
    sl = sql.lower()
    if "kpi_4_val" in sl or "learning_level" in sl:
        return True
    if not history:
        return False
    for rec in reversed(history[-6:]):
        if rec.get("role") != "assistant":
            continue
        c = (rec.get("content") or "").lower()
        if "learning level" in c or "schooling" in c or ("education" in c and "suburb" in c):
            return True
    return False


def _extract_major_city_token(text: str) -> str | None:
    t = _normalise_question(text)
    for city in sorted(MAJOR_CITY_TO_STATE.keys(), key=len, reverse=True):
        if re.search(rf"\b{re.escape(city)}\b", t):
            return city
    return None


def _rewrite_learning_geography_followup(
    question: str,
    context_meta: dict | None,
    history: list[dict] | None,
) -> str | None:
    """Turn 'top 5 for Melbourne' / 'what about NSW?' into an explicit learning query.

    Short geography-only follow-ups omit metric words, so templates and
    ``_contextual_metric_followup_question`` skip them; the LLM can then
    return an empty answer. Rewriting restores the prior metric from context.
    """
    if not _prior_turn_was_learning_ranking(context_meta, history):
        return None
    text = _normalise_question(question)
    if _mentions_learning(text):
        return None
    if len(text.split()) > 16:
        return None

    prior_sql = (context_meta or {}).get("sql") or ""
    limit = _prior_limit_from_sql(prior_sql) or _extract_limit(text, DEFAULT_LIMIT)

    city = _extract_major_city_token(text)
    if city:
        return f"Top {limit} suburbs by learning level in {city.title()}"

    st = _extract_state(text)
    if st:
        return f"Top {limit} suburbs by learning level in {st}"

    if any(tok in text.split() for tok in ("nsw", "vic", "qld", "sa", "wa", "tas", "act", "nt")):
        st2 = _extract_state(text)
        if st2:
            return f"Top {limit} suburbs by learning level in {st2}"
    return None


# --- Pairwise state average (e.g. "compare between both" after Vic + NSW) ---

KPI_AVG_PAIR_SPECS: dict[str, dict[str, str]] = {
    "kpi_1_val": {"column": "kpi_1_val", "label": "prosperity score", "alias": "avg_value", "fmt": "index"},
    "kpi_2_val": {"column": "kpi_2_val", "label": "diversity index", "alias": "avg_value", "fmt": "diversity"},
    "kpi_3_val": {"column": "kpi_3_val", "label": "migration footprint", "alias": "avg_value", "fmt": "pct"},
    "kpi_4_val": {"column": "kpi_4_val", "label": "learning level", "alias": "avg_value", "fmt": "pct"},
    "kpi_5_val": {"column": "kpi_5_val", "label": "social housing", "alias": "avg_value", "fmt": "pct"},
    "kpi_6_val": {"column": "kpi_6_val", "label": "home ownership", "alias": "avg_value", "fmt": "pct"},
    "kpi_7_val": {"column": "kpi_7_val", "label": "rental access", "alias": "avg_value", "fmt": "pct"},
    "kpi_8_val": {"column": "kpi_8_val", "label": "resident anchor", "alias": "avg_value", "fmt": "pct"},
    "kpi_9_val": {"column": "kpi_9_val", "label": "household mobility", "alias": "avg_value", "fmt": "decimal"},
    "kpi_10_val": {"column": "kpi_10_val", "label": "young family presence", "alias": "avg_value", "fmt": "pct"},
}


def _first_kpi_val_column_in_sql(sql: str | None) -> str | None:
    if not sql:
        return None
    found = re.findall(r"\b(kpi_\d+_val)\b", sql, flags=re.IGNORECASE)
    return found[0].lower() if found else None


def _extract_states_ordered_in_text(text: str) -> list[str]:
    """Full state names in left-to-right order (aliases and major cities)."""
    t = _normalise_question(text)
    hits: list[tuple[int, str]] = []
    for alias, full in STATE_ALIASES.items():
        for m in re.finditer(rf"\b{re.escape(alias)}\b", t, flags=re.IGNORECASE):
            hits.append((m.start(), full))
    for city, full in MAJOR_CITY_TO_STATE.items():
        for m in re.finditer(rf"\b{re.escape(city)}\b", t, flags=re.IGNORECASE):
            hits.append((m.start(), full))
    hits.sort(key=lambda x: x[0])
    out: list[str] = []
    for _, st in hits:
        if st not in out:
            out.append(st)
    return out


def _chronological_unique_states_from_user_history(history: list[dict] | None) -> list[str]:
    """States / city metros mentioned in user turns, in order (last mention wins position)."""
    if not history:
        return []
    out: list[str] = []
    for rec in history:
        if rec.get("role") != "user":
            continue
        content = (rec.get("content") or "")
        t = _normalise_question(content)
        st = _extract_state(t)
        added: str | None = None
        if st:
            added = st
        else:
            for city, full in sorted(MAJOR_CITY_TO_STATE.items(), key=lambda x: len(x[0]), reverse=True):
                if re.search(rf"\b{re.escape(city)}\b", t, flags=re.IGNORECASE):
                    added = full
                    break
        if added:
            if added in out:
                out.remove(added)
            out.append(added)
    return out


def _states_pair_for_compare(text: str, history: list[dict] | None) -> tuple[str, str] | None:
    text_states = _extract_states_ordered_in_text(text)
    if len(text_states) >= 2:
        return (text_states[-2], text_states[-1])
    hist = _chronological_unique_states_from_user_history(history)
    if len(hist) >= 2:
        return (hist[-2], hist[-1])
    return None


def _is_pairwise_comparison_followup(text: str) -> bool:
    """Short / deictic comparison that often omits metric and state names."""
    t = _normalise_question(text)
    if "home ownership" in t and "rental access" in t:
        return False
    has_cmp = any(w in t for w in ("compare", "comparison", "versus")) or " vs " in t
    has_diff = "difference" in t and "between" in t
    if not has_cmp and not has_diff:
        return False
    if len(_extract_states_ordered_in_text(t)) >= 2:
        return True
    deictic = (
        "between both",
        "compare both",
        "the two",
        "these two",
        "those two",
        "each other",
        "two states",
    )
    if any(d in t for d in deictic):
        return True
    if " both" in f" {t} " or t.startswith("both ") or " both?" in f" {t}":
        if "compare" in t or "difference" in t or "versus" in t or " vs " in t:
            return True
    if has_diff and len(t.split()) <= 12:
        return True
    return False


def _metric_spec_for_explicit_pair_question(text: str) -> dict[str, str] | None:
    """Resolve KPI for explicit two-state average wording (diversity is not in RANKABLE_METRICS)."""
    if "diversity" in text or "diverse" in text:
        return KPI_AVG_PAIR_SPECS["kpi_2_val"]
    m = _rankable_metric(text)
    if m:
        return KPI_AVG_PAIR_SPECS.get(m["column"])
    if "social housing" in text:
        return KPI_AVG_PAIR_SPECS["kpi_5_val"]
    if "rental access" in text or re.search(r"\brental\b", text):
        return KPI_AVG_PAIR_SPECS["kpi_7_val"]
    if _mentions_prosperity(text):
        return KPI_AVG_PAIR_SPECS["kpi_1_val"]
    if _mentions_learning(text):
        return KPI_AVG_PAIR_SPECS["kpi_4_val"]
    if "home ownership" in text or "resident equity" in text:
        return KPI_AVG_PAIR_SPECS["kpi_6_val"]
    return None


def _is_explicit_two_state_avg_comparison(text: str) -> bool:
    """True for standalone compare / vs / which-is-higher between two named states."""
    if "home ownership" in text and "rental access" in text:
        return False
    if "compare" in text or "comparison" in text:
        return True
    if re.search(r"\bvs\.?\b", text):
        return True
    if " versus " in f" {text} ":
        return True
    if any(
        p in text
        for p in (
            "which is higher",
            "which has higher",
            "which is lower",
            "which has lower",
        )
    ):
        return True
    if "difference" in text and "between" in text:
        return True
    return False


def _metric_spec_for_pair_compare(
    question: str,
    context_meta: dict | None,
    history: list[dict] | None,
) -> dict[str, str] | None:
    """Pick KPI column: explicit words in question > prior SQL > assistant wording."""
    t = _normalise_question(question)
    explicit = _metric_spec_for_explicit_pair_question(t)
    if explicit:
        return explicit
    sql = (context_meta or {}).get("sql") or ""
    col = _first_kpi_val_column_in_sql(sql)
    if col and col in KPI_AVG_PAIR_SPECS:
        return KPI_AVG_PAIR_SPECS[col]
    if not history:
        return KPI_AVG_PAIR_SPECS.get("kpi_4_val")
    for rec in reversed(history[-6:]):
        if rec.get("role") != "assistant":
            continue
        c = (rec.get("content") or "").lower()
        if "prosperity" in c or "socioeconomic" in c:
            return KPI_AVG_PAIR_SPECS["kpi_1_val"]
        if "diversity" in c or "diverse" in c:
            return KPI_AVG_PAIR_SPECS["kpi_2_val"]
        if "migration" in c:
            return KPI_AVG_PAIR_SPECS["kpi_3_val"]
        if "learning level" in c or ("education" in c and "suburb" in c) or "schooling" in c:
            return KPI_AVG_PAIR_SPECS["kpi_4_val"]
        if "young family" in c:
            return KPI_AVG_PAIR_SPECS["kpi_10_val"]
        if "rental access" in c or "affordab" in c:
            return KPI_AVG_PAIR_SPECS["kpi_7_val"]
        if "home ownership" in c or "resident equity" in c:
            return KPI_AVG_PAIR_SPECS["kpi_6_val"]
    return KPI_AVG_PAIR_SPECS.get("kpi_4_val")


def _sql_two_state_average(column: str, alias: str, s1: str, s2: str) -> str:
    e1 = str(s1).replace("'", "''")
    e2 = str(s2).replace("'", "''")
    return f"""SELECT state, ROUND(AVG({column}), 4) AS {alias}
FROM `demografy.prod_tables.a_master_view`
WHERE state IN ('{e1}', '{e2}')
  AND {column} IS NOT NULL
  AND sa2_name NOT LIKE '%Migratory%'
  AND sa2_name NOT LIKE '%No usual address%'
  AND sa2_name NOT LIKE '%Offshore%'
  AND sa2_name NOT LIKE '%Industrial%'
  AND sa2_name NOT LIKE '%Military%'
  AND population > 100
GROUP BY state
ORDER BY {alias} DESC
LIMIT 2;"""


def _format_pair_state_avg_cell(spec: dict[str, str], val: object) -> str:
    fmt = spec.get("fmt") or "pct"
    if fmt == "pct":
        return _fmt_number(val, "%")
    if fmt == "diversity":
        try:
            return f"{float(val):.4f}".rstrip("0").rstrip(".")
        except (TypeError, ValueError):
            return str(val)
    if fmt == "decimal":
        try:
            return f"{float(val):.2f}"
        except (TypeError, ValueError):
            return str(val)
    return _fmt_number(val, "")


def _answer_pair_state_avg_compare_from_context(
    question: str,
    context_meta: dict | None,
    history: list[dict] | None,
) -> tuple[str, str, dict] | None:
    """Resolve vague two-way comparisons using recent geography + inferred metric."""
    text = _normalise_question(question)
    if not _is_pairwise_comparison_followup(text):
        return None
    pair = _states_pair_for_compare(text, history)
    if not pair:
        return None
    s1, s2 = pair
    spec = _metric_spec_for_pair_compare(question, context_meta, history)
    if not spec:
        return None
    col = spec["column"]
    sql = _sql_two_state_average(col, spec["alias"], s1, s2)
    from db.bigquery_client import run_query

    rows = _rows_from_dataframe(run_query(sql))
    display_q = f"Compare average {spec['label']} between {s1} and {s2}"
    lead = _template_lead_in("pair_state_avg", rows, display_q, None)
    if not rows:
        empty_meta = _template_meta("pair_state_avg", sql, rows, display_q, None)
        empty_meta.update({"metric_label": spec["label"], "pair_states": [s1, s2], "kpi_column": col})
        return f"{lead}\n\nNo aggregate values found for those states.", sql, empty_meta
    body = "\n".join(
        f"{i}. {row[0]}: {_format_pair_state_avg_cell(spec, row[1])}"
        for i, row in enumerate(rows, start=1)
    )
    answer = f"{lead}\n\n{body}"
    meta = {
        "intent": "pair_state_avg",
        "sql": sql,
        "rows": rows,
        "question": display_q,
        "state": None,
        "metric_label": spec["label"],
        "pair_states": [s1, s2],
        "kpi_column": col,
    }
    return answer, sql, meta


# ---------------------------------------------------------------------------
# Text normalisation and extraction
# ---------------------------------------------------------------------------

def _normalise_question(question: str) -> str:
    return " ".join(question.lower().strip().rstrip("?").split())


_WORD_TO_NUM = {
    "twenty five": 25, "twenty-five": 25,
    "twenty": 20, "nineteen": 19, "eighteen": 18, "seventeen": 17, "sixteen": 16,
    "fifteen": 15, "fourteen": 14, "thirteen": 13, "twelve": 12, "eleven": 11,
    "ten": 10, "nine": 9, "eight": 8, "seven": 7, "six": 6,
    "five": 5, "four": 4, "three": 3, "two": 2, "one": 1,
}


def _extract_limit(text: str, default: int) -> int:
    match = re.search(r"\b(?:top|first)\s+(\d+)\b", text)
    if match:
        return max(1, min(int(match.group(1)), 25))
    for word, n in _WORD_TO_NUM.items():
        if re.search(rf"\b(?:top|first)\s+{re.escape(word)}\b", text):
            return max(1, min(n, 25))
    return default


def _extract_number_after(text: str, words: tuple[str, ...], default: float) -> float:
    pattern = rf"(?:{'|'.join(re.escape(w) for w in words)})\D+(\d[\d,]*(?:\.\d+)?)"
    match = re.search(pattern, text)
    return float(match.group(1).replace(",", "")) if match else default


def _has_explicit_number_near(text: str, words: tuple[str, ...]) -> bool:
    pattern = rf"(?:{'|'.join(re.escape(w) for w in words)})\D+(\d[\d,]*(?:\.\d+)?)"
    return bool(re.search(pattern, text))


def _extract_state(text: str) -> str | None:
    for alias, state in sorted(STATE_ALIASES.items(), key=lambda item: len(item[0]), reverse=True):
        if re.search(rf"\b{re.escape(alias)}\b", text):
            return state
    for city, state in sorted(MAJOR_CITY_TO_STATE.items(), key=lambda item: len(item[0]), reverse=True):
        parts = city.split()
        if len(parts) == 1:
            pat = rf"\b{re.escape(parts[0])}\b"
        else:
            pat = r"\s+".join(rf"\b{re.escape(p)}\b" for p in parts)
        if re.search(pat, text):
            return state
    return None


def _wants_national_scope(text: str) -> bool:
    return any(
        phrase in text
        for phrase in (
            "australia", "australian", "nationwide", "national", "all states",
            "every state", "each state", "across australia", "across the country",
            "whole country", "country wide", "countrywide",
        )
    )


_STATE_LEVEL_RE = re.compile(
    r"\b(?:australian\s+)?states?\b|\bby\s+state\b|\bper\s+state\b|\beach\s+state\b",
    re.IGNORECASE,
)


_EACH_STATE_AVG_RE = re.compile(
    r"\b(?:for\s+)?each\s+state\b|\bevery\s+state\b|\ball\s+states\b|"
    r"\bper\s+state\b|\bby\s+state\b|\bach\s+state\b",
    re.IGNORECASE,
)


def _each_state_average_learning_aggregate_intent(text: str) -> bool:
    """AVG learning/education grouped by state (not a suburb top-N list)."""
    if not _mentions_learning(text):
        return False
    if any(w in text for w in ("suburb", "suburbs", "sa2")):
        return False
    if not ("average" in text or "avg" in text or "mean" in text):
        return False
    return bool(_EACH_STATE_AVG_RE.search(text))


def _best_suburb_in_top_learning_state_intent(text: str) -> bool:
    """Best SA2 for learning in the state with the highest average learning (colloquial phrasing)."""
    if "suburb" not in text:
        return False
    if _extract_state(text):
        return False
    learning_ok = _mentions_learning(text) or bool(
        re.search(r"\btop\s+state\b", text) and ("best" in text or "top" in text)
    )
    if not learning_ok:
        return False
    if any(
        p in text
        for p in (
            "highest average",
            "best state",
            "leading state",
            "which state has the highest",
            "state with the highest",
        )
    ):
        return True
    if re.search(r"\btop\s+state\b.*\bsuburb", text):
        return True
    return False


def _state_level_diversity_average_rank_intent(text: str) -> bool:
    """User wants states ranked by average diversity (SA2 aggregate), not a suburb list."""
    if "diversity" not in text and "diverse" not in text:
        return False
    if any(w in text for w in ("suburb", "suburbs", "sa2")):
        return False
    if not _STATE_LEVEL_RE.search(text):
        return False
    if "average" in text or "avg" in text or "mean" in text:
        return True
    if "which" in text and any(w in text for w in ("highest", "most", "lowest", "least")):
        return True
    if (
        "what" in text
        and _STATE_LEVEL_RE.search(text)
        and any(w in text for w in ("highest", "most", "lowest", "least"))
    ):
        return True
    return False


def _diversity_suburb_list_intent(text: str) -> bool:
    if not ("diversity" in text or "diverse" in text):
        return False
    wants_ranked_list = any(
        w in text for w in ("top", "highest", "most", "rank", "show", "find", "give", "list", "tell")
    )
    mentions_suburb = any(w in text for w in ("suburb", "suburbs", "area", "areas", "sa2"))
    return wants_ranked_list or mentions_suburb


def _needs_diversity_geography_clarification(question: str) -> bool:
    text = _normalise_question(question)
    if _extract_state(text):
        return False
    if _wants_national_scope(text):
        return False
    return _diversity_suburb_list_intent(text)


def _geography_clarification_meta() -> dict:
    return {"clarification": True, "clarification_chips": list(GEOGRAPHY_CLARIFICATION_CHIPS)}


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
    return any(
        word in text
        for word in (
            "top", "highest", "high", "most", "least", "lowest", "low", "show",
            "find", "rank", "based on", "list", "give", "tell", "best", "good",
            "strong", "leading", "suburb", "suburbs", "area", "areas",
        )
    )


def _ranking_order(text: str, default: str = "DESC") -> str:
    low_patterns = (r"\blow\b", r"\blower\b", r"\blowest\b", r"\bleast\b", r"\bbottom\b", r"\bfewest\b", r"\bsmallest\b")
    high_patterns = (r"\bhigh\b", r"\bhigher\b", r"\bhighest\b", r"\bmost\b", r"\btop\b", r"\bbest\b", r"\bstrong\b", r"\bstrongest\b")
    if any(re.search(p, text) for p in low_patterns):
        return "ASC"
    if any(re.search(p, text) for p in high_patterns):
        return "DESC"
    return default


def _home_ownership_state_average_intent(text: str) -> bool:
    if "home ownership" not in text and "resident equity" not in text:
        return False
    if any(w in text for w in ("suburb", "suburbs", "sa2", "sa3", "sa4")):
        return False
    if any(phrase in text for phrase in ("all ", "every ", "each ", "full list")):
        return False
    if _is_ranking_request(text):
        return False
    return True


def _extract_trailing_place_name(text: str) -> str | None:
    text = text.strip().rstrip("?").strip()
    m = re.search(r"\b(?:in|for|at)\s+([a-z0-9][a-z0-9\s\-']{1,68})\s*$", text, flags=re.IGNORECASE)
    if not m:
        return None
    tail = " ".join(m.group(1).split()).strip()
    if len(tail) < 2:
        return None
    tl = tail.lower()
    if tl in _PLACE_TAIL_BLACKLIST or "suburbs" in tl.split():
        return None
    if tl in STATE_ALIASES:
        return None
    if tl in {s.lower() for s in STATE_ALIASES.values()}:
        return None
    return tail


def _sanitize_like_fragment(raw: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9\s'\-]", "", raw).strip()
    s = re.sub(r"\s+", " ", s)
    return s[:72]


def _resolve_single_area_metric(text: str) -> dict | None:
    if ("home ownership" in text or "resident equity" in text) and "compare" not in text:
        return {"column": "kpi_6_val", "alias": "resident_equity", "kind": "percent"}
    if "social housing" in text:
        return {"column": "kpi_5_val", "alias": "social_housing_pct", "kind": "percent"}
    if "migration" in text:
        return {"column": "kpi_3_val", "alias": "migration_footprint", "kind": "percent"}
    if _mentions_learning(text):
        return {"column": "kpi_4_val", "alias": "learning_level", "kind": "percent"}
    if "young family" in text:
        return {"column": "kpi_10_val", "alias": "young_family_presence", "kind": "percent"}
    if "resident anchor" in text or ("stable" in text and "suburb" in text):
        return {"column": "kpi_8_val", "alias": "resident_anchor", "kind": "percent"}
    if "rental access" in text or "affordable" in text or "affordability" in text:
        return {"column": "kpi_7_val", "alias": "rental_access", "kind": "percent"}
    if "household mobility" in text:
        return {"column": "kpi_9_val", "alias": "household_mobility", "kind": "decimal"}
    if "population" in text and "growth" not in text:
        return {"column": "population", "alias": "population", "kind": "int"}
    if _mentions_prosperity(text):
        return {"column": "kpi_1_val", "alias": "prosperity_score", "kind": "index"}
    if "diversity" in text or "diverse" in text:
        return {"column": "kpi_2_val", "alias": "diversity_index", "kind": "diversity"}
    return None


def _is_single_area_metric_question(text: str) -> bool:
    if _SINGLE_AREA_TOPN_RE.search(text):
        return False
    if _is_ranking_request(text):
        return False
    if _resolve_single_area_metric(text) is None:
        return False
    if _extract_trailing_place_name(text) is None:
        return False
    return True


def _is_previous_result_reference(text: str) -> bool:
    return any(
        phrase in text
        for phrase in (
            "these suburbs", "those suburbs", "this list", "that list", "the list",
            "above suburbs", "previous suburbs", "previous list", "same suburbs",
            "same list", "them",
        )
    )


def _literal_sql(value: object) -> str:
    return "'" + str(value or "").replace("'", "''") + "'"


# ---------------------------------------------------------------------------
# SQL template builder
# ---------------------------------------------------------------------------

def _template_sql_for_question(question: str) -> tuple[str, str] | None:
    text = _normalise_question(question)
    state = _extract_state(text)
    is_diversity_question = "diversity" in text or "diverse" in text

    ordered_states = _extract_states_ordered_in_text(text)
    if len(ordered_states) >= 2 and _is_explicit_two_state_avg_comparison(text):
        pair_spec = _metric_spec_for_explicit_pair_question(text)
        if pair_spec:
            s1, s2 = ordered_states[-2], ordered_states[-1]
            sql = _sql_two_state_average(pair_spec["column"], pair_spec["alias"], s1, s2)
            return "pair_state_avg", sql

    place_raw = _extract_trailing_place_name(text)
    metric_def = _resolve_single_area_metric(text)
    if place_raw and metric_def and _is_single_area_metric_question(text):
        frag = _sanitize_like_fragment(place_raw)
        if frag:
            esc = frag.replace("'", "''")
            col = metric_def["column"]
            alias = metric_def["alias"]
            filters = [
                f"LOWER(sa2_name) LIKE LOWER('%{esc}%')",
                f"{col} IS NOT NULL",
                *_residential_filters(include_statistical_categories=True),
            ]
            if state:
                filters.insert(0, f"state = '{state}'")
            sql = f"""SELECT sa2_name, state, {col} AS {alias}
FROM `demografy.prod_tables.a_master_view`
WHERE {_where_clause(filters)}
ORDER BY population DESC NULLS LAST
LIMIT 5"""
            return "single_area_metric", sql

    if is_diversity_question and "percentage" in text and state:
        threshold = _extract_number_after(text, ("above", "over", "greater than"), 0.7)
        filters = [f"state = '{state}'", "kpi_2_val IS NOT NULL", *_residential_filters()]
        sql = f"""SELECT ROUND(100 * SUM(CASE WHEN kpi_2_val > {threshold:g} THEN 1 ELSE 0 END) / COUNT(*), 2) AS percentage_high_diversity
FROM `demografy.prod_tables.a_master_view`
WHERE {_where_clause(filters)}
LIMIT 1;"""
        return "diversity_percentage", sql

    if _state_level_diversity_average_rank_intent(text):
        order = "ASC" if any(w in text for w in ("lowest", "least")) else "DESC"
        sql = f"""SELECT state, ROUND(AVG(kpi_2_val), 4) AS avg_diversity_index
FROM `demografy.prod_tables.a_master_view`
WHERE kpi_2_val IS NOT NULL
  AND state NOT IN ('Australian Capital Territory', 'Northern Territory', 'Other Territories')
GROUP BY state
ORDER BY avg_diversity_index {order}
LIMIT 1;"""
        return "single_name", sql

    if is_diversity_question and _diversity_suburb_list_intent(text):
        limit = _extract_limit(text, DEFAULT_LIMIT)
        filters: list[str] | None
        if state:
            filters = [f"state = '{state}'", "kpi_2_val IS NOT NULL", *_residential_filters()]
        elif _wants_national_scope(text):
            filters = ["kpi_2_val IS NOT NULL", *_residential_filters()]
        else:
            filters = None
        if filters is not None:
            sql = f"""SELECT sa2_name, state, kpi_2_val AS diversity_index
FROM `demografy.prod_tables.a_master_view`
WHERE {_where_clause(filters)}
ORDER BY kpi_2_val DESC
LIMIT {limit};"""
            return "ranked_metric", sql

    if "average" in text and _mentions_prosperity(text) and state:
        sql = f"""SELECT ROUND(AVG(kpi_1_val), 2) AS avg_prosperity_score
FROM `demografy.prod_tables.a_master_view`
WHERE state = '{state}'
  AND kpi_1_val IS NOT NULL
LIMIT 1;"""
        return "single_scalar", sql

    if "average" in text and _mentions_learning(text) and state:
        sql = f"""SELECT ROUND(AVG(kpi_4_val), 2) AS avg_learning_level
FROM `demografy.prod_tables.a_master_view`
WHERE state = '{state}'
  AND kpi_4_val IS NOT NULL
LIMIT 1;"""
        return "single_scalar", sql

    if state and _home_ownership_state_average_intent(text):
        filters = [
            f"state = '{state}'",
            "kpi_6_val IS NOT NULL",
            *_residential_filters(include_statistical_categories=True),
        ]
        sql = f"""SELECT ROUND(AVG(kpi_6_val), 2) AS avg_home_ownership
FROM `demografy.prod_tables.a_master_view`
WHERE {_where_clause(filters)}
LIMIT 1;"""
        return "single_scalar", sql

    if "state" in text and "highest" in text and _mentions_learning(text):
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
        limit = _extract_limit(text, DEFAULT_LIMIT)
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

    if "young family" in text and _mentions_learning(text):
        limit = _extract_limit(text, DEFAULT_LIMIT)
        family_words = ("family presence", "young family", "young families", "over", "above", "greater than")
        learning_has_threshold = bool(re.search(r"(?:learning level|education|educated|year 12)\D+(\d+(?:\.\d+)?)", text))
        family_has_threshold = _has_explicit_number_near(text, family_words)

        if not family_has_threshold and not learning_has_threshold:
            filters = ["kpi_10_val IS NOT NULL", "kpi_4_val IS NOT NULL", *_residential_filters()]
            if state:
                filters.insert(0, f"state = '{state}'")
            sql = f"""SELECT sa2_name, state, kpi_10_val AS young_family_presence, kpi_4_val AS learning_level
FROM `demografy.prod_tables.a_master_view`
WHERE {_where_clause(filters)}
ORDER BY (kpi_10_val * kpi_4_val) DESC, kpi_10_val DESC, kpi_4_val DESC
LIMIT {limit};"""
            return "young_family_learning", sql

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
        if state:
            filters.insert(0, f"state = '{state}'")
        sql = f"""SELECT sa2_name, state, kpi_10_val AS young_family_presence, kpi_4_val AS learning_level
FROM `demografy.prod_tables.a_master_view`
WHERE {_where_clause(filters)}
ORDER BY kpi_10_val DESC, kpi_4_val DESC
LIMIT {limit};"""
        return "young_family_learning", sql

    if ("stable" in text or "resident anchor" in text) and state:
        limit = _extract_limit(text, 1)
        filters = [f"state = '{state}'", "kpi_8_val IS NOT NULL", *_residential_filters()]
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
        limit = _extract_limit(text, DEFAULT_LIMIT)
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

    if _each_state_average_learning_aggregate_intent(text):
        sql = """SELECT state, ROUND(AVG(kpi_4_val), 2) AS avg_learning_level
FROM `demografy.prod_tables.a_master_view`
WHERE kpi_4_val IS NOT NULL
  AND sa2_name NOT LIKE '%Migratory%'
  AND sa2_name NOT LIKE '%No usual address%'
  AND sa2_name NOT LIKE '%Offshore%'
  AND sa2_name NOT LIKE '%Industrial%'
  AND sa2_name NOT LIKE '%Military%'
  AND population > 100
GROUP BY state
ORDER BY avg_learning_level DESC
LIMIT 10;"""
        return "state_learning_avg_list", sql

    if _best_suburb_in_top_learning_state_intent(text):
        sql = """WITH top_state AS (
  SELECT state
  FROM `demografy.prod_tables.a_master_view`
  WHERE kpi_4_val IS NOT NULL
    AND sa2_name NOT LIKE '%Migratory%'
    AND sa2_name NOT LIKE '%No usual address%'
    AND sa2_name NOT LIKE '%Offshore%'
    AND sa2_name NOT LIKE '%Industrial%'
    AND sa2_name NOT LIKE '%Military%'
    AND population > 100
  GROUP BY state
  ORDER BY AVG(kpi_4_val) DESC
  LIMIT 1
)
SELECT m.sa2_name, m.state, m.kpi_4_val AS learning_level
FROM `demografy.prod_tables.a_master_view` m
INNER JOIN top_state t ON m.state = t.state
WHERE m.kpi_4_val IS NOT NULL
  AND m.sa2_name NOT LIKE '%Migratory%'
  AND m.sa2_name NOT LIKE '%No usual address%'
  AND m.sa2_name NOT LIKE '%Offshore%'
  AND m.sa2_name NOT LIKE '%Industrial%'
  AND m.sa2_name NOT LIKE '%Military%'
  AND m.population > 100
ORDER BY m.kpi_4_val DESC
LIMIT 1;"""
        return "best_suburb_top_learning_state", sql

    metric = _rankable_metric(text)
    if metric and (_is_ranking_request(text) or state or _wants_national_scope(text)):
        limit = _extract_limit(text, DEFAULT_LIMIT)
        order = _ranking_order(text, metric["order"])
        filters = [f"{metric['column']} IS NOT NULL", *_residential_filters(include_statistical_categories=True)]
        if state:
            filters.insert(0, f"state = '{state}'")
        sql = f"""SELECT sa2_name, state, {metric['column']} AS {metric['alias']}
FROM `demografy.prod_tables.a_master_view`
WHERE {_where_clause(filters)}
ORDER BY {metric['column']} {order}
LIMIT {limit};"""
        return metric["intent"], sql

    return None


# ---------------------------------------------------------------------------
# Formatters
# ---------------------------------------------------------------------------

def _rows_from_dataframe(df) -> list:
    if df is None or df.empty:
        return []
    return [tuple(row) for row in df.itertuples(index=False, name=None)]


def _fmt_number(value, suffix: str = "") -> str:
    if value is None:
        return "N/A"
    try:
        number = float(value)
    except (TypeError, ValueError):
        return f"{value}{suffix}"
    text = f"{number:.2f}".rstrip("0").rstrip(".")
    return f"{text}{suffix}"


def _geo_phrase(state: str | None) -> str:
    return f" in {state}" if state else ""


def _state_abbrev(state: object) -> str:
    state_text = str(state or "").strip()
    return STATE_ABBREVIATIONS.get(state_text, state_text)


def _area_label(row: tuple, name_index: int = 0, state_index: int = 1) -> str:
    name = str(row[name_index]).strip() if len(row) > name_index else ""
    state = _state_abbrev(row[state_index]) if len(row) > state_index else ""
    return f"{name}, {state}" if state else name


def _template_lead_in(intent: str, rows: list, question: str, state: str | None) -> str:
    q = (question or "").lower()
    geo = _geo_phrase(state)
    n = len(rows) if rows else _extract_limit(_normalise_question(question), DEFAULT_LIMIT)

    if intent == "single_scalar":
        if _mentions_prosperity(q):
            return f"Average prosperity score{geo}:"
        if _mentions_learning(q):
            return f"Average learning level{geo}:"
        if "home ownership" in q or "resident equity" in q:
            return f"Average home ownership (resident equity){geo}:"
        return f"Result for your query{geo}:"
    if intent == "single_name":
        if "diversity" in q or "diverse" in q:
            if "lowest" in q or "least" in q:
                return "The state with the lowest average diversity index is:"
            return "The state with the highest average diversity index is:"
        return "The top state for this measure is:"
    if intent == "diversity_percentage":
        return f"Share of suburbs with high diversity{geo}:"
    if intent == "best_suburb_top_learning_state":
        return "The suburb with the highest learning level in the top-ranked state (by average learning) is:"
    if intent == "state_learning_avg_list":
        return "Average learning level (education) by state:"
    if intent == "pair_state_avg":
        if "prosperity" in q:
            return "Comparison of average prosperity score between the two states:"
        if "diversity" in q or "diverse" in q:
            return "Comparison of average diversity index between the two states:"
        if "migration" in q:
            return "Comparison of average migration footprint between the two states:"
        if "learning" in q or "education" in q or "school" in q:
            return "Comparison of average learning level between the two states:"
        if "young family" in q:
            return "Comparison of average young family presence between the two states:"
        if "rental" in q or "affordab" in q:
            return "Comparison of average rental access between the two states:"
        if "home ownership" in q or "resident equity" in q:
            return "Comparison of average home ownership between the two states:"
        return "Comparison of average values between the two states:"
    if intent == "state_comparison":
        return "Home ownership and rental access by state:"
    if intent == "young_family_learning":
        return f"Suburbs with strong young family presence and learning level{geo}:"
    if intent == "rental_access":
        return f"Most affordable rental access suburbs{geo}:"
    if intent == "single_area_metric":
        return f"SA2 areas matching your place name{geo}:"
    if intent == "ranked_metric":
        if "diversity" in q or "diverse" in q:
            return f"Here are the top {n} most diverse suburbs{geo}:"
        if _mentions_prosperity(q):
            return f"Here are the top {n} suburbs by prosperity score{geo}:"
        return f"Here are the top {n} ranked results{geo}:"
    if intent == "ranked_percent":
        if "migration" in q:
            return f"Here are the top {n} suburbs by migration footprint{geo}:"
        if _mentions_learning(q):
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


def _format_single_area_metric_cell(question: str, val: object) -> str:
    q = (question or "").lower()
    if val is None:
        return "—"
    if "population" in q and "kpi" not in q:
        try:
            return str(int(round(float(val))))
        except (TypeError, ValueError):
            return str(val)
    if "diversity" in q or "diverse" in q:
        try:
            return f"{float(val):.2f} (0–1 scale; higher = more culturally diverse)"
        except (TypeError, ValueError):
            return str(val)
    if "prosperity" in q:
        return f"{_fmt_number(val)} (0–100 socioeconomic index)"
    if "household mobility" in q:
        try:
            return f"{float(val):.2f} (0–1)"
        except (TypeError, ValueError):
            return str(val)
    return _fmt_number(val, "%")


def _format_template_answer(intent: str, rows: list, *, question: str, state: str | None) -> str:
    q = (question or "").lower()
    lead = _template_lead_in(intent, rows, question, state)

    if not rows:
        body = "No suburbs match both criteria." if intent == "young_family_learning" else "No matching suburbs found for this query."
        return f"{lead}\n\n{body}"

    if intent == "single_scalar":
        pct = "home ownership" in q or "resident equity" in q
        body = _fmt_number(rows[0][0], "%" if pct else "")
        return f"{lead}\n\n{body}"

    if intent == "single_area_metric":
        body = "\n".join(
            f"{i}. {_area_label(row)}: {_format_single_area_metric_cell(question, row[2])}"
            for i, row in enumerate(rows, start=1)
        )
        return f"{lead}\n\n{body}"

    if intent == "single_name":
        row = rows[0]
        if len(row) >= 2:
            if _mentions_learning(q):
                return f"{lead}\n\n{row[0]} ({_fmt_number(row[1], '%')} average learning level)"
            if "diversity" in q or "diverse" in q:
                div_spec = KPI_AVG_PAIR_SPECS["kpi_2_val"]
                return f"{lead}\n\n{row[0]} ({_format_pair_state_avg_cell(div_spec, row[1])} average diversity index)"
        return f"{lead}\n\n{row[0]}"

    if intent == "diversity_percentage":
        return f"{lead}\n\n{_fmt_number(rows[0][0], '%')}"

    if intent == "state_learning_avg_list":
        body = "\n".join(
            f"{i}. {row[0]}: {_fmt_number(row[1], '%')}"
            for i, row in enumerate(rows, start=1)
        )
        return f"{lead}\n\n{body}"

    if intent == "pair_state_avg":
        spec = _metric_spec_for_explicit_pair_question(q)
        if not rows:
            body = "No aggregate values found for those states."
        elif spec:
            body = "\n".join(
                f"{i}. {row[0]}: {_format_pair_state_avg_cell(spec, row[1])}"
                for i, row in enumerate(rows, start=1)
            )
        else:
            body = "\n".join(f"{i}. {row[0]}: {row[1]}" for i, row in enumerate(rows, start=1))
        return f"{lead}\n\n{body}"

    if intent == "best_suburb_top_learning_state":
        if not rows:
            return f"{lead}\n\nNo matching suburb found."
        r = rows[0]
        body = f"{_area_label(r)}: {_fmt_number(r[2], '%')}"
        return f"{lead}\n\n{body}"

    if intent == "state_comparison":
        body = "\n".join(
            f"{i}. {row[0]}: home ownership {_fmt_number(row[1], '%')}, rental access {_fmt_number(row[2], '%')}"
            for i, row in enumerate(rows, start=1)
        )
        return f"{lead}\n\n{body}"

    if intent == "young_family_learning":
        body = "\n".join(
            f"{i}. {_area_label(row)}: young family {_fmt_number(row[2], '%')}, learning level {_fmt_number(row[3], '%')}"
            for i, row in enumerate(rows, start=1)
        )
        return f"{lead}\n\n{body}"

    value_index = 3 if intent == "rental_access" else 2
    suffix = "" if intent == "ranked_metric" else "%"
    body = "\n".join(
        f"{i}. {_area_label(row)}: {_fmt_number(row[value_index], suffix)}"
        for i, row in enumerate(rows, start=1)
    )
    return f"{lead}\n\n{body}"


def _template_meta(intent: str, sql: str, rows: list, question: str, state: str | None) -> dict:
    return {"intent": intent, "sql": sql, "rows": rows, "question": question, "state": state}


# ---------------------------------------------------------------------------
# Template answer runner
# ---------------------------------------------------------------------------

def _answer_previous_result_metric_question(
    question: str,
    context_meta: dict | None,
    *,
    execute: bool = True,
) -> tuple[str, str | None, dict | None] | None:
    text = _normalise_question(question)
    if not context_meta or not _is_previous_result_reference(text):
        return None

    metric = _rankable_metric(text) or _resolve_single_area_metric(text)
    if not metric:
        return None

    rows = context_meta.get("rows") or []
    if not rows:
        return None

    column = metric["column"]
    alias = metric.get("alias", "value")
    pairs = [
        (row[0], row[1])
        for row in rows[:10]
        if isinstance(row, (tuple, list)) and len(row) >= 2
    ]
    if not pairs:
        return None

    filters = " OR\n  ".join(
        f"(sa2_name = {_literal_sql(name)} AND state = {_literal_sql(state)})"
        for name, state in pairs
    )

    if "average" in text or "avg" in text or "mean" in text:
        sql = f"""SELECT ROUND(AVG({column}), 2) AS avg_{alias}
FROM `demografy.prod_tables.a_master_view`
WHERE ({filters})
  AND {column} IS NOT NULL
LIMIT 1;"""
        if not execute:
            return "", sql, None
        from db.bigquery_client import run_query
        query_rows = _rows_from_dataframe(run_query(sql))
        if not query_rows:
            return "I could not calculate that metric for the previous suburb list.", sql, None
        suffix = "" if column in {"kpi_1_val", "kpi_2_val", "kpi_9_val", "population"} else "%"
        value = _fmt_number(query_rows[0][0], suffix)
        metric_name = {
            "kpi_1_val": "prosperity score", "kpi_2_val": "diversity index",
            "kpi_3_val": "migration footprint", "kpi_4_val": "learning level",
            "kpi_5_val": "social housing", "kpi_6_val": "home ownership",
            "kpi_7_val": "rental access", "kpi_8_val": "resident anchor",
            "kpi_9_val": "household mobility", "kpi_10_val": "young family presence",
            "population": "population",
        }.get(column, alias.replace("_", " "))
        explainer = _short_metric_explanation(column)
        prefix = f"{explainer}\n\n" if explainer else ""
        return (
            f"{prefix}The average {metric_name} across those {len(pairs)} suburbs is:\n\n{value}",
            sql,
            None,
        )

    sql = f"""SELECT sa2_name, state, {column} AS {alias}
FROM `demografy.prod_tables.a_master_view`
WHERE ({filters})
  AND {column} IS NOT NULL
ORDER BY {column} DESC
LIMIT 10;"""
    if not execute:
        return "", sql, None
    from db.bigquery_client import run_query
    query_rows = _rows_from_dataframe(run_query(sql))
    intent = metric.get("intent", "ranked_percent")
    answer = _format_template_answer(intent, query_rows, question=question, state=None)
    meta = _template_meta(intent, sql, query_rows, question, None)
    return answer, sql, meta


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
    if intent == "pair_state_avg":
        spec = _metric_spec_for_explicit_pair_question(text_norm)
        ordered = _extract_states_ordered_in_text(text_norm)
        if spec and len(ordered) >= 2:
            meta = {
                **meta,
                "metric_label": spec["label"],
                "pair_states": [ordered[-2], ordered[-1]],
                "kpi_column": spec["column"],
            }
    return answer, sql, meta


def _answer_deictic_suburbs_after_state_rank(
    question: str,
    context_meta: dict | None,
) -> tuple[str, str, dict] | None:
    """After ``single_name`` diversity state winner, resolve 'top suburbs there'."""
    if not context_meta or context_meta.get("intent") != "single_name":
        return None
    prev_q = _normalise_question(context_meta.get("question") or "")
    if "diversity" not in prev_q and "diverse" not in prev_q:
        return None
    text = _normalise_question(question)
    if "suburb" not in text and "suburbs" not in text:
        return None
    if not any(
        needle in text
        for needle in (
            "there",
            "that state",
            "this state",
            "in that state",
            "from that state",
        )
    ):
        return None

    rows = context_meta.get("rows") or []
    if not rows or not isinstance(rows[0], (list, tuple)) or not rows[0]:
        return None
    winning_state = str(rows[0][0]).strip()
    if not winning_state:
        return None

    limit = _extract_limit(text, DEFAULT_LIMIT)
    rewritten = f"Top {limit} most diverse suburbs in {winning_state}"
    return _answer_template_question(rewritten)


# ---------------------------------------------------------------------------
# Show-more follow-up
# ---------------------------------------------------------------------------

_SHOW_MORE_PHRASES = frozenset({
    "more", "more?", "more please", "show more", "show more results",
    "see more", "load more", "next", "next results", "give me more",
    "can i see more", "more suburbs", "more results please",
})


def _is_show_more_request(text: str) -> bool:
    normalized = " ".join(text.lower().strip().rstrip("?").split())
    return normalized in _SHOW_MORE_PHRASES


def _show_more_answer(context_meta: dict) -> tuple[str, str, dict] | None:
    """Re-run the previous templated SQL with a higher LIMIT."""
    sql = context_meta.get("sql")
    if not sql:
        return None
    current_rows = context_meta.get("rows") or []
    new_limit = min(len(current_rows) + DEFAULT_LIMIT, 25)
    if new_limit <= len(current_rows):
        return None
    new_sql = re.sub(r"\bLIMIT\s+\d+\b", f"LIMIT {new_limit}", sql, flags=re.IGNORECASE)
    if new_sql == sql:
        return None
    from db.bigquery_client import run_query
    rows = _rows_from_dataframe(run_query(new_sql))
    intent = context_meta.get("intent", "ranked_percent")
    question = context_meta.get("question", "")
    state = context_meta.get("state")
    answer = _format_template_answer(intent, rows, question=question, state=state)
    meta = _template_meta(intent, new_sql, rows, question, state)
    return answer, new_sql, meta


# ---------------------------------------------------------------------------
# Conversational follow-up resolvers
# ---------------------------------------------------------------------------

def _detect_affirmative_followup(text: str) -> bool:
    normalized = re.sub(r"[^a-z0-9\s]", " ", (text or "").lower())
    normalized = " ".join(normalized.split())
    return normalized in {re.sub(r"[^a-z0-9\s]", " ", x).strip() for x in _AFFIRMATIVE_FOLLOWUPS}


def _history_geography(history: list[dict] | None) -> str | None:
    if not history:
        return None
    for turn in reversed(history):
        if turn.get("role") != "user":
            continue
        previous = _normalise_question(turn.get("content") or "")
        state = _extract_state(previous)
        if state:
            return f"in {state}"
        if _wants_national_scope(previous):
            return "in Australia"
    return None


def _affirmative_followup_question(history: list[dict] | None) -> str | None:
    if not history:
        return None
    geography = _history_geography(history) or "in Australia"
    n = DEFAULT_LIMIT
    for turn in reversed(history):
        if turn.get("role") != "assistant":
            continue
        content = (turn.get("content") or "").lower()
        if "would you like" not in content:
            continue
        if "resident anchor" in content or "stable" in content:
            return f"Show me the top {n} suburbs with the highest resident anchor {geography}"
        if "diverse" in content or "diversity" in content:
            return f"Show me the top {n} most diverse suburbs {geography}"
        if "migration" in content or "overseas" in content:
            return f"Show me the top {n} suburbs by migration footprint {geography}"
        if "young family" in content or "families" in content:
            return f"Show me the top {n} suburbs by young family presence {geography}"
        if "prosperity" in content or "affluent" in content or "wealthy" in content:
            return f"Show me the top {n} suburbs by prosperity score {geography}"
        if "learning" in content or "education" in content:
            return f"Show me the top {n} suburbs by learning level {geography}"
        if "rental access" in content or "affordab" in content:
            return f"Show me the top {n} suburbs by rental access {geography}"
        if "home ownership" in content or "resident equity" in content:
            return f"Show me the top {n} suburbs by home ownership {geography}"
        if "social housing" in content:
            return f"Show me the top {n} suburbs by social housing {geography}"
    return None


def _is_short_metric_followup(question: str) -> bool:
    text = _normalise_question(question)
    if len(text.split()) > 10:
        return False
    if not _rankable_metric(text):
        return False
    starters = ("what about", "how about", "and", "also", "what is", "show", "show me", "tell me")
    return len(text.split()) <= 4 or text.startswith(starters)


def _contextual_metric_followup_question(question: str, history: list[dict] | None) -> str | None:
    if not _is_short_metric_followup(question):
        return None
    metric = _rankable_metric(_normalise_question(question))
    if not metric:
        return None
    geography = _history_geography(history) or "in Australia"
    label = {
        "kpi_1_val": "prosperity score", "kpi_4_val": "learning level",
        "kpi_2_val": "diversity index", "kpi_3_val": "migration footprint",
        "kpi_5_val": "social housing", "kpi_6_val": "home ownership",
        "kpi_7_val": "rental access", "kpi_8_val": "resident anchor",
        "kpi_10_val": "young family presence",
    }.get(metric["column"], metric["alias"].replace("_", " "))
    return f"Show me the top {DEFAULT_LIMIT} suburbs by {label} {geography}"


def _detect_state_only_followup(text: str) -> str | None:
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
    if not history:
        return None
    aliases = sorted(STATE_ALIASES.keys(), key=len, reverse=True)
    for turn in reversed(history):
        if turn.get("role") != "user":
            continue
        prev = (turn.get("content") or "").strip()
        if not prev:
            continue
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
