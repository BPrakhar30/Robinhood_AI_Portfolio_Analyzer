"""HTTP surface for the Stock Detail page and the Stocks tab.

Three endpoints:

  - ``GET /stocks``             : paginated stock-card grid (S&P 500 seed + user holdings).
  - ``GET /stocks/{symbol}``    : composite detail payload (profile + quote + candles* + earnings + news + position).
  - ``GET /stocks/{symbol}/candles`` : candles only  -  time-range selector calls this as the user switches ranges.

The /stocks/{symbol} response includes a default candles range (``1M``) so
the first paint is instant; subsequent range changes hit the candles-only
endpoint.
"""

from __future__ import annotations

import asyncio
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.service import get_current_user
from app.database.engine import get_async_session
from app.database.models import Position, User

from .ai_analysis import generate_stock_analysis
from .schemas import (
    CandleRange,
    StockAnalysisResponse,
    StockCandles,
    StockDetailResponse,
    StockPositionSummary,
    StockUniverseResponse,
)
from .service import (
    build_position_summary,
    fetch_candles,
    fetch_key_stats,
    fetch_quote,
    fetch_stock_detail,
    fetch_symbol_news,
    fetch_universe_cards,
)

router = APIRouter(prefix="/stocks", tags=["stocks"])


# ──────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────


async def _user_positions(db: AsyncSession, user_id) -> list[Position]:
    stmt = select(Position).where(Position.user_id == user_id)
    return list((await db.execute(stmt)).scalars().all())


def _portfolio_total_value(positions: list[Position]) -> float:
    return sum(
        (p.quantity or 0.0) * (p.current_price or 0.0)
        for p in positions
    )


def _owned_map(positions: list[Position]) -> dict[str, Position]:
    out: dict[str, Position] = {}
    for p in positions:
        if (p.quantity or 0) > 0 and p.symbol:
            out[p.symbol.upper()] = p
    return out


# ──────────────────────────────────────────────────────────────────────
# Universe listing
# ──────────────────────────────────────────────────────────────────────


@router.get("", response_model=StockUniverseResponse)
async def list_stocks(
    universe: str = Query(
        "all",
        pattern="^(all|owned)$",
        description="'all' (default) or 'owned'  -  filter to just the user's holdings.",
    ),
    search: Optional[str] = Query(None, min_length=1, max_length=50),
    limit: int = Query(120, ge=1, le=300),
    live_quotes: bool = Query(
        True,
        description="When false, skip the live quote enrichment for faster pagination.",
    ),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    """List browsable stocks + ETFs (curated S&P 500 + the user's holdings)."""
    positions = await _user_positions(db, current_user.id)
    owned_map = _owned_map(positions)
    owned_symbols = set(owned_map.keys())

    owned_positions = {
        sym: {
            "name": pos.name,
            "sector": pos.sector,
            "asset_type": pos.asset_type.value if pos.asset_type else None,
            "current_price": pos.current_price,
        }
        for sym, pos in owned_map.items()
    }

    return await fetch_universe_cards(
        owned_symbols=owned_symbols,
        universe=universe,
        search=search,
        limit=limit,
        live_quotes=live_quotes,
        owned_positions=owned_positions,
    )


# ──────────────────────────────────────────────────────────────────────
# Detail
# ──────────────────────────────────────────────────────────────────────


async def _build_position_summary(
    symbol: str, db: AsyncSession, user_id
) -> StockPositionSummary:
    positions = await _user_positions(db, user_id)
    total_value = _portfolio_total_value(positions)
    pos = next(
        (
            p
            for p in positions
            if (p.symbol or "").upper() == symbol.upper() and (p.quantity or 0) > 0
        ),
        None,
    )

    if pos is None:
        return StockPositionSummary(symbol=symbol.upper(), owned=False)

    # Fetch live quote for today's-return computation. Cached 60 s server-side.
    quote = await fetch_quote(symbol)
    previous_close = quote.previous_close

    return build_position_summary(
        symbol=symbol,
        quantity=pos.quantity or 0.0,
        average_cost=pos.average_cost,
        current_price=pos.current_price or quote.price,
        previous_close=previous_close,
        asset_type=pos.asset_type.value if pos.asset_type else None,
        portfolio_total_value=total_value or None,
    )


@router.get("/{symbol}", response_model=StockDetailResponse)
async def get_stock_detail(
    symbol: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    """One-shot payload for the Stock Detail page.

    Returns the company profile, live quote, key stats, next + last-4
    earnings, the user's position in this ticker (if any), and the most
    recent company-news items.
    """
    symbol = symbol.upper().strip()
    if not symbol or len(symbol) > 12:
        raise HTTPException(status_code=400, detail="Invalid symbol")

    position = await _build_position_summary(symbol, db, current_user.id)
    try:
        return await fetch_stock_detail(symbol, position=position)
    except Exception as exc:  # noqa: BLE001  -  never leak upstream errors
        from app.utils.logging import get_logger as _gl
        _gl("stocks.router").error(
            "Stock detail fetch failed",
            extra={"event": "stock_detail_error", "symbol": symbol, "error": str(exc)},
        )
        raise HTTPException(
            status_code=502,
            detail="Stock data is temporarily unavailable. Please try again shortly.",
        ) from exc


# ──────────────────────────────────────────────────────────────────────
# Candles (separate endpoint so range-switching doesn't re-fetch everything)
# ──────────────────────────────────────────────────────────────────────


@router.get("/{symbol}/candles", response_model=StockCandles)
async def get_stock_candles(
    symbol: str,
    range: CandleRange = Query("1M"),
    current_user: User = Depends(get_current_user),
):
    symbol = symbol.upper().strip()
    if not symbol or len(symbol) > 12:
        raise HTTPException(status_code=400, detail="Invalid symbol")
    try:
        return await fetch_candles(symbol, range)
    except Exception as exc:  # noqa: BLE001
        from app.utils.logging import get_logger as _gl
        _gl("stocks.router").error(
            "Candle fetch failed",
            extra={"event": "candle_error", "symbol": symbol, "error": str(exc)},
        )
        raise HTTPException(
            status_code=502,
            detail="Chart data is temporarily unavailable. Please try again shortly.",
        ) from exc


# ──────────────────────────────────────────────────────────────────────
# AI analysis
# ──────────────────────────────────────────────────────────────────────


@router.get("/{symbol}/analysis", response_model=StockAnalysisResponse)
async def get_stock_analysis(
    symbol: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    """AI-generated analysis combining chart, news, and user holdings context."""
    symbol = symbol.upper().strip()
    if not symbol or len(symbol) > 12:
        raise HTTPException(status_code=400, detail="Invalid symbol")

    position = await _build_position_summary(symbol, db, current_user.id)

    candles_task = fetch_candles(symbol, "3M")
    quote_task = fetch_quote(symbol)
    stats_task = fetch_key_stats(symbol)
    news_task = fetch_symbol_news(symbol)

    candles, quote, stats, news = await asyncio.gather(
        candles_task, quote_task, stats_task, news_task,
    )

    return await generate_stock_analysis(
        symbol=symbol,
        candles_data=candles.model_dump(mode="json"),
        quote_data=quote.model_dump(mode="json"),
        key_stats_data=stats.model_dump(mode="json"),
        news_articles=[a.model_dump(mode="json") for a in news.articles[:10]],
        position_data=position.model_dump(mode="json") if position.owned else None,
    )
