"""FastMCP server hosting the read-only portfolio tools.

``user_id`` is injected as MCP request metadata by the backend's
``process_tool_call`` hook — the LLM never sees or submits it. Missing
metadata raises (no permissive default).

Note: ``host``/``port``/``transport_security`` must be passed at
``FastMCP(...)`` construction. Post-hoc ``mcp.settings`` mutation doesn't
refresh the DNS-rebinding allow-list and causes 421s in Docker.
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from uuid import UUID

from mcp.server.fastmcp import Context, FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from pydantic import BaseModel
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai_agent.models import (
    CashPosition,
    Holding,
    PeriodLiteral,
    PerformanceSummary,
    TransactionOut,
)
from app.database.engine import AsyncSessionLocal
from app.database.models import PortfolioSnapshot, Position, Transaction
from app.stocks import service as stocks_service
from app.stocks.schemas import (
    StockEarnings,
    StockKeyStats,
    StockPositionSummary,
    StockProfile,
    StockQuote,
)
from app.utils.logging import get_logger

logger = get_logger("mcp_server")


_HOST = os.getenv("MCP_HOST", "127.0.0.1")
_PORT = int(os.getenv("MCP_PORT", "8765"))

# DNS-rebinding allow-list. ``mcp-server:*`` lets the backend reach us
# over the Compose network; override via ``MCP_ALLOWED_HOSTS`` (csv).
_DEFAULT_ALLOWED_HOSTS = [
    "127.0.0.1:*",
    "localhost:*",
    "[::1]:*",
    "mcp-server:*",
]
_allowed_hosts_env = os.getenv("MCP_ALLOWED_HOSTS", "").strip()
_ALLOWED_HOSTS = (
    [h.strip() for h in _allowed_hosts_env.split(",") if h.strip()]
    if _allowed_hosts_env
    else _DEFAULT_ALLOWED_HOSTS
)

_transport_security = TransportSecuritySettings(
    enable_dns_rebinding_protection=True,
    allowed_hosts=_ALLOWED_HOSTS,
)

mcp = FastMCP(
    name="portfolio-tools",
    instructions=(
        "Read-only portfolio data for the signed-in user. All tools return "
        "structured, typed data; none accept or need a user identifier — the "
        "signed-in user is resolved server-side."
    ),
    host=_HOST,
    port=_PORT,
    transport_security=_transport_security,
)


# Server-side caps against oversized result sets.
_HOLDINGS_MAX = 50
_TRANSACTIONS_MAX = 100


def _clamp(value: int, low: int, high: int) -> int:
    return max(low, min(high, value))


class MissingUserMetadata(ValueError):
    """Tool call arrived without valid ``user_id`` metadata."""


def _extract_user_id(ctx: Context) -> UUID:
    """Return the signed-in user's UUID from MCP request metadata."""
    meta: Any = getattr(ctx.request_context, "meta", None)
    if meta is None:
        raise MissingUserMetadata("MCP call missing request metadata.")

    # ``meta`` may be a Pydantic model, SimpleNamespace, or dict.
    raw = getattr(meta, "user_id", None)
    if raw is None and isinstance(meta, dict):
        raw = meta.get("user_id")
    if not raw:
        raise MissingUserMetadata("MCP call metadata missing 'user_id'.")

    try:
        return UUID(str(raw))
    except (ValueError, TypeError) as exc:
        raise MissingUserMetadata("MCP call metadata has invalid 'user_id'.") from exc


class _DbSession:
    """Fresh ``AsyncSession`` per tool call. Tool calls are stateless."""

    async def __aenter__(self) -> AsyncSession:
        self._session = AsyncSessionLocal()
        return self._session

    async def __aexit__(self, exc_type, exc, tb) -> None:
        try:
            if exc_type is None:
                await self._session.commit()
            else:
                await self._session.rollback()
        finally:
            await self._session.close()


def _log_tool_call(tool: str, user_id: UUID, **extra: Any) -> None:
    logger.info(
        f"Tool {tool}",
        extra={
            "event": "mcp_tool_call",
            "tool": tool,
            "user_id": str(user_id),
            **extra,
        },
    )


@mcp.tool()
async def get_holdings(ctx: Context, limit: int = 10) -> list[Holding]:
    """Return the signed-in user's current positions, ordered by market value (desc)."""
    user_id = _extract_user_id(ctx)
    limit = _clamp(limit, 1, _HOLDINGS_MAX)

    async with _DbSession() as session:
        stmt = (
            select(Position)
            .where(Position.user_id == user_id)
            .order_by(
                desc(Position.quantity * func.coalesce(Position.current_price, 0.0))
            )
            .limit(limit)
        )
        result = await session.execute(stmt)
        positions = result.scalars().all()

    holdings: list[Holding] = []
    for p in positions:
        price = p.current_price or 0.0
        holdings.append(
            Holding(
                symbol=p.symbol,
                name=p.name,
                asset_type=p.asset_type.value if p.asset_type else "stock",
                quantity=p.quantity,
                average_cost=p.average_cost,
                current_price=p.current_price,
                market_value=p.quantity * price,
                unrealized_gain=p.unrealized_gains or 0.0,
                sector=p.sector,
            )
        )

    _log_tool_call("get_holdings", user_id, returned=len(holdings))
    return holdings


@mcp.tool()
async def get_recent_transactions(
    ctx: Context, limit: int = 20
) -> list[TransactionOut]:
    """Return the signed-in user's most recent transactions (newest first)."""
    user_id = _extract_user_id(ctx)
    limit = _clamp(limit, 1, _TRANSACTIONS_MAX)

    async with _DbSession() as session:
        stmt = (
            select(Transaction)
            .where(Transaction.user_id == user_id)
            .order_by(desc(Transaction.executed_at))
            .limit(limit)
        )
        result = await session.execute(stmt)
        txns = result.scalars().all()

    out = [
        TransactionOut(
            symbol=t.symbol,
            transaction_type=t.transaction_type.value if t.transaction_type else "buy",
            quantity=t.quantity,
            price=t.price,
            total_amount=t.total_amount,
            fees=t.fees or 0.0,
            executed_at=t.executed_at,
        )
        for t in txns
    ]
    _log_tool_call("get_recent_transactions", user_id, returned=len(out))
    return out


@mcp.tool()
async def get_cash_position(ctx: Context) -> CashPosition:
    """Latest cash balance from the most recent portfolio snapshot."""
    user_id = _extract_user_id(ctx)

    async with _DbSession() as session:
        stmt = (
            select(PortfolioSnapshot)
            .where(PortfolioSnapshot.user_id == user_id)
            .order_by(desc(PortfolioSnapshot.captured_at))
            .limit(1)
        )
        snap = (await session.execute(stmt)).scalar_one_or_none()

    _log_tool_call("get_cash_position", user_id, has_data=snap is not None)

    if snap is None:
        return CashPosition(
            cash_balance=0.0,
            as_of=None,
            has_data=False,
            note="No portfolio snapshot available yet. Connect or sync a broker.",
        )
    return CashPosition(
        cash_balance=snap.cash_balance or 0.0,
        as_of=snap.captured_at,
    )


_PERIOD_TO_DELTA: dict[PeriodLiteral, Optional[timedelta]] = {
    "1W": timedelta(days=7),
    "1M": timedelta(days=30),
    "3M": timedelta(days=90),
    "6M": timedelta(days=180),
    "1Y": timedelta(days=365),
    "ALL": None,
}


@mcp.tool()
async def get_performance_summary(
    ctx: Context, period: PeriodLiteral = "1M"
) -> PerformanceSummary:
    """Compare the latest snapshot to the oldest snapshot inside ``period``."""
    user_id = _extract_user_id(ctx)
    if period not in _PERIOD_TO_DELTA:
        period = "1M"

    async with _DbSession() as session:
        latest_stmt = (
            select(PortfolioSnapshot)
            .where(PortfolioSnapshot.user_id == user_id)
            .order_by(desc(PortfolioSnapshot.captured_at))
            .limit(1)
        )
        latest = (await session.execute(latest_stmt)).scalar_one_or_none()

        if latest is None:
            return PerformanceSummary(
                period=period,
                has_data=False,
                note="No portfolio snapshots on file yet. Connect or sync a broker.",
            )

        delta = _PERIOD_TO_DELTA[period]
        earliest_stmt = select(PortfolioSnapshot).where(
            PortfolioSnapshot.user_id == user_id
        )
        if delta is not None:
            cutoff = datetime.now(timezone.utc) - delta
            earliest_stmt = earliest_stmt.where(PortfolioSnapshot.captured_at >= cutoff)
        earliest_stmt = earliest_stmt.order_by(
            PortfolioSnapshot.captured_at.asc()
        ).limit(1)
        earliest = (await session.execute(earliest_stmt)).scalar_one_or_none()

    if earliest is None or earliest.id == latest.id:
        return PerformanceSummary(
            period=period,
            start_value=latest.total_value,
            end_value=latest.total_value,
            absolute_change=0.0,
            percent_change=0.0,
            start_date=latest.captured_at,
            end_date=latest.captured_at,
            has_data=False,
            note=(
                "Only one snapshot available in this window — cannot compute a "
                "change. Try a longer period or sync more data."
            ),
        )

    start_v = earliest.total_value
    end_v = latest.total_value
    abs_change = end_v - start_v
    pct = (abs_change / start_v * 100.0) if start_v else None

    _log_tool_call("get_performance_summary", user_id, period=period)

    return PerformanceSummary(
        period=period,
        start_value=start_v,
        end_value=end_v,
        absolute_change=abs_change,
        percent_change=pct,
        start_date=earliest.captured_at,
        end_date=latest.captured_at,
    )


# ──────────────────────────────────────────────────────────────────────
# Per-symbol tools — let the assistant reason over individual holdings
# ──────────────────────────────────────────────────────────────────────


def _normalize_symbol(symbol: str) -> str:
    """Uppercase + strip for MCP safety. Raises on obviously bad input."""
    if not symbol or not isinstance(symbol, str):
        raise ValueError("symbol is required")
    s = symbol.strip().upper()
    if len(s) > 12:
        raise ValueError("symbol too long")
    return s


@mcp.tool()
async def get_symbol_profile(ctx: Context, symbol: str) -> StockProfile:
    """Company/fund profile for ``symbol`` — name, sector, industry, HQ, CEO, employees, description."""
    user_id = _extract_user_id(ctx)
    sym = _normalize_symbol(symbol)
    profile = await stocks_service.fetch_profile(sym)
    _log_tool_call("get_symbol_profile", user_id, symbol=sym)
    return profile


@mcp.tool()
async def get_symbol_quote(ctx: Context, symbol: str) -> StockQuote:
    """Latest quote for ``symbol`` — price, previous close, day change %, volume."""
    user_id = _extract_user_id(ctx)
    sym = _normalize_symbol(symbol)
    quote = await stocks_service.fetch_quote(sym)
    _log_tool_call("get_symbol_quote", user_id, symbol=sym, price=quote.price)
    return quote


@mcp.tool()
async def get_symbol_key_stats(ctx: Context, symbol: str) -> StockKeyStats:
    """Key fundamentals for ``symbol`` — market cap, P/E, EPS, beta, 52-wk range, dividend yield."""
    user_id = _extract_user_id(ctx)
    sym = _normalize_symbol(symbol)
    stats = await stocks_service.fetch_key_stats(sym)
    _log_tool_call("get_symbol_key_stats", user_id, symbol=sym)
    return stats


@mcp.tool()
async def get_symbol_earnings(
    ctx: Context, symbol: str, history: int = 4
) -> StockEarnings:
    """Upcoming earnings event + last ``history`` reported quarters for ``symbol``.

    Each quarter includes estimate vs actual EPS and a derived beat/miss/inline
    label so the assistant can comment on surprise trends.
    """
    user_id = _extract_user_id(ctx)
    sym = _normalize_symbol(symbol)
    history = _clamp(history, 1, 12)
    earnings = await stocks_service.fetch_earnings(sym, history=history)
    _log_tool_call(
        "get_symbol_earnings",
        user_id,
        symbol=sym,
        history=history,
        has_next=earnings.next_event is not None,
    )
    return earnings


class CandleSummary(BaseModel):
    """Compact historical-price summary — avoids flooding the LLM with raw bars."""

    symbol: str
    range: str
    interval: str
    start_price: Optional[float] = None
    end_price: Optional[float] = None
    change: Optional[float] = None
    change_percent: Optional[float] = None
    high: Optional[float] = None
    low: Optional[float] = None
    points: int = 0


@mcp.tool()
async def get_symbol_candles_summary(
    ctx: Context, symbol: str, period: str = "1M"
) -> CandleSummary:
    """Summary of OHLC history over ``period`` (``1D/1W/1M/3M/YTD/1Y/5Y/MAX``).

    Returns start/end price, period change %, and the min/max close over the
    window. We deliberately return a **summary** (not the full candle list)
    because the assistant almost always needs trend direction and magnitude,
    not raw bars — and raw bars would blow out the context window.
    """
    user_id = _extract_user_id(ctx)
    sym = _normalize_symbol(symbol)
    period_valid = period if period in stocks_service._RANGE_PARAMS else "1M"
    candles = await stocks_service.fetch_candles(sym, period_valid)  # type: ignore[arg-type]

    closes = [p.c for p in candles.points]
    hi = max(closes) if closes else None
    lo = min(closes) if closes else None

    out = CandleSummary(
        symbol=sym,
        range=candles.range,
        interval=candles.interval,
        start_price=candles.start_price,
        end_price=candles.end_price,
        change=candles.change,
        change_percent=candles.change_percent,
        high=hi,
        low=lo,
        points=len(candles.points),
    )
    _log_tool_call("get_symbol_candles_summary", user_id, symbol=sym, period=period_valid)
    return out


@mcp.tool()
async def get_position_for_symbol(
    ctx: Context, symbol: str
) -> StockPositionSummary:
    """How the signed-in user is positioned in ``symbol``.

    Returns ``owned=False`` with zeroed fields when the user has no open
    position, so the LLM can cleanly answer "do I own X?"-style questions.
    """
    user_id = _extract_user_id(ctx)
    sym = _normalize_symbol(symbol)

    async with _DbSession() as session:
        # Individual position.
        pos_stmt = (
            select(Position)
            .where(
                Position.user_id == user_id,
                func.upper(Position.symbol) == sym,
                Position.quantity > 0,
            )
            .limit(1)
        )
        pos = (await session.execute(pos_stmt)).scalar_one_or_none()

        # Portfolio-wide total to compute weight %.
        total_stmt = select(
            func.sum(Position.quantity * func.coalesce(Position.current_price, 0.0))
        ).where(Position.user_id == user_id)
        total_value = (await session.execute(total_stmt)).scalar_one() or 0.0

    if pos is None:
        _log_tool_call("get_position_for_symbol", user_id, symbol=sym, owned=False)
        return StockPositionSummary(symbol=sym, owned=False)

    # Live quote for today's-return + live price when the stored one is stale.
    quote = await stocks_service.fetch_quote(sym)
    summary = stocks_service.build_position_summary(
        symbol=sym,
        quantity=pos.quantity or 0.0,
        average_cost=pos.average_cost,
        current_price=pos.current_price or quote.price,
        previous_close=quote.previous_close,
        asset_type=pos.asset_type.value if pos.asset_type else None,
        portfolio_total_value=total_value or None,
    )
    _log_tool_call(
        "get_position_for_symbol",
        user_id,
        symbol=sym,
        owned=True,
        shares=summary.shares,
    )
    return summary
