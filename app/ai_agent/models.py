"""Typed Pydantic models returned by assistant tools and API.

These are the ONLY shape the LLM sees for portfolio data — a firewall
between ORM internals and model context.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field

PeriodLiteral = Literal["1W", "1M", "3M", "6M", "1Y", "ALL"]


class Holding(BaseModel):
    """A single position summarized for the assistant."""

    symbol: str
    name: Optional[str] = None
    asset_type: str
    quantity: float
    average_cost: float
    current_price: Optional[float] = None
    market_value: float = Field(
        description="quantity * current_price (0 if price unknown)"
    )
    unrealized_gain: float = 0.0
    sector: Optional[str] = None


class TransactionOut(BaseModel):
    """A single broker transaction, sanitized for the assistant."""

    symbol: str
    transaction_type: str
    quantity: float
    price: float
    total_amount: float
    fees: float = 0.0
    executed_at: datetime


class CashPosition(BaseModel):
    """Latest known cash balance across the user's broker connections."""

    cash_balance: float
    as_of: Optional[datetime] = None
    has_data: bool = True
    note: Optional[str] = None


class PerformanceSummary(BaseModel):
    """Portfolio value change over a trailing window, using snapshots."""

    period: PeriodLiteral
    start_value: Optional[float] = None
    end_value: Optional[float] = None
    absolute_change: Optional[float] = None
    percent_change: Optional[float] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    has_data: bool = True
    note: Optional[str] = None


class AssistantAnswer(BaseModel):
    """Final response returned to the frontend."""

    answer: str
    tools_used: list[str] = Field(default_factory=list)
