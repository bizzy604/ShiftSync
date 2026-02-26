from datetime import date, datetime, time, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import (
    CurrentUser,
    ensure_manager_location_access,
    get_current_user,
    require_roles,
)
from app.core.database import prisma
from app.schemas.shift import (
    PublishWeekRequest,
    PublishWeekResponse,
    ShiftCreateRequest,
    ShiftListResponse,
    ShiftRequiredSkill,
    ShiftResponse,
    ShiftUpdateRequest,
    UnpublishShiftRequest,
)
from app.services.timezone_utils import format_local_iso, parse_shift_local_range, week_start_monday


router = APIRouter()


def _date_as_date(value: Any) -> date:
    if isinstance(value, datetime):
        return value.date()
    return value


def _date_as_datetime(value: date) -> datetime:
    return datetime.combine(value, time.min)


def _to_shift_response(shift: object, location_timezone: str | None = None) -> ShiftResponse:
    tz_name = location_timezone
    if tz_name is None and getattr(shift, "location", None) is not None:
        tz_name = shift.location.iana_timezone
    if tz_name is None:
        tz_name = "UTC"

    required_skill = getattr(shift, "required_skill", None)
    required_skill_id = shift.required_skill_id
    required_skill_name = required_skill.name if required_skill is not None else "unknown"

    return ShiftResponse(
        id=shift.id,
        location_id=shift.location_id,
        date=_date_as_date(shift.shift_date),
        start_utc=shift.start_utc,
        end_utc=shift.end_utc,
        start_local=format_local_iso(shift.start_utc, tz_name),
        end_local=format_local_iso(shift.end_utc, tz_name),
        required_skill=ShiftRequiredSkill(id=required_skill_id, name=required_skill_name),
        headcount_needed=shift.headcount_needed,
        status=shift.status,
        week_start=_date_as_date(shift.week_start),
        edit_cutoff_utc=shift.edit_cutoff_utc,
        created_at=shift.created_at,
    )


async def _get_location_or_404(location_id: str) -> object:
    location = await prisma.location.find_unique(where={"id": location_id})
    if location is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Location not found.")
    return location


async def _ensure_staff_location_access(user_id: str, location_id: str) -> None:
    cert = await prisma.userlocationcertification.find_unique(
        where={"user_id_location_id": {"user_id": user_id, "location_id": location_id}},
    )
    if cert is None or cert.revoked_at is not None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")


@router.get("/locations/{location_id}/shifts", response_model=ShiftListResponse)
async def list_shifts(
    location_id: str,
    week_start: date = Query(...),
    status_filter: str | None = Query(default=None, alias="status"),
    current_user: CurrentUser = Depends(get_current_user),
) -> ShiftListResponse:
    location = await _get_location_or_404(location_id)

    if current_user.role == "manager":
        ensure_manager_location_access(current_user, location_id)
    elif current_user.role == "staff":
        await _ensure_staff_location_access(current_user.id, location_id)
        assignments = await prisma.shiftassignment.find_many(
            where={"user_id": current_user.id, "status": "assigned"},
            include={"shift": {"include": {"required_skill": True, "location": True}}},
            order={"assigned_at": "desc"},
        )
        shifts: list[object] = []
        for assignment in assignments:
            shift = assignment.shift
            if shift is None:
                continue
            if shift.location_id != location_id:
                continue
            if _date_as_date(shift.week_start) != week_start:
                continue
            if status_filter and shift.status != status_filter:
                continue
            shifts.append(shift)
        return ShiftListResponse(shifts=[_to_shift_response(shift, location.iana_timezone) for shift in shifts])

    where: dict[str, Any] = {
        "location_id": location_id,
        "week_start": _date_as_datetime(week_start),
    }
    if status_filter:
        where["status"] = status_filter

    shifts = await prisma.shift.find_many(
        where=where,
        include={"required_skill": True, "location": True},
        order={"start_utc": "asc"},
    )
    return ShiftListResponse(shifts=[_to_shift_response(shift, location.iana_timezone) for shift in shifts])


@router.post("/locations/{location_id}/shifts", response_model=ShiftResponse)
async def create_shift(
    location_id: str,
    payload: ShiftCreateRequest,
    current_user: CurrentUser = Depends(require_roles("admin", "manager")),
) -> ShiftResponse:
    location = await _get_location_or_404(location_id)
    if current_user.role == "manager":
        ensure_manager_location_access(current_user, location_id)

    skill = await prisma.skill.find_unique(where={"id": payload.required_skill_id})
    if skill is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Skill not found.")

    start_utc, end_utc = parse_shift_local_range(
        shift_date=payload.shift_date,
        start_time_hhmm=payload.start_time,
        end_time_hhmm=payload.end_time,
        timezone_name=location.iana_timezone,
    )
    week_start_value = week_start_monday(payload.shift_date)

    shift = await prisma.shift.create(
        data={
            "location_id": location_id,
            "required_skill_id": payload.required_skill_id,
            "shift_date": _date_as_datetime(payload.shift_date),
            "start_utc": start_utc,
            "end_utc": end_utc,
            "headcount_needed": payload.headcount_needed,
            "status": "draft",
            "week_start": _date_as_datetime(week_start_value),
            "created_by": current_user.id,
        },
        include={"required_skill": True, "location": True},
    )
    return _to_shift_response(shift, location.iana_timezone)


@router.get("/locations/{location_id}/shifts/{shift_id}", response_model=ShiftResponse)
async def get_shift(
    location_id: str,
    shift_id: str,
    current_user: CurrentUser = Depends(get_current_user),
) -> ShiftResponse:
    location = await _get_location_or_404(location_id)
    shift = await prisma.shift.find_unique(
        where={"id": shift_id},
        include={"required_skill": True, "location": True},
    )
    if shift is None or shift.location_id != location_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shift not found.")

    if current_user.role == "manager":
        ensure_manager_location_access(current_user, location_id)
    elif current_user.role == "staff":
        assignment = await prisma.shiftassignment.find_first(
            where={"shift_id": shift_id, "user_id": current_user.id, "status": "assigned"},
        )
        if assignment is None:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")

    return _to_shift_response(shift, location.iana_timezone)


@router.put("/locations/{location_id}/shifts/{shift_id}", response_model=ShiftResponse)
async def update_shift(
    location_id: str,
    shift_id: str,
    payload: ShiftUpdateRequest,
    current_user: CurrentUser = Depends(require_roles("admin", "manager")),
) -> ShiftResponse:
    location = await _get_location_or_404(location_id)
    if current_user.role == "manager":
        ensure_manager_location_access(current_user, location_id)

    shift = await prisma.shift.find_unique(
        where={"id": shift_id},
        include={"required_skill": True, "location": True},
    )
    if shift is None or shift.location_id != location_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shift not found.")

    if shift.status == "published" and shift.edit_cutoff_utc and datetime.now(tz=timezone.utc) > shift.edit_cutoff_utc:
        if not payload.override_reason:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Published shift is past edit cutoff. Override reason is required.",
            )

    new_date = payload.shift_date or _date_as_date(shift.shift_date)

    # Restore local HH:MM defaults using location timezone.
    location_tz = ZoneInfo(location.iana_timezone)
    existing_start_hhmm = shift.start_utc.astimezone(location_tz).strftime("%H:%M")
    existing_end_hhmm = shift.end_utc.astimezone(location_tz).strftime("%H:%M")
    start_hhmm = payload.start_time or existing_start_hhmm
    end_hhmm = payload.end_time or existing_end_hhmm

    start_utc, end_utc = parse_shift_local_range(
        shift_date=new_date,
        start_time_hhmm=start_hhmm,
        end_time_hhmm=end_hhmm,
        timezone_name=location.iana_timezone,
    )
    week_start_value = week_start_monday(new_date)

    required_skill_id = payload.required_skill_id or shift.required_skill_id
    if payload.required_skill_id:
        skill = await prisma.skill.find_unique(where={"id": payload.required_skill_id})
        if skill is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Skill not found.")

    update_data: dict[str, Any] = {
        "shift_date": _date_as_datetime(new_date),
        "start_utc": start_utc,
        "end_utc": end_utc,
        "required_skill_id": required_skill_id,
        "headcount_needed": payload.headcount_needed or shift.headcount_needed,
        "week_start": _date_as_datetime(week_start_value),
    }

    updated = await prisma.shift.update(
        where={"id": shift_id},
        data=update_data,
        include={"required_skill": True, "location": True},
    )
    return _to_shift_response(updated, location.iana_timezone)


@router.delete("/locations/{location_id}/shifts/{shift_id}")
async def delete_shift(
    location_id: str,
    shift_id: str,
    current_user: CurrentUser = Depends(require_roles("admin", "manager")),
) -> dict[str, bool]:
    if current_user.role == "manager":
        ensure_manager_location_access(current_user, location_id)

    shift = await prisma.shift.find_unique(where={"id": shift_id})
    if shift is None or shift.location_id != location_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shift not found.")

    await prisma.shift.update(where={"id": shift_id}, data={"status": "cancelled"})
    return {"deleted": True}


@router.post("/locations/{location_id}/shifts/publish-week", response_model=PublishWeekResponse)
async def publish_week(
    location_id: str,
    payload: PublishWeekRequest,
    current_user: CurrentUser = Depends(require_roles("admin", "manager")),
) -> PublishWeekResponse:
    if current_user.role == "manager":
        ensure_manager_location_access(current_user, location_id)

    shifts = await prisma.shift.find_many(
        where={
            "location_id": location_id,
            "week_start": _date_as_datetime(payload.week_start),
            "status": {"in": ["draft", "published"]},
        },
        order={"start_utc": "asc"},
    )
    if not shifts:
        return PublishWeekResponse(published_shifts=0, edit_cutoff_utc=None, notified_staff_count=0)

    earliest_start = min(shift.start_utc for shift in shifts)
    cutoff = earliest_start - timedelta(hours=48)

    now = datetime.now(tz=timezone.utc)
    for shift in shifts:
        await prisma.shift.update(
            where={"id": shift.id},
            data={
                "status": "published",
                "published_at": now,
                "edit_cutoff_utc": cutoff,
            },
        )

    return PublishWeekResponse(
        published_shifts=len(shifts),
        edit_cutoff_utc=cutoff,
        notified_staff_count=0,
    )


@router.post("/locations/{location_id}/shifts/{shift_id}/unpublish", response_model=ShiftResponse)
async def unpublish_shift(
    location_id: str,
    shift_id: str,
    payload: UnpublishShiftRequest,
    current_user: CurrentUser = Depends(require_roles("admin", "manager")),
) -> ShiftResponse:
    location = await _get_location_or_404(location_id)
    if current_user.role == "manager":
        ensure_manager_location_access(current_user, location_id)

    shift = await prisma.shift.find_unique(
        where={"id": shift_id},
        include={"required_skill": True, "location": True},
    )
    if shift is None or shift.location_id != location_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shift not found.")

    if shift.status != "published":
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Shift is not published.")

    if shift.edit_cutoff_utc and datetime.now(tz=timezone.utc) > shift.edit_cutoff_utc and not payload.override_reason:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Past edit cutoff. Override reason is required to unpublish.",
        )

    updated = await prisma.shift.update(
        where={"id": shift_id},
        data={"status": "draft", "published_at": None},
        include={"required_skill": True, "location": True},
    )
    return _to_shift_response(updated, location.iana_timezone)
