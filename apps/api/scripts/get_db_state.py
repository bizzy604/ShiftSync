import asyncio
from app.core.database import prisma, engine

async def main():
    locations = await prisma.location.find_many()
    print("Locations:", len(locations))
    for loc in locations:
        print(f"  {loc.id} | {loc.name} | {loc.iana_timezone}")

    skills = await prisma.skill.find_many()
    print("Skills:", len(skills))
    for s in skills:
        print(f"  {s.id} | {s.name}")

    users = await prisma.user.find_many()
    print("Users:", len(users))
    for u in users[:5]:
        print(f"  {u.id} | {u.name} | {u.role}")

    if len(users) > 5:
        print(f"  ... and {len(users)-5} more users")

if __name__ == "__main__":
    asyncio.run(main())
