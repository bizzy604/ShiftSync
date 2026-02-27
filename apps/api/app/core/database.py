from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any, AsyncIterator
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from sqlalchemy import and_, delete as sa_delete, false, func, or_, select, text, update as sa_update
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.inspection import inspect
from sqlalchemy.orm import selectinload

from app.core.config import get_settings
from app.core.models import (
    AuditLog,
    Availability,
    Location,
    ManagerLocationAssignment,
    Notification,
    Shift,
    ShiftAssignment,
    Skill,
    SwapRequest,
    User,
    UserLocationCertification,
    UserSkill,
)


def _to_async_url(url: str) -> str:
    """Convert a PostgreSQL DSN to the SQLAlchemy asyncpg form."""
    normalized = url
    if url.startswith("postgresql://"):
        normalized = f"postgresql+asyncpg://{url[len('postgresql://'):]}"
    elif url.startswith("postgres://"):
        normalized = f"postgresql+asyncpg://{url[len('postgres://'):]}"

    # asyncpg expects `ssl`, while many hosted URLs provide `sslmode`.
    parsed = urlsplit(normalized)
    if parsed.scheme != "postgresql+asyncpg":
        return normalized

    query_pairs = parse_qsl(parsed.query, keep_blank_values=True)
    has_ssl = any(key.lower() == "ssl" for key, _ in query_pairs)
    sslmode_value: str | None = None
    filtered_pairs: list[tuple[str, str]] = []

    for key, value in query_pairs:
        if key.lower() == "sslmode":
            sslmode_value = value
            continue
        filtered_pairs.append((key, value))

    if not has_ssl and sslmode_value is not None:
        filtered_pairs.append(("ssl", sslmode_value))

    rebuilt_query = urlencode(filtered_pairs, doseq=True)
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, rebuilt_query, parsed.fragment))


settings = get_settings()
engine = create_async_engine(
    _to_async_url(settings.database_url),
    pool_pre_ping=True,
)
AsyncSessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)


MODEL_REGISTRY: dict[str, type] = {
    "user": User,
    "location": Location,
    "skill": Skill,
    "userskill": UserSkill,
    "userlocationcertification": UserLocationCertification,
    "managerlocationassignment": ManagerLocationAssignment,
    "availability": Availability,
    "shift": Shift,
    "shiftassignment": ShiftAssignment,
    "swaprequest": SwapRequest,
    "notification": Notification,
    "auditlog": AuditLog,
}


def _is_operator_map(value: Any) -> bool:
    return isinstance(value, dict) and any(key in value for key in ("in", "not", "lt", "lte", "gt", "gte"))


def _build_single_clause(column: Any, value: Any) -> Any:
    if not isinstance(value, dict) or not _is_operator_map(value):
        if value is None:
            return column.is_(None)
        return column == value

    clauses: list[Any] = []
    for op, operand in value.items():
        if op == "in":
            if not operand:
                clauses.append(false())
            else:
                clauses.append(column.in_(operand))
        elif op == "not":
            if isinstance(operand, dict) and "in" in operand:
                in_values = operand["in"] or []
                clauses.append(~column.in_(in_values) if in_values else column.is_not(None))
            elif operand is None:
                clauses.append(column.is_not(None))
            else:
                clauses.append(column != operand)
        elif op == "lt":
            clauses.append(column < operand)
        elif op == "lte":
            clauses.append(column <= operand)
        elif op == "gt":
            clauses.append(column > operand)
        elif op == "gte":
            clauses.append(column >= operand)
        else:
            raise ValueError(f"Unsupported filter operator: {op}")

    if not clauses:
        raise ValueError("Empty operator map is not allowed.")
    return and_(*clauses)


def _build_filters(model: type, where: dict[str, Any] | None) -> list[Any]:
    if not where:
        return []

    mapper = inspect(model)
    filters: list[Any] = []
    for key, value in where.items():
        if key == "AND" and isinstance(value, list):
            nested = [and_(*_build_filters(model, item)) for item in value]
            if nested:
                filters.append(and_(*nested))
            continue
        if key == "OR" and isinstance(value, list):
            nested = [and_(*_build_filters(model, item)) for item in value]
            if nested:
                filters.append(or_(*nested))
            continue

        if key in mapper.relationships:
            raise ValueError(f"Relationship filters are not supported in this adapter: {key}")

        if key not in mapper.columns:
            if isinstance(value, dict):
                for sub_key, sub_value in value.items():
                    if sub_key not in mapper.columns:
                        raise ValueError(f"Unknown field in where clause: {sub_key}")
                    column = getattr(model, sub_key)
                    filters.append(_build_single_clause(column, sub_value))
                continue
            raise ValueError(f"Unknown field in where clause: {key}")

        column = getattr(model, key)
        filters.append(_build_single_clause(column, value))
    return filters


def _build_load_options(model: type, include: dict[str, Any] | None) -> list[Any]:
    if not include:
        return []

    mapper = inspect(model)
    options: list[Any] = []
    for rel_name, rel_spec in include.items():
        if rel_name not in mapper.relationships:
            continue
        loader = selectinload(getattr(model, rel_name))
        if isinstance(rel_spec, dict):
            nested_include = rel_spec.get("include")
            if isinstance(nested_include, dict):
                nested_model = mapper.relationships[rel_name].mapper.class_
                nested_options = _build_load_options(nested_model, nested_include)
                if nested_options:
                    loader = loader.options(*nested_options)
        options.append(loader)
    return options


def _apply_order(stmt: Any, model: type, order: dict[str, Any] | None) -> Any:
    if not order:
        return stmt
    
    mapper = inspect(model)
    for field, direction in order.items():
        if field in mapper.relationships and isinstance(direction, dict):
            # Support one level of nested ordering via join
            rel = mapper.relationships[field]
            nested_model = rel.mapper.class_
            stmt = stmt.join(getattr(model, field))
            for sub_field, sub_direction in direction.items():
                column = getattr(nested_model, sub_field)
                stmt = stmt.order_by(column.desc() if str(sub_direction).lower() == "desc" else column.asc())
        else:
            column = getattr(model, field)
            stmt = stmt.order_by(column.desc() if str(direction).lower() == "desc" else column.asc())
    return stmt


def _normalize_data(model: type, data: dict[str, Any]) -> dict[str, Any]:
    mapper = inspect(model)
    normalized: dict[str, Any] = {}

    for key, value in data.items():
        if key in mapper.relationships and isinstance(value, dict) and "connect" in value:
            rel = mapper.relationships[key]
            local_columns = list(rel.local_columns)
            if len(local_columns) != 1:
                raise ValueError(f"Only single-column relationship connects are supported for {key}.")
            connect_payload = value.get("connect", {})
            if not isinstance(connect_payload, dict) or not connect_payload:
                raise ValueError(f"Invalid connect payload for {key}.")
            normalized[local_columns[0].key] = next(iter(connect_payload.values()))
            continue
        if key in mapper.relationships:
            continue
        normalized[key] = value

    return normalized


class ModelAccessor:
    """Prisma-like model accessor backed by SQLAlchemy ORM."""

    def __init__(self, model: type, client: "DatabaseClient") -> None:
        self._model = model
        self._client = client

    async def _fetch_one(
        self,
        session: AsyncSession,
        where: dict[str, Any] | None,
        include: dict[str, Any] | None = None,
    ) -> Any | None:
        stmt = select(self._model)
        filters = _build_filters(self._model, where)
        if filters:
            stmt = stmt.where(and_(*filters))
        include_options = _build_load_options(self._model, include)
        if include_options:
            stmt = stmt.options(*include_options)
        stmt = stmt.limit(1)
        result = await session.execute(stmt)
        return result.scalars().unique().one_or_none()

    async def _fetch_many(
        self,
        session: AsyncSession,
        where: dict[str, Any] | None,
        include: dict[str, Any] | None = None,
        order: dict[str, str] | None = None,
        skip: int | None = None,
        take: int | None = None,
    ) -> list[Any]:
        stmt = select(self._model)
        filters = _build_filters(self._model, where)
        if filters:
            stmt = stmt.where(and_(*filters))
        include_options = _build_load_options(self._model, include)
        if include_options:
            stmt = stmt.options(*include_options)
        stmt = _apply_order(stmt, self._model, order)
        if skip:
            stmt = stmt.offset(skip)
        if take:
            stmt = stmt.limit(take)
        result = await session.execute(stmt)
        return list(result.scalars().unique().all())

    async def _reload_instance(self, session: AsyncSession, instance: Any, include: dict[str, Any] | None) -> Any:
        mapper = inspect(self._model)
        where = {column.key: getattr(instance, column.key) for column in mapper.primary_key}
        row = await self._fetch_one(session, where=where, include=include)
        if row is None:
            raise NoResultFound(f"Unable to reload {self._model.__name__}.")
        return row

    async def find_unique(self, *, where: dict[str, Any], include: dict[str, Any] | None = None) -> Any | None:
        async with self._client.session_scope() as session:
            return await self._fetch_one(session, where=where, include=include)

    async def find_first(self, *, where: dict[str, Any], include: dict[str, Any] | None = None) -> Any | None:
        return await self.find_unique(where=where, include=include)

    async def find_many(
        self,
        *,
        where: dict[str, Any] | None = None,
        include: dict[str, Any] | None = None,
        order: dict[str, str] | None = None,
        skip: int | None = None,
        take: int | None = None,
    ) -> list[Any]:
        async with self._client.session_scope() as session:
            return await self._fetch_many(
                session,
                where=where,
                include=include,
                order=order,
                skip=skip,
                take=take,
            )

    async def count(self, *, where: dict[str, Any] | None = None) -> int:
        async with self._client.session_scope() as session:
            stmt = select(func.count()).select_from(self._model)
            filters = _build_filters(self._model, where)
            if filters:
                stmt = stmt.where(and_(*filters))
            result = await session.execute(stmt)
            return int(result.scalar_one())

    async def create(self, *, data: dict[str, Any], include: dict[str, Any] | None = None) -> Any:
        async with self._client.session_scope() as session:
            instance = self._model(**_normalize_data(self._model, data))
            session.add(instance)
            await session.flush()
            await session.refresh(instance)
            if include:
                return await self._reload_instance(session, instance, include)
            return instance

    async def create_many(self, *, data: list[dict[str, Any]]) -> dict[str, int]:
        async with self._client.session_scope() as session:
            for item in data:
                session.add(self._model(**_normalize_data(self._model, item)))
            await session.flush()
            return {"count": len(data)}

    async def update(self, *, where: dict[str, Any], data: dict[str, Any], include: dict[str, Any] | None = None) -> Any:
        async with self._client.session_scope() as session:
            instance = await self._fetch_one(session, where=where)
            if instance is None:
                raise NoResultFound(f"{self._model.__name__} not found for update.")
            for key, value in _normalize_data(self._model, data).items():
                setattr(instance, key, value)
            await session.flush()
            await session.refresh(instance)
            if include:
                return await self._reload_instance(session, instance, include)
            return instance

    async def update_many(self, *, where: dict[str, Any] | None = None, data: dict[str, Any]) -> dict[str, int]:
        async with self._client.session_scope() as session:
            stmt = sa_update(self._model).values(**_normalize_data(self._model, data))
            filters = _build_filters(self._model, where)
            if filters:
                stmt = stmt.where(and_(*filters))
            result = await session.execute(stmt)
            return {"count": int(result.rowcount or 0)}

    async def delete(self, *, where: dict[str, Any]) -> Any:
        async with self._client.session_scope() as session:
            instance = await self._fetch_one(session, where=where)
            if instance is None:
                raise NoResultFound(f"{self._model.__name__} not found for delete.")
            await session.delete(instance)
            await session.flush()
            return instance

    async def delete_many(self, *, where: dict[str, Any] | None = None) -> dict[str, int]:
        async with self._client.session_scope() as session:
            stmt = sa_delete(self._model)
            filters = _build_filters(self._model, where)
            if filters:
                stmt = stmt.where(and_(*filters))
            result = await session.execute(stmt)
            return {"count": int(result.rowcount or 0)}

    async def upsert(self, *, where: dict[str, Any], data: dict[str, Any]) -> Any:
        async with self._client.session_scope() as session:
            instance = await self._fetch_one(session, where=where)
            if instance is None:
                payload = _normalize_data(self._model, data.get("create", {}))
                instance = self._model(**payload)
                session.add(instance)
                await session.flush()
                await session.refresh(instance)
                return instance

            for key, value in _normalize_data(self._model, data.get("update", {})).items():
                setattr(instance, key, value)
            await session.flush()
            await session.refresh(instance)
            return instance


class TransactionClient:
    """Context manager that provides a transactional SQLAlchemy-backed client."""

    def __init__(self) -> None:
        self._session: AsyncSession | None = None

    async def __aenter__(self) -> "DatabaseClient":
        self._session = AsyncSessionLocal()
        await self._session.begin()
        return DatabaseClient(session=self._session)

    async def __aexit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        if self._session is None:
            return
        try:
            if exc_type is None:
                await self._session.commit()
            else:
                await self._session.rollback()
        finally:
            await self._session.close()


class DatabaseClient:
    """Prisma-compatible facade over SQLAlchemy models and sessions."""

    def __init__(self, session: AsyncSession | None = None) -> None:
        self._session = session
        for name, model in MODEL_REGISTRY.items():
            setattr(self, name, ModelAccessor(model, self))

    @asynccontextmanager
    async def session_scope(self) -> AsyncIterator[AsyncSession]:
        if self._session is not None:
            yield self._session
            return
        async with AsyncSessionLocal() as session:
            async with session.begin():
                yield session

    def tx(self) -> TransactionClient:
        return TransactionClient()

    async def connect(self) -> None:
        await connect_db()

    async def disconnect(self) -> None:
        await disconnect_db()

    def is_connected(self) -> bool:
        return True


prisma = DatabaseClient()


async def connect_db() -> None:
    """Validate database connectivity on app startup."""
    async with engine.connect() as conn:
        await conn.execute(text("SELECT 1"))


async def disconnect_db() -> None:
    """Dispose SQLAlchemy engine and its connection pool."""
    await engine.dispose()


async def get_session() -> AsyncIterator[AsyncSession]:
    """Yield a request-scoped async SQLAlchemy session."""
    async with AsyncSessionLocal() as session:
        yield session
