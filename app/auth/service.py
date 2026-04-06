from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings, Environment
from app.database.engine import get_async_session
from app.database.models import User
from app.utils.email import (
    generate_verification_code,
    verification_code_expiry,
    send_verification_email,
)
from app.utils.logging import get_logger

logger = get_logger("auth")

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
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
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An account with this email already exists.",
            )

        hashed = pwd_context.hash(password)
        code = generate_verification_code()

        user = User(
            email=email,
            hashed_password=hashed,
            full_name=full_name,
            is_email_verified=False,
            email_verification_token=code,
            email_verification_expires_at=verification_code_expiry(),
        )
        self._session.add(user)
        await self._session.flush()
        await self._session.refresh(user)

        logger.info(
            "User registered",
            extra={"event": "user_registered", "user_id": user.id},
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
            if expiry.tzinfo is None:
                expiry = expiry.replace(tzinfo=timezone.utc)
            if expiry < now:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Verification code has expired. Please request a new one.",
                )

        if user.email_verification_token != code:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid verification code.",
            )

        user.is_email_verified = True
        user.email_verification_token = None
        user.email_verification_expires_at = None
        await self._session.flush()

        logger.info(
            "Email verified", extra={"event": "email_verified", "user_id": user.id}
        )
        return user

    async def resend_verification(self, email: str) -> dict:
        result = await self._session.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

        if not user:
            return {
                "message": "If an account with that email exists, a new code has been sent."
            }

        if user.is_email_verified:
            return {"message": "Email is already verified. You can log in."}

        code = generate_verification_code()
        user.email_verification_token = code
        user.email_verification_expires_at = verification_code_expiry()
        await self._session.flush()

        await send_verification_email(email, code, user.full_name)

        logger.info(
            "Verification code resent",
            extra={"event": "verification_resent", "user_id": user.id},
        )
        return {
            "message": "If an account with that email exists, a new code has been sent."
        }

    async def login(self, email: str, password: str) -> dict:
        result = await self._session.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

        if not user or not pwd_context.verify(password, user.hashed_password):
            logger.warning(
                "Failed login attempt", extra={"event": "login_failed", "email": email}
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

        token = self._create_access_token(user_id=user.id)
        expires_in = self._settings.jwt_access_token_expire_minutes * 60

        logger.info(
            "User logged in", extra={"event": "login_success", "user_id": user.id}
        )

        return {
            "access_token": token,
            "token_type": "bearer",
            "expires_in": expires_in,
        }

    def _create_access_token(self, user_id: int) -> str:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=self._settings.jwt_access_token_expire_minutes
        )
        payload = {
            "sub": str(user_id),
            "exp": expire,
            "iat": datetime.now(timezone.utc),
        }
        return jwt.encode(
            payload,
            self._settings.jwt_secret_key,
            algorithm=self._settings.jwt_algorithm,
        )

    @staticmethod
    def verify_token(token: str) -> Optional[int]:
        settings = get_settings()
        try:
            payload = jwt.decode(
                token,
                settings.jwt_secret_key,
                algorithms=[settings.jwt_algorithm],
            )
            user_id = payload.get("sub")
            return int(user_id) if user_id else None
        except (JWTError, ValueError):
            return None


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    session: AsyncSession = Depends(get_async_session),
) -> User:
    user_id = AuthService.verify_token(token)
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    return user
