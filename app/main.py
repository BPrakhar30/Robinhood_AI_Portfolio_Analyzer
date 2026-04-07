"""FastAPI application entry: middleware, routers, and global exception handling.

Startup/shutdown run through the ``lifespan`` context manager (e.g. dev-only
``init_db``). CORS allows all origins (``*``) only when ``debug`` is true;
production must use an explicit allowlist.

``AppException`` and a catch-all ``Exception`` handler both return sanitized
JSON so clients never see raw stack traces. OpenAPI UIs (``docs_url``,
``redoc_url``) are disabled when not in debug mode.

Added: 2026-04-03
"""
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.database.engine import init_db
from app.auth.router import router as auth_router
from app.broker_integrations.router import router as broker_router
from app.utils.exceptions import AppException
from app.utils.logging import get_logger

logger = get_logger("main")
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(
        "Application starting",
        extra={"event": "app_start", "env": settings.app_env.value},
    )
    if settings.app_env.value == "development":
        await init_db()
        logger.info("Database tables created (development mode)")
    yield
    logger.info("Application shutting down", extra={"event": "app_shutdown"})


app = FastAPI(
    title=settings.app_name,
    description="AI Portfolio Copilot for Robinhood users — "
    "securely connects accounts, analyzes portfolios, and provides AI-driven insights.",
    version="0.1.0",
    lifespan=lifespan,
    # /docs and /redoc off in production to reduce exposed surface.
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
)

# Debug: permissive CORS for local frontends. Production: set real origins (empty list here is a safe default).
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.debug else [],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    """Global handler that wraps AppException subclasses into standard API responses."""
    logger.error(
        f"AppException: {exc.message}",
        extra={
            "event": "app_error",
            "status_code": exc.status_code,
            "details": exc.details,
        },
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "status": "error",
            "data": None,
            "error_message": exc.message,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    """Catch-all handler — never return raw exceptions to frontend."""
    logger.error(
        f"Unhandled exception: {exc}",
        extra={"event": "unhandled_error", "error": str(exc)},
    )
    return JSONResponse(
        status_code=500,
        content={
            "status": "error",
            "data": None,
            "error_message": "An internal error occurred. Please try again later.",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )


# ──────────────────────────────── API Routes ────────────────────────────────

app.include_router(auth_router, prefix="/api/v1")
app.include_router(broker_router, prefix="/api/v1")


# ──────────────────────────────── Health & Status ────────────────────────────────


@app.get("/health")
async def health_check():
    """Basic health check endpoint for deployment monitoring."""
    return {
        "status": "healthy",
        "service": settings.app_name,
        "environment": settings.app_env.value,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/status")
async def status_check():
    """Detailed status endpoint with component health."""
    db_healthy = True
    try:
        from app.database.engine import async_engine

        async with async_engine.connect() as conn:
            await conn.execute(__import__("sqlalchemy").text("SELECT 1"))
    except Exception:
        db_healthy = False

    return {
        "status": "healthy" if db_healthy else "degraded",
        "components": {
            "api": "healthy",
            "database": "healthy" if db_healthy else "unhealthy",
        },
        "version": "0.1.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
