"""Cross-session user memory for the portfolio assistant.

Best-practice AI memory taxonomy (following OpenAI / Anthropic production
patterns) applied to this codebase:

  1. IN-SESSION BUFFER MEMORY (already works)
     Full conversation history passed via ``message_history=`` to every
     PydanticAI run. Stored in ``ChatSession.agent_history`` (Postgres).
     Window capped at 40 messages to stay within LLM token limits.

  2. CROSS-SESSION PERSISTENT MEMORY  ← this module
     After each completed turn the assistant extracts memorable facts from
     the latest exchange (investment goals, risk tolerance, favourite tickers,
     portfolio concerns) and upserts them into ``UserMemory``. The next
     session begins with these facts injected into the system prompt so the
     assistant feels contextually aware across conversations  -  like a
     financial advisor who remembers past meetings.

     Design choices:
     - Plain list of ≤ 25 short strings. Auditable, deletable, no embedding
       infrastructure required.
     - Extraction runs as a fire-and-forget background task so it never
       delays the user's response stream.
     - Deduplication is token-level: a new fact is only added when it isn't
       a substring of any existing fact (case-insensitive). This keeps the
       list tight without a vector similarity search.
     - Facts are intentionally conservative: the extractor prompt forbids
       fabrication and only captures things explicitly stated by the user.

  3. FUTURE: SUMMARY MEMORY (not yet implemented)
     When ``agent_history`` grows beyond the window, the assistant could
     summarize the earliest turns and store the summary as a single fake
     "assistant" message, reducing token usage while preserving context.
"""

from __future__ import annotations

import asyncio
import re
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database.engine import AsyncSessionLocal
from app.database.models import UserMemory
from app.utils.logging import get_logger

logger = get_logger("ai_agent.memory")

_MAX_FACTS = 25
_MAX_FACT_WORDS = 20  # keep each fact tight

# ── Extraction prompt ────────────────────────────────────────────────

_MEMORY_EXTRACTION_PROMPT = """\
You are an assistant memory extractor for a portfolio AI.

Given one exchange (a user question and assistant answer), extract ONLY
facts the user has explicitly stated or clearly revealed about themselves,
their finances, or their investment preferences.

Output format: one fact per line, each ≤ {max_words} words, starting with
"- ". Return an empty response if nothing new and memorable was revealed.

Valid categories:
- Investment goals (saving for retirement, house, education, etc.)
- Risk tolerance (conservative, moderate, aggressive, etc.)
- Time horizon (short-term, 5-year plan, etc.)
- Asset/sector preferences or aversions (loves tech stocks, avoids crypto, etc.)
- Portfolio concerns (overexposed to NVDA, worried about rate hikes, etc.)
- Trading style (buy-and-hold, dividend investing, momentum, etc.)

Hard rules:
- NEVER invent or infer facts not clearly stated by the user.
- Do NOT repeat facts that already appear in EXISTING_FACTS.
- Do NOT capture facts about the market or economy (only about THIS user).
- Do NOT include the user's specific holdings or balances (those come from
  live portfolio tools; memory is for preferences and goals only).
- Maximum {max_facts} total facts including existing ones.

EXISTING_FACTS:
{existing_facts}

LATEST EXCHANGE:
User: {question}
Assistant: {answer}

New memorable facts (or empty if none):
"""


# ── Gemini call for extraction ───────────────────────────────────────


async def _call_gemini_for_facts(
    question: str,
    answer: str,
    existing_facts: list[str],
) -> list[str]:
    """Call the LLM to extract new memorable facts from one turn.

    Returns only the *new* facts (not the merged list). Returns ``[]``
    on any failure so the caller can skip gracefully.
    """
    try:
        from pydantic_ai import Agent
        from pydantic_ai.models.google import GoogleModel
        from pydantic_ai.providers.google import GoogleProvider
    except ImportError:
        return []

    settings = get_settings()
    if not settings.google_api_key:
        return []

    model = GoogleModel(
        settings.google_model,
        provider=GoogleProvider(api_key=settings.google_api_key),
    )
    agent: Agent[None, str] = Agent(model, output_type=str)

    existing_block = (
        "\n".join(f"- {f}" for f in existing_facts) if existing_facts else "(none)"
    )
    prompt = _MEMORY_EXTRACTION_PROMPT.format(
        max_words=_MAX_FACT_WORDS,
        max_facts=_MAX_FACTS,
        existing_facts=existing_block,
        question=question[:800],
        answer=answer[:1200],
    )

    try:
        result = await agent.run(prompt)
        raw = (result.output or "").strip()
    except Exception as exc:  # noqa: BLE001
        logger.debug(f"Memory extraction LLM call failed: {exc}")
        return []

    facts: list[str] = []
    for line in raw.splitlines():
        line = re.sub(r"^[-•\*]\s*", "", line).strip()
        if not line or len(line.split()) > _MAX_FACT_WORDS + 2:
            continue
        facts.append(line)
    return facts[:_MAX_FACTS]


# ── Deduplication ────────────────────────────────────────────────────


def _dedupe_facts(existing: list[str], new_facts: list[str]) -> list[str]:
    """Merge new facts into existing, dropping near-duplicates.

    A new fact is suppressed when it appears as a substring (case-insensitive,
    ignoring leading/trailing whitespace) of any existing fact, or vice-versa.
    This avoids "prefers dividend stocks" and "likes dividend-paying stocks"
    both living in the store.
    """
    merged = list(existing)
    for new in new_facts:
        new_l = new.strip().lower()
        if not new_l:
            continue
        duplicate = any(
            new_l in ex.lower() or ex.lower() in new_l
            for ex in merged
        )
        if not duplicate:
            merged.append(new.strip())
        if len(merged) >= _MAX_FACTS:
            break
    return merged[:_MAX_FACTS]


# ── DB helpers ───────────────────────────────────────────────────────


async def get_user_memory(db: AsyncSession, user_id: UUID) -> list[str]:
    """Return stored memory facts for ``user_id`` (empty list if none)."""
    result = await db.execute(
        select(UserMemory).where(UserMemory.user_id == user_id)
    )
    row = result.scalar_one_or_none()
    if row is None:
        return []
    return list(row.facts or [])


async def _upsert_user_memory(
    db: AsyncSession, user_id: UUID, facts: list[str]
) -> None:
    """Insert or update the user's memory row."""
    stmt = pg_insert(UserMemory).values(user_id=user_id, facts=facts)
    stmt = stmt.on_conflict_do_update(
        index_elements=["user_id"],
        set_={"facts": facts},
    )
    await db.execute(stmt)
    await db.commit()


# ── Public: fire-and-forget task ─────────────────────────────────────


async def _extract_and_save(
    user_id: UUID,
    question: str,
    answer: str,
) -> None:
    """Background coroutine: extract + save memory without blocking the response."""
    async with AsyncSessionLocal() as db:
        try:
            existing = await get_user_memory(db, user_id)
            new_facts = await _call_gemini_for_facts(question, answer, existing)
            if not new_facts:
                return
            merged = _dedupe_facts(existing, new_facts)
            if merged == existing:
                return  # nothing actually changed
            await _upsert_user_memory(db, user_id, merged)
            logger.info(
                "User memory updated",
                extra={
                    "event": "user_memory_updated",
                    "user_id": str(user_id),
                    "total_facts": len(merged),
                    "new_facts": len(merged) - len(existing),
                },
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "Memory update failed",
                extra={"event": "memory_update_failed", "user_id": str(user_id), "error": type(exc).__name__},
            )


def schedule_memory_extraction(
    user_id: UUID,
    question: str,
    answer: str,
) -> None:
    """Non-blocking: schedule memory extraction after a completed turn.

    Uses ``asyncio.create_task`` so the caller returns immediately.
    The background task creates its own DB session so the caller's session
    can commit independently.
    """
    if not answer.strip() or not question.strip():
        return
    try:
        asyncio.create_task(
            _extract_and_save(user_id, question, answer),
            name=f"mem-extract-{user_id}",
        )
    except RuntimeError:
        # No running event loop (test environment). Skip silently.
        pass


def format_memory_for_prompt(facts: list[str]) -> str:
    """Format facts into a concise block for system prompt injection.

    Returns an empty string when there are no facts so the system prompt
    stays clean for new users.
    """
    if not facts:
        return ""
    lines = "\n".join(f"- {f}" for f in facts[:_MAX_FACTS])
    return (
        "Long-term memory (facts the user has shared across past sessions):\n"
        f"{lines}"
    )
