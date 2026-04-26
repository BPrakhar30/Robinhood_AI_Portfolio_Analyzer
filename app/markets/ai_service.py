"""AI enrichment for market news and earnings.

Separate Gemini agent (no MCP, no chat history) so markets summarization is
decoupled from the portfolio assistant:

* Different system prompts, tuned for news editing vs. portfolio analysis.
* No per-user deps or tool calls to the DB (news is public data).
* Batched calls — one LLM request summarizes 10–15 articles at once to fit
  inside Gemini's free-tier 10 RPM without blowing the budget on reloads.
* In-memory TTL cache keyed by a hash of the article URL, so identical
  articles aren't re-summarized every time a client refreshes.

Failure mode: if the LLM is unreachable or the Google key is missing, the
enrichers return the original raw summaries/excerpts. Markets UI never blocks
on AI.
"""

from __future__ import annotations

import asyncio
import hashlib
import time
from functools import lru_cache
from typing import Any, Optional

from pydantic_ai import Agent
from pydantic_ai.exceptions import ModelHTTPError
from pydantic_ai.models.google import GoogleModel
from pydantic_ai.providers.google import GoogleProvider

from app.config import get_settings
from app.utils.logging import get_logger

from .prompts import (
    DEVELOPMENT_SUMMARY_PROMPT,
    HEADLINE_SUMMARY_PROMPT,
    PORTFOLIO_NEWS_SUMMARY_PROMPT,
)

import re

# Belt-and-suspenders: strip any filler the model still emits despite the
# prompt forbidding it. Catches "(details pending)", "details pending.",
# "(more to come)", "story developing", etc. Case-insensitive.
_FILLER_RE = re.compile(
    r"\s*[\(\[]?\s*(?:details pending|more to come|story developing|"
    r"developing story|details to follow|to be confirmed|tbd)\s*[\.\)\]]?\s*",
    re.IGNORECASE,
)


def _strip_filler(text: Optional[str]) -> Optional[str]:
    if not text:
        return text
    cleaned = _FILLER_RE.sub(" ", text)
    cleaned = re.sub(r"\s{2,}", " ", cleaned).strip()
    cleaned = cleaned.rstrip(" .,;:") + ("." if cleaned and cleaned[-1].isalnum() else "")
    return cleaned or None


_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")


def _enforce_summary_shape(text: Optional[str], *, max_words: int = 80) -> Optional[str]:
    """Trim summaries to whole sentences within ``max_words`` and end with a period.

    Used for the Market Summary headlines so a single rambling LLM response
    can't blow past 80 words or end on a fragment / ellipsis / comma.
    """
    if not text:
        return text

    sentences = [s.strip() for s in _SENTENCE_SPLIT_RE.split(text) if s.strip()]
    if not sentences:
        return None

    kept: list[str] = []
    word_total = 0
    for sentence in sentences:
        word_count = len(sentence.split())
        if kept and word_total + word_count > max_words:
            break
        kept.append(sentence)
        word_total += word_count

    out = " ".join(kept).strip()
    if not out:
        return None
    if out[-1] not in ".!?":
        out = out.rstrip(" ,;:-—…") + "."
    return out

logger = get_logger("markets.ai_service")


# ── Caching ───────────────────────────────────────────────────────────

_SUMMARY_TTL_SECONDS = 1800  # 30 minutes — long enough to dodge reload storms
_summary_cache: dict[str, tuple[float, str]] = {}


def _hash_url(url: str, title: str) -> str:
    """Stable short key combining URL + title (titles change for same URL rarely)."""
    return hashlib.sha1(f"{url}|{title[:80]}".encode("utf-8")).hexdigest()[:16]


def _cache_get(key: str) -> Optional[str]:
    entry = _summary_cache.get(key)
    if entry and (time.time() - entry[0]) < _SUMMARY_TTL_SECONDS:
        return entry[1]
    return None


def _cache_set(key: str, value: str) -> None:
    _summary_cache[key] = (time.time(), value)


# ── Agent construction ───────────────────────────────────────────────


@lru_cache(maxsize=1)
def _summarizer_agent() -> Agent[None, list[str]]:
    """Stateless batch summarizer. Structured output: list of strings, one per input."""
    settings = get_settings()
    if not settings.google_api_key:
        raise RuntimeError("GOOGLE_API_KEY is not configured")
    model = GoogleModel(
        settings.google_model,
        provider=GoogleProvider(api_key=settings.google_api_key),
    )
    # No system prompt here — we pass it per call so headlines and dev cards
    # share one agent instance with different framing.
    return Agent(model, output_type=list[str])


# ── Helpers ──────────────────────────────────────────────────────────


def _format_articles_for_prompt(articles: list[dict[str, Any]]) -> str:
    """Render articles into a numbered block the LLM can summarize positionally."""
    lines: list[str] = []
    for i, art in enumerate(articles, start=1):
        title = (art.get("title") or "").strip()
        source = (art.get("source") or "").strip()
        excerpt = (art.get("summary") or art.get("excerpt") or "").strip()
        # Truncate aggressively to keep the batch prompt well under 10k tokens.
        if len(excerpt) > 400:
            excerpt = excerpt[:400] + "…"
        lines.append(
            f"[{i}] Title: {title}\n"
            f"    Source: {source}\n"
            f"    Excerpt: {excerpt or '(no excerpt)'}"
        )
    return "\n\n".join(lines)


async def _batch_summarize(
    articles: list[dict[str, Any]],
    system_prompt: str,
    *,
    kind: str,
) -> list[Optional[str]]:
    """Summarize a batch of articles in a single LLM call.

    Returns a list aligned with ``articles``. On any failure, returns
    ``[None] * len(articles)`` so callers fall back to raw excerpts.
    """
    if not articles:
        return []

    try:
        agent = _summarizer_agent()
    except RuntimeError as exc:
        logger.debug(f"Markets AI disabled ({kind}): {exc}")
        return [None] * len(articles)

    prompt = (
        f"{system_prompt}\n\n"
        f"Here are the {len(articles)} articles:\n\n"
        f"{_format_articles_for_prompt(articles)}\n\n"
        f"Return exactly {len(articles)} summaries, in order."
    )

    try:
        result = await agent.run(prompt)
        summaries = result.output
    except ModelHTTPError as exc:
        logger.warning(
            f"Markets {kind} summarization rate-limited or upstream error: "
            f"status={exc.status_code}"
        )
        return [None] * len(articles)
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"Markets {kind} summarization failed: {exc}")
        return [None] * len(articles)

    # Guard against count mismatch — pad/truncate to input length.
    if len(summaries) < len(articles):
        summaries = summaries + [None] * (len(articles) - len(summaries))  # type: ignore[list-item]
    elif len(summaries) > len(articles):
        summaries = summaries[: len(articles)]

    cleaned: list[Optional[str]] = []
    for s in summaries:
        if not isinstance(s, str):
            cleaned.append(None)
            continue
        stripped = _strip_filler(s)
        cleaned.append(stripped or None)
    return cleaned


# ── Public: enrichment pipelines ─────────────────────────────────────


async def enrich_headlines(headlines: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Attach ``ai_summary`` to each headline. Cached per URL.

    Summaries are clamped to ≤80 words ending on a complete sentence so the
    Market Summary list stays scannable.
    """
    if not headlines:
        return headlines

    # ``:hl2`` cache namespace forces a refresh after the prompt rewrite —
    # old prose summaries cached under the previous key shape are ignored.
    keys = [_hash_url(h.get("url", ""), h.get("title", "")) + ":hl2" for h in headlines]
    cached = [_cache_get(k) for k in keys]

    misses = [i for i, c in enumerate(cached) if c is None]
    new_summaries: list[Optional[str]] = []
    if misses:
        new_summaries = await _batch_summarize(
            [headlines[i] for i in misses],
            HEADLINE_SUMMARY_PROMPT,
            kind="headlines",
        )
        new_summaries = [_enforce_summary_shape(s) for s in new_summaries]
        for i, s in zip(misses, new_summaries):
            if s:
                _cache_set(keys[i], s)

    miss_iter = iter(new_summaries)
    enriched: list[dict[str, Any]] = []
    for head, cached_summary in zip(headlines, cached):
        ai_summary = cached_summary if cached_summary is not None else next(miss_iter, None)
        enriched.append({**head, "ai_summary": ai_summary})
    return enriched


async def enrich_developments(articles: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Attach ``ai_summary`` to each development card. Cached per URL."""
    if not articles:
        return articles

    keys = [_hash_url(a.get("url", ""), a.get("title", "")) for a in articles]
    cached = [_cache_get(k + ":dev") for k in keys]

    misses = [i for i, c in enumerate(cached) if c is None]
    new_summaries: list[Optional[str]] = []
    if misses:
        new_summaries = await _batch_summarize(
            [articles[i] for i in misses],
            DEVELOPMENT_SUMMARY_PROMPT,
            kind="developments",
        )
        for i, s in zip(misses, new_summaries):
            if s:
                _cache_set(keys[i] + ":dev", s)

    miss_iter = iter(new_summaries)
    enriched: list[dict[str, Any]] = []
    for art, cached_summary in zip(articles, cached):
        ai_summary = cached_summary if cached_summary is not None else next(miss_iter, None)
        enriched.append({**art, "ai_summary": ai_summary})
    return enriched


# Strips ANY combination of leading bullet glyphs, dashes, asterisks, and
# whitespace — handles models that emit "• ", "** ", "- ", and even nested
# garbage like "• • " or "* - " at the start of a line.
_LEADING_BULLET_RE = re.compile(r"^[\u2022\u2023\u25E6\u2043\-\*\s]+")


def _normalize_three_bullets(raw: str, headline: str) -> str:
    """Coerce model output into up to three "• " bullets, one per line.

    Guarantees:
      * Each line starts with exactly one "• " (frontend re-renders the
        glyph itself, so a stray bullet from the model can never produce
        the dreaded double-bullet "• • text" rendering).
      * No two bullets carry the same content (case-insensitive). The
        previous implementation padded with the headline when the model
        returned <3 unique points, which is what produced the duplicate
        third bullet visible in the UI screenshot.
      * Returns whatever number of UNIQUE bullets we actually have — 1,
        2, or 3. The frontend handles partial counts gracefully.

    ``headline`` is unused for padding (intentional) but kept in the
    signature in case future callers want it for ranking heuristics.
    """
    del headline  # padding is intentionally disabled
    text = _strip_filler(raw) or ""

    raw_lines: list[str] = []
    for line in text.splitlines():
        cleaned = _LEADING_BULLET_RE.sub("", line).strip()
        cleaned = re.sub(r"^\d+[\.\)]\s*", "", cleaned).strip()
        if cleaned:
            raw_lines.append(cleaned)

    # If the model emitted prose instead of bullets, fall back to
    # sentence-splitting on the original text.
    if len(raw_lines) < 2:
        raw_lines = [
            s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()
        ]

    seen: set[str] = set()
    unique: list[str] = []
    for line in raw_lines:
        key = re.sub(r"\s+", " ", line).strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        unique.append(line.rstrip("."))
        if len(unique) == 3:
            break

    return "\n".join(f"• {line}." for line in unique)


async def enrich_portfolio_news(articles: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Attach a strict 3-bullet ``ai_summary`` to each portfolio-news card.

    Cached separately from headlines/developments so the 3-bullet shape
    can never be polluted by a previously cached prose summary.
    """
    if not articles:
        return articles

    # ``:pnews2`` namespace forces a refresh after the dedupe-and-no-padding
    # rewrite; the previous ``:pnews`` cache is full of headline-padded
    # entries that produced duplicate bullets in the UI.
    keys = [_hash_url(a.get("url", ""), a.get("title", "")) + ":pnews2" for a in articles]
    cached = [_cache_get(k) for k in keys]

    misses = [i for i, c in enumerate(cached) if c is None]
    new_summaries: list[Optional[str]] = []
    if misses:
        new_summaries = await _batch_summarize(
            [articles[i] for i in misses],
            PORTFOLIO_NEWS_SUMMARY_PROMPT,
            kind="portfolio_news",
        )
        for i, s in zip(misses, new_summaries):
            if s:
                normalized = _normalize_three_bullets(s, articles[i].get("title", ""))
                if normalized:
                    _cache_set(keys[i], normalized)

    miss_iter = iter(new_summaries)
    enriched: list[dict[str, Any]] = []
    for art, cached_summary in zip(articles, cached):
        if cached_summary is not None:
            ai_summary = cached_summary
        else:
            raw = next(miss_iter, None)
            normalized = _normalize_three_bullets(raw or "", art.get("title", ""))
            ai_summary = normalized or None
        enriched.append({**art, "ai_summary": ai_summary})
    return enriched


async def enrich_news_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Run headlines + developments enrichment in parallel.

    Mutates a copy of the input payload. Safe to call even when AI is disabled
    (it just returns the payload unchanged).
    """
    headlines = payload.get("headlines", []) or []
    articles = payload.get("articles", []) or []

    enriched_headlines, enriched_articles = await asyncio.gather(
        enrich_headlines(headlines),
        enrich_developments(articles),
    )
    return {
        **payload,
        "headlines": enriched_headlines,
        "articles": enriched_articles,
    }
