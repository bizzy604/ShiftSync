from contextlib import asynccontextmanager
import asyncio

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import get_settings
from app.core.database import connect_db, disconnect_db
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


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
