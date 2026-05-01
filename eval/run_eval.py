"""
Automated evaluation script for the Demografy chatbot.

Runs all questions from the golden dataset through the chatbot,
scores each answer with LLM-as-a-judge, and generates a report.
"""

import json
import re
import sys

from agent.sql_agent import ask
from eval.judge import score_answer


def save_results(results):
    with open("eval/results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)


def run_evaluation():
    """
    Runs the full evaluation suite and prints a report.
    """
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    with open("eval/golden_dataset.json", "r", encoding="utf-8") as f:
        dataset = json.load(f)

    results = []
    total_score = 0

    print("=" * 80)
    print("DEMOGRAFY CHATBOT EVALUATION")
    print("=" * 80)
    print()

    for item in dataset:
        question_id = item["id"]
        question = item["question"]
        expected_pattern = item["expected_sql_pattern"]
        validation = item["validation"]

        print(f"[{question_id}/10] Testing: {question}")
        print("-" * 80)

        try:
            answer, sql_query = ask(question)
            print("[ok] Answer received", flush=True)

            sql_match = bool(re.search(expected_pattern, sql_query or "", re.IGNORECASE | re.DOTALL))
            print(f"[ok] SQL pattern match: {'YES' if sql_match else 'NO'}", flush=True)

            print("Scoring with judge...", flush=True)
            judge_result = score_answer(question, answer, validation)
            score = judge_result["score"]
            reasoning = judge_result["reasoning"]

            total_score += score

            results.append({
                "id": question_id,
                "question": question,
                "answer": answer,
                "sql": sql_query,
                "sql_pattern_match": sql_match,
                "score": score,
                "reasoning": reasoning,
            })
            save_results(results)

            print(f"[ok] Judge score: {score}/5")
            print(f"  Reasoning: {reasoning}")

        except Exception as e:
            print(f"[failed] {str(e)}")
            results.append({
                "id": question_id,
                "question": question,
                "error": str(e),
                "score": 0,
            })
            save_results(results)

        print()

    print("=" * 80)
    print("EVALUATION SUMMARY")
    print("=" * 80)

    passed = [r for r in results if r.get("score", 0) >= 4]
    failed = [r for r in results if r.get("score", 0) < 4]
    avg_score = total_score / len(dataset) if dataset else 0

    print(f"Total questions: {len(dataset)}")
    print(f"Passed (score >= 4): {len(passed)}")
    print(f"Failed (score < 4): {len(failed)}")
    print(f"Average score: {avg_score:.2f}/5")
    print()

    if failed:
        print("FAILED QUESTIONS:")
        for r in failed:
            print(f"  - Q{r['id']}: {r['question']} (score: {r.get('score', 0)}/5)")

    print()
    print("Evaluation complete. Full results saved to eval/results.json")
    save_results(results)


if __name__ == "__main__":
    run_evaluation()
