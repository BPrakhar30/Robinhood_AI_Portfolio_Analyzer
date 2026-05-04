"""Standalone tool functions for the research sub-agent.

These tools give the AI the ability to screen stocks, compare fundamentals,
and analyze sector performance - capabilities beyond the per-symbol MCP tools.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel, Field

from app.config import get_settings
from app.utils.logging import get_logger

logger = get_logger("ai_agent.tools")

_SP500_PATH = Path(__file__).resolve().parent.parent / "stocks" / "data" / "sp500.json"

_SECTOR_ETFS = {
    "Information Technology": "XLK",
    "Health Care": "XLV",
    "Financials": "XLF",
    "Consumer Discretionary": "XLY",
    "Communication Services": "XLC",
    "Industrials": "XLI",
    "Consumer Staples": "XLP",
    "Energy": "XLE",
    "Utilities": "XLU",
    "Real Estate": "XLRE",
    "Materials": "XLB",
}


def _load_sp500() -> list[dict[str, str]]:
    try:
        return json.loads(_SP500_PATH.read_text(encoding="utf-8"))
    except Exception:
        return []


# ── Pydantic models for tool outputs ────────────────────────────────


class ScreenerResult(BaseModel):
    symbol: str
    name: str
    sector: str
    price: Optional[float] = None
    market_cap: Optional[float] = None
    pe_ratio: Optional[float] = None
    forward_pe: Optional[float] = None
    dividend_yield: Optional[float] = None
    eps_ttm: Optional[float] = None
    beta: Optional[float] = None
    change_percent_3m: Optional[float] = None
    fifty_two_week_high: Optional[float] = None
    fifty_two_week_low: Optional[float] = None


class ScreenerOutput(BaseModel):
    criteria_used: str
    total_screened: int
    results: list[ScreenerResult] = Field(default_factory=list)
    note: str = ""


class ComparisonRow(BaseModel):
    symbol: str
    name: Optional[str] = None
    price: Optional[float] = None
    market_cap: Optional[float] = None
    pe_ratio: Optional[float] = None
    forward_pe: Optional[float] = None
    dividend_yield: Optional[float] = None
    eps_ttm: Optional[float] = None
    beta: Optional[float] = None
    fifty_two_week_high: Optional[float] = None
    fifty_two_week_low: Optional[float] = None
    change_percent_ytd: Optional[float] = None
    sector: Optional[str] = None


class ComparisonOutput(BaseModel):
    symbols: list[str]
    rows: list[ComparisonRow] = Field(default_factory=list)


class SectorRow(BaseModel):
    sector: str
    etf: str
    price: Optional[float] = None
    change_percent: Optional[float] = None


class SectorOutput(BaseModel):
    period: str
    rows: list[SectorRow] = Field(default_factory=list)


# ── Tool implementations ────────────────────────────────────────────


def _yf_info_sync(symbol: str) -> dict[str, Any]:
    """Fetch .info dict from yfinance (synchronous)."""
    try:
        import yfinance as yf

        ticker = yf.Ticker(symbol)
        return dict(ticker.info or {})
    except Exception as exc:
        logger.debug(f"yfinance .info failed for {symbol}: {exc}")
        return {}


def _yf_batch_stats_sync(symbols: list[str]) -> dict[str, dict[str, Any]]:
    """Fetch .info for multiple symbols. Returns {SYMBOL: info_dict}."""
    import yfinance as yf

    result: dict[str, dict[str, Any]] = {}
    for sym in symbols:
        try:
            info = dict(yf.Ticker(sym).info or {})
            result[sym] = info
        except Exception:
            result[sym] = {}
    return result


def _yf_batch_candles_sync(
    symbols: list[str], period: str = "3mo"
) -> dict[str, dict[str, float]]:
    """Batch-fetch price change over a period. Returns {SYMBOL: {start, end, change_pct}}."""
    try:
        import yfinance as yf
        import pandas as pd

        df = yf.download(
            tickers=" ".join(symbols),
            period=period,
            interval="1d",
            group_by="ticker",
            threads=True,
            progress=False,
            auto_adjust=False,
        )
        if df is None or df.empty:
            return {}
    except Exception:
        return {}

    result: dict[str, dict[str, float]] = {}
    for sym in symbols:
        try:
            if len(symbols) == 1:
                closes = df["Close"].dropna()
            else:
                closes = df[(sym, "Close")].dropna()
            if closes.empty:
                continue
            start = float(closes.iloc[0])
            end = float(closes.iloc[-1])
            pct = ((end - start) / start * 100) if start else 0.0
            result[sym] = {"start": start, "end": end, "change_pct": round(pct, 2)}
        except Exception:
            continue
    return result


async def stock_screener(
    sector: Optional[str] = None,
    min_market_cap: Optional[float] = None,
    max_pe: Optional[float] = None,
    min_dividend_yield: Optional[float] = None,
    sort_by: str = "market_cap",
    limit: int = 10,
) -> ScreenerOutput:
    """Screen S&P 500 stocks by fundamental criteria.

    Args:
        sector: Filter to a specific GICS sector (e.g. "Information Technology").
        min_market_cap: Minimum market cap in USD (e.g. 50_000_000_000 for $50B).
        max_pe: Maximum trailing P/E ratio.
        min_dividend_yield: Minimum dividend yield as a decimal (0.02 = 2%).
        sort_by: Sort results by "market_cap", "pe_ratio", "dividend_yield",
                 "momentum", or "eps_ttm".
        limit: Number of results to return (max 15).
    """
    limit = max(1, min(limit, 15))
    universe = _load_sp500()
    if not universe:
        return ScreenerOutput(
            criteria_used="N/A", total_screened=0,
            note="Could not load stock universe data.",
        )

    if sector:
        sector_lower = sector.lower()
        universe = [s for s in universe if s.get("sector", "").lower() == sector_lower]

    symbols = [s["symbol"] for s in universe]
    criteria_parts: list[str] = []
    if sector:
        criteria_parts.append(f"sector={sector}")
    if min_market_cap:
        criteria_parts.append(f"min_market_cap=${min_market_cap:,.0f}")
    if max_pe:
        criteria_parts.append(f"max_pe={max_pe}")
    if min_dividend_yield:
        criteria_parts.append(f"min_div_yield={min_dividend_yield:.1%}")
    criteria_parts.append(f"sort={sort_by}")

    infos = await asyncio.to_thread(_yf_batch_stats_sync, symbols)
    candles = await asyncio.to_thread(_yf_batch_candles_sync, symbols, "3mo")

    sp500_map = {s["symbol"]: s for s in _load_sp500()}
    candidates: list[ScreenerResult] = []

    for sym, info in infos.items():
        mc = info.get("marketCap")
        pe = info.get("trailingPE")
        fpe = info.get("forwardPE")
        dy = info.get("dividendYield")
        eps = info.get("trailingEps")
        beta = info.get("beta")
        price = info.get("currentPrice") or info.get("regularMarketPrice")
        hi52 = info.get("fiftyTwoWeekHigh")
        lo52 = info.get("fiftyTwoWeekLow")

        if min_market_cap and (not mc or mc < min_market_cap):
            continue
        if max_pe and (not pe or pe > max_pe or pe <= 0):
            continue
        if min_dividend_yield and (not dy or dy < min_dividend_yield):
            continue

        change_3m = candles.get(sym, {}).get("change_pct")
        sp_entry = sp500_map.get(sym, {})

        candidates.append(ScreenerResult(
            symbol=sym,
            name=info.get("shortName") or sp_entry.get("name", sym),
            sector=info.get("sector") or sp_entry.get("sector", ""),
            price=price,
            market_cap=mc,
            pe_ratio=pe,
            forward_pe=fpe,
            dividend_yield=dy,
            eps_ttm=eps,
            beta=beta,
            change_percent_3m=change_3m,
            fifty_two_week_high=hi52,
            fifty_two_week_low=lo52,
        ))

    sort_key_map = {
        "market_cap": lambda r: r.market_cap or 0,
        "pe_ratio": lambda r: r.pe_ratio if r.pe_ratio and r.pe_ratio > 0 else 9999,
        "dividend_yield": lambda r: r.dividend_yield or 0,
        "momentum": lambda r: r.change_percent_3m or -9999,
        "eps_ttm": lambda r: r.eps_ttm or 0,
    }
    reverse = sort_by not in ("pe_ratio",)
    candidates.sort(key=sort_key_map.get(sort_by, sort_key_map["market_cap"]), reverse=reverse)

    return ScreenerOutput(
        criteria_used=", ".join(criteria_parts) or "all S&P 500",
        total_screened=len(infos),
        results=candidates[:limit],
        note=f"Screened {len(infos)} stocks, {len(candidates)} passed filters.",
    )


async def compare_fundamentals(symbols: list[str]) -> ComparisonOutput:
    """Compare key fundamentals for 2-5 stock symbols side by side.

    Args:
        symbols: List of 2-5 ticker symbols to compare.
    """
    symbols = [s.upper().strip() for s in symbols[:5]]
    infos = await asyncio.to_thread(_yf_batch_stats_sync, symbols)
    candles = await asyncio.to_thread(_yf_batch_candles_sync, symbols, "ytd")

    rows: list[ComparisonRow] = []
    for sym in symbols:
        info = infos.get(sym, {})
        ytd = candles.get(sym, {}).get("change_pct")
        rows.append(ComparisonRow(
            symbol=sym,
            name=info.get("shortName"),
            price=info.get("currentPrice") or info.get("regularMarketPrice"),
            market_cap=info.get("marketCap"),
            pe_ratio=info.get("trailingPE"),
            forward_pe=info.get("forwardPE"),
            dividend_yield=info.get("dividendYield"),
            eps_ttm=info.get("trailingEps"),
            beta=info.get("beta"),
            fifty_two_week_high=info.get("fiftyTwoWeekHigh"),
            fifty_two_week_low=info.get("fiftyTwoWeekLow"),
            change_percent_ytd=ytd,
            sector=info.get("sector"),
        ))

    return ComparisonOutput(symbols=symbols, rows=rows)


async def sector_performance(period: str = "3mo") -> SectorOutput:
    """Fetch performance of all 11 GICS sector ETFs over a given period.

    Args:
        period: yfinance period string - "1mo", "3mo", "6mo", "ytd", "1y".
    """
    etf_symbols = list(_SECTOR_ETFS.values())
    candles = await asyncio.to_thread(_yf_batch_candles_sync, etf_symbols, period)

    reverse_map = {v: k for k, v in _SECTOR_ETFS.items()}
    rows: list[SectorRow] = []
    for etf in etf_symbols:
        data = candles.get(etf, {})
        rows.append(SectorRow(
            sector=reverse_map.get(etf, etf),
            etf=etf,
            price=data.get("end"),
            change_percent=data.get("change_pct"),
        ))

    rows.sort(key=lambda r: r.change_percent or -9999, reverse=True)
    return SectorOutput(period=period, rows=rows)
