import re
from datetime import date, datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import CurrentUser, ensure_self_or_admin, get_current_user, require_roles
from app.core.database import prisma
from app.core.security import hash_password
from app.schemas.user import (
    AvailabilityEntryResponse,
    AvailabilityReplaceRequest,
    AvailabilityResponse,
    CertificationAttachRequest,
    SkillAttachRequest,
    UserCertificationResponse,
    UserCreateRequest,
    UserListResponse,
    UserResponse,
    UserSkillResponse,
    UserUpdateRequest,
)
from app.services.audit import create_audit_log
from app.services.user_access import get_manager_user_scope


CLOCK_TIME_REGEX = re.compile(r"^([01]\d|2[0-3]):([0-5]\d)$")

router = APIRouter()


def _to_user_response(user: object) -> UserResponse:
    return UserResponse(
        id=user.id,
        name=user.name,
        email=user.email,
        role=user.role,
        home_timezone=user.home_timezone,
        desired_hours_per_week=user.desired_hours_per_week,
        hourly_rate=user.hourly_rate,
        notification_pref=user.notification_pref,
        is_active=user.is_active,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


def _ensure_clock(clock_time: str | None) -> None:
    if clock_time is None or CLOCK_TIME_REGEX.match(clock_time):
        return
    raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Invalid clock time: {clock_time}")


async def _assert_user_visible_to_actor(actor: CurrentUser, target_user_id: str) -> None:
    if actor.role == "admin":
        return
    if actor.id == target_user_id:
        return
    if actor.role != "manager":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")

    visible_ids = await get_manager_user_scope(actor)
    if target_user_id not in visible_ids:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")


@router.get("", response_model=UserListResponse)
async def list_users(
    location_id: str | None = Query(default=None),
    skill_id: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=25, ge=1, le=100),
    current_user: CurrentUser = Depends(require_roles("admin", "manager")),
) -> UserListResponse:
    where: dict[str, Any] = {"is_active": True}

    if current_user.role == "manager":
        scoped_ids = await get_manager_user_scope(current_user)
        where["id"] = {"in": list(scoped_ids)}

    if location_id:
        certs = await prisma.userlocationcertification.find_many(
            where={"location_id": location_id, "revoked_at": None},
        )
        location_user_ids = {item.user_id for item in certs}
        if "id" in where and "in" in where["id"]:
            existing_ids = set(where["id"]["in"])
            where["id"]["in"] = list(existing_ids.intersection(location_user_ids))
        else:
            where["id"] = {"in": list(location_user_ids)}

    if skill_id:
        skill_users = await prisma.userskill.find_many(
            where={"skill_id": skill_id},
        )
        skill_user_ids = {item.user_id for item in skill_users}
        if "id" in where and "in" in where["id"]:
            existing_ids = set(where["id"]["in"])
            where["id"]["in"] = list(existing_ids.intersection(skill_user_ids))
        else:
            where["id"] = {"in": list(skill_user_ids)}

    skip = (page - 1) * limit
    users = await prisma.user.find_many(where=where, skip=skip, take=limit, order={"name": "asc"})
    total = await prisma.user.count(where=where)

    return UserListResponse(
        users=[_to_user_response(user) for user in users],
        total=total,
        page=page,
        limit=limit,
    )


@router.post("", response_model=UserResponse)
async def create_user(
    payload: UserCreateRequest,
    current_user: CurrentUser = Depends(require_roles("admin")),
) -> UserResponse:
    existing = await prisma.user.find_unique(where={"email": payload.email})
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already exists.")

    data = payload.model_dump()
    password = data.pop("password")
    data["password_hash"] = hash_password(password)
    async with prisma.tx() as tx:
        user = await tx.user.create(data=data)
        await create_audit_log(
            actor_id=current_user.id,
            action_type="user.create",
            entity_type="user",
            entity_id=user.id,
            after_state={
                "name": user.name,
                "email": user.email,
                "role": user.role,
                "is_active": user.is_active,
            },
            db=tx,
        )
    return _to_user_response(user)


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(user_id: str, current_user: CurrentUser = Depends(get_current_user)) -> UserResponse:
    await _assert_user_visible_to_actor(current_user, user_id)

    user = await prisma.user.find_unique(where={"id": user_id})
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    return _to_user_response(user)


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    payload: UserUpdateRequest,
    current_user: CurrentUser = Depends(get_current_user),
) -> UserResponse:
    ensure_self_or_admin(current_user, user_id)

    user = await prisma.user.find_unique(where={"id": user_id})
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    data = payload.model_dump(exclude_none=True)
    if current_user.role != "admin":
        blocked_keys = {"hourly_rate", "is_active"}
        forbidden = blocked_keys.intersection(data.keys())
        if forbidden:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Field update is not allowed.")

    async with prisma.tx() as tx:
        updated = await tx.user.update(where={"id": user_id}, data=data)
        await create_audit_log(
            actor_id=current_user.id,
            action_type="user.update",
            entity_type="user",
            entity_id=user_id,
            before_state={
                "name": user.name,
                "home_timezone": user.home_timezone,
                "desired_hours_per_week": user.desired_hours_per_week,
                "hourly_rate": float(user.hourly_rate or 0) if user.hourly_rate is not None else None,
                "notification_pref": user.notification_pref,
                "is_active": user.is_active,
            },
            after_state={
                "name": updated.name,
                "home_timezone": updated.home_timezone,
                "desired_hours_per_week": updated.desired_hours_per_week,
                "hourly_rate": float(updated.hourly_rate or 0) if updated.hourly_rate is not None else None,
                "notification_pref": updated.notification_pref,
                "is_active": updated.is_active,
            },
            db=tx,
        )
    return _to_user_response(updated)


@router.delete("/{user_id}")
async def delete_user(
    user_id: str,
    current_user: CurrentUser = Depends(require_roles("admin")),
) -> dict[str, bool]:
    user = await prisma.user.find_unique(where={"id": user_id})
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    async with prisma.tx() as tx:
        await tx.user.update(where={"id": user_id}, data={"is_active": False})
        await create_audit_log(
            actor_id=current_user.id,
            action_type="user.deactivate",
            entity_type="user",
            entity_id=user_id,
            before_state={"is_active": user.is_active},
            after_state={"is_active": False},
            db=tx,
        )
    return {"deleted": True}


@router.get("/{user_id}/skills", response_model=list[UserSkillResponse])
async def list_user_skills(
    user_id: str,
    current_user: CurrentUser = Depends(require_roles("admin", "manager")),
) -> list[UserSkillResponse]:
    await _assert_user_visible_to_actor(current_user, user_id)
    records = await prisma.userskill.find_many(
        where={"user_id": user_id},
        include={"skill": True},
    )
    return [UserSkillResponse(skill_id=item.skill_id, skill_name=item.skill.name) for item in records]


@router.post("/{user_id}/skills", response_model=UserSkillResponse)
async def add_user_skill(
    user_id: str,
    payload: SkillAttachRequest,
    current_user: CurrentUser = Depends(require_roles("admin")),
) -> UserSkillResponse:
    user = await prisma.user.find_unique(where={"id": user_id})
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    skill = await prisma.skill.find_unique(where={"id": payload.skill_id})
    if skill is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Skill not found.")

    existing = await prisma.userskill.find_unique(
        where={"user_id_skill_id": {"user_id": user_id, "skill_id": payload.skill_id}}
    )
    if existing is None:
        async with prisma.tx() as tx:
            await tx.userskill.create(data={"user_id": user_id, "skill_id": payload.skill_id})
            await create_audit_log(
                actor_id=current_user.id,
                action_type="skill.add",
                entity_type="user_skill",
                entity_id=user_id,
                after_state={"user_id": user_id, "skill_id": payload.skill_id},
                db=tx,
            )

    return UserSkillResponse(skill_id=skill.id, skill_name=skill.name)


@router.delete("/{user_id}/skills/{skill_id}")
async def remove_user_skill(
    user_id: str,
    skill_id: str,
    current_user: CurrentUser = Depends(require_roles("admin")),
) -> dict[str, bool]:
    existing = await prisma.userskill.find_unique(where={"user_id_skill_id": {"user_id": user_id, "skill_id": skill_id}})
    if existing is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Skill link not found.")
    async with prisma.tx() as tx:
        await tx.userskill.delete(where={"user_id_skill_id": {"user_id": user_id, "skill_id": skill_id}})
        await create_audit_log(
            actor_id=current_user.id,
            action_type="skill.remove",
            entity_type="user_skill",
            entity_id=user_id,
            before_state={"user_id": user_id, "skill_id": skill_id},
            db=tx,
        )
    return {"removed": True}


@router.get("/{user_id}/certifications", response_model=list[UserCertificationResponse])
async def list_user_certifications(
    user_id: str,
    current_user: CurrentUser = Depends(require_roles("admin", "manager")),
) -> list[UserCertificationResponse]:
    await _assert_user_visible_to_actor(current_user, user_id)
    records = await prisma.userlocationcertification.find_many(
        where={"user_id": user_id},
        include={"location": True},
    )
    return [
        UserCertificationResponse(
            location_id=item.location_id,
            location_name=item.location.name if item.location else "",
            certified_at=item.certified_at,
            revoked_at=item.revoked_at,
        )
        for item in records
    ]


@router.post("/{user_id}/certifications", response_model=UserCertificationResponse)
async def add_user_certification(
    user_id: str,
    payload: CertificationAttachRequest,
    current_user: CurrentUser = Depends(require_roles("admin")),
) -> UserCertificationResponse:
    location = await prisma.location.find_unique(where={"id": payload.location_id})
    if location is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Location not found.")

    async with prisma.tx() as tx:
        record = await tx.userlocationcertification.upsert(
            where={"user_id_location_id": {"user_id": user_id, "location_id": payload.location_id}},
            data={
                "create": {
                    "user_id": user_id,
                    "location_id": payload.location_id,
                },
                "update": {
                    "revoked_at": None,
                    "revoked_by": None,
                },
            },
        )
        await create_audit_log(
            actor_id=current_user.id,
            action_type="cert.grant",
            entity_type="certification",
            entity_id=user_id,
            location_id=payload.location_id,
            after_state={
                "user_id": user_id,
                "location_id": payload.location_id,
                "revoked_at": None,
            },
            db=tx,
        )
    return UserCertificationResponse(
        location_id=record.location_id,
        location_name=location.name,
        certified_at=record.certified_at,
        revoked_at=record.revoked_at,
    )


@router.delete("/{user_id}/certifications/{location_id}")
async def remove_user_certification(
    user_id: str,
    location_id: str,
    current_user: CurrentUser = Depends(require_roles("admin")),
) -> dict[str, bool]:
    record = await prisma.userlocationcertification.find_unique(
        where={"user_id_location_id": {"user_id": user_id, "location_id": location_id}}
    )
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Certification not found.")

    revoked_at = datetime.now(timezone.utc)
    async with prisma.tx() as tx:
        await tx.userlocationcertification.update(
            where={"user_id_location_id": {"user_id": user_id, "location_id": location_id}},
            data={
                "revoked_at": revoked_at,
                "revoked_by": current_user.id,
            },
        )
        await create_audit_log(
            actor_id=current_user.id,
            action_type="cert.revoke",
            entity_type="certification",
            entity_id=user_id,
            location_id=location_id,
            before_state={"revoked_at": record.revoked_at},
            after_state={"revoked_at": revoked_at.isoformat()},
            db=tx,
        )
    return {"revoked": True}


@router.get("/{user_id}/availability", response_model=AvailabilityResponse)
async def get_user_availability(
    user_id: str,
    current_user: CurrentUser = Depends(get_current_user),
) -> AvailabilityResponse:
    if current_user.role == "manager":
        await _assert_user_visible_to_actor(current_user, user_id)
    else:
        ensure_self_or_admin(current_user, user_id)

    entries = await prisma.availability.find_many(where={"user_id": user_id}, order={"created_at": "asc"})
    recurring: list[AvailabilityEntryResponse] = []
    exceptions: list[AvailabilityEntryResponse] = []

    for entry in entries:
        mapped = AvailabilityEntryResponse(
            id=entry.id,
            avail_type=entry.avail_type,
            day_of_week=entry.day_of_week,
            specific_date=entry.specific_date,
            start_clock=entry.start_clock,
            end_clock=entry.end_clock,
            is_available=entry.is_available,
        )
        if entry.avail_type == "recurring":
            recurring.append(mapped)
        else:
            exceptions.append(mapped)

    return AvailabilityResponse(user_id=user_id, recurring=recurring, exceptions=exceptions)


@router.put("/{user_id}/availability", response_model=AvailabilityResponse)
async def replace_user_availability(
    user_id: str,
    payload: AvailabilityReplaceRequest,
    current_user: CurrentUser = Depends(get_current_user),
) -> AvailabilityResponse:
    ensure_self_or_admin(current_user, user_id)

    user = await prisma.user.find_unique(where={"id": user_id})
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    create_data: list[dict[str, Any]] = []
    for recurring in payload.recurring:
        _ensure_clock(recurring.start_clock_time)
        _ensure_clock(recurring.end_clock_time)
        create_data.append(
            {
                "user_id": user_id,
                "avail_type": "recurring",
                "day_of_week": recurring.day_of_week,
                "start_clock": recurring.start_clock_time,
                "end_clock": recurring.end_clock_time,
                "is_available": True,
            }
        )

    for exception in payload.exceptions:
        _ensure_clock(exception.start_clock_time)
        _ensure_clock(exception.end_clock_time)
        specific_date = datetime.combine(exception.date, datetime.min.time())
        create_data.append(
            {
                "user_id": user_id,
                "avail_type": "exception",
                "specific_date": specific_date,
                "start_clock": exception.start_clock_time,
                "end_clock": exception.end_clock_time,
                "is_available": exception.is_available,
            }
        )

    previous_entries = await prisma.availability.find_many(where={"user_id": user_id})
    previous_recurring = sum(1 for entry in previous_entries if entry.avail_type == "recurring")
    previous_exceptions = len(previous_entries) - previous_recurring
    next_recurring = sum(1 for row in create_data if row["avail_type"] == "recurring")
    next_exceptions = len(create_data) - next_recurring

    async with prisma.tx() as tx:
        await tx.availability.delete_many(where={"user_id": user_id})
        if create_data:
            await tx.availability.create_many(data=create_data)
        await create_audit_log(
            actor_id=current_user.id,
            action_type="availability.replace",
            entity_type="availability",
            entity_id=user_id,
            before_state={
                "count": len(previous_entries),
                "recurring_count": previous_recurring,
                "exception_count": previous_exceptions,
            },
            after_state={
                "count": len(create_data),
                "recurring_count": next_recurring,
                "exception_count": next_exceptions,
            },
            db=tx,
        )

    return await get_user_availability(user_id=user_id, current_user=current_user)
