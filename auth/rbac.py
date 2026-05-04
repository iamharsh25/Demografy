"""
Role-Based Access Control (RBAC) for Demografy Insights Chatbot.

What this file does:
- Looks up a user in the dev_customers BigQuery table using their user_id
- Returns their tier (free / basic / pro)
- Enforces question limits per session based on tier

Tiers:
    free  → 5  questions per session
    basic → 20 questions per session
    pro   → 50 questions per session

No passwords — login is by user_id only (as per project spec).
"""

import os
import time
from typing import Optional

from db.bigquery_client import run_query


def _env_positive_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or not str(raw).strip():
        return default
    try:
        value = int(str(raw).strip(), 10)
    except ValueError:
        return default
    return value if value > 0 else default

# Question limits for each tier
TIER_LIMITS = {
    "free": 5,
    "basic": 20,
    "pro": 50,
}

# Warning thresholds — show a warning when user is close to their limit
TIER_WARNINGS = {
    "free": 4,    # warn at question 4 (1 left)
    "basic": 15,  # warn at question 15 (5 left)
    "pro": 45,    # warn at question 45 (5 left)
}

# Length of the post-limit cooldown. After it elapses the engine resets
# ``question_count`` to zero so the user gets a fresh "mini-session"
# without us mutating tier limits. Override with ``SESSION_COOLDOWN_SECONDS``
# in ``.env`` (see ``.env.template``).
COOLDOWN_SECONDS = _env_positive_int("SESSION_COOLDOWN_SECONDS", 30)


def get_user(user_id: str) -> dict | None:
    """
    Looks up a user in the dev_customers table by their user_id.

    Args:
        user_id (str): The user ID entered at login (e.g. "user_001")

    Returns:
        dict: User info with keys: user_id, email, tier, is_active
        None: If user is not found or account is inactive
    """
    df = run_query(f"""
        SELECT user_id, email, tier, is_active
        FROM demografy.ref_tables.dev_customers
        WHERE user_id = '{user_id}'
          AND is_active = TRUE
        LIMIT 1
    """)

    if df.empty:
        return None

    row = df.iloc[0]
    return {
        "user_id": row["user_id"],
        "email": row["email"],
        "tier": row["tier"],
        "is_active": row["is_active"],
    }


def get_question_limit(tier: str) -> int:
    """
    Returns the maximum number of questions allowed per session for a given tier.

    Args:
        tier (str): One of "free", "basic", "pro"

    Returns:
        int: The question limit (5, 20, or 50)
    """
    return TIER_LIMITS.get(tier, 5)  # Default to 5 if tier is unknown


def is_limit_reached(tier: str, question_count: int) -> bool:
    """
    Checks if a user has reached their question limit for this session.

    Args:
        tier (str): The user's tier
        question_count (int): How many questions they have asked so far

    Returns:
        bool: True if limit reached (block the input), False if still under limit
    """
    return question_count >= get_question_limit(tier)


def seconds_remaining(cooldown_until: Optional[float]) -> int:
    """How many whole seconds remain on a cooldown timestamp.

    Returns ``0`` when ``cooldown_until`` is ``None`` or already in the
    past. Always returns a non-negative integer so the UI can render the
    label without extra clamping.
    """
    if not cooldown_until:
        return 0
    remaining = float(cooldown_until) - time.time()
    if remaining <= 0:
        return 0
    return int(remaining + 0.999)  # round up so "0.4s left" still shows "1s"


def should_show_warning(tier: str, question_count: int) -> bool:
    """
    Checks if we should show a "you're almost at your limit" warning.

    Args:
        tier (str): The user's tier
        question_count (int): How many questions they have asked so far

    Returns:
        bool: True if a warning should be displayed
    """
    warning_at = TIER_WARNINGS.get(tier, 4)
    limit = get_question_limit(tier)
    return warning_at <= question_count < limit
