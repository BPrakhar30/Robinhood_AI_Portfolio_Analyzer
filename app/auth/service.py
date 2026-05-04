"""Auth service: registration, login, email verification, JWT access tokens.

``resend_verification`` returns generic responses to prevent email enumeration.
``login`` requires an active, email-verified account.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

import hmac

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
import bcrypt
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database.engine import get_async_session
from app.database.models import User
import secrets

from app.utils.email import (
    generate_verification_code,
    verification_code_expiry,
    send_verification_email,
    password_reset_expiry,
    send_password_reset_email,
)
from app.utils.logging import get_logger

logger = get_logger("auth")


import hashlib
import time


def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def _verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())


def _redact_email(email: str) -> str:
    """One-way hash for safe log indexing without exposing PII."""
    return hashlib.sha256(email.lower().encode()).hexdigest()[:16]


def _hash_secret_token(token: str) -> str:
    """HMAC-hash one-time tokens before persisting (prevents plaintext token-at-rest)."""
    secret = get_settings().secret_key.encode()
    return hmac.new(secret, token.encode(), hashlib.sha256).hexdigest()


# ---------------------------------------------------------------------------
# Brute-force protection: bounded in-memory tracker for failed login attempts.
# After MAX_ATTEMPTS consecutive failures, the account is locked for
# LOCKOUT_SECONDS.  Successful login resets the counter.
# Bounded to prevent memory exhaustion from distributed brute-force attacks.
# ---------------------------------------------------------------------------

_MAX_ATTEMPTS = 5
_LOCKOUT_SECONDS = 300  # 5 minutes
_TRACKER_MAXSIZE = 10_000

from app.utils.cache import BoundedTTLCache

_login_tracker: BoundedTTLCache = BoundedTTLCache(
    maxsize=_TRACKER_MAXSIZE, default_ttl=_LOCKOUT_SECONDS
)


def _check_login_lockout(email: str) -> None:
    """Raise 429 if the email is currently locked out."""
    key = _redact_email(email)
    entry = _login_tracker.get(key)
    if entry is None:
        return
    attempts, locked_until = entry
    if attempts >= _MAX_ATTEMPTS and time.time() < locked_until:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many failed login attempts. Please try again in a few minutes.",
        )
    if time.time() >= locked_until:
        _login_tracker.delete(key)


def _record_failed_login(email: str) -> None:
    key = _redact_email(email)
    entry = _login_tracker.get(key)
    attempts = (entry[0] if entry else 0) + 1
    locked_until = time.time() + _LOCKOUT_SECONDS if attempts >= _MAX_ATTEMPTS else 0
    _login_tracker.set(key, (attempts, locked_until), ttl=_LOCKOUT_SECONDS)


def _clear_login_tracker(email: str) -> None:
    key = _redact_email(email)
    _login_tracker.delete(key)


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


class AuthService:
    """
    Handles user registration, login, email verification, and JWT token management.
    Passwords are hashed with bcrypt — never stored in plaintext.
    """

    def __init__(self, session: AsyncSession):
        self._session = session
        self._settings = get_settings()

    async def register(
        self, email: str, password: str, full_name: Optional[str] = None
    ) -> dict:
        existing = await self._session.execute(select(User).where(User.email == email))
        existing_user = existing.scalar_one_or_none()
        if existing_user:
            logger.warning(
                "Duplicate registration attempt",
                extra={"event": "register_duplicate", "user_id": str(existing_user.id)},
            )
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Registration could not be completed. If you already have an account, try logging in.",
            )

        hashed = _hash_password(password)
        code = generate_verification_code()

        user = User(
            email=email,
            hashed_password=hashed,
            full_name=full_name,
            is_email_verified=False,
            email_verification_token=_hash_secret_token(code),
            email_verification_expires_at=verification_code_expiry(),
        )
        self._session.add(user)
        await self._session.flush()
        await self._session.refresh(user)

        logger.info(
            "User registered",
            extra={"event": "user_registered", "user_id": str(user.id)},
        )

        await send_verification_email(email, code, full_name)

        return {
            "message": "Account created! Please check your email for a verification code.",
            "email": email,
            "requires_verification": True,
        }

    async def verify_email(self, email: str, code: str) -> User:
        result = await self._session.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid verification code.",
            )

        if user.is_email_verified:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email is already verified.",
            )

        if user.email_verification_expires_at:
            expiry = user.email_verification_expires_at
            now = datetime.now(timezone.utc)
            # ORM may yield naive datetimes; treat stored expiry as UTC before comparing.
            if expiry.tzinfo is None:
                expiry = expiry.replace(tzinfo=timezone.utc)
            if expiry < now:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Verification code has expired. Please request a new one.",
                )

        if not hmac.compare_digest(
            (user.email_verification_token or "").encode(),
            _hash_secret_token(code).encode(),
        ):
            logger.warning(
                "Email verification failed - wrong code",
                extra={"event": "verify_failed", "user_id": str(user.id)},
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid verification code.",
            )

        user.is_email_verified = True
        user.email_verification_token = None
        user.email_verification_expires_at = None
        await self._session.flush()

        logger.info(
            "Email verified", extra={"event": "email_verified", "user_id": str(user.id)}
        )
        return user

    async def resend_verification(self, email: str) -> dict:
        # Same outward message for missing vs present email to avoid email enumeration.
        result = await self._session.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

        if not user:
            return {
                "message": "If an account with that email exists, a new code has been sent."
            }

        if user.is_email_verified:
            return {"message": "Email is already verified. You can log in."}

        code = generate_verification_code()
        user.email_verification_token = _hash_secret_token(code)
        user.email_verification_expires_at = verification_code_expiry()
        await self._session.flush()

        await send_verification_email(email, code, user.full_name)

        logger.info(
            "Verification code resent",
            extra={"event": "verification_resent", "user_id": str(user.id)},
        )
        return {
            "message": "If an account with that email exists, a new code has been sent."
        }

    async def login(self, email: str, password: str) -> dict:
        _check_login_lockout(email)

        result = await self._session.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

        if not user or not _verify_password(password, user.hashed_password):
            _record_failed_login(email)
            logger.warning(
                "Failed login attempt",
                extra={"event": "login_failed", "email_hash": _redact_email(email)},
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is deactivated.",
            )

        if not user.is_email_verified:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Please verify your email address before logging in.",
            )

        _clear_login_tracker(email)

        # Only verified, active users receive a JWT (defense-in-depth with get_current_user).
        token = self._create_access_token(
            user_id=user.id,
            token_version=int(user.token_version or 0),
        )
        expires_in = self._settings.jwt_access_token_expire_minutes * 60

        logger.info(
            "User logged in", extra={"event": "login_success", "user_id": str(user.id)}
        )

        return {
            "access_token": token,
            "token_type": "bearer",
            "expires_in": expires_in,
        }

    def _create_access_token(self, user_id: UUID, token_version: int) -> str:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=self._settings.jwt_access_token_expire_minutes
        )
        payload = {
            # UUID serialized as a canonical 36-char string. Opaque to clients.
            "sub": str(user_id),
            "exp": expire,
            "iat": datetime.now(timezone.utc),
            # Per-user token generation version for stateless revocation.
            "tv": int(token_version),
        }
        return jwt.encode(
            payload,
            self._settings.jwt_secret_key,
            algorithm=self._settings.jwt_algorithm,
        )

    async def forgot_password(self, email: str) -> dict:
        """Generate a password reset token and send it via email.

        Always returns a generic message to prevent email enumeration.
        """
        result = await self._session.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

        if not user:
            return {
                "message": "If an account with that email exists, a reset link has been sent."
            }

        token = secrets.token_urlsafe(32)
        user.password_reset_token = _hash_secret_token(token)
        user.password_reset_expires_at = password_reset_expiry()
        await self._session.flush()

        await send_password_reset_email(email, token, user.full_name)

        logger.info(
            "Password reset requested",
            extra={"event": "password_reset_requested", "user_id": str(user.id)},
        )
        return {
            "message": "If an account with that email exists, a reset link has been sent."
        }

    async def reset_password(self, token: str, new_password: str) -> dict:
        """Validate a reset token and update the user's password."""
        token_hash = _hash_secret_token(token)
        result = await self._session.execute(
            select(User).where(User.password_reset_token == token_hash)
        )
        user = result.scalar_one_or_none()

        if not user:
            logger.warning(
                "Password reset attempted with invalid token",
                extra={"event": "reset_token_invalid"},
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired reset link.",
            )

        if user.password_reset_expires_at:
            expiry = user.password_reset_expires_at
            now = datetime.now(timezone.utc)
            if expiry.tzinfo is None:
                expiry = expiry.replace(tzinfo=timezone.utc)
            if expiry < now:
                user.password_reset_token = None
                user.password_reset_expires_at = None
                await self._session.flush()
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Reset link has expired. Please request a new one.",
                )

        user.hashed_password = _hash_password(new_password)
        user.password_reset_token = None
        user.password_reset_expires_at = None
        # Password reset invalidates all existing JWTs for this user.
        user.token_version = int(user.token_version or 0) + 1
        await self._session.flush()

        logger.info(
            "Password reset completed",
            extra={"event": "password_reset_completed", "user_id": str(user.id)},
        )
        return {"message": "Password has been reset successfully. You can now log in."}

    async def delete_account(self, user: User) -> bool:
        """Permanently delete a user account and all associated data."""
        await self._session.delete(user)
        await self._session.flush()
        logger.info(
            "Account deleted",
            extra={"event": "account_deleted", "user_id": str(user.id)},
        )
        return True

    async def revoke_tokens(self, user: User) -> None:
        """Revoke all active JWTs by bumping the user's token version."""
        user.token_version = int(user.token_version or 0) + 1
        await self._session.flush()
        logger.info(
            "User tokens revoked",
            extra={"event": "tokens_revoked", "user_id": str(user.id)},
        )

    @staticmethod
    def verify_token(token: str) -> Optional[tuple[UUID, int]]:
        """Decode JWT and return (user_id, token_version), or None if invalid."""
        settings = get_settings()
        try:
            payload = jwt.decode(
                token,
                settings.jwt_secret_key,
                algorithms=[settings.jwt_algorithm],
            )
            sub = payload.get("sub")
            if not sub:
                return None
            tv_raw = payload.get("tv", 0)
            token_version = int(tv_raw)
            # Rejecting malformed UUIDs here prevents them from reaching the DB
            # layer as opaque strings that might match due to implicit casting.
            return (UUID(str(sub)), token_version)
        except (JWTError, ValueError):
            return None


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    session: AsyncSession = Depends(get_async_session),
) -> User:
    claims = AuthService.verify_token(token)
    if claims is None:
        logger.warning(
            "JWT verification failed",
            extra={"event": "jwt_invalid"},
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user_id, token_version = claims

    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        logger.warning(
            "JWT valid but user inactive or missing",
            extra={"event": "jwt_user_invalid", "user_id": str(user_id)},
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    if int(user.token_version or 0) != token_version:
        logger.warning(
            "JWT rejected due to token version mismatch",
            extra={"event": "jwt_revoked", "user_id": str(user_id)},
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user
