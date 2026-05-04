"""
LLM-as-a-Judge for evaluating chatbot responses.

Compares the chatbot's answer against expected criteria and scores it 1-5.
Runs are logged to LangSmith when tracing env vars are set (same as the app).
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langsmith import traceable

# Demografy repo root (eval/GoldenDatasetEval -> eval -> Demografy)
_DEMOGRAFY_ROOT = Path(__file__).resolve().parent.parent.parent
load_dotenv(_DEMOGRAFY_ROOT / ".env")

_LANGSMITH_PROJECT = os.getenv("LANGCHAIN_PROJECT") or os.getenv("LANGSMITH_PROJECT")


@traceable(
    name="golden_dataset_judge",
    run_type="llm",
    tags=["golden_dataset_eval", "judge"],
    project_name=_LANGSMITH_PROJECT,
)
def score_answer(question: str, bot_answer: str, validation_criteria: str) -> dict:
    """
    Uses Gemini as a judge to score the chatbot's answer.

    Args:
        question (str): The original question asked
        bot_answer (str): The chatbot's answer
        validation_criteria (str): What the correct answer should contain

    Returns:
        dict: {
            "score": int (1-5),
            "reasoning": str (why this score was given)
        }
    """
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        google_api_key=os.getenv("GEMINI_API_KEY"),
        temperature=0,
    )

    prompt = f"""You are evaluating a Demografy demographic chatbot's answer.

Important domain context:
- Demografy covers Australian SA2-level areas. In this project, user words like "suburb" or "area" mean SA2 areas, which can include remote communities, islands, and combined suburb names.
- State names are Australian states and territories unless the expected criteria explicitly says otherwise.
- KPI values are proprietary Demografy dataset metrics. Treat returned query results as the source of truth; do not override them with general-world assumptions.
- "Rental access" is kpi_7_val: the percentage of rentals below $450/week. It is not a share of households that rent, so it should not be added to home ownership.

Question: {question}

Chatbot's Answer: {bot_answer}

Expected Criteria: {validation_criteria}

Score the answer on a scale of 1-5:
- 5 = Perfect match, correct data and formatting
- 4 = Correct data, minor formatting issues
- 3 = Mostly correct, small discrepancies
- 2 = Partially correct, significant errors
- 1 = Wrong answer or failed to execute

Respond in this exact format:
Score: [number]
Reasoning: [brief explanation]"""

    response = llm.invoke(
        [
            SystemMessage(content="You are a fair and objective evaluator."),
            HumanMessage(content=prompt),
        ]
    )

    text = response.content
    try:
        score_line = [line for line in text.split("\n") if line.startswith("Score:")][0]
        score = int(score_line.split(":")[1].strip())

        reasoning_line = [line for line in text.split("\n") if line.startswith("Reasoning:")][0]
        reasoning = reasoning_line.split(":", 1)[1].strip()
    except Exception:
        score = 3
        reasoning = "Could not parse judge response"

    return {
        "score": score,
        "reasoning": reasoning,
    }
