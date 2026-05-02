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

---

## Data reference

- **Main analytical view:** `demografy.prod_tables.a_master_view` (and related ref tables as configured in the agent)  
- **Coverage:** thousands of Australian SA2 suburbs  

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
