import asyncio
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from passlib.context import CryptContext
from prisma import Prisma


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
ROOT_DIR = Path(__file__).resolve().parents[1]
load_dotenv(ROOT_DIR / ".env", override=False)
load_dotenv(ROOT_DIR / ".env.local", override=True)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


async def ensure_location(db: Prisma, payload: dict[str, Any]) -> Any:
    existing = await db.location.find_first(where={"name": payload["name"]})
    if existing:
        return existing
    return await db.location.create(data=payload)


async def ensure_skill(db: Prisma, name: str) -> Any:
    existing = await db.skill.find_unique(where={"name": name})
    if existing:
        return existing
    return await db.skill.create(data={"name": name})


async def ensure_user(db: Prisma, payload: dict[str, Any]) -> Any:
    existing = await db.user.find_unique(where={"email": payload["email"]})
    if existing:
        return existing
    data = payload.copy()
    data["password_hash"] = hash_password(data.pop("password"))
    return await db.user.create(data=data)


async def ensure_manager_location(db: Prisma, manager_id: str, location_id: str) -> None:
    existing = await db.managerlocationassignment.find_unique(
        where={"manager_id_location_id": {"manager_id": manager_id, "location_id": location_id}}
    )
    if existing is None:
        await db.managerlocationassignment.create(data={"manager_id": manager_id, "location_id": location_id})


async def ensure_user_skill(db: Prisma, user_id: str, skill_id: str) -> None:
    existing = await db.userskill.find_unique(where={"user_id_skill_id": {"user_id": user_id, "skill_id": skill_id}})
    if existing is None:
        await db.userskill.create(data={"user_id": user_id, "skill_id": skill_id})


async def ensure_certification(db: Prisma, user_id: str, location_id: str) -> None:
    await db.userlocationcertification.upsert(
        where={"user_id_location_id": {"user_id": user_id, "location_id": location_id}},
        data={
            "create": {"user_id": user_id, "location_id": location_id},
            "update": {"revoked_at": None, "revoked_by": None},
        },
    )


async def seed() -> None:
    db = Prisma()
    await db.connect()

    try:
        # Keep seed deterministic across reruns.
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
            "carlos@coastaleats.com": {"skills": ["bartender"], "locations": ["Ocean Ave", "Midtown Bistro"]},
            "maria@coastaleats.com": {"skills": ["bartender", "server"], "locations": ["Ocean Ave"]},
            "amy@coastaleats.com": {"skills": ["server", "host"], "locations": ["Ocean Ave"]},
            "ben@coastaleats.com": {"skills": ["server"], "locations": ["Ocean Ave"]},
            "alex@coastaleats.com": {"skills": ["line cook"], "locations": ["Ocean Ave", "Pier 39"]},
            "dana@coastaleats.com": {"skills": ["bartender"], "locations": ["Ocean Ave"]},
            "finn@coastaleats.com": {"skills": ["host"], "locations": ["Midtown Bistro"]},
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

        print("Phase 1 seed complete.")
    finally:
        await db.disconnect()


if __name__ == "__main__":
    asyncio.run(seed())
