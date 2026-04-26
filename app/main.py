"""FastAPI entry: middleware, routers, global exception handling.

Permissive CORS and OpenAPI UIs are only enabled in debug mode. Both
exception handlers return sanitized JSON so clients never see stack traces.
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
from app.portfolio_engine.router import router as portfolio_router
from app.markets.router import router as markets_router
from app.stocks.router import router as stocks_router
from app.ai_agent.router import router as assistant_router
from app.chat.router import router as chat_router
from app.utils.exceptions import AppException
from app.utils.logging import get_logger
from app.utils.observability import setup_logfire

logger = get_logger("main")
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Logfire is set up here (not at import time) so FastAPI is fully
    # constructed before instrumentation wraps its routes.
    setup_logfire(service_name="robinhood-ai-backend", app=app)
    logger.info(
        "Application starting",
        extra={
            "event": "app_start",
            "env": settings.app_env.value,
            "logfire": bool(settings.logfire_token),
        },
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
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
)

_DEV_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:3001",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_DEV_ORIGINS if settings.debug else [settings.frontend_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    """Wrap AppException subclasses into a standard API response."""
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
    """Catch-all — never leak raw exceptions to the client."""
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
app.include_router(portfolio_router, prefix="/api/v1")
app.include_router(markets_router, prefix="/api/v1")
app.include_router(stocks_router, prefix="/api/v1")
app.include_router(assistant_router, prefix="/api/v1")
app.include_router(chat_router, prefix="/api/v1")


# ──────────────────────────────── Health & Status ────────────────────────────────


@app.get("/health")
async def health_check():
    """Basic health check for deployment monitoring."""
    return {
        "status": "healthy",
        "service": settings.app_name,
        "environment": settings.app_env.value,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/status")
async def status_check():
    """Component-level health check."""
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
