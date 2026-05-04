"""LLM-as-judge scorer for multi-turn conversation scenarios.

Mirrors the style of ``eval/GoldenDatasetEval/judge.py`` but consumes a
full conversation transcript (with assistant suggestions) and returns a single
overall score. Uses Gemini via ``langchain_google_genai`` so the call appears
in LangSmith alongside the agent runs.
"""

from __future__ import annotations

import os
from typing import List

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI


def _format_transcript(turns: List[dict]) -> str:
    """Render a list of {user_turn, assistant_answer, suggestions} dicts.

    The judge prompt is text-only, so we serialise the conversation into a
    short labelled block instead of passing it as chat messages.
    """
    lines: list[str] = []
    for idx, turn in enumerate(turns, start=1):
        lines.append(f"Turn {idx}")
        lines.append(f"  User: {turn.get('user_turn', '').strip()}")
        lines.append(f"  Assistant: {turn.get('assistant_answer', '').strip()}")
        chips = turn.get("suggestions") or []
        if chips:
            lines.append("  Suggested follow-ups:")
            for chip in chips:
                lines.append(f"    - {chip}")
        lines.append("")
    return "\n".join(lines).strip()


def score_conversation(scenario_name: str, turns: List[dict]) -> dict:
    """Score a whole conversation transcript on a 1-5 scale.

    Args:
        scenario_name: Human-readable scenario label (for the prompt).
        turns: List of {user_turn, assistant_answer, suggestions} dicts in
            the order they happened.

    Returns:
        {"score": int (1-5), "reasoning": str}. Falls back to score=3 with
        a "parse failed" reasoning if the judge response can't be parsed,
        matching ``GoldenDatasetEval/judge.py`` behaviour.
    """
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        google_api_key=os.getenv("GEMINI_API_KEY"),
        temperature=0,
    )

    transcript = _format_transcript(turns)

    prompt = f"""You are evaluating a multi-turn conversation with the Demografy
demographic chatbot. The chatbot answers questions about Australian SA2-level
demographic data (states, suburbs, KPIs like diversity, prosperity, migration,
rental access, social housing).

Scenario: {scenario_name}

Full transcript (with the assistant's suggested follow-up chips after each
reply):

{transcript}

Score the WHOLE conversation on a 1-5 scale, weighting these criteria equally:

1. Follow-up understanding - did each later turn correctly resolve against
   the previous turn's intent (state swap, metric switch, limit change,
   drill-down, narrowing)?
2. Factual coherence and helpfulness - answers are concrete, on-topic, and
   reference Australian states/suburbs where relevant.
3. No internal-detail leakage - the user-facing text must NEVER contain
   raw SQL, table or dataset names (a_master_view, prod_tables, demografy.*),
   or column names (kpi_*_val, sa2_name, etc.). Backticks around identifiers
   are also a leak.
4. Suggestion quality - chips are short, end with "?", are relevant to the
   answer, do not repeat the previous question, and never expose internal
   names.

Score guide:
  5 - All four criteria met across all turns.
  4 - Minor issues (mild repetition, slightly off chip, small phrasing nit).
  3 - One clear failure (e.g. a follow-up was misinterpreted) but the rest is fine.
  2 - Multiple failures or a single major leak / crash-style answer.
  1 - Conversation broke down or leaked internal schema repeatedly.

Respond in this EXACT format (no markdown, no extra text):
Score: <integer 1-5>
Reasoning: <one or two sentences>
"""

    response = llm.invoke([
        SystemMessage(content="You are a fair and objective evaluator."),
        HumanMessage(content=prompt),
    ])

    text = response.content if isinstance(response.content, str) else str(response.content)
    score = 3
    reasoning = "Could not parse judge response"
    try:
        score_line = next(line for line in text.splitlines() if line.lower().startswith("score:"))
        score = int(score_line.split(":", 1)[1].strip().split()[0])
        reason_line = next(line for line in text.splitlines() if line.lower().startswith("reasoning:"))
        reasoning = reason_line.split(":", 1)[1].strip()
    except StopIteration:
        pass
    except Exception:
        pass

    score = max(1, min(5, score))
    return {"score": score, "reasoning": reasoning}
