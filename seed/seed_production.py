import asyncio
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from passlib.context import CryptContext


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
ROOT_DIR = Path(__file__).resolve().parents[1]
API_DIR = ROOT_DIR / "apps" / "api"
if str(API_DIR) not in sys.path:
    sys.path.insert(0, str(API_DIR))


def _resolve_active_env_file() -> Path:
    explicit = os.getenv("ENV_FILE")
    if explicit:
        env_path = Path(explicit)
        if not env_path.is_absolute():
            env_path = ROOT_DIR / env_path
        return env_path
    app_env = os.getenv("APP_ENV", "development").strip().lower()
    if app_env in {"production", "prod"}:
        return ROOT_DIR / ".env.production"
    return ROOT_DIR / ".env.local"


load_dotenv(ROOT_DIR / ".env", override=False)
load_dotenv(_resolve_active_env_file(), override=True)


from app.core.database import connect_db, disconnect_db, prisma


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def parse_skill_names(raw: str | None) -> list[str]:
    if not raw:
        return ["bartender", "line cook", "server", "host"]
    names: list[str] = []
    for item in raw.split(","):
        name = item.strip().lower()
        if name and name not in names:
            names.append(name)
    return names or ["bartender", "line cook", "server", "host"]


async def ensure_skill(db: object, name: str) -> tuple[bool, str]:
    existing = await db.skill.find_unique(where={"name": name})
    if existing:
        return False, existing.id
    created = await db.skill.create(data={"name": name})
    return True, created.id


async def ensure_admin_user(db: object) -> tuple[str, str]:
    existing_admin = await db.user.find_first(where={"role": "admin"})
    if existing_admin:
        return "unchanged", existing_admin.email

    admin_email = os.getenv("INITIAL_ADMIN_EMAIL", "").strip().lower()
    admin_password = os.getenv("INITIAL_ADMIN_PASSWORD", "").strip()
    admin_name = os.getenv("INITIAL_ADMIN_NAME", "Platform Admin").strip() or "Platform Admin"
    admin_timezone = os.getenv("INITIAL_ADMIN_TIMEZONE", "America/New_York").strip() or "America/New_York"

    if not admin_email or not admin_password:
        raise RuntimeError(
            "No admin user exists. Set INITIAL_ADMIN_EMAIL and INITIAL_ADMIN_PASSWORD, then re-run this script."
        )
    if len(admin_password) < 12:
        raise RuntimeError("INITIAL_ADMIN_PASSWORD must be at least 12 characters.")

    existing_user = await db.user.find_unique(where={"email": admin_email})
    payload = {
        "name": admin_name,
        "email": admin_email,
        "password_hash": hash_password(admin_password),
        "role": "admin",
        "home_timezone": admin_timezone,
        "desired_hours_per_week": 40,
        "hourly_rate": None,
        "is_active": True,
    }

    if existing_user:
        await db.user.update(
            where={"id": existing_user.id},
            data={
                "name": payload["name"],
                "password_hash": payload["password_hash"],
                "role": payload["role"],
                "home_timezone": payload["home_timezone"],
                "is_active": payload["is_active"],
            },
        )
        return "promoted", admin_email

    await db.user.create(data=payload)
    return "created", admin_email


async def seed_production() -> int:
    db = prisma
    await connect_db()
    try:
        added_skills = 0
        for skill_name in parse_skill_names(os.getenv("SEED_CORE_SKILLS")):
            created, _ = await ensure_skill(db, skill_name)
            if created:
                added_skills += 1

        admin_state, admin_email = await ensure_admin_user(db)
        print(
            f"Production seed complete. skills_added={added_skills}, admin_state={admin_state}, admin_email={admin_email}"
        )
        return 0
    finally:
        await disconnect_db()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(seed_production()))
