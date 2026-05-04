# Golden dataset evaluation

Single-turn questions with **SQL pattern checks** and an **LLM judge** (`judge.py`).

## Dataset shape

- **`core_set` (ids 1–5):** diversity ranking (VIC), NSW prosperity average, best state for learning, social housing threshold, most affordable rental suburbs.
- **`comparison_followup` (ids 6–10):** paired-state / cross-state comparisons on the same KPI themes (diversity, prosperity, learning, social housing, rental access).

## Run

From the **Demografy** repo root:

```bash
python eval/GoldenDatasetEval/run_eval.py
```

## LangSmith

Use the same `.env` as the app: `LANGCHAIN_TRACING_V2=true`, `LANGCHAIN_API_KEY`, and optionally `LANGCHAIN_PROJECT`. The runner loads `.env` before importing the agent so LangChain SQL traces are emitted; each golden row is also wrapped in a LangSmith `traceable` span tagged `golden_dataset_eval`, and the judge is tagged `judge`. Filter by those tags in the LangSmith UI. If the banner says tracing may be off, traces may still appear for some paths—confirm with `python eval/LangsmithEval/verify_langsmith.py`.

## Output

Written only in this folder:

- `results.json` — one object per question, keys in order: `question`, `answer`, `langchain_connected`, `log_sent_to_langsmith`, `langsmith_account`, `judge_score`, `sql`, `sql_pattern_match`, `reasoning`, then `id` and `source`. On failure, `answer` / `sql` / `reasoning` are null and `error` is set. `log_sent_to_langsmith` is true only when LangChain tracing env is on **and** the LangSmith API accepts a test `list_runs` call (best-effort, not a per-span delivery guarantee).
