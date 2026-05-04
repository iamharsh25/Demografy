# How the Demografy Insights Chatbot Works
### A plain-English explanation for the team

---

## What We Built

We built an AI chatbot that lets anyone type a question in plain English — like *"Which suburbs in Victoria have the highest diversity?"* — and get a real, data-driven answer pulled directly from Demografy's database of 2,329 Australian suburbs.

The chatbot does not guess when answering from data: it reads the question, may write a database query (via the LangChain SQL agent), runs it against BigQuery when needed, and returns a factual answer in **plain English**. **LangSmith** (optional) logs the technical steps for the team. The **main chat UI** does not show raw SQL or internal column names to end users; those details stay in traces and in code paths used for follow-ups and charts.

---

## The Technology Stack — What Each Tool Is

Think of it like a restaurant kitchen:

| Tool | What it is in plain English | Role in our project |
|---|---|---|
| **Python** | The programming language everything is written in | The base language |
| **Streamlit** | A Python library that turns Python code into a website | Page shell: header, body, login, **fragments** |
| **Gemini AI** | Google's AI (like ChatGPT) | Reads the question, writes SQL when the SQL agent runs, formats answers |
| **LangChain** | A Python library that connects AI to a database | Wires Gemini to BigQuery tools (schema, checker, query) |
| **Google BigQuery** | Google's cloud database where Demografy's suburb data lives | Where the actual data is stored and queried |
| **LangSmith** | A dashboard that records AI / chain steps | Debugging, eval visibility, screenshots for deliverables |
| **Virtual Environment (venv)** | An isolated Python workspace | Keeps this project's packages separate from the rest of your laptop |
| **.env file** | A text file that stores secret keys | Keeps passwords and API keys out of the code |

**The kitchen analogy:**

- **BigQuery** = the fridge (all the ingredients / data)
- **Gemini** = the chef (makes decisions, writes the recipe / SQL when we use the SQL agent path)
- **LangChain** = the kitchen manager (organises the chef, the fridge, and the tools)
- **Streamlit + our custom chat iframe** = the restaurant front-of-house (what the customer sees and types into)
- **LangSmith** = the CCTV camera (records technical steps for the team)

---

## Project File Map — The Important Pieces

```
Demografy/
│
├── app.py                 ← Thin entry: `streamlit run app.py` loads app_v4
├── app_v4.py             ← Page config, header/body layout, chat area (runs agent inside @st.fragment)
│
├── components/
│   ├── chat_engine.py     ← Heart of the UX loop: bridge events → ask() → history JSONL, limits, charts path
│   ├── chat_widget/       ← Custom HTML/JS chat UI (iframe) + Python bridge (question / new_chat / open_thread)
│   ├── user_profile.py    ← Login dialog, profile pill, tier-aware UI hooks
│   ├── header.py / body.py / styles.py / state.py  ← Layout, theme, session restore
│   └── ...
│
├── agent/
│   ├── sql_agent.py      ← Routing + LangChain SQL agent: templates vs LLM, guardrails, strip_for_ui
│   ├── prompts.py        ← Instruction manual for SQL: KPIs, rules, few-shots
│   ├── suggestions.py    ← Follow-up suggestion chips after a reply
│   ├── guardrails.py     ← Topic / phrasing checks used in routing
│   └── templates.py      ← Deterministic answers for common question shapes (fast + reliable)
│
├── chat_history/          ← JSONL storage, thread list, context snippets for the agent
│
├── db/
│   ├── bigquery_client.py ← Service-account BigQuery runs (also used for chart hydration)
│   └── explore.py         ← Optional exploration helpers
│
├── auth/
│   ├── rbac.py            ← Tiers, question limits, BigQuery user lookup (dev_customers)
│   └── cooldown.py        ← Short cooldown between asks to protect the backend
│
├── eval/
│   ├── GoldenDatasetEval/   ← Single-turn golden questions, SQL pattern + LLM judge → results.json
│   ├── LangsmithEval/       ← Workspace verification + langsmith_report.json
│   ├── ConversationEval/    ← Multi-turn stress + chips + transcript judge
│   ├── guardrail_smoke.py   ← Fast routing checks without BigQuery
│   └── README.md            ← Index of eval commands
│
├── .streamlit/config.toml ← Theme, default port (8502)
├── .env / .env.template   ← Secrets (gitignored) vs template safe to commit
├── requirements.txt
├── README.md                ← Setup + eval overview (kept in sync with code)
├── HOW_IT_WORKS.md          ← This document
├── PROJECT_FILES.md         ← Deeper per-file map
└── CHANGELOG.md
```

---

## The Full Journey — What Happens When You Ask a Question

Let's trace what happens when a user types (in the chat widget):

> *"What are the top 5 most diverse suburbs in Victoria?"*

```
Step 1 — User types in the custom chat iframe
         ↓
         The widget sends a "question" payload through the Streamlit components bridge

Step 2 — components/chat_engine.py handles the event (inside @st.fragment)
         ↓
         Loads recent turns for this chat_thread_id from chat_history (JSONL on disk)
         so follow-ups stay in context

Step 3 — chat_engine calls agent/sql_agent.py: ask(question, history, context_meta, ...)
         ↓
         ask() is not "always SQL first": it applies guardrails, may answer from
         templates, or may invoke the LangChain SQL agent depending on the question
         and conversation context (see sql_agent docstring)

Step 4 — When the SQL agent path runs, LangChain sends the (possibly contextualised)
         input to Gemini
         ↓
         Together with prompts.py (rules, KPI map, few-shots) and schema tools

Step 5 — Gemini plans SQL (example shape)
         ↓
         SELECT sa2_name, state, kpi_2_val AS diversity_index
         FROM `demografy.prod_tables.a_master_view`
         WHERE state = 'Victoria'
           AND kpi_2_val IS NOT NULL
         ORDER BY kpi_2_val DESC
         LIMIT 5;

Step 6 — LangChain checks the SQL (query checker tool), then runs it against BigQuery
         ↓
         Rows come back as real data

Step 7 — Gemini turns rows into a plain-English reply; strip_assistant_reply_for_ui
         removes internal phrasing we do not want in the bubble

Step 8 — chat_engine persists the turn (user + assistant) to JSONL under ChatHistory/<user>/
         ↓
         The iframe shows the final message; while waiting, users see a "Thinking..." style
         indicator (not a live dump of every tool name unless we add that later)

Step 9 — Optional: agent/suggestions.py proposes short follow-up chips (e.g. chart or drill-down)

Step 10 — If LangSmith env vars are set, the chain is traced under LANGCHAIN_PROJECT
          ↓
          Developers open smith.langchain.com in the correct workspace to inspect SQL, tools, latency
```

**What users see vs what the team sees:** Users see natural language, loading state, and chips. **SQL and tool internals** are primarily for **LangSmith** and **engineering**, not copied into the main bubble as raw diagnostics.

---

## Each File Explained in Detail

---

### `app.py` and `app_v4.py` — The Website Shell

**`app.py`** is a tiny entry file: it runs `app_v4.py` so the command stays `streamlit run app.py`.

**`app_v4.py`** is the real Streamlit page:

- Page config (title, layout, favicon)
- Imports layout pieces from `components/` (header, body, styles)
- Hosts the **chat widget** and runs **`components/chat_engine.maybe_consume_bridge`** inside an **`@st.fragment`** so a long `ask()` does not flash the whole page with a global "Running…" overlay

**Port:** With the bundled `.streamlit/config.toml`, the app is usually at **http://localhost:8502** (not 8501).

---

### `components/chat_engine.py` — The Chat Loop

This module connects the **iframe bridge** to **`sql_agent.ask`** and **disk history**.

**Bridge actions** (see module docstring):

- **`question`** — run the agent for the active thread, append messages, enforce RBAC limits and cooldowns, optionally trigger chart rendering when the user asks for a chart in natural language
- **`new_chat`** — new `chat_thread_id`, clears live messages, keeps old JSONL files
- **`open_thread`** — load an existing transcript into the widget

Agent context uses **`last_n_turns`** for the **current thread only**, so conversations do not bleed across threads.

---

### `components/chat_widget/` — The Typing UI

A **declared Streamlit custom component** (persistent iframe with HTML/JS) — see the **Communication contract** in `chat_widget/__init__.py`. Python pushes props (`messages`, `pending`, `suggestions`, …); JavaScript sends **`setComponentValue`** payloads (`question`, `new_chat`, `open_thread`, `chart`, …) back to **`maybe_consume_bridge`** in `chat_engine.py`. This avoids full iframe reloads on every rerun and cuts visible flicker compared to embedding a one-off HTML snippet.

---

### `components/user_profile.py` — Login and Profile

**Wired today:** **Login** opens from the header (`@st.dialog` sign-in), looks up the user via **`auth/rbac.get_user`**, and ties chat history paths to that user id. Tier limits from **`rbac.py`** apply once signed in.

---

### `agent/sql_agent.py` — The Brain (Routing + SQL Agent)

This is the most important backend file. It:

1. **Normalises** the question and applies **guardrails** (unsupported topics, schema probes, vague phrasing, etc.).
2. Chooses between **deterministic template answers** (`templates.py`) and the **LangChain SQL agent** (`_invoke_llm_sql_agent`), depending on context — templates are fast and reliable for common shapes; the LLM path handles richer follow-ups.
3. Returns **`(answer, sql, meta)`** — SQL may be `None` for template-only answers; `meta` can carry rows for charts or clarification chips.

**LangChain agent tools** (when the SQL path runs): schema, SQL checker, SQL query — same mental model as before.

**`temperature=0`** — keeps SQL behaviour stable.

**`max_iterations=10`** — prevents runaway tool loops.

---

### `agent/prompts.py` — The Instruction Manual

Same role as before: role, rules (read-only, `a_master_view`, LIMIT, no `SELECT *`, NULL handling), KPI translation, few-shot SQL aligned with Demografy's business patterns. Quality here directly affects SQL accuracy.

---

### `agent/suggestions.py` and `agent/templates.py`

- **`suggestions.py`** — builds a small set of **follow-up chips** after an answer (e.g. chart or related query), with rules enforced in evals.
- **`templates.py`** — pattern-matched answers that **skip the LLM** when we already know the SQL shape; improves latency and consistency.

---

### `db/bigquery_client.py` — The Key to the Database

Reads **`GOOGLE_APPLICATION_CREDENTIALS`**, runs SQL to DataFrames. Used by RBAC user lookup, chart hydration paths, and indirectly by LangChain's BigQuery connection (same credentials story).

---

### `auth/rbac.py` and `auth/cooldown.py`

**`rbac.py`** — tiers (Free / Basic / Pro), per-session question caps, **`get_user`** against BigQuery `dev_customers`, helpers for limit warnings.

**`cooldown.py`** — short spacing between asks to reduce accidental double-submits and load spikes.

---

## How We Evaluate Quality (High Level)

Automated checks live under **`eval/`** (see **`eval/README.md`** and **`README.md`**):

| Area | Plain English |
|------|----------------|
| **GoldenDatasetEval** | Fixed single-turn questions; checks SQL patterns and uses an LLM judge; writes `results.json`. |
| **ConversationEval** | Scripted multi-turn chats through the real `ask` + chips; rule checks + transcript judge; writes `conversation_results.json`. |
| **LangsmithEval** | Confirms your API key's workspace and that runs show up where you expect (avoids "wrong workspace" confusion). |
| **guardrail_smoke.py** | Quick routing smoke tests without hitting BigQuery. |

These complement **LangSmith** traces for debugging individual failures.

---

## Key Design Decisions

**Why a custom chat iframe instead of only built-in Streamlit chat widgets?**  
Product UX: persistent thread feel, controlled styling, and a clear bridge for **new chat / open thread** without rewriting the whole page on every keystroke.

**Why `@st.fragment` around the agent?**  
So **slow LLM + BigQuery** work shows a **fragment-scoped** loading state instead of blocking the entire Streamlit app shell.

**Why templates *and* an LLM SQL agent?**  
Templates give **predictable, fast** answers for common questions; the **LLM agent** handles **contextual follow-ups** ("same for NSW?", "show more") that would be brittle if hard-coded only.

**Why does the left panel collapse?**  
More horizontal room for the chat on small screens and during demos.

**What if the model cannot answer from data?**  
Users get a controlled **unanswerable / clarify** style reply (`USER_FACING_UNANSWERABLE_REPLY` or geography chips) rather than silent failure; we do **not** advertise a separate "ask Gemini general knowledge instead of census data" path for failed BigQuery — product answers stay on the data assistant contract.

**Why few-shots from the company's SQL document?**  
So the model learns **Demografy's real naming and thresholds**, not generic textbook SQL.

**Why `temperature=0` for SQL generation?**  
Consistency beats creativity for database queries.

---

## What Happens in LangSmith

When tracing is enabled, LangSmith can record:

1. The user's question (and wrapped context for eval spans)
2. Tool calls and order (schema / checker / query)
3. Generated SQL
4. Final assistant text (and judge spans for golden eval)

Open **[smith.langchain.com](https://smith.langchain.com)** → correct **workspace** (use `eval/LangsmithEval/langsmith_account_check.py` if traces seem missing) → project **`demografy-chatbot`** (or your `LANGCHAIN_PROJECT`) → **Runs**.

Useful for **debugging**, **golden/conversation evals**, and **cost** visibility.

---

## Summary — The One-Paragraph Version

The Demografy Insights Chatbot is a **Streamlit v4** app: **`app_v4.py`** and **`components/`** render the shell and a **custom chat iframe**; **`chat_engine.py`** turns user actions into calls to **`sql_agent.ask`**, which combines **guardrails**, **template** answers, and a **LangChain + Gemini SQL agent** against **BigQuery**, using **`prompts.py`** as the instruction manual. Replies are **plain English** in the UI; **per-thread JSONL** history lives under **`chat_history/`**; **sign-in and tiers** come from **`user_profile.py`** and **`auth/rbac.py`**. Optional **LangSmith** tracing and the **`eval/`** suites help the team prove quality and debug issues.

---

*Document updated: May 2026 | Project: Demografy AI Internship — Team D*
