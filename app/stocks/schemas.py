"""Wire-level DTOs for per-symbol market data.

Every field here is shaped for direct consumption by the Stock Detail
page and the assistant MCP tools — no ORM leak.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


CandleRange = Literal["1D", "1W", "1M", "3M", "YTD", "1Y", "5Y", "MAX"]
AssetTypeLiteral = Literal[
    "stock",
    "etf",
    "crypto",
    "option",
    "mutual_fund",
    "bond",
    "cash",
    "unknown",
]


# ── Profile / About ──────────────────────────────────────────────────


class StockProfile(BaseModel):
    """Company / fund profile — powers the About section."""

    symbol: str
    name: str
    asset_type: AssetTypeLiteral = "stock"
    exchange: Optional[str] = None
    currency: str = "USD"
    country: Optional[str] = None
    sector: Optional[str] = None
    industry: Optional[str] = None
    website: Optional[str] = None
    logo: Optional[str] = None
    description: Optional[str] = None
    ceo: Optional[str] = None
    employees: Optional[int] = None
    headquarters: Optional[str] = None
    founded: Optional[int] = None
    ipo_date: Optional[date] = None


# ── Live quote ───────────────────────────────────────────────────────


class StockQuote(BaseModel):
    """Latest quote snapshot — powers the page header pricing."""

    symbol: str
    price: Optional[float] = None
    previous_close: Optional[float] = None
    open: Optional[float] = None
    day_high: Optional[float] = None
    day_low: Optional[float] = None
    volume: Optional[float] = None
    change: Optional[float] = None
    change_percent: Optional[float] = None
    currency: str = "USD"
    market_state: Optional[str] = None  # REGULAR / CLOSED / PRE / POST if known
    as_of: Optional[datetime] = None


# ── Historical candles ───────────────────────────────────────────────


class CandlePoint(BaseModel):
    """One downsampled OHLC bar."""

    t: datetime
    o: float
    h: float
    low: float = Field(alias="l")  # ``l`` is a single-char field, alias avoids the shadow
    c: float
    v: Optional[float] = None

    model_config = {"populate_by_name": True}


class StockCandles(BaseModel):
    symbol: str
    range: CandleRange
    interval: str  # e.g. "5m", "1d"
    points: list[CandlePoint] = Field(default_factory=list)
    # Pre-computed so the UI doesn't recompute every render.
    start_price: Optional[float] = None
    end_price: Optional[float] = None
    change: Optional[float] = None
    change_percent: Optional[float] = None


# ── Key statistics ───────────────────────────────────────────────────


class StockKeyStats(BaseModel):
    """Fundamentals grid shown under the About section."""

    symbol: str
    market_cap: Optional[float] = None
    pe_ratio: Optional[float] = None
    forward_pe: Optional[float] = None
    dividend_yield: Optional[float] = None  # as a ratio (0.023 == 2.3%)
    eps_ttm: Optional[float] = None
    beta: Optional[float] = None
    average_volume: Optional[float] = None
    volume: Optional[float] = None
    day_high: Optional[float] = None
    day_low: Optional[float] = None
    open_price: Optional[float] = None
    fifty_two_week_high: Optional[float] = None
    fifty_two_week_low: Optional[float] = None
    short_ratio: Optional[float] = None
    shares_outstanding: Optional[float] = None


# ── Earnings ─────────────────────────────────────────────────────────


class EarningsQuarter(BaseModel):
    """One historical / upcoming earnings event."""

    date: date
    quarter: Optional[int] = None
    year: Optional[int] = None
    eps_estimate: Optional[float] = None
    eps_actual: Optional[float] = None
    revenue_estimate: Optional[float] = None
    revenue_actual: Optional[float] = None
    hour: Optional[str] = None
    # Derived: "beat" / "miss" / "inline" / None (not yet reported / no estimate).
    surprise: Optional[Literal["beat", "miss", "inline"]] = None
    surprise_percent: Optional[float] = None
    reported: bool = False


class StockEarnings(BaseModel):
    symbol: str
    next_event: Optional[EarningsQuarter] = None
    history: list[EarningsQuarter] = Field(default_factory=list)


# ── News (per-symbol) ────────────────────────────────────────────────


class StockNewsItem(BaseModel):
    """A single company-news article."""

    id: Optional[str] = None
    symbol: Optional[str] = None  # Filled when this came from an aggregation.
    headline: str
    summary: str = ""
    ai_summary: Optional[str] = None
    sentiment: Optional[str] = None  # "positive", "negative", "neutral" for portfolio news
    source: str
    source_url: Optional[str] = None
    url: str
    image: Optional[str] = None
    published_at: datetime
    time_ago: str = ""


class StockNewsResponse(BaseModel):
    symbol: str
    articles: list[StockNewsItem] = Field(default_factory=list)
    updated_at: datetime


# ── Position summary ─────────────────────────────────────────────────


class StockPositionSummary(BaseModel):
    """How the signed-in user is positioned in this symbol (if at all)."""

    symbol: str
    owned: bool = False
    shares: float = 0.0
    average_cost: Optional[float] = None
    market_value: Optional[float] = None
    total_invested: Optional[float] = None
    todays_return: Optional[float] = None
    todays_return_percent: Optional[float] = None
    total_return: Optional[float] = None
    total_return_percent: Optional[float] = None
    portfolio_weight_percent: Optional[float] = None
    asset_type: Optional[str] = None


# ── Composite detail response ────────────────────────────────────────


class StockDetailResponse(BaseModel):
    """One-shot payload for the Stock Detail page."""

    symbol: str
    profile: StockProfile
    quote: StockQuote
    key_stats: StockKeyStats
    earnings: StockEarnings
    position: StockPositionSummary
    news: list[StockNewsItem] = Field(default_factory=list)


# ── Universe / Stocks tab ────────────────────────────────────────────


class StockCardOut(BaseModel):
    """Minimal data for the Stocks-tab card grid."""

    symbol: str
    name: str
    sector: Optional[str] = None
    asset_type: AssetTypeLiteral = "stock"
    owned: bool = False
    price: Optional[float] = None
    change_percent: Optional[float] = None
    logo: Optional[str] = None


class StockUniverseResponse(BaseModel):
    items: list[StockCardOut] = Field(default_factory=list)
    total: int = 0
    owned_count: int = 0


# ── Portfolio-news (markets side, but defined here because it reuses
# StockNewsItem) ─────────────────────────────────────────────────────


class PortfolioNewsResponse(BaseModel):
    """Aggregated news across every holding for the signed-in user."""

    articles: list[StockNewsItem] = Field(default_factory=list)
    symbols: list[str] = Field(default_factory=list)
    updated_at: datetime


# ── AI stock analysis ────────────────────────────────────────────────


class StockAnalysisResponse(BaseModel):
    """AI-generated analysis combining chart, news, and holdings context."""

    symbol: str
    chart_analysis: str
    news_analysis: str
    holdings_impact: Optional[str] = None
    generated_at: datetime
