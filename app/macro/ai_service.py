"""AI-powered macro summary generation using Google Gemini."""

from __future__ import annotations

import asyncio
import time
from typing import Any

from pydantic_ai import Agent
from pydantic_ai.models.google import GoogleModel
from pydantic_ai.providers.google import GoogleProvider

from app.config import get_settings
from app.utils.logging import get_logger

from .prompts import MACRO_DETAILED_SUMMARY_PROMPT, MACRO_SUMMARY_PROMPT

logger = get_logger("macro.ai_service")


def _sanitise(text: str) -> str:
    """Replace em dashes with a plain hyphen for consistent UI display."""
    return text.replace("—", " - ").replace("\u2014", " - ")


# Successful results cached for 15 minutes; failed results cached for 3 minutes
# to prevent hammering a transiently overloaded model.
_cache: dict[str, tuple[float, str | None]] = {}
_SUMMARY_TTL = 15 * 60
_FAILURE_TTL = 3 * 60


def _build_macro_prompt(
    indicators: list[dict],
    exposure: dict,
    holdings: list[dict] | None = None,
) -> str:
    parts = ["Current macro indicators:\n"]
    for ind in indicators:
        val = ind.get("display_value", "—")
        chg = ind.get("change_display", "")
        sig = ind.get("signal_label", "")
        parts.append(f"- {ind['label']}: {val} ({chg}) — {sig}")

    parts.append("\nYour portfolio exposure:")
    parts.append(f"- Growth stocks: {exposure.get('growth_pct', 0):.0f}%")
    parts.append(f"- Rate-sensitive: {exposure.get('rate_sensitive_pct', 0):.0f}%")
    parts.append(f"- Cyclical: {exposure.get('cyclical_pct', 0):.0f}%")
    parts.append(f"- Defensive: {exposure.get('defensive_pct', 0):.0f}%")
    parts.append(f"- Energy: {exposure.get('energy_pct', 0):.0f}%")
    parts.append(f"- International revenue: {exposure.get('international_revenue_pct', 0):.0f}%")
    parts.append(f"- Total market value: ${exposure.get('total_market_value', 0):,.0f}")

    if holdings:
        parts.append("\nYour holdings:")
        for h in holdings[:30]:
            sym = h.get("symbol", "")
            sector = h.get("sector", "")
            qty = h.get("quantity", 0)
            price = h.get("current_price", 0)
            mv = float(qty or 0) * float(price or 0)
            if mv > 0:
                parts.append(f"- {sym} ({sector or 'Unknown'}) — ${mv:,.0f}")

    return "\n".join(parts)


def _cache_key(indicators: list[dict], exposure: dict, suffix: str = "") -> str:
    vals = "|".join(str(i.get("value", "")) for i in indicators)
    exp_key = f"{exposure.get('growth_pct', 0)}-{exposure.get('rate_sensitive_pct', 0)}"
    return f"macro_summary{suffix}:{vals}:{exp_key}"


async def _run_llm_with_retry(
    system_prompt: str,
    user_prompt: str,
    *,
    max_attempts: int = 3,
    base_delay: float = 2.0,
) -> str | None:
    """Call the LLM with exponential-backoff retry on 429/503 transient errors."""
    settings = get_settings()
    if not settings.google_api_key:
        return None

    model = GoogleModel(
        settings.google_model,
        provider=GoogleProvider(api_key=settings.google_api_key),
    )
    agent: Agent[None, str] = Agent(
        model,
        system_prompt=system_prompt,
        output_type=str,
    )

    last_exc: Exception | None = None
    for attempt in range(max_attempts):
        try:
            result = await agent.run(user_prompt)
            return _sanitise(result.output.strip())
        except Exception as exc:
            last_exc = exc
            msg = str(exc).lower()
            is_transient = "503" in msg or "429" in msg or "unavailable" in msg or "overload" in msg
            if not is_transient or attempt == max_attempts - 1:
                raise
            delay = base_delay * (2 ** attempt)
            logger.warning(f"LLM transient error (attempt {attempt + 1}/{max_attempts}), retrying in {delay:.1f}s: {exc}")
            await asyncio.sleep(delay)

    if last_exc:
        raise last_exc
    return None


async def generate_macro_summary(
    indicators: list[dict],
    exposure: dict,
) -> str | None:
    """Generate a short AI macro briefing for the top of the page."""
    key = _cache_key(indicators, exposure)
    cached = _cache.get(key)
    if cached:
        ts, val = cached
        ttl = _SUMMARY_TTL if val is not None else _FAILURE_TTL
        if (time.time() - ts) < ttl:
            return val

    try:
        user_prompt = _build_macro_prompt(indicators, exposure)
        summary = await _run_llm_with_retry(MACRO_SUMMARY_PROMPT, user_prompt)
        _cache[key] = (time.time(), summary)
        return summary
    except Exception as exc:
        logger.error(f"Macro summary generation failed: {exc}")
        _cache[key] = (time.time(), None)  # short-circuit repeated 503s
        return None


async def generate_detailed_macro_summary(
    indicators: list[dict],
    exposure: dict,
    holdings: list[dict] | None = None,
) -> str | None:
    """Generate a comprehensive AI macro summary for the bottom of the page."""
    key = _cache_key(indicators, exposure, suffix=":detailed")
    cached = _cache.get(key)
    if cached:
        ts, val = cached
        ttl = _SUMMARY_TTL if val is not None else _FAILURE_TTL
        if (time.time() - ts) < ttl:
            return val

    try:
        user_prompt = _build_macro_prompt(indicators, exposure, holdings)
        summary = await _run_llm_with_retry(MACRO_DETAILED_SUMMARY_PROMPT, user_prompt)
        _cache[key] = (time.time(), summary)
        return summary
    except Exception as exc:
        logger.error(f"Detailed macro summary generation failed: {exc}")
        _cache[key] = (time.time(), None)
        return None
