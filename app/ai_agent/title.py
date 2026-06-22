"""LLM-generated, de-duplicated chat session titles.

Invoked exactly once per session  -  after the first assistant turn finishes  - 
to replace the default ``"New chat"`` placeholder with a short, human
title. Kept in its own module so the prompt can evolve independently of the
main assistant agent, and so caching / fallback behaviour is explicit.

Design notes:

* A tiny Gemini agent (no tools, structured string output) is fast and cheap
  enough to run inline on the first turn without noticeably extending the
  request. If it fails, we fall back to a truncated user prompt so the user
  never sees a literal "New chat" row for a session that already has content.
* Emoji / pictograph stripping is done post-LLM because (a) models still
  leak emoji occasionally despite the prompt and (b) we want deterministic
  behaviour regardless of model drift.
* De-duplication is a two-step guard: we pass existing titles into the
  prompt AND enforce uniqueness ourselves after generation (appending a
  numeric suffix if needed). The prompt alone is not strong enough on
  free-tier models.
"""

from __future__ import annotations

import re
from functools import lru_cache
from typing import Iterable, Optional

from pydantic_ai import Agent
from pydantic_ai.exceptions import ModelHTTPError
from pydantic_ai.models.google import GoogleModel
from pydantic_ai.providers.google import GoogleProvider

from app.config import get_settings
from app.utils.logging import get_logger

logger = get_logger("ai_agent.title")

# Hard cap  -  titles truncate here if the model over-produces.
_MAX_TITLE_CHARS = 60
# Fallback source: first N chars of the user prompt when the LLM is
# unavailable. Shorter than ``_MAX_TITLE_CHARS`` so it reads like a title.
_FALLBACK_CHARS = 50

# Unicode ranges for emoji / pictographic / dingbat glyphs. ``re.UNICODE``
# is implicit in Python 3  -  kept explicit here as a readability cue.
_EMOJI_RE = re.compile(
    "["
    "\U0001F300-\U0001F6FF"  # misc symbols & pictographs, transport
    "\U0001F700-\U0001F77F"  # alchemical
    "\U0001F780-\U0001F7FF"  # geometric shapes ext.
    "\U0001F800-\U0001F8FF"  # supplemental arrows-c
    "\U0001F900-\U0001F9FF"  # supplemental symbols & pictographs
    "\U0001FA00-\U0001FA6F"  # chess symbols
    "\U0001FA70-\U0001FAFF"  # symbols & pictographs ext-a
    "\U00002600-\U000026FF"  # misc symbols (e.g. ☀, ☂)
    "\U00002700-\U000027BF"  # dingbats (e.g. ✂, ✔)
    "\U0001F1E6-\U0001F1FF"  # regional indicators (flags)
    "\u200d"                  # ZWJ used in emoji sequences
    "\ufe0f"                  # variation selector-16
    "]+",
    flags=re.UNICODE,
)

_TITLE_SYSTEM_PROMPT = """\
You generate concise session titles for a portfolio-analysis chat assistant.

Hard requirements:
- Return a single title, 3-7 words, Title Case.
- Maximum 60 characters. No trailing punctuation.
- Describe the topic, not the format (good: "Tech Sector Concentration Risk";
  bad: "User Question About My Portfolio").
- Absolutely no emoji, pictographs, icons, or decorative symbols of any kind.
- Do NOT use any of the "Existing titles" provided  -  pick a clearly distinct
  wording. Near-duplicates (same first 2-3 words) also count as collisions.
- Do NOT wrap the title in quotes or add any prefix like "Title:".

Output ONLY the title text. Nothing else.
"""


@lru_cache(maxsize=1)
def _title_agent() -> Agent[None, str]:
    """Lazily built, process-wide singleton title agent."""
    settings = get_settings()
    if not settings.google_api_key:
        raise RuntimeError("GOOGLE_API_KEY is not configured")
    model = GoogleModel(
        settings.google_model,
        provider=GoogleProvider(api_key=settings.google_api_key),
    )
    return Agent(model, system_prompt=_TITLE_SYSTEM_PROMPT, output_type=str)


def _strip_emoji(text: str) -> str:
    """Drop emoji / pictographs the model may emit despite the prompt."""
    return _EMOJI_RE.sub("", text)


def _clean(text: str) -> str:
    """Normalize model output into a presentable title.

    - Drops leading/trailing quotes, asterisks, and whitespace.
    - Collapses inner whitespace to single spaces.
    - Strips trailing punctuation (periods, commas, colons).
    - Enforces ``_MAX_TITLE_CHARS`` hard cap.
    """
    if not text:
        return ""
    text = _strip_emoji(text).strip()
    # Model sometimes wraps in quotes/backticks AND prefixes with "Title: ",
    # in either order. Strip quotes first so the prefix regex can match.
    text = text.strip("\"'`*").strip()
    text = re.sub(r"^(title\s*:\s*)", "", text, flags=re.IGNORECASE)
    text = text.strip("\"'`*").strip()
    text = re.sub(r"\s+", " ", text)
    text = text.rstrip(".,:;!?")
    if len(text) > _MAX_TITLE_CHARS:
        text = text[:_MAX_TITLE_CHARS].rstrip()
    return text


def _disambiguate(title: str, existing: Iterable[str]) -> str:
    """Append a numeric suffix if ``title`` collides with an existing one.

    Case-insensitive exact match only  -  near-duplicates are the model's job.
    """
    existing_lower = {t.strip().lower() for t in existing if t and t.strip()}
    if title.lower() not in existing_lower:
        return title

    for i in range(2, 100):
        candidate = f"{title} ({i})"
        if candidate.lower() not in existing_lower:
            return candidate
    # Extreme edge case: 100 collisions. Let it through  -  better than blocking.
    return title


def _fallback_title(question: str, existing: Iterable[str]) -> str:
    """Deterministic title when the LLM is unreachable or misbehaves."""
    base = _clean(question)[:_FALLBACK_CHARS].strip() or "New Chat"
    return _disambiguate(base, existing)


async def generate_session_title(
    *,
    question: str,
    answer: str,
    existing_titles: Iterable[str],
) -> Optional[str]:
    """Produce a short, unique session title for the first turn.

    Returns ``None`` only if both the LLM call and the fallback somehow fail,
    letting the caller keep the ``"New chat"`` placeholder.
    """
    existing_list = list(existing_titles)

    try:
        agent = _title_agent()
    except RuntimeError as exc:
        logger.debug("Auto-title LLM disabled: %s", exc)
        return _fallback_title(question, existing_list)

    existing_block = (
        "\n".join(f"- {t}" for t in existing_list[:25]) if existing_list else "(none)"
    )
    # Trim answer aggressively  -  context for the model, not a document.
    answer_snippet = (answer or "").strip().replace("\n", " ")
    if len(answer_snippet) > 400:
        answer_snippet = answer_snippet[:400] + "…"
    question_snippet = (question or "").strip()
    if len(question_snippet) > 400:
        question_snippet = question_snippet[:400] + "…"

    user_prompt = (
        "Generate the session title now.\n\n"
        f"User's first message:\n{question_snippet}\n\n"
        f"Assistant's first reply (for topic context):\n{answer_snippet}\n\n"
        f"Existing titles to avoid (do not reuse, do not near-duplicate):\n{existing_block}\n\n"
        "Return ONLY the title."
    )

    try:
        result = await agent.run(user_prompt)
    except ModelHTTPError as exc:
        logger.warning("Auto-title upstream error: status=%s", exc.status_code)
        return _fallback_title(question, existing_list)
    except Exception as exc:  # noqa: BLE001 - titling must never break a turn
        logger.warning("Auto-title failed: %s", exc)
        return _fallback_title(question, existing_list)

    cleaned = _clean(str(result.output))
    if not cleaned:
        return _fallback_title(question, existing_list)

    unique = _disambiguate(cleaned, existing_list)
    logger.info(
        "Auto-title generated",
        extra={"event": "chat_title_generated", "title": unique},
    )
    return unique
