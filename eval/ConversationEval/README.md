# Conversation stress evaluation

Multi-turn scenarios: follow-ups, chips, rule checks (no SQL / `kpi_*` leak), LLM judge over the full transcript.

## Run (from repo root)

```bash
python eval/ConversationEval/run_conversation_eval.py
python eval/ConversationEval/run_education_conversation_eval.py
python eval/ConversationEval/run_education_conversation_eval.py --id drill-down --output eval/ConversationEval/my_run.json
```

## Files

- `conversation_stress_dataset.json` — scenario definitions
- `conversation_judge.py` — transcript scorer
- `conversation_results.json` — **output** of the full suite (incremental while running)
- `education_conversation_results.json` — **output** of the single-scenario helper (default path)
