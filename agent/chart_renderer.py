"""Build simple bar charts from templated SQL result rows for inline chat display.

Uses matplotlib Agg backend only. Returns a PNG as base64 for embedding in
the Streamlit chat widget as a data URL.
"""

from __future__ import annotations

import base64
import io
import re
from typing import Any, List, Optional, Tuple

# Intents whose ``rows`` are suitable for a simple bar chart (suburb/area labels).
CHARTABLE_INTENTS = frozenset({
    "ranked_metric",
    "ranked_percent",
    "rental_access",
    "young_family_learning",
    "state_comparison",
})

CHART_TITLE_MAX = 72

# Demografy brand purples (from Streamlit theme / guidelines).
_COLOR_PRIMARY = "#9a66ee"
_COLOR_SECONDARY = "#5e17eb"


def is_chartable(intent: str, rows: Any) -> bool:
    if intent not in CHARTABLE_INTENTS:
        return False
    if not rows or not isinstance(rows, list):
        return False
    return len(rows) >= 1


def _shorten_label(text: str, max_len: int = 28) -> str:
    text = (text or "").strip()
    if len(text) <= max_len:
        return text
    return text[: max_len - 1] + "…"


def build_chart_png_b64(
    intent: str,
    rows: List[tuple],
    question: str,
) -> Optional[Tuple[str, str]]:
    """Return ``(title, base64_png)`` or ``None`` if chart is not viable."""
    if not is_chartable(intent, rows):
        return None

    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    title = _chart_title(intent, question, rows)
    labels: list[str] = []
    values: list[float] = []

    try:
        if intent == "state_comparison":
            for row in rows[:10]:
                labels.append(_shorten_label(str(row[0])))
                values.append(float(row[1]) if row[1] is not None else 0.0)
            y2 = [float(row[2]) if len(row) > 2 and row[2] is not None else 0.0 for row in rows[:10]]
            fig, ax = plt.subplots(figsize=(9, 4.2), dpi=120)
            x = range(len(labels))
            w = 0.35
            ax.bar([i - w / 2 for i in x], values, width=w, label="Home ownership %", color=_COLOR_PRIMARY)
            ax.bar([i + w / 2 for i in x], y2, width=w, label="Rental access %", color=_COLOR_SECONDARY)
            ax.set_xticks(list(x))
            ax.set_xticklabels(labels, rotation=35, ha="right", fontsize=9)
            ax.set_ylabel("%")
            ax.legend(loc="upper right", fontsize=8)
            ax.set_title(title[:CHART_TITLE_MAX], fontsize=11, color="#272d2d")
            fig.tight_layout()
        elif intent == "young_family_learning":
            for row in rows[:10]:
                labels.append(_shorten_label(str(row[0])))
                values.append(float(row[2]) if len(row) > 2 and row[2] is not None else 0.0)
            fig, ax = plt.subplots(figsize=(8, 4), dpi=120)
            ax.barh(labels[::-1], values[::-1], color=_COLOR_PRIMARY)
            ax.set_xlabel("Young family presence %")
            ax.set_title(title[:CHART_TITLE_MAX], fontsize=11, color="#272d2d")
            fig.tight_layout()
        else:
            # ranked_metric, ranked_percent, rental_access: label row[0], value row[2] or row[3]
            value_index = 3 if intent == "rental_access" else 2
            for row in rows[:10]:
                labels.append(_shorten_label(str(row[0])))
                raw_v = row[value_index] if len(row) > value_index else 0
                values.append(float(raw_v) if raw_v is not None else 0.0)
            fig, ax = plt.subplots(figsize=(8, 4), dpi=120)
            ax.barh(labels[::-1], values[::-1], color=_COLOR_PRIMARY)
            unit = "%" if intent != "ranked_metric" else ""
            ax.set_xlabel("Value" + (f" ({unit})" if unit else " (index)"))
            ax.set_title(title[:CHART_TITLE_MAX], fontsize=11, color="#272d2d")
            fig.tight_layout()

        buf = io.BytesIO()
        fig.savefig(buf, format="png", bbox_inches="tight", facecolor="white")
        plt.close(fig)
        b64 = base64.b64encode(buf.getvalue()).decode("ascii")
        return title, b64
    except Exception:
        try:
            plt.close("all")
        except Exception:
            pass
        return None


def _chart_title(intent: str, question: str, rows: list) -> str:
    q = (question or "").strip()
    if len(q) > 60:
        q = q[:57] + "…"
    n = len(rows)
    if intent == "state_comparison":
        return f"State comparison ({n} rows)"
    if "diversity" in q.lower() or "diverse" in q.lower():
        return f"Diversity ranking ({n} areas)"
    if "prosperity" in q.lower():
        return f"Prosperity ranking ({n} areas)"
    if "migration" in q.lower():
        return f"Migration footprint ({n} areas)"
    if "rental" in q.lower() or "affordable" in q.lower():
        return f"Rental access ({n} areas)"
    return re.sub(r"\s+", " ", q) or f"Chart ({n} values)"

