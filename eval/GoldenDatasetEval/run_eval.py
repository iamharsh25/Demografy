"""
Automated evaluation for the golden dataset (single-turn).

Run from repo root::

    python eval/GoldenDatasetEval/run_eval.py

Reads ``golden_dataset.json`` in this directory and writes ``results.json`` here.

LangSmith: loads ``.env`` from the Demografy root *before* importing the SQL agent so
``LANGCHAIN_TRACING_V2`` / ``LANGCHAIN_API_KEY`` / ``LANGCHAIN_PROJECT`` apply to
LangChain runs. Each question is wrapped in a ``traceable`` span; the judge LLM is
traced separately (see ``judge.py``). Requires the same .env setup as the Streamlit app.
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_ROOT = _HERE.parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from dotenv import load_dotenv
from langsmith import traceable

load_dotenv(_ROOT / ".env")

from agent.sql_agent import ask  # noqa: E402
from judge import score_answer  # noqa: E402


DATASET_PATH = _HERE / "golden_dataset.json"
RESULTS_PATH = _HERE / "results.json"

_LANGSMITH_PROJECT = os.getenv("LANGCHAIN_PROJECT") or os.getenv("LANGSMITH_PROJECT")


def _tracing_env_ready() -> bool:
    v2 = (os.getenv("LANGCHAIN_TRACING_V2") or os.getenv("LANGSMITH_TRACING_V2") or "").lower()
    tracing_on = v2 in ("1", "true", "yes")
    key = os.getenv("LANGCHAIN_API_KEY") or os.getenv("LANGSMITH_API_KEY")
    return bool(tracing_on and key)


def _langsmith_api_key() -> str | None:
    return os.getenv("LANGCHAIN_API_KEY") or os.getenv("LANGSMITH_API_KEY")


def _langsmith_result_fields() -> dict:
    """Per-row LangSmith / LangChain metadata (same snapshot for the whole eval run)."""
    langchain_connected = _tracing_env_ready()
    langsmith_account: str | None = None
    log_sent_to_langsmith = False
    key = _langsmith_api_key()
    if not key:
        return {
            "langchain_connected": False,
            "log_sent_to_langsmith": False,
            "langsmith_account": None,
        }
    try:
        from langsmith import Client

        client = Client(api_key=key)
        settings = client._get_settings()
        langsmith_account = str(settings.display_name or "").strip() or None
        if settings.tenant_handle:
            langsmith_account = (
                f"{langsmith_account} ({settings.tenant_handle})"
                if langsmith_account
                else str(settings.tenant_handle)
            )
    except Exception:
        return {
            "langchain_connected": langchain_connected,
            "log_sent_to_langsmith": False,
            "langsmith_account": None,
        }

    try:
        next(iter(client.list_runs(limit=1)), None)
        log_sent_to_langsmith = bool(langchain_connected)
    except Exception:
        log_sent_to_langsmith = False

    return {
        "langchain_connected": langchain_connected,
        "log_sent_to_langsmith": log_sent_to_langsmith,
        "langsmith_account": langsmith_account,
    }


def _print_langsmith_banner() -> None:
    project = _LANGSMITH_PROJECT or "(default from LANGCHAIN_PROJECT / LangSmith client)"
    if _tracing_env_ready():
        print(f"LangSmith: tracing env OK — runs go to project {project!r}")
    else:
        print(
            "LangSmith: tracing may be OFF — set LANGCHAIN_TRACING_V2=true and "
            "LANGCHAIN_API_KEY in Demografy/.env (optional: LANGCHAIN_PROJECT). "
            "The eval still runs; see README 'LangSmith tracing'."
        )
    print()


def save_results(results: list) -> None:
    RESULTS_PATH.write_text(json.dumps(results, indent=2), encoding="utf-8")


@traceable(
    name="golden_dataset_item",
    run_type="chain",
    tags=["golden_dataset_eval"],
    project_name=_LANGSMITH_PROJECT,
)
def _evaluate_one(
    question_id: int,
    question: str,
    expected_pattern: str,
    validation: str,
    source: str | None,
) -> dict:
    """One golden row: ``ask()`` + SQL regex check + LLM judge (nested LangSmith spans)."""
    answer, sql_query, _meta = ask(question)

    sql_match = bool(
        re.search(expected_pattern, sql_query or "", re.IGNORECASE | re.DOTALL)
    )

    judge_result = score_answer(question, answer, validation)
    judge_score = judge_result["score"]
    reasoning = judge_result["reasoning"]

    return {
        "id": question_id,
        "source": source,
        "question": question,
        "answer": answer,
        "sql": sql_query,
        "sql_pattern_match": sql_match,
        "judge_score": judge_score,
        "reasoning": reasoning,
    }


def run_evaluation() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    dataset = json.loads(DATASET_PATH.read_text(encoding="utf-8"))

    results: list = []
    total_score = 0

    print("=" * 80)
    print("DEMOGRAFY GOLDEN DATASET EVAL")
    print(f"Dataset: {DATASET_PATH}")
    print(f"Output:  {RESULTS_PATH}")
    print("=" * 80)
    print()
    _print_langsmith_banner()

    ls_fields = _langsmith_result_fields()

    for item in dataset:
        question_id = item["id"]
        question = item["question"]
        expected_pattern = item["expected_sql_pattern"]
        validation = item["validation"]

        print(f"[{question_id}/{len(dataset)}] Testing: {question}")
        print("-" * 80)

        try:
            print("[ok] Running ask() + judge...", flush=True)
            row = _evaluate_one(
                question_id,
                question,
                expected_pattern,
                validation,
                item.get("source"),
            )
            print("[ok] Answer received", flush=True)
            print(
                f"[ok] SQL pattern match: {'YES' if row['sql_pattern_match'] else 'NO'}",
                flush=True,
            )

            row_out = {
                "question": row["question"],
                "answer": row["answer"],
                "langchain_connected": ls_fields["langchain_connected"],
                "log_sent_to_langsmith": ls_fields["log_sent_to_langsmith"],
                "langsmith_account": ls_fields["langsmith_account"],
                "judge_score": row["judge_score"],
                "sql": row["sql"],
                "sql_pattern_match": row["sql_pattern_match"],
                "reasoning": row["reasoning"],
                "id": row["id"],
                "source": row.get("source"),
            }
            total_score += row_out["judge_score"]
            results.append(row_out)
            save_results(results)

            print(f"[ok] Judge score: {row_out['judge_score']}/5")
            print(f"  Reasoning: {row_out['reasoning']}")

        except Exception as e:
            print(f"[failed] {str(e)}")
            results.append(
                {
                    "question": question,
                    "answer": None,
                    "langchain_connected": ls_fields["langchain_connected"],
                    "log_sent_to_langsmith": ls_fields["log_sent_to_langsmith"],
                    "langsmith_account": ls_fields["langsmith_account"],
                    "judge_score": 0,
                    "sql": None,
                    "sql_pattern_match": False,
                    "reasoning": None,
                    "id": question_id,
                    "source": item.get("source"),
                    "error": str(e),
                }
            )
            save_results(results)

        print()

    print("=" * 80)
    print("EVALUATION SUMMARY")
    print("=" * 80)

    passed = [r for r in results if r.get("judge_score", 0) >= 4]
    failed = [r for r in results if r.get("judge_score", 0) < 4]
    avg_score = total_score / len(dataset) if dataset else 0

    print(f"Total questions: {len(dataset)}")
    print(f"Passed (score >= 4): {len(passed)}")
    print(f"Failed (score < 4): {len(failed)}")
    print(f"Average score: {avg_score:.2f}/5")
    print()

    if failed:
        print("FAILED QUESTIONS:")
        for r in failed:
            print(f"  - Q{r['id']}: {r['question']} (score: {r.get('judge_score', 0)}/5)")

    print()
    print(f"Evaluation complete. Full results saved to {RESULTS_PATH}")
    save_results(results)


if __name__ == "__main__":
    run_evaluation()
