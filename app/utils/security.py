"""Security middleware: rate limiting and HTTP security headers.

Rate limits use in-memory storage by default. Swap to Redis via
``settings.redis_url`` for multi-process / multi-container deployments.
"""

from __future__ import annotations

from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.config import get_settings

settings = get_settings()


# ---------------------------------------------------------------------------
# Rate Limiter (per-IP by default)
# ---------------------------------------------------------------------------

def _rate_limit_storage_uri() -> str:
    """Use Redis only when explicitly configured; fall back to in-memory.

    The default redis_url value ("redis://localhost:6379/0") is a placeholder
    for local dev  -  using it unconditionally causes a hard crash when Redis
    is not running. Only switch to Redis when the URL is overridden via env.
    """
    default = "redis://localhost:6379/0"
    url = settings.redis_url or ""
    if url and url != default:
        return url
    return "memory://"


limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200/minute"],
    storage_uri=_rate_limit_storage_uri(),
)


def rate_limit_exceeded_handler(_request: Request, exc: RateLimitExceeded) -> Response:
    return JSONResponse(
        status_code=429,
        content={
            "status": "error",
            "data": None,
            "error_message": "Too many requests. Please slow down and try again shortly.",
        },
    )


# Decorators for specific endpoint limits (import in routers):
#   from app.utils.security import limiter
#   @limiter.limit("5/minute")


# ---------------------------------------------------------------------------
# Security Headers Middleware
# ---------------------------------------------------------------------------

_SECURITY_HEADERS: dict[str, str] = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "X-XSS-Protection": "1; mode=block",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
}

if not settings.debug:
    _SECURITY_HEADERS["Strict-Transport-Security"] = (
        "max-age=63072000; includeSubDomains; preload"
    )
    _SECURITY_HEADERS["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: https:; "
        "connect-src 'self' https:; "
        "font-src 'self'; "
        "frame-ancestors 'none'"
    )


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)
        for header, value in _SECURITY_HEADERS.items():
            response.headers.setdefault(header, value)
        return response
