"""Fast guardrail checks for natural-language SQL routing.

These tests do not call BigQuery. They verify the app-layer routing that keeps
the SQL agent conversational and product-safe.
"""

from agent.sql_agent import (
    ask,
    _answer_previous_result_metric_question,
    _contextual_metric_followup_question,
    _format_template_answer,
    _template_sql_for_question,
)


def assert_contains(text: str, expected: str) -> None:
    if expected not in text:
        raise AssertionError(f"Expected {expected!r} in:\n{text}")


def main() -> None:
    cases = [
        ("affluent suburbs in Victoria", "kpi_1_val AS prosperity_score"),
        ("wealthiest suburbs in NSW", "state = 'New South Wales'"),
        ("education suburbs in Queensland", "kpi_4_val AS learning_level"),
        ("average education in Victoria", "AVG(kpi_4_val)"),
        ("educated suburbs in Australia", "kpi_4_val AS learning_level"),
        (
            "Which suburbs in Victoria have high young family presence and strong learning levels?",
            "ORDER BY (kpi_10_val * kpi_4_val) DESC",
        ),
        ("suburbs with high home ownership in Victoria", "ORDER BY kpi_6_val DESC"),
        ("suburbs with low home ownership in Victoria", "ORDER BY kpi_6_val ASC"),
    ]
    for question, expected_sql in cases:
        routed = _template_sql_for_question(question)
        if not routed:
            raise AssertionError(f"No template route for: {question}")
        _intent, sql = routed
        assert_contains(sql, expected_sql)

    history = [{"role": "user", "content": "What are the top 5 affluent suburbs in Victoria?"}]
    rewritten = _contextual_metric_followup_question("what about education?", history)
    if rewritten != "Show me the top 10 suburbs by learning level in Victoria":
        raise AssertionError(f"Unexpected rewrite: {rewritten}")

    answer = _format_template_answer(
        "ranked_percent",
        [("Berwick", "Victoria", 71.23), ("Parramatta", "New South Wales", 68.0)],
        question="highest resident anchor",
        state=None,
    )
    assert_contains(answer, "Berwick, Vic")
    assert_contains(answer, "Parramatta, NSW")

    answer, sql, meta = ask("What are the house prices in Berwick?")
    assert_contains(answer, "I don't have live house-price")
    assert sql is None
    assert meta is None

    unsupported_cases = [
        ("Which suburbs have the best schools?", "school rankings"),
        ("What are the safest suburbs in Victoria?", "crime rates"),
        ("Which suburbs have good public transport?", "public transport access"),
        ("Which suburbs will be the next growth hotspot?", "forecasts"),
        ("What is the average income in Berwick?", "direct income"),
    ]
    for question, expected in unsupported_cases:
        answer, sql, meta = ask(question)
        assert_contains(answer, "I don't have")
        assert_contains(answer, expected)
        assert sql is None
        assert meta is None

    answer, sql, meta = ask("what's the criteria for rental access?")
    assert_contains(answer, "Rental access is Demografy's rental-affordability proxy")
    assert_contains(answer, "below $450 per week")
    assert_contains(answer, "It is not live rent listings, median rent, or median house-price data")
    assert sql is None
    assert meta is None

    context_meta = {
        "rows": [("Point Cook - South", "Victoria", 32.07), ("Tarneit - North", "Victoria", 29.72)]
    }
    routed = _answer_previous_result_metric_question(
        "What is the average learning level in these suburbs?",
        context_meta,
        execute=False,
    )
    assert routed is not None
    assert_contains(routed[1] or "", "AVG(kpi_4_val)")

    print("Guardrail smoke checks passed.")


if __name__ == "__main__":
    main()
