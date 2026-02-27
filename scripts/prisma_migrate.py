"""
MODULE: /scripts/prisma_migrate.py

FUNCTION:
    Implements module logic for `prisma_migrate`.

DEPENDENCIES:
    - (No in-repo dependents detected.)

IMPORTANCE:
    This module is important for maintainability and predictable behavior of
    `prisma_migrate`.
"""

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def parse_env_file(path: Path) -> dict[str, str]:
    parsed: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if value.startswith('"') and value.endswith('"') and len(value) >= 2:
            value = value[1:-1]
        parsed[key] = value
    return parsed


def load_env() -> dict[str, str]:
    env = os.environ.copy()
    for env_file in (ROOT / ".env", ROOT / ".env.local"):
        if not env_file.exists():
            continue
        values = parse_env_file(env_file)
        for key, value in values.items():
            env[key] = value
    return env


def main() -> int:
    if len(sys.argv) != 2 or sys.argv[1] not in {"deploy", "dev"}:
        print("Usage: python scripts/prisma_migrate.py [deploy|dev]")
        return 1

    mode = sys.argv[1]
    npx_executable = "npx.cmd" if os.name == "nt" else "npx"
    command = [npx_executable, "prisma", "migrate", "deploy", "--schema", "prisma/schema.prisma"]
    if mode == "dev":
        command = [npx_executable, "prisma", "migrate", "dev", "--schema", "prisma/schema.prisma", "--skip-generate"]

    process = subprocess.run(command, cwd=ROOT, env=load_env(), check=False)
    return process.returncode


if __name__ == "__main__":
    raise SystemExit(main())
