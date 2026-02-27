"""
MODULE: /apps/api/app/modules/locations/router.py

FUNCTION:
    Exposes locations HTTP endpoints through a thin modular route layer.

DEPENDENCIES:
    - /apps/api/app/api/router.py
    - /apps/api/app/modules/locations/router.py

IMPORTANCE:
    This module preserves existing `/locations` API contracts while delegating logic to
    service and repository layers.
"""

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import CurrentUser, get_current_user, require_roles
from app.modules.locations.exceptions import LocationAccessDeniedError, LocationNotFoundError
from app.modules.locations.service import (
    create_location as create_location_record,
    get_location as get_location_record,
    list_locations as list_location_records,
    update_location as update_location_record,
)
from app.schemas.location import (
    LocationCreateRequest,
    LocationListResponse,
    LocationResponse,
    LocationUpdateRequest,
)


router = APIRouter()


def _to_location_response(location: object) -> LocationResponse:
    """Convert a location ORM object to response schema."""

    return LocationResponse(
        id=location.id,
        name=location.name,
        address=location.address,
        iana_timezone=location.iana_timezone,
        is_active=location.is_active,
        created_at=location.created_at,
    )


async def list_locations(
    current_user: CurrentUser = Depends(get_current_user),
) -> LocationListResponse:
    """List locations visible to the current user."""

    locations = await list_location_records(current_user=current_user)
    return LocationListResponse(locations=[_to_location_response(location) for location in locations])


async def create_location(
    payload: LocationCreateRequest,
    current_user: CurrentUser = Depends(require_roles("admin")),
) -> LocationResponse:
    """Create a location for administrators."""

    location = await create_location_record(payload=payload, actor_id=current_user.id)
    return _to_location_response(location)


async def get_location(
    location_id: str,
    current_user: CurrentUser = Depends(get_current_user),
) -> LocationResponse:
    """Fetch one location after access validation."""

    try:
        location = await get_location_record(location_id=location_id, current_user=current_user)
    except LocationNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Location not found.") from exc
    except LocationAccessDeniedError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.") from exc

    return _to_location_response(location)


async def update_location(
    location_id: str,
    payload: LocationUpdateRequest,
    current_user: CurrentUser = Depends(require_roles("admin")),
) -> LocationResponse:
    """Update one location for administrators."""

    try:
        location = await update_location_record(
            location_id=location_id,
            payload=payload,
            actor_id=current_user.id,
        )
    except LocationNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Location not found.") from exc

    return _to_location_response(location)


router.add_api_route("", list_locations, methods=["GET"], response_model=LocationListResponse)
router.add_api_route("", create_location, methods=["POST"], response_model=LocationResponse)
router.add_api_route("/{location_id}", get_location, methods=["GET"], response_model=LocationResponse)
router.add_api_route("/{location_id}", update_location, methods=["PUT"], response_model=LocationResponse)
