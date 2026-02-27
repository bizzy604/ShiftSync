import os
import site
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ALEMBIC_INI = ROOT / "apps" / "api" / "alembic.ini"


def parse_env_file(path: Path) -> dict[str, str]:
    """Parse a simple KEY=VALUE dotenv file."""
    parsed: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if value.startswith('"') and value.endswith('"') and len(value) >= 2:
            value = value[1:-1]
        parsed[key] = value
    return parsed


def resolve_active_env_file(env: dict[str, str]) -> Path:
    explicit = env.get("ENV_FILE", "").strip()
    if explicit:
        env_path = Path(explicit)
        if not env_path.is_absolute():
            env_path = ROOT / env_path
        return env_path

    app_env = env.get("APP_ENV", "development").strip().lower()
    if app_env in {"production", "prod"}:
        return ROOT / ".env.production"
    return ROOT / ".env.local"


def load_env() -> dict[str, str]:
    """Load process env with .env and active env-file overrides."""
    env = os.environ.copy()
    base_file = ROOT / ".env"
    if base_file.exists():
        env.update(parse_env_file(base_file))

    active_file = resolve_active_env_file(env)
    if active_file.exists():
        env.update(parse_env_file(active_file))
    return env


def main() -> int:
    """Run Alembic commands for schema management."""
    if len(sys.argv) < 2:
        print("Usage: python scripts/alembic_migrate.py [upgrade|downgrade|stamp|revision] [args...]")
        return 1

    mode = sys.argv[1]
    extra = sys.argv[2:]
    scripts_dir = Path(site.getusersitepackages()).parent / "Scripts"
    alembic_executable = scripts_dir / ("alembic.exe" if os.name == "nt" else "alembic")
    base = [str(alembic_executable) if alembic_executable.exists() else "alembic", "-c", str(ALEMBIC_INI)]

    if mode == "upgrade":
        command = base + ["upgrade", extra[0] if extra else "head"]
    elif mode == "downgrade":
        command = base + ["downgrade", extra[0] if extra else "-1"]
    elif mode == "stamp":
        command = base + ["stamp", extra[0] if extra else "head"]
    elif mode == "revision":
        if not extra:
            print("Usage: python scripts/alembic_migrate.py revision \"message\"")
            return 1
        command = base + ["revision", "--autogenerate", "-m", extra[0]]
    else:
        print(f"Unsupported mode: {mode}")
        return 1

    process = subprocess.run(command, cwd=ROOT / "apps" / "api", env=load_env(), check=False)
    return process.returncode


if __name__ == "__main__":
    raise SystemExit(main())
