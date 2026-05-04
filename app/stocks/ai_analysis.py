"""AI-powered stock analysis using Google Gemini.

Generates a three-section analysis (chart, news, holdings impact) from
pre-fetched market data.  Results are cached for 15 minutes per symbol.
"""

from __future__ import annotations

import re
import time
from datetime import datetime, timezone
from typing import Any, Optional

from pydantic_ai import Agent
from pydantic_ai.models.google import GoogleModel
from pydantic_ai.providers.google import GoogleProvider

from app.config import get_settings
from app.utils.logging import get_logger

from .schemas import StockAnalysisResponse

logger = get_logger("stocks.ai_analysis")

# ── Cache ────────────────────────────────────────────────────────────

from app.utils.cache import BoundedTTLCache

_cache = BoundedTTLCache(maxsize=512, default_ttl=15 * 60)
_ANALYSIS_TTL = 15 * 60  # 15 minutes


def _cache_get(key: str) -> StockAnalysisResponse | None:
    return _cache.get(key)


def _cache_set(key: str, value: StockAnalysisResponse) -> None:
    _cache.set(key, value, ttl=_ANALYSIS_TTL)


# ── System prompt ────────────────────────────────────────────────────

_SYSTEM_PROMPT = """\
You are an elite financial analyst providing stock analysis for a retail \
investor dashboard. Your analysis must be DIRECT and OPINIONATED - state \
clearly what the data suggests. Do NOT hedge with "it depends" or "consult \
a financial advisor". State the analysis clearly. Use simple language that \
a retail investor can understand.

You will receive market data for a stock and must produce EXACTLY three \
sections using the headers below. Use markdown formatting within each \
section. Each section should be 100–200 words.

## Chart Analysis

Analyze the price chart data following this systematic hierarchy:

1. **Trend identification**: Determine whether the stock is in an uptrend \
(higher highs and higher lows), downtrend (lower highs and lower lows), or \
sideways consolidation. State this clearly.
2. **Key levels**: Identify the most important support and resistance zones \
from the price data - where has price repeatedly bounced or stalled?
3. **Moving average context**: Approximate where price sits relative to the \
200-day and 50-day moving averages from the data provided. Is it above both \
(bullish), below both (bearish), or sandwiched between them (transitional)?
4. **Volume confirmation**: Assess whether the recent price move is confirmed \
by volume. Rising price on rising volume is healthy; rising price on falling \
volume is suspicious.
5. **Momentum assessment**: Is the stock overextended (moved too far too fast) \
or mean-reverting toward a support/resistance level?
6. **Investor takeaway**: For a long-term investor, is this a good entry \
point, an overextended level to wait on, or sitting at key support worth \
watching?

Always end the Chart Analysis with a **What Matters** paragraph summarizing \
the single key takeaway for an investor.

## News Analysis

- Summarize the key recent news themes in 2–3 bullet points.
- Assess overall market sentiment from the news: bullish, bearish, or neutral.
- Note any upcoming catalysts, material risks, or scheduled events.
- Keep it concise and actionable.

## Holdings Impact

This section is ONLY relevant if the user owns the stock. If no position data \
is provided, output exactly: "You do not currently hold this stock."

If the user owns the stock:
- Combine chart analysis + news context + the user's position data (shares, \
average cost, unrealized P&L, portfolio weight).
- Assess: Is the position at risk based on technical and news signals? Is it \
well-timed relative to key levels?
- Flag portfolio concentration concerns if the position weight is high (>10%).
- State what to watch for - specific price levels, upcoming events, or \
momentum shifts that would change the outlook.
- Be direct and factual.

Hard rule: NEVER use the em dash (—) character anywhere in your response. \
Use a regular hyphen (-) or restructure the sentence instead.
"""


def _build_user_prompt(
    symbol: str,
    candles_data: dict,
    quote_data: dict,
    key_stats_data: dict,
    news_articles: list[dict],
    position_data: Optional[dict],
) -> str:
    """Assemble the data payload the LLM will analyze."""
    parts = [f"Analyze **{symbol}** using the data below.\n"]

    parts.append("### Current Quote")
    for k, v in quote_data.items():
        if v is not None:
            parts.append(f"- {k}: {v}")

    parts.append("\n### Key Statistics")
    for k, v in key_stats_data.items():
        if v is not None:
            parts.append(f"- {k}: {v}")

    points = candles_data.get("points", [])
    if points:
        parts.append(f"\n### Price History ({candles_data.get('range', '?')} "
                      f"/ {candles_data.get('interval', '?')}, "
                      f"{len(points)} bars)")
        sample = points if len(points) <= 60 else (
            points[:20] + [{"_note": f"... {len(points) - 40} bars omitted ..."}] + points[-20:]
        )
        for p in sample:
            if "_note" in p:
                parts.append(f"  {p['_note']}")
            else:
                t = p.get("t", "")
                parts.append(
                    f"  {t}  O={p.get('o')}  H={p.get('h')}  "
                    f"L={p.get('low', p.get('l'))}  C={p.get('c')}  V={p.get('v')}"
                )

    if news_articles:
        parts.append(f"\n### Recent News ({len(news_articles)} articles)")
        for a in news_articles[:10]:
            headline = a.get("headline", "")
            summary = a.get("summary", "")
            source = a.get("source", "")
            pub = a.get("published_at", "")
            parts.append(f"- [{source}] {headline}")
            if summary:
                parts.append(f"  {summary[:300]}")
            if pub:
                parts.append(f"  Published: {pub}")

    if position_data and position_data.get("owned"):
        parts.append("\n### User Position")
        for k, v in position_data.items():
            if v is not None:
                parts.append(f"- {k}: {v}")
    else:
        parts.append("\n### User Position")
        parts.append("- The user does NOT currently own this stock.")

    return "\n".join(parts)


# ── Text sanitiser ───────────────────────────────────────────────────

def _sanitise(text: str) -> str:
    """Replace em dashes with a plain hyphen-space for consistent UI display."""
    return text.replace("—", " - ").replace("\u2014", " - ")


# ── Section parser ───────────────────────────────────────────────────

_SECTION_RE = re.compile(
    r"##\s+(Chart Analysis|News Analysis|Holdings Impact)\s*\n",
    re.IGNORECASE,
)


def _parse_sections(text: str) -> dict[str, str]:
    """Split the LLM response into the three named sections."""
    splits = _SECTION_RE.split(text)
    sections: dict[str, str] = {}
    i = 1
    while i < len(splits) - 1:
        header = splits[i].strip().lower()
        body = splits[i + 1].strip()
        if "chart" in header:
            sections["chart"] = body
        elif "news" in header:
            sections["news"] = body
        elif "holding" in header:
            sections["holdings"] = body
        i += 2
    return sections


# ── Public API ───────────────────────────────────────────────────────


async def generate_stock_analysis(
    symbol: str,
    candles_data: dict,
    quote_data: dict,
    key_stats_data: dict,
    news_articles: list[dict],
    position_data: Optional[dict] = None,
) -> StockAnalysisResponse:
    """Generate a comprehensive AI analysis for a stock.

    Returns a cached result when available.  On any LLM failure, returns a
    graceful fallback with a user-friendly message.
    """
    symbol = symbol.upper()
    cache_key = f"ai_analysis:{symbol}"

    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    try:
        settings = get_settings()

        if not settings.google_api_key:
            raise RuntimeError("GOOGLE_API_KEY is not configured")

        model = GoogleModel(
            settings.google_model,
            provider=GoogleProvider(api_key=settings.google_api_key),
        )

        agent: Agent[None, str] = Agent(
            model,
            system_prompt=_SYSTEM_PROMPT,
            output_type=str,
        )

        user_prompt = _build_user_prompt(
            symbol, candles_data, quote_data,
            key_stats_data, news_articles, position_data,
        )

        result = await agent.run(user_prompt)
        raw_text = _sanitise(result.output)

        sections = _parse_sections(raw_text)

        chart = sections.get("chart", "").strip()
        news = sections.get("news", "").strip()
        holdings = sections.get("holdings", "").strip() or None

        if not chart:
            chart = raw_text.strip()
        if not news:
            news = "News analysis could not be generated."

        if position_data and position_data.get("owned"):
            if not holdings:
                holdings = "Holdings impact analysis could not be generated."
        else:
            holdings = None

        response = StockAnalysisResponse(
            symbol=symbol,
            chart_analysis=chart,
            news_analysis=news,
            holdings_impact=holdings,
            generated_at=datetime.now(timezone.utc),
        )

        _cache_set(cache_key, response)
        return response

    except Exception as exc:
        logger.error(
            f"AI analysis failed for {symbol}: {exc}",
            extra={"event": "ai_analysis_error", "symbol": symbol},
        )
        return StockAnalysisResponse(
            symbol=symbol,
            chart_analysis="Analysis is temporarily unavailable. Please try again shortly.",
            news_analysis="News analysis is temporarily unavailable.",
            holdings_impact=(
                "Holdings analysis is temporarily unavailable."
                if position_data and position_data.get("owned")
                else None
            ),
            generated_at=datetime.now(timezone.utc),
        )
