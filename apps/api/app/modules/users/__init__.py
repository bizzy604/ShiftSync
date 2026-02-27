"""
MODULE: /apps/api/app/modules/users/__init__.py

FUNCTION:
    Defines the public API boundary and exported contracts for the users domain.

DEPENDENCIES:
    - /apps/api/app/api/router.py
    - /apps/api/app/modules/users/router.py

IMPORTANCE:
    Exporting a stable surface here prevents external callers from depending on private
    module internals.
"""

from app.modules.users.router import (
    AvailabilityReplaceRequest,
    AvailabilityResponse,
    UserCreateRequest,
    UserListResponse,
    UserResponse,
    UserUpdateRequest,
    add_user_certification,
    add_user_skill,
    create_user,
    delete_user,
    get_user,
    get_user_availability,
    list_user_certifications,
    list_user_skills,
    list_users,
    remove_user_certification,
    remove_user_skill,
    replace_user_availability,
    router,
    update_user,
)
from app.modules.users.service import assert_user_visible_to_actor, ensure_clock, get_manager_user_scope

__all__ = [
    "router",
    "UserCreateRequest",
    "UserUpdateRequest",
    "UserResponse",
    "UserListResponse",
    "AvailabilityReplaceRequest",
    "AvailabilityResponse",
    "list_users",
    "create_user",
    "get_user",
    "update_user",
    "delete_user",
    "list_user_skills",
    "add_user_skill",
    "remove_user_skill",
    "list_user_certifications",
    "add_user_certification",
    "remove_user_certification",
    "get_user_availability",
    "replace_user_availability",
    "get_manager_user_scope",
    "assert_user_visible_to_actor",
    "ensure_clock",
]
