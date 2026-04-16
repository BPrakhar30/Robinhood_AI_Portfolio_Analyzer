from __future__ import annotations
from pydantic import BaseModel


class MarketHeadline(BaseModel):
    title: str
    summary: str
    source: str
    url: str


class MarketSummaryResponse(BaseModel):
    headlines: list[MarketHeadline]
    updated_at: str


class RecentDevelopment(BaseModel):
    source: str
    time_ago: str
    title: str
    excerpt: str
    url: str


class RecentDevelopmentsResponse(BaseModel):
    articles: list[RecentDevelopment]
    updated_at: str


class EarningsDay(BaseModel):
    date: str
    day_label: str
    earnings_count: int
    symbols: list[str]


class EarningsCalendarResponse(BaseModel):
    week: list[EarningsDay]
    selected_date: str


class EarningsEntry(BaseModel):
    symbol: str
    company: str
    date: str
    hour: str
    quarter: int
    year: int
    eps_estimate: float | None = None
    eps_actual: float | None = None
    revenue_estimate: float | None = None
    revenue_actual: float | None = None


class EarningsListResponse(BaseModel):
    entries: list[EarningsEntry]
    date: str
