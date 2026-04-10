"""
REST routes for authentication: register, verify email, resend code, login, and current user.

``/resend-verification`` delegates to the service layer, which uses generic responses so
clients cannot distinguish unknown emails from known ones (anti-enumeration).

Added: 2026-04-03
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.schemas import (
    UserCreate,
    UserLogin,
    UserResponse,
    TokenResponse,
    RegistrationResponse,
    VerifyEmailRequest,
    ResendVerificationRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    MessageResponse,
)
from app.auth.service import AuthService, get_current_user
from app.database.engine import get_async_session
from app.database.models import User

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=RegistrationResponse, status_code=201)
async def register(
    payload: UserCreate,
    session: AsyncSession = Depends(get_async_session),
):
    """Register a new user account. Sends a 6-digit verification code to their email."""
    service = AuthService(session)
    return await service.register(
        email=payload.email,
        password=payload.password,
        full_name=payload.full_name,
    )


@router.post("/verify-email", response_model=MessageResponse)
async def verify_email(
    payload: VerifyEmailRequest,
    session: AsyncSession = Depends(get_async_session),
):
    """Verify a user's email address using the 6-digit code."""
    service = AuthService(session)
    await service.verify_email(email=payload.email, code=payload.code)
    return {"message": "Email verified successfully! You can now log in."}


@router.post("/resend-verification", response_model=MessageResponse)
async def resend_verification(
    payload: ResendVerificationRequest,
    session: AsyncSession = Depends(get_async_session),
):
    """Resend the verification code. Uses generic messaging to prevent email enumeration."""
    service = AuthService(session)
    return await service.resend_verification(email=payload.email)


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: UserLogin,
    session: AsyncSession = Depends(get_async_session),
):
    """Authenticate and receive a JWT access token."""
    service = AuthService(session)
    return await service.login(email=payload.email, password=payload.password)


@router.post("/forgot-password", response_model=MessageResponse)
async def forgot_password(
    payload: ForgotPasswordRequest,
    session: AsyncSession = Depends(get_async_session),
):
    """Request a password reset link. Always returns generic messaging (anti-enumeration)."""
    service = AuthService(session)
    return await service.forgot_password(email=payload.email)


@router.post("/reset-password", response_model=MessageResponse)
async def reset_password(
    payload: ResetPasswordRequest,
    session: AsyncSession = Depends(get_async_session),
):
    """Reset password using a valid reset token."""
    service = AuthService(session)
    return await service.reset_password(token=payload.token, new_password=payload.new_password)


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """Get the current authenticated user's profile."""
    return current_user


@router.delete("/account", response_model=MessageResponse)
async def delete_account(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Permanently delete the authenticated user's account and all associated data."""
    service = AuthService(session)
    await service.delete_account(current_user)
    return {"message": "Account deleted successfully."}
