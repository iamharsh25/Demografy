"""Run a single conversation scenario from the stress dataset (default: education thread).

Use this for a fast check without running the full multi-scenario suite.

From the Demografy repo root::

    python eval/ConversationEval/run_education_conversation_eval.py
    python eval/ConversationEval/run_education_conversation_eval.py --id drill-down

Writes ``eval/ConversationEval/education_conversation_results.json`` (one-element list)
so the full ``conversation_results.json`` from the main suite is untouched.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_ROOT = _HERE.parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

import run_conversation_eval as _ce  # noqa: E402

DATASET_PATH = _HERE / "conversation_stress_dataset.json"
OUTPUT_PATH = _HERE / "education_conversation_results.json"
DEFAULT_SCENARIO_ID = "education-multi-turn"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run one conversation scenario by id (default: education-multi-turn)."
    )
    parser.add_argument(
        "--id",
        default=DEFAULT_SCENARIO_ID,
        help=f"Scenario id from conversation_stress_dataset.json (default: {DEFAULT_SCENARIO_ID!r})",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=OUTPUT_PATH,
        help=f"Where to write JSON results (default: {OUTPUT_PATH})",
    )
    args = parser.parse_args()

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    if not DATASET_PATH.exists():
        print(f"Dataset not found: {DATASET_PATH}", file=sys.stderr)
        sys.exit(1)

    scenarios: list[dict] = json.loads(DATASET_PATH.read_text(encoding="utf-8"))
    chosen = [s for s in scenarios if s.get("id") == args.id]
    if not chosen:
        ids = [s.get("id") for s in scenarios]
        print(f"No scenario with id={args.id!r}. Available ids: {ids}", file=sys.stderr)
        sys.exit(1)

    scenario = chosen[0]
    print("=" * 80)
    print("DEMOGRAFY SINGLE-SCENARIO CONVERSATION EVAL")
    print(f"Scenario id: {args.id}")
    print("=" * 80)
    print()

    result = _ce._run_scenario(scenario)
    out = [result]
    args.output.write_text(json.dumps(out, indent=2), encoding="utf-8")

    passed = result["judge_score"] >= 4 and not result["rule_failures"]
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Pass (judge >= 4 and no rule failures): {passed}")
    print(f"Judge score: {result['judge_score']}/5")
    if result.get("rule_failures"):
        print(f"Rule failures: {len(result['rule_failures'])}")
        for f in result["rule_failures"]:
            print(f"  - {f}")
    print()
    print(f"Results written to: {args.output.resolve()}")


if __name__ == "__main__":
    main()
