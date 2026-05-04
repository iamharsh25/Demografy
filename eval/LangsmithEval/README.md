# LangSmith checks

Scripts to confirm which **LangSmith workspace** your API key uses and whether **recent runs** appear for `LANGCHAIN_PROJECT`.

## Commands (from repo root)

```bash
python eval/LangsmithEval/langsmith_account_check.py
python eval/LangsmithEval/verify_langsmith.py
python eval/LangsmithEval/verify_langsmith.py --smoke
python eval/LangsmithEval/run_langsmith_checks.py
python eval/LangsmithEval/run_langsmith_checks.py --smoke
```

## Output

- `langsmith_report.json` — written by `run_langsmith_checks.py` only (workspace + project + recent runs summary).
