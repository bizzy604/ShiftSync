"""
MODULE: /apps/api/run.py

FUNCTION:
    Implements module logic for `run`.

DEPENDENCIES:
    - (No in-repo dependents detected.)

IMPORTANCE:
    This module is important for maintainability and predictable behavior of `run`.
"""

import os
from pathlib import Path

import uvicorn


API_DIR = Path(__file__).resolve().parent


if __name__ == "__main__":
    reload_enabled = os.getenv("UVICORN_RELOAD", "false").lower() == "true"
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=port,
        reload=reload_enabled,
        app_dir=str(API_DIR),
    )
