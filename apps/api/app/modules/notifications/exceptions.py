"""
MODULE: /apps/api/app/modules/notifications/exceptions.py

FUNCTION:
    Defines typed domain exceptions for notifications workflows.

DEPENDENCIES:
    - /apps/api/app/modules/notifications/router.py
    - /apps/api/app/modules/notifications/service.py

IMPORTANCE:
    Domain-specific exceptions keep service errors explicit and let routes map them to
    stable HTTP contracts.
"""


class NotificationNotFoundError(Exception):
    """Raised when a notification cannot be found for the current user."""


class NotificationUserNotFoundError(Exception):
    """Raised when the current user record cannot be found."""


class InvalidNotificationPreferenceError(Exception):
    """Raised when a notification preference value is unsupported."""

