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


def _sanitise(text: str) -> str:
    """Replace em dashes with a plain hyphen for consistent UI display."""
    return text.replace("—", " - ").replace("\u2014", " - ")


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
        summaries = [_sanitise(s) if isinstance(s, str) else s for s in result.output]
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


_SENTIMENT_RE = re.compile(
    r"^SENTIMENT:\s*(POSITIVE|NEGATIVE|NEUTRAL)\s*$",
    re.IGNORECASE | re.MULTILINE,
)


def _extract_bullets_and_sentiment(raw_block: str) -> tuple[list[str], str]:
    """Parse a single article's LLM output into (bullets_list, sentiment).

    Handles every observed LLM output format: bullet lines, numbered
    lines, prose, inline bullets, and sentiment tags.
    """
    text = _strip_filler(raw_block) or ""

    sentiment = "neutral"
    sm = _SENTIMENT_RE.search(text)
    if sm:
        sentiment = sm.group(1).lower()
        text = _SENTIMENT_RE.sub("", text).strip()

    raw_lines: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if re.match(r"^SENTIMENT:", stripped, re.IGNORECASE):
            continue
        cleaned = _LEADING_BULLET_RE.sub("", stripped).strip()
        cleaned = re.sub(r"^\d+[\.\)]\s*", "", cleaned).strip()
        if not cleaned:
            continue
        for part in re.split(r"\s*[•]\s*", cleaned):
            part = part.strip()
            if part and not re.match(r"^SENTIMENT:", part, re.IGNORECASE):
                raw_lines.append(part)

    if len(raw_lines) < 2:
        raw_lines = [
            s.strip()
            for s in re.split(r"(?<=[.!?])\s+", text)
            if s.strip() and not re.match(r"^SENTIMENT:", s.strip(), re.IGNORECASE)
        ]

    seen: set[str] = set()
    unique: list[str] = []
    for line in raw_lines:
        normalized = re.sub(r"\s+", " ", line).strip()
        key = normalized.lower()
        if not key or key in seen:
            continue
        seen.add(key)
        if not normalized.endswith((".","!","?")):
            normalized += "."
        unique.append(normalized)
        if len(unique) == 3:
            break

    return unique, sentiment


def _format_cached_entry(bullets: list[str], sentiment: str) -> str:
    """Serialize bullets + sentiment into a stable JSON cache entry."""
    import json
    return json.dumps({"bullets": bullets, "sentiment": sentiment})


def _parse_cached_entry(raw: str) -> tuple[list[str], str]:
    """Deserialize a cached JSON entry. Falls back gracefully."""
    import json
    try:
        data = json.loads(raw)
        return data["bullets"], data["sentiment"]
    except (json.JSONDecodeError, KeyError, TypeError):
        return [], "neutral"


_POSITIVE_KEYWORDS = re.compile(
    r"\b(bullish|positive|upside|benefit|gain|growth|beat|strong|upgrade|"
    r"outperform|opportunity|tailwind|favorable|holders.*benefit|"
    r"good news|encouraging|well.?positioned)\b",
    re.IGNORECASE,
)
_NEGATIVE_KEYWORDS = re.compile(
    r"\b(bearish|negative|downside|risk|loss|decline|miss|weak|downgrade|"
    r"underperform|threat|headwind|concern|caution|holders.*risk|"
    r"bad news|worrying|pressure|vulnerable|warning)\b",
    re.IGNORECASE,
)


def _infer_sentiment(bullets: list[str]) -> str:
    """Infer sentiment from bullet content when the LLM omits the tag.

    Scans all bullets (especially bullet 3 — portfolio impact) for
    positive/negative signal words. Returns "positive", "negative", or
    "neutral".
    """
    text = " ".join(bullets)
    pos = len(_POSITIVE_KEYWORDS.findall(text))
    neg = len(_NEGATIVE_KEYWORDS.findall(text))
    if pos > neg:
        return "positive"
    if neg > pos:
        return "negative"
    return "neutral"


async def _portfolio_news_raw_summarize(
    articles: list[dict[str, Any]],
) -> Optional[str]:
    """Call the LLM with raw text output (not list[str]) for portfolio news.

    Returns the full raw text from the model, or None on failure.
    Using raw text avoids the list[str] structured-output problem where
    PydanticAI splits multi-line bullets into separate list elements.
    """
    if not articles:
        return None

    settings = get_settings()
    if not settings.google_api_key:
        return None

    try:
        model = GoogleModel(
            settings.google_model,
            provider=GoogleProvider(api_key=settings.google_api_key),
        )
        agent: Agent[None, str] = Agent(model, output_type=str)

        prompt = (
            f"{PORTFOLIO_NEWS_SUMMARY_PROMPT}\n\n"
            f"Here are the {len(articles)} articles:\n\n"
            f"{_format_articles_for_prompt(articles)}\n\n"
            f"Produce the bullet blocks now. Remember: EVERY article "
            f"MUST have exactly 3 bullets AND a SENTIMENT tag."
        )

        result = await agent.run(prompt)
        return _sanitise(result.output)
    except ModelHTTPError as exc:
        logger.warning(f"Portfolio news summarization rate-limited: status={exc.status_code}")
        return None
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"Portfolio news summarization failed: {exc}")
        return None


def _extract_all_sentiments(raw: str) -> list[str]:
    """Extract ALL SENTIMENT tags from the raw LLM output in order.

    This runs BEFORE block splitting so sentiment tags are never lost
    to incorrect block boundaries.
    """
    return [m.group(1).lower() for m in _SENTIMENT_RE.finditer(raw)]


def _split_raw_into_article_blocks(raw: str, article_count: int) -> list[str]:
    """Split the raw LLM output into per-article blocks.

    First strips all SENTIMENT lines (already extracted separately),
    then splits on blank lines and merges to match article count.
    """
    clean = _SENTIMENT_RE.sub("", raw).strip()
    blocks = re.split(r"\n\s*\n", clean)
    blocks = [b.strip() for b in blocks if b.strip()]

    if len(blocks) == article_count:
        return blocks

    if len(blocks) > article_count:
        merged: list[str] = []
        per = max(1, len(blocks) // article_count)
        for i in range(article_count):
            start = i * per
            end = start + per if i < article_count - 1 else len(blocks)
            merged.append("\n".join(blocks[start:end]))
        return merged

    while len(blocks) < article_count:
        blocks.append("")
    return blocks[:article_count]


async def enrich_portfolio_news(articles: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Attach a 3-bullet ``ai_summary`` and ``sentiment`` to each portfolio-news card.

    Architecture:
    1. Extract ALL SENTIMENT tags from the raw text BEFORE splitting —
       this prevents tags from being lost to block-boundary errors.
    2. Strip sentiment lines, then split into per-article bullet blocks.
    3. For any article missing an explicit SENTIMENT tag, infer it from
       bullet content using keyword matching (ensures every article
       always has a sentiment).
    4. Cache as JSON for stability.
    """
    if not articles:
        return articles

    cache_ns = ":pnews5"
    keys = [_hash_url(a.get("url", ""), a.get("title", "")) + cache_ns for a in articles]
    cached = [_cache_get(k) for k in keys]

    misses = [i for i, c in enumerate(cached) if c is None]
    if misses:
        miss_articles = [articles[i] for i in misses]
        raw_text = await _portfolio_news_raw_summarize(miss_articles)

        if raw_text:
            sentiments = _extract_all_sentiments(raw_text)
            blocks = _split_raw_into_article_blocks(raw_text, len(miss_articles))

            for idx, (miss_i, block) in enumerate(zip(misses, blocks)):
                bullets, _block_sentiment = _extract_bullets_and_sentiment(block)

                if idx < len(sentiments):
                    sentiment = sentiments[idx]
                elif _block_sentiment != "neutral":
                    sentiment = _block_sentiment
                else:
                    sentiment = _infer_sentiment(bullets)

                entry = _format_cached_entry(bullets, sentiment)
                _cache_set(keys[miss_i], entry)
                cached[miss_i] = entry

    enriched: list[dict[str, Any]] = []
    for art, entry in zip(articles, cached):
        if entry is not None:
            bullets, sentiment = _parse_cached_entry(entry)
        else:
            bullets, sentiment = [], "neutral"

        if sentiment == "neutral" and bullets:
            sentiment = _infer_sentiment(bullets)

        ai_summary = "\n".join(f"• {b}" for b in bullets) if bullets else None
        enriched.append({**art, "ai_summary": ai_summary, "sentiment": sentiment})
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
