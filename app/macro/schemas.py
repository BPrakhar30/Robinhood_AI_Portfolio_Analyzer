"""Pydantic schemas for the Macro Pulse feature."""

from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


Signal = Literal["bullish", "bearish", "neutral", "caution"]


class MacroIndicator(BaseModel):
    """One macro indicator with its current value and context."""

    key: str
    label: str
    value: Optional[float] = None
    display_value: str = ""
    change: Optional[float] = None
    change_display: str = ""
    signal: Signal = "neutral"
    signal_label: str = ""
    description: str = ""
    portfolio_impact: str = ""
    detail: str = ""
    category: Literal["essential", "important", "contextual"] = "essential"
    unit: str = ""


class PortfolioExposure(BaseModel):
    """User's portfolio broken down by macro-relevant dimensions."""

    rate_sensitive_pct: float = 0.0
    cyclical_pct: float = 0.0
    defensive_pct: float = 0.0
    growth_pct: float = 0.0
    value_pct: float = 0.0
    international_revenue_pct: float = 0.0
    energy_pct: float = 0.0
    total_positions: int = 0
    total_market_value: float = 0.0
    symbols_by_category: dict[str, list[str]] = Field(default_factory=dict)


class MacroAlert(BaseModel):
    """A threshold-triggered alert for the dashboard."""

    indicator_key: str
    indicator_label: str
    severity: Literal["info", "warning", "critical"] = "warning"
    title: str
    message: str
    link: str = "/macro-pulse"


class MacroPulseResponse(BaseModel):
    """Full Macro Pulse API payload."""

    indicators: list[MacroIndicator] = Field(default_factory=list)
    exposure: PortfolioExposure = Field(default_factory=PortfolioExposure)
    ai_summary: Optional[str] = None
    detailed_summary: Optional[str] = None
    alerts: list[MacroAlert] = Field(default_factory=list)
    updated_at: datetime
