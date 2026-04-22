"""HTTP surface for chat sessions.

Every handler scopes to ``current_user.id``. Unknown / other-owner ids
yield 404 (not 403) so session existence isn't leakable.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.service import get_current_user
from app.database.engine import get_async_session
from app.database.models import User
from app.utils.logging import get_logger

from .schemas import (
    ChatSessionCreate,
    ChatSessionDetail,
    ChatSessionOut,
    ChatSessionUpdate,
)
from .service import (
    SessionNotFound,
    create_session,
    delete_session,
    get_session_detail,
    list_sessions,
    update_session,
)

logger = get_logger("chat.router")

router = APIRouter(prefix="/chat", tags=["chat"])


def _not_found() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Chat session not found.",
    )


@router.get("/sessions", response_model=list[ChatSessionOut])
async def list_chat_sessions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
) -> list[ChatSessionOut]:
    """List the signed-in user's chat sessions, newest-updated first."""
    return await list_sessions(db, current_user.id)


@router.post(
    "/sessions",
    response_model=ChatSessionOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_chat_session(
    payload: ChatSessionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
) -> ChatSessionOut:
    """Create an empty chat session for the signed-in user."""
    return await create_session(db, current_user.id, payload)


@router.get("/sessions/{session_id}", response_model=ChatSessionDetail)
async def get_chat_session(
    session_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
) -> ChatSessionDetail:
    """Return a session's metadata plus its full message transcript."""
    try:
        return await get_session_detail(db, session_id, current_user.id)
    except SessionNotFound:
        raise _not_found()


@router.patch("/sessions/{session_id}", response_model=ChatSessionOut)
async def patch_chat_session(
    session_id: UUID,
    patch: ChatSessionUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
) -> ChatSessionOut:
    """Partial update: title / starred / archived."""
    try:
        return await update_session(db, session_id, current_user.id, patch)
    except SessionNotFound:
        raise _not_found()


@router.delete(
    "/sessions/{session_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
)
async def delete_chat_session(
    session_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    """Hard-delete a session and its messages."""
    try:
        await delete_session(db, session_id, current_user.id)
    except SessionNotFound:
        raise _not_found()
