"""
Run LangSmith workspace + recent-run checks and write a JSON report in this folder.

From repo root::

    python eval/LangsmithEval/run_langsmith_checks.py
    python eval/LangsmithEval/run_langsmith_checks.py --smoke

Output::

    eval/LangsmithEval/langsmith_report.json
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_ROOT = _HERE.parent.parent
REPORT_PATH = _HERE / "langsmith_report.json"

if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


def main() -> None:
    parser = argparse.ArgumentParser(description="LangSmith checks → langsmith_report.json")
    parser.add_argument(
        "--smoke",
        action="store_true",
        help="Call ask() once before listing runs (BigQuery + Gemini)",
    )
    parser.add_argument("--minutes", type=int, default=30)
    args = parser.parse_args()

    from dotenv import load_dotenv

    load_dotenv(_ROOT / ".env")
    import os

    report: dict = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "ok": False,
        "errors": [],
        "workspace": None,
        "project": os.getenv("LANGCHAIN_PROJECT") or "demografy-chatbot",
        "recent_runs": [],
    }

    tracing = (os.getenv("LANGCHAIN_TRACING_V2") or "").lower() in ("1", "true", "yes")
    key = os.getenv("LANGCHAIN_API_KEY")
    if not key:
        report["errors"].append("LANGCHAIN_API_KEY is not set in .env")
    if not tracing:
        report["errors"].append("LANGCHAIN_TRACING_V2 should be true for tracing")

    if args.smoke and not report["errors"]:
        try:
            from agent.sql_agent import ask

            ask("What is the average prosperity score in Victoria?")
            report["smoke_ask"] = "completed"
        except Exception as exc:
            report["errors"].append(f"smoke ask failed: {exc!r}")

    if not key:
        REPORT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"Wrote {REPORT_PATH} (incomplete — missing API key)")
        sys.exit(1)

    try:
        from langsmith import Client

        client = Client(api_key=key)
        settings = client._get_settings()
        report["workspace"] = {
            "display_name": settings.display_name,
            "tenant_handle": settings.tenant_handle,
            "id": str(settings.id),
        }
        project = report["project"]
        p = client.read_project(project_name=project, include_stats=True)
        report["project_details"] = {
            "name": p.name,
            "id": str(p.id),
            "run_count": getattr(p, "run_count", None),
            "url": f"https://smith.langchain.com/o/{settings.id}/projects/p/{p.id}",
        }

        cutoff = datetime.now(timezone.utc) - timedelta(minutes=args.minutes)
        for run in client.list_runs(project_name=project, limit=40):
            st = getattr(run, "start_time", None)
            if st is None:
                continue
            if st.tzinfo is None:
                st = st.replace(tzinfo=timezone.utc)
            if st >= cutoff:
                report["recent_runs"].append({
                    "start_time": st.isoformat(),
                    "run_type": getattr(run, "run_type", ""),
                    "name": getattr(run, "name", ""),
                    "id": str(run.id),
                })
        report["ok"] = len(report["recent_runs"]) > 0
        if not report["recent_runs"]:
            report["errors"].append(
                f"No runs in the last {args.minutes} minutes for project {project!r}"
            )
    except Exception as exc:
        report["errors"].append(f"langsmith client: {exc!r}")

    REPORT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Wrote {REPORT_PATH}")
    if report.get("errors"):
        for e in report["errors"]:
            print(f"  note: {e}")
    sys.exit(0 if report.get("ok") else 2)


if __name__ == "__main__":
    main()
