"""Pydantic schemas for the chat REST API.

Wire-level shapes the frontend consumes; kept independent of the ORM.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ChatSessionCreate(BaseModel):
    """Session creation payload. ``title`` auto-derives from the first
    user message if omitted."""

    title: Optional[str] = Field(default=None, max_length=255)


class ChatSessionUpdate(BaseModel):
    """Partial update; only the provided fields are mutated."""

    title: Optional[str] = Field(default=None, max_length=255)
    starred: Optional[bool] = None
    archived: Optional[bool] = None


class ChatSessionOut(BaseModel):
    """Summary view for sidebar listings  -  no message payload."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    starred: bool
    archived: bool
    preview: str = ""
    created_at: datetime
    updated_at: datetime


class ChatMessageOut(BaseModel):
    """A UI-facing message in a chat session."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    role: Literal["user", "assistant"]
    content: str
    tools_used: list[str] = Field(default_factory=list)
    created_at: datetime

    @field_validator("tools_used", mode="before")
    @classmethod
    def _coerce_tools_used(cls, v: Any) -> list[str]:
        # DB column is nullable JSON; coerce NULL/scalars to a list.
        if v is None:
            return []
        if isinstance(v, list):
            return v
        return [str(v)]


class ChatSessionDetail(ChatSessionOut):
    """Session summary + its message transcript."""

    messages: list[ChatMessageOut] = Field(default_factory=list)
