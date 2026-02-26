from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.api.deps import CurrentUser, ensure_manager_location_access, get_current_user, require_roles
from app.core.database import prisma
from app.schemas.swap import (
    AvailableDropListResponse,
    AvailableDropRequest,
    AvailableDropShift,
    DropCreateRequest,
    DropPickupRequest,
    SwapActionRequest,
    SwapCreateRequest,
    SwapRequestListResponse,
    SwapRequestResponse,
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
from app.services.timezone_utils import format_local_iso

router = APIRouter()
PENDING = {"OPEN", "PENDING_ACCEPTEE", "PENDING_MANAGER"}


def to_resp(row: object) -> SwapRequestResponse:
    return SwapRequestResponse(
        id=row.id,
        type=row.type,
        status=row.status,
        requester_assignment_id=row.requester_assignment_id,
        target_user_id=row.target_user_id,
        candidate_assignment_id=row.candidate_assignment_id,
        pickup_user_id=row.pickup_user_id,
        initiated_by=row.initiated_by,
        expires_at=row.expires_at,
        created_at=row.created_at,
        resolved_at=row.resolved_at,
        resolution_note=row.resolution_note,
    )


def user_snapshot(user: object) -> UserSnapshot:
    return UserSnapshot(
        id=user.id,
        name=user.name,
        home_timezone=user.home_timezone,
        skills={x.skill_id for x in user.user_skills},
        active_location_ids={x.location_id for x in user.user_location_certifications if x.revoked_at is None},
        availability=[
            AvailabilityRule(
                avail_type=x.avail_type,
                day_of_week=x.day_of_week,
                specific_date=x.specific_date.date() if hasattr(x.specific_date, "date") else x.specific_date,
                start_clock=x.start_clock,
                end_clock=x.end_clock,
                is_available=x.is_available,
            )
            for x in user.availability
        ],
        hourly_rate=float(user.hourly_rate or 0),
    )


def shift_snapshot(shift: object) -> ShiftSnapshot:
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


async def existing_assignments(user_id: str, exclude_shift_id: str) -> list[AssignmentSnapshot]:
    rows = await prisma.shiftassignment.find_many(
        where={"user_id": user_id, "status": "assigned"},
        include={"shift": True},
    )
    return [
        AssignmentSnapshot(shift_id=r.shift_id, start_utc=r.shift.start_utc, end_utc=r.shift.end_utc)
        for r in rows
        if r.shift is not None and r.shift_id != exclude_shift_id
    ]


async def enforce_pending_limit(user_id: str) -> None:
    count = await prisma.swaprequest.count(where={"initiated_by": user_id, "status": {"in": list(PENDING)}})
    if count >= 3:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "MAX_PENDING_REQUESTS", "message": "You already have 3 pending swap/drop requests."},
        )


async def manager_notify(location_id: str, message: str, payload: dict, db: object | None = None) -> list[object]:
    client = db or prisma
    links = await client.managerlocationassignment.find_many(where={"location_id": location_id})
    notifications = []
    for link in links:
        notif = await create_notification(
            user_id=link.manager_id,
            notif_type="swap.manager_action_required",
            message=message,
            payload=payload,
            db=client,
            ws_manager=None,
        )
        notifications.append(notif)
    return notifications


async def emit_notifications(ws_manager: object, notifications: list[object]) -> None:
    for notif in notifications:
        await ws_manager.emit_to_user(
            notif.user_id,
            "notification.new",
            {
                "notificationId": notif.id,
                "type": notif.type,
                "message": notif.message,
            },
        )


@router.get("/swap-requests", response_model=SwapRequestListResponse)
async def list_swap_requests(current_user: CurrentUser = Depends(get_current_user)) -> SwapRequestListResponse:
    rows = await prisma.swaprequest.find_many(
        include={"requester_assignment": {"include": {"shift": True}}},
        order={"created_at": "desc"},
    )
    out = []
    for row in rows:
        if current_user.role == "admin":
            out.append(row)
        elif current_user.id in {row.initiated_by, row.target_user_id, row.pickup_user_id}:
            out.append(row)
        elif current_user.role == "manager" and row.requester_assignment and row.requester_assignment.shift:
            if row.requester_assignment.shift.location_id in current_user.location_ids:
                out.append(row)
    return SwapRequestListResponse(requests=[to_resp(x) for x in out])


@router.get("/swap-requests/{request_id}", response_model=SwapRequestResponse)
async def get_swap_request(request_id: str, current_user: CurrentUser = Depends(get_current_user)) -> SwapRequestResponse:
    row = await prisma.swaprequest.find_unique(
        where={"id": request_id},
        include={"requester_assignment": {"include": {"shift": True}}},
    )
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Request not found.")
    allowed = current_user.role == "admin" or current_user.id in {row.initiated_by, row.target_user_id, row.pickup_user_id}
    if not allowed and current_user.role == "manager" and row.requester_assignment and row.requester_assignment.shift:
        allowed = row.requester_assignment.shift.location_id in current_user.location_ids
    if not allowed:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")
    return to_resp(row)


@router.post("/swap-requests", response_model=SwapRequestResponse)
async def create_swap_request(payload: SwapCreateRequest, request: Request, current_user: CurrentUser = Depends(require_roles("staff"))) -> SwapRequestResponse:
    await enforce_pending_limit(current_user.id)
    a = await prisma.shiftassignment.find_unique(where={"id": payload.my_assignment_id}, include={"shift": True})
    if a is None or a.user_id != current_user.id or a.status != "assigned":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found.")
    if a.shift is None or a.shift.start_utc <= datetime.now(tz=timezone.utc):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Cannot swap a started shift.")
    target = await prisma.user.find_unique(where={"id": payload.target_user_id})
    if target is None or target.role != "staff" or not target.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target staff not found.")
    async with prisma.tx() as tx:
        row = await tx.swaprequest.create(
            data={
                "type": "swap",
                "requester_assignment_id": payload.my_assignment_id,
                "target_user_id": payload.target_user_id,
                "candidate_assignment_id": payload.target_assignment_id,
                "status": "PENDING_ACCEPTEE",
                "initiated_by": current_user.id,
            }
        )
        target_notification = await create_notification(
            user_id=target.id,
            notif_type="swap.requested",
            message="You have a swap request.",
            payload={"swapRequestId": row.id},
            db=tx,
            ws_manager=None,
        )
        await create_audit_log(
            actor_id=current_user.id,
            action_type="swap.create",
            entity_type="swap_request",
            entity_id=row.id,
            location_id=a.shift.location_id if a.shift else None,
            after_state={"type": row.type, "status": row.status},
            db=tx,
        )
    ws = request.app.state.ws_manager
    await emit_notifications(ws, [target_notification])
    await ws.emit_to_users([current_user.id, target.id], "swap.status_changed", {"swapRequestId": row.id, "newStatus": "PENDING_ACCEPTEE"})
    return to_resp(row)


@router.put("/swap-requests/{request_id}/accept", response_model=SwapRequestResponse)
async def accept_swap(request_id: str, body: SwapActionRequest, request: Request, current_user: CurrentUser = Depends(require_roles("staff"))) -> SwapRequestResponse:
    row = await prisma.swaprequest.find_unique(where={"id": request_id}, include={"requester_assignment": {"include": {"shift": True}}})
    if row is None or row.type != "swap":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Swap request not found.")
    if row.target_user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only target staff can accept.")
    if row.status != "PENDING_ACCEPTEE":
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Swap not awaiting acceptee.")
    manager_notifications: list[object] = []
    async with prisma.tx() as tx:
        row = await tx.swaprequest.update(where={"id": row.id}, data={"status": "PENDING_MANAGER", "resolution_note": body.note, "version": row.version + 1}, include={"requester_assignment": {"include": {"shift": True}}})
        await create_audit_log(
            actor_id=current_user.id,
            action_type="swap.accept",
            entity_type="swap_request",
            entity_id=row.id,
            location_id=row.requester_assignment.shift.location_id if row.requester_assignment and row.requester_assignment.shift else None,
            before_state={"status": "PENDING_ACCEPTEE"},
            after_state={"status": "PENDING_MANAGER"},
            reason=body.note,
            db=tx,
        )
        if row.requester_assignment and row.requester_assignment.shift:
            manager_notifications = await manager_notify(
                row.requester_assignment.shift.location_id,
                "Swap needs manager approval.",
                {"swapRequestId": row.id},
                db=tx,
            )
    ws = request.app.state.ws_manager
    await emit_notifications(ws, manager_notifications)
    await ws.emit_to_users([row.initiated_by, current_user.id], "swap.status_changed", {"swapRequestId": row.id, "newStatus": "PENDING_MANAGER"})
    return to_resp(row)


@router.put("/swap-requests/{request_id}/reject", response_model=SwapRequestResponse)
async def reject_swap(request_id: str, body: SwapActionRequest, request: Request, current_user: CurrentUser = Depends(require_roles("staff"))) -> SwapRequestResponse:
    row = await prisma.swaprequest.find_unique(where={"id": request_id})
    if row is None or row.type != "swap":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Swap request not found.")
    if row.target_user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only target staff can reject.")
    initiator_notification = None
    async with prisma.tx() as tx:
        row = await tx.swaprequest.update(where={"id": row.id}, data={"status": "REJECTED", "resolved_at": datetime.now(tz=timezone.utc), "resolved_by": current_user.id, "resolution_note": body.note, "version": row.version + 1})
        initiator_notification = await create_notification(
            user_id=row.initiated_by,
            notif_type="swap.rejected",
            message="Your swap request was rejected.",
            payload={"swapRequestId": row.id},
            db=tx,
            ws_manager=None,
        )
        await create_audit_log(
            actor_id=current_user.id,
            action_type="swap.reject",
            entity_type="swap_request",
            entity_id=row.id,
            before_state={"status": "PENDING_ACCEPTEE"},
            after_state={"status": "REJECTED"},
            reason=body.note,
            db=tx,
        )
    ws = request.app.state.ws_manager
    await emit_notifications(ws, [initiator_notification])
    await ws.emit_to_users([row.initiated_by, current_user.id], "swap.status_changed", {"swapRequestId": row.id, "newStatus": "REJECTED"})
    return to_resp(row)


@router.put("/swap-requests/{request_id}/cancel", response_model=SwapRequestResponse)
async def cancel_swap(request_id: str, body: SwapActionRequest, request: Request, current_user: CurrentUser = Depends(get_current_user)) -> SwapRequestResponse:
    row = await prisma.swaprequest.find_unique(where={"id": request_id})
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Request not found.")
    if current_user.role != "admin" and row.initiated_by != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only initiator can cancel.")
    if row.status not in PENDING:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Request cannot be cancelled.")
    async with prisma.tx() as tx:
        row = await tx.swaprequest.update(where={"id": row.id}, data={"status": "CANCELLED", "resolved_at": datetime.now(tz=timezone.utc), "resolved_by": current_user.id, "resolution_note": body.note, "version": row.version + 1})
        await create_audit_log(
            actor_id=current_user.id,
            action_type="swap.cancel",
            entity_type="swap_request",
            entity_id=row.id,
            before_state={"status": "PENDING"},
            after_state={"status": "CANCELLED"},
            reason=body.note,
            db=tx,
        )
    ws = request.app.state.ws_manager
    recipients = [row.initiated_by] + ([row.target_user_id] if row.target_user_id else []) + ([row.pickup_user_id] if row.pickup_user_id else [])
    await ws.emit_to_users(recipients, "swap.status_changed", {"swapRequestId": row.id, "newStatus": "CANCELLED"})
    return to_resp(row)


async def approve_transfer(row: object, actor: CurrentUser, note: str | None, request: Request, drop: bool) -> tuple[object, list[object], str]:
    a = await prisma.shiftassignment.find_unique(where={"id": row.requester_assignment_id}, include={"shift": {"include": {"location": True, "required_skill": True}}})
    if a is None or a.shift is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Requester assignment not found.")
    target_user_id = row.pickup_user_id if drop else row.target_user_id
    if target_user_id is None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Target user missing.")
    u = await prisma.user.find_unique(where={"id": target_user_id}, include={"user_skills": True, "user_location_certifications": True, "availability": True})
    if u is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target user not found.")
    result = evaluate_assignment(
        shift_snapshot(a.shift),
        user_snapshot(u),
        await existing_assignments(u.id, a.shift_id),
    )
    if any(v.severity == "HARD_BLOCK" for v in result.violations):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Target no longer qualifies.")
    if result.requires_override and not note:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Override note is required.")
    async with prisma.tx() as tx:
        await tx.shiftassignment.update(
            where={"id": a.id},
            data={"user_id": u.id, "assigned_by": actor.id, "override_reason": note, "version": a.version + 1},
        )
        row = await tx.swaprequest.update(
            where={"id": row.id},
            data={"status": "APPROVED", "resolved_at": datetime.now(tz=timezone.utc), "resolved_by": actor.id, "resolution_note": note, "version": row.version + 1},
        )
        await create_audit_log(
            actor_id=actor.id,
            action_type="drop.approve" if drop else "swap.approve",
            entity_type="swap_request",
            entity_id=row.id,
            location_id=a.shift.location_id,
            before_state={"status": "PENDING_MANAGER"},
            after_state={"status": "APPROVED", "new_user_id": u.id},
            reason=note,
            db=tx,
        )
        notif_1 = await create_notification(
            user_id=row.initiated_by,
            notif_type="swap.approved" if not drop else "drop.approved",
            message="Request approved.",
            payload={"requestId": row.id},
            db=tx,
            ws_manager=None,
        )
        notif_2 = await create_notification(
            user_id=u.id,
            notif_type="swap.approved" if not drop else "drop.approved",
            message="You are assigned to the shift.",
            payload={"requestId": row.id},
            db=tx,
            ws_manager=None,
        )

    ws = request.app.state.ws_manager
    await ws.emit_to_user(
        row.initiated_by,
        "notification.new",
        {"notificationId": notif_1.id, "type": notif_1.type, "message": notif_1.message},
    )
    await ws.emit_to_user(
        u.id,
        "notification.new",
        {"notificationId": notif_2.id, "type": notif_2.type, "message": notif_2.message},
    )
    await ws.emit_to_users([row.initiated_by, u.id], "swap.status_changed", {"swapRequestId": row.id, "newStatus": "APPROVED"})
    await ws.emit_to_user(u.id, "assignment.changed", {"shiftId": a.shift_id, "userId": u.id, "status": "assigned", "changedBy": actor.id})
    return row, [notif_1, notif_2], a.shift.location_id


@router.put("/swap-requests/{request_id}/approve", response_model=SwapRequestResponse)
async def approve_swap_like(request_id: str, body: SwapActionRequest, request: Request, current_user: CurrentUser = Depends(require_roles("admin", "manager"))) -> SwapRequestResponse:
    row = await prisma.swaprequest.find_unique(where={"id": request_id}, include={"requester_assignment": {"include": {"shift": True}}})
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Request not found.")
    if row.status != "PENDING_MANAGER":
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Request is not pending manager.")
    if current_user.role == "manager" and row.requester_assignment and row.requester_assignment.shift:
        ensure_manager_location_access(current_user, row.requester_assignment.shift.location_id)
    row, _, _ = await approve_transfer(row, current_user, body.note, request, drop=row.type == "drop")
    return to_resp(row)


@router.put("/swap-requests/{request_id}/decline", response_model=SwapRequestResponse)
async def decline_swap_like(request_id: str, body: SwapActionRequest, request: Request, current_user: CurrentUser = Depends(require_roles("admin", "manager"))) -> SwapRequestResponse:
    row = await prisma.swaprequest.find_unique(where={"id": request_id}, include={"requester_assignment": {"include": {"shift": True}}})
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Request not found.")
    if row.status not in {"OPEN", "PENDING_MANAGER"}:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Request cannot be declined.")
    if current_user.role == "manager" and row.requester_assignment and row.requester_assignment.shift:
        ensure_manager_location_access(current_user, row.requester_assignment.shift.location_id)
    previous_status = row.status
    location_id = row.requester_assignment.shift.location_id if row.requester_assignment and row.requester_assignment.shift else None
    initiator_notif_type = "drop.rejected" if row.type == "drop" else "swap.rejected"
    initiator_notification = None
    async with prisma.tx() as tx:
        row = await tx.swaprequest.update(where={"id": row.id}, data={"status": "REJECTED", "resolved_at": datetime.now(tz=timezone.utc), "resolved_by": current_user.id, "resolution_note": body.note, "version": row.version + 1})
        initiator_notification = await create_notification(
            user_id=row.initiated_by,
            notif_type=initiator_notif_type,
            message="Request declined.",
            payload={"requestId": row.id},
            db=tx,
            ws_manager=None,
        )
        await create_audit_log(
            actor_id=current_user.id,
            action_type="drop.decline" if row.type == "drop" else "swap.decline",
            entity_type="swap_request",
            entity_id=row.id,
            location_id=location_id,
            before_state={"status": previous_status},
            after_state={"status": "REJECTED"},
            reason=body.note,
            db=tx,
        )
    ws = request.app.state.ws_manager
    await emit_notifications(ws, [initiator_notification])
    await ws.emit_to_users([row.initiated_by] + ([row.pickup_user_id] if row.pickup_user_id else []), "swap.status_changed", {"swapRequestId": row.id, "newStatus": "REJECTED"})
    return to_resp(row)


@router.post("/drop-requests", response_model=SwapRequestResponse)
async def create_drop(payload: DropCreateRequest, request: Request, current_user: CurrentUser = Depends(require_roles("staff"))) -> SwapRequestResponse:
    await enforce_pending_limit(current_user.id)
    a = await prisma.shiftassignment.find_unique(where={"id": payload.assignment_id}, include={"shift": True})
    if a is None or a.user_id != current_user.id or a.status != "assigned":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found.")
    if a.shift is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shift not found.")
    expires_at = a.shift.start_utc - timedelta(hours=24)
    if expires_at <= datetime.now(tz=timezone.utc):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Drop already within expiry window.")
    manager_notifications: list[object] = []
    async with prisma.tx() as tx:
        row = await tx.swaprequest.create(data={"type": "drop", "requester_assignment_id": a.id, "status": "OPEN", "initiated_by": current_user.id, "expires_at": expires_at})
        await create_audit_log(
            actor_id=current_user.id,
            action_type="drop.create",
            entity_type="swap_request",
            entity_id=row.id,
            location_id=a.shift.location_id,
            after_state={"type": "drop", "status": "OPEN", "expires_at": expires_at.isoformat()},
            db=tx,
        )
        manager_notifications = await manager_notify(
            a.shift.location_id,
            "A drop request was opened.",
            {"dropRequestId": row.id},
            db=tx,
        )
    await emit_notifications(request.app.state.ws_manager, manager_notifications)
    return to_resp(row)


@router.get("/drop-requests/available", response_model=AvailableDropListResponse)
async def available_drops(current_user: CurrentUser = Depends(require_roles("staff"))) -> AvailableDropListResponse:
    now = datetime.now(tz=timezone.utc)
    expired = await prisma.swaprequest.find_many(where={"type": "drop", "status": {"in": ["OPEN", "PENDING_MANAGER"]}, "expires_at": {"lt": now}})
    for x in expired:
        await prisma.swaprequest.update(where={"id": x.id}, data={"status": "EXPIRED", "resolved_at": now, "resolution_note": "Expired."})
    rows = await prisma.swaprequest.find_many(
        where={"type": "drop", "status": "OPEN", "expires_at": {"gt": now}, "initiated_by": {"not": current_user.id}},
        include={"requester_assignment": {"include": {"shift": {"include": {"location": True, "required_skill": True}}, "user": True}}},
    )
    u = await prisma.user.find_unique(where={"id": current_user.id}, include={"user_skills": True, "user_location_certifications": True, "availability": True})
    if u is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Staff user not found.")
    out = []
    for row in rows:
        a = row.requester_assignment
        if a is None or a.shift is None or a.user is None:
            continue
        result = evaluate_assignment(shift_snapshot(a.shift), user_snapshot(u), await existing_assignments(u.id, a.shift.id))
        if any(v.severity == "HARD_BLOCK" for v in result.violations) or result.requires_override:
            continue
        shift = a.shift
        out.append(
            AvailableDropRequest(
                drop_request_id=row.id,
                shift=AvailableDropShift(
                    id=shift.id,
                    date=shift.shift_date.date().isoformat() if hasattr(shift.shift_date, "date") else str(shift.shift_date),
                    start_local=format_local_iso(shift.start_utc, shift.location.iana_timezone),
                    end_local=format_local_iso(shift.end_utc, shift.location.iana_timezone),
                    location={"name": shift.location.name},
                    required_skill=shift.required_skill.name,
                ),
                original_staff={"name": a.user.name},
                expires_at=row.expires_at,
            )
        )
    return AvailableDropListResponse(available=out)


@router.post("/drop-requests/{request_id}/pickup", response_model=SwapRequestResponse)
async def pickup_drop(request_id: str, body: DropPickupRequest, request: Request, current_user: CurrentUser = Depends(require_roles("staff"))) -> SwapRequestResponse:
    row = await prisma.swaprequest.find_unique(where={"id": request_id}, include={"requester_assignment": {"include": {"shift": {"include": {"location": True, "required_skill": True}}}}})
    if row is None or row.type != "drop":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Drop request not found.")
    if row.status != "OPEN":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Drop request not open.")
    if row.expires_at and row.expires_at <= datetime.now(tz=timezone.utc):
        await prisma.swaprequest.update(where={"id": row.id}, data={"status": "EXPIRED", "resolved_at": datetime.now(tz=timezone.utc), "resolution_note": "Expired."})
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Drop request expired.")
    a = row.requester_assignment
    if a is None or a.shift is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found.")
    if a.user_id == current_user.id:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Cannot pickup own drop.")
    u = await prisma.user.find_unique(where={"id": current_user.id}, include={"user_skills": True, "user_location_certifications": True, "availability": True})
    if u is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Staff user not found.")
    result = evaluate_assignment(shift_snapshot(a.shift), user_snapshot(u), await existing_assignments(u.id, a.shift_id))
    if any(v.severity == "HARD_BLOCK" for v in result.violations):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="You do not qualify for this shift.")
    manager_notifications: list[object] = []
    initiator_notification = None
    async with prisma.tx() as tx:
        row = await tx.swaprequest.update(where={"id": row.id}, data={"status": "PENDING_MANAGER", "pickup_user_id": current_user.id, "resolution_note": body.note, "version": row.version + 1})
        initiator_notification = await create_notification(
            user_id=row.initiated_by,
            notif_type="drop.picked_up",
            message="Your dropped shift has been picked up.",
            payload={"dropRequestId": row.id},
            db=tx,
            ws_manager=None,
        )
        await create_audit_log(
            actor_id=current_user.id,
            action_type="drop.pickup",
            entity_type="swap_request",
            entity_id=row.id,
            location_id=a.shift.location_id,
            before_state={"status": "OPEN"},
            after_state={"status": "PENDING_MANAGER", "pickup_user_id": current_user.id},
            reason=body.note,
            db=tx,
        )
        manager_notifications = await manager_notify(
            a.shift.location_id,
            "Drop pickup pending manager approval.",
            {"dropRequestId": row.id},
            db=tx,
        )
    ws = request.app.state.ws_manager
    await emit_notifications(ws, manager_notifications + [initiator_notification])
    await ws.emit_to_users([row.initiated_by, current_user.id], "swap.status_changed", {"swapRequestId": row.id, "newStatus": "PENDING_MANAGER"})
    return to_resp(row)


@router.put("/drop-requests/{request_id}/approve", response_model=SwapRequestResponse)
async def approve_drop(request_id: str, body: SwapActionRequest, request: Request, current_user: CurrentUser = Depends(require_roles("admin", "manager"))) -> SwapRequestResponse:
    row = await prisma.swaprequest.find_unique(where={"id": request_id}, include={"requester_assignment": {"include": {"shift": True}}})
    if row is None or row.type != "drop":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Drop request not found.")
    if row.status != "PENDING_MANAGER":
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Drop is not pending manager.")
    if current_user.role == "manager" and row.requester_assignment and row.requester_assignment.shift:
        ensure_manager_location_access(current_user, row.requester_assignment.shift.location_id)
    row, _, _ = await approve_transfer(row, current_user, body.note, request, drop=True)
    return to_resp(row)


@router.put("/drop-requests/{request_id}/decline", response_model=SwapRequestResponse)
async def decline_drop(request_id: str, body: SwapActionRequest, request: Request, current_user: CurrentUser = Depends(require_roles("admin", "manager"))) -> SwapRequestResponse:
    row = await prisma.swaprequest.find_unique(where={"id": request_id}, include={"requester_assignment": {"include": {"shift": True}}})
    if row is None or row.type != "drop":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Drop request not found.")
    if row.status not in {"OPEN", "PENDING_MANAGER"}:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Drop cannot be declined.")
    if current_user.role == "manager" and row.requester_assignment and row.requester_assignment.shift:
        ensure_manager_location_access(current_user, row.requester_assignment.shift.location_id)
    previous_status = row.status
    location_id = row.requester_assignment.shift.location_id if row.requester_assignment and row.requester_assignment.shift else None
    initiator_notification = None
    pickup_notification = None
    async with prisma.tx() as tx:
        row = await tx.swaprequest.update(where={"id": row.id}, data={"status": "REJECTED", "resolved_at": datetime.now(tz=timezone.utc), "resolved_by": current_user.id, "resolution_note": body.note, "version": row.version + 1})
        initiator_notification = await create_notification(
            user_id=row.initiated_by,
            notif_type="drop.rejected",
            message="Your drop request was declined.",
            payload={"dropRequestId": row.id},
            db=tx,
            ws_manager=None,
        )
        if row.pickup_user_id:
            pickup_notification = await create_notification(
                user_id=row.pickup_user_id,
                notif_type="drop.rejected",
                message="Your drop pickup was declined.",
                payload={"dropRequestId": row.id},
                db=tx,
                ws_manager=None,
            )
        await create_audit_log(
            actor_id=current_user.id,
            action_type="drop.decline",
            entity_type="swap_request",
            entity_id=row.id,
            location_id=location_id,
            before_state={"status": previous_status},
            after_state={"status": "REJECTED"},
            reason=body.note,
            db=tx,
        )
    ws = request.app.state.ws_manager
    notifications = [initiator_notification] + ([pickup_notification] if pickup_notification else [])
    await emit_notifications(ws, notifications)
    await ws.emit_to_users([row.initiated_by] + ([row.pickup_user_id] if row.pickup_user_id else []), "swap.status_changed", {"swapRequestId": row.id, "newStatus": "REJECTED"})
    return to_resp(row)
