"""Macro Pulse data service.

Fetches macro indicators via yfinance batch download and computes
portfolio exposure scores from user positions. All yfinance calls
run in ``asyncio.to_thread`` to avoid blocking the event loop.

Results are globally cached (indicators are the same for every user)
and per-user cached (exposure scores depend on holdings).
"""

from __future__ import annotations

import asyncio
import json
import time
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

from app.utils.logging import get_logger

try:
    import yfinance as yf

    _YF = True
except Exception:
    yf = None  # type: ignore[assignment]
    _YF = False

logger = get_logger("macro.service")

# ── Caches ────────────────────────────────────────────────────────────

from app.utils.cache import BoundedTTLCache

_indicator_cache = BoundedTTLCache(maxsize=128, default_ttl=5 * 60)
_INDICATOR_TTL = 5 * 60  # 5 minutes  -  macro tickers move slowly

_exposure_cache = BoundedTTLCache(maxsize=256, default_ttl=15 * 60)
_EXPOSURE_TTL = 15 * 60  # 15 minutes per user


def _cache_get(cache: BoundedTTLCache, key: str, ttl: int = 0) -> Any | None:
    return cache.get(key)


def _cache_set(cache: BoundedTTLCache, key: str, value: Any, ttl: int | None = None) -> None:
    cache.set(key, value, ttl=ttl)


# ── Indicator definitions ─────────────────────────────────────────────

_INDICATORS = [
    {
        "key": "vix",
        "label": "VIX",
        "ticker": "^VIX",
        "full_name": "Market Fear Index",
        "unit": "",
        "category": "essential",
        "headline": "Measures expected 30-day market volatility, the market's fear gauge.",
        "description": (
            "The VIX tracks how much volatility traders expect over the next 30 days. "
            "Below 15 means markets are calm and complacent. Between 15-20 is normal. "
            "Above 20 signals elevated anxiety and wider daily price swings. "
            "Above 30 means panic, historically associated with major selloffs and crashes."
        ),
    },
    {
        "key": "us10y",
        "label": "10Y Treasury",
        "ticker": "^TNX",
        "full_name": "US Interest Rate Benchmark",
        "unit": "%",
        "category": "essential",
        "headline": "The most important interest rate in finance, directly drives stock valuations.",
        "description": (
            "The 10-year US Treasury yield is the benchmark rate that underpins all "
            "asset pricing. When yields rise, borrowing costs increase and future "
            "earnings are worth less today - this hits growth and tech stocks hardest. "
            "When yields fall, it supports higher valuations and risk appetite. Rapid "
            "moves of 10+ basis points in a day often trigger volatility across equities."
        ),
    },
    {
        "key": "sp500",
        "label": "S&P 500",
        "ticker": "^GSPC",
        "full_name": "US Broad Market",
        "unit": "",
        "category": "essential",
        "headline": "The main benchmark for the overall US stock market.",
        "description": (
            "The S&P 500 tracks the 500 largest US companies and represents about 80% "
            "of total US stock market value. It is the yardstick most investors measure "
            "themselves against. If your portfolio underperforms the S&P over time, a "
            "simple index fund would have done better."
        ),
    },
    {
        "key": "nasdaq",
        "label": "NASDAQ",
        "ticker": "^IXIC",
        "full_name": "Tech-Weighted Benchmark",
        "unit": "",
        "category": "essential",
        "headline": "Tech-heavy index, more volatile and rate-sensitive than the S&P 500.",
        "description": (
            "The NASDAQ Composite is heavily weighted toward technology and growth "
            "companies. It tends to outperform during low-rate, risk-on environments and "
            "underperform when rates rise or fear spikes. If your portfolio is tech-heavy, "
            "the NASDAQ is a more relevant benchmark than the S&P 500."
        ),
    },
    {
        "key": "dxy",
        "label": "US Dollar (DXY)",
        "ticker": "DX-Y.NYB",
        "full_name": "Dollar Strength",
        "unit": "",
        "category": "important",
        "headline": "Measures USD strength, impacts companies with overseas revenue.",
        "description": (
            "The Dollar Index measures the USD against a basket of major currencies "
            "(Euro, Yen, Pound, etc.). A strong dollar reduces the value of overseas "
            "revenue when converted back to USD - this directly impacts companies like "
            "Apple, Microsoft, and Nike that earn 40–60% of their revenue internationally."
        ),
    },
    {
        "key": "oil",
        "label": "Crude Oil (WTI)",
        "ticker": "CL=F",
        "full_name": "Energy Barometer",
        "unit": "$/barrel",
        "category": "important",
        "headline": "US crude oil benchmark, drives inflation and energy sector earnings.",
        "description": (
            "WTI crude oil is the primary US energy price benchmark. Oil above $90/barrel "
            "tends to fuel inflation and squeeze consumers. Below $60 hurts energy "
            "producers but benefits the broader economy. Rapid price spikes often precede "
            "market volatility as inflation expectations adjust."
        ),
    },
    {
        "key": "hyg",
        "label": "HY Credit",
        "ticker": "HYG",
        "full_name": "Credit Stress Indicator",
        "unit": "$",
        "category": "important",
        "headline": "Tracks high-yield bonds, an early warning system for market stress.",
        "description": (
            "The HYG ETF tracks high-yield (junk) corporate bonds. When HYG falls, it "
            "means investors are demanding higher interest rates to lend to riskier "
            "companies - a sign of rising credit stress. Historically, sustained drops in "
            "HYG have preceded broader equity selloffs by 1–3 months."
        ),
    },
    {
        "key": "gold",
        "label": "Gold",
        "ticker": "GC=F",
        "full_name": "Safe Haven Asset",
        "unit": "$/oz",
        "category": "contextual",
        "headline": "Traditional safe-haven asset, rises during fear and inflation.",
        "description": (
            "Gold is where investors flee during uncertainty. Rising gold alongside "
            "falling stocks signals genuine fear in the market. Rising gold alongside "
            "rising stocks often signals inflation concerns. Sharp gold rallies can be an "
            "early warning that the market is pricing in trouble ahead."
        ),
    },
]


def _fmt_number(val: float | None, unit: str = "", decimals: int = 2) -> str:
    if val is None:
        return " - "
    if abs(val) >= 1_000_000_000:
        return f"{val / 1e9:,.1f}B{unit}"
    if abs(val) >= 1_000_000:
        return f"{val / 1e6:,.1f}M{unit}"
    if abs(val) >= 10_000:
        return f"{val:,.0f}{unit}"
    return f"{val:,.{decimals}f}{unit}"


def _fmt_change(pct: float | None) -> str:
    if pct is None:
        return " - "
    sign = "+" if pct >= 0 else ""
    return f"{sign}{pct:.2f}%"


# ── yfinance batch fetch ──────────────────────────────────────────────


def _fetch_indicators_sync() -> list[dict]:
    """Blocking: batch-download macro tickers via yfinance."""
    if not _YF:
        logger.warning("yfinance not available  -  returning empty indicators")
        return []

    tickers = [ind["ticker"] for ind in _INDICATORS]

    results: list[dict] = []
    try:
        data = yf.download(
            tickers,
            period="5d",
            interval="1d",
            group_by="ticker",
            progress=False,
            threads=True,
        )
    except Exception as exc:
        logger.error(f"yfinance batch download failed: {exc}")
        return [
            {**ind, "value": None, "change": None, "prev_close": None}
            for ind in _INDICATORS
        ]

    for ind in _INDICATORS:
        ticker = ind["ticker"]
        try:
            if len(tickers) == 1:
                ticker_data = data
            else:
                ticker_data = data[ticker] if ticker in data.columns.get_level_values(0) else None

            if ticker_data is None or ticker_data.empty:
                results.append({**ind, "value": None, "change": None, "prev_close": None})
                continue

            close_col = "Close"
            if close_col not in ticker_data.columns:
                close_col = "Adj Close"

            closes = ticker_data[close_col].dropna()
            if closes.empty:
                results.append({**ind, "value": None, "change": None, "prev_close": None})
                continue

            current = float(closes.iloc[-1])
            prev = float(closes.iloc[-2]) if len(closes) > 1 else current
            change_pct = ((current - prev) / prev * 100) if prev != 0 else 0.0

            results.append({
                **ind,
                "value": current,
                "change": change_pct,
                "prev_close": prev,
            })
        except Exception as exc:
            logger.warning(f"Failed to parse {ticker}: {exc}")
            results.append({**ind, "value": None, "change": None, "prev_close": None})

    return results


async def fetch_macro_indicators() -> list[dict]:
    """Async wrapper  -  returns cached or freshly-fetched indicators."""
    cached = _cache_get(_indicator_cache, "macro_indicators", _INDICATOR_TTL)
    if cached is not None:
        return cached

    data = await asyncio.to_thread(_fetch_indicators_sync)
    _cache_set(_indicator_cache, "macro_indicators", data, ttl=_INDICATOR_TTL)
    return data


# ── Signal computation ────────────────────────────────────────────────


def _compute_signal(ind: dict) -> tuple[str, str]:
    """Return (signal, signal_label) based on indicator value and thresholds."""
    key = ind["key"]
    val = ind.get("value")
    change = ind.get("change")

    if val is None:
        return "neutral", "No data"

    if key == "vix":
        if val < 15:
            return "bullish", "Low fear"
        if val < 20:
            return "neutral", "Normal"
        if val < 30:
            return "caution", "Elevated fear"
        return "bearish", "High fear"

    if key == "us10y":
        if change is not None:
            if change > 3:
                return "bearish", "Yields spiking"
            if change > 1:
                return "caution", "Yields rising"
            if change < -3:
                return "bullish", "Yields falling fast"
            if change < -1:
                return "bullish", "Yields easing"
        if val > 5:
            return "bearish", "High rates"
        if val > 4.5:
            return "caution", "Elevated rates"
        return "neutral", "Stable rates"

    if key in ("sp500", "nasdaq"):
        if change is not None:
            if change > 1:
                return "bullish", "Strong rally"
            if change > 0.3:
                return "bullish", "Gaining"
            if change < -2:
                return "bearish", "Sharp selloff"
            if change < -0.5:
                return "caution", "Declining"
        return "neutral", "Flat"

    if key == "dxy":
        if change is not None:
            if change > 1:
                return "caution", "Dollar strengthening"
            if change < -1:
                return "bullish", "Dollar weakening"
        return "neutral", "Stable"

    if key == "oil":
        if change is not None:
            if change > 3:
                return "caution", "Oil spiking"
            if change < -3:
                return "bearish", "Oil dropping"
        if val > 100:
            return "caution", "Elevated prices"
        return "neutral", "Normal range"

    if key == "hyg":
        if change is not None:
            if change < -1:
                return "bearish", "Credit stress rising"
            if change < -0.3:
                return "caution", "Credit tightening"
            if change > 0.5:
                return "bullish", "Credit conditions easing"
        return "neutral", "Stable"

    if key == "gold":
        if change is not None:
            if change > 2:
                return "caution", "Flight to safety"
            if change < -2:
                return "bullish", "Risk appetite returning"
        return "neutral", "Stable"

    return "neutral", " - "


# ── Portfolio exposure computation ────────────────────────────────────


@lru_cache(maxsize=1)
def _load_sector_lookup() -> dict[str, str]:
    """Build symbol → sector map from sp500.json + common ETF sectors."""
    lookup: dict[str, str] = {}
    path = Path(__file__).parent.parent / "stocks" / "data" / "sp500.json"
    try:
        with path.open("r", encoding="utf-8") as f:
            for entry in json.load(f):
                sym = entry.get("symbol", "").upper()
                sec = entry.get("sector", "")
                if sym and sec:
                    lookup[sym] = sec
    except Exception as exc:
        logger.error(f"Failed to load sp500.json for sector lookup: {exc}")

    _ETF_SECTORS = {
        "QQQ": "Information Technology", "SPY": "Broad Market", "VOO": "Broad Market",
        "VTI": "Broad Market", "IVV": "Broad Market", "VGT": "Information Technology",
        "XLK": "Information Technology", "XLF": "Financials", "XLE": "Energy",
        "XLV": "Health Care", "XLP": "Consumer Staples", "XLY": "Consumer Discretionary",
        "XLI": "Industrials", "XLU": "Utilities", "XLRE": "Real Estate",
        "XLB": "Materials", "XLC": "Communication Services",
        "IWM": "Broad Market", "DIA": "Broad Market",
        "ARKK": "Information Technology", "SOXX": "Information Technology",
        "SMH": "Information Technology", "VNQ": "Real Estate",
        "GLD": "Commodities", "SLV": "Commodities", "USO": "Energy",
        "TLT": "Bonds", "BND": "Bonds", "AGG": "Bonds", "HYG": "Bonds",
        "LQD": "Bonds", "SCHD": "Broad Market",
    }
    lookup.update(_ETF_SECTORS)
    return lookup


_RATE_SENSITIVE_SECTORS = {
    "Technology", "Information Technology", "Communication Services",
    "Real Estate", "Consumer Discretionary",
}
_CYCLICAL_SECTORS = {
    "Technology", "Information Technology", "Consumer Discretionary",
    "Industrials", "Materials", "Financials", "Energy",
}
_DEFENSIVE_SECTORS = {
    "Consumer Staples", "Utilities", "Health Care", "Healthcare",
    "Bonds",
}
_GROWTH_SECTORS = {
    "Technology", "Information Technology", "Communication Services",
    "Consumer Discretionary",
}
_ENERGY_SECTORS = {"Energy"}

_HIGH_INTL_REVENUE = {
    "AAPL": 60, "MSFT": 50, "GOOGL": 55, "META": 55, "NVDA": 55,
    "AMZN": 40, "TSLA": 50, "AVGO": 60, "CRM": 30, "ORCL": 45,
    "ADBE": 40, "CSCO": 45, "NFLX": 55, "INTC": 75, "QCOM": 65,
    "TXN": 60, "AMD": 55, "MU": 70, "LRCX": 75, "AMAT": 75,
    "IBM": 60, "CAT": 55, "MMM": 55, "JNJ": 50, "PG": 55,
    "KO": 60, "PEP": 40, "MCD": 60, "NKE": 60, "BA": 55,
    "GE": 55, "HON": 55, "UPS": 40, "DE": 50, "ABT": 55,
    "XOM": 40, "CVX": 30,
}


def compute_portfolio_exposure(
    positions: list[dict[str, Any]],
) -> dict:
    """Compute portfolio's macro exposure scores from position data.

    Resolves sector from Position.sector first, then falls back to the
    sp500.json/ETF lookup by symbol  -  so holdings with NULL sector in the
    DB still get classified correctly.
    """
    sector_lookup = _load_sector_lookup()

    total_value = 0.0
    rate_value = 0.0
    cyclical_value = 0.0
    defensive_value = 0.0
    growth_value = 0.0
    value_value = 0.0
    intl_value = 0.0
    energy_value = 0.0

    # Track symbols per category (ordered by market value descending)
    cat_symbols: dict[str, list[tuple[float, str]]] = {
        "rate_sensitive": [],
        "cyclical": [],
        "defensive": [],
        "growth": [],
        "international_revenue": [],
        "energy": [],
    }

    for pos in positions:
        qty = float(pos.get("quantity", 0) or 0)
        price = float(pos.get("current_price", 0) or 0)
        mv = qty * price
        if mv <= 0:
            continue

        total_value += mv
        symbol = (pos.get("symbol") or "").upper()
        sector = pos.get("sector") or ""

        if not sector:
            sector = sector_lookup.get(symbol, "")

        if sector in _RATE_SENSITIVE_SECTORS:
            rate_value += mv
            cat_symbols["rate_sensitive"].append((mv, symbol))
        if sector in _CYCLICAL_SECTORS:
            cyclical_value += mv
            cat_symbols["cyclical"].append((mv, symbol))
        if sector in _DEFENSIVE_SECTORS:
            defensive_value += mv
            cat_symbols["defensive"].append((mv, symbol))
        if sector in _GROWTH_SECTORS:
            growth_value += mv
            cat_symbols["growth"].append((mv, symbol))
        if sector and sector not in _GROWTH_SECTORS:
            value_value += mv
        if sector in _ENERGY_SECTORS:
            energy_value += mv
            cat_symbols["energy"].append((mv, symbol))

        # International revenue  -  flag symbols with high overseas revenue
        intl_pct = _HIGH_INTL_REVENUE.get(symbol, 20)
        intl_value += mv * (intl_pct / 100)
        if intl_pct >= 40:
            cat_symbols["international_revenue"].append((mv, symbol))

    if total_value == 0:
        return {
            "rate_sensitive_pct": 0, "cyclical_pct": 0, "defensive_pct": 0,
            "growth_pct": 0, "value_pct": 0, "international_revenue_pct": 0,
            "energy_pct": 0, "total_positions": len(positions),
            "total_market_value": 0,
            "symbols_by_category": {k: [] for k in cat_symbols},
        }

    # Sort each category by market value and keep top 10 symbols
    symbols_by_category = {
        k: [sym for _, sym in sorted(v, reverse=True)[:10]]
        for k, v in cat_symbols.items()
    }

    return {
        "rate_sensitive_pct": round(rate_value / total_value * 100, 1),
        "cyclical_pct": round(cyclical_value / total_value * 100, 1),
        "defensive_pct": round(defensive_value / total_value * 100, 1),
        "growth_pct": round(growth_value / total_value * 100, 1),
        "value_pct": round(value_value / total_value * 100, 1),
        "international_revenue_pct": round(intl_value / total_value * 100, 1),
        "energy_pct": round(energy_value / total_value * 100, 1),
        "total_positions": len([p for p in positions if float(p.get("quantity", 0) or 0) > 0]),
        "total_market_value": round(total_value, 2),
        "symbols_by_category": symbols_by_category,
    }


# ── Alert generation ──────────────────────────────────────────────────


def compute_alerts(
    indicators: list[dict],
    exposure: dict,
) -> list[dict]:
    """Generate threshold-triggered macro alerts relevant to user's portfolio."""
    alerts: list[dict] = []

    ind_map = {i["key"]: i for i in indicators}

    vix = ind_map.get("vix", {})
    vix_val = vix.get("value")
    if vix_val is not None and vix_val >= 25:
        growth_pct = exposure.get("growth_pct", 0)
        severity = "critical" if vix_val >= 30 else "warning"
        alerts.append({
            "indicator_key": "vix",
            "indicator_label": "VIX",
            "severity": severity,
            "title": f"VIX at {vix_val:.0f} - Elevated market fear",
            "message": (
                f"Market volatility is significantly elevated. "
                f"Your portfolio is {growth_pct:.0f}% growth stocks - "
                f"historically this allocation sees larger drawdowns in high-VIX periods."
            ),
            "link": "/macro-pulse",
        })

    ust = ind_map.get("us10y", {})
    ust_change = ust.get("change")
    if ust_change is not None and abs(ust_change) > 2:
        rate_pct = exposure.get("rate_sensitive_pct", 0)
        if ust_change > 0:
            alerts.append({
                "indicator_key": "us10y",
                "indicator_label": "10Y Treasury",
                "severity": "warning",
                "title": "Treasury yields rising sharply",
                "message": (
                    f"10Y yield jumped {ust_change:+.1f}% today. "
                    f"Your portfolio is {rate_pct:.0f}% rate-sensitive assets - "
                    f"rising yields compress valuations on growth and tech stocks."
                ),
                "link": "/macro-pulse",
            })

    hyg = ind_map.get("hyg", {})
    hyg_change = hyg.get("change")
    if hyg_change is not None and hyg_change < -1:
        alerts.append({
            "indicator_key": "hyg",
            "indicator_label": "HY Credit",
            "severity": "warning",
            "title": "Credit markets showing stress",
            "message": (
                "High-yield bonds are selling off - this often precedes broader equity weakness. "
                f"Your defensive allocation is only {exposure.get('defensive_pct', 0):.0f}%."
            ),
            "link": "/macro-pulse",
        })

    oil = ind_map.get("oil", {})
    oil_change = oil.get("change")
    energy_pct = exposure.get("energy_pct", 0)
    if oil_change is not None and abs(oil_change) > 4 and energy_pct > 5:
        direction = "surging" if oil_change > 0 else "plunging"
        alerts.append({
            "indicator_key": "oil",
            "indicator_label": "Oil",
            "severity": "warning",
            "title": f"Oil prices {direction}",
            "message": (
                f"WTI crude moved {oil_change:+.1f}% today. "
                f"Your portfolio has {energy_pct:.0f}% energy exposure - "
                f"this directly impacts those holdings."
            ),
            "link": "/macro-pulse",
        })

    return alerts


# ── Build full response ──────────────────────────────────────────────


async def build_macro_pulse(
    positions: list[dict[str, Any]],
) -> dict:
    """Build the complete Macro Pulse payload for a user."""
    raw_indicators = await fetch_macro_indicators()

    indicators = []
    for ind in raw_indicators:
        signal, signal_label = _compute_signal(ind)
        indicators.append({
            "key": ind["key"],
            "label": ind["label"],
            "value": ind.get("value"),
            "display_value": _fmt_number(ind.get("value"), ind.get("unit", ""), decimals=2),
            "change": ind.get("change"),
            "change_display": _fmt_change(ind.get("change")),
            "signal": signal,
            "signal_label": signal_label,
            "description": ind.get("headline", ""),
            "portfolio_impact": "",
            "detail": ind.get("description", ""),
            "category": ind.get("category", "essential"),
            "unit": ind.get("unit", ""),
        })

    exposure = compute_portfolio_exposure(positions)
    alerts = compute_alerts(raw_indicators, exposure)

    _add_portfolio_impact(indicators, exposure)

    return {
        "indicators": indicators,
        "exposure": exposure,
        "alerts": alerts,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


def _add_portfolio_impact(indicators: list[dict], exposure: dict) -> None:
    """Enrich each indicator with a personalized portfolio impact sentence."""
    exp = exposure

    for ind in indicators:
        key = ind["key"]
        val = ind.get("value")
        if val is None:
            ind["portfolio_impact"] = "Data unavailable."
            continue

        if key == "vix":
            g = exp.get("growth_pct", 0)
            if val >= 25:
                ind["portfolio_impact"] = (
                    f"Your portfolio is {g:.0f}% growth stocks. In VIX above 25 periods, "
                    f"growth-heavy allocations historically see 10-15% drawdowns."
                )
            elif val >= 20:
                ind["portfolio_impact"] = (
                    f"Volatility is above normal. Your {g:.0f}% growth allocation "
                    f"may experience wider daily swings."
                )
            else:
                ind["portfolio_impact"] = (
                    f"Low volatility environment favors your {g:.0f}% growth allocation. "
                    f"Good conditions for holding."
                )

        elif key == "us10y":
            r = exp.get("rate_sensitive_pct", 0)
            if val > 4.5:
                ind["portfolio_impact"] = (
                    f"Your portfolio is {r:.0f}% rate-sensitive assets. "
                    f"At current yield levels, growth stock valuations face compression pressure."
                )
            else:
                ind["portfolio_impact"] = (
                    f"With {r:.0f}% of your portfolio in rate-sensitive assets, "
                    f"current yield levels are relatively supportive for valuations."
                )

        elif key in ("sp500", "nasdaq"):
            ind["portfolio_impact"] = (
                f"Your portfolio benchmark. Compare your returns against this "
                f"to measure whether active positions are adding value."
            )

        elif key == "dxy":
            intl = exp.get("international_revenue_pct", 0)
            if intl > 40:
                ind["portfolio_impact"] = (
                    f"~{intl:.0f}% of your portfolio's company revenue comes from overseas. "
                    f"A strong dollar reduces the value of that foreign revenue when converted back to USD."
                )
            else:
                ind["portfolio_impact"] = (
                    f"Your portfolio has ~{intl:.0f}% international revenue exposure - "
                    f"dollar moves have moderate impact on your holdings."
                )

        elif key == "oil":
            e = exp.get("energy_pct", 0)
            if e > 5:
                ind["portfolio_impact"] = (
                    f"Your portfolio has {e:.0f}% energy exposure. "
                    f"Oil price moves directly affect those holdings' earnings."
                )
            else:
                ind["portfolio_impact"] = (
                    f"With only {e:.0f}% energy exposure, oil price moves primarily "
                    f"affect you through broader inflation and consumer spending."
                )

        elif key == "hyg":
            d = exp.get("defensive_pct", 0)
            ind["portfolio_impact"] = (
                f"Credit market health acts as an early warning for stocks. "
                f"Your defensive allocation is {d:.0f}% - "
                + ("consider whether that's enough cushion." if d < 20
                   else "a reasonable buffer against credit stress.")
            )

        elif key == "gold":
            g = exp.get("growth_pct", 0)
            ind["portfolio_impact"] = (
                f"Gold rising alongside falling equities signals fear. "
                f"With {g:.0f}% in growth stocks, sharp gold rallies may signal "
                f"headwinds for your portfolio."
            )
