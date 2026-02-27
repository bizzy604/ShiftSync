"""
MODULE: /apps/api/app/api/routes/locations.py

FUNCTION:
    Defines FastAPI endpoints and request/response orchestration for the `locations` domain.

DEPENDENCIES:
    - /apps/api/app/api/router.py

IMPORTANCE:
    This module directly shapes externally visible API behavior and role-based access flows.
"""

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import CurrentUser, get_current_user, require_roles
from app.core.database import prisma
from app.schemas.location import (
    LocationCreateRequest,
    LocationListResponse,
    LocationResponse,
    LocationUpdateRequest,
)
from app.services.audit import create_audit_log


router = APIRouter()


def _to_location_response(location: object) -> LocationResponse:
    return LocationResponse(
        id=location.id,
        name=location.name,
        address=location.address,
        iana_timezone=location.iana_timezone,
        is_active=location.is_active,
        created_at=location.created_at,
    )


@router.get("", response_model=LocationListResponse)
async def list_locations(current_user: CurrentUser = Depends(get_current_user)) -> LocationListResponse:
    """List locations.
    
    Args:
        current_user: Authenticated user from dependency resolution.
    
    Returns:
        Result typed as `LocationListResponse`.
    """
    if current_user.role == "admin":
        locations = await prisma.location.find_many(order={"name": "asc"})
    elif current_user.role == "manager":
        assignments = await prisma.managerlocationassignment.find_many(
            where={"manager_id": current_user.id},
            include={"location": True},
        )
        locations = [assignment.location for assignment in assignments if assignment.location is not None]
    else:
        certifications = await prisma.userlocationcertification.find_many(
            where={"user_id": current_user.id, "revoked_at": None},
            include={"location": True},
        )
        locations = [cert.location for cert in certifications if cert.location is not None]

    return LocationListResponse(locations=[_to_location_response(location) for location in locations])


@router.post("", response_model=LocationResponse)
async def create_location(
    payload: LocationCreateRequest,
    current_user: CurrentUser = Depends(require_roles("admin")),
) -> LocationResponse:
    """Create location.
    
    Args:
        payload: Validated request payload model.
        current_user: Authenticated user from dependency resolution.
    
    Returns:
        Result typed as `LocationResponse`.
    """
    async with prisma.tx() as tx:
        location = await tx.location.create(data=payload.model_dump())
        await create_audit_log(
            actor_id=current_user.id,
            action_type="location.create",
            entity_type="location",
            entity_id=location.id,
            location_id=location.id,
            after_state={
                "name": location.name,
                "address": location.address,
                "iana_timezone": location.iana_timezone,
                "is_active": location.is_active,
            },
            db=tx,
        )
    return _to_location_response(location)


@router.get("/{location_id}", response_model=LocationResponse)
async def get_location(
    location_id: str,
    current_user: CurrentUser = Depends(get_current_user),
) -> LocationResponse:
    """Get location.
    
    Args:
        location_id: Target location identifier.
        current_user: Authenticated user from dependency resolution.
    
    Returns:
        Result typed as `LocationResponse`.
    """
    location = await prisma.location.find_unique(where={"id": location_id})
    if location is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Location not found.")

    if current_user.role == "manager":
        if location_id not in current_user.location_ids:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")
    elif current_user.role == "staff":
        cert = await prisma.userlocationcertification.find_unique(
            where={"user_id_location_id": {"user_id": current_user.id, "location_id": location_id}},
        )
        if cert is None or cert.revoked_at is not None:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")

    return _to_location_response(location)


@router.put("/{location_id}", response_model=LocationResponse)
async def update_location(
    location_id: str,
    payload: LocationUpdateRequest,
    current_user: CurrentUser = Depends(require_roles("admin")),
) -> LocationResponse:
    """Update location.
    
    Args:
        location_id: Target location identifier.
        payload: Validated request payload model.
        current_user: Authenticated user from dependency resolution.
    
    Returns:
        Result typed as `LocationResponse`.
    """
    existing = await prisma.location.find_unique(where={"id": location_id})
    if existing is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Location not found.")

    data = payload.model_dump(exclude_none=True)
    async with prisma.tx() as tx:
        location = await tx.location.update(where={"id": location_id}, data=data)
        await create_audit_log(
            actor_id=current_user.id,
            action_type="location.update",
            entity_type="location",
            entity_id=location_id,
            location_id=location_id,
            before_state={
                "name": existing.name,
                "address": existing.address,
                "iana_timezone": existing.iana_timezone,
                "is_active": existing.is_active,
            },
            after_state={
                "name": location.name,
                "address": location.address,
                "iana_timezone": location.iana_timezone,
                "is_active": location.is_active,
            },
            db=tx,
        )
    return _to_location_response(location)
