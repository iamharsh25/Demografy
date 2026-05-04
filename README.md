# Demografy Insights Chatbot

A natural-language AI assistant for the Demografy platform. Ask questions about Australian suburb demographics in plain English and get concise, data-driven answers backed by BigQuery.

**Built with:** Python · Streamlit · LangChain · Gemini · Google BigQuery · LangSmith

---

## What it does

Users ask questions like:

> "What are the top 3 suburbs in Victoria with the highest diversity index?"

The app:

1. Routes the question through **`app_v4.py`** and **`components/chat_engine.py`** (the chat runs inside an **`@st.fragment`** so long agent work does not trigger a full-page Streamlit rerun overlay).
2. Uses a **custom chat widget** (persistent **iframe** + `st.components` bridge) for the typing UI; actions like **new chat**, **open thread**, and **send question** are dispatched from the widget into Python.
3. Uses Gemini (via a LangChain SQL agent) to turn the question into SQL where needed, runs **read-only** queries against Demografy's BigQuery views, and returns a **plain-English** answer (internal column names stay in prompts/SQL—not surfaced as jargon in the main reply).
4. Keeps **per-thread** context: recent turns are loaded from **`chat_history`** JSONL under `ChatHistory/<user>/`, so follow-ups stay scoped to the active thread.
5. Supports **sign-in**, **per-session question limits**, **multi-thread chat history**, and **optional follow-up suggestion chips** after each reply (see `components/user_profile.py` and `auth/rbac.py`).

For a longer stakeholder-friendly walkthrough (stack roles, file map, step-by-step request path), see **[HOW_IT_WORKS.md](HOW_IT_WORKS.md)**. That doc is the narrative companion to this README; when they disagree on an implementation detail, **this README and the code win**.

---

## How it works (at a glance)

**Stack roles** (same story as `HOW_IT_WORKS.md`, shortened):

| Piece | Role |
|--------|------|
| **Streamlit (`app_v4.py` + `components/`)** | Layout, header, login/profile, body, styles; hosts the chat iframe and fragments. |
| **`components/chat_engine.py`** | Turns bridge events into `sql_agent.ask(...)`, updates session state, appends JSONL transcripts, applies RBAC limits and cooldowns. |
| **LangChain + `agent/sql_agent.py`** | SQL agent with schema / checker / query tools backed by BigQuery. |
| **`agent/prompts.py`** | KPI naming, safety rules, few-shot patterns for `a_master_view`. |
| **`agent/suggestions.py`** | Follow-up chips after an answer. |
| **BigQuery** | Live suburb metrics. |
| **LangSmith** (optional) | Traces for debugging and eval visibility. |

**One request, end-to-end:** user message in the iframe → bridge payload (`question` / `new_chat` / `open_thread`) → `chat_engine` loads **`last_n_turns`** for `chat_thread_id` → **`sql_agent.ask`** runs the LangChain agent → answer (and optional chart path / chips) → UI + disk history. Optional LangSmith traces mirror the same steps.

---

## Project structure (overview)

```
Demografy/
├── app.py                 # Entry: `streamlit run app.py` (delegates to app_v4)
├── app_v4.py              # Page config, header/body, chat @st.fragment
├── components/            # Header, body, styles, state, chat_engine, chat_widget (iframe)
├── agent/                 # sql_agent, prompts, suggestions, guardrails, templates
├── chat_history/          # JSONL storage, context block, thread list
├── auth/                  # rbac, cooldown
├── db/                    # BigQuery helpers (+ optional catalog scripts)
├── eval/                  # GoldenDatasetEval, LangsmithEval, ConversationEval; see below
├── ChatHistory/           # Runtime transcripts (gitignored)
├── .streamlit/config.toml # Theme + port (8502)
├── README.md              # This file
├── PROJECT_FILES.md       # Per-file map
├── HOW_IT_WORKS.md        # Plain-English architecture for stakeholders
└── CHANGELOG.md
```

For a **line-by-line map** of source files, see **[PROJECT_FILES.md](PROJECT_FILES.md)**. For **eval-only** commands and outputs, see **[eval/README.md](eval/README.md)**.

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

Quality checks live under **`eval/`** and are split into **three suite folders** plus a **fast smoke** script. **Run every command from the Demografy repo root** (same `.env` as the app).

| Suite | What it measures | Command | Default output |
|--------|------------------|---------|----------------|
| **GoldenDatasetEval** | Single-turn accuracy: golden questions, **SQL pattern** checks, **LLM judge** per row | `python eval/GoldenDatasetEval/run_eval.py` | `eval/GoldenDatasetEval/results.json` |
| **ConversationEval** | Multi-turn behaviour: follow-ups, **suggestion chips**, rule checks (no SQL / `kpi_*` leak, chip shape), **transcript judge** | `python eval/ConversationEval/run_conversation_eval.py` | `eval/ConversationEval/conversation_results.json` |
| **LangsmithEval** | Which **workspace** your API key uses and whether **recent runs** exist for `LANGCHAIN_PROJECT` | `python eval/LangsmithEval/run_langsmith_checks.py` | `eval/LangsmithEval/langsmith_report.json` |
| **Guardrail smoke** | Fast **routing / guardrail** checks **without BigQuery** | `python eval/guardrail_smoke.py` | (console) |

More detail per folder: **[eval/README.md](eval/README.md)**, **[eval/GoldenDatasetEval/README.md](eval/GoldenDatasetEval/README.md)**, **[eval/ConversationEval/README.md](eval/ConversationEval/README.md)**, **[eval/LangsmithEval/README.md](eval/LangsmithEval/README.md)**.

### Golden dataset eval (deliverable-style QA)

- **Input:** [`eval/GoldenDatasetEval/golden_dataset.json`](eval/GoldenDatasetEval/golden_dataset.json) — `core_set` (ids 1–5) and `comparison_followup` (ids 6–10) covering diversity, prosperity, learning, social housing, rental access, and cross-state comparisons.
- **How it runs:** For each row, the runner exercises the real agent path (LangChain + BigQuery when configured), records the model answer and SQL, checks **expected SQL patterns**, then calls **`judge.py`** (LLM) for a quality score and reasoning.
- **Output:** [`eval/GoldenDatasetEval/results.json`](eval/GoldenDatasetEval/results.json) — per question: e.g. `question`, `answer`, `sql`, `sql_pattern_match`, `judge_score`, `reasoning`, LangSmith connectivity flags, `id`, `source`, or `error` on failure.
- **LangSmith:** With tracing env vars set, golden rows are wrapped in traceable spans tagged e.g. `golden_dataset_eval` and `judge` so you can filter runs in the LangSmith UI (see golden eval README).

### Conversation stress eval (internal multi-turn QA)

- **Input:** [`eval/ConversationEval/conversation_stress_dataset.json`](eval/ConversationEval/conversation_stress_dataset.json) — scripted multi-turn scenarios.
- **How it runs:** Uses the real **`agent.sql_agent.ask`** and **`agent.suggestions.generate_suggestions`** with in-memory `history` (does **not** write to `ChatHistory/`). Each turn is validated against **rules** (no internal SQL/KPI leakage to the user-facing text, chips end with `?`, max chips, etc.), then **`conversation_judge.py`** scores the full transcript (e.g. 1–5).
- **Output:** [`eval/ConversationEval/conversation_results.json`](eval/ConversationEval/conversation_results.json).
- **Education / single-scenario runs:**  
  `python eval/ConversationEval/run_education_conversation_eval.py`  
  Optional: `--id <scenario> --output path/to.json` (see ConversationEval README).

### LangSmith verification

Useful when traces “disappear” in the browser (wrong workspace) or before demos:

```bash
python eval/LangsmithEval/verify_langsmith.py --smoke   # optional smoke trace + list runs
python eval/LangsmithEval/langsmith_account_check.py    # workspace + project the key sees
python eval/LangsmithEval/run_langsmith_checks.py       # writes langsmith_report.json
```

Both **golden** and **conversation** evals go through LangChain where applicable, so runs can appear under the project named by **`LANGCHAIN_PROJECT`** (default `demografy-chatbot` in `.env.template`).

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
python eval/LangsmithEval/langsmith_account_check.py
```

That prints the **workspace display name**, **workspace ID**, **project ID**, **run count**, and a **direct URL** like  
`https://smith.langchain.com/o/<workspace-id>/projects/p/<project-id>`  
Open that link while logged into LangSmith (same account that created the API key in `.env`). You should see all traces there—use that page for **deliverable screenshots**.

Other checks:

1. **`.env` in the repo root** must include `LANGCHAIN_TRACING_V2=true`, `LANGCHAIN_API_KEY`, and `LANGCHAIN_PROJECT=demografy-chatbot` (see `.env.template`). Restart the app after editing.
2. In the UI, use the **workspace switcher** until it matches the **display name** from `langsmith_account_check.py`.
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
Browser (Streamlit layout + custom chat iframe)
    ↓ st.components bridge (question / new_chat / open_thread)
components/chat_engine.py  [@st.fragment — scoped loading UI]
    ↓ last_n_turns from chat_history/storage.py (per chat_thread_id)
agent/sql_agent.py  →  Gemini + BigQuery (read-only)
    ↓
Plain-English answer + optional charts path + agent/suggestions.py chips
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
- **[HOW_IT_WORKS.md](HOW_IT_WORKS.md)** — plain-English architecture for stakeholders (stack, journey, file map)  
- **[eval/README.md](eval/README.md)** — evaluation suite index  
- **[CHANGELOG.md](CHANGELOG.md)** — version history  
