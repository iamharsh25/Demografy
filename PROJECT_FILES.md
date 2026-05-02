# Project file reference

This document describes what each important file and folder in the Demografy repository does. For setup steps, see [README.md](README.md). For a plain-English architecture walkthrough, see [HOW_IT_WORKS.md](HOW_IT_WORKS.md).

---

## Entry point

| Path | Role |
|------|------|
| `app.py` | **Run this.** Uses `runpy` to execute `app_v4.py` so `st.set_page_config` runs in a single, predictable context. Command: `streamlit run app.py`. |
| `app_v4.py` | **Main Streamlit app (v4).** Sets page config, loads CSS, renders header and body, and runs the chat inside an `@st.fragment` (`_chat_panel`) so the SQL agent does not fade the whole page. |

---

## `components/` — UI building blocks

| Path | Role |
|------|------|
| `components/__init__.py` | Package marker for the components namespace. |
| `components/header.py` | Renders the top bar: logo, menu, login/profile. |
| `components/logo.py` | Demografy logo markup/styling. |
| `components/menu.py` | Navigation links (Home, Features, etc.). |
| `components/user_profile.py` | Login dialog, profile dropdown, sign-out; resets chat state and calls `hydrate_chat_history` on login. |
| `components/body.py` | Hero section and marketing mockup card (iframe HTML/CSS). |
| `components/styles.py` | Global Streamlit CSS overrides (hide deploy chrome, chat iframe sizing, stale-block fixes for the custom chat component). |
| `components/state.py` | `init_session_state()` defaults (user, chat, thread id, suggestions); URL `?u=` restore; `hydrate_chat_history()` loads the latest thread from disk. |
| `components/chat_engine.py` | **Chat orchestration:** bridge payloads (`question`, `new_chat`, `open_thread`), RBAC limits, `ask()` invocation, persistence to JSONL, follow-up suggestion generation hook, fragment-friendly (no full `st.rerun`). |
| `components/chat_widget/__init__.py` | Declares the Streamlit custom component `demografy_chat_widget` and passes props (`messages`, `pending`, `threads`, `suggestions`, etc.). |
| `components/chat_widget/frontend/index.html` | **Chat UI (JS/CSS):** FAB, panel, expand/split, new chat (+), past-chats overlay, optimistic send, reconcile with Python args, suggestion chips. |

---

## `agent/` — AI and NL→SQL

| Path | Role |
|------|------|
| `agent/sql_agent.py` | **Core agent:** LangChain SQL agent over BigQuery, template fast-paths, chat history context, output sanitisation (no raw SQL/column names in user-facing text), optional state-swap follow-ups. |
| `agent/prompts.py` | Few-shot instructions, KPI semantics, output rules for the SQL agent. |
| `agent/suggestions.py` | LLM-generated follow-up question chips (Gemini flash-lite, timeout, sanitisation via `_strip_sql_from_answer`). |
| `agent/conversation.py` | Helpers for conversational behaviour (state aliases, metric notes). Used alongside or by agent flows where richer context is needed. |

---

## `chat_history/` — Persistent transcripts (v4)

| Path | Role |
|------|------|
| `chat_history/__init__.py` | Re-exports storage, context, thread listing helpers. |
| `chat_history/storage.py` | **On-disk format:** `ChatHistory/<user_id>/<timestamp>_<thread_id>.jsonl` — append/load/last-N-turns; `new_thread_id()`; legacy single-file migration. |
| `chat_history/context.py` | Builds a bounded text block from recent turns for the LLM context window. |
| `chat_history/thread_list.py` | Scans user directories to list past threads (title, updated time, counts) for the chat widget overlay. |

---

## `auth/` — Access control

| Path | Role |
|------|------|
| `auth/rbac.py` | User lookup by id, tier, per-session question limits, limit warnings. |

---

## `db/` — Database

| Path | Role |
|------|------|
| `db/bigquery_client.py` | BigQuery connection / helper used by the SQL agent path. |
| `db/explore.py` | Ad-hoc exploration script (not part of the live app). |

---

## `eval/` — Quality checks

| Path | Role |
|------|------|
| `eval/golden_dataset.json` | Reference Q&A pairs (`id`, `question`, `expected_sql_pattern`, `validation`) for `run_eval.py`. |
| `eval/run_eval.py` | Runs each golden item through `ask()`, pattern-checks SQL, scores with `judge.py`, writes `eval/results.json`. Run: `python eval/run_eval.py` from repo root (script fixes `PYTHONPATH`). |
| `eval/judge.py` | LLM-as-judge scoring for single-turn eval outputs (Gemini). |
| `eval/conversation_stress_dataset.json` | Multi-turn scenarios for the conversational stress eval (state swap, metric switch, limit swap, drill-down, edge cases). |
| `eval/run_conversation_eval.py` | Internal QA: drives each scenario through `ask` + `generate_suggestions`, runs rule checks (no SQL / `kpi_*` leak, chip shape), then scores the whole transcript with `conversation_judge.py`. Writes `eval/conversation_results.json`. |
| `eval/conversation_judge.py` | LLM judge for whole multi-turn transcripts (1-5 + reasoning). |
| `eval/verify_langsmith.py` | Lists recent LangSmith runs for `LANGCHAIN_PROJECT`; optional `--smoke` to call `ask()` once. Confirms tracing + API key. |
| `eval/langsmith_account_check.py` | Prints workspace name/ID and a direct browser URL for `LANGCHAIN_PROJECT` so the UI matches the API key (fixes “0 traces” in the wrong workspace). |
| `eval/results.json` | Generated report from the last single-turn eval (gitignored if added). |
| `eval/conversation_results.json` | Generated report from the last conversation stress eval. |

---

## `utils/` — Legacy / auxiliary

| Path | Role |
|------|------|
| `utils/chat_history.py` | **Legacy** JSON session store under a `chat_history/` directory name (different from the v4 `chat_history/` **package** and `ChatHistory/` data folder). Prefer the package + `ChatHistory/` layout for the current app. |

---

## Runtime data (not committed)

| Path | Role |
|------|------|
| `ChatHistory/` | Created at runtime: per-user folders, one `.jsonl` file per conversation thread. Gitignored content; structure is defined in `chat_history/storage.py`. |

---

## Configuration and dependencies

| Path | Role |
|------|------|
| `.streamlit/config.toml` | Streamlit theme (Demografy colours) and **server port** (default in this repo: `8502`). |
| `requirements.txt` | Python dependencies for `pip install -r requirements.txt`. |
| `.env.template` | Example environment variables; copy to `.env` (gitignored). |
| `.gitignore` | Excludes secrets, venv, `ChatHistory/`, `.env`, etc. |

---

## Documentation and assets

| Path | Role |
|------|------|
| `README.md` | Clone, install, env vars, run instructions, embedding notes, troubleshooting. |
| `HOW_IT_WORKS.md` | Team-friendly explanation of the stack and request flow. |
| `CHANGELOG.md` | Version history. |
| `PROJECT_FILES.md` | This file — map of source files to responsibilities. |
| `Source/` | Brand and reference materials (e.g. brand guidelines PDF). |

---

## Request flow (short)

1. User opens `app.py` → `app_v4.py` renders shell + (if logged in) chat fragment.  
2. Chat widget posts `{ action, question?, thread_id?, ts }` → `maybe_consume_bridge` → `handle_new_question` / thread switches.  
3. `resolve_pending_question` loads `last_n_turns` from `chat_history/storage.py`, calls `agent.sql_agent.ask()`, appends assistant message, optionally fills `chat_suggestions`.  
4. UI updates via the custom component iframe without full page reload (fragment + persistent component).
