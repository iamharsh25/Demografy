# Demografy Insights Chatbot

A natural-language AI assistant for the Demografy platform. Ask questions about Australian suburb demographics in plain English and get concise, data-driven answers backed by BigQuery.

**Built with:** Python · Streamlit · LangChain · Gemini · Google BigQuery · LangSmith

---

## What it does

Users ask questions like:

> "What are the top 3 suburbs in Victoria with the highest diversity index?"

The app:

1. Uses Gemini (via a LangChain SQL agent) to turn the question into SQL where needed  
2. Runs read-only queries against Demografy's BigQuery views  
3. Returns a **plain-English** answer (internal column names and SQL are not shown in the chat UI)  
4. Supports **login**, **per-session question limits**, **multi-thread chat history** on disk, and **optional follow-up suggestion chips** after each reply  

The current UI is **Streamlit v4** with a **custom chat widget** (persistent iframe + fragment-scoped agent runs to avoid page-wide flicker).

---

## Project structure (overview)

```
Demografy/
├── app.py                 # Entry: run `streamlit run app.py` (delegates to app_v4)
├── app_v4.py              # Page config, header/body, chat @st.fragment
├── components/            # Header, body, styles, state, chat_engine, chat_widget
├── agent/                 # sql_agent, prompts, suggestions
├── chat_history/          # JSONL storage, context block, thread list
├── auth/rbac.py           # Tiers and question limits
├── db/                    # BigQuery helpers
├── eval/                  # Golden dataset + eval scripts
├── ChatHistory/           # Runtime transcripts (gitignored); see chat_history/
├── .streamlit/config.toml # Theme + port (8502)
├── README.md              # This file
├── PROJECT_FILES.md       # What each file/folder does (detailed)
├── HOW_IT_WORKS.md        # Plain-English architecture for the team
└── CHANGELOG.md
```

For a **line-by-line map** of source files, see **[PROJECT_FILES.md](PROJECT_FILES.md)**.

---

## Setup

### Prerequisites

- **Python 3.11+** — `python3 --version`  
- **Git**  
- A terminal  

### Clone and install

```bash
git clone https://github.com/iamharsh25/Demografy.git
cd Demografy
python3 -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Credentials

```bash
cp .env.template .env
```

Edit `.env`:

| Variable | Purpose |
|----------|---------|
| `GOOGLE_APPLICATION_CREDENTIALS` | Full path to your GCP service account JSON (BigQuery) |
| `GEMINI_API_KEY` | [Google AI Studio](https://aistudio.google.com) API key |
| `LANGCHAIN_API_KEY` | [LangSmith](https://smith.langchain.com) (optional but recommended) |

Never commit `.env` or `*.json` key files.

### Run the app

```bash
streamlit run app.py
```

This repo sets **`port = 8502`** in `.streamlit/config.toml`, so the app is typically at:

**http://localhost:8502**

(If you remove or override that file, Streamlit defaults to port `8501`.)

### Quick verification

Sign in (demo users from `auth/rbac.py`), then ask:

> "What are the top 5 most diverse suburbs in Victoria?"

You should see real suburb names and metrics explained in natural language. If you see connection or permission errors, check `GOOGLE_APPLICATION_CREDENTIALS` and restart Streamlit.

---

## Evaluation

Two complementary evaluation suites live under [`eval/`](eval).

### 1. Golden-dataset eval (project deliverable)

Single-turn accuracy with SQL-pattern matching and an LLM judge per question.

```bash
python eval/run_eval.py
```

Reads [`eval/golden_dataset.json`](eval/golden_dataset.json), writes
[`eval/results.json`](eval/results.json), and prints a pass/fail summary.

### 2. Conversation stress eval (internal QA)

Multi-turn scenarios that exercise follow-up understanding, suggested
follow-up chips, and conversational memory. Each scenario runs through the
real `agent.sql_agent.ask` plus `agent.suggestions.generate_suggestions`, with
in-memory `history` (does not write to `ChatHistory/`). Every turn is checked
against rules (no SQL / `kpi_*` leak, chips end with `?`, max 3 chips), and the
whole transcript is scored 1-5 by a Gemini judge.

```bash
python eval/run_conversation_eval.py
```

Reads [`eval/conversation_stress_dataset.json`](eval/conversation_stress_dataset.json)
and writes [`eval/conversation_results.json`](eval/conversation_results.json).
This is **internal QA**, not part of the golden-dataset deliverable.

### LangSmith tracing for evals

Both evals run through LangChain, so traces appear in the LangSmith project
named by `LANGCHAIN_PROJECT` (default `demografy-chatbot`). To confirm:

```bash
python eval/verify_langsmith.py --smoke           # add a fresh trace + list runs
python eval/langsmith_account_check.py            # which workspace owns your key
```

---

## Website embedding and “plugin” integrations

**Today:** the chat is a **Streamlit application**, not a drop-in `<script>` for arbitrary websites. Integration options you can support **right now**:

| Approach | Effort for the customer | Notes |
|----------|-------------------------|--------|
| **Link** | Trivial | Button or link to your hosted Streamlit URL (e.g. Streamlit Community Cloud or your own server). |
| **iframe** | Low | Embed your hosted app: `<iframe src="https://your-app-url" ...></iframe>`. You must allow framing (CSP / `X-Frame-Options`) on your host. Height, mobile UX, and cookies for login need thought. |
| **Self-host** | Medium | They clone this repo, set `.env`, and run `streamlit run app.py` behind their reverse proxy / domain. |

**Future plugin model:** a separate **HTTP API** (e.g. FastAPI) that wraps the same `sql_agent.ask()` logic with API keys or JWTs would let **any** frontend (React, Vue, mobile) call Demografy as a backend service. That layer is not in this repo yet; treat it as a product roadmap item for true “plugin” parity with SaaS chat widgets.

---

## Troubleshooting

| Problem | What to try |
|---------|-------------|
| `ModuleNotFoundError` | Activate the venv: `source venv/bin/activate` |
| Wrong port / bookmarked URL | Use **8502** if using the bundled `.streamlit/config.toml` |
| BigQuery / auth errors | Verify `GOOGLE_APPLICATION_CREDENTIALS` path and IAM roles |
| VS Code import squiggles | Select interpreter: `./venv/bin/python` |
| **LangSmith shows 0 traces** | See [LangSmith tracing](#langsmith-tracing) below. |

### LangSmith tracing

If **`verify_langsmith.py` shows runs** but the **LangSmith website** shows **0 traces**, you are almost always in the **wrong workspace** in the browser (the API key is scoped to one workspace; the UI defaults to another).

**Confirm which workspace your key uses:**

```bash
python eval/langsmith_account_check.py
```

That prints the **workspace display name**, **workspace ID**, **project ID**, **run count**, and a **direct URL** like  
`https://smith.langchain.com/o/<workspace-id>/projects/p/<project-id>`  
Open that link while logged into LangSmith (same account that created the API key in `.env`). You should see all traces there—use that page for **deliverable screenshots**.

Other checks:

1. **`.env` in the repo root** must include `LANGCHAIN_TRACING_V2=true`, `LANGCHAIN_API_KEY`, and `LANGCHAIN_PROJECT=demografy-chatbot` (see `.env.template`). Restart the app after editing.
2. In the UI, use the **workspace switcher** (often bottom-left or next to your org name) until it matches the **display name** from `langsmith_account_check.py`.
3. **Open the project, not only Home:** **Tracing** → **`demografy-chatbot`** → **Runs**.

The app loads `.env` from the **Demografy directory** automatically (even if you start Streamlit from a parent folder) so LangChain sees tracing variables before it initialises.

---

## Data reference

- **Main analytical view:** `demografy.prod_tables.a_master_view` (and related ref tables as configured in the agent)  
- **Coverage:** thousands of Australian SA2 suburbs  

### Exploring other BigQuery tables

The LangChain agent is restricted to **`a_master_view`** by default (`agent/sql_agent.py`). To **inventory every dataset/table/column** in your GCP project (so you can plan joins, extra dimensions, or benchmarks), run from the **Demografy** directory with credentials in `.env`:

```bash
python db/evaluate_bigquery_catalog.py
# optional: row counts per base table (slower)
python db/evaluate_bigquery_catalog.py --with-counts
```

This writes **`db/bigquery_catalog_snapshot.md`** and **`db/bigquery_catalog_snapshot.json`** (JSON is gitignored). Review the Markdown snapshot, then extend **`FEW_SHOT_PREFIX`** / **`include_tables`** only after you know join keys and allowed scopes.

The chat surfaces metrics in **plain English**. Internally, KPI columns map roughly as follows (see `agent/prompts.py` for full agent context):

| Column | Metric (user-facing name) | Typical range |
|--------|---------------------------|---------------|
| `kpi_1_val` | Prosperity score | 0–100 |
| `kpi_2_val` | Diversity index | 0–1 |
| `kpi_3_val` | Migration footprint | 0–100% |
| `kpi_4_val` | Learning level | 0–100% |
| `kpi_5_val` | Social housing | 0–100% |
| `kpi_6_val` | Home ownership / resident equity | 0–100% |
| `kpi_7_val` | Rental access | 0–100% |
| `kpi_8_val` | Resident anchor | 0–100% |
| `kpi_9_val` | Household mobility potential | 0–1 |
| `kpi_10_val` | Young family indicator | 0–100% |

---

## User tiers

| Tier | Questions per session (typical) |
|------|----------------------------------|
| Free | 5 |
| Basic | 20 |
| Pro | 50 |

(Configured in `auth/rbac.py`.)

---

## Architecture (high level)

```
Browser (Streamlit + custom chat iframe)
    ↓ component value (question / new_chat / open_thread)
components/chat_engine.py
    ↓ last_n_turns from chat_history/storage.py
agent/sql_agent.py  →  Gemini + BigQuery (read-only)
    ↓
Answer + optional agent/suggestions.py chips
    ↓
Session state + JSONL under ChatHistory/<user>/
```

Observability: LangSmith when configured.

---

## Security notes

- Secrets stay in `.env` and are gitignored.  
- Agent prompts and sanitisation discourage destructive SQL and hide internal schema details from end users.  
- Queries should remain bounded (e.g. `LIMIT`) per agent configuration.  

---

## More documentation

- **[PROJECT_FILES.md](PROJECT_FILES.md)** — what each file does  
- **[HOW_IT_WORKS.md](HOW_IT_WORKS.md)** — narrative explanation for stakeholders  
- **[CHANGELOG.md](CHANGELOG.md)** — version history  
