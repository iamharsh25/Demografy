# Evaluation suites

Quality checks are split into three folders. **Run all commands from the Demografy repo root.**

| Folder | Purpose | Main command | Output (in same folder) |
|--------|---------|--------------|-------------------------|
| **`GoldenDatasetEval/`** | Single-turn golden questions + SQL pattern + LLM judge | `python eval/GoldenDatasetEval/run_eval.py` | `results.json` |
| **`LangsmithEval/`** | Workspace / recent-run verification + JSON report | `python eval/LangsmithEval/run_langsmith_checks.py` | `langsmith_report.json` |
| **`ConversationEval/`** | Multi-turn stress scenarios + chips + judge | `python eval/ConversationEval/run_conversation_eval.py` | `conversation_results.json` |

Also in this directory:

- **`guardrail_smoke.py`** — Fast routing checks (no BigQuery). Run: `python eval/guardrail_smoke.py`
