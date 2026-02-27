"""
MODULE: /apps/api/app/api/routes/shifts.py

FUNCTION:
    Defines FastAPI endpoints and request/response orchestration for the `shifts` domain.

DEPENDENCIES:
    - /apps/api/app/api/router.py
    - /apps/api/tests/integration/test_shifts_prune_unclaimed.py

IMPORTANCE:
    This module directly shapes externally visible API behavior and role-based access flows.
"""

from datetime import date, datetime, time, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

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
from app.services.audit import create_audit_log
from app.services.notifications import create_notification
from app.services.swap_lifecycle import cancel_pending_swaps_for_shift
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


async def _prune_past_unclaimed_shifts(shifts: list[object], *, now_utc: datetime | None = None) -> list[object]:
    if not shifts:
        return shifts

    effective_now = now_utc or datetime.now(tz=timezone.utc)
    candidate_shift_ids = [
        shift.id
        for shift in shifts
        if shift.status in {"draft", "published"} and shift.end_utc <= effective_now
    ]
    if not candidate_shift_ids:
        return shifts

    assignments = await prisma.shiftassignment.find_many(
        where={"shift_id": {"in": candidate_shift_ids}, "status": "assigned"},
    )
    assigned_counts: dict[str, int] = {}
    for assignment in assignments:
        assigned_counts[assignment.shift_id] = assigned_counts.get(assignment.shift_id, 0) + 1

    filtered: list[object] = []
    for shift in shifts:
        if shift.id not in candidate_shift_ids:
            filtered.append(shift)
            continue

        assigned = assigned_counts.get(shift.id, 0)
        if assigned >= int(shift.headcount_needed or 0):
            filtered.append(shift)

    return filtered


@router.get("", response_model=ShiftListResponse)
async def list_shifts(
    location_id: str = Query(...),
    week_start: date = Query(...),
    status_filter: str | None = Query(default=None, alias="status"),
    current_user: CurrentUser = Depends(get_current_user),
) -> ShiftListResponse:
    """List shifts.
    
    Args:
        location_id: Target location identifier.
        week_start: Input parameter `week_start` used by this operation.
        status_filter: Input parameter `status_filter` used by this operation.
        current_user: Authenticated user from dependency resolution.
    
    Returns:
        Result typed as `ShiftListResponse`.
    """
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
    if current_user.role in {"admin", "manager"}:
        shifts = await _prune_past_unclaimed_shifts(shifts)
    return ShiftListResponse(shifts=[_to_shift_response(shift, location.iana_timezone) for shift in shifts])


@router.post("", response_model=ShiftResponse)
async def create_shift(
    payload: ShiftCreateRequest,
    location_id: str = Query(...),
    current_user: CurrentUser = Depends(require_roles("admin", "manager")),
) -> ShiftResponse:
    """Create shift.
    
    Args:
        payload: Validated request payload model.
        location_id: Target location identifier.
        current_user: Authenticated user from dependency resolution.
    
    Returns:
        Result typed as `ShiftResponse`.
    """
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

    async with prisma.tx() as tx:
        shift = await tx.shift.create(
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
        await create_audit_log(
            actor_id=current_user.id,
            action_type="shift.create",
            entity_type="shift",
            entity_id=shift.id,
            location_id=location_id,
            after_state={
                "location_id": shift.location_id,
                "required_skill_id": shift.required_skill_id,
                "shift_date": _date_as_date(shift.shift_date).isoformat(),
                "start_utc": shift.start_utc.isoformat(),
                "end_utc": shift.end_utc.isoformat(),
                "status": shift.status,
                "headcount_needed": shift.headcount_needed,
            },
            db=tx,
        )
    return _to_shift_response(shift, location.iana_timezone)


@router.get("/{shift_id}", response_model=ShiftResponse)
async def get_shift(
    shift_id: str,
    location_id: str = Query(...),
    current_user: CurrentUser = Depends(get_current_user),
) -> ShiftResponse:
    """Get shift.
    
    Args:
        shift_id: Target shift identifier.
        location_id: Target location identifier.
        current_user: Authenticated user from dependency resolution.
    
    Returns:
        Result typed as `ShiftResponse`.
    """
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


@router.put("/{shift_id}", response_model=ShiftResponse)
async def update_shift(
    shift_id: str,
    payload: ShiftUpdateRequest,
    request: Request,
    location_id: str = Query(...),
    current_user: CurrentUser = Depends(require_roles("admin", "manager")),
) -> ShiftResponse:
    """Update shift.
    
    Args:
        shift_id: Target shift identifier.
        payload: Validated request payload model.
        request: Incoming FastAPI request context.
        location_id: Target location identifier.
        current_user: Authenticated user from dependency resolution.
    
    Returns:
        Result typed as `ShiftResponse`.
    """
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

    affected_user_ids: list[str] = []
    notification_records: list[object] = []
    async with prisma.tx() as tx:
        updated = await tx.shift.update(
            where={"id": shift_id},
            data=update_data,
            include={"required_skill": True, "location": True},
        )
        await create_audit_log(
            actor_id=current_user.id,
            action_type="shift.update",
            entity_type="shift",
            entity_id=shift_id,
            location_id=location_id,
            before_state={
                "shift_date": _date_as_date(shift.shift_date).isoformat(),
                "start_utc": shift.start_utc.isoformat(),
                "end_utc": shift.end_utc.isoformat(),
                "required_skill_id": shift.required_skill_id,
                "headcount_needed": shift.headcount_needed,
                "status": shift.status,
            },
            after_state={
                "shift_date": _date_as_date(updated.shift_date).isoformat(),
                "start_utc": updated.start_utc.isoformat(),
                "end_utc": updated.end_utc.isoformat(),
                "required_skill_id": updated.required_skill_id,
                "headcount_needed": updated.headcount_needed,
                "status": updated.status,
            },
            reason=payload.override_reason,
            db=tx,
        )
        active_assignments = await tx.shiftassignment.find_many(where={"shift_id": shift_id, "status": "assigned"})
        affected_user_ids = sorted({item.user_id for item in active_assignments})
        for user_id in affected_user_ids:
            record = await create_notification(
                user_id=user_id,
                notif_type="shift.changed",
                message=f"Your shift at {location.name} was updated.",
                payload={"shiftId": shift_id, "locationId": location_id},
                db=tx,
                ws_manager=None,
            )
            notification_records.append(record)

    ws_manager = request.app.state.ws_manager
    await cancel_pending_swaps_for_shift(
        shift_id=shift_id,
        actor_id=current_user.id,
        reason="Swap request cancelled because the shift was edited.",
        ws_manager=ws_manager,
    )

    if shift.status == "published":
        payload_data = {
            "locationId": location_id,
            "shiftId": shift_id,
            "changes": {
                "shiftDate": new_date.isoformat(),
                "startUtc": start_utc.isoformat(),
                "endUtc": end_utc.isoformat(),
                "requiredSkillId": required_skill_id,
                "headcountNeeded": update_data["headcount_needed"],
            },
        }
        await ws_manager.emit_to_location(
            location_id,
            "schedule.updated",
            payload_data,
        )
        if affected_user_ids:
            await ws_manager.emit_to_users(affected_user_ids, "schedule.updated", payload_data)
            for record in notification_records:
                await ws_manager.emit_to_user(
                    record.user_id,
                    "notification.new",
                    {"notificationId": record.id, "type": record.type, "message": record.message},
                )

    return _to_shift_response(updated, location.iana_timezone)


@router.delete("/{shift_id}")
async def delete_shift(
    shift_id: str,
    request: Request,
    location_id: str = Query(...),
    current_user: CurrentUser = Depends(require_roles("admin", "manager")),
) -> dict[str, bool]:
    """Delete shift.
    
    Args:
        shift_id: Target shift identifier.
        request: Incoming FastAPI request context.
        location_id: Target location identifier.
        current_user: Authenticated user from dependency resolution.
    
    Returns:
        True when the operation succeeds, otherwise False.
    """
    if current_user.role == "manager":
        ensure_manager_location_access(current_user, location_id)

    shift = await prisma.shift.find_unique(where={"id": shift_id})
    if shift is None or shift.location_id != location_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shift not found.")

    async with prisma.tx() as tx:
        await tx.shift.update(where={"id": shift_id}, data={"status": "cancelled"})
        await create_audit_log(
            actor_id=current_user.id,
            action_type="shift.cancel",
            entity_type="shift",
            entity_id=shift_id,
            location_id=location_id,
            before_state={"status": shift.status},
            after_state={"status": "cancelled"},
            db=tx,
        )
    ws_manager = request.app.state.ws_manager
    await cancel_pending_swaps_for_shift(
        shift_id=shift_id,
        actor_id=current_user.id,
        reason="Swap request cancelled because the shift was cancelled.",
        ws_manager=ws_manager,
    )
    await ws_manager.emit_to_location(
        location_id,
        "schedule.updated",
        {
            "locationId": location_id,
            "shiftId": shift_id,
            "changes": {"status": "cancelled"},
        },
    )
    return {"deleted": True}


@router.post("/publish", response_model=PublishWeekResponse)
async def publish_week(
    payload: PublishWeekRequest,
    request: Request,
    location_id: str = Query(...),
    current_user: CurrentUser = Depends(require_roles("admin", "manager")),
) -> PublishWeekResponse:
    """Publish week.
    
    Args:
        payload: Validated request payload model.
        request: Incoming FastAPI request context.
        location_id: Target location identifier.
        current_user: Authenticated user from dependency resolution.
    
    Returns:
        Result typed as `PublishWeekResponse`.
    """
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
    notification_records: list[object] = []
    async with prisma.tx() as tx:
        for shift in shifts:
            await tx.shift.update(
                where={"id": shift.id},
                data={
                    "status": "published",
                    "published_at": now,
                    "edit_cutoff_utc": cutoff,
                },
            )
            await create_audit_log(
                actor_id=current_user.id,
                action_type="shift.publish",
                entity_type="shift",
                entity_id=shift.id,
                location_id=location_id,
                before_state={"status": shift.status},
                after_state={"status": "published", "edit_cutoff_utc": cutoff.isoformat()},
                db=tx,
            )

        shift_ids = [shift.id for shift in shifts]
        assignments = await tx.shiftassignment.find_many(
            where={"shift_id": {"in": shift_ids}, "status": "assigned"},
        )
        affected_user_ids = sorted({item.user_id for item in assignments})

        for user_id in affected_user_ids:
            record = await create_notification(
                user_id=user_id,
                notif_type="schedule.published",
                message=f"Schedule published for week of {payload.week_start.isoformat()}.",
                payload={"locationId": location_id, "weekStart": payload.week_start.isoformat()},
                db=tx,
                ws_manager=None,
            )
            notification_records.append(record)

    ws_manager = request.app.state.ws_manager
    event_payload = {
        "locationId": location_id,
        "weekStart": payload.week_start.isoformat(),
        "affectedUserIds": affected_user_ids,
    }
    await ws_manager.emit_to_location(location_id, "schedule.published", event_payload)
    if affected_user_ids:
        await ws_manager.emit_to_users(affected_user_ids, "schedule.published", event_payload)
        for record in notification_records:
            await ws_manager.emit_to_user(
                record.user_id,
                "notification.new",
                {"notificationId": record.id, "type": record.type, "message": record.message},
            )

    return PublishWeekResponse(
        published_shifts=len(shifts),
        edit_cutoff_utc=cutoff,
        notified_staff_count=len(affected_user_ids),
    )


@router.post("/locations/{location_id}/shifts/{shift_id}/unpublish", response_model=ShiftResponse)
async def unpublish_shift(
    location_id: str,
    shift_id: str,
    payload: UnpublishShiftRequest,
    request: Request,
    current_user: CurrentUser = Depends(require_roles("admin", "manager")),
) -> ShiftResponse:
    """Unpublish shift.
    
    Args:
        location_id: Target location identifier.
        shift_id: Target shift identifier.
        payload: Validated request payload model.
        request: Incoming FastAPI request context.
        current_user: Authenticated user from dependency resolution.
    
    Returns:
        Result typed as `ShiftResponse`.
    """
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

    async with prisma.tx() as tx:
        updated = await tx.shift.update(
            where={"id": shift_id},
            data={"status": "draft", "published_at": None},
            include={"required_skill": True, "location": True},
        )
        await create_audit_log(
            actor_id=current_user.id,
            action_type="shift.unpublish",
            entity_type="shift",
            entity_id=shift_id,
            location_id=location_id,
            before_state={"status": shift.status},
            after_state={"status": "draft"},
            reason=payload.override_reason,
            db=tx,
        )
    await request.app.state.ws_manager.emit_to_location(
        location_id,
        "schedule.updated",
        {
            "locationId": location_id,
            "shiftId": shift_id,
            "changes": {"status": "draft"},
        },
    )
    return _to_shift_response(updated, location.iana_timezone)
