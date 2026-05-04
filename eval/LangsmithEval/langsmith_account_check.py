"""
Show which LangSmith *workspace* your ``LANGCHAIN_API_KEY`` belongs to.

Use this when the LangSmith **website** shows 0 traces but Python tracing
works: you are usually logged into a different workspace than the one tied
to the key in ``.env``.

Usage (from repo root)::

    python eval/LangsmithEval/langsmith_account_check.py

Compare the printed **display name** and **workspace id** with the workspace
switcher in the LangSmith UI (bottom-left or profile menu on smith.langchain.com).
"""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


def main() -> None:
    from dotenv import load_dotenv

    load_dotenv(_ROOT / ".env")
    import os

    key = os.getenv("LANGCHAIN_API_KEY")
    project = os.getenv("LANGCHAIN_PROJECT", "demografy-chatbot")
    if not key:
        print("LANGCHAIN_API_KEY is not set in .env")
        sys.exit(1)

    from langsmith import Client

    client = Client(api_key=key)
    settings = client._get_settings()

    print("=" * 60)
    print("WORKSPACE YOUR API KEY USES (traces go here)")
    print("=" * 60)
    print(f"  Display name:   {settings.display_name}")
    print(f"  Tenant handle:  {settings.tenant_handle or '(none)'}")
    print(f"  Workspace ID:   {settings.id}")
    print()

    try:
        p = client.read_project(project_name=project, include_stats=True)
        tid = settings.id
        pid = str(p.id)
        print(f"Project: {p.name}")
        print(f"  Project ID:     {pid}")
        print(f"  Run count:      {getattr(p, 'run_count', 'n/a')}")
        print()
        print("Open this project directly in the browser (log in with the")
        print("same LangSmith account that created this API key):")
        print(f"  https://smith.langchain.com/o/{tid}/projects/p/{pid}")
        print()
    except Exception as exc:
        print(f"Could not read project {project!r}: {exc}")
        print("Try: Tracing → switch workspace to match display name above.")


if __name__ == "__main__":
    main()
