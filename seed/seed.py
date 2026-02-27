import asyncio
import os
import sys
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

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


def _as_date_datetime(value: date) -> datetime:
    return datetime.combine(value, time.min)


def _local_range_to_utc(shift_date: date, start_clock: str, end_clock: str, timezone_name: str) -> tuple[datetime, datetime]:
    tz = ZoneInfo(timezone_name)
    start_h, start_m = [int(part) for part in start_clock.split(":")]
    end_h, end_m = [int(part) for part in end_clock.split(":")]
    local_start = datetime.combine(shift_date, time(start_h, start_m), tzinfo=tz)
    local_end = datetime.combine(shift_date, time(end_h, end_m), tzinfo=tz)
    if local_end <= local_start:
        local_end += timedelta(days=1)
    return local_start.astimezone(timezone.utc), local_end.astimezone(timezone.utc)


def _week_start_monday(value: date) -> date:
    return value - timedelta(days=value.weekday())


async def create_seed_shift(
    db: object,
    *,
    location: object,
    required_skill_id: str,
    shift_date: date,
    start_clock: str,
    end_clock: str,
    created_by: str,
    status: str = "published",
    headcount_needed: int = 1,
) -> object:
    start_utc, end_utc = _local_range_to_utc(shift_date, start_clock, end_clock, location.iana_timezone)
    published_at = datetime.now(tz=timezone.utc) if status == "published" else None
    edit_cutoff_utc = (start_utc - timedelta(hours=48)) if status == "published" else None
    return await db.shift.create(
        data={
            "location_id": location.id,
            "required_skill_id": required_skill_id,
            "shift_date": _as_date_datetime(shift_date),
            "start_utc": start_utc,
            "end_utc": end_utc,
            "headcount_needed": headcount_needed,
            "status": status,
            "week_start": _as_date_datetime(_week_start_monday(shift_date)),
            "published_at": published_at,
            "edit_cutoff_utc": edit_cutoff_utc,
            "created_by": created_by,
        }
    )


async def create_seed_assignment(
    db: object,
    *,
    shift_id: str,
    user_id: str,
    assigned_by: str,
) -> object:
    return await db.shiftassignment.create(
        data={
            "shift_id": shift_id,
            "user_id": user_id,
            "assigned_by": assigned_by,
            "status": "assigned",
            "version": 1,
        }
    )


async def ensure_location(db: object, payload: dict[str, Any]) -> Any:
    existing = await db.location.find_first(where={"name": payload["name"]})
    if existing:
        return existing
    return await db.location.create(data=payload)


async def ensure_skill(db: object, name: str) -> Any:
    existing = await db.skill.find_unique(where={"name": name})
    if existing:
        return existing
    return await db.skill.create(data={"name": name})


async def ensure_user(db: object, payload: dict[str, Any]) -> Any:
    existing = await db.user.find_unique(where={"email": payload["email"]})
    if existing:
        return existing
    data = payload.copy()
    data["password_hash"] = hash_password(data.pop("password"))
    return await db.user.create(data=data)


async def ensure_manager_location(db: object, manager_id: str, location_id: str) -> None:
    existing = await db.managerlocationassignment.find_unique(
        where={"manager_id_location_id": {"manager_id": manager_id, "location_id": location_id}}
    )
    if existing is None:
        await db.managerlocationassignment.create(data={"manager_id": manager_id, "location_id": location_id})


async def ensure_user_skill(db: object, user_id: str, skill_id: str) -> None:
    existing = await db.userskill.find_unique(where={"user_id_skill_id": {"user_id": user_id, "skill_id": skill_id}})
    if existing is None:
        await db.userskill.create(data={"user_id": user_id, "skill_id": skill_id})


async def ensure_certification(db: object, user_id: str, location_id: str) -> None:
    await db.userlocationcertification.upsert(
        where={"user_id_location_id": {"user_id": user_id, "location_id": location_id}},
        data={
            "create": {"user_id": user_id, "location_id": location_id},
            "update": {"revoked_at": None, "revoked_by": None},
        },
    )


async def seed() -> None:
    db = prisma
    await connect_db()

    try:
        # Keep seed deterministic across reruns.
        await db.auditlog.delete_many()
        await db.notification.delete_many()
        await db.swaprequest.delete_many()
        await db.shiftassignment.delete_many()
        await db.shift.delete_many()

        locations = {}
        for payload in [
            {"name": "Ocean Ave", "address": "123 Ocean Ave, Santa Monica, CA", "iana_timezone": "America/Los_Angeles"},
            {"name": "Pier 39", "address": "39 Pier Blvd, San Francisco, CA", "iana_timezone": "America/Los_Angeles"},
            {"name": "Midtown Bistro", "address": "456 5th Ave, New York, NY", "iana_timezone": "America/New_York"},
            {"name": "Brooklyn Tap", "address": "789 Atlantic Ave, Brooklyn, NY", "iana_timezone": "America/New_York"},
        ]:
            location = await ensure_location(db, payload)
            locations[payload["name"]] = location

        skills = {}
        for skill_name in ["bartender", "line cook", "server", "host"]:
            skill = await ensure_skill(db, skill_name)
            skills[skill_name] = skill

        users = {}
        for payload in [
            {
                "name": "Admin User",
                "email": "admin@coastaleats.com",
                "password": "Admin123!",
                "role": "admin",
                "home_timezone": "America/New_York",
                "desired_hours_per_week": 40,
                "hourly_rate": 50.00,
            },
            {
                "name": "Jordan Lee",
                "email": "jordan@coastaleats.com",
                "password": "Manager123!",
                "role": "manager",
                "home_timezone": "America/Los_Angeles",
                "desired_hours_per_week": 40,
                "hourly_rate": 35.00,
            },
            {
                "name": "Sam Rivera",
                "email": "sam@coastaleats.com",
                "password": "Manager123!",
                "role": "manager",
                "home_timezone": "America/New_York",
                "desired_hours_per_week": 40,
                "hourly_rate": 35.00,
            },
            {
                "name": "Carlos Rivera",
                "email": "carlos@coastaleats.com",
                "password": "Staff123!",
                "role": "staff",
                "home_timezone": "America/Los_Angeles",
                "desired_hours_per_week": 32,
                "hourly_rate": 18.50,
            },
            {
                "name": "Maria Torres",
                "email": "maria@coastaleats.com",
                "password": "Staff123!",
                "role": "staff",
                "home_timezone": "America/Los_Angeles",
                "desired_hours_per_week": 40,
                "hourly_rate": 20.00,
            },
            {
                "name": "Amy Chen",
                "email": "amy@coastaleats.com",
                "password": "Staff123!",
                "role": "staff",
                "home_timezone": "America/Los_Angeles",
                "desired_hours_per_week": 32,
                "hourly_rate": 19.00,
            },
            {
                "name": "Ben Nguyen",
                "email": "ben@coastaleats.com",
                "password": "Staff123!",
                "role": "staff",
                "home_timezone": "America/Los_Angeles",
                "desired_hours_per_week": 32,
                "hourly_rate": 19.00,
            },
            {
                "name": "Alex Kim",
                "email": "alex@coastaleats.com",
                "password": "Staff123!",
                "role": "staff",
                "home_timezone": "America/Los_Angeles",
                "desired_hours_per_week": 36,
                "hourly_rate": 21.00,
            },
            {
                "name": "Dana Park",
                "email": "dana@coastaleats.com",
                "password": "Staff123!",
                "role": "staff",
                "home_timezone": "America/Los_Angeles",
                "desired_hours_per_week": 30,
                "hourly_rate": 18.00,
            },
            {
                "name": "Finn Walsh",
                "email": "finn@coastaleats.com",
                "password": "Staff123!",
                "role": "staff",
                "home_timezone": "America/New_York",
                "desired_hours_per_week": 28,
                "hourly_rate": 17.50,
            },
            {
                "name": "Luna Patel",
                "email": "luna@coastaleats.com",
                "password": "Staff123!",
                "role": "staff",
                "home_timezone": "America/New_York",
                "desired_hours_per_week": 30,
                "hourly_rate": 17.00,
            },
        ]:
            user = await ensure_user(db, payload)
            users[payload["email"]] = user

        await ensure_manager_location(db, users["jordan@coastaleats.com"].id, locations["Ocean Ave"].id)
        await ensure_manager_location(db, users["jordan@coastaleats.com"].id, locations["Midtown Bistro"].id)
        await ensure_manager_location(db, users["sam@coastaleats.com"].id, locations["Pier 39"].id)
        await ensure_manager_location(db, users["sam@coastaleats.com"].id, locations["Brooklyn Tap"].id)

        staff_setup = {
            "carlos@coastaleats.com": {"skills": ["bartender", "server"], "locations": ["Ocean Ave", "Midtown Bistro"]},
            "maria@coastaleats.com": {"skills": ["bartender", "server"], "locations": ["Ocean Ave"]},
            "amy@coastaleats.com": {"skills": ["server", "host"], "locations": ["Ocean Ave"]},
            "ben@coastaleats.com": {"skills": ["server", "host"], "locations": ["Ocean Ave"]},
            "alex@coastaleats.com": {"skills": ["line cook", "bartender"], "locations": ["Ocean Ave", "Pier 39"]},
            "dana@coastaleats.com": {"skills": ["bartender", "host"], "locations": ["Ocean Ave"]},
            "finn@coastaleats.com": {"skills": ["host", "server"], "locations": ["Midtown Bistro"]},
            "luna@coastaleats.com": {"skills": ["server", "host"], "locations": ["Brooklyn Tap", "Midtown Bistro"]},
        }

        for email, setup in staff_setup.items():
            user = users[email]
            for skill_name in setup["skills"]:
                await ensure_user_skill(db, user.id, skills[skill_name].id)
            for location_name in setup["locations"]:
                await ensure_certification(db, user.id, locations[location_name].id)

        await db.availability.delete_many(where={"user_id": users["carlos@coastaleats.com"].id})
        await db.availability.create_many(
            data=[
                {
                    "user_id": users["carlos@coastaleats.com"].id,
                    "avail_type": "recurring",
                    "day_of_week": 1,
                    "start_clock": "09:00",
                    "end_clock": "17:00",
                },
                {
                    "user_id": users["carlos@coastaleats.com"].id,
                    "avail_type": "recurring",
                    "day_of_week": 2,
                    "start_clock": "09:00",
                    "end_clock": "17:00",
                },
                {
                    "user_id": users["carlos@coastaleats.com"].id,
                    "avail_type": "recurring",
                    "day_of_week": 6,
                    "start_clock": "17:00",
                    "end_clock": "23:59",
                },
            ]
        )

        # Scenario: staff at overtime threshold (Maria at ~35h this week at Ocean Ave).
        ocean = locations["Ocean Ave"]
        la_today = datetime.now(ZoneInfo(ocean.iana_timezone)).date()
        current_week_monday = _week_start_monday(la_today)
        maria_id = users["maria@coastaleats.com"].id
        jordan_id = users["jordan@coastaleats.com"].id
        bartender_id = skills["bartender"].id
        for offset in range(5):
            day = current_week_monday + timedelta(days=offset)
            shift = await create_seed_shift(
                db,
                location=ocean,
                required_skill_id=bartender_id,
                shift_date=day,
                start_clock="10:00",
                end_clock="17:00",
                created_by=jordan_id,
                status="published",
            )
            await create_seed_assignment(db, shift_id=shift.id, user_id=maria_id, assigned_by=jordan_id)

        # Scenario: Sunday Night Chaos (high-pressure Sunday evening demand).
        sunday = current_week_monday + timedelta(days=6)
        await create_seed_shift(
            db,
            location=ocean,
            required_skill_id=bartender_id,
            shift_date=sunday,
            start_clock="18:00",
            end_clock="23:00",
            created_by=jordan_id,
            status="published",
            headcount_needed=2,
        )

        # Scenario: fairness imbalance over 4 weeks (Ben gets premium shifts; Amy gets regular shifts).
        ben_id = users["ben@coastaleats.com"].id
        amy_id = users["amy@coastaleats.com"].id
        server_id = skills["server"].id
        for week_back in range(1, 5):
            week_monday = current_week_monday - timedelta(days=7 * week_back)
            friday = week_monday + timedelta(days=4)
            saturday = week_monday + timedelta(days=5)
            wednesday = week_monday + timedelta(days=2)

            premium_fri = await create_seed_shift(
                db,
                location=ocean,
                required_skill_id=server_id,
                shift_date=friday,
                start_clock="18:00",
                end_clock="23:00",
                created_by=jordan_id,
                status="published",
            )
            premium_sat = await create_seed_shift(
                db,
                location=ocean,
                required_skill_id=server_id,
                shift_date=saturday,
                start_clock="18:00",
                end_clock="23:00",
                created_by=jordan_id,
                status="published",
            )
            regular_amy = await create_seed_shift(
                db,
                location=ocean,
                required_skill_id=server_id,
                shift_date=wednesday,
                start_clock="09:00",
                end_clock="13:00",
                created_by=jordan_id,
                status="published",
            )
            await create_seed_assignment(db, shift_id=premium_fri.id, user_id=ben_id, assigned_by=jordan_id)
            await create_seed_assignment(db, shift_id=premium_sat.id, user_id=ben_id, assigned_by=jordan_id)
            await create_seed_assignment(db, shift_id=regular_amy.id, user_id=amy_id, assigned_by=jordan_id)

        # Scenario: de-certified staff with historical assignment (Dana at Pier 39).
        dana_id = users["dana@coastaleats.com"].id
        sam_id = users["sam@coastaleats.com"].id
        pier = locations["Pier 39"]
        await ensure_certification(db, dana_id, pier.id)
        historical_date = current_week_monday - timedelta(days=35)
        pier_shift = await create_seed_shift(
            db,
            location=pier,
            required_skill_id=bartender_id,
            shift_date=historical_date,
            start_clock="18:00",
            end_clock="22:00",
            created_by=sam_id,
            status="published",
        )
        await create_seed_assignment(db, shift_id=pier_shift.id, user_id=dana_id, assigned_by=sam_id)
        await db.userlocationcertification.update(
            where={"user_id_location_id": {"user_id": dana_id, "location_id": pier.id}},
            data={"revoked_at": datetime.now(tz=timezone.utc) - timedelta(days=30), "revoked_by": users["admin@coastaleats.com"].id},
        )

        # Scenario: pending swap request (Regret Swap workflow).
        midtown = locations["Midtown Bistro"]
        host_id = skills["host"].id
        finn_id = users["finn@coastaleats.com"].id
        luna_id = users["luna@coastaleats.com"].id
        ny_today = datetime.now(ZoneInfo(midtown.iana_timezone)).date()
        next_week_monday = _week_start_monday(ny_today) + timedelta(days=7)
        swap_shift_a = await create_seed_shift(
            db,
            location=midtown,
            required_skill_id=host_id,
            shift_date=next_week_monday + timedelta(days=1),
            start_clock="10:00",
            end_clock="14:00",
            created_by=jordan_id,
            status="published",
        )
        swap_shift_b = await create_seed_shift(
            db,
            location=midtown,
            required_skill_id=host_id,
            shift_date=next_week_monday + timedelta(days=2),
            start_clock="10:00",
            end_clock="14:00",
            created_by=jordan_id,
            status="published",
        )
        asg_a = await create_seed_assignment(db, shift_id=swap_shift_a.id, user_id=finn_id, assigned_by=jordan_id)
        asg_b = await create_seed_assignment(db, shift_id=swap_shift_b.id, user_id=luna_id, assigned_by=jordan_id)
        await db.swaprequest.create(
            data={
                "type": "swap",
                "requester_assignment_id": asg_a.id,
                "target_user_id": luna_id,
                "candidate_assignment_id": asg_b.id,
                "status": "PENDING_MANAGER",
                "initiated_by": finn_id,
                "resolution_note": "Need manager approval for planned travel.",
            }
        )

        print("Seed complete (Phase 1 baseline + Phase 4/5 scenarios).")
    finally:
        await disconnect_db()


if __name__ == "__main__":
    asyncio.run(seed())
