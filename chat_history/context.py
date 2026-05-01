"""Format chat-history turns into a prompt-friendly context block.

Used by ``agent.sql_agent.ask`` to prepend recent conversation in front
of the user's current question, so the SQL agent can resolve follow-ups
like "diversity" against the topic of the previous turn.
"""

from __future__ import annotations

from typing import Iterable, List


# Soft cap on the rendered transcript size. If the formatted block grows
# larger than this, we drop the oldest user/assistant pairs until it fits.
# Picked to comfortably stay under typical LLM context budgets while
# still preserving 5 short turns worth of dialogue.
MAX_CONTEXT_CHARS = 4000


_HEADER = "Previous conversation (most recent last):\n"


def _format_turn(record: dict) -> str:
    role = record.get("role", "")
    content = (record.get("content") or "").strip()
    if not content:
        return ""
    label = "User" if role == "user" else "Assistant"
    return f"{label}: {content}\n"


def _pair_turns(turns: Iterable[dict]) -> List[List[dict]]:
    """Group a flat turns list into [user, (assistant?)] pairs.

    Anything that isn't a user message starting a fresh pair gets folded
    into the previous pair so we can drop "oldest pair first" cleanly
    when the rendered context exceeds the soft cap.
    """
    pairs: List[List[dict]] = []
    for record in turns:
        if record.get("role") == "user" or not pairs:
            pairs.append([record])
        else:
            pairs[-1].append(record)
    return pairs


def build_context_block(turns: Iterable[dict]) -> str:
    """Render ``turns`` as a transcript prefix for the agent.

    Returns an empty string when no turns are provided so callers can
    cheaply check truthiness instead of parsing the output.
    """
    pairs = _pair_turns(turns)
    if not pairs:
        return ""

    while pairs:
        rendered = _HEADER + "".join(
            _format_turn(record) for pair in pairs for record in pair
        )
        if len(rendered) <= MAX_CONTEXT_CHARS:
            return rendered + "\n"
        # Trim the oldest pair and try again.
        pairs.pop(0)

    return ""
