from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import CurrentUser, get_current_user, require_roles
from app.core.database import prisma
from app.schemas.location import (
    LocationCreateRequest,
    LocationListResponse,
    LocationResponse,
    LocationUpdateRequest,
)


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
    _: CurrentUser = Depends(require_roles("admin")),
) -> LocationResponse:
    location = await prisma.location.create(data=payload.model_dump())
    return _to_location_response(location)


@router.get("/{location_id}", response_model=LocationResponse)
async def get_location(
    location_id: str,
    current_user: CurrentUser = Depends(get_current_user),
) -> LocationResponse:
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
    _: CurrentUser = Depends(require_roles("admin")),
) -> LocationResponse:
    existing = await prisma.location.find_unique(where={"id": location_id})
    if existing is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Location not found.")

    data = payload.model_dump(exclude_none=True)
    location = await prisma.location.update(where={"id": location_id}, data=data)
    return _to_location_response(location)
