"""
MODULE: /apps/api/app/modules/assignments/__init__.py

FUNCTION:
    Defines the public API boundary and exported contracts for the assignments domain.

DEPENDENCIES:
    - /apps/api/app/api/router.py
    - /apps/api/app/modules/assignments/router.py

IMPORTANCE:
    Exporting a stable surface here prevents external callers from depending on private
    module internals.
"""

from app.modules.assignments.router import (
    AssignmentCreateRequest,
    AssignmentListResponse,
    AssignmentPreviewResponse,
    AssignmentResponse,
    ConstraintSuggestion,
    _create_overtime_warning_notifications,
    _weekly_hours_warning,
    create_assignment,
    delete_assignment,
    list_assignments,
    list_my_assignments,
    list_shift_suggestions,
    preview_assignment,
    router,
)

__all__ = [
    "router",
    "AssignmentCreateRequest",
    "AssignmentResponse",
    "AssignmentListResponse",
    "AssignmentPreviewResponse",
    "ConstraintSuggestion",
    "list_my_assignments",
    "list_assignments",
    "preview_assignment",
    "list_shift_suggestions",
    "create_assignment",
    "delete_assignment",
    "_weekly_hours_warning",
    "_create_overtime_warning_notifications",
]
