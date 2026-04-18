"""HTTP surface for the portfolio assistant.

``user_id`` always comes from the JWT (``get_current_user``), never the
body, so the model can't target another account.
"""

from __future__ import annotations

import json
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.service import get_current_user
from app.database.engine import get_async_session
from app.database.models import User
from app.utils.logging import get_logger

from .models import AssistantAnswer
from .service import AssistantService

logger = get_logger("ai_agent.router")

router = APIRouter(prefix="/assistant", tags=["assistant"])


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)


class StreamRequest(AskRequest):
    # Without a session the stream is ephemeral (no persistence, no context).
    session_id: Optional[UUID] = None


@router.post("/ask", response_model=AssistantAnswer)
async def ask_assistant(
    payload: AskRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> AssistantAnswer:
    service = AssistantService(session=session, user_id=current_user.id)
    try:
        return await service.ask(payload.question)
    except RuntimeError as e:
        logger.error("Assistant unavailable", extra={"error": str(e)})
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Assistant is not configured. Contact an administrator.",
        )
    except Exception as e:  # noqa: BLE001
        logger.exception("Assistant failed", extra={"error": str(e)})
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The assistant could not answer right now. Please try again.",
        )


def _sse(event: str, data: dict) -> str:
    """Format a single Server-Sent Event frame."""
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


@router.post("/stream")
async def stream_assistant(
    payload: StreamRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> StreamingResponse:
    """Stream the assistant response as SSE (``event: delta|done|error``).

    POST (not EventSource) so auth headers work; the frontend reads the
    response body as a chunked stream.
    """
    service = AssistantService(session=session, user_id=current_user.id)

    async def event_source():
        try:
            async for event in service.stream(
                payload.question, session_id=payload.session_id
            ):
                yield _sse(event["type"], event)
        except RuntimeError as e:
            logger.error("Assistant unavailable", extra={"error": str(e)})
            yield _sse(
                "error",
                {
                    "type": "error",
                    "message": "Assistant is not configured. Contact an administrator.",
                },
            )
        except Exception as e:  # noqa: BLE001
            logger.exception("Stream failed", extra={"error": str(e)})
            yield _sse(
                "error",
                {
                    "type": "error",
                    "message": "The assistant could not answer right now. Please try again.",
                },
            )

    return StreamingResponse(
        event_source(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )
