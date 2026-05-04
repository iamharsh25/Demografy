# How the Demografy Insights Chatbot Works
### A plain-English explanation for the team

---

## What We Built

We built an AI chatbot that lets anyone type a question in plain English — like *"Which suburbs in Victoria have the highest diversity?"* — and get a real, data-driven answer pulled directly from Demografy's database of 2,329 Australian suburbs.

The chatbot does not guess. It reads the question, writes a database query, runs it against real data, and gives back a factual answer. Every step is logged so the team can see exactly what happened.

---

## The Technology Stack — What Each Tool Is

Think of it like a restaurant kitchen:

| Tool | What it is in plain English | Role in our project |
|---|---|---|
| **Python** | The programming language everything is written in | The base language |
| **Streamlit** | A Python library that turns Python code into a website | The chat window users see |
| **Gemini AI** | Google's AI (like ChatGPT) | Reads the question, writes the SQL, formats the answer |
| **LangChain** | A Python library that connects AI to a database | The "glue" — tells Gemini what tools it has and runs everything |
| **Google BigQuery** | Google's cloud database where Demografy's suburb data lives | Where the actual data is stored and queried |
| **LangSmith** | A dashboard that records every AI step | The "security camera" — logs what happened for debugging |
| **Virtual Environment (venv)** | An isolated Python workspace | Keeps this project's packages separate from the rest of your laptop |
| **.env file** | A text file that stores secret keys | Keeps passwords and API keys out of the code |

**The kitchen analogy:**
- **BigQuery** = the fridge (all the ingredients / data)
- **Gemini** = the chef (makes decisions, writes the recipe / SQL)
- **LangChain** = the kitchen manager (organises the chef, the fridge, and the tools)
- **Streamlit** = the restaurant front-of-house (what the customer sees)
- **LangSmith** = the CCTV camera (records everything for review)

---

## Project File Map — Every File in One Sentence

```
Demografy/
│
├── app.py                ← The entire website UI (what you see in the browser)
│
├── agent/
│   ├── sql_agent.py      ← The brain — connects Gemini AI to BigQuery via LangChain
│   └── prompts.py        ← The instruction manual — teaches Gemini which columns mean what
│
├── db/
│   ├── bigquery_client.py ← The key to the database — handles the BigQuery connection
│   └── explore.py        ← A one-time script to explore and understand the data
│
├── auth/
│   └── rbac.py           ← The bouncer — checks user tier and enforces question limits
│
├── eval/
│   ├── GoldenDatasetEval/  ← golden_dataset.json, run_eval.py, judge.py, results.json
│   ├── LangsmithEval/      ← verify LangSmith workspace + langsmith_report.json
│   ├── ConversationEval/   ← multi-turn scenarios, conversation_results.json
│   └── guardrail_smoke.py  ← fast routing checks without BigQuery
│
├── .streamlit/
│   └── config.toml       ← Demografy brand colours and font settings
│
├── .env                  ← Secret keys (not on GitHub — gitignored)
├── .env.template         ← A blank version of .env safe to share
├── requirements.txt      ← The shopping list of Python packages to install
├── README.md             ← Setup instructions for anyone cloning the repo
└── CHANGELOG.md          ← Version history of what changed and when
```

---

## The Full Journey — What Happens When You Ask a Question

Let's trace exactly what happens when a user types:
> *"What are the top 5 most diverse suburbs in Victoria?"*

```
Step 1 — User types the question
         ↓
         app.py receives the text

Step 2 — app.py calls ask() in sql_agent.py
         ↓
         "Please figure out the answer to this question"

Step 3 — sql_agent.py checks if the agent is ready
         ↓
         If first question ever: connects to BigQuery + sets up Gemini (takes ~5 seconds)
         If already used before: skips setup, goes straight to step 4

Step 4 — LangChain sends the question to Gemini AI
         ↓
         Along with: our instruction manual (prompts.py) + the database schema
         Gemini reads all of this and thinks: "I need to write a SQL query"

Step 5 — Gemini writes a SQL query
         ↓
         SELECT sa2_name, state, kpi_2_val AS diversity_index
         FROM `demografy.prod_tables.a_master_view`
         WHERE state = 'Victoria'
           AND kpi_2_val IS NOT NULL
         ORDER BY kpi_2_val DESC
         LIMIT 5;

Step 6 — LangChain checks the SQL (uses a built-in SQL checker tool)
         ↓
         Confirms the query is valid before running it

Step 7 — LangChain runs the SQL against BigQuery
         ↓
         BigQuery searches through 2,329 suburbs and returns 5 rows of real data:
         [('Keilor Downs', 'Victoria', 0.88), ('Delahey', 'Victoria', 0.87), ...]

Step 8 — LangChain sends the raw data back to Gemini
         ↓
         "Here are the results. Now write a nice plain-English answer."

Step 9 — Gemini writes the final answer
         ↓
         "The top 5 most diverse suburbs in Victoria are:
          1. Keilor Downs (diversity index: 0.88)
          2. Delahey (0.87)
          ..."

Step 10 — app.py displays the answer in the chat
          ↓
          Also shows a "🔍 View SQL Query" expander so users can inspect what ran

Step 11 — LangSmith records every single step above
          ↓
          The Demografy team can log into smith.langchain.com and see the full trace
```

**Every step above is visible live in the chat window** — you see the AI "thinking" in real-time before the final answer appears.

---

## Each File Explained in Detail

---

### `app.py` — The Website

This is the only file that creates the visual interface. When you run `streamlit run app.py`, Python reads this file and serves a website at `http://localhost:8501`.

**What it does:**
- Sets up the page (title, icon, layout)
- Injects CSS (the brand colours, font, gradient background)
- Creates the two-column layout: left info panel + right chat
- Handles the ▶/◀ collapse toggle on the left panel
- Manages chat history (stored in `st.session_state` — Streamlit's memory)
- When a user submits a question, calls `ask()` from `sql_agent.py`
- Displays the answer and a collapsible SQL query viewer
- If BigQuery fails for any reason, falls back to asking Gemini directly (no SQL, just general knowledge) and shows a warning

**Key Streamlit concepts used:**
- `st.columns()` — creates side-by-side sections
- `st.chat_message()` — renders user/assistant chat bubbles
- `st.chat_input()` — the text box at the bottom
- `st.session_state` — remembers things between interactions (like a notepad)
- `st.expander()` — the collapsible "View SQL Query" section
- `st.spinner()` — the "Thinking..." loading indicator

---

### `agent/sql_agent.py` — The Brain

This is the most important file. It is the bridge between the AI and the database.

**The key concept — a LangChain "agent":**
An agent is an AI that has been given *tools* it can use. Our agent has three tools:
1. **sql_db_schema** — look at the database table structure
2. **sql_db_query_checker** — check if a SQL query is valid before running it
3. **sql_db_query** — actually run a SQL query and get results

The agent decides which tools to use, in which order, on its own.

**The two main functions:**

`_create_agent()` — runs once, on the first question ever asked:
1. Connects LangChain to BigQuery (`SQLDatabase.from_uri`)
2. Creates a Gemini AI instance (`ChatGoogleGenerativeAI`)
3. Combines them into an agent with our instruction manual (`create_sql_agent`)
4. Returns the ready-to-use agent

`ask(question, callbacks)` — runs every time a user asks something:
1. Creates the agent if it doesn't exist yet
2. Passes the question to the agent
3. The agent does all the work (steps 4–9 in the journey above)
4. Extracts the SQL that was used from the agent's logs (`intermediate_steps`)
5. Returns a tuple: `(answer text, SQL query)`

**Why `temperature=0`?**
Temperature controls how "creative" the AI is. At 0, Gemini is fully deterministic — it gives the same SQL for the same question every time. Higher temperature would mean unpredictable queries, which is bad for a database bot.

**Why `max_iterations=10`?**
This stops the agent from going in circles. If it hasn't figured out the answer in 10 steps, it stops and reports what it has. Prevents infinite loops.

---

### `agent/prompts.py` — The Instruction Manual

This is arguably the most important file for *accuracy*. Before Gemini writes any SQL, it reads this file entirely. Think of it as a briefing document given to a new employee.

**What it contains:**

**1. The role definition:**
> "You are a demographic data analyst for Demografy. You help users query Australian suburb-level demographic data stored in Google BigQuery."

This tells Gemini *who it is* and *what it's supposed to do*.

**2. The rules:**
- Only query `demografy.prod_tables.a_master_view` (can't touch other tables)
- Never run DELETE, UPDATE, INSERT, or DROP (read-only)
- Always use LIMIT (max 50 rows — prevents expensive full-table scans)
- Never use SELECT * (always name specific columns)
- Always filter out NULLs with IS NOT NULL

**3. The KPI translation table:**
This is critical. Gemini doesn't know that "diversity" means `kpi_2_val`. We tell it:

| What users say | Column in database |
|---|---|
| "prosperity score" | kpi_1_val |
| "diversity index" | kpi_2_val |
| "migration footprint" | kpi_3_val |
| "learning level" | kpi_4_val |
| ...and so on | ... |

**4. Ten example queries:**
We give Gemini 10 real examples of questions and their correct SQL. This is called *few-shot prompting* — teaching by example. The examples come from Demografy's own Sample SQL Queries document, so the patterns are exactly what the business expects.

By seeing examples, Gemini learns:
- Always use backtick-quoted table names
- Always use IS NOT NULL
- Always use ROUND() for decimal values
- Use meaningful column aliases like `AS diversity_index` not just the raw column name

The better this file is, the more accurate the chatbot's SQL becomes.

---

### `db/bigquery_client.py` — The Key to the Database

This file handles the low-level mechanics of connecting to BigQuery.

**What it does:**
- Reads the service account JSON file path from the `.env` file
- Creates an authenticated BigQuery client (like logging into the database)
- Provides a `run_query(sql)` function that takes SQL text and returns a table of results as a pandas DataFrame (a Python table structure)

**What a service account is:**
A service account is like a "robot user" in Google Cloud. Instead of a person logging in with a username and password, our code logs in using a JSON file that contains a private cryptographic key. Google checks the key and grants access.

This file is used directly by `auth/rbac.py` (to look up users) and indirectly by `sql_agent.py` (LangChain uses its own connection, but the same credentials).

---

### `auth/rbac.py` — The Bouncer

RBAC stands for Role-Based Access Control. This file manages *who can ask how many questions*.

**The tier system:**

| Tier | Questions per session |
|---|---|
| Free | 5 |
| Basic | 20 |
| Pro | 50 |

**The four functions:**

`get_user(user_id)` — looks up a user ID in the `dev_customers` BigQuery table. Returns their email, tier, and whether they're active. Returns `None` if not found.

`get_question_limit(tier)` — given a tier name, returns the number (5, 20, or 50).

`is_limit_reached(tier, count)` — returns True if the user has used up all their questions for this session.

`should_show_warning(tier, count)` — returns True when a user is close to their limit (so the UI can show a warning message).

Note: this module is written and ready, but the login screen hasn't been wired into the current UI yet. The chatbot currently works without login — this will be connected in a future version.

---

## Key Design Decisions

**Why no login screen currently?**
We built the RBAC logic first so it's ready, but skipped the login UI for now to keep development fast. The chatbot works without it, and the login can be added later without changing any backend code.

**Why does the left panel collapse?**
It gives more space to the chat. On smaller screens or during demos, collapsing the panel makes the chat full-width.

**Why does the app fall back to Gemini if BigQuery fails?**
So the chatbot is never completely broken. If the database connection drops, users still get an AI-powered answer with a clear disclaimer saying it's not from live data.

**Why are the few-shot examples from the company's SQL document?**
We could have written generic examples, but using Demografy's own SQL patterns means the AI learns the exact business logic the company already uses — correct thresholds, correct KPI combinations, correct column names.

**Why `temperature=0`?**
A chatbot that writes database queries needs to be consistent and predictable. Creative AI is fun for writing stories, but terrible for SQL generation.

---

## What Happens in LangSmith

LangSmith is Demografy's observability platform. Every time someone asks a question, LangSmith records:

1. The user's question
2. Which tools the agent called (and in what order)
3. The exact SQL that was generated
4. The raw BigQuery results
5. The final formatted answer
6. How long each step took
7. Token usage (how much AI was consumed)

To see it: log into [smith.langchain.com](https://smith.langchain.com) → open the `demografy-chatbot` project → click any trace to see every step expanded.

This is useful for:
- **Debugging**: if someone gets a wrong answer, you can see exactly which SQL ran and why
- **Evaluation**: checking if the AI is writing good SQL over time
- **Cost tracking**: seeing how many tokens are being used per question

---

## Summary — The One-Paragraph Version

The Demografy Insights Chatbot is a Python web app built with Streamlit. When a user types a question, the app passes it to a LangChain SQL agent. The agent uses Gemini AI as its brain and has been given an instruction manual (`prompts.py`) that teaches it Demografy's database structure and KPI names. The agent writes a SQL query, checks it, runs it against BigQuery, and then asks Gemini to format the results into a plain-English answer. Every step streams live into the chat window so users can see the AI thinking. The full trace is also logged to LangSmith so the team can inspect, debug, and evaluate every query.

---

*Document written: April 2026 | Project: Demografy AI Internship — Team D*
