"""Persistence + CRUD for chat sessions/messages.

All queries are scoped by ``user_id``. Unknown or other-owner ids raise
``SessionNotFound`` (router → 404) so existence isn't leakable.
"""

from __future__ import annotations

from typing import Iterable, Optional
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database.models import ChatMessage, ChatSession
from app.utils.logging import get_logger

from .schemas import (
    ChatMessageOut,
    ChatSessionCreate,
    ChatSessionDetail,
    ChatSessionOut,
    ChatSessionUpdate,
)

logger = get_logger("chat.service")

_PREVIEW_LEN = 80


class SessionNotFound(Exception):
    """Session id doesn't exist for the given user."""


def _preview_from_messages(messages: Iterable[ChatMessage]) -> str:
    last = None
    for m in messages:
        last = m
    if not last or not last.content:
        return ""
    return last.content[:_PREVIEW_LEN]


def _to_summary(session: ChatSession) -> ChatSessionOut:
    """ORM → summary DTO. Callers must eager-load ``messages``."""
    # Read via __dict__ to skip async lazy-load IO.
    loaded_msgs = session.__dict__.get("messages")
    preview = _preview_from_messages(loaded_msgs) if loaded_msgs else ""
    return ChatSessionOut(
        id=session.id,
        title=session.title,
        starred=session.starred,
        archived=session.archived,
        preview=preview,
        created_at=session.created_at,
        updated_at=session.updated_at,
    )


async def _get_owned_session(
    db: AsyncSession, session_id: UUID, user_id: UUID, *, with_messages: bool = False
) -> ChatSession:
    """Fetch a session scoped to ``user_id`` or raise ``SessionNotFound``."""
    stmt = select(ChatSession).where(
        ChatSession.id == session_id,
        ChatSession.user_id == user_id,
    )
    if with_messages:
        stmt = stmt.options(selectinload(ChatSession.messages))
    result = await db.execute(stmt)
    session = result.scalar_one_or_none()
    if session is None:
        raise SessionNotFound(f"session {session_id} not found for user")
    return session


async def list_sessions(db: AsyncSession, user_id: UUID) -> list[ChatSessionOut]:
    """All of a user's sessions, newest-updated first."""
    stmt = (
        select(ChatSession)
        .where(ChatSession.user_id == user_id)
        .options(selectinload(ChatSession.messages))
        .order_by(ChatSession.updated_at.desc())
    )
    result = await db.execute(stmt)
    sessions = result.scalars().all()
    return [_to_summary(s) for s in sessions]


async def create_session(
    db: AsyncSession, user_id: UUID, payload: ChatSessionCreate
) -> ChatSessionOut:
    """Create an empty session owned by ``user_id``."""
    session = ChatSession(
        user_id=user_id,
        title=(payload.title or "New chat").strip() or "New chat",
    )
    db.add(session)
    await db.flush()
    await db.refresh(session)

    logger.info(
        "Chat session created",
        extra={
            "event": "chat_session_created",
            "user_id": str(user_id),
            "session_id": str(session.id),
        },
    )

    return ChatSessionOut(
        id=session.id,
        title=session.title,
        starred=session.starred,
        archived=session.archived,
        preview="",
        created_at=session.created_at,
        updated_at=session.updated_at,
    )


async def get_session_detail(
    db: AsyncSession, session_id: UUID, user_id: UUID
) -> ChatSessionDetail:
    """Session metadata + full message transcript."""
    session = await _get_owned_session(db, session_id, user_id, with_messages=True)
    messages = [ChatMessageOut.model_validate(m) for m in session.messages]
    return ChatSessionDetail(
        id=session.id,
        title=session.title,
        starred=session.starred,
        archived=session.archived,
        preview=_preview_from_messages(session.messages),
        created_at=session.created_at,
        updated_at=session.updated_at,
        messages=messages,
    )


async def update_session(
    db: AsyncSession,
    session_id: UUID,
    user_id: UUID,
    patch: ChatSessionUpdate,
) -> ChatSessionOut:
    """Apply a partial update; return the fresh summary."""
    session = await _get_owned_session(db, session_id, user_id, with_messages=True)

    data = patch.model_dump(exclude_unset=True)
    if "title" in data and data["title"] is not None:
        session.title = data["title"].strip() or session.title
    if "starred" in data and data["starred"] is not None:
        session.starred = bool(data["starred"])
    if "archived" in data and data["archived"] is not None:
        session.archived = bool(data["archived"])

    await db.flush()
    return _to_summary(session)


async def delete_session(db: AsyncSession, session_id: UUID, user_id: UUID) -> None:
    """Hard-delete a session (cascades to messages)."""
    session = await _get_owned_session(db, session_id, user_id)
    await db.delete(session)
    logger.info(
        "Chat session deleted",
        extra={
            "event": "chat_session_deleted",
            "user_id": str(user_id),
            "session_id": str(session_id),
        },
    )


async def load_session_for_agent(
    db: AsyncSession, session_id: UUID, user_id: UUID
) -> ChatSession:
    """Ownership-verified fetch for the streaming endpoint."""
    return await _get_owned_session(db, session_id, user_id, with_messages=False)


async def append_chat_message(
    db: AsyncSession,
    session_id: UUID,
    role: str,
    content: str,
    tools_used: Optional[list[str]] = None,
) -> ChatMessage:
    """Insert a UI-facing message row (caller commits)."""
    msg = ChatMessage(
        session_id=session_id,
        role=role,
        content=content,
        tools_used=list(tools_used) if tools_used else None,
    )
    db.add(msg)
    await db.flush()
    return msg


async def persist_agent_turn(
    db: AsyncSession,
    session_id: UUID,
    *,
    agent_history: list,
    new_title: Optional[str] = None,
) -> None:
    """Overwrite ``agent_history`` (and title, if given)."""
    values = {"agent_history": agent_history}
    if new_title is not None:
        values["title"] = new_title
    stmt = update(ChatSession).where(ChatSession.id == session_id).values(**values)
    await db.execute(stmt)
