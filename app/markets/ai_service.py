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
from pydantic_ai.common_tools.duckduckgo import duckduckgo_search_tool
from pydantic_ai.exceptions import ModelHTTPError
from pydantic_ai.models.google import GoogleModel
from pydantic_ai.providers.google import GoogleProvider

from app.config import get_settings
from app.utils.logging import get_logger

from .prompts import (
    DEVELOPMENT_SUMMARY_PROMPT,
    EARNINGS_HIGHLIGHTS_PROMPT,
    HEADLINE_SUMMARY_PROMPT,
)

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


@lru_cache(maxsize=1)
def _earnings_agent() -> Agent[None, str]:
    """Agent with a web-search tool for earnings research."""
    settings = get_settings()
    if not settings.google_api_key:
        raise RuntimeError("GOOGLE_API_KEY is not configured")
    model = GoogleModel(
        settings.google_model,
        provider=GoogleProvider(api_key=settings.google_api_key),
    )
    return Agent(
        model,
        system_prompt=EARNINGS_HIGHLIGHTS_PROMPT,
        output_type=str,
        tools=[duckduckgo_search_tool()],
    )


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

    return [s.strip() if isinstance(s, str) and s.strip() else None for s in summaries]


# ── Public: enrichment pipelines ─────────────────────────────────────


async def enrich_headlines(headlines: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Attach ``ai_summary`` to each headline. Cached per URL."""
    if not headlines:
        return headlines

    keys = [_hash_url(h.get("url", ""), h.get("title", "")) for h in headlines]
    cached = [_cache_get(k) for k in keys]

    # Only hit the model for misses.
    misses = [i for i, c in enumerate(cached) if c is None]
    new_summaries: list[Optional[str]] = []
    if misses:
        new_summaries = await _batch_summarize(
            [headlines[i] for i in misses],
            HEADLINE_SUMMARY_PROMPT,
            kind="headlines",
        )
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


# ── Earnings highlights ──────────────────────────────────────────────


_earnings_cache: dict[str, tuple[float, str]] = {}
_EARNINGS_TTL_SECONDS = 3600  # 1 hour — earnings data is stable per quarter


def _earnings_cache_key(symbol: str, quarter: int, year: int) -> str:
    return f"earn::{symbol.upper()}::{year}Q{quarter}"


async def generate_earnings_highlights(
    *,
    symbol: str,
    company: str,
    quarter: int,
    year: int,
    eps_estimate: Optional[float] = None,
    eps_actual: Optional[float] = None,
    revenue_estimate: Optional[float] = None,
    revenue_actual: Optional[float] = None,
    reported: bool = True,
) -> Optional[str]:
    """Produce a markdown highlights brief for a single earnings entry.

    Returns ``None`` on failure so the UI can show a graceful "unavailable"
    state (not a stack trace).
    """
    key = _earnings_cache_key(symbol, quarter, year)
    entry = _earnings_cache.get(key)
    if entry and (time.time() - entry[0]) < _EARNINGS_TTL_SECONDS:
        return entry[1]

    try:
        agent = _earnings_agent()
    except RuntimeError as exc:
        logger.debug(f"Earnings AI disabled: {exc}")
        return None

    known_lines = [f"Symbol: {symbol}", f"Company: {company}", f"Quarter: Q{quarter} {year}"]
    if eps_estimate is not None:
        known_lines.append(f"EPS estimate: ${eps_estimate:.2f}")
    if eps_actual is not None:
        known_lines.append(f"EPS actual: ${eps_actual:.2f}")
    if revenue_estimate is not None:
        known_lines.append(f"Revenue estimate: ${revenue_estimate:,.0f}")
    if revenue_actual is not None:
        known_lines.append(f"Revenue actual: ${revenue_actual:,.0f}")
    known_lines.append(f"Status: {'Reported' if reported else 'Not yet reported'}")

    prompt = (
        "Produce the highlights brief for this earnings event.\n\n"
        + "\n".join(known_lines)
        + "\n\nUse the duckduckgo_search tool if you need the most recent public "
        "details (guidance, product news, segment colour). Do not invent numbers."
    )

    try:
        result = await agent.run(prompt)
        text = result.output.strip()
    except ModelHTTPError as exc:
        logger.warning(
            f"Earnings highlights upstream error for {symbol}: status={exc.status_code}"
        )
        return None
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"Earnings highlights failed for {symbol}: {exc}")
        return None

    _earnings_cache[key] = (time.time(), text)
    return text
