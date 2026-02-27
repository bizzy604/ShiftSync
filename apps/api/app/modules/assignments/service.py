"""
MODULE: /apps/api/app/modules/assignments/service.py

FUNCTION:
    Implements assignments domain workflows and orchestration for constraints, conflicts, and locking.

DEPENDENCIES:
    - /apps/api/app/modules/assignments/router.py
    - /apps/api/app/modules/assignments/__init__.py

IMPORTANCE:
    Centralizing assignment orchestration here keeps route handlers thin while preserving
    constraint checks, transaction boundaries, and conflict semantics.
"""

from datetime import datetime, timezone
from typing import Any

from fastapi import Depends, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError

from app.api.deps import (
    CurrentUser,
    ensure_manager_location_access,
    get_current_user,
    require_roles,
)
from app.core.database import prisma
from app.schemas.assignment import (
    AssignmentCreateRequest,
    AssignmentResponse,
    AssignmentListResponse,
    ConstraintSuggestion,
    ConstraintDetail,
    AssignmentPreviewResponse,
    MyAssignmentResponse,
    MyAssignmentListResponse,
    AssignmentShiftInfo,
)
from app.services.constraint_engine import (
    AssignmentSnapshot,
    AvailabilityRule,
    ShiftSnapshot,
    UserSnapshot,
    evaluate_assignment,
)
from app.services.audit import create_audit_log
from app.services.notifications import create_notification




def _json_error(
    status_code: int,
    code: str,
    message: str,
    details: list[dict[str, Any]] | None = None,
    suggestions: list[dict[str, Any]] | None = None,
) -> JSONResponse:
    payload = {
        "error": {
            "code": code,
            "message": message,
        }
    }
    if details is not None:
        payload["error"]["details"] = details
    if suggestions is not None:
        payload["error"]["suggestions"] = suggestions
    return JSONResponse(status_code=status_code, content=payload)


def _to_assignment_response(assignment: object) -> AssignmentResponse:
    user_name = assignment.user.name if getattr(assignment, "user", None) is not None else "unknown"
    return AssignmentResponse(
        id=assignment.id,
        shift_id=assignment.shift_id,
        user_id=assignment.user_id,
        user_name=user_name,
        status=assignment.status,
        version=assignment.version,
        assigned_by=assignment.assigned_by,
        assigned_at=assignment.assigned_at,
    )


def _to_shift_snapshot(shift: object) -> ShiftSnapshot:
    if shift.location is None or shift.required_skill is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Shift context is incomplete.")
    return ShiftSnapshot(
        id=shift.id,
        location_id=shift.location_id,
        location_name=shift.location.name,
        location_timezone=shift.location.iana_timezone,
        required_skill_id=shift.required_skill_id,
        required_skill_name=shift.required_skill.name,
        start_utc=shift.start_utc,
        end_utc=shift.end_utc,
    )


def _to_user_snapshot(user: object) -> UserSnapshot:
    skills = {item.skill_id for item in user.user_skills}
    active_locations = {
        item.location_id for item in user.user_location_certifications if item.revoked_at is None
    }
    availability = [
        AvailabilityRule(
            avail_type=item.avail_type,
            day_of_week=item.day_of_week,
            specific_date=item.specific_date.date() if hasattr(item.specific_date, "date") else item.specific_date,
            start_clock=item.start_clock,
            end_clock=item.end_clock,
            is_available=item.is_available,
        )
        for item in user.availability
    ]
    return UserSnapshot(
        id=user.id,
        name=user.name,
        home_timezone=user.home_timezone,
        skills=skills,
        active_location_ids=active_locations,
        availability=availability,
        hourly_rate=float(user.hourly_rate or 0),
    )


async def _get_shift_with_access(shift_id: str, current_user: CurrentUser) -> object:
    shift = await prisma.shift.find_unique(
        where={"id": shift_id},
        include={"location": True, "required_skill": True},
    )
    if shift is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shift not found.")

    if current_user.role == "manager":
        ensure_manager_location_access(current_user, shift.location_id)
    elif current_user.role == "staff":
        assignment = await prisma.shiftassignment.find_first(
            where={"shift_id": shift_id, "user_id": current_user.id, "status": "assigned"},
        )
        if assignment is None:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")

    return shift


async def _load_existing_assignments(user_id: str, exclude_shift_id: str) -> list[AssignmentSnapshot]:
    assignments = await prisma.shiftassignment.find_many(
        where={"user_id": user_id, "status": "assigned"},
        include={"shift": True},
    )
    snapshots: list[AssignmentSnapshot] = []
    for assignment in assignments:
        if assignment.shift is None:
            continue
        if assignment.shift.status == "cancelled":
            continue
        if assignment.shift_id == exclude_shift_id:
            continue
        snapshots.append(
            AssignmentSnapshot(
                shift_id=assignment.shift_id,
                start_utc=assignment.shift.start_utc,
                end_utc=assignment.shift.end_utc,
            )
        )
    return snapshots


def _constraint_details(result: object) -> list[dict[str, Any]]:
    return [
        {
            "rule": item.rule,
            "description": item.description,
            "severity": item.severity,
        }
        for item in result
    ]


def _weekly_hours_warning(warnings: list[object]) -> object | None:
    for warning in warnings:
        if getattr(warning, "rule", None) == "WEEKLY_HOURS":
            return warning
    return None


async def _create_overtime_warning_notifications(
    *,
    tx: object,
    location_id: str,
    assigned_user: object,
    shift_id: str,
    projected_weekly_hours: float,
    warning_description: str,
) -> list[object]:
    manager_links = await tx.managerlocationassignment.find_many(where={"location_id": location_id})
    manager_ids = sorted({item.manager_id for item in manager_links})
    notifications: list[object] = []
    for manager_id in manager_ids:
        notif = await create_notification(
            user_id=manager_id,
            notif_type="overtime.warning",
            message=f"Overtime warning: {assigned_user.name} projected at {projected_weekly_hours:.2f}h.",
            payload={
                "userId": assigned_user.id,
                "shiftId": shift_id,
                "locationId": location_id,
                "projectedWeeklyHours": round(projected_weekly_hours, 2),
                "detail": warning_description,
            },
            db=tx,
            ws_manager=None,
        )
        notifications.append(notif)
    return notifications


async def _emit_assignment_conflict(
    request: Request,
    *,
    manager_user_id: str,
    shift_id: str,
    conflicting_user_id: str,
    message: str,
) -> None:
    ws_manager = getattr(request.app.state, "ws_manager", None)
    if ws_manager is None:
        return
    await ws_manager.emit_to_user(
        manager_user_id,
        "assignment.conflict",
        {
            "shiftId": shift_id,
            "conflictingUserId": conflicting_user_id,
            "message": message,
        },
    )


async def _compute_suggestions(shift_snapshot: ShiftSnapshot, target_user_id: str, limit: int = 5) -> list[ConstraintSuggestion]:
    skill_links = await prisma.userskill.find_many(where={"skill_id": shift_snapshot.required_skill_id})
    cert_links = await prisma.userlocationcertification.find_many(
        where={"location_id": shift_snapshot.location_id, "revoked_at": None},
    )

    skill_user_ids = {item.user_id for item in skill_links}
    cert_user_ids = {item.user_id for item in cert_links}
    candidate_ids = list(skill_user_ids.intersection(cert_user_ids))
    if not candidate_ids:
        return []

    candidates = await prisma.user.find_many(
        where={"id": {"in": candidate_ids}, "role": "staff", "is_active": True},
        include={
            "user_skills": True,
            "user_location_certifications": True,
            "availability": True,
        },
    )

    suggestions: list[ConstraintSuggestion] = []
    for candidate in candidates:
        if candidate.id == target_user_id:
            continue
        existing = await _load_existing_assignments(candidate.id, shift_snapshot.id)
        result = evaluate_assignment(shift_snapshot, _to_user_snapshot(candidate), existing)
        hard_blocks = [item for item in result.violations if item.severity == "HARD_BLOCK"]
        if hard_blocks:
            continue
        if result.requires_override:
            continue
        suggestions.append(
            ConstraintSuggestion(
                user_id=candidate.id,
                name=candidate.name,
                reason="Meets all requirements",
            )
        )
        if len(suggestions) >= limit:
            break
    return suggestions


async def list_my_assignments(
    current_user: CurrentUser = Depends(get_current_user),
) -> MyAssignmentListResponse:
    """List my assignments.
    
    Args:
        current_user: Authenticated user from dependency resolution.
    
    Returns:
        Result typed as `MyAssignmentListResponse`.
    """
    assignments = await prisma.shiftassignment.find_many(
        where={"user_id": current_user.id, "status": "assigned"},
        include={"shift": {"include": {"location": True, "required_skill": True}}},
        order={"shift": {"start_utc": "asc"}},
    )
    
    out = []
    for a in assignments:
        if not a.shift:
            continue
        
        from app.services.timezone_utils import format_local_iso
        tz = a.shift.location.iana_timezone
        
        shift_info = AssignmentShiftInfo(
            id=a.shift.id,
            location_id=a.shift.location_id,
            location_name=a.shift.location.name,
            shift_date=a.shift.shift_date,
            start_utc=a.shift.start_utc,
            end_utc=a.shift.end_utc,
            start_local=format_local_iso(a.shift.start_utc, tz),
            end_local=format_local_iso(a.shift.end_utc, tz),
            required_skill=a.shift.required_skill.name if a.shift.required_skill else "Staff",
        )
        
        out.append(MyAssignmentResponse(
            id=a.id,
            status=a.status,
            shift=shift_info
        ))
        
    return MyAssignmentListResponse(assignments=out)


async def list_assignments(
    shift_id: str = Query(...),
    current_user: CurrentUser = Depends(get_current_user),
) -> AssignmentListResponse:
    """List assignments.
    
    Args:
        shift_id: Target shift identifier.
        current_user: Authenticated user from dependency resolution.
    
    Returns:
        Result typed as `AssignmentListResponse`.
    """
    await _get_shift_with_access(shift_id, current_user)
    where = {"shift_id": shift_id}
    if current_user.role == "staff":
        where["user_id"] = current_user.id

    assignments = await prisma.shiftassignment.find_many(
        where=where,
        include={"user": True},
        order={"assigned_at": "asc"},
    )
    return AssignmentListResponse(assignments=[_to_assignment_response(item) for item in assignments])


async def preview_assignment(
    shift_id: str = Query(...),
    user_id: str = Query(...),
    current_user: CurrentUser = Depends(require_roles("admin", "manager")),
) -> AssignmentPreviewResponse:
    """Preview assignment.
    
    Args:
        shift_id: Target shift identifier.
        user_id: Target user identifier.
        current_user: Authenticated user from dependency resolution.
    
    Returns:
        Result typed as `AssignmentPreviewResponse`.
    """
    shift = await _get_shift_with_access(shift_id, current_user)

    user = await prisma.user.find_unique(
        where={"id": user_id},
        include={
            "user_skills": True,
            "user_location_certifications": True,
            "availability": True,
        },
    )
    if user is None or user.role != "staff" or not user.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Staff user not found.")

    shift_snapshot = _to_shift_snapshot(shift)
    existing = await _load_existing_assignments(user.id, shift_id)
    result = evaluate_assignment(shift_snapshot, _to_user_snapshot(user), existing)
    suggestions = await _compute_suggestions(shift_snapshot, target_user_id=user.id)

    return AssignmentPreviewResponse(
        user_id=user.id,
        user_name=user.name,
        valid=result.valid and not result.requires_override,
        violations=_constraint_details(result.violations),
        warnings=_constraint_details(result.warnings),
        requires_override=result.requires_override,
        projected_weekly_hours=result.projected_weekly_hours,
        projected_daily_hours=result.projected_daily_hours,
        projected_overtime_cost=result.projected_overtime_cost,
        suggestions=[item.model_dump() for item in suggestions],
    )


async def list_shift_suggestions(
    shift_id: str,
    limit: int = Query(10, ge=1, le=50),
    current_user: CurrentUser = Depends(require_roles("admin", "manager", "staff")),
) -> list[ConstraintSuggestion]:
    """List shift suggestions.
    
    Args:
        shift_id: Target shift identifier.
        limit: Maximum items to return per page.
        current_user: Authenticated user from dependency resolution.
    
    Returns:
        List of resulting items.
    """
    shift = await _get_shift_with_access(shift_id, current_user)
    shift_snapshot = _to_shift_snapshot(shift)
    suggestions = await _compute_suggestions(shift_snapshot, target_user_id="", limit=limit)
    return suggestions


async def create_assignment(
    payload: AssignmentCreateRequest,
    request: Request,
    shift_id: str = Query(...),
    current_user: CurrentUser = Depends(require_roles("admin", "manager")),
):
    """Create assignment.
    
    Args:
        payload: Validated request payload model.
        request: Incoming FastAPI request context.
        shift_id: Target shift identifier.
        current_user: Authenticated user from dependency resolution.
    """
    shift = await _get_shift_with_access(shift_id, current_user)
    if shift.status == "cancelled":
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Cannot assign to cancelled shift.")

    user = await prisma.user.find_unique(
        where={"id": payload.user_id},
        include={
            "user_skills": True,
            "user_location_certifications": True,
            "availability": True,
        },
    )
    if user is None or user.role != "staff" or not user.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Staff user not found.")

    async with request.app.state.assignment_locks.user_lock(user.id):
        existing_assignment = await prisma.shiftassignment.find_unique(
            where={"shift_id_user_id": {"shift_id": shift_id, "user_id": user.id}},
        )
        if existing_assignment:
            await _emit_assignment_conflict(
                request,
                manager_user_id=current_user.id,
                shift_id=shift_id,
                conflicting_user_id=user.id,
                message=f"{user.name} is already assigned to this shift.",
            )
            return _json_error(
                status_code=status.HTTP_409_CONFLICT,
                code="CONCURRENT_CONFLICT",
                message=f"{user.name} is already assigned to this shift.",
            )

        headcount_used = await prisma.shiftassignment.count(
            where={"shift_id": shift_id, "status": "assigned"},
        )
        if headcount_used >= shift.headcount_needed:
            await _emit_assignment_conflict(
                request,
                manager_user_id=current_user.id,
                shift_id=shift_id,
                conflicting_user_id=user.id,
                message=f"Shift headcount is full ({shift.headcount_needed}).",
            )
            return _json_error(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                code="HEADCOUNT_FULL",
                message=f"Shift headcount is full ({shift.headcount_needed}).",
            )

        shift_snapshot = _to_shift_snapshot(shift)
        existing = await _load_existing_assignments(user.id, shift_id)
        result = evaluate_assignment(shift_snapshot, _to_user_snapshot(user), existing)
        suggestions = await _compute_suggestions(shift_snapshot, target_user_id=user.id)
        suggestion_dicts = [item.model_dump() for item in suggestions]

        hard_violations = [item for item in result.violations if item.severity == "HARD_BLOCK"]
        if hard_violations:
            double_booking = next((item for item in hard_violations if item.rule == "DOUBLE_BOOKING"), None)
            if double_booking is not None:
                await _emit_assignment_conflict(
                    request,
                    manager_user_id=current_user.id,
                    shift_id=shift_id,
                    conflicting_user_id=user.id,
                    message=double_booking.description,
                )
                return _json_error(
                    status_code=status.HTTP_409_CONFLICT,
                    code="CONCURRENT_CONFLICT",
                    message=double_booking.description,
                    details=_constraint_details(result.violations) + _constraint_details(result.warnings),
                    suggestions=suggestion_dicts,
                )
            return _json_error(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                code="CONSTRAINT_VIOLATION",
                message=f"Cannot assign {user.name} to this shift.",
                details=_constraint_details(result.violations) + _constraint_details(result.warnings),
                suggestions=suggestion_dicts,
            )

        if result.requires_override and not payload.override_reason:
            return _json_error(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                code="OVERRIDE_REQUIRED",
                message="Assignment requires manager override reason.",
                details=_constraint_details(result.violations),
                suggestions=suggestion_dicts,
            )

        weekly_warning = _weekly_hours_warning(result.warnings)
        overtime_warning_text = weekly_warning.description if weekly_warning is not None else ""
        manager_overtime_notifs: list[object] = []

        try:
            async with prisma.tx() as tx:
                assignment = await tx.shiftassignment.create(
                    data={
                        "shift_id": shift_id,
                        "user_id": user.id,
                        "assigned_by": current_user.id,
                        "status": "assigned",
                        "version": 1,
                        "override_reason": payload.override_reason,
                    },
                    include={"user": True},
                )
                notif = await create_notification(
                    user_id=user.id,
                    notif_type="shift.assigned",
                    message=f"You have been assigned to a shift at {shift.location.name}.",
                    payload={"shiftId": shift_id, "locationId": shift.location_id},
                    db=tx,
                    ws_manager=None,
                )
                if overtime_warning_text:
                    manager_overtime_notifs = await _create_overtime_warning_notifications(
                        tx=tx,
                        location_id=shift.location_id,
                        assigned_user=user,
                        shift_id=shift_id,
                        projected_weekly_hours=result.projected_weekly_hours,
                        warning_description=overtime_warning_text,
                    )
                await create_audit_log(
                    actor_id=current_user.id,
                    action_type="shift.assign",
                    entity_type="assignment",
                    entity_id=assignment.id,
                    location_id=shift.location_id,
                    after_state={
                        "shift_id": assignment.shift_id,
                        "user_id": assignment.user_id,
                        "status": assignment.status,
                        "assigned_by": assignment.assigned_by,
                    },
                    reason=payload.override_reason,
                    db=tx,
                )
        except IntegrityError:
            await _emit_assignment_conflict(
                request,
                manager_user_id=current_user.id,
                shift_id=shift_id,
                conflicting_user_id=user.id,
                message=f"{user.name} was assigned in another concurrent request.",
            )
            return _json_error(
                status_code=status.HTTP_409_CONFLICT,
                code="CONCURRENT_CONFLICT",
                message=f"{user.name} was assigned in another concurrent request.",
            )

    ws_manager = request.app.state.ws_manager
    await ws_manager.emit_to_user(
        user.id,
        "assignment.changed",
        {
            "shiftId": shift_id,
            "userId": user.id,
            "status": "assigned",
            "changedBy": current_user.id,
        },
    )
    await ws_manager.emit_to_user(
        user.id,
        "notification.new",
        {"notificationId": notif.id, "type": notif.type, "message": notif.message},
    )
    for manager_notif in manager_overtime_notifs:
        await ws_manager.emit_to_user(
            manager_notif.user_id,
            "notification.new",
            {"notificationId": manager_notif.id, "type": manager_notif.type, "message": manager_notif.message},
        )
    return AssignmentResponse(**_to_assignment_response(assignment).model_dump())


async def delete_assignment(
    assignment_id: str,
    request: Request,
    shift_id: str = Query(...),
    current_user: CurrentUser = Depends(require_roles("admin", "manager")),
) -> dict[str, bool]:
    """Delete assignment.
    
    Args:
        assignment_id: Target assignment identifier.
        request: Incoming FastAPI request context.
        shift_id: Target shift identifier.
        current_user: Authenticated user from dependency resolution.
    
    Returns:
        True when the operation succeeds, otherwise False.
    """
    shift = await _get_shift_with_access(shift_id, current_user)
    if shift is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shift not found.")

    assignment = await prisma.shiftassignment.find_unique(where={"id": assignment_id}, include={"user": True})
    if assignment is None or assignment.shift_id != shift_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found.")

    async with prisma.tx() as tx:
        await tx.shiftassignment.delete(where={"id": assignment_id})
        notif = await create_notification(
            user_id=assignment.user_id,
            notif_type="shift.unassigned",
            message="You have been removed from a shift.",
            payload={"shiftId": shift_id, "locationId": shift.location_id},
            db=tx,
            ws_manager=None,
        )
        await create_audit_log(
            actor_id=current_user.id,
            action_type="shift.unassign",
            entity_type="assignment",
            entity_id=assignment.id,
            location_id=shift.location_id,
            before_state={
                "shift_id": assignment.shift_id,
                "user_id": assignment.user_id,
                "status": assignment.status,
                "assigned_by": assignment.assigned_by,
            },
            after_state={"status": "removed"},
            db=tx,
        )
    ws_manager = request.app.state.ws_manager
    await ws_manager.emit_to_user(
        assignment.user_id,
        "assignment.changed",
        {
            "shiftId": shift_id,
            "userId": assignment.user_id,
            "status": "removed",
            "changedBy": current_user.id,
        },
    )
    await ws_manager.emit_to_user(
        assignment.user_id,
        "notification.new",
        {"notificationId": notif.id, "type": notif.type, "message": notif.message},
    )
    return {"deleted": True}

