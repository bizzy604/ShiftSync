"""
MODULE: /apps/api/app/modules/notifications/router.py

FUNCTION:
    Exposes notifications HTTP endpoints through a thin modular route layer.

DEPENDENCIES:
    - /apps/api/app/api/router.py
    - /apps/api/app/modules/notifications/router.py

IMPORTANCE:
    This route layer preserves existing `/notifications` behavior while delegating
    business logic to the service and repository layers.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import CurrentUser, get_current_user
from app.modules.notifications.exceptions import (
    InvalidNotificationPreferenceError,
    NotificationNotFoundError,
    NotificationUserNotFoundError,
)
from app.modules.notifications.service import (
    get_preferences as get_notification_preferences,
    list_notifications as list_user_notifications,
    mark_all_read as mark_all_notifications_read,
    mark_notification_read as mark_one_notification_read,
    update_preferences as update_notification_preferences,
)
from app.schemas.notification import (
    NotificationListResponse,
    NotificationPreferencesResponse,
    NotificationPreferencesUpdateRequest,
    NotificationResponse,
)


router = APIRouter(prefix="/notifications")


async def list_notifications(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    unread_only: bool = Query(default=False, alias="unreadOnly"),
    current_user: CurrentUser = Depends(get_current_user),
) -> NotificationListResponse:
    """List notifications visible to the current user."""

    payload = await list_user_notifications(
        user_id=current_user.id,
        page=page,
        limit=limit,
        unread_only=unread_only,
    )
    notifications = [NotificationResponse(**item) for item in payload["notifications"]]
    return NotificationListResponse(
        unread_count=payload["unread_count"],
        notifications=notifications,
        pagination=payload["pagination"],
    )


async def mark_all_read(
    current_user: CurrentUser = Depends(get_current_user),
) -> dict[str, bool]:
    """Mark all unread notifications as read for the current user."""

    await mark_all_notifications_read(user_id=current_user.id)
    return {"updated": True}


async def mark_notification_read(
    notification_id: str,
    current_user: CurrentUser = Depends(get_current_user),
) -> dict[str, bool]:
    """Mark one notification as read for the current user."""

    try:
        await mark_one_notification_read(notification_id=notification_id, user_id=current_user.id)
    except NotificationNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found.") from exc

    return {"updated": True}


async def get_preferences(
    current_user: CurrentUser = Depends(get_current_user),
) -> NotificationPreferencesResponse:
    """Return the current user's notification preferences."""

    try:
        pref = await get_notification_preferences(user_id=current_user.id)
    except NotificationUserNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.") from exc
    return NotificationPreferencesResponse(notification_pref=pref)


async def update_preferences(
    payload: NotificationPreferencesUpdateRequest,
    current_user: CurrentUser = Depends(get_current_user),
) -> NotificationPreferencesResponse:
    """Update and return the current user's notification preferences."""

    try:
        pref = await update_notification_preferences(
            user_id=current_user.id,
            notification_pref=payload.notification_pref,
        )
    except InvalidNotificationPreferenceError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid notification preference.",
        ) from exc

    return NotificationPreferencesResponse(notification_pref=pref)


router.add_api_route("", list_notifications, methods=["GET"], response_model=NotificationListResponse)
router.add_api_route("/read-all", mark_all_read, methods=["PUT"])
router.add_api_route("/{notification_id}/read", mark_notification_read, methods=["PUT"])
router.add_api_route("/preferences", get_preferences, methods=["GET"], response_model=NotificationPreferencesResponse)
router.add_api_route(
    "/preferences",
    update_preferences,
    methods=["PUT"],
    response_model=NotificationPreferencesResponse,
)
