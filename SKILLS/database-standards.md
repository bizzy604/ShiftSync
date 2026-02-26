# Database Engineering Standards
## ShiftSync — SQLAlchemy 2.0 (async) + Alembic + PostgreSQL 15

---

## Repository Pattern — The Only Way to Access the Database

No SQLAlchemy session imports outside of repository files and the infrastructure layer.
Services declare Protocol interfaces; repositories implement them.

### Protocol First

```python
# modules/assignments/repository.py

from typing import Protocol
from uuid import UUID
from app.modules.assignments.schemas import AssignmentProposal, DateRange
from app.modules.assignments.models import Assignment
from constraint_engine.types import ConstraintContext


class IAssignmentRepository(Protocol):
    """Data access contract for the assignment module.

    PATTERN: Repository — isolates SQLAlchemy from business logic.

    Enables:
        1. AsyncMock test doubles in unit tests without a real database.
        2. Swapping SQLAlchemy for another ORM without changing the service layer.
        3. Single place to add logging or caching at the data layer.
    """

    async def load_constraint_context(self, proposal: AssignmentProposal) -> ConstraintContext:
        """Load all data needed by the constraint engine in a single round trip.

        Fetches: user certifications, skills, availability, existing assignments ±24h.

        Args:
            proposal: The proposed assignment (shift + user IDs and shift details).
        """
        ...

    async def create(self, proposal: AssignmentProposal, actor_id: UUID) -> Assignment:
        """Insert an assignment record inside the active session transaction.

        Must be called within a session.begin() block that holds a
        pg_advisory_xact_lock on the user_id.

        Args:
            proposal:  Full assignment details.
            actor_id:  Manager/admin performing the action (stored in audit trail).

        Raises:
            sqlalchemy.exc.IntegrityError: On UNIQUE constraint violation —
                last-resort double-booking prevention at the database level.
        """
        ...

    async def find_active_by_user_and_range(
        self, user_id: UUID, date_range: DateRange
    ) -> list[Assignment]:
        """Return all active (status='assigned') assignments for a user within [start, end).

        Used by the constraint engine for overlap detection and rest-period checks.
        The ±24h window relative to the proposed shift covers both checks.
        """
        ...
```

---

## SQLAlchemy ORM Models

```python
# modules/assignments/models.py

import uuid
from datetime import datetime
from sqlalchemy import String, ForeignKey, Integer, DateTime, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from app.infrastructure.database import Base


class ShiftAssignment(Base):
    """ORM model for the shift_assignments table.

    Ownership: The assignments module owns this table.
    Other modules read from it via repository interfaces, never directly.

    Attributes:
        version: Optimistic lock counter. Incremented on every status transition.
                 If a concurrent update sets version=N+1 before ours, our WHERE
                 version=N update affects 0 rows, signalling a conflict.
    """

    __tablename__ = "shift_assignments"
    __table_args__ = (
        # WHY: Database-level UNIQUE guard is the last line of defence against
        # double-booking. Even if the advisory lock or constraint engine has a bug,
        # the DB rejects a second assignment for the same shift + user combination.
        UniqueConstraint("shift_id", "user_id", name="uq_shift_assignments_shift_user"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    shift_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("shifts.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="assigned",
        comment="assigned | swap_pending | dropped | removed"
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    assigned_by: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default="now()"
    )
    override_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    shift: Mapped["Shift"] = relationship("Shift", back_populates="assignments")
    user: Mapped["User"] = relationship("User", back_populates="assignments")
```

---

## Session Management

```python
# infrastructure/database.py

from collections.abc import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

engine = create_async_engine(
    settings.database_url,
    pool_size=20,
    max_overflow=10,
    echo=settings.debug,
)

AsyncSessionLocal = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


class Base(DeclarativeBase):
    """Shared declarative base for all SQLAlchemy ORM models."""
    pass


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields a per-request async DB session.

    Session is automatically closed after the request completes.
    Transaction management (begin/commit/rollback) is handled in the service layer,
    NOT here — the session is yielded without an active transaction.
    """
    async with AsyncSessionLocal() as session:
        yield session
```

---

## Migration Standards (Alembic)

### File Naming

```
alembic/versions/
├── 001_initial_schema.py
├── 002_add_swap_requests.py
├── 003_add_audit_logs.py
└── 004_add_notification_preferences.py
```

### Rules for Every Migration

1. **Always reversible** — every `upgrade()` has a complete `downgrade()`
2. **Use `CREATE INDEX CONCURRENTLY`** — via `postgresql_concurrently=True` to avoid table locks
3. **Never rename columns in one step** — add new column, migrate data, drop old in a later migration
4. **Always add `NOT NULL` with a `server_default`** — never add nullable columns without justification

```python
# alembic/versions/004_add_notification_preferences.py

"""Add notification_pref column to users table.

Revision ID: 004
Down revision: 003
"""

from alembic import op
import sqlalchemy as sa


def upgrade() -> None:
    """Add notification_pref with a safe default for existing rows."""
    op.add_column(
        "users",
        sa.Column(
            "notification_pref",
            sa.String(20),
            nullable=False,
            server_default="in_app",
            comment="in_app | in_app_email",
        ),
    )
    op.create_check_constraint(
        "ck_users_notification_pref",
        "users",
        "notification_pref IN ('in_app', 'in_app_email')",
    )
    # WHY: Partial index — only NULL read_at rows are 'unread'.
    # Avoids scanning all notifications for an unread count query.
    op.create_index(
        "idx_notifications_unread",
        "notifications",
        ["user_id", "read_at"],
        postgresql_where=sa.text("read_at IS NULL"),
        postgresql_concurrently=True,  # Avoids table lock during index build
    )


def downgrade() -> None:
    op.drop_index("idx_notifications_unread", table_name="notifications")
    op.drop_constraint("ck_users_notification_pref", "users", type_="check")
    op.drop_column("users", "notification_pref")
```

---

## Query Patterns

### Never Load What You Don't Need

```python
from sqlalchemy import select
from sqlalchemy.orm import load_only, joinedload

# ❌ WRONG — loads entire User with all relationships
user = await session.get(User, user_id)

# ✅ CORRECT — load only the columns the constraint engine needs
stmt = (
    select(User)
    .where(User.id == user_id)
    .options(
        load_only(User.id, User.email, User.role, User.home_timezone),
        joinedload(User.skills).load_only(UserSkill.skill_id),
        joinedload(User.location_certifications.and_(
            LocationCertification.revoked_at.is_(None)
        )).load_only(LocationCertification.location_id),
        joinedload(User.availability),
    )
)
user = (await session.execute(stmt)).scalar_one()
```

### Raw SQL for PostgreSQL-Specific Features

```python
# Use text() only for features SQLAlchemy doesn't abstract:
# advisory locks, AT TIME ZONE queries, EXTRACT with timezone

# Advisory lock — always inside a session.begin() block
await session.execute(
    text("SELECT pg_advisory_xact_lock(hashtext(:user_id))"),
    {"user_id": str(user_id)},
)

# Premium shift detection using AT TIME ZONE
result = await session.execute(
    text("""
        SELECT
            sa.user_id,
            COUNT(*) AS shift_count
        FROM shift_assignments sa
        JOIN shifts s ON s.id = sa.shift_id
        JOIN locations l ON l.id = s.location_id
        WHERE
            s.location_id = :location_id
            AND s.shift_date BETWEEN :start_date AND :end_date
            AND sa.status = 'assigned'
            -- Premium: Friday(5) or Saturday(6), 17:00+ in location timezone
            AND EXTRACT(DOW FROM s.start_utc AT TIME ZONE l.iana_timezone) IN (5, 6)
            AND EXTRACT(HOUR FROM s.start_utc AT TIME ZONE l.iana_timezone) >= 17
        GROUP BY sa.user_id
    """),
    {"location_id": str(location_id), "start_date": start_date, "end_date": end_date},
)
rows = result.mappings().all()
```

### Optimistic Locking for Swap State Transitions

```python
async def transition_status(
    self,
    swap_request_id: UUID,
    from_status: SwapStatus,
    to_status: SwapStatus,
    expected_version: int,
) -> SwapRequest:
    """Transition a swap request to a new status using optimistic locking.

    Prevents two actors (e.g. two managers approving simultaneously) from
    transitioning the same request at the same time.

    Args:
        swap_request_id:  UUID of the swap request to transition.
        from_status:      The current expected status (guard condition).
        to_status:        The desired next status.
        expected_version: The version the caller read — used as the lock guard.

    Returns:
        The updated SwapRequest with incremented version.

    Raises:
        OptimisticLockError: If 0 rows were updated (version mismatch —
            another actor already modified the record).
    """
    from sqlalchemy import update

    # WHY: WHERE on both status and version — if 0 rows updated, someone else
    # already changed it. We detect this and raise rather than silently overwriting.
    stmt = (
        update(SwapRequest)
        .where(
            SwapRequest.id == swap_request_id,
            SwapRequest.status == from_status,
            SwapRequest.version == expected_version,  # Optimistic lock guard
        )
        .values(status=to_status, version=expected_version + 1)
        .returning(SwapRequest)
    )
    result = (await self._session.execute(stmt)).scalar_one_or_none()

    if result is None:
        raise OptimisticLockError(swap_request_id, "swap_request", expected_version)

    return result
```

---

## SQLAlchemy Type Helpers

```python
# shared/types/db_types.py

from datetime import datetime
from dataclasses import dataclass


@dataclass(frozen=True)
class DateRange:
    """UTC date range for time-bounded queries.

    Both bounds use half-open semantics: [start, end).
    start is inclusive, end is exclusive.

    Example:
        range = DateRange(start=datetime(2025, 8, 11), end=datetime(2025, 8, 18))
        # Covers all of the week Mon Aug 11 – Sun Aug 17 inclusive.
    """
    start: datetime
    end: datetime
```
