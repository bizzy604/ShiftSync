"""
MODULE: /apps/api/app/main.py

FUNCTION:
    Implements module logic for `main`.

DEPENDENCIES:
    - (No in-repo dependents detected.)

IMPORTANCE:
    This module is important for maintainability and predictable behavior of `main`.
"""

from contextlib import asynccontextmanager
import asyncio

from fastapi import FastAPI
from fastapi.requests import Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.router import api_router
from app.core.config import get_settings
from app.core.database import connect_db, disconnect_db
from app.core.errors import AppError
from app.core.session_store import SessionStore
from app.services.assignment_lock import AssignmentLockManager
from app.services.drop_expiry_worker import run_drop_expiry_worker
from app.services.realtime import RealtimeManager


def _build_cors_origins() -> list[str]:
    settings = get_settings()
    origins = list(settings.cors_origins)
    if settings.app_env.lower() != "production":
        origins.extend(
            [
                "http://localhost:5173",
                "http://127.0.0.1:5173",
                "http://localhost:8000",
                "http://127.0.0.1:8000",
            ]
        )
    deduped: list[str] = []
    for origin in origins:
        if origin and origin not in deduped:
            deduped.append(origin)
    return deduped


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan.
    
    Args:
        app: Input parameter `app` used by this operation.
    """
    settings = get_settings()
    app.state.session_store = SessionStore(settings.redis_url)
    app.state.ws_manager = RealtimeManager()
    app.state.assignment_locks = AssignmentLockManager()
    app.state.drop_expiry_stop_event = asyncio.Event()
    app.state.drop_expiry_task = None

    await app.state.session_store.connect()
    await connect_db()
    app.state.drop_expiry_task = asyncio.create_task(run_drop_expiry_worker(app))
    yield
    app.state.drop_expiry_stop_event.set()
    if app.state.drop_expiry_task:
        try:
            await asyncio.wait_for(app.state.drop_expiry_task, timeout=5)
        except Exception:
            app.state.drop_expiry_task.cancel()
    await disconnect_db()
    await app.state.session_store.close()

settings = get_settings()
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_build_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.exception_handler(AppError)
async def handle_app_error(_: Request, exc: AppError) -> JSONResponse:
    """Handle app error.
    
    Args:
        _: Input parameter `_` used by this operation.
        exc: Input parameter `exc` used by this operation.
    
    Returns:
        Structured JSON error/response payload.
    """
    details = {"error": {"code": exc.code, "message": exc.message}}
    if exc.details:
        details["error"]["details"] = exc.details
    return JSONResponse(status_code=exc.status_code, content=details)


@app.get("/health")
async def health() -> dict[str, str]:
    """Health.
    
    Returns:
        Structured dictionary result.
    """
    return {"status": "ok"}
