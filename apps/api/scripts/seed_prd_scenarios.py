import asyncio
import uuid
from datetime import datetime, timedelta, date, timezone
from zoneinfo import ZoneInfo
from app.core.database import engine, AsyncSessionLocal
from app.core.models import Shift, ShiftAssignment, SwapRequest, Location, User, Skill, Notification
from sqlalchemy import select, delete

async def main():
    async with AsyncSessionLocal() as session:
        # Fetch fundamental DB records
        stmt_locs = select(Location)
        result_locs = await session.execute(stmt_locs)
        locations = {loc.name: loc for loc in result_locs.scalars().all()}
        
        stmt_skills = select(Skill)
        result_skills = await session.execute(stmt_skills)
        skills = {skill.name: skill for skill in result_skills.scalars().all()}
        
        stmt_users = select(User)
        result_users = await session.execute(stmt_users)
        users = {user.name: user for user in result_users.scalars().all()}
        
        # Clear existing seed data
        admin = users.get("Admin User")
        if not admin:
            print("Could not find Admin User. Exiting.")
            return

        print("Cleaning up old mock shifts...")
        await session.execute(delete(Shift).where(Shift.created_by == admin.id))
        await session.commit()
        
        loc_pt = locations.get("Ocean Ave")
        loc_et = locations.get("Midtown Bistro")
        skill_bartender = skills.get("bartender")
        skill_server = skills.get("server")
        
        manager = users.get("Jordan Lee")
        staff_a = users.get("Carlos Rivera")
        staff_b = users.get("Amy Chen")
        
        # We need a week starting next Monday for clean viewing
        today = date.today()
        days_ahead = 0 - today.weekday()
        if days_ahead <= 0: # Target next Monday
            days_ahead += 7
        next_monday = today + timedelta(days=days_ahead)
        
        print(f"Seeding week starting: {next_monday}")

        # ---------------------------------------------------------
        # Scenario 2: The Overtime Trap (Trigger Overtime)
        # ---------------------------------------------------------
        print("Seeding Overtime Base Scenario...")
        for i in range(4): # Mon-Thu
            shift_date = next_monday + timedelta(days=i)
            start_dt = datetime.combine(shift_date, datetime.strptime("09:00", "%H:%M").time())
            start_utc = start_dt.replace(tzinfo=ZoneInfo(loc_pt.iana_timezone)).astimezone(timezone.utc)
            end_utc = start_utc + timedelta(hours=8)
            
            s = Shift(
                location_id=loc_pt.id,
                required_skill_id=skill_bartender.id,
                shift_date=shift_date,
                start_utc=start_utc,
                end_utc=end_utc,
                headcount_needed=1,
                status="published",
                week_start=next_monday,
                created_by=admin.id
            )
            session.add(s)
            
            # Need to flush to get shift.id for the assignment
            await session.flush()
            
            a = ShiftAssignment(
                shift_id=s.id,
                user_id=staff_a.id,
                assigned_by=manager.id,
                status="assigned"
            )
            session.add(a)

        # ---------------------------------------------------------
        # Scenario 3: The Timezone Tangle
        # ---------------------------------------------------------
        print("Seeding Timezone Base Scenario...")
        tz_shift_date = next_monday + timedelta(days=4) # Friday
        
        tz_start_1 = datetime.combine(tz_shift_date, datetime.strptime("09:00", "%H:%M").time())
        tz_start_1_utc = tz_start_1.replace(tzinfo=ZoneInfo(loc_et.iana_timezone)).astimezone(timezone.utc)
        s_tz_1 = Shift(
            location_id=loc_et.id,
            required_skill_id=skill_server.id,
            shift_date=tz_shift_date,
            start_utc=tz_start_1_utc,
            end_utc=tz_start_1_utc + timedelta(hours=8),
            headcount_needed=1,
            status="published",
            week_start=next_monday,
            created_by=admin.id
        )
        session.add(s_tz_1)

        tz_start_2 = datetime.combine(tz_shift_date, datetime.strptime("12:00", "%H:%M").time())
        tz_start_2_utc = tz_start_2.replace(tzinfo=ZoneInfo(loc_et.iana_timezone)).astimezone(timezone.utc)
        s_tz_2 = Shift(
            location_id=loc_et.id,
            required_skill_id=skill_server.id,
            shift_date=tz_shift_date,
            start_utc=tz_start_2_utc,
            end_utc=tz_start_2_utc + timedelta(hours=8),
            headcount_needed=1,
            status="published",
            week_start=next_monday,
            created_by=admin.id
        )
        session.add(s_tz_2)

        # ---------------------------------------------------------
        # Scenario 5: Fairness Analytics (Premium Shifts)
        # ---------------------------------------------------------
        print("Seeding Fairness/Premium Scenarios...")
        # Going back 1 week
        past_friday = next_monday - timedelta(days=3)
        past_saturday = next_monday - timedelta(days=2)
        
        for d in [past_friday, past_saturday]:
            start_dt = datetime.combine(d, datetime.strptime("18:00", "%H:%M").time())
            start_utc = start_dt.replace(tzinfo=ZoneInfo(loc_pt.iana_timezone)).astimezone(timezone.utc)
            
            s_prem = Shift(
                location_id=loc_pt.id,
                required_skill_id=skill_bartender.id,
                shift_date=d,
                start_utc=start_utc,
                end_utc=start_utc + timedelta(hours=6),
                headcount_needed=1,
                status="published",
                week_start=d - timedelta(days=d.weekday()), # The Monday of that past week
                created_by=admin.id
            )
            session.add(s_prem)
            await session.flush()
            
            a_prem = ShiftAssignment(
                shift_id=s_prem.id,
                user_id=staff_b.id,
                assigned_by=manager.id,
                status="assigned"
            )
            session.add(a_prem)

        # ---------------------------------------------------------
        # Scenario 6: The Regret Swap
        # ---------------------------------------------------------
        print("Seeding Swap Flow Scenarios...")
        swap_date = next_monday + timedelta(days=2) # Wednesday
        swap_start_dt = datetime.combine(swap_date, datetime.strptime("10:00", "%H:%M").time())
        swap_start_utc = swap_start_dt.replace(tzinfo=ZoneInfo(loc_pt.iana_timezone)).astimezone(timezone.utc)
        
        s_swap = Shift(
            location_id=loc_pt.id,
            required_skill_id=skill_server.id,
            shift_date=swap_date,
            start_utc=swap_start_utc,
            end_utc=swap_start_utc + timedelta(hours=6),
            headcount_needed=1,
            status="published",
            week_start=next_monday,
            created_by=admin.id
        )
        session.add(s_swap)
        await session.flush()
        
        a_swap = ShiftAssignment(
            shift_id=s_swap.id,
            user_id=staff_b.id, # Staff B has this shift
            assigned_by=manager.id,
            status="swap_pending"
        )
        session.add(a_swap)
        await session.flush() # Needed for swap request fk
        
        swap_req = SwapRequest(
            type="swap",
            requester_assignment_id=a_swap.id,
            target_user_id=staff_a.id, # Wants to swap with Carlos
            status="PENDING_MANAGER", # Carlos accepted
            initiated_by=staff_b.id
        )
        session.add(swap_req)
        
        # ---------------------------------------------------------
        # Scenario 1: Open Drop for Pickup
        # ---------------------------------------------------------
        print("Seeding Open Drop Request...")
        drop_date = next_monday + timedelta(days=5) # Saturday
        drop_start_dt = datetime.combine(drop_date, datetime.strptime("10:00", "%H:%M").time())
        drop_start_utc = drop_start_dt.replace(tzinfo=ZoneInfo(loc_pt.iana_timezone)).astimezone(timezone.utc)
        
        s_drop = Shift(
            location_id=loc_pt.id,
            required_skill_id=skill_bartender.id,
            shift_date=drop_date,
            start_utc=drop_start_utc,
            end_utc=drop_start_utc + timedelta(hours=6),
            headcount_needed=1,
            status="published",
            week_start=next_monday,
            created_by=admin.id
        )
        session.add(s_drop)
        await session.flush()
        
        a_drop = ShiftAssignment(
            shift_id=s_drop.id,
            user_id=staff_b.id,
            assigned_by=manager.id,
            status="assigned"
        )
        session.add(a_drop)
        await session.flush()
        
        drop_req = SwapRequest(
            type="drop",
            requester_assignment_id=a_drop.id,
            status="OPEN",
            initiated_by=staff_b.id
        )
        session.add(drop_req)
        
        try:
            await session.commit()
            print("Successfully seeded all PRD scenarios!")
        except Exception as e:
            await session.rollback()
            print(f"Failed to seed: {e}")

if __name__ == "__main__":
    asyncio.run(main())
