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
