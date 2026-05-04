"""
Check that LangSmith is receiving traces for this project.

Prerequisites (in ``.env``)::

    LANGCHAIN_TRACING_V2=true
    LANGCHAIN_API_KEY=...
    LANGCHAIN_PROJECT=demografy-chatbot

Usage from repo root::

    python eval/LangsmithEval/verify_langsmith.py              # list recent runs
    python eval/LangsmithEval/verify_langsmith.py --smoke      # one ask() then list runs

After a golden or conversation eval run, you should see new runs in the LangSmith UI
and in this script's output.
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


def _check_env() -> tuple[bool, str]:
    from dotenv import load_dotenv

    load_dotenv(_ROOT / ".env")
    import os

    tracing = (os.getenv("LANGCHAIN_TRACING_V2") or "").lower() in ("1", "true", "yes")
    key = os.getenv("LANGCHAIN_API_KEY")
    project = os.getenv("LANGCHAIN_PROJECT") or "demografy-chatbot"
    if not key:
        return False, "LANGCHAIN_API_KEY is not set in .env"
    if not tracing:
        return False, "LANGCHAIN_TRACING_V2 should be true for tracing"
    return True, project


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify LangSmith runs for LANGCHAIN_PROJECT")
    parser.add_argument(
        "--smoke",
        action="store_true",
        help="Run one sql_agent.ask() before listing (uses BigQuery + Gemini)",
    )
    parser.add_argument(
        "--minutes",
        type=int,
        default=30,
        help="Highlight runs newer than this many minutes (default: 30)",
    )
    args = parser.parse_args()

    ok, project_or_msg = _check_env()
    if not ok:
        print("Configuration:", project_or_msg)
        sys.exit(1)
    project = project_or_msg

    if args.smoke:
        from agent.sql_agent import ask

        print("Smoke: calling ask() once (traced if LangChain tracing is on)...")
        ask("What is the average prosperity score in Victoria?")
        print("Smoke: done.\n")

    from dotenv import load_dotenv

    load_dotenv(_ROOT / ".env")
    import os

    from langsmith import Client

    client = Client(api_key=os.environ["LANGCHAIN_API_KEY"])
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=args.minutes)

    recent = []
    for run in client.list_runs(project_name=project, limit=40):
        st = getattr(run, "start_time", None)
        if st is None:
            continue
        if st.tzinfo is None:
            st = st.replace(tzinfo=timezone.utc)
        if st >= cutoff:
            recent.append((st, getattr(run, "run_type", ""), getattr(run, "name", ""), str(run.id)))

    print(f"Project: {project}")
    print(f"Runs in the last {args.minutes} minutes: {len(recent)}")
    for st, rt, name, rid in sorted(recent, reverse=True)[:20]:
        print(f"  {st.isoformat()}  {rt or '?'}  {name or '(no name)'}  {rid[:8]}...")

    if not recent:
        print("\nNo recent runs. Open https://smith.langchain.com and confirm the project name")
        print("matches LANGCHAIN_PROJECT. Then run eval or --smoke and try again.")
        sys.exit(2)

    print("\nLangSmith logging appears active (recent runs found).")
    sys.exit(0)


if __name__ == "__main__":
    main()
