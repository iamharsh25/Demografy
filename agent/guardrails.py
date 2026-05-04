"""Static guardrail answers: topic detection, KPI definitions, unsupported redirects."""

from __future__ import annotations

import re

from agent.kpis import METRIC_CRITERIA, RANKABLE_METRICS, UNSUPPORTED_TOPIC_RULES

_SCHEMA_PROBE_RE = re.compile(
    r"\b(?:kpi_\d+_(?:val|ind)|a_master_view|sa2_(?:name|code)|sa[34]_name"
    r"|prod_tables|ref_tables|dev_customers)\b",
    re.IGNORECASE,
)


def _is_schema_probe(text: str) -> bool:
    return bool(_SCHEMA_PROBE_RE.search(text))


def _mentions_prosperity(text: str) -> bool:
    return any(
        metric["column"] == "kpi_1_val" and any(kw in text for kw in metric["keywords"])
        for metric in RANKABLE_METRICS
    )


def _mentions_learning(text: str) -> bool:
    return any(
        metric["column"] == "kpi_4_val" and any(kw in text for kw in metric["keywords"])
        for metric in RANKABLE_METRICS
    )


def _metric_key_from_text(text: str) -> str | None:
    if _mentions_prosperity(text):
        return "prosperity"
    if "diversity" in text or "diverse" in text:
        return "diversity"
    if "migration" in text:
        return "migration"
    if _mentions_learning(text):
        return "learning"
    if "social housing" in text:
        return "social_housing"
    if "home ownership" in text or "resident equity" in text:
        return "home_ownership"
    if "rental access" in text or "affordability" in text:
        return "rental_access"
    if "resident anchor" in text or "stability" in text or "stable" in text:
        return "resident_anchor"
    if "household mobility" in text:
        return "household_mobility"
    if "young family" in text or "young families" in text:
        return "young_family"
    if "population" in text:
        return "population"
    return None


def _is_kpi_overview_question(text: str) -> bool:
    if len(text) > 320:
        return False
    triggers = (
        "what kpis", "which kpis", "what kpi ", "which kpi ",
        "kpis do you", "kpi do you", "what metrics do you", "which metrics do you",
        "what measures do you", "what data do you measure", "what do you measure",
        "how are kpi", "how are the kpi", "how are scores", "how do you measure",
        "what scores do you", "list kpi", "list of kpi", "available kpi",
        "explain the kpi", "describe the kpi", "tell me about kpi",
        "what indicators", "which indicators",
        "what demografy measure", "what does demografy measure",
    )
    if any(t in text for t in triggers):
        return True
    if ("kpi" in text or "metric" in text) and any(
        w in text for w in ("measure", "measuring", "available", "offer", "track", "cover", "define")
    ):
        if any(w in text for w in ("what ", "which ", "how ", "list", "tell me", "explain")):
            return True
    return False


def _kpi_overview_answer() -> str:
    return """Demografy summarises Australian Bureau of Statistics (ABS)–based suburb data at **SA2** level (what we call a "suburb" or area in chat).

**How scores work**
Most KPIs are percentages or indices derived from census-style inputs for residents in that SA2. Values are comparable across suburbs; higher or lower depends on the metric (see below).

**KPIs you can ask about**
• **Prosperity score** — Socioeconomic advantage and disadvantage (index **0–100**, higher = more advantaged).
• **Diversity index** — Cultural and linguistic diversity (**0–1**, higher = more diverse).
• **Migration footprint** — Share of residents with overseas-born parents (**0–100%**).
• **Learning level** — Year 12 or equivalent attainment (**0–100%**).
• **Social housing** — Share of households in public or community housing (**0–100%**).
• **Home ownership (resident equity)** — Share of households owned outright or with a mortgage (**0–100%**).
• **Rental access** — Affordability proxy: share renting below $450/week (**0–100%**).
• **Resident anchor** — Stability: share of residents who lived at the same address 5+ years ago (**0–100%**).
• **Household mobility** — Households in transitional situations (index **0–1**).
• **Young families** — Share of residents aged 0–14 (**0–100%**).
• **Population** — Estimated resident population (count).

Ask for any of these **for a state, city, or suburb name** (e.g. "prosperity in Forde" or "top 5 diverse suburbs in NSW")."""


def _is_metric_definition_question(text: str) -> bool:
    if not _metric_key_from_text(text):
        return False
    # Numeric / geographic questions should reach SQL templates, not the static blurb
    # (e.g. "What is the average prosperity score in NSW?" matches "what is" + prosperity).
    if "average" in text or "median" in text:
        return False
    if re.search(r"\b(?:top|first)\s+\d+\b", text):
        return False
    if "compare" in text or "comparison" in text:
        return False
    if re.search(r"\bvs\.?\b", text) or " versus " in f" {text} ":
        return False
    if re.search(r"\bwhich\s+state\b", text) and re.search(
        r"\b(?:highest|lowest|most|least|average|avg)\b", text
    ):
        return False
    triggers = (
        "what is", "what's", "criteria", "criterion", "definition", "define",
        "meaning", "mean", "means", "measured", "measure", "calculated",
        "calculation", "how do you", "how is", "how are", "explain",
    )
    return any(trigger in text for trigger in triggers)


def _metric_definition_answer(text: str) -> str | None:
    key = _metric_key_from_text(text)
    return METRIC_CRITERIA.get(key) if key else None


def _short_metric_explanation(column: str) -> str:
    return {
        "kpi_1_val": "Prosperity score is a 0-100 socioeconomic advantage index; higher values suggest more advantaged areas.",
        "kpi_2_val": "Diversity index runs from 0 to 1; higher values indicate a broader mix of ancestry groups.",
        "kpi_3_val": "Migration footprint is the percentage of residents with at least one overseas-born parent.",
        "kpi_4_val": "Learning level is Demografy's education-attainment signal, based on Year 12 or equivalent completion.",
        "kpi_5_val": "Social housing is the percentage of households in public or community housing.",
        "kpi_6_val": "Home ownership, also called resident equity, is the percentage of households owned outright or with a mortgage.",
        "kpi_7_val": "Rental access is the percentage of renting households paying below $450 per week.",
        "kpi_8_val": "Resident anchor is the percentage of residents who lived at the same address five years earlier.",
        "kpi_9_val": "Household mobility is a 0-1 index for households in more transitional living situations.",
        "kpi_10_val": "Young family presence is the percentage of residents aged 0 to 14.",
        "population": "Population is the estimated resident headcount for the suburb-level area.",
    }.get(column, "")


def _is_property_price_question(text: str) -> bool:
    if not text:
        return False
    if "social housing" in text or "home ownership" in text or "resident equity" in text:
        return False
    direct_price_terms = (
        "house price", "house prices", "home price", "home prices",
        "property price", "property prices", "median price", "median house",
        "median home", "sale price", "sales price", "sold price",
        "capital growth", "property value", "property values",
        "dwelling value", "dwelling values", "mortgage repayment",
    )
    if any(term in text for term in direct_price_terms):
        return True
    property_context = any(
        term in text
        for term in ("house", "houses", "home", "homes", "property", "properties", "real estate")
    )
    price_intent = any(
        term in text
        for term in (
            "buy", "buying", "purchase", "expensive", "cheapest", "cheap",
            "affordable", "price", "prices", "cost", "costs", "value", "values",
        )
    )
    return property_context and price_intent


def _unsupported_topic_rule(text: str) -> dict | None:
    if not text:
        return None
    for rule in UNSUPPORTED_TOPIC_RULES:
        if any(term in text for term in rule["terms"]):
            return rule
    return None


def _unsupported_topic_redirect_answer(text: str) -> str | None:
    rule = _unsupported_topic_rule(text)
    if not rule:
        return None
    proxies = "\n".join(f"{i}. {proxy}" for i, proxy in enumerate(rule["proxies"], start=1))
    return (
        f"I don't have {rule['missing']} in the Demografy dataset, so I should not answer that directly.\n\n"
        f"The closest Demografy signals are:\n\n{proxies}\n\n"
        f"Try asking: \"{rule['example']}\"."
    )


def _property_price_redirect_answer() -> str:
    return (
        "I don't have live house-price, sales, or property valuation data in the Demografy dataset, "
        "so I should not rank suburbs by actual prices.\n\n"
        "I can help with related demographic signals instead:\n\n"
        "1. Rental access - affordability proxy based on lower weekly rent share\n"
        "2. Home ownership - share of homes owned outright or with a mortgage\n"
        "3. Prosperity score - socioeconomic advantage\n"
        "4. Social housing - public/community housing share\n"
        "5. Resident anchor - population stability\n\n"
        "Try asking: \"affordable rental suburbs in Victoria\", \"stable suburbs with high home ownership\", "
        "or \"affluent suburbs in NSW\"."
    )
