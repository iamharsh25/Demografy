"""Build bar or pie charts from templated SQL result rows for inline chat display.

Uses matplotlib Agg backend only. Returns a PNG as base64 for embedding in
the Streamlit chat widget as a data URL.
"""

from __future__ import annotations

import base64
import io
import os
import re
import tempfile
from typing import Any, List, Literal, Optional, Tuple

ChartKind = Literal["bar", "pie"]

# Intents whose ``rows`` are suitable for a simple bar chart (suburb/area labels).
CHARTABLE_INTENTS = frozenset({
    "ranked_metric",
    "ranked_percent",
    "rental_access",
    "young_family_learning",
    "state_comparison",
    "single_area_metric",
})

CHART_TITLE_MAX = 72

# Demografy brand purples (from Streamlit theme / guidelines).
_COLOR_PRIMARY = "#9a66ee"
_COLOR_SECONDARY = "#5e17eb"
_SLICE_COLORS = (
    "#9a66ee",
    "#5e17eb",
    "#b894f7",
    "#7c3aed",
    "#c4b5fd",
    "#a78bfa",
    "#8b5cf6",
    "#6d28d9",
    "#ddd6fe",
    "#ede9fe",
)

_STATE_ABBREVIATIONS = {
    "Australian Capital Territory": "ACT",
    "New South Wales": "NSW",
    "Northern Territory": "NT",
    "Queensland": "Qld",
    "South Australia": "SA",
    "Tasmania": "Tas",
    "Victoria": "Vic",
    "Western Australia": "WA",
}


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


def _area_label(row: tuple) -> str:
    name = str(row[0] or "").strip() if len(row) > 0 else ""
    state = str(row[1] or "").strip() if len(row) > 1 else ""
    if state:
        state = _STATE_ABBREVIATIONS.get(state, state)
    return f"{name}, {state}" if state else name


def _render_pie(
    ax,
    labels: list[str],
    values: list[float],
    title: str,
    *,
    value_unit: str = "%",
) -> None:
    """Draw a pie chart with slice labels, percentages, legend, and title."""
    vals = [max(v, 0.0) for v in values]
    total_v = sum(vals) or 1.0
    n = len(labels)
    colors = [_SLICE_COLORS[i % len(_SLICE_COLORS)] for i in range(n)]

    def _autopct(pct: float) -> str:
        abs_v = pct / 100.0 * total_v
        if value_unit == "%":
            return f"{abs_v:.1f}%"
        return f"{abs_v:.2f}"

    wedges, texts, autotexts = ax.pie(
        vals,
        labels=None,
        autopct=_autopct,
        pctdistance=0.72,
        colors=colors,
        startangle=90,
        wedgeprops={"linewidth": 1.0, "edgecolor": "white"},
    )
    for t in texts:
        if t is not None:
            t.set_fontsize(9)
    for t in autotexts:
        if t is not None:
            t.set_fontsize(8)
            t.set_color("#272d2d")

    ax.legend(
        wedges,
        labels,
        title="Area",
        loc="center left",
        bbox_to_anchor=(1.02, 0.5),
        fontsize=8,
        title_fontsize=9,
        frameon=True,
        fancybox=False,
        edgecolor="#e5e7eb",
    )
    ax.set_title(title[:CHART_TITLE_MAX], fontsize=12, fontweight="600", color="#272d2d", pad=12)
    ax.axis("equal")


def build_chart_png_b64(
    intent: str,
    rows: List[tuple],
    question: str,
    *,
    chart_kind: ChartKind = "bar",
) -> Optional[Tuple[str, str]]:
    """Return ``(title, base64_png)`` or ``None`` if chart is not viable."""
    if not is_chartable(intent, rows):
        return None

    os.environ.setdefault(
        "MPLCONFIGDIR",
        os.path.join(tempfile.gettempdir(), "demografy-matplotlib"),
    )

    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    title = _chart_title(intent, question, rows)
    labels: list[str] = []
    values: list[float] = []

    try:
        # Dual-series state comparison: always grouped bars (pie would be misleading).
        if intent == "state_comparison":
            chart_kind = "bar"

        if intent == "state_comparison":
            for row in rows[:10]:
                labels.append(_shorten_label(_area_label(row)))
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
                labels.append(_shorten_label(_area_label(row)))
                values.append(float(row[2]) if len(row) > 2 and row[2] is not None else 0.0)
            if chart_kind == "pie":
                fig, ax = plt.subplots(figsize=(9, 5.2), dpi=120)
                _render_pie(ax, labels, values, title)
                fig.tight_layout()
            else:
                fig, ax = plt.subplots(figsize=(8, 4), dpi=120)
                ax.barh(labels[::-1], values[::-1], color=_COLOR_PRIMARY)
                ax.set_xlabel("Young family presence %")
                ax.set_title(title[:CHART_TITLE_MAX], fontsize=11, color="#272d2d")
                fig.tight_layout()
        else:
            # ranked_metric, ranked_percent, rental_access, single_area_metric
            value_index = 3 if intent == "rental_access" else 2
            for row in rows[:10]:
                labels.append(_shorten_label(str(row[0])))
                raw_v = row[value_index] if len(row) > value_index else 0
                values.append(float(raw_v) if raw_v is not None else 0.0)
            ql = (question or "").lower()
            if intent == "ranked_metric":
                unit = ""
            elif intent == "single_area_metric":
                unit = "%"
                if any(
                    x in ql
                    for x in (
                        "diversity",
                        "diverse",
                        "prosperity",
                        "household mobility",
                        "population",
                    )
                ):
                    unit = ""
            else:
                unit = "%"
            if chart_kind == "pie":
                fig, ax = plt.subplots(figsize=(9, 5.2), dpi=120)
                _render_pie(ax, labels, values, title, value_unit=unit)
                fig.tight_layout()
            else:
                fig, ax = plt.subplots(figsize=(8, 4), dpi=120)
                ax.barh(labels[::-1], values[::-1], color=_COLOR_PRIMARY)
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
    if intent == "single_area_metric":
        return re.sub(r"\s+", " ", q) or f"Area metric ({n} areas)"
    if "diversity" in q.lower() or "diverse" in q.lower():
        return f"Diversity ranking ({n} areas)"
    if "prosperity" in q.lower():
        return f"Prosperity ranking ({n} areas)"
    if "migration" in q.lower():
        return f"Migration footprint ({n} areas)"
    if "rental" in q.lower() or "affordable" in q.lower():
        return f"Rental access ({n} areas)"
    return re.sub(r"\s+", " ", q) or f"Chart ({n} values)"

