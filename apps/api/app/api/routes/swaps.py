from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm.exc import DetachedInstanceError

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
from app.services.drop_expiry import expire_drop_request, expire_due_drop_requests
from app.services.notifications import create_notification
from app.services.timezone_utils import format_local_iso

router = APIRouter()
PENDING = {"OPEN", "PENDING_ACCEPTEE", "PENDING_MANAGER"}
SWAP_RESPONSE_INCLUDE = {
    "requester_assignment": {
        "include": {
            "shift": {"include": {"location": True, "required_skill": True}},
            "user": True,
        }
    },
    "target_user": True,
    "pickup_user": True,
}


def _safe_getattr(obj: object, attr: str):
    try:
        return getattr(obj, attr)
    except DetachedInstanceError:
        return None


def to_resp(row: object) -> SwapRequestResponse:
    requester_name = None
    target_name = None
    pickup_name = None
    shift_id = None
    shift_date = None
    shift_time = None
    shift_label = None

    requester_assignment = _safe_getattr(row, "requester_assignment")
    if requester_assignment:
        a = requester_assignment
        user = _safe_getattr(a, "user")
        if user:
            requester_name = user.name
        shift = _safe_getattr(a, "shift")
        if shift:
            s = shift
            shift_id = s.id
            shift_date = s.shift_date.isoformat() if hasattr(s.shift_date, "isoformat") else str(s.shift_date)
            # Simple time formatting
            location = _safe_getattr(s, "location")
            start_local = format_local_iso(s.start_utc, location.iana_timezone) if location else s.start_utc.isoformat()
            end_local = format_local_iso(s.end_utc, location.iana_timezone) if location else s.end_utc.isoformat()
            
            # Extract time part for UI convenience
            shift_time = f"{start_local[11:16]} – {end_local[11:16]}"
            required_skill = _safe_getattr(s, "required_skill")
            if required_skill:
                shift_label = required_skill.name

    target_user = _safe_getattr(row, "target_user")
    if target_user:
        target_name = target_user.name
    
    pickup_user = _safe_getattr(row, "pickup_user")
    if pickup_user:
        pickup_name = pickup_user.name

    return SwapRequestResponse(
        id=row.id,
        type=row.type,
        status=row.status,
        requester_assignment_id=row.requester_assignment_id,
        shift_id=shift_id,
        requester_name=requester_name,
        target_user_id=row.target_user_id,
        target_name=target_name,
        candidate_assignment_id=row.candidate_assignment_id,
        pickup_user_id=row.pickup_user_id,
        pickup_name=pickup_name,
        initiated_by=row.initiated_by,
        expires_at=row.expires_at,
        created_at=row.created_at,
        resolved_at=row.resolved_at,
        resolution_note=row.resolution_note,
        shift_date=shift_date,
        shift_time=shift_time,
        shift_label=shift_label,
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


async def existing_assignments(user_id: str, exclude_shift_ids: set[str] | None = None) -> list[AssignmentSnapshot]:
    excluded = exclude_shift_ids or set()
    rows = await prisma.shiftassignment.find_many(
        where={"user_id": user_id, "status": "assigned"},
        include={"shift": True},
    )
    return [
        AssignmentSnapshot(shift_id=r.shift_id, start_utc=r.shift.start_utc, end_utc=r.shift.end_utc)
        for r in rows
        if r.shift is not None and r.shift_id not in excluded
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


async def _load_swap_for_response(request_id: str) -> object:
    row = await prisma.swaprequest.find_unique(where={"id": request_id}, include=SWAP_RESPONSE_INCLUDE)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Request not found.")
    return row


@router.get("", response_model=SwapRequestListResponse)
async def list_swap_requests(current_user: CurrentUser = Depends(get_current_user)) -> SwapRequestListResponse:
    rows = await prisma.swaprequest.find_many(
        include={
            "requester_assignment": {
                "include": {
                    "shift": {"include": {"location": True, "required_skill": True}},
                    "user": True
                }
            },
            "target_user": True,
            "pickup_user": True,
        },
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


@router.get("/{request_id}", response_model=SwapRequestResponse)
async def get_swap_request(request_id: str, current_user: CurrentUser = Depends(get_current_user)) -> SwapRequestResponse:
    row = await prisma.swaprequest.find_unique(
        where={"id": request_id},
        include={
            "requester_assignment": {
                "include": {
                    "shift": {"include": {"location": True, "required_skill": True}},
                    "user": True
                }
            },
            "target_user": True,
            "pickup_user": True,
        },
    )
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Request not found.")
    allowed = current_user.role == "admin" or current_user.id in {row.initiated_by, row.target_user_id, row.pickup_user_id}
    if not allowed and current_user.role == "manager" and row.requester_assignment and row.requester_assignment.shift:
        allowed = row.requester_assignment.shift.location_id in current_user.location_ids
    if not allowed:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")
    return to_resp(row)


@router.post("", response_model=SwapRequestResponse)
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
    candidate_assignment_id = None
    if payload.target_assignment_id:
        candidate_assignment = await prisma.shiftassignment.find_unique(
            where={"id": payload.target_assignment_id},
            include={"shift": True},
        )
        if (
            candidate_assignment is None
            or candidate_assignment.user_id != target.id
            or candidate_assignment.status != "assigned"
        ):
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Target assignment is invalid.")
        if candidate_assignment.shift is None or candidate_assignment.shift.start_utc <= datetime.now(tz=timezone.utc):
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Target assignment shift has already started.")
        if candidate_assignment.id == a.id:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Cannot swap the same assignment.")
        candidate_assignment_id = candidate_assignment.id
    async with prisma.tx() as tx:
        row = await tx.swaprequest.create(
            data={
                "type": "swap",
                "requester_assignment_id": payload.my_assignment_id,
                "target_user_id": payload.target_user_id,
                "candidate_assignment_id": candidate_assignment_id,
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


@router.post("/{request_id}/accept", response_model=SwapRequestResponse)
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


@router.post("/{request_id}/reject", response_model=SwapRequestResponse)
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


@router.post("/{request_id}/cancel", response_model=SwapRequestResponse)
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
    now = datetime.now(tz=timezone.utc)
    is_legacy_single_transfer = False
    requester_assignment = await prisma.shiftassignment.find_unique(
        where={"id": row.requester_assignment_id},
        include={"user": True, "shift": {"include": {"location": True, "required_skill": True}}},
    )
    if requester_assignment is None or requester_assignment.shift is None or requester_assignment.user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Requester assignment not found.")
    if requester_assignment.status not in {"assigned", "swap_pending"}:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Requester assignment is no longer assigned.")
    if requester_assignment.shift.start_utc <= now:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Cannot approve after shift start.")

    target_user_id = row.pickup_user_id if drop else row.target_user_id
    if target_user_id is None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Target user missing.")
    target_user = await prisma.user.find_unique(
        where={"id": target_user_id},
        include={"user_skills": True, "user_location_certifications": True, "availability": True},
    )
    if target_user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target user not found.")

    candidate_assignment = None
    if not drop:
        if not row.candidate_assignment_id:
            is_legacy_single_transfer = True
        else:
            candidate_assignment = await prisma.shiftassignment.find_unique(
                where={"id": row.candidate_assignment_id},
                include={"user": True, "shift": {"include": {"location": True, "required_skill": True}}},
            )
            if (
                candidate_assignment is None
                or candidate_assignment.user is None
                or candidate_assignment.shift is None
                or candidate_assignment.status not in {"assigned", "swap_pending"}
            ):
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Candidate assignment is no longer valid.")
            if candidate_assignment.user_id != target_user_id:
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Candidate assignment no longer belongs to target user.")
            if candidate_assignment.shift.start_utc <= now:
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Cannot approve after shift start.")

    target_excludes = {requester_assignment.shift_id}
    if candidate_assignment is not None:
        target_excludes.add(candidate_assignment.shift_id)
    target_result = evaluate_assignment(
        shift_snapshot(requester_assignment.shift),
        user_snapshot(target_user),
        await existing_assignments(target_user.id, target_excludes),
    )
    target_hard_blocks = [v for v in target_result.violations if v.severity == "HARD_BLOCK"]
    if target_hard_blocks:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Target no longer qualifies: {target_hard_blocks[0].description}",
        )
    if target_result.requires_override and not note:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Override note is required.")

    requester_result = None
    if candidate_assignment is not None:
        requester_profile = await prisma.user.find_unique(
            where={"id": requester_assignment.user_id},
            include={"user_skills": True, "user_location_certifications": True, "availability": True},
        )
        if requester_profile is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Requester user not found.")
        requester_result = evaluate_assignment(
            shift_snapshot(candidate_assignment.shift),
            user_snapshot(requester_profile),
            await existing_assignments(
                requester_profile.id,
                {requester_assignment.shift_id, candidate_assignment.shift_id},
            ),
        )
        requester_hard_blocks = [v for v in requester_result.violations if v.severity == "HARD_BLOCK"]
        if requester_hard_blocks:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Requester no longer qualifies for target shift: {requester_hard_blocks[0].description}",
            )
        if requester_result.requires_override and not note:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Override note is required.")

    transfer_records: list[dict[str, str]] = []
    notifications: list[object] = []
    async with prisma.tx() as tx:
        if candidate_assignment is None:
            await tx.shiftassignment.update(
                where={"id": requester_assignment.id},
                data={
                    "user_id": target_user.id,
                    "status": "assigned",
                    "assigned_by": actor.id,
                    "override_reason": note,
                    "version": requester_assignment.version + 1,
                },
            )
            transfer_records.append(
                {
                    "assignment_id": requester_assignment.id,
                    "from_user_id": requester_assignment.user_id,
                    "to_user_id": target_user.id,
                }
            )
        else:
            await tx.shiftassignment.update(
                where={"id": requester_assignment.id},
                data={
                    "user_id": target_user.id,
                    "status": "assigned",
                    "assigned_by": actor.id,
                    "override_reason": note,
                    "version": requester_assignment.version + 1,
                },
            )
            await tx.shiftassignment.update(
                where={"id": candidate_assignment.id},
                data={
                    "user_id": requester_assignment.user_id,
                    "status": "assigned",
                    "assigned_by": actor.id,
                    "override_reason": note,
                    "version": candidate_assignment.version + 1,
                },
            )
            transfer_records.extend(
                [
                    {
                        "assignment_id": requester_assignment.id,
                        "from_user_id": requester_assignment.user_id,
                        "to_user_id": target_user.id,
                    },
                    {
                        "assignment_id": candidate_assignment.id,
                        "from_user_id": candidate_assignment.user_id,
                        "to_user_id": requester_assignment.user_id,
                    },
                ]
            )

        row = await tx.swaprequest.update(
            where={"id": row.id},
            data={"status": "APPROVED", "resolved_at": now, "resolved_by": actor.id, "resolution_note": note, "version": row.version + 1},
        )
        await create_audit_log(
            actor_id=actor.id,
            action_type="drop.approve" if drop else "swap.approve",
            entity_type="swap_request",
            entity_id=row.id,
            location_id=requester_assignment.shift.location_id,
            before_state={"status": "PENDING_MANAGER"},
            after_state={
                "status": "APPROVED",
                "transfers": transfer_records,
                "legacy_single_transfer": is_legacy_single_transfer,
            },
            reason=note,
            db=tx,
        )

        notif_1 = await create_notification(
            user_id=row.initiated_by,
            notif_type="swap.approved" if not drop else "drop.approved",
            message=(
                "Request approved."
                if drop
                else (
                    "Swap approved and assignments were exchanged."
                    if not is_legacy_single_transfer
                    else "Swap approved."
                )
            ),
            payload={"requestId": row.id},
            db=tx,
            ws_manager=None,
        )
        notif_2 = await create_notification(
            user_id=target_user.id,
            notif_type="swap.approved" if not drop else "drop.approved",
            message=(
                "You are assigned to the shift."
                if drop
                else (
                    "Swap approved and assignments were exchanged."
                    if not is_legacy_single_transfer
                    else "Swap approved."
                )
            ),
            payload={"requestId": row.id},
            db=tx,
            ws_manager=None,
        )
        notifications = [notif_1, notif_2]

    ws = request.app.state.ws_manager
    await emit_notifications(ws, notifications)
    recipients = [row.initiated_by, target_user.id]
    await ws.emit_to_users(recipients, "swap.status_changed", {"swapRequestId": row.id, "newStatus": "APPROVED"})
    if candidate_assignment is None:
        await ws.emit_to_user(
            requester_assignment.user_id,
            "assignment.changed",
            {
                "shiftId": requester_assignment.shift_id,
                "userId": requester_assignment.user_id,
                "status": "removed",
                "changedBy": actor.id,
            },
        )
        await ws.emit_to_user(
            target_user.id,
            "assignment.changed",
            {
                "shiftId": requester_assignment.shift_id,
                "userId": target_user.id,
                "status": "assigned",
                "changedBy": actor.id,
            },
        )
    else:
        await ws.emit_to_user(
            requester_assignment.user_id,
            "assignment.changed",
            {
                "shiftId": requester_assignment.shift_id,
                "userId": requester_assignment.user_id,
                "status": "removed",
                "changedBy": actor.id,
            },
        )
        await ws.emit_to_user(
            requester_assignment.user_id,
            "assignment.changed",
            {
                "shiftId": candidate_assignment.shift_id,
                "userId": requester_assignment.user_id,
                "status": "assigned",
                "changedBy": actor.id,
            },
        )
        await ws.emit_to_user(
            target_user.id,
            "assignment.changed",
            {
                "shiftId": candidate_assignment.shift_id,
                "userId": target_user.id,
                "status": "removed",
                "changedBy": actor.id,
            },
        )
        await ws.emit_to_user(
            target_user.id,
            "assignment.changed",
            {
                "shiftId": requester_assignment.shift_id,
                "userId": target_user.id,
                "status": "assigned",
                "changedBy": actor.id,
            },
        )
    return row, notifications, requester_assignment.shift.location_id


@router.post("/{request_id}/approve", response_model=SwapRequestResponse)
async def approve_swap_like(request_id: str, body: SwapActionRequest, request: Request, current_user: CurrentUser = Depends(require_roles("admin", "manager"))) -> SwapRequestResponse:
    row = await prisma.swaprequest.find_unique(where={"id": request_id}, include={"requester_assignment": {"include": {"shift": True}}})
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Request not found.")
    if row.status != "PENDING_MANAGER":
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Request is not pending manager.")
    if current_user.role == "manager" and row.requester_assignment and row.requester_assignment.shift:
        ensure_manager_location_access(current_user, row.requester_assignment.shift.location_id)
    row, _, _ = await approve_transfer(row, current_user, body.note, request, drop=row.type == "drop")
    response_row = await _load_swap_for_response(row.id)
    return to_resp(response_row)


@router.post("/{request_id}/decline", response_model=SwapRequestResponse)
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
    response_row = await _load_swap_for_response(row.id)
    return to_resp(response_row)


@router.post("/drops", response_model=SwapRequestResponse)
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


@router.get("/drops/available", response_model=AvailableDropListResponse)
async def available_drops(request: Request, current_user: CurrentUser = Depends(require_roles("staff"))) -> AvailableDropListResponse:
    now = datetime.now(tz=timezone.utc)
    await expire_due_drop_requests(now=now, ws_manager=request.app.state.ws_manager)
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
        result = evaluate_assignment(shift_snapshot(a.shift), user_snapshot(u), await existing_assignments(u.id, {a.shift.id}))
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


@router.post("/drops/{request_id}/pickup", response_model=SwapRequestResponse)
async def pickup_drop(request_id: str, body: DropPickupRequest, request: Request, current_user: CurrentUser = Depends(require_roles("staff"))) -> SwapRequestResponse:
    row = await prisma.swaprequest.find_unique(where={"id": request_id}, include={"requester_assignment": {"include": {"shift": {"include": {"location": True, "required_skill": True}}}}})
    if row is None or row.type != "drop":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Drop request not found.")
    if row.status != "OPEN":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Drop request not open.")
    if row.expires_at and row.expires_at <= datetime.now(tz=timezone.utc):
        await expire_drop_request(
            request_row=row,
            now=datetime.now(tz=timezone.utc),
            ws_manager=request.app.state.ws_manager,
        )
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Drop request expired.")
    a = row.requester_assignment
    if a is None or a.shift is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found.")
    if a.user_id == current_user.id:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Cannot pickup own drop.")
    u = await prisma.user.find_unique(where={"id": current_user.id}, include={"user_skills": True, "user_location_certifications": True, "availability": True})
    if u is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Staff user not found.")
    result = evaluate_assignment(shift_snapshot(a.shift), user_snapshot(u), await existing_assignments(u.id, {a.shift_id}))
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


@router.post("/drops/{request_id}/approve", response_model=SwapRequestResponse)
async def approve_drop(request_id: str, body: SwapActionRequest, request: Request, current_user: CurrentUser = Depends(require_roles("admin", "manager"))) -> SwapRequestResponse:
    row = await prisma.swaprequest.find_unique(where={"id": request_id}, include={"requester_assignment": {"include": {"shift": True}}})
    if row is None or row.type != "drop":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Drop request not found.")
    if row.status != "PENDING_MANAGER":
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Drop is not pending manager.")
    if current_user.role == "manager" and row.requester_assignment and row.requester_assignment.shift:
        ensure_manager_location_access(current_user, row.requester_assignment.shift.location_id)
    row, _, _ = await approve_transfer(row, current_user, body.note, request, drop=True)
    response_row = await _load_swap_for_response(row.id)
    return to_resp(response_row)


@router.post("/drops/{request_id}/decline", response_model=SwapRequestResponse)
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
    response_row = await _load_swap_for_response(row.id)
    return to_resp(response_row)


@router.post("/drops/{request_id}/notify-qualified")
async def notify_qualified_staff(
    request_id: str,
    request: Request,
    current_user: CurrentUser = Depends(require_roles("admin", "manager")),
) -> dict[str, int]:
    row = await prisma.swaprequest.find_unique(
        where={"id": request_id},
        include={"requester_assignment": {"include": {"shift": {"include": {"location": True, "required_skill": True}}}}}
    )
    if row is None or row.type != "drop":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Drop request not found.")
    if row.status != "OPEN":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Drop request is not open for notifications (status: {row.status}).",
        )
    
    a = row.requester_assignment
    if a is None or a.shift is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment/Shift context missing.")

    # Find all active staff candidates (certified + skilled)
    skill_links = await prisma.userskill.find_many(where={"skill_id": a.shift.required_skill_id})
    cert_links = await prisma.userlocationcertification.find_many(
        where={"location_id": a.shift.location_id, "revoked_at": None}
    )
    skill_uids = {link.user_id for link in skill_links}
    cert_uids = {link.user_id for link in cert_links}
    candidate_ids = list(skill_uids.intersection(cert_uids))
    
    # Remove initiator
    if row.initiated_by in candidate_ids:
        candidate_ids.remove(row.initiated_by)

    candidates = await prisma.user.find_many(
        where={"id": {"in": candidate_ids}, "role": "staff", "is_active": True},
        include={"user_skills": True, "user_location_certifications": True, "availability": True}
    )

    count = 0
    ws = request.app.state.ws_manager
    async with prisma.tx() as tx:
        for u in candidates:
            # Quick qualification check
            res = evaluate_assignment(
                shift_snapshot(a.shift),
                user_snapshot(u),
                await existing_assignments(u.id, {a.shift.id})
            )
            if res.valid and not res.requires_override:
                notif = await create_notification(
                    user_id=u.id,
                    notif_type="drop.available",
                    message=f"Urgent coverage needed for {a.shift.required_skill.name} at {a.shift.location.name}.",
                    payload={"dropRequestId": row.id},
                    db=tx,
                    ws_manager=None
                )
                if ws:
                    await ws.emit_to_user(u.id, "notification.new", {
                        "notificationId": notif.id,
                        "type": notif.type,
                        "message": notif.message
                    })
                count += 1

    return {"notified": count}
