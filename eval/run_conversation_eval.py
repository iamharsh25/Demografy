"""Conversation stress eval for the Demografy chatbot.

Runs each scenario in
[eval/conversation_stress_dataset.json](Demografy/eval/conversation_stress_dataset.json)
through ``agent.sql_agent.ask`` with an in-memory ``history`` list, then asks
``agent.suggestions.generate_suggestions`` for follow-up chips. Each turn is
checked against quick rules (no SQL/column leak, chip shape) and the whole
transcript is scored 1-5 by ``eval/conversation_judge.py``.

Run from repo root::

    python eval/run_conversation_eval.py

Outputs:
  * ``eval/conversation_results.json`` - per-scenario report (incremental)
  * Console summary with pass count, average score, and any failures.

This eval is internal QA. It does NOT touch ``ChatHistory/`` on disk; the
``history`` argument is a plain list. LangSmith picks up traces automatically
because each ``ask`` runs through LangChain.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from agent.chart_renderer import is_chartable  # noqa: E402
from agent.sql_agent import GEOGRAPHY_CLARIFICATION_CHIPS, ask  # noqa: E402
from agent.suggestions import generate_suggestions  # noqa: E402
from eval.conversation_judge import score_conversation  # noqa: E402


DATASET_PATH = _ROOT / "eval" / "conversation_stress_dataset.json"
RESULTS_PATH = _ROOT / "eval" / "conversation_results.json"


# Forbidden tokens that should never reach the user-facing answer or any chip.
_FORBIDDEN_PATTERNS = [
    re.compile(r"\bkpi_\d+_(?:val|ind)\b", re.IGNORECASE),
    re.compile(r"\bsa[234]_(?:name|code)\b", re.IGNORECASE),
    re.compile(r"\ba_master_view\b", re.IGNORECASE),
    re.compile(r"\bdemografy\.(?:prod_tables|ref_tables)\b", re.IGNORECASE),
    re.compile(r"```", re.IGNORECASE),
    re.compile(r"\bSELECT\s", re.IGNORECASE),
]


def _save(results: list[dict]) -> None:
    RESULTS_PATH.write_text(json.dumps(results, indent=2), encoding="utf-8")


def _check_text_for_leaks(text: str) -> list[str]:
    failures: list[str] = []
    if not text:
        return failures
    for pat in _FORBIDDEN_PATTERNS:
        if pat.search(text):
            failures.append(f"text contains forbidden pattern: {pat.pattern}")
    return failures


def _check_chip_shape(chips: list[str]) -> list[str]:
    failures: list[str] = []
    if len(chips) > 4:
        failures.append(f"more than 4 chips ({len(chips)})")
    geo_ok = set(GEOGRAPHY_CLARIFICATION_CHIPS)
    for chip in chips:
        if not chip.strip():
            failures.append("empty chip text")
            continue
        if not chip.strip().endswith("?") and chip.strip() not in geo_ok:
            failures.append(f"chip missing '?' (and not a geography label): {chip!r}")
        failures.extend(f"chip leak in {chip!r}: {f}" for f in _check_text_for_leaks(chip))
    return failures


def _check_must_mention(
    answer: str,
    must_mention: list[str],
    *,
    extra_text: str = "",
) -> list[str]:
    failures: list[str] = []
    blob = f"{answer or ''} {extra_text or ''}".lower()
    for token in must_mention or []:
        if token.lower() not in blob:
            failures.append(f"answer/chips missing required token: {token!r}")
    return failures


def _check_must_not_mention(answer: str, must_not_mention: list[str]) -> list[str]:
    failures: list[str] = []
    lowered = (answer or "").lower()
    for token in must_not_mention or []:
        if token.lower() in lowered:
            failures.append(f"answer contains forbidden token: {token!r}")
    return failures


def _run_scenario(scenario: dict) -> dict:
    sid = scenario.get("id") or "?"
    name = scenario.get("name") or sid
    turns_in: list[str] = scenario.get("turns") or []
    must_mention_final: list[str] = scenario.get("must_mention") or []
    must_not_mention: list[str] = scenario.get("must_not_mention") or []

    print(f"[{sid}] {name}")
    print("-" * 80, flush=True)

    history: list[dict] = []
    transcript: list[dict] = []
    rule_failures: list[str] = []
    error: str | None = None

    for i, q in enumerate(turns_in, start=1):
        print(f"  Turn {i} user: {q}", flush=True)
        try:
            answer, sql, meta = ask(q, history=history)
        except Exception as exc:
            error = f"ask() raised: {exc!r}"
            rule_failures.append(error)
            answer, sql, meta = "", None, None

        # Rule checks on the answer.
        rule_failures.extend(
            f"turn {i} answer: {f}" for f in _check_text_for_leaks(answer)
        )

        # Suggestions: best-effort. Empty is allowed (no API key, timeout, etc).
        chart_meta = None
        if meta and is_chartable(str(meta.get("intent") or ""), meta.get("rows")):
            chart_meta = meta

        try:
            chips = generate_suggestions(
                question=q,
                answer=answer,
                history=history,
                chart_meta=chart_meta,
            )
        except Exception as exc:
            chips = []
            rule_failures.append(f"turn {i} generate_suggestions raised: {exc!r}")

        rule_failures.extend(f"turn {i} {f}" for f in _check_chip_shape(chips))

        # Update history AFTER the call so the model sees the same context the
        # live engine builds in chat_engine.resolve_pending_question.
        history.append({"role": "user", "content": q})
        history.append({"role": "assistant", "content": answer})

        transcript.append({
            "user_turn": q,
            "assistant_answer": answer,
            "sql": sql,
            "suggestions": chips,
        })

        print(f"  Turn {i} assistant: {answer[:140].replace(chr(10), ' ') }", flush=True)
        if chips:
            print(f"  Turn {i} chips: {chips}", flush=True)

    # must_mention is checked against the FINAL assistant answer, since most
    # scenarios expect the follow-up to land on the right state/topic.
    if transcript:
        final_answer = transcript[-1]["assistant_answer"]
        final_chips = transcript[-1].get("suggestions") or []
        rule_failures.extend(
            _check_must_mention(
                final_answer,
                must_mention_final,
                extra_text=" ".join(str(c) for c in final_chips),
            )
        )
        rule_failures.extend(_check_must_not_mention(final_answer, must_not_mention))

    # Whole-transcript LLM judge.
    judge_result: dict[str, Any]
    try:
        judge_result = score_conversation(name, transcript)
    except Exception as exc:
        judge_result = {"score": 0, "reasoning": f"judge raised: {exc!r}"}

    print(f"  Judge: {judge_result['score']}/5 - {judge_result['reasoning']}")
    if rule_failures:
        print(f"  Rule failures ({len(rule_failures)}):")
        for f in rule_failures:
            print(f"    - {f}")
    print()

    return {
        "id": sid,
        "name": name,
        "turns": transcript,
        "rule_failures": rule_failures,
        "judge_score": judge_result["score"],
        "judge_reasoning": judge_result["reasoning"],
        "error": error,
    }


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    if not DATASET_PATH.exists():
        print(f"Dataset not found: {DATASET_PATH}")
        sys.exit(1)

    scenarios = json.loads(DATASET_PATH.read_text(encoding="utf-8"))

    print("=" * 80)
    print("DEMOGRAFY CONVERSATION STRESS EVAL")
    print(f"Scenarios: {len(scenarios)}")
    print("=" * 80)
    print()

    results: list[dict] = []
    total_score = 0
    for scenario in scenarios:
        result = _run_scenario(scenario)
        results.append(result)
        total_score += int(result.get("judge_score") or 0)
        _save(results)

    passed = [r for r in results if r["judge_score"] >= 4 and not r["rule_failures"]]
    failed = [r for r in results if r["judge_score"] < 4 or r["rule_failures"]]
    avg = total_score / len(results) if results else 0

    print("=" * 80)
    print("CONVERSATION STRESS EVAL SUMMARY")
    print("=" * 80)
    print(f"Total scenarios: {len(results)}")
    print(f"Passed (judge >= 4 AND no rule failures): {len(passed)}")
    print(f"Failed: {len(failed)}")
    print(f"Average judge score: {avg:.2f}/5")
    print()
    if failed:
        print("FAILED SCENARIOS:")
        for r in failed:
            reason = r["judge_reasoning"]
            extra = f" + {len(r['rule_failures'])} rule failure(s)" if r["rule_failures"] else ""
            print(f"  - {r['id']} (score {r['judge_score']}/5{extra}): {reason}")
        print()
    print(f"Full results: {RESULTS_PATH}")


if __name__ == "__main__":
    main()
