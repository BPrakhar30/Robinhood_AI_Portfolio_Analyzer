"""Seed a verified demo user for public free-tier deployments.

The script is intentionally idempotent. Existing users are never modified
unless ``RESET_DEMO_USER_PASSWORD=true`` is set explicitly.
"""

from __future__ import annotations

import asyncio
import hashlib

import bcrypt
from sqlalchemy import select

from app.config import get_settings
from app.database.engine import AsyncSessionLocal
from app.database.models import User
from app.utils.logging import get_logger

logger = get_logger("scripts.seed_demo_user")


def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def _redact_email(email: str) -> str:
    return hashlib.sha256(email.lower().encode()).hexdigest()[:16]


async def seed_demo_user() -> None:
    settings = get_settings()
    if not settings.seed_demo_user:
        logger.info("Demo user seeding skipped")
        return

    email = settings.demo_user_email.strip().lower()
    password = settings.demo_user_password
    if len(password) < 8:
        raise RuntimeError("DEMO_USER_PASSWORD must be at least 8 characters")

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

        if user:
            user.is_active = True
            user.is_email_verified = True
            user.email_verification_token = None
            user.email_verification_expires_at = None
            if settings.reset_demo_user_password:
                user.hashed_password = _hash_password(password)
                user.token_version = int(user.token_version or 0) + 1
            await session.commit()
            logger.info(
                "Demo user verified",
                extra={"email_hash": _redact_email(email), "created": False},
            )
            return

        session.add(
            User(
                email=email,
                hashed_password=_hash_password(password),
                full_name="Demo User",
                is_active=True,
                is_email_verified=True,
            )
        )
        await session.commit()
        logger.info(
            "Demo user created",
            extra={"email_hash": _redact_email(email), "created": True},
        )


def main() -> None:
    asyncio.run(seed_demo_user())


if __name__ == "__main__":
    main()
