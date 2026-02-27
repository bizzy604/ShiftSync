"""
MODULE: /scripts/seed_production_once.py

FUNCTION:
    Implements module logic for `seed_production_once`.

DEPENDENCIES:
    - (No in-repo dependents detected.)

IMPORTANCE:
    This module is important for maintainability and predictable behavior of
    `seed_production_once`.
"""

import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SEED_FLAG = "RUN_PROD_SEED_ON_DEPLOY"


def is_truthy(raw: str | None) -> bool:
    if raw is None:
        return False
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def main() -> int:
    if not is_truthy(os.getenv(SEED_FLAG)):
        print(f"{SEED_FLAG} is not enabled; skipping production seed.")
        return 0

    command = [sys.executable, str(ROOT / "seed" / "seed_production.py")]
    result = subprocess.run(command, cwd=ROOT, check=False)
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
