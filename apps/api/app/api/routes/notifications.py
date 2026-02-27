"""
MODULE: /apps/api/app/api/routes/notifications.py

FUNCTION:
    Defines FastAPI endpoints and request/response orchestration for the `notifications`
    domain.

DEPENDENCIES:
    - /apps/api/app/api/router.py

IMPORTANCE:
    This module directly shapes externally visible API behavior and role-based access flows.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import CurrentUser, get_current_user
from app.core.database import prisma
from app.schemas.notification import (
    NotificationListResponse,
    NotificationPreferencesResponse,
    NotificationPreferencesUpdateRequest,
    NotificationResponse,
)
from app.services.notifications import to_notification_response


router = APIRouter(prefix="/notifications")


@router.get("", response_model=NotificationListResponse)
async def list_notifications(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    unread_only: bool = Query(default=False, alias="unreadOnly"),
    current_user: CurrentUser = Depends(get_current_user),
) -> NotificationListResponse:
    """List notifications.
    
    Args:
        page: 1-based page number.
        limit: Maximum items to return per page.
        unread_only: Input parameter `unread_only` used by this operation.
        current_user: Authenticated user from dependency resolution.
    
    Returns:
        Result typed as `NotificationListResponse`.
    """
    where: dict = {"user_id": current_user.id}
    if unread_only:
        where["read_at"] = None

    skip = (page - 1) * limit
    records = await prisma.notification.find_many(
        where=where,
        order={"created_at": "desc"},
        skip=skip,
        take=limit,
    )
    total = await prisma.notification.count(where=where)
    unread_count = await prisma.notification.count(where={"user_id": current_user.id, "read_at": None})

    notifications = [NotificationResponse(**to_notification_response(item)) for item in records]
    return NotificationListResponse(
        unread_count=unread_count,
        notifications=notifications,
        pagination={"page": page, "limit": limit, "total": total},
    )


@router.put("/read-all")
async def mark_all_read(current_user: CurrentUser = Depends(get_current_user)) -> dict[str, bool]:
    """Mark all read.
    
    Args:
        current_user: Authenticated user from dependency resolution.
    
    Returns:
        True when the operation succeeds, otherwise False.
    """
    await prisma.notification.update_many(
        where={"user_id": current_user.id, "read_at": None},
        data={"read_at": datetime.now(tz=timezone.utc)},
    )
    return {"updated": True}


@router.put("/{notification_id}/read")
async def mark_notification_read(
    notification_id: str,
    current_user: CurrentUser = Depends(get_current_user),
) -> dict[str, bool]:
    """Mark notification read.
    
    Args:
        notification_id: Identifier for the target resource.
        current_user: Authenticated user from dependency resolution.
    
    Returns:
        True when the operation succeeds, otherwise False.
    """
    notification = await prisma.notification.find_unique(where={"id": notification_id})
    if notification is None or notification.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found.")
    if notification.read_at is None:
        await prisma.notification.update(
            where={"id": notification_id},
            data={"read_at": datetime.now(tz=timezone.utc)},
        )
    return {"updated": True}


@router.get("/preferences", response_model=NotificationPreferencesResponse)
async def get_preferences(current_user: CurrentUser = Depends(get_current_user)) -> NotificationPreferencesResponse:
    """Get preferences.
    
    Args:
        current_user: Authenticated user from dependency resolution.
    
    Returns:
        Result typed as `NotificationPreferencesResponse`.
    """
    user = await prisma.user.find_unique(where={"id": current_user.id})
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    return NotificationPreferencesResponse(notification_pref=user.notification_pref)


@router.put("/preferences", response_model=NotificationPreferencesResponse)
async def update_preferences(
    payload: NotificationPreferencesUpdateRequest,
    current_user: CurrentUser = Depends(get_current_user),
) -> NotificationPreferencesResponse:
    """Update preferences.
    
    Args:
        payload: Validated request payload model.
        current_user: Authenticated user from dependency resolution.
    
    Returns:
        Result typed as `NotificationPreferencesResponse`.
    """
    if payload.notification_pref not in {"in_app", "in_app_email"}:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid notification preference.")
    user = await prisma.user.update(
        where={"id": current_user.id},
        data={"notification_pref": payload.notification_pref},
    )
    return NotificationPreferencesResponse(notification_pref=user.notification_pref)
