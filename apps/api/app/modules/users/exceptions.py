"""
MODULE: /apps/api/app/modules/users/exceptions.py

FUNCTION:
    Defines typed domain exceptions for users workflows.

DEPENDENCIES:
    - /apps/api/app/modules/users/router.py
    - /apps/api/app/modules/users/service.py

IMPORTANCE:
    Typed domain exceptions keep users-service failures explicit and simplify stable
    HTTP mapping at the route layer.
"""


class UserNotFoundError(Exception):
    """Raised when a target user record cannot be found."""


class UserAccessDeniedError(Exception):
    """Raised when current actor is not permitted to access target user data."""


class UserEmailAlreadyExistsError(Exception):
    """Raised when creating a user with an already-registered email address."""


class UserFieldUpdateNotAllowedError(Exception):
    """Raised when a non-admin attempts to update restricted fields."""


class UserSkillNotFoundError(Exception):
    """Raised when a target skill record does not exist."""


class UserSkillLinkNotFoundError(Exception):
    """Raised when removing a non-existent user-skill association."""


class UserCertificationNotFoundError(Exception):
    """Raised when a target user-location certification record does not exist."""


class UserLocationNotFoundError(Exception):
    """Raised when a target location record does not exist."""


class UserInvalidClockTimeError(Exception):
    """Raised when submitted availability clock-time values are invalid."""

    def __init__(self, clock_time: str | None) -> None:
        """Initialize exception with invalid clock-time value."""

        super().__init__(f"Invalid clock time: {clock_time}")
        self.clock_time = clock_time

