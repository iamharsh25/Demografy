# Changelog

All notable changes to this project are documented here.
Format: `[vX.Y.Z] — YYYY-MM-DD — Description`

---

## [Unreleased]

### Changed
- **Eval layout:** suites moved into `eval/GoldenDatasetEval/` (golden questions + `results.json`), `eval/LangsmithEval/` (account check, verify, `langsmith_report.json`), and `eval/ConversationEval/` (stress dataset, judges, conversation result JSON). Index: `eval/README.md`. Golden dataset expanded to 10 items (five client §6.2–style samples + five extended); align first five with the client PDF when available.

---

## [v0.1.0] — 2026-04-12 — Project Scaffold

### Added
- Full project folder structure created
- `.gitignore` — excludes secrets (.env, *.json), Source/ folder, Python cache
- `requirements.txt` — all Python dependencies listed
- `.env.template` — safe-to-commit template for environment variables
- `CHANGELOG.md` — this file
- `README.md` — setup instructions and project overview

### Notes
- BigQuery connection not yet active (waiting for service account key)
- No code logic yet — structure only

---

## [v0.2.0] — 2026-04-12 — Core Code

### Added
- `db/bigquery_client.py` — BigQuery connection using service account credentials
- `db/explore.py` — data exploration script (run once after getting SA key)
- `agent/prompts.py` — KPI name→column mappings + 8 few-shot SQL examples
- `agent/sql_agent.py` — LangChain SQL agent wiring Gemini to BigQuery
- `auth/rbac.py` — user tier lookup + question limit enforcement
- `app.py` — full Streamlit app (login screen + chat UI + sidebar)
- `.streamlit/config.toml` — Demografy brand colours (purple theme)
- All packages installed in venv (Python 3.13)

### Changed
- `app.py` — redesigned to collapsible left info panel + full-width chat on right
- Left panel collapses to a thin strip with ▶/◀ toggle button

### Notes
- Gemini API key and LangSmith API key configured in .env
- BigQuery connection not yet testable (waiting for service account JSON from Wayne)
- Streamlit UI launches correctly — chat UI and collapsible panel working

---

## [v0.3.0] — 2026-04-12 — BigQuery Live + Brand UI + SQL Visibility

### Added
- Full BigQuery integration — live suburb data now connected end-to-end
- `agent/sql_agent.py` — `ask()` now returns `(answer, sql_query)` tuple
- `app.py` — "🔍 View SQL Query" expander shows the exact SQL used for each answer
- SQL persists in chat history so previous queries remain viewable on scroll
- Gemini fallback mode — if BigQuery unavailable, answers from general AI knowledge with clear disclaimer

### Changed
- `agent/sql_agent.py` — fixed `credentials_path` arg (not supported; uses env var instead)
- `agent/sql_agent.py` — updated model to `gemini-2.5-flash` (confirmed working)
- `agent/prompts.py` — replaced generic examples with 9 real company SQL patterns from official Sample SQL Queries doc
- `agent/prompts.py` — strengthened rules: ALWAYS LIMIT, NEVER SELECT *, IS NOT NULL guards, descriptive aliases
- `.streamlit/config.toml` — updated to official Demografy brand colours from Brand Guidelines PDF
- `app.py` — full CSS redesign using official brand colours (gradient left panel, 3-colour tags, Open Sans font)
- `README.md` — complete rewrite with full step-by-step setup guide, troubleshooting table, architecture diagram

### Fixed
- `.env` updated with all 3 company credentials (BigQuery JSON, Gemini key, LangSmith key)
- LangSmith tracing now active — all queries visible in `demografy-chatbot` project

### Notes
- LangSmith is the company account — all query traces visible to Demografy team
- "Migratory - Offshore - Shipping" and "No usual address" are ABS statistical categories that may appear in diversity results — not real suburbs

---

## [v0.4.0] — 2026-04-12 — Live Agent Steps + Code Explanation Doc

### Added
- `app.py` — live agent step streaming using `StreamlitCallbackHandler` (each reasoning step appears in the UI as the agent thinks)
- `HOW_IT_WORKS.md` — plain-English explanation of the entire codebase for team onboarding

### Changed
- `agent/sql_agent.py` — `ask()` now accepts optional `callbacks` parameter for streaming steps to the UI
- `app.py` — removed `st.spinner` wrapper from BigQuery path; steps now stream live instead
