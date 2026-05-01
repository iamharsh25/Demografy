"""Per-user chat history persistence.

This package owns reading and writing chat transcripts to disk
(``ChatHistory/<user_id>.jsonl``) and shaping a context block to feed
back into the SQL agent for follow-up questions.
"""

from chat_history.context import MAX_CONTEXT_CHARS, build_context_block
from chat_history.storage import (
    HISTORY_DIR,
    append_message,
    last_n_turns,
    load_history,
)

__all__ = [
    "HISTORY_DIR",
    "MAX_CONTEXT_CHARS",
    "append_message",
    "build_context_block",
    "last_n_turns",
    "load_history",
]
