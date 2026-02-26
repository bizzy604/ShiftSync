from datetime import datetime

from pydantic import BaseModel


class NotificationResponse(BaseModel):
    id: str
    type: str
    message: str
    payload: dict
    created_at: datetime
    read_at: datetime | None


class NotificationListResponse(BaseModel):
    unread_count: int
    notifications: list[NotificationResponse]
    pagination: dict[str, int]


class NotificationPreferencesResponse(BaseModel):
    notification_pref: str


class NotificationPreferencesUpdateRequest(BaseModel):
    notification_pref: str
