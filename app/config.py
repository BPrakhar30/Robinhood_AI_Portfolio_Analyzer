from pydantic_settings import BaseSettings
from pydantic import Field
from functools import lru_cache
from enum import Enum


class Environment(str, Enum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class Settings(BaseSettings):
    app_name: str = "RobinhoodAICopilot"
    app_env: Environment = Environment.DEVELOPMENT
    debug: bool = True
    secret_key: str = "change-me-in-production"

    # Database (defaults to SQLite for local dev; use PostgreSQL in staging/production)
    database_url: str = "sqlite+aiosqlite:///./robinhood_ai.db"
    database_url_sync: str = "sqlite:///./robinhood_ai.db"

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
    yahoo_finance_fallback: bool = True

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

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


@lru_cache()
def get_settings() -> Settings:
    return Settings()
