"""Service layer between the HTTP router and the PydanticAI agent.

Multi-turn context follows PydanticAI's ``ModelMessage`` pattern: the full
serialized history lives on ``ChatSession.agent_history`` and is replayed
via ``run_stream(..., message_history=...)`` each turn. See
https://ai.pydantic.dev/message-history/.
"""

from __future__ import annotations

from typing import AsyncIterator, Optional
from uuid import UUID

from pydantic_ai import ModelMessagesTypeAdapter
from pydantic_core import to_jsonable_python
from sqlalchemy.ext.asyncio import AsyncSession

from app.chat.service import (
    SessionNotFound,
    append_chat_message,
    list_titles_for_user,
    load_session_for_agent,
    persist_agent_turn,
)
from app.utils.logging import get_logger

from .agent import AssistantDeps, get_agent
from .memory import format_memory_for_prompt, get_user_memory, schedule_memory_extraction
from .models import AssistantAnswer
from .title import generate_session_title

logger = get_logger("ai_agent.service")

# Replay window sent to the LLM (storage is uncapped). ~20 turns.
_HISTORY_WINDOW = 40


def _collect_tools_used(result) -> list[str]:
    """Extract unique tool names from a finished agent run."""
    tools_used: list[str] = []
    try:
        for msg in result.new_messages():
            for part in getattr(msg, "parts", []) or []:
                name = getattr(part, "tool_name", None)
                if name and name not in tools_used:
                    tools_used.append(name)
    except Exception:  # noqa: BLE001 - telemetry only
        return []
    return tools_used


def _load_history(raw):
    """Deserialize stored ``agent_history`` into ``ModelMessage`` objects.

    Returns ``None`` on empty/corrupt history so PydanticAI re-emits the
    system prompt. The next turn overwrites any corrupt blob.
    """
    if not raw:
        return None
    try:
        messages = ModelMessagesTypeAdapter.validate_python(raw)
    except Exception:  # noqa: BLE001
        logger.warning(
            "Failed to deserialize agent_history; starting fresh",
            extra={"event": "agent_history_invalid"},
        )
        return None
    if len(messages) > _HISTORY_WINDOW:
        messages = messages[-_HISTORY_WINDOW:]
    return messages


class AssistantService:
    """Answer portfolio questions for a specific authenticated user."""

    def __init__(self, session: AsyncSession, user_id: UUID):
        self._db = session
        self._user_id = user_id

    async def ask(self, question: str) -> AssistantAnswer:
        """Single-shot, non-streaming, non-persisted. For tests/jobs."""
        question = (question or "").strip()
        if not question:
            return AssistantAnswer(answer="Please ask a question about your portfolio.")

        memory_facts = await get_user_memory(self._db, self._user_id)
        deps = AssistantDeps(
            user_id=self._user_id,
            user_memory=format_memory_for_prompt(memory_facts),
        )
        agent = get_agent()
        result = await agent.run(question, deps=deps)

        tools_used = _collect_tools_used(result)
        answer = str(result.output)

        schedule_memory_extraction(self._user_id, question, answer)

        logger.info(
            "Assistant answered",
            extra={
                "event": "assistant_answered",
                "user_id": str(self._user_id),
                "tools_used": tools_used,
            },
        )

        return AssistantAnswer(answer=answer, tools_used=tools_used)

    async def stream(
        self,
        question: str,
        session_id: Optional[UUID] = None,
    ) -> AsyncIterator[dict]:
        """Stream the agent's response as structured events.

        Events: ``{"type":"delta","text":...}``, ``{"type":"done","tools_used":...}``,
        ``{"type":"error","message":...}``.

        With ``session_id``: ownership-verified, history replayed, user +
        assistant turns persisted, ``agent_history`` overwritten with the
        full updated message list. Without it: ephemeral run, no persistence.
        """
        question = (question or "").strip()
        if not question:
            yield {
                "type": "delta",
                "text": "Please ask a question about your portfolio.",
            }
            yield {"type": "done", "tools_used": []}
            return

        # Fetch cross-session memory facts BEFORE loading the chat session so
        # they're ready to inject into deps regardless of the session path.
        memory_facts = await get_user_memory(self._db, self._user_id)
        deps = AssistantDeps(
            user_id=self._user_id,
            user_memory=format_memory_for_prompt(memory_facts),
        )

        chat_session = None
        message_history = None
        if session_id is not None:
            try:
                chat_session = await load_session_for_agent(
                    self._db, session_id, self._user_id
                )
            except SessionNotFound:
                yield {
                    "type": "error",
                    "message": "Chat session not found.",
                }
                return
            message_history = _load_history(chat_session.agent_history)

            # Persist user turn up-front so it survives aborted streams.
            await append_chat_message(
                self._db,
                session_id=session_id,
                role="user",
                content=question,
            )
            await self._db.commit()

        agent = get_agent()

        # Accumulate deltas so the persisted message matches the client output.
        final_text_parts: list[str] = []
        async with agent.run_stream(
            question,
            deps=deps,
            message_history=message_history,
        ) as result:
            async for delta in result.stream_text(delta=True):
                if delta:
                    final_text_parts.append(delta)
                    yield {"type": "delta", "text": delta}

            tools_used = _collect_tools_used(result)
            # Serialize inside the context  -  some accessors require the
            # stream to be fully drained first.
            all_messages_json = (
                to_jsonable_python(result.all_messages())
                if session_id is not None
                else None
            )

        final_text = "".join(final_text_parts)

        # Fire-and-forget: extract any memorable facts from this turn.
        # Runs as a background task so it never delays the SSE response.
        schedule_memory_extraction(self._user_id, question, final_text)

        if session_id is not None and chat_session is not None:
            new_title: Optional[str] = None
            if chat_session.title.strip().lower() in ("", "new chat"):
                # Only the first turn of a session triggers the LLM titler.
                # Subsequent turns keep whatever name the user / model chose.
                existing_titles = await list_titles_for_user(
                    self._db,
                    self._user_id,
                    exclude_session_id=session_id,
                )
                generated = await generate_session_title(
                    question=question,
                    answer=final_text,
                    existing_titles=existing_titles,
                )
                new_title = generated or chat_session.title

            await append_chat_message(
                self._db,
                session_id=session_id,
                role="assistant",
                content=final_text,
                tools_used=tools_used,
            )
            await persist_agent_turn(
                self._db,
                session_id=session_id,
                agent_history=all_messages_json,
                new_title=new_title,
            )
            await self._db.commit()

        logger.info(
            "Assistant streamed answer",
            extra={
                "event": "assistant_streamed",
                "user_id": str(self._user_id),
                "session_id": str(session_id) if session_id else None,
                "tools_used": tools_used,
            },
        )
        yield {"type": "done", "tools_used": tools_used}
