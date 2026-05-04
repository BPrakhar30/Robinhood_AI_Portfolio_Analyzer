"""Auth routes: register, verify email, resend code, login, current user.

``/resend-verification`` returns generic responses to prevent email enumeration.
"""

from fastapi import APIRouter, Depends, Request
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
from app.utils.security import limiter

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=RegistrationResponse, status_code=201)
@limiter.limit("5/minute")
async def register(
    request: Request,
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
@limiter.limit("10/minute")
async def verify_email(
    request: Request,
    payload: VerifyEmailRequest,
    session: AsyncSession = Depends(get_async_session),
):
    """Verify a user's email address using the 6-digit code."""
    service = AuthService(session)
    await service.verify_email(email=payload.email, code=payload.code)
    return {"message": "Email verified successfully! You can now log in."}


@router.post("/resend-verification", response_model=MessageResponse)
@limiter.limit("3/minute")
async def resend_verification(
    request: Request,
    payload: ResendVerificationRequest,
    session: AsyncSession = Depends(get_async_session),
):
    """Resend the verification code. Uses generic messaging to prevent email enumeration."""
    service = AuthService(session)
    return await service.resend_verification(email=payload.email)


@router.post("/login", response_model=TokenResponse)
@limiter.limit("10/minute")
async def login(
    request: Request,
    payload: UserLogin,
    session: AsyncSession = Depends(get_async_session),
):
    """Authenticate and receive a JWT access token."""
    service = AuthService(session)
    return await service.login(email=payload.email, password=payload.password)


@router.post("/forgot-password", response_model=MessageResponse)
@limiter.limit("3/minute")
async def forgot_password(
    request: Request,
    payload: ForgotPasswordRequest,
    session: AsyncSession = Depends(get_async_session),
):
    """Request a password reset link. Always returns generic messaging (anti-enumeration)."""
    service = AuthService(session)
    return await service.forgot_password(email=payload.email)


@router.post("/reset-password", response_model=MessageResponse)
@limiter.limit("5/minute")
async def reset_password(
    request: Request,
    payload: ResetPasswordRequest,
    session: AsyncSession = Depends(get_async_session),
):
    """Reset password using a valid reset token."""
    service = AuthService(session)
    return await service.reset_password(
        token=payload.token, new_password=payload.new_password
    )


@router.post("/logout", response_model=MessageResponse)
@limiter.limit("20/minute")
async def logout(
    request: Request,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Revoke active JWTs for the authenticated user."""
    service = AuthService(session)
    await service.revoke_tokens(current_user)
    return {"message": "Logged out successfully."}


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
