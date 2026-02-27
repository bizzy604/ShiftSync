"""
MODULE: /apps/api/app/modules/assignments/router.py

FUNCTION:
    Exposes thin HTTP route registration for assignments workflows implemented in service.

DEPENDENCIES:
    - /apps/api/app/api/router.py
    - /apps/api/app/modules/assignments/router.py
    - /apps/api/tests/integration/test_assignments_notifications.py

IMPORTANCE:
    This module keeps transport concerns separate while assignment constraint and locking
    orchestration lives in the assignments service layer.
"""

from fastapi import APIRouter

from app.modules.assignments.service import (
    AssignmentCreateRequest,
    AssignmentListResponse,
    AssignmentPreviewResponse,
    AssignmentResponse,
    ConstraintSuggestion,
    MyAssignmentListResponse,
    _create_overtime_warning_notifications,
    _weekly_hours_warning,
    create_assignment,
    delete_assignment,
    list_assignments,
    list_my_assignments,
    list_shift_suggestions,
    preview_assignment,
)


router = APIRouter()
router.add_api_route("/me", list_my_assignments, methods=["GET"], response_model=MyAssignmentListResponse)
router.add_api_route("", list_assignments, methods=["GET"], response_model=AssignmentListResponse)
router.add_api_route("/preview", preview_assignment, methods=["GET"], response_model=AssignmentPreviewResponse)
router.add_api_route(
    "/shifts/{shift_id}/suggestions",
    list_shift_suggestions,
    methods=["GET"],
    response_model=list[ConstraintSuggestion],
)
router.add_api_route("", create_assignment, methods=["POST"], response_model=AssignmentResponse)
router.add_api_route("/{assignment_id}", delete_assignment, methods=["DELETE"])

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
