"""
Demografy V1 entrypoint.
Run with: streamlit run app_v1.py
"""

import os

# Force legacy mode before importing the main module.
os.environ["DEMOGRAFY_APP_MODE"] = "v1"

import app  # noqa: F401,E402
