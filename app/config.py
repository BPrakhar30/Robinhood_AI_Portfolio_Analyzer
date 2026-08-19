"""Application settings loaded from environment via pydantic-settings.

``get_settings()`` is memoized so a single Settings instance is shared
process-wide. Defaults are for local dev; production must override via env.
"""

from pathlib import Path
from urllib.parse import urlparse
from pydantic_settings import BaseSettings
from pydantic import Field
from functools import lru_cache
from enum import Enum

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_ENV_FILE = _PROJECT_ROOT / ".env"


class Environment(str, Enum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


_INSECURE_DEFAULTS = frozenset(
    {
        "change-me-in-production",
        "",
        "secret",
        "password",
        "your-secret-key-here-change-in-production",
        "your-jwt-secret-key-change-in-production",
    }
)

# Symmetric HMAC algorithms only  -  prevents downgrade tricks (e.g. "none")
# from sneaking in via a misconfigured JWT_ALGORITHM env var.
_ALLOWED_JWT_ALGORITHMS = frozenset({"HS256", "HS384", "HS512"})


class Settings(BaseSettings):
    app_name: str = "RobinhoodAICopilot"
    app_env: Environment = Environment.DEVELOPMENT
    debug: bool = False
    secret_key: str = "change-me-in-production"

    # Database (PostgreSQL via docker-compose; override via .env or environment)
    database_url: str = (
        "postgresql+asyncpg://postgres:postgres@localhost:5432/robinhood_ai"
    )
    database_url_sync: str = (
        "postgresql://postgres:postgres@localhost:5432/robinhood_ai"
    )

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # JWT
    jwt_secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30

    # Encryption
    encryption_key: str = ""

    # Robinhood
    robinhood_client_id: str = ""
    robinhood_device_token: str = ""

    # Plaid
    plaid_client_id: str = ""
    plaid_secret: str = ""
    plaid_env: str = "sandbox"

    # Market Data
    polygon_api_key: str = ""
    finnhub_api_key: str = ""
    yahoo_finance_fallback: bool = True
    # Fetch live quotes for CSV/Excel imports that omit current_price
    csv_live_price_enrichment: bool = True

    # Email / SMTP
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from_email: str = "noreply@robinhoodai.local"
    smtp_use_tls: bool = True

    # Frontend URL (for email verification links)
    frontend_url: str = "http://localhost:3000"

    # Email verification token lifetime (hours)
    email_verification_token_hours: int = 24

    # LLM
    openai_api_key: str = ""
    ollama_base_url: str = "http://localhost:11434"

    # AI Assistant (PydanticAI + Google Gemini, via Google AI Studio free tier)
    google_api_key: str = ""
    google_model: str = "gemini-2.5-flash"

    # Legacy OpenRouter fields (kept for backwards-compat; unused if google_api_key is set)
    openrouter_api_key: str = ""
    openrouter_model: str = "meta-llama/llama-3.3-70b-instruct:free"

    # MCP portfolio tools (Streamable HTTP). Compose default; override for bare-metal.
    mcp_server_url: str = "http://mcp-server:8765/mcp"

    # Observability (Pydantic Logfire, built on OpenTelemetry)
    # Leave token empty to disable cloud shipping  -  Logfire becomes a no-op locally.
    # Get a free token at https://logfire.pydantic.dev (10M spans/month free tier).
    logfire_token: str = ""
    # Also emit spans to the console in dev for quick inspection without the web UI.
    logfire_console: bool = True
    # Scrub user questions / LLM prompts from Logfire exports. Turn off for debugging.
    logfire_scrub_prompts: bool = False
    # Self-hosted OpenTelemetry endpoint (traces + metrics + logs via OTLP/HTTP).
    # When set, Logfire stops shipping to its cloud and exports here instead
    # (e.g. http://localhost:4318 for the local collector, or the collector
    # service URL in the observability compose). Empty = Logfire cloud behavior.
    otel_exporter_otlp_endpoint: str = ""

    model_config = {
        "env_file": str(_ENV_FILE),
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


@lru_cache()
def get_settings() -> Settings:
    s = Settings()
    if s.jwt_algorithm not in _ALLOWED_JWT_ALGORITHMS:
        raise RuntimeError(
            f"JWT_ALGORITHM must be one of {sorted(_ALLOWED_JWT_ALGORITHMS)}, "
            f"got {s.jwt_algorithm!r}"
        )
    if s.app_env != Environment.DEVELOPMENT:
        errors: list[str] = []
        if s.secret_key in _INSECURE_DEFAULTS:
            errors.append("SECRET_KEY is set to an insecure default")
        if s.jwt_secret_key in _INSECURE_DEFAULTS:
            errors.append("JWT_SECRET_KEY is set to an insecure default")
        if not s.encryption_key:
            errors.append("ENCRYPTION_KEY is not set")
        if s.debug:
            errors.append("DEBUG=true must not be used outside development")
        parsed_frontend = urlparse(s.frontend_url)
        if s.frontend_url.strip() in {"*", "http://*", "https://*"}:
            errors.append("FRONTEND_URL must not use wildcard origins")
        if parsed_frontend.scheme not in {"http", "https"}:
            errors.append("FRONTEND_URL must be an absolute http(s) URL")
        elif parsed_frontend.scheme != "https":
            errors.append("FRONTEND_URL must use https outside development")
        if errors:
            raise RuntimeError(
                "Refusing to start in "
                + s.app_env.value
                + " with insecure configuration:\n  - "
                + "\n  - ".join(errors)
            )
    return s
