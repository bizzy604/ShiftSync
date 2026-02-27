"""
MODULE: /apps/api/app/core/models.py

FUNCTION:
    Provides core infrastructure logic for `models` used across backend modules.

DEPENDENCIES:
    - /apps/api/alembic/env.py
    - /apps/api/app/core/database.py
    - /apps/api/scripts/seed_prd_scenarios.py

IMPORTANCE:
    This module is foundational infrastructure; regressions here can cascade across the
    backend.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, Text, text
from sqlalchemy.dialects.postgresql import ENUM, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.db_base import Base


RoleEnum = ENUM("admin", "manager", "staff", name="role", create_type=False)
NotificationPreferenceEnum = ENUM("in_app", "in_app_email", name="notification_preference", create_type=False)
AvailabilityTypeEnum = ENUM("recurring", "exception", name="availability_type", create_type=False)
ShiftStatusEnum = ENUM("draft", "published", "cancelled", name="shift_status", create_type=False)
AssignmentStatusEnum = ENUM("assigned", "swap_pending", "dropped", "removed", name="assignment_status", create_type=False)
SwapRequestTypeEnum = ENUM("swap", "drop", name="swap_request_type", create_type=False)
SwapRequestStatusEnum = ENUM(
    "OPEN",
    "PENDING_ACCEPTEE",
    "PENDING_MANAGER",
    "APPROVED",
    "REJECTED",
    "CANCELLED",
    "EXPIRED",
    name="swap_request_status",
    create_type=False,
)


class User(Base):
    """ORM model for platform users."""

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, server_default=text("gen_random_uuid()"))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(RoleEnum, nullable=False)
    home_timezone: Mapped[str] = mapped_column(String(100), nullable=False, default="America/New_York")
    desired_hours_per_week: Mapped[int] = mapped_column(Integer, nullable=False, default=40)
    hourly_rate: Mapped[Decimal | None] = mapped_column(Numeric(8, 2), nullable=True)
    notification_pref: Mapped[str] = mapped_column(NotificationPreferenceEnum, nullable=False, default="in_app")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    user_skills: Mapped[list[UserSkill]] = relationship(back_populates="user")
    user_location_certifications: Mapped[list[UserLocationCertification]] = relationship(
        back_populates="user",
        foreign_keys="UserLocationCertification.user_id",
    )
    manager_location_assignments: Mapped[list[ManagerLocationAssignment]] = relationship(
        back_populates="manager",
        foreign_keys="ManagerLocationAssignment.manager_id",
    )
    availability: Mapped[list[Availability]] = relationship(back_populates="user")
    revoked_certs: Mapped[list[UserLocationCertification]] = relationship(
        back_populates="revoked_user",
        foreign_keys="UserLocationCertification.revoked_by",
    )
    created_shifts: Mapped[list[Shift]] = relationship(
        back_populates="created_by_user",
        foreign_keys="Shift.created_by",
    )
    user_assignments: Mapped[list[ShiftAssignment]] = relationship(
        back_populates="user",
        foreign_keys="ShiftAssignment.user_id",
    )
    assignments_made: Mapped[list[ShiftAssignment]] = relationship(
        back_populates="assigned_by_user",
        foreign_keys="ShiftAssignment.assigned_by",
    )
    swap_requests_initiated: Mapped[list[SwapRequest]] = relationship(
        back_populates="initiator",
        foreign_keys="SwapRequest.initiated_by",
    )
    swap_requests_targeted: Mapped[list[SwapRequest]] = relationship(
        back_populates="target_user",
        foreign_keys="SwapRequest.target_user_id",
    )
    swap_requests_pickup: Mapped[list[SwapRequest]] = relationship(
        back_populates="pickup_user",
        foreign_keys="SwapRequest.pickup_user_id",
    )
    swap_requests_resolved: Mapped[list[SwapRequest]] = relationship(
        back_populates="resolver",
        foreign_keys="SwapRequest.resolved_by",
    )
    notifications: Mapped[list[Notification]] = relationship(back_populates="user")
    audit_logs: Mapped[list[AuditLog]] = relationship(back_populates="actor")


class Location(Base):
    """ORM model for work locations."""

    __tablename__ = "locations"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, server_default=text("gen_random_uuid()"))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    iana_timezone: Mapped[str] = mapped_column(String(100), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    user_location_certifications: Mapped[list[UserLocationCertification]] = relationship(back_populates="location")
    manager_location_assignments: Mapped[list[ManagerLocationAssignment]] = relationship(back_populates="location")
    shifts: Mapped[list[Shift]] = relationship(back_populates="location")
    audit_logs: Mapped[list[AuditLog]] = relationship(back_populates="location")


class Skill(Base):
    """ORM model for staff skills."""

    __tablename__ = "skills"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, server_default=text("gen_random_uuid()"))
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)

    user_skills: Mapped[list[UserSkill]] = relationship(back_populates="skill")
    shifts: Mapped[list[Shift]] = relationship(back_populates="required_skill")


class UserSkill(Base):
    """ORM join model for user-to-skill links."""

    __tablename__ = "user_skills"

    user_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    skill_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("skills.id", ondelete="CASCADE"), primary_key=True)

    user: Mapped[User] = relationship(back_populates="user_skills")
    skill: Mapped[Skill] = relationship(back_populates="user_skills")


class UserLocationCertification(Base):
    """ORM join model for user certifications at locations."""

    __tablename__ = "user_location_certifications"

    user_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    location_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("locations.id", ondelete="CASCADE"), primary_key=True)
    certified_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_by: Mapped[str | None] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=True)

    user: Mapped[User] = relationship(back_populates="user_location_certifications", foreign_keys=[user_id])
    location: Mapped[Location] = relationship(back_populates="user_location_certifications")
    revoked_user: Mapped[User | None] = relationship(back_populates="revoked_certs", foreign_keys=[revoked_by])


class ManagerLocationAssignment(Base):
    """ORM join model for manager-to-location ownership."""

    __tablename__ = "manager_location_assignments"

    manager_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    location_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("locations.id", ondelete="CASCADE"), primary_key=True)
    assigned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    manager: Mapped[User] = relationship(back_populates="manager_location_assignments")
    location: Mapped[Location] = relationship(back_populates="manager_location_assignments")


class Availability(Base):
    """ORM model for recurring and exception availability windows."""

    __tablename__ = "availability"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, server_default=text("gen_random_uuid()"))
    user_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    avail_type: Mapped[str] = mapped_column(AvailabilityTypeEnum, nullable=False)
    day_of_week: Mapped[int | None] = mapped_column(Integer, nullable=True)
    specific_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    start_clock: Mapped[str | None] = mapped_column(String(5), nullable=True)
    end_clock: Mapped[str | None] = mapped_column(String(5), nullable=True)
    is_available: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    user: Mapped[User] = relationship(back_populates="availability")


class Shift(Base):
    """ORM model for scheduled shifts."""

    __tablename__ = "shifts"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, server_default=text("gen_random_uuid()"))
    location_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("locations.id"), nullable=False)
    required_skill_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("skills.id"), nullable=False)
    shift_date: Mapped[date] = mapped_column(Date, nullable=False)
    start_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    headcount_needed: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[str] = mapped_column(ShiftStatusEnum, nullable=False, default="draft")
    week_start: Mapped[date] = mapped_column(Date, nullable=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    edit_cutoff_utc: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by: Mapped[str | None] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    location: Mapped[Location] = relationship(back_populates="shifts")
    required_skill: Mapped[Skill] = relationship(back_populates="shifts")
    created_by_user: Mapped[User | None] = relationship(back_populates="created_shifts")
    assignments: Mapped[list[ShiftAssignment]] = relationship(back_populates="shift")


class ShiftAssignment(Base):
    """ORM model for shift assignments."""

    __tablename__ = "shift_assignments"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, server_default=text("gen_random_uuid()"))
    shift_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("shifts.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)
    status: Mapped[str] = mapped_column(AssignmentStatusEnum, nullable=False, default="assigned")
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    assigned_by: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)
    override_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    assigned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    shift: Mapped[Shift] = relationship(back_populates="assignments")
    user: Mapped[User] = relationship(back_populates="user_assignments", foreign_keys=[user_id])
    assigned_by_user: Mapped[User] = relationship(back_populates="assignments_made", foreign_keys=[assigned_by])
    swap_requests: Mapped[list[SwapRequest]] = relationship(
        back_populates="requester_assignment",
        foreign_keys="SwapRequest.requester_assignment_id",
    )
    candidate_swap_requests: Mapped[list[SwapRequest]] = relationship(
        back_populates="candidate_assignment",
        foreign_keys="SwapRequest.candidate_assignment_id",
    )


class SwapRequest(Base):
    """ORM model for shift swap and drop workflows."""

    __tablename__ = "swap_requests"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, server_default=text("gen_random_uuid()"))
    type: Mapped[str] = mapped_column(SwapRequestTypeEnum, nullable=False)
    requester_assignment_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("shift_assignments.id", ondelete="CASCADE"), nullable=False)
    target_user_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=True)
    candidate_assignment_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), ForeignKey("shift_assignments.id", ondelete="CASCADE"), nullable=True)
    pickup_user_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=True)
    status: Mapped[str] = mapped_column(SwapRequestStatusEnum, nullable=False, default="PENDING_ACCEPTEE")
    initiated_by: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_by: Mapped[str | None] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=True)
    resolution_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    requester_assignment: Mapped[ShiftAssignment] = relationship(
        back_populates="swap_requests",
        foreign_keys=[requester_assignment_id],
    )
    candidate_assignment: Mapped[ShiftAssignment | None] = relationship(
        back_populates="candidate_swap_requests",
        foreign_keys=[candidate_assignment_id],
    )
    target_user: Mapped[User | None] = relationship(back_populates="swap_requests_targeted", foreign_keys=[target_user_id])
    pickup_user: Mapped[User | None] = relationship(back_populates="swap_requests_pickup", foreign_keys=[pickup_user_id])
    initiator: Mapped[User] = relationship(back_populates="swap_requests_initiated", foreign_keys=[initiated_by])
    resolver: Mapped[User | None] = relationship(back_populates="swap_requests_resolved", foreign_keys=[resolved_by])


class Notification(Base):
    """ORM model for user notifications."""

    __tablename__ = "notifications"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, server_default=text("gen_random_uuid()"))
    user_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    type: Mapped[str] = mapped_column(String(60), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped[User] = relationship(back_populates="notifications")


class AuditLog(Base):
    """ORM model for mutation audit logs."""

    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, server_default=text("gen_random_uuid()"))
    actor_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)
    action_type: Mapped[str] = mapped_column(String(60), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(60), nullable=False)
    entity_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False)
    before_state: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    after_state: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    location_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), ForeignKey("locations.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    actor: Mapped[User] = relationship(back_populates="audit_logs")
    location: Mapped[Location | None] = relationship(back_populates="audit_logs")
