# Demografy Insights Chatbot

A natural-language AI chatbot for the Demografy platform. Ask questions about Australian suburb demographics in plain English and get instant, data-driven answers.

**Built with:** Python · Streamlit · LangChain · Gemini 2.5 Flash · Google BigQuery · LangSmith

---

## What It Does

Users type questions like:
> "What are the top 3 suburbs in Victoria with the highest diversity index?"

The bot:
1. Translates the question into SQL using Gemini AI
2. Runs the query against Demografy's BigQuery database
3. Returns a clear, plain-English answer
4. Shows the exact SQL query used (expandable in the UI)

---

## Project Structure

```
Demografy/
├── app.py                    # Streamlit app — entry point, run this
├── agent/
│   ├── sql_agent.py          # LangChain SQL agent (core AI logic)
│   └── prompts.py            # Few-shot examples + KPI column mappings
├── auth/
│   └── rbac.py               # User tier lookup + question limits
├── db/
│   ├── bigquery_client.py    # BigQuery connection wrapper
│   └── explore.py            # One-time data exploration script
├── eval/
│   ├── golden_dataset.json   # Test Q&A pairs
│   ├── run_eval.py           # Automated evaluation script
│   └── judge.py              # LLM-as-a-judge scorer
├── .streamlit/
│   └── config.toml           # Demografy brand theme (colours, font)
├── .env.template             # Copy this to .env and fill in your keys
├── requirements.txt          # All Python dependencies
└── CHANGELOG.md              # Version history
```

---

## Setup Instructions

Follow these steps in order. Takes about 10 minutes.

### Step 1 — Prerequisites

Make sure you have:
- **Python 3.11 or higher** — check with `python3 --version`
- **Git** — check with `git --version`
- A terminal (Mac: Terminal app or VS Code integrated terminal)

---

### Step 2 — Clone the repository

```bash
git clone https://github.com/iamharsh25/Demografy.git
cd Demografy
```

---

### Step 3 — Create a virtual environment

A virtual environment keeps this project's packages separate from the rest of your system.

```bash
python3 -m venv venv
```

Then activate it:

```bash
# Mac / Linux
source venv/bin/activate

# Windows
venv\Scripts\activate
```

You should see `(venv)` appear at the start of your terminal line. You need to run this activate command every time you open a new terminal.

---

### Step 4 — Install all dependencies

```bash
pip install -r requirements.txt
```

This installs everything: Streamlit, LangChain, Gemini SDK, BigQuery client, and more. Takes 1–2 minutes.

---

### Step 5 — Set up your credentials

Copy the template to create your `.env` file:

```bash
cp .env.template .env
```

Open `.env` and fill in the three values:

```
GOOGLE_APPLICATION_CREDENTIALS=/full/path/to/your-bigquery-key.json
GEMINI_API_KEY=your-gemini-api-key-here
LANGCHAIN_API_KEY=your-langsmith-api-key-here
```

#### Where to get each credential:

| Credential | Where to get it |
|---|---|
| **BigQuery JSON key** | GCP Console → IAM & Admin → Service Accounts → `ai-insights-bot` → Keys tab → Add Key → JSON. Ask Wayne if you don't have access. |
| **Gemini API Key** | Go to [aistudio.google.com](https://aistudio.google.com) → Sign in → Get API Key → Create API Key |
| **LangSmith API Key** | Go to [smith.langchain.com](https://smith.langchain.com) → Sign up free → Settings → Create API Key |

> **Security:** Never commit `.env` or any `*.json` key file to GitHub. They are already listed in `.gitignore`.

---

### Step 6 — Run the app

```bash
streamlit run app.py
```

The app opens automatically in your browser at `http://localhost:8501`

---

### Step 7 — Verify everything is working

Ask the chatbot:
> "What are the top 5 most diverse suburbs in Victoria?"

You should see:
- Real suburb names (e.g. Keilor Downs, Delahey) — not generic AI answers
- A **🔍 View SQL Query** expander below the answer — click it to see the SQL that ran

If you see *"Live data not connected"*, check that your `GOOGLE_APPLICATION_CREDENTIALS` path in `.env` points to the correct JSON file and restart the app.

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `ModuleNotFoundError` | Run `source venv/bin/activate` then try again |
| `"Live data not connected"` | Check `.env` has correct BigQuery key path, restart Streamlit |
| Red import errors in VS Code | Press `Cmd+Shift+P` → "Python: Select Interpreter" → choose `./venv/bin/python3` |
| Port already in use | Run `pkill -f streamlit` then `streamlit run app.py` |

---

## Data Reference

- **Production table:** `demografy.prod_tables.a_master_view`
- **Customer table:** `demografy.ref_tables.dev_customers`
- **Coverage:** 2,329 Australian SA2 suburbs

### KPI Column Reference

| Column | KPI Name | Description | Range |
|---|---|---|---|
| kpi_1_val | Prosperity Score | Socioeconomic advantage based on income, occupation, education, housing | 0–100 |
| kpi_2_val | Diversity Index | Cultural diversity — 1.0 = maximally diverse, 0 = homogeneous | 0–1 |
| kpi_3_val | Migration Footprint | % residents with at least one overseas-born parent | 0–100% |
| kpi_4_val | Learning Level | % residents who completed Year 12 | 0–100% |
| kpi_5_val | Social Housing | % dwellings that are public/community housing | 0–100% |
| kpi_6_val | Resident Equity | % dwellings owned outright or with a mortgage | 0–100% |
| kpi_7_val | Rental Access | % dwellings renting below $450/week | 0–100% |
| kpi_8_val | Resident Anchor | % residents who stayed 5+ years in same community | 0–100% |
| kpi_9_val | Household Mobility Potential | % households in transitional socioeconomic positions | 0–1 |
| kpi_10_val | Young Family Indicator | % population aged 0–14 | 0–100% |

---

## User Tiers

| Tier | Questions per Session |
|---|---|
| Free | 5 |
| Basic | 20 |
| Pro | 50 |

---

## How It Works (Architecture)

```
User types question
    ↓
Streamlit (app.py) — the web interface
    ↓
LangChain SQL Agent (agent/sql_agent.py) — the orchestrator
    ↓ sends question + few-shot examples
Gemini 2.5 Flash — generates SQL
    ↓ SQL query
Google BigQuery — runs the query, returns data
    ↓ results
Gemini 2.5 Flash — formats data into a plain English answer
    ↓
User sees the answer + SQL expander
    ↓ (logged automatically)
LangSmith — records every step for observability
```

---

## Security

- `.env` and all `*.json` key files are gitignored — never committed to GitHub
- SQL agent is restricted to read-only queries on `a_master_view` only
- Destructive SQL (DELETE, UPDATE, INSERT, DROP) is blocked in the agent prompt
- All queries include LIMIT clauses to prevent expensive full-table scans

---

## Version History

See [CHANGELOG.md](CHANGELOG.md)
